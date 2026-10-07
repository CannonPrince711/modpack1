#!/usr/bin/env python3
"""Generate the ddo:trapvault structure template and its worldgen/loot datapack files.

Output goes to overrides/kubejs/data/ddo/. Everything is vanilla redstone: stone
pressure plates and trapped chests directly adjacent to dispensers power them, so
the traps need no wiring and no extra mods.
"""

from __future__ import annotations

import gzip
import json
import random
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "overrides" / "kubejs" / "data" / "ddo"

SIZE = (19, 11, 25)  # x, y, z
FLOOR = 5  # y of floor blocks; walking level is FLOOR + 1
WALK = FLOOR + 1
DATA_VERSION = 3465  # 1.20.1


# --- minimal NBT writer -------------------------------------------------------
class Byte(int): pass
class Long(int): pass


def _name(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


def _tag_id(v) -> int:
    if isinstance(v, Byte): return 1
    if isinstance(v, Long): return 4
    if isinstance(v, bool): raise TypeError("use Byte for booleans")
    if isinstance(v, int): return 3
    if isinstance(v, str): return 8
    if isinstance(v, list): return 9
    if isinstance(v, dict): return 10
    raise TypeError(type(v))


def _payload(v) -> bytes:
    if isinstance(v, Byte): return struct.pack(">b", v)
    if isinstance(v, Long): return struct.pack(">q", v)
    if isinstance(v, int): return struct.pack(">i", v)
    if isinstance(v, str): return _name(v)
    if isinstance(v, list):
        if not v: return struct.pack(">bi", 0, 0)
        tid = _tag_id(v[0])
        return struct.pack(">bi", tid, len(v)) + b"".join(_payload(x) for x in v)
    if isinstance(v, dict):
        out = b""
        for k, x in v.items():
            out += struct.pack(">b", _tag_id(x)) + _name(k) + _payload(x)
        return out + b"\x00"
    raise TypeError(type(v))


def nbt_bytes(root: dict) -> bytes:
    return gzip.compress(struct.pack(">b", 10) + _name("") + _payload(root), mtime=0)


# --- template builder -----------------------------------------------------------
class Template:
    def __init__(self):
        self.cells: dict[tuple[int, int, int], tuple[str, tuple, dict | None]] = {}

    def set(self, x, y, z, name, props=None, nbt=None):
        self.cells[(x, y, z)] = (name, tuple(sorted((props or {}).items())), nbt)

    def fill(self, x1, y1, z1, x2, y2, z2, name, props=None):
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                for z in range(z1, z2 + 1):
                    self.set(x, y, z, name, props)

    def to_nbt(self) -> dict:
        palette: list[tuple[str, tuple]] = []
        blocks = []
        for pos in sorted(self.cells, key=lambda p: (p[1], p[2], p[0])):
            name, props, nbt = self.cells[pos]
            key = (name, props)
            if key not in palette:
                palette.append(key)
            block = {"pos": list(pos), "state": palette.index(key)}
            if nbt:
                block["nbt"] = nbt
            blocks.append(block)
        pal = []
        for name, props in palette:
            entry = {"Name": name}
            if props:
                entry["Properties"] = {k: v for k, v in props}
            pal.append(entry)
        return {"DataVersion": DATA_VERSION, "size": list(SIZE), "palette": pal, "blocks": blocks, "entities": []}


def stack(slot, item, count, potion=None):
    entry = {"Slot": Byte(slot), "id": item, "Count": Byte(count)}
    if potion:
        entry["tag"] = {"Potion": potion}
    return entry


def dispenser(t, x, y, z, facing, items):
    t.set(x, y, z, "minecraft:dispenser", {"facing": facing, "triggered": "false"},
          {"id": "minecraft:dispenser", "Items": items})


def build() -> Template:
    t = Template()
    rng = random.Random(1923847)
    sx, sy, sz = SIZE

    def brick():
        r = rng.random()
        return "minecraft:stone_bricks" if r < 0.7 else "minecraft:cracked_stone_bricks" if r < 0.85 else "minecraft:mossy_stone_bricks"

    # Solid mass for the building, plus an under-floor block below the hall so the pit has walls.
    for x in range(sx):
        for y in range(FLOOR, sy):
            for z in range(sz):
                t.set(x, y, z, brick())
    for x in range(2, 17):
        for y in range(0, FLOOR):
            for z in range(3, 14):
                t.set(x, y, z, brick())

    air = "minecraft:air"
    t.fill(9, WALK, 13, 9, WALK + 2, 23, air)        # potion gallery corridor (3 high)
    t.fill(3, WALK, 4, 15, WALK + 3, 12, air)        # hall
    t.fill(3, 1, 7, 15, FLOOR, 9, air)               # spike pit across the hall

    # Spike pit: stalagmites on a checkerboard, pillars carrying the bridge dispensers.
    for x in range(3, 16):
        for z in range(7, 10):
            if (x + z) % 2 == 0 and not (x in (8, 10) and z == 8):
                t.set(x, 1, z, "minecraft:pointed_dripstone",
                      {"thickness": "tip", "vertical_direction": "up", "waterlogged": "false"})
    for x in (8, 10):
        t.fill(x, 1, 8, x, FLOOR, 8, "minecraft:stone_bricks")

    # One-block-wide bridge with a pressure plate in the middle.
    for z in range(7, 10):
        t.set(9, FLOOR, z, "minecraft:stone_brick_slab", {"type": "top", "waterlogged": "false"})
    t.set(9, WALK, 8, "minecraft:stone_pressure_plate", {"powered": "false"})
    # Dispensers face up into a solid block so the splash potion shatters the instant it spawns,
    # right beside the plate. (Arrows spawn 0.2 blocks into the next cell, so an arrow that starts
    # inside the target's hitbox never registers a hit; a potion thrown across an open cell sails
    # past the target to the far wall. Verified on a test server.)
    crossfire = lambda: [stack(0, "minecraft:splash_potion", 6, "minecraft:harming"),
                         stack(1, "minecraft:splash_potion", 6, "minecraft:slowness"),
                         stack(2, "minecraft:splash_potion", 6, "minecraft:weakness")]
    for x in (8, 10):
        t.set(x, WALK + 1, 8, "minecraft:chiseled_stone_bricks")  # lintel: the potion breaks against it
        dispenser(t, x, WALK, 8, "up", crossfire())

    # Potion gallery: plate in the corridor, dispensers in both walls beside it.
    for z in (21, 18, 15):
        t.set(9, WALK, z, "minecraft:stone_pressure_plate", {"powered": "false"})
        dispenser(t, 8, WALK, z, "up", [stack(0, "minecraft:splash_potion", 8, "minecraft:poison"),
                                        stack(1, "minecraft:splash_potion", 8, "minecraft:slowness")])
        dispenser(t, 10, WALK, z, "up", [stack(0, "minecraft:splash_potion", 8, "minecraft:poison"),
                                         stack(1, "minecraft:splash_potion", 8, "minecraft:weakness")])

    # Treasure ambush: trapped chest powers the three dispensers touching it.
    splash = lambda: [stack(0, "minecraft:splash_potion", 3, "minecraft:harming"),
                      stack(1, "minecraft:splash_potion", 3, "minecraft:poison"),
                      stack(2, "minecraft:splash_potion", 3, "minecraft:weakness")]
    t.set(9, WALK, 4, "minecraft:trapped_chest", {"facing": "south", "type": "single", "waterlogged": "false"},
          {"id": "minecraft:chest", "LootTable": "ddo:chests/trapvault_treasure"})
    dispenser(t, 8, WALK, 4, "east", splash())
    dispenser(t, 10, WALK, 4, "west", splash())
    dispenser(t, 9, WALK, 3, "south", splash())

    # Safer, lesser caches.
    for x, z in ((4, 5), (14, 5), (4, 11)):
        t.set(x, WALK, z, "minecraft:chest", {"facing": "south", "type": "single", "waterlogged": "false"},
              {"id": "minecraft:chest", "LootTable": "ddo:chests/trapvault_cache"})

    # Light.
    for x, y, z in ((9, WALK + 2, 22), (9, WALK + 2, 16), (4, WALK + 3, 5), (14, WALK + 3, 5),
                    (4, WALK + 3, 11), (14, WALK + 3, 11), (9, WALK + 3, 11)):
        t.set(x, y, z, "minecraft:soul_lantern", {"hanging": "true", "waterlogged": "false"})
    return t


# --- datapack JSON ----------------------------------------------------------------
def item(name, weight, count=None, functions=None):
    entry = {"type": "minecraft:item", "name": name, "weight": weight}
    funcs = list(functions or [])
    if count:
        funcs.insert(0, {"function": "minecraft:set_count", "count": {"min": count[0], "max": count[1]}})
    if funcs:
        entry["functions"] = funcs
    return entry


def enchant(lo, hi):
    return {"function": "minecraft:enchant_with_levels", "levels": {"min": lo, "max": hi}, "treasure": True}


def loot(pools):
    return {"type": "minecraft:chest", "pools": pools}


TREASURE = loot([
    {"rolls": {"min": 3, "max": 5}, "entries": [
        item("minecraft:diamond", 8, (1, 3)), item("minecraft:emerald", 14, (4, 12)),
        item("minecraft:gold_ingot", 16, (4, 10)), item("minecraft:ender_pearl", 8, (1, 3)),
        item("minecraft:experience_bottle", 12, (4, 10)), item("minecraft:golden_apple", 5, (1, 2)),
        item("minecraft:enchanted_golden_apple", 1), item("minecraft:iron_ingot", 18, (6, 14)),
    ]},
    {"rolls": {"min": 1, "max": 2}, "entries": [  # tiered modded gear (see tools/gen_gear_loot.py)
        {"type": "minecraft:loot_table", "name": "ddo:gear/nether", "weight": 3},
        {"type": "minecraft:loot_table", "name": "ddo:gear/end", "weight": 1},
    ]},
    {"rolls": 1, "entries": [
        item("minecraft:diamond_sword", 4, functions=[enchant(20, 35)]),
        item("minecraft:diamond_chestplate", 3, functions=[enchant(20, 35)]),
        item("minecraft:bow", 4, functions=[enchant(20, 35)]),
        item("minecraft:book", 6, functions=[enchant(25, 40)]),
    ]},
])
CACHE = loot([
    {"rolls": {"min": 2, "max": 4}, "entries": [
        item("minecraft:iron_ingot", 20, (2, 8)), item("minecraft:gold_ingot", 12, (2, 6)),
        item("minecraft:emerald", 8, (1, 4)), item("minecraft:arrow", 16, (8, 24)),
        item("minecraft:bread", 14, (2, 6)), item("minecraft:experience_bottle", 6, (1, 4)),
        item("minecraft:diamond", 2, (1, 1)),
    ]},
    {"rolls": 1, "entries": [
        {"type": "minecraft:loot_table", "name": "ddo:gear/overworld", "weight": 1},
        {"type": "minecraft:empty", "weight": 3},
    ]},
])
STRUCTURE = {
    "type": "minecraft:jigsaw", "biomes": "#ddo:has_trapvault", "step": "underground_structures",
    "terrain_adaptation": "none", "spawn_overrides": {}, "start_pool": "ddo:trapvault/start",
    "size": 1, "start_height": {"absolute": -40}, "max_distance_from_center": 80,
    "use_expansion_hack": False,
}
POOL = {"fallback": "minecraft:empty", "elements": [{"weight": 1, "element": {
    "element_type": "minecraft:single_pool_element", "location": "ddo:trapvault",
    "processors": "minecraft:empty", "projection": "rigid"}}]}
STRUCTURE_SET = {"structures": [{"structure": "ddo:trapvault", "weight": 1}],
                 "placement": {"type": "minecraft:random_spread", "spacing": 24, "separation": 10, "salt": 1923847}}
BIOME_TAG = {"replace": False, "values": ["#minecraft:is_overworld"]}


def write_json(rel: str, obj) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    nbt_path = DATA / "structures" / "trapvault.nbt"
    nbt_path.parent.mkdir(parents=True, exist_ok=True)
    nbt_path.write_bytes(nbt_bytes(build().to_nbt()))
    write_json("worldgen/structure/trapvault.json", STRUCTURE)
    write_json("worldgen/template_pool/trapvault/start.json", POOL)
    write_json("worldgen/structure_set/trapvault.json", STRUCTURE_SET)
    write_json("tags/worldgen/biome/has_trapvault.json", BIOME_TAG)
    write_json("loot_tables/chests/trapvault_treasure.json", TREASURE)
    write_json("loot_tables/chests/trapvault_cache.json", CACHE)
    print(f"wrote {nbt_path.relative_to(ROOT)} ({nbt_path.stat().st_size} bytes) and 6 JSON files")


if __name__ == "__main__":
    main()
