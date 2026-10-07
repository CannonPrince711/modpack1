#!/usr/bin/env python3
"""Keep overlapping structure systems from piling on top of each other.

Several structure mods in the pack cover the same ground. This copies the relevant structure_set files out of the
mod jars and adds an exclusion_zone (the same mechanism vanilla uses to keep villages and outposts apart), writing
the result to overrides/kubejs/data/ where it overrides the originals.

  strongholds           YUNG's Better Strongholds and the Dungeons and Taverns stronghold overhaul both generate
                        a stronghold system, and both are Eye of Ender targets. The D&T/vanilla rings now keep
                        16 chunks clear of YUNG's strongholds.
  jungle / swamp towns  Dungeons and Taverns adds its own jungle and swamp villages beside CTOV's, which already
                        feed the vanilla village set. They now keep 10 chunks clear of any village.

The Dungeons and Taverns modules themselves need nothing: their shared files are byte-identical apart from one
biome tag, so they stack cleanly.

  python3 tools/gen_structure_fit.py --mods <dir with the pack's jars>
"""

from __future__ import annotations

import argparse
import glob
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "overrides" / "kubejs" / "data"

# (jar glob, member path, other_set to stay away from, chunk_count)
FITS = [
    ("dungeons-and-taverns-stronghold-rework*.jar", "data/minecraft/worldgen/structure_set/strongholds.json",
     "betterstrongholds:stronghold", 16),
    ("dungeons-and-taverns-3*.jar", "data/nova_structures/worldgen/structure_set/villages_jungle.json",
     "minecraft:villages", 10),
    ("dungeons-and-taverns-3*.jar", "data/nova_structures/worldgen/structure_set/villages_swamp.json",
     "minecraft:villages", 10),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mods", required=True)
    args = parser.parse_args()
    for jar_glob, member, other_set, chunks in FITS:
        jars = sorted(glob.glob(f"{args.mods}/{jar_glob}"))
        if not jars:
            raise SystemExit(f"no jar matches {jar_glob}")
        placement_file = json.loads(zipfile.ZipFile(jars[0]).read(member))
        placement_file["placement"]["exclusion_zone"] = {"other_set": other_set, "chunk_count": chunks}
        target = DATA / Path(member).relative_to("data")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(placement_file, indent=2) + "\n", encoding="utf-8")
        print(f"{target.relative_to(ROOT)}: keeps {chunks} chunks clear of {other_set}")


if __name__ == "__main__":
    main()
