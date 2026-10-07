#!/usr/bin/env python3
"""Build a Modrinth .mrpack from the checked-in immutable Modrinth lock."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "mods.lock.json"
OVERRIDES = ROOT / "overrides"
OUTPUT = ROOT / "Dungeon-Delvers-Odyssey.mrpack"


DEFAULT_ENV = {"client": "required", "server": "required"}


def build_manifest(lock: dict) -> dict:
    """Modrinth index for the lock. A mod's optional "env" entry ({"client", "server"}: required / optional /
    unsupported) keeps client-only mods (rendering, FPS) off the dedicated server."""
    mod_files = []
    for mod in lock["mods"] + lock.get("curseforge_mods", []):
        if not mod["sha1"] or not mod["sha512"]:
            raise ValueError(f"Missing immutable file hashes for {mod['name']}")
        mod_files.append(
            {
                "path": f"mods/{mod['filename']}",
                "hashes": {"sha1": mod["sha1"], "sha512": mod["sha512"]},
                "env": mod.get("env", DEFAULT_ENV),
                "downloads": [mod["url"]],
                "fileSize": mod["size"],
            }
        )
    return {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": lock["pack"]["version"],
        "name": lock["pack"]["name"],
        "summary": lock["pack"]["summary"],
        "files": mod_files,
        "dependencies": {
            "minecraft": lock["pack"]["minecraft"],
            "forge": lock["pack"]["forge"],
        },
    }


def build() -> Path:
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=True,
    )
    manifest = build_manifest(json.loads(LOCK.read_text(encoding="utf-8")))

    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "modrinth.index.json",
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )
        for file in sorted(OVERRIDES.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(OVERRIDES).as_posix())
    return OUTPUT


if __name__ == "__main__":
    print(build())
