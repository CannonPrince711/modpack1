#!/usr/bin/env python3
"""Unit test for the pack's mod resolver.

The build sandbox cannot reach api.modrinth.com, so the resolver's *logic* is proven here
against synthetic API payloads shaped exactly like Modrinth's /project/{id}/version
response. This tests the parts that can silently pick the wrong jar: version_number
matching, loader filtering, game-version filtering, and primary-file selection.

Run:  python3 tools/tests/test_fetch_mods.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fetch_mods as fm  # noqa: E402

# a realistic payload: the pinned version, a newer beta for the wrong loader, an older build
FAKE = [
    {"id": "old", "version_number": "1.20.1-6.0.6", "version_type": "release",
     "loaders": ["forge", "neoforge"], "game_versions": ["1.20.1"],
     "date_published": "2025-06-11T00:00:00Z",
     "files": [{"filename": "create-1.20.1-6.0.6.jar", "primary": True,
                "url": "https://cdn.modrinth.com/data/LNytGWDc/versions/A/create-1.20.1-6.0.6.jar",
                "size": 100, "hashes": {"sha1": "aa", "sha512": "bb"}}]},
    {"id": "want", "version_number": "1.20.1-6.0.8", "version_type": "release",
     "loaders": ["forge", "neoforge"], "game_versions": ["1.20.1"],
     "date_published": "2025-11-02T00:00:00Z",
     "files": [{"filename": "sources.jar", "primary": False,
                "url": "https://cdn.modrinth.com/data/LNytGWDc/versions/B/sources.jar",
                "size": 9, "hashes": {"sha1": "cc", "sha512": "dd"}},
               {"filename": "create-1.20.1-6.0.8.jar", "primary": True,
                "url": "https://cdn.modrinth.com/data/LNytGWDc/versions/B/create-1.20.1-6.0.8.jar",
                "size": 200, "hashes": {"sha1": "ee", "sha512": "ff"}}]},
    {"id": "fabric", "version_number": "1.20.1-6.0.8", "version_type": "release",
     "loaders": ["fabric"], "game_versions": ["1.20.1"],
     "files": [{"filename": "create-fabric.jar", "primary": True, "url": "https://x/fabric.jar",
                "size": 1, "hashes": {"sha1": "00"}}]},
    {"id": "wrongmc", "version_number": "1.20.1-6.0.8", "version_type": "release",
     "loaders": ["forge"], "game_versions": ["1.21.1"],
     "files": [{"filename": "create-1.21.1.jar", "primary": True, "url": "https://x/121.jar",
                "size": 1, "hashes": {"sha1": "11"}}]},
]


def run():
    fm.get_json = lambda url: FAKE          # stub the network
    mod = {"slug": "create", "name": "Create", "version": "1.20.1-6.0.8",
           "filename": "create-1.20.1-6.0.8.jar", "environment": "both",
           "source": {"kind": "modrinth", "project": "LNytGWDc"}}
    r = fm.resolve_modrinth(mod, "1.20.1")
    checks = [
        ("picks the pinned version, not the older one", r["version"] == "1.20.1-6.0.8"),
        ("ignores the fabric build with the same version", r["version_id"] == "want"),
        ("ignores the build for another Minecraft version", r["version_id"] != "wrongmc"),
        ("takes the primary file, not the sources jar",
         r["filename"] == "create-1.20.1-6.0.8.jar"),
        ("carries the publisher's sha1 through", r["sha1"] == "ee"),
        ("carries the publisher's sha512 through", r["sha512"] == "ff"),
        ("keeps the download URL from the API", r["url"].endswith("create-1.20.1-6.0.8.jar")),
    ]

    # a pin that does not exist must fail loudly rather than fall back to something else
    bad = dict(mod, version="9.9.9")
    try:
        fm.resolve_modrinth(bad, "1.20.1")
        checks.append(("unknown pin raises instead of silently picking another build", False))
    except SystemExit as e:
        checks.append(("unknown pin raises instead of silently picking another build",
                       "9.9.9" in str(e)))

    # curseforge entries must resolve to their pinned CDN URL without touching the API
    cf = fm.resolve_curseforge({
        "slug": "ftb-library", "name": "FTB Library", "version": "2001.2.13",
        "filename": "ftb-library-forge-2001.2.13.jar", "environment": "both",
        "source": {"kind": "curseforge", "project": 404465, "file": 8226927,
                   "url": "https://edge.forgecdn.net/files/8226/927/ftb-library-forge-2001.2.13.jar"}})
    checks.append(("curseforge pin resolves offline to the pinned CDN url",
                   cf["url"].endswith("/8226/927/ftb-library-forge-2001.2.13.jar")))

    ok = True
    for name, passed in checks:
        print(f"  [{'ok' if passed else 'FAIL'}] {name}")
        ok &= bool(passed)
    print(f"{sum(1 for _, p in checks if p)}/{len(checks)} resolver checks passed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
