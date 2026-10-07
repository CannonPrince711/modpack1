#!/usr/bin/env python3
"""Generates MODLIST.md from pack/mods.lock.json so the list can never drift from the
actual pins, and refreshes the mod table inside export/curseforge + export/server docs.

Run:  python3 tools/gen_docs.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = json.loads((ROOT / "pack/mods.lock.json").read_text(encoding="utf-8"))

ENV_LABEL = {
    "both": "both sides",
    "client": "client only",
    "client-optional": "client (optional on server)",
    "server": "server side (safe in singleplayer)",
}

GROUPS = [
    ("Foundation", "worldgen-independent core the whole pack stands on",
     ["create", "farmers-delight"]),
    ("Landscape & structures", "the drained basin's silhouette",
     ["yungs-extras", "yungs-api", "paxi"]),
    ("Life", "the only fauna in the pack",
     ["alexs-mobs", "citadel"]),
    ("Depth system — light and conjuration", "the magic pillar, deliberately not a combat pillar",
     ["ars-nouveau"]),
    ("Travel", "vertical travel that is earned and finite",
     ["paragliders"]),
    ("Carrying & storage", "one backpack instead of six storage mods",
     ["sophisticated-backpacks", "sophisticated-core"]),
    ("Survival & recovery", "death in a large landscape must not cost an hour of walking",
     ["corail-tombstone"]),
    ("Quest book", "the pack's direction-of-travel, solo and co-op",
     ["ftb-quests", "ftb-library", "ftb-teams", "architectury"]),
    ("Interface & information", "one recipe viewer, one map, both optional and quiet",
     ["emi", "xaeros-minimap"]),
    ("Performance", "mid-range hardware, 6 GB client target",
     ["embeddium", "oculus", "modernfix"]),
    ("Ambience", "wind on salt and surf under glass",
     ["ambientsounds", "creativecore"]),
]


def main() -> int:
    by_slug = {m["slug"]: m for m in LOCK["mods"]}
    p = LOCK["pack"]
    out = []
    A = out.append

    A("# MODLIST — Saltglass v" + p["version"])
    A("")
    A(f"**Minecraft {p['minecraft']} · Forge {p['forge']['version']} · Java {p['java']}**")
    A("")
    A(f"{len(LOCK['mods'])} mods. Every pin was checked on the project's own page on "
      "Modrinth or CurseForge on 2026-10-07; the exact evidence, including the ones where a "
      "newer build existed and was *rejected*, is in `pack/mods.lock.json` under "
      "`verification.sources` and `verification.note`.")
    A("")
    A("| Legend | Meaning |")
    A("| --- | --- |")
    A("| `verified` | loader, MC version, environment and filename read from the project page |")
    A("| `inferred` | version + loader + environment confirmed; jar filename resolved by the "
      "build tool from the project API rather than quoted |")
    A("")
    A("Nothing in this pack is a mirror, an edited jar, or a manual install. "
      "No 'latest'. No betas. No OptiFine.")
    A("")
    A("---")
    A("")

    seen: set[str] = set()
    for title, why, slugs in GROUPS:
        A(f"## {title}")
        A("")
        A(f"*{why}*")
        A("")
        A("| Mod | Version | MC | Sides | Verified |")
        A("| --- | --- | --- | --- | --- |")
        for slug in slugs:
            m = by_slug.get(slug)
            if not m:
                raise SystemExit(f"lockfile is missing '{slug}' referenced by gen_docs")
            seen.add(slug)
            badge = "verified" if m["verification"]["status"] == "official-page-verified" \
                else "inferred"
            link = f"[{m['name']}]({m['source'].get('page', '')})" if m["source"].get("page") \
                else m["name"]
            A(f"| {link} | `{m['version']}` | {p['minecraft']} | {ENV_LABEL[m['environment']]} "
              f"| {badge} |")
        A("")
        for slug in slugs:
            m = by_slug[slug]
            A(f"**{m['name']}** — {m['purpose']}")
            A("")
        A("---")
        A("")

    missing = [m["slug"] for m in LOCK["mods"] if m["slug"] not in seen]
    if missing:
        raise SystemExit(f"gen_docs groups do not cover: {missing}")

    A("## Dependencies, all of them")
    A("")
    A("| Mod | Requires |")
    A("| --- | --- |")
    for m in LOCK["mods"]:
        if m.get("deps"):
            A(f"| {m['name']} | {', '.join(d for d in m['deps'])} |")
    A("")
    A("Create 6.0.8 **bundles** Flywheel and Ponder inside its own jar. Installing a separate "
      "Flywheel is the single most common way a Create 6 pack fails to start, and is a "
      "licence-redundancy problem besides. Do not add one.")
    A("")

    A("## Considered and rejected")
    A("")
    A("Every one of these was verified for 1.20.1 Forge and then dropped anyway, because "
      "being compatible is not the same as earning a place.")
    A("")
    A("| Mod | Why it is not in the pack |")
    A("| --- | --- |")
    for r in LOCK["considered_and_rejected"]:
        A(f"| {r['mod']} | {r['reason']} |")
    A("")
    A("## Server-side exclusion list")
    A("")
    A("These jars are client-only or client-side and are **not** part of the server export. "
      "Putting any of them in a headless server's `mods/` folder is the usual cause of a "
      "server that will not boot.")
    A("")
    A("| Mod | Why |")
    A("| --- | --- |")
    for slug in ("embeddium", "oculus", "xaeros-minimap", "ambientsounds", "creativecore",
                 "emi"):
        m = by_slug[slug]
        A(f"| {m['name']} | {ENV_LABEL[m['environment']]} |")
    A("")

    text = "\n".join(out) + "\n"
    (ROOT / "MODLIST.md").write_text(text, encoding="utf-8")
    print(f"wrote MODLIST.md ({len(LOCK['mods'])} mods, {len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
