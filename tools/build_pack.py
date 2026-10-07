#!/usr/bin/env python3
"""
Saltglass pack builder.

Reads  pack/mods.lock.json  +  pack/overrides/**  +  pack/datapack/**
Writes export/*  (Modrinth .mrpack, CurseForge tree + manifest, server export, manifests)

Deterministic: same inputs -> byte-identical modrinth.index.json / manifest.json.
It also *is* the validator: `--check` (default on) enforces the rules from the brief
(no 'latest', one worldgen stack, one recipe viewer, dependency closure, licence recorded,
no placeholders, datapack JSON well-formed, no duplicate paths) and refuses to build on failure.

  python3 tools/build_pack.py            # build + validate
  python3 tools/build_pack.py --server   # also write the server export tree
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "pack/mods.lock.json"
OVERRIDES = ROOT / "pack/overrides"
DATAPACK = OVERRIDES / "config/paxi/datapacks/saltglass"
EXPORT = ROOT / "export"

# ---------------------------------------------------------------- exclusions
# Client-only mods are removed from the server export; server-never mods from the client
# mrpack would break the launcher, so they ship in both and are labelled by environment.
CLIENT_ONLY_ENVS = {"client", "client-optional"}
SERVER_NEVER = {"embeddium", "oculus", "xaeros-minimap", "ambientsounds", "creativecore", "emi"}


class BuildError(Exception):
    pass


def load_lock():
    return json.loads(LOCK.read_text(encoding="utf-8"))


def load_resolved() -> dict:
    """Publisher hashes + URLs from `tools/fetch_mods.py --resolve`, when it has been run.

    If it has not, entries keep empty hash maps and the CurseForge/CDN URL only — because a
    hash this project invented would be worse than a missing one."""
    p = EXPORT / "resolved-downloads.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return {f["slug"]: f for f in data.get("files", [])}


def lockfile_pins(lock: dict) -> dict:
    """Publisher-verified pins recorded in the lockfile itself (see tools/apply_verified_pins.py)."""
    return {m["slug"]: m["pins"] for m in lock.get("mods", []) if m.get("pins")}


RESOLVED_FILES: dict = {}


def sha512_b64(path: Path) -> str:
    h = hashlib.sha512()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return base64.b64encode(h.digest()).decode()


def sha1_hex(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- validation
def validate(lock: dict) -> list[str]:
    problems: list[str] = []
    mods = lock["mods"]
    slugs = [m["slug"] for m in mods]

    if len(set(slugs)) != len(slugs):
        problems.append("duplicate mod slugs in lockfile")

    slugs_set = set(slugs)
    for m in mods:
        for d in m.get("deps", []):
            if d not in slugs_set:
                problems.append(f"{m['slug']}: dependency '{d}' is not in the pack")
        for field in ("slug", "name", "version", "filename", "environment", "purpose",
                      "verification", "source"):
            if not m.get(field):
                problems.append(f"{m['slug']}: missing field '{field}'")
        if re.search(r"\b(latest|current|latest-version|TBD|TODO)\b", str(m["version"]), re.I):
            problems.append(f"{m['slug']}: version must be an exact pin, found '{m['version']}'")
        if not m["filename"].endswith(".jar"):
            problems.append(f"{m['slug']}: filename is not a .jar")
        if m["environment"] not in ("both", "client", "server", "client-optional"):
            problems.append(f"{m['slug']}: bad environment '{m['environment']}'")
        v = m["verification"]
        if v.get("status") not in ("official-page-verified", "filename-inferred"):
            problems.append(f"{m['slug']}: unrecognised verification status")
        if not v.get("sources"):
            problems.append(f"{m['slug']}: no verification source recorded")
        if not str(m.get("license", "")).strip():
            problems.append(f"{m['slug']}: no licence recorded")
        mc = lock["pack"]["minecraft"]
        if mc not in json.dumps(m):
            problems.append(f"{m['slug']}: no mention of Minecraft {mc} in the entry "
                            "(version string or verification note) — pin must be MC-specific")

    # one worldgen stack, one recipe viewer, one quest system
    if sum(1 for s in slugs_set if s in ("terralith", "terralith-forge", "boilerplate")) > 1:
        problems.append("more than one worldgen stack")
    viewers = {"jei", "rei", "emi", "just-enough-items"} & slugs_set
    if len(viewers) > 1:
        problems.append(f"more than one recipe viewer: {sorted(viewers)}")
    if not viewers:
        problems.append("no recipe viewer at all")
    if "ftb-quests" not in slugs_set:
        problems.append("quest system missing")

    # rejections in DESIGN.md must actually hold
    banned = {"optifine", "anyflight", "creativecore-forge-elytra", "elytra-slot", "parachest"}
    if banned & slugs_set:
        problems.append(f"banned-by-design mod present: {sorted(banned & slugs_set)}")

    # datapack JSON well-formedness
    for p in sorted(DATAPACK.rglob("*.json")):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            problems.append(f"invalid JSON in datapack: {p.relative_to(ROOT)}: {e}")
    for p in sorted(DATAPACK.rglob("*.mcfunction")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.count("{") != s.count("}"):
                problems.append(f"unbalanced braces {p.relative_to(ROOT)}:{i}: {s[:60]}")
    # no placeholders anywhere in what we ship
    for base in (OVERRIDES, DATAPACK):
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix in (".txt", ".toml", ".json", ".mcfunction", ".md",
                                            ".lang", ".pack-mcmeta"):
                if re.search(r"\b(TODO|TBD|FIXME|placeholder|coming soon)\b",
                             p.read_text(encoding="utf-8"), re.I):
                    problems.append(f"placeholder text in shipped file: {p.relative_to(ROOT)}")

    for name in ("README.md", "MODLIST.md", "DESIGN.md", "CREDITS_AND_LICENSES.md",
                 "CHANGELOG.md", "TEST_REPORT.md", "INTEGRATION_LOG.md"):
        if not (ROOT / name).exists():
            problems.append(f"missing deliverable: {name}")
    return problems


# ---------------------------------------------------------------- datapack assembly
def install_datapack(target: Path, side: str) -> None:
    """Copy the authoring datapack into a target dir, generating pack.mcmeta deterministically."""
    target.mkdir(parents=True, exist_ok=True)
    for src in sorted(DATAPACK.rglob("*")):
        rel = src.relative_to(DATAPACK)
        dst = target / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if src.name == "pack.mcmeta":
            data = json.loads(src.read_text(encoding="utf-8"))
            data["pack"].setdefault("description",
                                    "Saltglass — the drained basin, the Reflected Deep, "
                                    "and the Turning. " + side)
            dst.mkdir(parents=True, exist_ok=True) if dst.is_dir() else None
            dst.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


# ---------------------------------------------------------------- mrpack
def mrpack_files(lock: dict, only: set[str] | None = None) -> list[dict]:
    out = []
    for m in lock["mods"]:
        if only is not None and m["slug"] not in only:
            continue
        env = m["environment"]
        if env == "client":
            mr_env = {"client": "required", "server": "unsupported"}
        elif env == "server":
            mr_env = {"client": "optional", "server": "required"}
        elif env == "client-optional":
            mr_env = {"client": "required", "server": "optional"}
        else:
            mr_env = {"client": "required", "server": "required"}

        entry = {
            "path": f"mods/{m['filename']}",
            "hashes": {},
            "envs": mr_env,
            "downloads": [],
        }
        pins = (RESOLVED_FILES or {}).get(m["slug"]) or m.get("pins") or {}
        if pins.get("sha1") and pins.get("sha512"):
            entry["hashes"] = {"sha1": pins["sha1"], "sha512": pins["sha512"]}
            entry["downloads"] = [pins["url"]]
            if pins.get("size"):
                entry["fileSize"] = pins["size"]
            if pins.get("filename") and pins["filename"] != m["filename"]:
                entry["path"] = f"mods/{pins['filename']}"
        elif m["source"]["kind"] == "curseforge" and m["source"].get("url"):
            # Pinned canonical CurseForge CDN file. Modrinth App accepts non-Modrinth
            # download URLs; hashes stay empty (see docs/PACK_MANIFEST_NOTES.md) because
            # they must come from the authoritative API, never be invented.
            entry["downloads"] = [m["source"]["url"]]
        out.append(entry)
    return sorted(out, key=lambda e: e["path"])


def build(lock: dict, icon: Path, out_dir: Path) -> dict:
    p = lock["pack"]
    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": p["version"],
        "required": ["minecraft", "forge"],
        "gameVersion": p["minecraft"],
        "projectID": None,
        "modloaderVersion": p["forge"]["version"],
        "license": "SEE CREDITS_AND_LICENSES.md",
        "icon": None,
        "name": p["name"],
        "version": p["version"],
        "title": "Saltglass",
        "dependencies": {"minecraft": p["minecraft"], "forge": p["forge"]["version"]},
        "files": mrpack_files(lock),
        "overrides": "overrides",
    }
    index.pop("projectID")
    index.pop("modloaderVersion")
    index["license"] = "MIT (pack content) — third-party mods keep their own licences"
    if icon.exists():
        index["icon"] = "data:image/png;base64," + base64.b64encode(icon.read_bytes()).decode()

    # ---- overrides tree for the mrpack
    work = out_dir / "_overrides"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(OVERRIDES, work)
    # The datapack ships inside the overrides at config/paxi/datapacks/saltglass/ —
    # Paxi loads it into every world on both sides, so there is exactly one copy to keep
    # in sync and no per-world install step. The same directory is reused in the server
    # export's defaultconfigs/ so a host can copy it into config/paxi/datapacks/.
    srv_dp = out_dir / "reference-server" / "defaultconfigs" / "saltglass_datapack"
    install_datapack(srv_dp, "server copy: place in config/paxi/datapacks/saltglass")

    # pack-format docs travel inside overrides so an installed pack explains itself
    docs = work / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for doc in ("README.md", "MODLIST.md", "CREDITS_AND_LICENSES.md", "CHANGELOG.md",
                "INTEGRATION_LOG.md", "DESIGN.md", "TEST_REPORT.md"):
        src = ROOT / doc
        if src.exists():
            shutil.copy2(src, docs / doc)

    mrpack = out_dir / f"saltglass-{p['version']}.mrpack"
    with zipfile.ZipFile(mrpack, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, indent=2, sort_keys=False) + "\n")
        for f in sorted(work.rglob("*")):
            if f.is_file():
                z.write(f, "overrides/" + str(f.relative_to(work)))
    shutil.rmtree(work)

    # ---- CurseForge tree + manifest.json
    cf = out_dir / "curseforge"
    if cf.exists():
        shutil.rmtree(cf)
    shutil.copytree(OVERRIDES, cf)
    shutil.copytree(out_dir / "reference-server" / "defaultconfigs",
                    cf / "defaultconfigs", dirs_exist_ok=True)
    files = []
    for m in lock["mods"]:
        if m["source"]["kind"] == "curseforge":
            files.append({"projectID": m["source"]["project"], "fileID": m["source"]["file"]})
    manifest = {
        "minecraft": {"version": p["minecraft"], "modLoaders": [
            {"id": f"forge-{p['forge']['version'].split('-')[1]}", "primary": True}]},
        "manifestType": "minecraftModpack", "manifestVersion": 1,
        "name": "Saltglass", "version": p["version"], "author": "Arena modpack studio",
        "fileProjectID": None, "overrides": "overrides",
        "files": sorted(files, key=lambda f: f["projectID"]),
    }
    manifest.pop("fileProjectID")
    (cf / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (cf / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # jars are not embedded in either format; the resolver downloads them (see docs)
    (cf / "mods").mkdir(exist_ok=True)

    # ---- server export
    srv = out_dir / "server"
    if srv.exists():
        shutil.rmtree(srv)
    (srv / "mods").mkdir(parents=True)
    server_slugs = {m["slug"] for m in lock["mods"] if m["slug"] not in SERVER_NEVER}
    (srv / "server-mods.tsv").write_text(
        "filename\tversion\tsource\turl_or_page\n" + "".join(
            f"{m['filename']}\t{m['version']}\t{m['source']['kind']}\t"
            f"{m['source'].get('url') or m['source'].get('page','')}\n"
            for m in lock["mods"] if m["slug"] in server_slugs), encoding="utf-8")
    (srv / "modlist.json").write_text(json.dumps(
        [{"filename": m["filename"], "slug": m["slug"], "version": m["version"],
          "source": m["source"]["kind"]} for m in lock["mods"] if m["slug"] in server_slugs],
        indent=2) + "\n", encoding="utf-8")
    install_datapack(srv / "defaultconfigs" / "saltglass_datapack", "server copy")
    for f in ("server.properties", "jvm_args.txt", "README-SERVER.md"):
        src = ROOT / "pack" / "server" / f
        if src.exists():
            shutil.copy2(src, srv / f)
    shutil.copy2(ROOT / "tools/fetch_mods.py", srv / "fetch_mods.py")
    (srv / "fetch-server-mods.sh").write_text(
        "#!/bin/sh\n"
        "# Saltglass — fetch and verify the server-side mods.\n"
        "# Needs Python 3.8+ and network access to api.modrinth.com and edge.forgecdn.net.\n"
        "set -e\n"
        'cd "$(dirname "$0")"\n'
        "python3 fetch_mods.py --resolve\n"
        "python3 fetch_mods.py --download mods --server\n"
        "echo 'mods/ is ready. Client-only jars were deliberately skipped.'\n",
        encoding="utf-8")
    (srv / "fetch-server-mods.sh").chmod(0o755)

    # zip the server export
    srv_zip = out_dir / f"saltglass-{p['version']}-server.zip"
    with zipfile.ZipFile(srv_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(srv.rglob("*")):
            if f.is_file():
                z.write(f, str(f.relative_to(srv)))

    # ---- human-readable resolved manifest
    (out_dir / "resolved-manifest.json").write_text(json.dumps(
        {"pack": p, "files": index["files"], "curseforge_manifest": manifest,
         "server_slugs": sorted(server_slugs)}, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(out_dir / "reference-server", ignore_errors=True)
    return {"mrpack": str(mrpack), "index": index, "server": str(srv_zip)}


def verify_export(out_dir: Path, res: dict, lock: dict) -> list[str]:
    """Re-open the artifacts we just wrote and check them as a launcher would."""
    problems: list[str] = []
    mrpack = Path(res["mrpack"])
    with zipfile.ZipFile(mrpack) as z:
        names = z.namelist()
        if "modrinth.index.json" not in names:
            problems.append("mrpack has no modrinth.index.json at its root")
        index = json.loads(z.read("modrinth.index.json").decode())
        for key in ("formatVersion", "game", "versionId", "name", "files", "dependencies"):
            if key not in index:
                problems.append(f"modrinth.index.json missing '{key}'")
        for e in index["files"]:
            if not e["path"].startswith("mods/"):
                problems.append(f"index file outside mods/: {e['path']}")
            if not e["downloads"]:
                problems.append(f"index entry without a download: {e['path']}")
            for side in ("client", "server"):
                if e["envs"].get(side) not in ("required", "optional", "unsupported"):
                    problems.append(f"bad envs for {e['path']}")
            if e["hashes"] and (len(e["hashes"].get("sha1", "")) != 40
                                or len(e["hashes"].get("sha512", "")) != 128):
                problems.append(f"malformed hash in index for {e['path']}")
        if not any(n == "overrides/config/paxi/datapacks/saltglass/pack.mcmeta" for n in names):
            problems.append("mrpack overrides are missing the datapack (pack.mcmeta)")
        for want in ("drowned_cathedral.nbt", "beacon_tower.nbt", "tide_trench.nbt"):
            if not any(n.endswith(want) for n in names):
                problems.append(f"mrpack overrides are missing structure {want}")
        if not any(n.startswith("overrides/config/ftbquests/quests/chapters/") for n in names):
            problems.append("mrpack overrides are missing the quest book")
        if index.get("dependencies", {}).get("minecraft") != lock["pack"]["minecraft"]:
            problems.append("mrpack declares the wrong Minecraft version")
        if index.get("dependencies", {}).get("forge") != lock["pack"]["forge"]["version"]:
            problems.append("mrpack declares the wrong Forge version")

    with zipfile.ZipFile(Path(res["server"])) as z:
        sn = z.namelist()
        for want in ("server.properties", "jvm_args.txt", "README-SERVER.md",
                     "server-mods.tsv", "fetch-server-mods.sh", "fetch_mods.py",
                     "defaultconfigs/saltglass_datapack/pack.mcmeta"):
            if want not in sn:
                problems.append(f"server export missing {want}")
        tsv = z.read("server-mods.tsv").decode()
        for client_only in ("embeddium", "oculus", "AmbientSounds", "CreativeCore",
                            "Xaeros_Minimap", "emi-"):
            if client_only.lower() in tsv.lower():
                problems.append(f"server export lists client-only mod: {client_only}")

    cf = out_dir / "curseforge"
    mf = cf / "manifest.json"
    if not mf.exists():
        problems.append("curseforge export has no manifest.json")
    else:
        data = json.loads(mf.read_text(encoding="utf-8"))
        if data.get("manifestType") != "minecraftModpack":
            problems.append("curseforge manifest has the wrong manifestType")
        ml = data.get("minecraft", {}).get("modLoaders", [{}])[0].get("id")
        if ml != f"forge-{lock['pack']['forge']['version'].split('-')[1]}":
            problems.append(f"curseforge manifest loader is '{ml}'")
        if not (cf / "config/paxi/datapacks/saltglass/pack.mcmeta").exists():
            problems.append("curseforge overrides are missing the datapack")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(EXPORT))
    ap.add_argument("--skip-check", action="store_true")
    ap.add_argument("--no-cf", action="store_true")
    a = ap.parse_args()

    global RESOLVED_FILES
    lock = load_lock()
    RESOLVED_FILES = load_resolved()
    RESOLVED_FILES.update({k: v for k, v in lockfile_pins(lock).items()
                           if k not in RESOLVED_FILES})
    problems = [] if a.skip_check else validate(lock)
    if problems:
        print("VALIDATION FAILED:")
        for p in problems:
            print("  -", p)
        return 2

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    res = build(lock, out_dir / "saltglass-icon" / "icon-256.png", out_dir)

    if not a.skip_check:
        vp = verify_export(out_dir, res, lock)
        if vp:
            print("EXPORT VERIFICATION FAILED:")
            for p in vp:
                print("  -", p)
            return 2
        print("export verification: ok "
              "(mrpack structure, index schema, datapack payload, server manifest)")

    n = len(lock["mods"])
    print(f"built: {n} mod files, {len(res['index']['files'])} mrpack entries")
    print("  " + res["mrpack"])
    print("  " + res["server"])
    if not a.no_cf:
        print("  " + str(out_dir / "curseforge"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
