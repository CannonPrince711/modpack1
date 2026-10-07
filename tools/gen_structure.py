#!/usr/bin/env python3
"""
Generates the Saltglass structures as real Minecraft structure (.nbt) files.

These are written into the shipped datapack at
    pack/datapack/data/saltglass/structures/*.nbt
and placed in-world by datapack functions with /place structure.

Format reference: Minecraft 1.20.1 structure block file layout —
  root { DataVersion: int, size: [x,y,z], palette: [{Name, Properties}], blocks: [{pos,state,nbt}], entities: [] }
Built with nbtlib, so the output is genuine NBT, not a hand-rolled byte blob.

Run:  python3 tools/gen_structure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import nbtlib
from nbtlib import Compound, Int, String

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pack/overrides/config/paxi/datapacks/saltglass/data/saltglass/structures"
DATA_VERSION = 3465  # Minecraft 1.20.1

# ---------------------------------------------------------------- palette/blocks
BLOCKS = {
    "air": "minecraft:air",
    "bone": "minecraft:bone_block",
    "salt": "minecraft:calcite",
    "deep": "minecraft:deepslate_bricks",
    "deep_slab": "minecraft:deepslate_brick_slab",
    "deep_stairs": "minecraft:deepslate_brick_stairs",
    "glass": "minecraft:glass",
    "tinted": "minecraft:tinted_glass",
    "prismarine": "minecraft:prismarine_bricks",
    "dark_prism": "minecraft:dark_prismarine",
    "sea_lantern": "minecraft:sea_lantern",
    "lamp": "minecraft:lantern",
    "lantern": "minecraft:lantern",
    "calcite": "minecraft:calcite",
    "water": "minecraft:water",
    "tar": "minecraft:stripped_dark_oak_log",
    "plank": "minecraft:dark_oak_planks",
    "iron": "minecraft:iron_bars",
    "amethyst": "minecraft:amethyst_block",
    "budding": "minecraft:budding_amethyst",
    "glass_pane": "minecraft:glass_pane",
    "copper": "minecraft:oxidized_copper",
    "wax": "minecraft:oxidized_cut_copper",
}


class Builder:
    """Sparse block volume, then emitted as a structure palette + block list."""

    def __init__(self, sx: int, sy: int, sz: int):
        self.size = (sx, sy, sz)
        self.cells: dict[tuple[int, int, int], str] = {}

    def set(self, x, y, z, key):
        sx, sy, sz = self.size
        if 0 <= x < sx and 0 <= y < sy and 0 <= z < sz:
            self.cells[(x, y, z)] = key

    def box(self, x0, y0, z0, x1, y1, z1, key, hollow=False):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    if hollow and not (x in (x0, x1) or y in (y0, y1) or z in (z0, z1)):
                        continue
                    self.set(x, y, z, key)

    def pillar(self, x, z, y0, y1, key):
        for y in range(y0, y1 + 1):
            self.set(x, y, z, key)

    def to_nbt(self, entities=None):
        sx, sy, sz = self.size
        used = sorted({v for v in self.cells.values()})
        idx = {k: i for i, k in enumerate(used)}
        palette = nbtlib.List[nbtlib.Compound]([])
        for k in used:
            palette.append(Compound({"Name": String(BLOCKS[k])}))
        blocks = nbtlib.List[nbtlib.Compound]([])
        for (x, y, z), k in sorted(self.cells.items()):
            blocks.append(Compound({
                "pos": nbtlib.List[nbtlib.Int]([Int(x), Int(y), Int(z)]),
                "state": Int(idx[k]),
            }))
        return Compound({
            "DataVersion": Int(DATA_VERSION),
            "size": nbtlib.List[nbtlib.Int]([Int(sx), Int(sy), Int(sz)]),
            "palette": palette,
            "blocks": blocks,
            "entities": entities if entities is not None else nbtlib.List[nbtlib.Compound]([]),
        })


# ---------------------------------------------------------------- the cathedral
def drowned_cathedral() -> Builder:
    """111 x 46 x 61. A nine-bay nave in calcite and deepslate, flooded to the chest,
    lit by sea lanterns, with the three doors of the Kettle Sea at the west end.

    Deliberately *not* ruined: the premise is that it is finished and open, not that it fell.
    """
    W, H, D = 111, 46, 61
    b = Builder(W, H, D)
    cx, cz = 55, 30
    nave_h = 20

    # --- platform / drowned foundation (pylons instead of solid stone: it reads better
    # from underneath, which matters because the sea floor is a glass ceiling)
    for x in range(0, W, 6):
        for z in (2, D - 3, 12, D - 13):
            b.set(x, 0, z, "deep")
            b.set(x, 1, z, "deep")

    # --- floor
    b.box(4, 2, 10, W - 5, 2, D - 11, "prismarine")
    b.box(4, 3, 10, W - 5, 3, D - 11, "deep_slab")
    # drowned gospel: a shallow sheet of water on the floor, 2 blocks
    b.box(6, 4, 12, W - 7, 5, D - 13, "water")
    b.box(4, 3, 10, W - 5, 3, D - 11, "deep_slab")

    # --- outer walls, aisle height
    for x in range(4, W - 4):
        b.pillar(x, 10, 4, nave_h, "deep")
        b.pillar(x, D - 11, 4, nave_h, "deep")
    for z in range(10, D - 10):
        b.pillar(4, z, 4, nave_h, "deep")
        b.pillar(W - 5, z, 4, nave_h, "deep")

    # --- clerestory windows (the only light in the nave that is not a lantern)
    for x in range(10, W - 10, 8):
        for y in range(10, 17, 3):
            b.set(x, y, 10, "glass")
            b.set(x + 1, y, 10, "glass")
            b.set(x, y, D - 11, "glass")
            b.set(x + 1, y, D - 11, "glass")
    for z in range(16, D - 16, 8):
        for y in range(10, 17, 3):
            b.set(4, y, z, "glass")
            b.set(4, y, z + 1, "glass")
            b.set(W - 5, y, z, "glass")
            b.set(W - 5, y, z + 1, "glass")

    # --- the nine bays: columns + arches, with a lantern hanging in each
    for i in range(9):
        x = 8 + i * 12
        b.box(x - 2, 3, 14, x - 2, nave_h + 3, 15, "deep")
        b.box(x + 2, 3, 14, x + 2, nave_h + 3, 15, "deep")
        b.box(x - 2, 3, D - 16, x - 2, nave_h + 3, D - 15, "deep")
        b.box(x + 2, 3, D - 16, x + 2, nave_h + 3, D - 15, "deep")
        # capital
        b.box(x - 3, nave_h + 4, 13, x - 1, nave_h + 4, 16, "prismarine")
        b.box(x + 1, nave_h + 4, 13, x + 3, nave_h + 4, 16, "prismarine")
        b.box(x - 3, nave_h + 4, D - 17, x - 1, nave_h + 4, D - 14, "prismarine")
        b.box(x + 1, nave_h + 4, D - 17, x + 3, nave_h + 4, D - 14, "prismarine")
        # arch across the nave
        for t in range(0, 22):
            dx = x - 2 + t * 0
            b.set(x, nave_h + 6, 14, "deep_stairs")
        b.box(x - 1, nave_h + 6, 14, x + 1, nave_h + 6, 15, "deep")
        b.box(x - 1, nave_h + 6, D - 16, x + 1, nave_h + 6, D - 15, "deep")
        # hanging lanterns (sea lantern + lantern: lamp of the salvage-priests)
        for z in (22, D - 23):
            b.set(x, nave_h + 2, z, "lantern")
            b.set(x, nave_h + 3, z, "iron")

    # --- roof: a stepped barrel vault, calcite above, so it glows under the glass ceiling
    for step in range(0, 9):
        y = nave_h + 7 + step
        z0, z1 = 10 + step, D - 11 - step
        if z0 > z1:
            break
        for x in range(4, W - 4):
            b.set(x, y, z0, "salt")
            b.set(x, y, z1, "salt")
            if step > 0:
                b.set(x, y - 1, z0 + 1, "salt")
                b.set(x, y - 1, z1 - 1, "salt")
    # ridge beam
    b.box(4, nave_h + 15, cz, W - 5, nave_h + 15, cz, "tar")

    # --- apse (east): altar, nine doors, amethyst heart
    b.box(W - 12, 4, cz - 8, W - 11, nave_h + 6, cz + 8, "deep")
    for i in range(9):
        z = cz - 8 + i * 2
        b.box(W - 13, 5, z, W - 13, 7, z, "tinted")
        b.box(W - 14, 5, z, W - 14, 7, z, "glass_pane")
    # altar
    b.box(W - 22, 4, cz - 3, W - 18, 4, cz + 3, "prismarine")
    b.box(W - 22, 5, cz - 2, W - 18, 5, cz + 2, "dark_prism")
    b.box(W - 21, 6, cz - 1, W - 19, 6, cz + 1, "amethyst")
    b.set(W - 20, 7, cz, "budding")
    # the nine candles at the altar still burn: nine sea lanterns, still lit
    for i in range(9):
        z = cz - 4 + i
        b.set(W - 22, 5, z, "sea_lantern")

    # --- the three doors of the Kettle Sea (west end): where the player enters
    for dz in (cz - 9, cz, cz + 9):
        # shut until the three beacons are lit: saltglass:cathedral/open breaks them
        b.box(3, 4, dz - 2, 5, 9, dz + 2, "tinted")
        b.box(3, 10, dz - 3, 5, 10, dz + 3, "salt")
        b.box(2, 11, dz - 3, 4, 11, dz + 3, "bone")

    # --- porch
    b.box(0, 2, cz - 12, 4, 3, cz + 12, "prismarine")
    for z in (cz - 12, cz + 12):
        b.pillar(1, z, 4, 16, "deep")
        b.pillar(3, z, 4, 16, "deep")
    b.box(0, 17, cz - 13, 4, 17, cz + 13, "salt")
    b.box(0, 18, cz - 12, 3, 18, cz + 12, "bone")

    # --- the three spires (seen from above through the glass ceiling)
    for (sx, sz, h, r) in ((22, cz, 30, 5), (55, cz, 36, 6), (88, cz, 24, 4)):
        for y in range(nave_h + 8, nave_h + 8 + h):
            shrink = max(1, r - (y - nave_h - 8) // 4)
            b.box(sx - shrink, y, sz - shrink, sx + shrink, y, sz + shrink, "salt", hollow=True)
            if y % 4 == 0:
                b.box(sx - shrink, y, sz - shrink, sx + shrink, y, sz + shrink, "calcite"
                      if False else "prismarine", hollow=False)
        b.set(sx, nave_h + 8 + h + 1, sz, "sea_lantern")
        b.set(sx, nave_h + 8 + h, sz, "copper")

    # --- drowned fleet at the anchorage: three hulls, hull-up, inside the nave
    for (hx, hz, ln) in ((30, 20, 11), (42, 41, 9), (66, 18, 8)):
        for i in range(ln):
            x = hx + i
            w = 3 if i in (0, ln - 1) else 4
            b.box(x, 6, hz - w, x, 6, hz + w, "tar")
            b.box(x, 7, hz - w + 1, x, 7, hz + w - 1, "plank")
        b.set(hx + ln // 2, 8, hz, "tar")
        b.set(hx, 8, hz - 1, "iron")

    # --- salt crust over the outer floor: nothing here is clean
    for x in range(0, W, 3):
        for z in range(0, D, 3):
            if b.cells.get((x, 3, z)) is None and b.cells.get((x, 2, z)) is None:
                b.set(x, 2, z, "salt")

    return b


# ---------------------------------------------------------------- the harbour beacon
def beacon_tower() -> Builder:
    """33 x 40 x 33: a salvage-priest beacon — salt-glazed tower, amber fire on top,
    machinery bays at the base for the Create pump. Placed by each harbour quest."""
    W, H, D = 33, 40, 33
    b = Builder(W, H, D)
    cx, cz = 16, 16
    # base
    b.box(cx - 6, 0, cz - 6, cx + 6, 2, cz + 6, "prismarine")
    b.box(cx - 5, 3, cz - 5, cx + 5, 3, cz + 5, "deep_stairs")
    b.box(cx - 4, 4, cz - 4, cx + 4, 4, cz + 4, "prismarine")
    # tower
    for y in range(5, 33):
        r = 4 if y < 16 else (3 if y < 26 else 2)
        b.box(cx - r, y, cz - r, cx + r, y, cz + r, "deep", hollow=True)
        if y % 7 == 0:
            b.box(cx - r, y, cz - r, cx + r, y, cz + r, "bone")
    # door
    b.box(cx, 5, cz - 4, cx, 7, cz - 4, "air")
    b.box(cx - 1, 5, cz - 4, cx + 1, 8, cz - 4, "air")
    # gallery + lantern room
    b.box(cx - 3, 33, cz - 3, cx + 3, 33, cz + 3, "tar")
    b.box(cx - 2, 34, cz - 2, cx + 2, 37, cz + 2, "glass_pane")
    b.box(cx - 1, 34, cz - 1, cx + 1, 36, cz + 1, "sea_lantern")
    b.box(cx - 3, 38, cz - 3, cx + 3, 38, cz + 3, "copper")
    b.box(cx - 1, 39, cz - 1, cx + 1, 39, cz + 1, "wax")
    return b


# ---------------------------------------------------------------- the last trench
def tide_trench() -> Builder:
    """25 x 12 x 25: the dry trench where the Tide Heart is set. Salt-rimmed, glass-lined,
    with the four anchor points the Act III quest needs."""
    W, H, D = 25, 12, 25
    b = Builder(W, H, D)
    cx, cz = 12, 12
    b.box(0, 0, 0, W - 1, 0, D - 1, "prismarine")
    b.box(1, 1, 1, W - 2, 3, D - 2, "deep", hollow=True)
    for x in range(1, W - 1):
        for z in range(1, D - 1):
            d = max(abs(x - cx), abs(z - cz))
            if d < 7:
                b.set(x, 1, z, "air")
                b.set(x, 2, z, "air")
                b.set(x, 3, z, "air")
                b.set(x, 4, z, "air")
    b.box(3, 5, 3, W - 4, 5, D - 4, "deep_slab")
    for (ax, az) in ((cx - 6, cz - 6), (cx + 6, cz - 6), (cx - 6, cz + 6), (cx + 6, cz + 6)):
        b.box(ax, 5, az, ax, 8, az, "copper")
        b.set(ax, 9, az, "sea_lantern")
    b.set(cx, 1, cz, "amethyst")
    b.set(cx, 2, cz, "budding")
    for dx in (-2, 2):
        for dz in (-2, 2):
            b.set(cx + dx, 1, cz + dz, "glass")
    return b


def save(b: Builder, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    f = nbtlib.File(b.to_nbt(), gzipped=True)
    path = OUT / f"{name}.nbt"
    f.save(path, gzipped=True)
    print(f"  wrote {path.relative_to(ROOT)}  ({len(b.cells)} blocks, "
          f"{b.size[0]}x{b.size[1]}x{b.size[2]})")
    return path


def main():
    print("generating structures:")
    save(drowned_cathedral(), "drowned_cathedral")
    save(beacon_tower(), "beacon_tower")
    save(tide_trench(), "tide_trench")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
