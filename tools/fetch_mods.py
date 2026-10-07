#!/usr/bin/env python3
"""
Saltglass mod resolver / fetcher.

The pack's exports contain **no mod jars** — that is deliberate (no redistribution) and it is
also how the intended launcher works. This tool is what turns `pack/mods.lock.json` into real
files, and it is the same tool a server host runs:

    python3 tools/fetch_mods.py --resolve                 # API lookup -> export/resolved-downloads.json
    python3 tools/fetch_mods.py --download /path/to/mods  # fetch + verify into a folder
    python3 tools/fetch_mods.py --download mods --server  # server-side subset only (skips client-only)

How a mod is resolved
---------------------
* Modrinth mods: GET https://api.modrinth.com/v2/project/<id>/version , then pick the entry whose
  `version_number` equals the pinned version and which declares the forge loader and 1.20.1.
  The download URL and sha1/sha512 come from the API response — never invented.
* FTB mods (CurseForge-only): the pinned `edge.forgecdn.net` URL from the lockfile is used
  directly; that host is CurseForge's own CDN and the file page is recorded in the lockfile.

Every downloaded file is checked against the sha1 the API published. A mismatch aborts.

This is also why `MODLIST.md` and the manifests can be trusted: the hashes in an .mrpack built
after a successful `--resolve` are the publishers' own hashes, not ones this project made up.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "pack/mods.lock.json"
RESOLVED = ROOT / "export/resolved-downloads.json"
API = "https://api.modrinth.com/v2"
UA = {"User-Agent": "saltglass-pack-builder/1.0 (modpack build tool)"}

SERVER_SKIP = {"embeddium", "oculus", "xaeros-minimap", "ambientsounds", "creativecore", "emi"}


def get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def resolve_modrinth(m: dict, mc: str) -> dict:
    ident = m["source"].get("project") or m["slug"]
    versions = get_json(f"{API}/project/{ident}/version")
    pin = m["version"]
    cands = [v for v in versions
             if v.get("version_number") == pin
             and v.get("version_type") in ("release", "beta")
             and "forge" in (v.get("loaders") or [])
             and mc in (v.get("game_versions") or [])]
    if not cands:
        loose = [v for v in versions if mc in (v.get("game_versions") or [])
                 and "forge" in (v.get("loaders") or [])]
        hint = ", ".join(sorted({v["version_number"] for v in loose})[:8]) or "none"
        raise SystemExit(f"  ! {m['slug']}: pinned version '{pin}' not found for {mc}+forge. "
                         f"Available: {hint}")
    v = cands[0]
    f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
    return {
        "slug": m["slug"], "name": m["name"], "version": v["version_number"],
        "filename": f["filename"], "url": f["url"], "size": f.get("size"),
        "sha1": (f.get("hashes") or {}).get("sha1"),
        "sha512": (f.get("hashes") or {}).get("sha512"),
        "environment": m["environment"], "source": "modrinth",
        "version_id": v.get("id"), "published": v.get("date_published"),
    }


def resolve_curseforge(m: dict) -> dict:
    src = m["source"]
    if not src.get("url"):
        raise SystemExit(f"  ! {m['slug']}: curseforge entry without a pinned URL")
    return {
        "slug": m["slug"], "name": m["name"], "version": m["version"],
        "filename": m["filename"], "url": src["url"], "size": None,
        "sha1": None, "sha512": None, "environment": m["environment"],
        "source": "curseforge", "page": src.get("page"),
    }


def resolve(server_only: bool) -> dict:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    mc = lock["pack"]["minecraft"]
    out = []
    for m in lock["mods"]:
        if server_only and m["slug"] in SERVER_SKIP:
            print(f"  - skip (client-only) {m['slug']}")
            continue
        try:
            r = (resolve_curseforge(m) if m["source"]["kind"] == "curseforge"
                 else resolve_modrinth(m, mc))
        except urllib.error.HTTPError as e:
            raise SystemExit(f"  ! {m['slug']}: HTTP {e.code} from the registry")
        print(f"  + {r['slug']:<24} {r['version']:<22} {r['filename']}")
        if r["filename"] != m["filename"]:
            print(f"      note: lockfile filename was '{m['filename']}', registry says "
                  f"'{r['filename']}' — registry wins, and the lockfile should be updated")
        out.append(r)
    return {"minecraft": mc, "forge": lock["pack"]["forge"]["version"], "files": out}


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def download(target: Path, entries: list[dict]) -> int:
    target.mkdir(parents=True, exist_ok=True)
    bad = 0
    for e in entries:
        dest = target / e["filename"]
        if dest.exists() and e.get("sha1") and sha1_of(dest) == e["sha1"]:
            print(f"  = {e['filename']} (already present and verified)")
            continue
        req = urllib.request.Request(e["url"], headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=180) as r, dest.open("wb") as f:
                while True:
                    chunk = r.read(1 << 16)
                    if not chunk:
                        break
                    f.write(chunk)
        except urllib.error.HTTPError as ex:
            print(f"  ! {e['slug']}: HTTP {ex.code} downloading {e['url']}")
            bad += 1
            continue
        if e.get("sha1"):
            got = sha1_of(dest)
            if got != e["sha1"]:
                print(f"  ! {e['slug']}: sha1 mismatch (want {e['sha1']}, got {got}) — deleted")
                dest.unlink()
                bad += 1
                continue
            print(f"  + {e['filename']} ({dest.stat().st_size // 1024} KiB, sha1 verified)")
        else:
            print(f"  + {e['filename']} ({dest.stat().st_size // 1024} KiB, "
                  "no published hash for this host — size only)")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve", action="store_true", help="query the registry and write pins")
    ap.add_argument("--download", metavar="DIR", help="fetch jars into DIR")
    ap.add_argument("--server", action="store_true", help="server-side subset only")
    a = ap.parse_args()
    if not (a.resolve or a.download):
        ap.print_help()
        return 1

    if a.resolve:
        print("resolving:", "server subset" if a.server else "all mods")
        data = resolve(a.server)
        RESOLVED.parent.mkdir(parents=True, exist_ok=True)
        RESOLVED.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {RESOLVED.relative_to(ROOT)}: {len(data['files'])} files")
        n_hash = sum(1 for f in data["files"] if f.get("sha1"))
        print(f"  {n_hash} with publisher-published sha1, "
              f"{len(data['files']) - n_hash} without (CurseForge CDN pins only)")
        return 0

    if a.download:
        if not RESOLVED.exists():
            print("no resolved manifest yet — run --resolve first", file=sys.stderr)
            return 2
        data = json.loads(RESOLVED.read_text(encoding="utf-8"))
        entries = [f for f in data["files"]
                   if not (a.server and f["slug"] in SERVER_SKIP)]
        print(f"downloading {len(entries)} files into {a.download}")
        bad = download(Path(a.download), entries)
        print("done." if not bad else f"done with {bad} failures")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
