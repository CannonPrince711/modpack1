#!/usr/bin/env python3
"""Generate the starting town and castle (ddo:castle/tile_*) and the layout the intro cutscene follows.

Writes
  overrides/kubejs/data/ddo/structures/castle/tile_<i>_<j>.nbt   the build, cut into 32x32 tiles
  overrides/kubejs/server_scripts/castle_layout.js               tile offsets and cutscene waypoints (global.CASTLE)

Coordinates: x east, z south, y up. The origin (0, 0, 0) is the castle courtyard centre at ground level (y = 0 is the
first air layer; y = -1 is the ground). The castle sits to the north (z < 0) with its gate in the south wall, a moat
around it, and the town street running south from the drawbridge. The generator walks a pathfinder from the town's far
end to the throne (the moat can only be crossed by the bridge), so a build that cannot be walked end to end fails here,
not in the game.
"""

from __future__ import annotations

import collections
import importlib.util
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRUCT_DIR = ROOT / "overrides" / "kubejs" / "data" / "ddo" / "structures" / "castle"
LAYOUT_JS = ROOT / "overrides" / "kubejs" / "server_scripts" / "castle_layout.js"
TILE = 32


def load_vault():
    spec = importlib.util.spec_from_file_location("gen_trapvault", ROOT / "tools" / "gen_trapvault.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = load_vault()
RNG = random.Random(20261007)

PASSABLE = {"minecraft:air", "minecraft:red_carpet", "minecraft:wall_torch", "minecraft:lantern", "minecraft:oak_door",
            "minecraft:dirt_path", "minecraft:water", "minecraft:wheat", "minecraft:carrots", "minecraft:potatoes",
            "minecraft:potted_poppy", "minecraft:red_wall_banner", "minecraft:oak_trapdoor", "minecraft:bell",
            "minecraft:ladder", "minecraft:oak_pressure_plate", "minecraft:candle"}
AIR = "minecraft:air"
BRICK, MOSS, CRACK = "minecraft:stone_bricks", "minecraft:mossy_stone_bricks", "minecraft:cracked_stone_bricks"
COBBLE, MOSSY_COBBLE = "minecraft:cobblestone", "minecraft:mossy_cobblestone"
BASE = "minecraft:polished_deepslate"
PLANKS, LOG = "minecraft:dark_oak_planks", "minecraft:dark_oak_log"
ROOF_STAIR, ROOF_SLAB, ROOF_BLOCK = "minecraft:dark_oak_stairs", "minecraft:dark_oak_slab", "minecraft:dark_oak_planks"
PLASTER = "minecraft:white_terracotta"
NOCONN = {"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"}
WALLPROPS = {"up": "true", "north": "none", "south": "none", "east": "none", "west": "none", "waterlogged": "false"}


class World:
    """Sparse block grid with architectural helpers; later writes win."""

    def __init__(self):
        self.t = V.Template()

    def set(self, x, y, z, name, props=None, nbt=None):
        self.t.set(x, y, z, name, props, nbt)

    def get(self, x, y, z):
        c = self.t.cells.get((x, y, z))
        return c[0] if c else None

    def fill(self, x1, y1, z1, x2, y2, z2, name, props=None):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set(x, y, z, name, props)

    def clear(self, x1, y1, z1, x2, y2, z2):
        self.fill(x1, y1, z1, x2, y2, z2, AIR)

    def box(self, x1, y1, z1, x2, y2, z2, name, thick=1):
        self.fill(x1, y1, z1, x2, y2, z2, name)
        self.clear(x1 + thick, y1, z1 + thick, x2 - thick, y2, z2 - thick)

    def disc(self, cx, cz, r, y1, y2, name):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dz * dz <= r * r + r // 2:
                    for y in range(y1, y2 + 1):
                        self.set(cx + dx, y, cz + dz, name)

    def ring(self, cx, cz, r, thick, y1, y2, name):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                d = dx * dx + dz * dz
                if d <= r * r + r // 2 and d > (r - thick) * (r - thick):
                    for y in range(y1, y2 + 1):
                        self.set(cx + dx, y, cz + dz, name)

    def stairs(self, x, y, z, name, facing, half="bottom"):
        self.set(x, y, z, name, {"facing": facing, "half": half, "shape": "straight", "waterlogged": "false"})

    def lantern(self, x, y, z, hanging=False):
        self.set(x, y, z, "minecraft:lantern", {"hanging": "true" if hanging else "false", "waterlogged": "false"})

    def pane(self, x, y, z):
        self.set(x, y, z, "minecraft:glass_pane", dict(NOCONN))

    def wallpost(self, x, y, z, name="minecraft:cobblestone_wall"):
        self.set(x, y, z, name, dict(WALLPROPS))

    def door(self, x, y, z, facing):
        for half in ("lower", "upper"):
            self.set(x, y + (half == "upper"), z, "minecraft:oak_door",
                     {"facing": facing, "half": half, "hinge": "left", "open": "false", "powered": "false"})

    def shutter(self, x, y, z, facing):
        self.set(x, y, z, "minecraft:oak_trapdoor", {"facing": facing, "half": "bottom", "open": "true", "powered": "false", "waterlogged": "false"})

    def banner(self, x, y, z, facing, colour="red"):
        self.set(x, y, z, f"minecraft:{colour}_wall_banner", {"facing": facing})

    def waystone(self, x, y, z, facing, block="waystones:waystone"):
        for half, dy in (("lower", 0), ("upper", 1)):
            self.set(x, y + dy, z, block, {"facing": facing, "half": half})

    def chest(self, x, y, z, facing):
        self.set(x, y, z, "minecraft:chest", {"facing": facing, "type": "single", "waterlogged": "false"},
                 {"id": "minecraft:chest", "LootTable": "ddo:chests/trapvault_cache"})

    def pyramid(self, cx, cz, half, y0, name):
        for i in range(half + 1):
            self.fill(cx - half + i, y0 + i, cz - half + i, cx + half - i, y0 + i, cz + half - i, name)

    def cone(self, cx, cz, r, y0, name):
        """Round conical roof of shrinking discs, topped with a lightning rod."""
        y, radius = y0, r + 1
        while radius >= 0:
            self.disc(cx, cz, radius, y, y, name)
            radius -= 1
            y += 1
        self.set(cx, y, cz, "minecraft:lightning_rod", {"facing": "up", "powered": "false", "waterlogged": "false"})


def weathered():
    r = RNG.random()
    return BRICK if r < 0.72 else MOSS if r < 0.9 else CRACK


def course(y):
    """Wall material by height: dark base course, cobble plinth, weathered bricks above."""
    if y <= 1:
        return BASE if RNG.random() < 0.6 else "minecraft:deepslate_bricks"
    if y <= 3:
        return COBBLE if RNG.random() < 0.7 else MOSSY_COBBLE
    return weathered()


def wall_block(w, x1, y1, z1, x2, y2, z2):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                w.set(x, y, z, course(y))


# --- castle -------------------------------------------------------------------------------------------------------------
def moat(w):
    """Water trench around the curtain wall, crossed only by the drawbridge."""
    for x in range(-50, 51):
        for z in range(-50, 51):
            outside = max(abs(x), abs(z))
            if 43 <= outside <= 49:
                w.set(x, -3, z, BRICK)
                w.set(x, -2, z, "minecraft:water")
                w.set(x, -1, z, "minecraft:water")
            elif outside in (42, 50):
                w.set(x, -1, z, COBBLE)
    w.fill(-2, -1, 42, 2, -1, 50, PLANKS)                          # drawbridge
    for x in (-3, 3):
        for z in (43, 49):
            w.fill(x, 0, z, x, 3, z, LOG, {"axis": "y"})
        w.fill(x, 4, 43, x, 4, 49, "minecraft:dark_oak_fence")
    for z in (44, 48):
        w.lantern(-3, 5, z)
        w.lantern(3, 5, z)


def curtain_wall(w):
    h = 14
    wall_block(w, -41, 0, -41, 41, h, -39)   # north
    wall_block(w, -41, 0, 39, 41, h, 41)     # south
    wall_block(w, -41, 0, -41, -39, h, 41)   # west
    wall_block(w, 39, 0, -41, 41, h, 41)     # east
    # parapet: merlons on the outer edge, a low wall on the inner edge, a one-block walkway between
    for i in range(-41, 42):
        for zo, zi in ((-41, -39), (41, 39)):
            w.set(i, h + 1, zo, BRICK if i % 3 else AIR)
            w.wallpost(i, h + 1, zi, "minecraft:stone_brick_wall")
        for xo, xi in ((-41, -39), (41, 39)):
            w.set(xo, h + 1, i, BRICK if i % 3 else AIR)
            if not 21 <= i <= 25:                   # keep the head of each stair open
                w.wallpost(xi, h + 1, i, "minecraft:stone_brick_wall")
    for i in range(-36, 37, 12):                    # lanterns along the walk
        for x, z in ((i, -39), (i, 39), (-39, i), (39, i)):
            if z == 39 and abs(i) < 5:
                continue
            w.lantern(x, h + 2, z)
    for i in range(-30, 31, 7):                     # arrow slits
        for x, z in ((i, -41), (i, 41), (-41, i), (41, i)):
            if z == 41 and abs(i) < 8:
                continue
            w.set(x, 9, z, AIR)
            w.set(x, 10, z, AIR)
    # gatehouse: tall flanking piers, arch, portcullis teeth, banners
    w.clear(-4, 0, 38, 4, 9, 42)
    for x in (-5, 5):
        wall_block(w, x, 0, 38, x, 18, 42)
    for x in range(-5, 6):
        w.fill(x, 10, 38, x, 12, 42, BRICK)
    for x in range(-3, 4):
        w.set(x, 9, 40, BRICK)
    for x in range(-3, 4, 2):
        w.fill(x, 7, 40, x, 8, 40, "minecraft:iron_bars", dict(NOCONN))
    for z in (38, 42):
        w.lantern(-5, 9, z)
        w.lantern(5, 9, z)
    for x in (-6, 6):
        w.banner(x, 6, 42, "south")


def curtain_stairs(w):
    """Two stairways from the courtyard up to the wall walk, either side of the gate."""
    for side in (-1, 1):
        for i in range(15):                          # 15 steps: the last is level with the wall top
            z = 37 - i
            for col in (37, 38):
                x = side * col
                w.stairs(x, i, z, "minecraft:stone_brick_stairs", "north")
                if i > 0:
                    w.fill(x, 0, z, x, i - 1, z, BRICK)
        w.fill(side * 36, 0, 23, side * 36, 14, 37, BRICK)   # outer cheek wall of the stair


def tower(w, cx, cz, r, height, doors=True):
    w.disc(cx, cz, r, -3, -1, BRICK)                 # foundation, also over the moat
    w.disc(cx, cz, r, 0, height, BRICK)
    w.disc(cx, cz, r - 2, 0, height, AIR)
    for y in range(0, height + 1):                   # weather the shell
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if w.get(cx + dx, y, cz + dz) == BRICK:
                    w.set(cx + dx, y, cz + dz, course(y))
    for y in range(8, height, 8):
        w.disc(cx, cz, r - 2, y, y, PLANKS)
        w.set(cx, y, cz, AIR)
    for dx in range(-r, r + 1):                      # crenellated rim
        for dz in range(-r, r + 1):
            d = dx * dx + dz * dz
            if d <= r * r + r // 2 and d > (r - 1) * (r - 1) and (dx + dz) % 2 == 0:
                w.set(cx + dx, height + 1, cz + dz, BRICK)
    w.cone(cx, cz, r, height + 1, ROOF_BLOCK)
    for y in range(4, height, 8):                    # arrow slits
        for ang in range(0, 360, 90):
            ax = cx + int(round(math.cos(math.radians(ang)) * r))
            az = cz + int(round(math.sin(math.radians(ang)) * r))
            w.set(ax, y, az, AIR)
            w.set(ax, y + 1, az, AIR)
    if doors:                                        # archways toward the courtyard
        sx = -1 if cx > 0 else 1
        sz = -1 if cz > 0 else 1
        w.clear(cx + sx * (r - 2), 0, cz, cx + sx * r, 3, cz)
        w.clear(cx, 0, cz + sz * (r - 2), cx, 3, cz + sz * r)


def keep(w):
    x1, x2, z1, z2, h = -16, 16, -33, -3, 40
    wall_block(w, x1, 0, z1, x2, h, z2)
    w.clear(x1 + 3, 0, z1 + 3, x2 - 3, h - 1, z2 - 3)             # hollow great hall, full height
    # entrance porch with columns, and an approach of stone steps
    w.clear(-3, 0, z2 - 3, 3, 9, z2)
    for x in range(-4, 5):
        w.set(x, 10, z2, BRICK)
    for x in (-5, 5):
        w.fill(x, 0, z2 + 1, x, 9, z2 + 1, "minecraft:quartz_pillar", {"axis": "y"})
    w.fill(-5, 10, z2 + 1, 5, 10, z2 + 1, BRICK)
    # windows cut right through the three-block walls: two rows on every face
    for y in (6, 22):
        for x in range(-12, 13, 4):
            if abs(x) < 5 and y < 12:
                continue
            for dy in range(4):
                for dz in range(3):
                    w.pane(x, y + dy, z2 - dz)
        for z in range(z1 + 6, z2 - 3, 5):
            for dy in range(4):
                for d in range(3):
                    w.pane(x1 + d, y + dy, z)
                    w.pane(x2 - d, y + dy, z)
    # floors: gallery ring at 16, top floor at 30
    for y in (16, 30):
        w.fill(x1 + 3, y, z1 + 3, x2 - 3, y, z2 - 3, PLANKS)
        w.clear(x1 + 8, y, z1 + 8, x2 - 8, y, z2 - 8)
    for i in range(16):                              # grand stair along the west wall up to the gallery
        for col in (x1 + 3, x1 + 4):
            w.stairs(col, i, z2 - 5 - i, "minecraft:stone_brick_stairs", "north")
            if i > 0:
                w.fill(col, 0, z2 - 5 - i, col, i - 1, z2 - 5 - i, BRICK)
    w.clear(x1 + 3, 16, z2 - 5 - 16, x1 + 5, 17, z2 - 5 - 14)
    for sx in (-1, 1):                               # round corner towers
        for sz in (-1, 1):
            tower(w, sx * 16, z1 if sz < 0 else z2, 5, 50, doors=False)
    for x in range(x1, x2 + 1):
        for z in (z1, z2):
            if (x + z) % 2 == 0:
                w.set(x, h + 1, z, BRICK)
    for z in range(z1, z2 + 1):
        for x in (x1, x2):
            if (x + z) % 2 == 0:
                w.set(x, h + 1, z, BRICK)
    w.pyramid(0, (z1 + z2) // 2, 14, h + 1, ROOF_BLOCK)
    # throne room: red carpet runway, two-step dais, gold throne with banners behind
    for z in range(z2 - 4, z1 + 6, -1):
        w.fill(-2, 0, z, 2, 0, z, "minecraft:red_carpet")
    w.fill(-7, 0, z1 + 3, 7, 0, z1 + 8, "minecraft:polished_andesite")
    w.fill(-5, 1, z1 + 3, 5, 1, z1 + 6, "minecraft:polished_andesite")
    w.fill(-2, 0, z1 + 8, 2, 0, z1 + 8, "minecraft:red_carpet")
    w.fill(-2, 1, z1 + 6, 2, 1, z1 + 6, "minecraft:red_carpet")
    w.stairs(0, 2, z1 + 4, "minecraft:quartz_stairs", "south")
    w.fill(0, 2, z1 + 3, 0, 5, z1 + 3, "minecraft:gold_block")
    for sx in (-1, 1):
        w.fill(sx, 2, z1 + 3, sx, 4, z1 + 3, "minecraft:red_wool")
        w.fill(sx * 5, 2, z1 + 4, sx * 5, 6, z1 + 4, "minecraft:quartz_pillar", {"axis": "y"})
    for z in range(z2 - 6, z1 + 7, -6):              # columns and banners down the hall
        for sx in (-1, 1):
            w.fill(sx * 8, 0, z, sx * 8, 15, z, "minecraft:quartz_pillar", {"axis": "y"})
            w.banner(sx * 12, 8, z, "east" if sx < 0 else "west")
            w.banner(sx * 12, 9, z, "east" if sx < 0 else "west")
    for dx in (-3, 3):
        w.banner(dx, 8, z1 + 3, "south")
        w.banner(dx, 9, z1 + 3, "south")
    for z in range(z2 - 6, z1 + 6, -5):              # chandeliers
        w.fill(0, 15, z, 0, 15, z, "minecraft:chain", {"axis": "y", "waterlogged": "false"})
        w.lantern(0, 14, z, hanging=True)
    for z in (z1 + 5, z2 - 8):
        for x in (-8, 8):
            w.set(x, 0, z, "minecraft:campfire", {"facing": "north", "lit": "true", "signal_fire": "false", "waterlogged": "false"})


def courtyard(w):
    w.fill(-38, -1, -38, 38, -1, 38, BRICK)
    for x in range(-38, 39):
        for z in range(-38, 39):
            r = (x * 7 + z * 13) % 11
            if r == 0 and abs(x) > 3:
                w.set(x, -1, z, "minecraft:grass_block")
            elif r in (3, 4):
                w.set(x, -1, z, MOSS if RNG.random() < 0.5 else COBBLE)
    w.fill(-3, -1, -3, 3, -1, 41, "minecraft:polished_andesite")
    barracks(w, 20, 12)
    stable(w, -22, 14)
    smithy(w, 22, 28)
    well(w, -12, 26)
    for x in (-12, 12):
        for z in (6, 18):
            w.wallpost(x, 0, z)
            w.wallpost(x, 1, z)
            w.wallpost(x, 2, z)
            w.lantern(x, 3, z)
    for z in (-8, 4):                                # training dummies: hay on a post
        for x in (-26, 26):
            w.fill(x, 0, z, x, 1, z, "minecraft:dark_oak_fence")
            w.set(x, 2, z, "minecraft:hay_block", {"axis": "y"})


def gable(w, x1, x2, z1, z2, y0, axis="x", end=PLASTER, overhang=1):
    """Gabled roof of stair blocks with the ridge along `axis`; gable ends filled in."""
    if axis == "x":
        half = (z2 - z1) // 2 + 1
        for i in range(half + 1):
            zn, zs = z1 - overhang + i, z2 + overhang - i
            for x in range(x1 - overhang, x2 + overhang + 1):
                if zn < zs:
                    w.stairs(x, y0 + i, zn, ROOF_STAIR, "south")
                    w.stairs(x, y0 + i, zs, ROOF_STAIR, "north")
                elif zn == zs:
                    w.set(x, y0 + i, zn, ROOF_BLOCK)
        for x in (x1, x2):
            for i in range(half):
                if z1 + i <= z2 - i:
                    w.fill(x, y0 + i, z1 + i, x, y0 + i, z2 - i, end)
    else:
        half = (x2 - x1) // 2 + 1
        for i in range(half + 1):
            xw, xe = x1 - overhang + i, x2 + overhang - i
            for z in range(z1 - overhang, z2 + overhang + 1):
                if xw < xe:
                    w.stairs(xw, y0 + i, z, ROOF_STAIR, "east")
                    w.stairs(xe, y0 + i, z, ROOF_STAIR, "west")
                elif xw == xe:
                    w.set(xw, y0 + i, z, ROOF_BLOCK)
        for z in (z1, z2):
            for i in range(half):
                if x1 + i <= x2 - i:
                    w.fill(x1 + i, y0 + i, z, x2 - i, y0 + i, z, end)


def barracks(w, cx, cz):
    x1, x2, z1, z2 = cx - 9, cx + 9, cz - 6, cz + 6
    w.fill(x1, -1, z1, x2, -1, z2, COBBLE)
    w.box(x1, 0, z1, x2, 6, z2, COBBLE, thick=1)
    wall_block(w, x1, 0, z1, x2, 6, z1)
    wall_block(w, x1, 0, z2, x2, 6, z2)
    for x in range(x1 + 2, x2, 4):
        for dy in (3, 4):
            w.pane(x, dy, z2)
    w.clear(x1, 0, cz - 1, x1, 2, cz + 1)
    gable(w, x1, x2, z1, z2, 7, "x", end=COBBLE)
    for i in range(5):
        w.set(x1 + 2 + i * 3, 0, z1 + 1, "minecraft:red_bed", {"facing": "south", "part": "foot", "occupied": "false"})
        w.set(x1 + 2 + i * 3, 0, z1 + 2, "minecraft:red_bed", {"facing": "south", "part": "head", "occupied": "false"})
    w.lantern(cx, 6, cz, hanging=True)


def stable(w, cx, cz):
    x1, x2, z1, z2 = cx - 8, cx + 8, cz - 5, cz + 5
    w.fill(x1, -1, z1, x2, -1, z2, "minecraft:coarse_dirt")
    for x in range(x1, x2 + 1, 4):
        w.fill(x, 0, z1, x, 3, z1, LOG, {"axis": "y"})
        w.fill(x, 0, z2, x, 3, z2, LOG, {"axis": "y"})
    for x in range(x1, x2 + 1):
        w.set(x, 1, z2, "minecraft:dark_oak_fence")
    for x in range(x1 + 2, x2, 4):
        w.fill(x, 0, z1 + 1, x, 1, z1 + 1, "minecraft:hay_block", {"axis": "y"})
    gable(w, x1, x2, z1, z2, 4, "x", end="minecraft:oak_planks")


def smithy(w, cx, cz):
    x1, x2, z1, z2 = cx - 5, cx + 5, cz - 4, cz + 4
    w.fill(x1, -1, z1, x2, -1, z2, COBBLE)
    for x, z in ((x1, z1), (x1, z2), (x2, z1), (x2, z2)):
        w.fill(x, 0, z, x, 4, z, LOG, {"axis": "y"})
    w.fill(x1, 0, z1, x2, 2, z1, COBBLE)
    w.set(cx - 2, 0, z1 + 1, "minecraft:blast_furnace", {"facing": "south", "lit": "false"})
    w.set(cx, 0, z1 + 1, "minecraft:anvil", {"facing": "east"})
    w.set(cx + 2, 0, z1 + 1, "minecraft:grindstone", {"face": "floor", "facing": "south"})
    w.set(cx + 4, 0, z1 + 1, "minecraft:cauldron")
    w.fill(cx - 1, 0, z1 + 3, cx + 1, 0, z1 + 3, "minecraft:smooth_stone")
    gable(w, x1, x2, z1, z2, 5, "x", end="minecraft:oak_planks")
    w.lantern(cx, 4, cz, hanging=True)


def well(w, x, z):
    w.fill(x - 1, 0, z - 1, x + 1, 1, z + 1, COBBLE)
    w.clear(x, 0, z, x, 1, z)
    w.set(x, -1, z, "minecraft:water")
    for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        w.fill(x + dx, 2, z + dz, x + dx, 3, z + dz, "minecraft:dark_oak_fence")
    w.fill(x - 1, 4, z - 1, x + 1, 4, z + 1, ROOF_SLAB, {"type": "bottom", "waterlogged": "false"})


# --- town ----------------------------------------------------------------------------------------------------------------
def house(w, cx, cz, facing, style):
    """Timber-framed house: stone footing, plaster panels between dark beams, stair roof, shutters, chimney, furnishings."""
    two_floors = style % 3 == 1
    wide, deep = (9, 8) if not two_floors else (7, 9)
    x1, x2, z1, z2 = cx - wide // 2, cx + wide // 2, cz - deep // 2, cz + deep // 2
    wall_h = 4 if not two_floors else 8
    w.fill(x1 - 1, -1, z1 - 1, x2 + 1, -1, z2 + 1, COBBLE)
    w.box(x1, 0, z1, x2, wall_h, z2, PLASTER, thick=1)
    for x in range(x1, x2 + 1):                      # footing course
        for z in (z1, z2):
            w.set(x, 0, z, COBBLE if (x + z) % 3 else MOSSY_COBBLE)
    for z in range(z1, z2 + 1):
        for x in (x1, x2):
            w.set(x, 0, z, COBBLE if (x + z) % 3 else MOSSY_COBBLE)
    for x, z in ((x1, z1), (x1, z2), (x2, z1), (x2, z2)):
        w.fill(x, 0, z, x, wall_h, z, LOG, {"axis": "y"})
    for y in ([3] if not two_floors else [3, 7]) + [wall_h]:      # storey beams
        for x in range(x1, x2 + 1):
            w.set(x, y, z1, LOG, {"axis": "x"})
            w.set(x, y, z2, LOG, {"axis": "x"})
        for z in range(z1, z2 + 1):
            w.set(x1, y, z, LOG, {"axis": "z"})
            w.set(x2, y, z, LOG, {"axis": "z"})
    if two_floors:
        w.fill(x1 + 1, 4, z1 + 1, x2 - 1, 4, z2 - 1, "minecraft:spruce_planks")
        w.clear(x1 + 1, 4, z2 - 4, x1 + 2, 4, z2 - 1)
        for i in range(4):                                         # internal stair
            w.stairs(x1 + 1, i, z2 - 1 - i, "minecraft:oak_stairs", "north")
    gable(w, x1, x2, z1, z2, wall_h + 1, "x")
    out = 1 if facing == "east" else -1                            # direction pointing away from the door wall
    dx = x2 if facing == "east" else x1
    step = dx + out
    w.clear(dx, 0, cz, dx, 1, cz)
    w.door(dx, 0, cz, facing)
    w.stairs(step, 0, cz, "minecraft:stone_brick_stairs", "west" if facing == "east" else "east")
    w.lantern(step, 2, cz - 1)
    w.set(step, 0, cz + 2, "minecraft:potted_poppy")
    w.set(step, 0, cz - 2, "minecraft:potted_poppy")
    for z in (cz - 2, cz + 2):                                     # windows with open shutters
        if z1 < z < z2:
            w.pane(dx, 2, z)
            w.shutter(step, 2, z - 1, facing)
            w.shutter(step, 2, z + 1, facing)
    for x in (cx - 2, cx + 2):
        for z in (z1, z2):
            w.pane(x, 2, z)
    bx = x1 + 1 if facing == "east" else x2 - 1                    # chimney on the back gable
    w.fill(bx, 0, z1 - 1, bx, wall_h + 5, z1 - 1, COBBLE)
    w.set(bx, wall_h + 6, z1 - 1, "minecraft:campfire", {"facing": "north", "lit": "true", "signal_fire": "false", "waterlogged": "false"})
    w.set(bx, 0, z1, "minecraft:furnace", {"facing": "south", "lit": "false"})
    inner = x1 + 2 if facing == "east" else x2 - 2
    w.set(inner, 0, z2 - 1, "minecraft:red_bed", {"facing": "north", "part": "foot", "occupied": "false"})
    w.set(inner, 0, z2 - 2, "minecraft:red_bed", {"facing": "north", "part": "head", "occupied": "false"})
    w.set(cx, 0, cz - 1, "minecraft:oak_fence")
    w.set(cx, 1, cz - 1, "minecraft:oak_pressure_plate", {"powered": "false"})
    w.chest(cx - out, 0, z1 + 1, "south")
    w.set(cx, 0, z1 + 1, "minecraft:bookshelf")
    w.fill(cx - 1, -1, cz - 1, cx + 1, -1, cz + 1, "minecraft:spruce_planks")
    w.fill(cx - 1, 0, cz + 1, cx + 1, 0, cz + 1, "minecraft:red_carpet")
    w.lantern(cx, wall_h - 1 if not two_floors else 3, cz, hanging=True)
    gx = (x1 - 3) if facing == "east" else (x2 + 3)                # kitchen garden behind the house
    for gz in range(cz - 3, cz + 4):
        w.set(gx, -1, gz, "minecraft:farmland", {"moisture": "7"})
        w.set(gx, 0, gz, "minecraft:wheat", {"age": str(RNG.randint(4, 7))})
    w.fill(gx - 1, 0, cz - 4, gx + 1, 0, cz - 4, "minecraft:oak_fence")
    w.fill(gx - 1, 0, cz + 4, gx + 1, 0, cz + 4, "minecraft:oak_fence")


def tavern(w, cx, cz, facing):
    x1, x2, z1, z2 = cx - 7, cx + 7, cz - 6, cz + 6
    out = 1 if facing == "east" else -1
    w.fill(x1 - 1, -1, z1 - 1, x2 + 1, -1, z2 + 1, COBBLE)
    w.box(x1, 0, z1, x2, 9, z2, PLASTER, thick=1)
    for x, z in ((x1, z1), (x1, z2), (x2, z1), (x2, z2)):
        w.fill(x, 0, z, x, 9, z, LOG, {"axis": "y"})
    for y in (4, 9):
        for x in range(x1, x2 + 1):
            w.set(x, y, z1, LOG, {"axis": "x"})
            w.set(x, y, z2, LOG, {"axis": "x"})
        for z in range(z1, z2 + 1):
            w.set(x1, y, z, LOG, {"axis": "z"})
            w.set(x2, y, z, LOG, {"axis": "z"})
    w.fill(x1 + 1, 4, z1 + 1, x2 - 1, 4, z2 - 1, "minecraft:spruce_planks")
    w.clear(x1 + 1, 4, z1 + 1, x1 + 4, 4, z1 + 3)
    for i in range(4):
        w.stairs(x1 + 1 + i, i, z1 + 1, "minecraft:oak_stairs", "east")
    gable(w, x1, x2, z1, z2, 10, "x")
    dx = x2 if facing == "east" else x1
    w.clear(dx, 0, cz - 1, dx, 2, cz + 1)
    for dz in (-1, 1):
        w.door(dx, 0, cz + dz, facing)
    for z in range(z1 + 2, z2 - 1, 3):
        for y in (2, 6):
            if abs(z - cz) > 1:
                w.pane(dx, y, z)
    for x in range(x1 + 3, x2 - 2, 3):
        for y in (2, 6):
            for z in (z1, z2):
                w.pane(x, y, z)
    w.fill(x1 + 2, 0, z2 - 2, x2 - 2, 0, z2 - 2, PLANKS)             # bar
    for x in range(x1 + 3, x2 - 2, 2):
        w.set(x, 1, z2 - 2, "minecraft:barrel", {"facing": "up", "open": "false"})
        w.set(x, 0, z2 - 1, "minecraft:barrel", {"facing": "up", "open": "false"})
    for tx, tz in ((cx - 3, cz - 2), (cx + 1, cz - 2), (cx - 3, cz + 1), (cx + 1, cz + 1)):
        w.fill(tx, 0, tz, tx + 1, 0, tz, "minecraft:oak_fence")
        w.fill(tx, 1, tz, tx + 1, 1, tz, "minecraft:oak_pressure_plate", {"powered": "false"})
        w.stairs(tx, 0, tz - 1, "minecraft:oak_stairs", "south")
        w.stairs(tx + 1, 0, tz + 1, "minecraft:oak_stairs", "north")
    bx = x1 + 1 if facing == "east" else x2 - 1
    w.fill(bx, 0, z1 + 1, bx, 3, z1 + 1, COBBLE)
    w.set(bx, 0, z1 + 2, "minecraft:campfire", {"facing": "east", "lit": "true", "signal_fire": "false", "waterlogged": "false"})
    w.fill(bx, 4, z1 - 1, bx, 15, z1 - 1, COBBLE)
    for lx in range(x1 + 3, x2 - 2, 4):
        w.lantern(lx, 3, cz, hanging=True)
    w.lantern(dx + out, 3, cz - 2)
    w.lantern(dx + out, 3, cz + 2)


def chapel(w, cx, cz, facing):
    x1, x2, z1, z2 = cx - 5, cx + 5, cz - 8, cz + 8
    w.fill(x1 - 1, -1, z1 - 1, x2 + 1, -1, z2 + 1, COBBLE)
    w.fill(x1, 0, z1, x2, 9, z2, BRICK)
    w.clear(x1 + 1, 0, z1 + 1, x2 - 1, 9, z2 - 1)
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            for y in range(0, 10):
                if w.get(x, y, z) == BRICK:
                    w.set(x, y, z, course(y))
    for x, z in ((x1, z1), (x1, z2), (x2, z1), (x2, z2)):
        w.fill(x, 0, z, x, 11, z, BRICK)
    dx = x2 if facing == "east" else x1
    far = x1 if facing == "east" else x2
    w.clear(dx, 0, cz, dx, 2, cz)
    for z in range(z1 + 3, z2 - 2, 4):
        for y in (3, 4, 5, 6):
            w.pane(far, y, z)
            w.pane(dx, y, z) if abs(z - cz) > 1 else None
    gable(w, x1, x2, z1, z2, 10, "z", end=BRICK)
    for z in range(z1 + 3, z2 - 4, 2):                               # pews
        for x in (cx - 3, cx - 2, cx + 2, cx + 3):
            w.stairs(x, 0, z, "minecraft:oak_stairs", "north")
    w.fill(cx - 1, 0, z1 + 1, cx + 1, 0, z1 + 1, "minecraft:smooth_quartz")
    w.set(cx, 1, z1 + 1, "minecraft:candle", {"candles": "1", "lit": "true", "waterlogged": "false"})
    w.lantern(cx, 8, cz, hanging=True)
    tz = z2 + 3                                                      # bell tower beside the nave end
    w.fill(cx - 3, -1, tz - 3, cx + 3, -1, tz + 3, COBBLE)
    w.disc(cx, tz, 3, 0, 18, BRICK)
    w.disc(cx, tz, 2, 0, 18, AIR)
    w.clear(cx - 1, 0, tz - 3, cx + 1, 3, tz - 3)
    w.disc(cx, tz, 2, 11, 11, PLANKS)
    w.clear(cx - 3, 12, tz, cx + 3, 16, tz)
    w.clear(cx, 12, tz - 3, cx, 16, tz + 3)
    w.set(cx, 15, tz, "minecraft:bell", {"attachment": "ceiling", "facing": "north", "powered": "false"})
    w.set(cx, 16, tz, ROOF_BLOCK)
    w.cone(cx, tz, 3, 19, ROOF_BLOCK)


def stall(w, x, z, colour):
    w.fill(x - 2, -1, z - 1, x + 2, -1, z + 1, "minecraft:smooth_stone")
    for px in (x - 2, x + 2):
        for pz in (z - 1, z + 1):
            w.fill(px, 0, pz, px, 2, pz, "minecraft:dark_oak_fence")
    for dx in range(-3, 4):
        for dz in range(-2, 3):
            w.set(x + dx, 3, z + dz, f"minecraft:{colour}_wool" if (dx + dz) % 2 == 0 else "minecraft:white_wool")
    w.fill(x - 1, 0, z, x + 1, 0, z, "minecraft:spruce_planks")
    w.set(x - 1, 1, z, "minecraft:barrel", {"facing": "up", "open": "false"})
    w.set(x + 1, 1, z, "minecraft:hay_block", {"axis": "y"})
    w.set(x, 1, z, "minecraft:composter", {"level": "4"})


def tree(w, x, z, h):
    w.fill(x, 0, z, x, h, z, "minecraft:oak_log", {"axis": "y"})
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            for dy in range(0, 3):
                if abs(dx) + abs(dz) + dy <= 4 and not (dx == 0 and dz == 0 and dy < 2):
                    w.set(x + dx, h - 1 + dy, z + dz, "minecraft:oak_leaves", {"distance": "1", "persistent": "true", "waterlogged": "false"})


def farm(w, x1, z1, x2, z2):
    w.fill(x1, -1, z1, x2, -1, z2, "minecraft:farmland", {"moisture": "7"})
    cz = (z1 + z2) // 2
    w.fill(x1, -1, cz, x2, -1, cz, "minecraft:water")
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            if z != cz:
                w.set(x, 0, z, RNG.choice(["minecraft:wheat", "minecraft:wheat", "minecraft:carrots", "minecraft:potatoes"]), {"age": "7"})
    for x in range(x1 - 1, x2 + 2):
        w.set(x, 0, z1 - 1, "minecraft:oak_fence")
        w.set(x, 0, z2 + 1, "minecraft:oak_fence")
    for z in range(z1 - 1, z2 + 2):
        w.set(x1 - 1, 0, z, "minecraft:oak_fence")
        w.set(x2 + 1, 0, z, "minecraft:oak_fence")
    w.set(x1 - 1, 0, cz, AIR)


def waystones(w):
    w.fill(-2, -1, 61, 2, -1, 65, "minecraft:polished_andesite")
    w.waystone(0, 0, 63, "south")
    for x in (-2, 2):
        w.wallpost(x, 0, 61)
        w.lantern(x, 1, 61)
    w.waystone(8, 0, 72, "west", "waystones:mossy_waystone")
    w.waystone(-8, 0, 30, "east", "waystones:mossy_waystone")


def town(w):
    for z in range(50, 113):                          # main road: worn path with cobbled margins
        for x in range(-3, 4):
            w.set(x, -1, z, "minecraft:dirt_path" if RNG.random() > 0.12 else "minecraft:coarse_dirt")
        for x in (-4, 4):
            w.set(x, -1, z, COBBLE if RNG.random() < 0.7 else "minecraft:gravel")
    w.fill(-16, -1, 68, 16, -1, 86, BRICK)             # market square
    for x in range(-16, 17):
        for z in range(68, 87):
            if RNG.random() < 0.18:
                w.set(x, -1, z, COBBLE)
    well(w, 0, 77)
    stall(w, -9, 72, "red")
    stall(w, 9, 72, "blue")
    stall(w, -9, 83, "yellow")
    stall(w, 9, 83, "green")
    for x, z in ((-14, 70), (14, 70), (-14, 84), (14, 84)):
        w.fill(x, 0, z, x, 3, z, LOG, {"axis": "y"})
        w.lantern(x, 4, z)
    plots = [(-12, 55, "east", "house", 0), (12, 55, "west", "house", 1), (-12, 63, "east", "house", 2),
             (12, 63, "west", "house", 3), (-14, 98, "east", "tavern", 0), (13, 97, "west", "chapel", 0),
             (-12, 108, "east", "house", 4)]
    for x, z, face, kind, style in plots:
        if kind == "house":
            house(w, x, z, face, style)
        elif kind == "tavern":
            tavern(w, x, z, face)
        else:
            chapel(w, x, z, face)
    smithy(w, -16, 90)
    for z in range(52, 112, 8):                        # lamp posts along the road
        for x in (-5, 5):
            w.fill(x, 0, z, x, 3, z, "minecraft:cobblestone_wall", dict(WALLPROPS))
            w.lantern(x, 4, z)
    farm(w, 24, 56, 34, 66)
    farm(w, -36, 70, -26, 80)
    farm(w, 24, 108, 34, 118)
    for tx, tz, th in ((-22, 104, 5), (-30, 96, 6), (22, 92, 5), (32, 96, 6), (-24, 58, 5), (38, 80, 6), (-38, 86, 5), (26, 124, 5), (-26, 120, 6)):
        tree(w, tx, tz, th)


def connect_pass(w):
    """Set the north/south/east/west connection state of fences, walls, panes and bars from their neighbours."""
    fences = {"minecraft:oak_fence", "minecraft:dark_oak_fence"}
    panes = {"minecraft:glass_pane", "minecraft:iron_bars"}
    walls = {"minecraft:cobblestone_wall", "minecraft:stone_brick_wall"}
    family = fences | panes | walls
    cells = w.t.cells
    nonsolid = ("_carpet", "torch", "lantern", "_trapdoor", "_door", "air", "banner", "water", "potted_poppy", "wheat", "carrots",
                "potatoes", "bell", "campfire", "ladder", "_pressure_plate", "candle", "leaves", "farmland")

    def solidish(c):
        return bool(c) and not any(c[0].endswith(s) or s in c[0] for s in nonsolid)

    dirs = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}
    for (x, y, z), (name, props, nbt) in list(cells.items()):
        if name not in family:
            continue
        new = dict(props)
        for d, (dx, dy, dz) in dirs.items():
            nb = cells.get((x + dx, y + dy, z + dz))
            joined = bool(nb) and (nb[0] in family or solidish(nb))
            new[d] = ("low" if joined else "none") if name in walls else ("true" if joined else "false")
        if name in walls:
            new["up"] = "true"
        new.setdefault("waterlogged", "false")
        cells[(x, y, z)] = (name, tuple(sorted(new.items())), nbt)


# --- validation -----------------------------------------------------------------------------------------------------
def walkable(w, start, goal):
    cells = w.t.cells

    def solid(x, y, z):
        c = cells.get((x, y, z))
        if y < 0:
            return not (c and c[0] == "minecraft:water")     # open water is not walkable, the bridge is
        return bool(c) and c[0] not in PASSABLE and not c[0].endswith("_pane") and "fence" not in c[0] and "leaves" not in c[0]

    def stand(x, y, z):
        return (not solid(x, y, z) and not solid(x, y + 1, z) and solid(x, y - 1, z)
                and (cells.get((x, y, z)) or (AIR,))[0] != "minecraft:water")

    seen, queue = {start}, collections.deque([start])
    while queue:
        x, y, z = queue.popleft()
        if (x, y, z) == goal:
            return True
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (0, 1, -1):
                n = (x + dx, y + dy, z + dz)
                if n in seen or not (-60 <= n[0] <= 60 and -50 <= n[2] <= 125 and 0 <= n[1] <= 60):
                    continue
                if dy == 1 and solid(x, y + 1, z):
                    continue
                if stand(*n):
                    seen.add(n)
                    queue.append(n)
    return False


def build():
    RNG.seed(20261007)
    w = World()
    moat(w)
    courtyard(w)
    curtain_wall(w)
    curtain_stairs(w)
    for sx in (-1, 1):
        for sz in (-1, 1):
            tower(w, sx * 41, sz * 41, 6, 26)
    tower(w, 0, -41, 5, 20)
    tower(w, -41, 0, 5, 20)
    tower(w, 41, 0, 5, 20)
    keep(w)
    town(w)
    waystones(w)
    connect_pass(w)
    return w


def split_tiles(w):
    tiles = collections.defaultdict(dict)
    for (x, y, z), cell in w.t.cells.items():
        tiles[(x // TILE, z // TILE)][(x, y, z)] = cell
    return tiles


def write(w):
    STRUCT_DIR.mkdir(parents=True, exist_ok=True)
    for old in STRUCT_DIR.glob("*.nbt"):
        old.unlink()
    tiles = split_tiles(w)
    meta = []
    ymin = min(y for (_, y, _) in w.t.cells)
    ymax = max(y for (_, y, _) in w.t.cells)
    for (i, j), cells in sorted(tiles.items()):
        x0, z0 = i * TILE, j * TILE
        tpl = V.Template()
        for (x, y, z), (name, props, nbt) in cells.items():
            tpl.set(x - x0, y - ymin, z - z0, name, dict(props), nbt)
        size = (TILE, ymax - ymin + 1, TILE)
        original = V.SIZE
        V.SIZE = size
        try:
            data = V.nbt_bytes(tpl.to_nbt())
        finally:
            V.SIZE = original
        name = f"tile_{i}_{j}".replace("-", "m")
        (STRUCT_DIR / f"{name}.nbt").write_bytes(data)
        meta.append({"name": f"ddo:castle/{name}", "dx": x0, "dy": ymin, "dz": z0, "blocks": len(cells)})
    return meta, ymin, ymax


def layout_js(meta, ymin, ymax):
    layout = {
        "tiles": [{"id": m["name"], "dx": m["dx"], "dy": m["dy"], "dz": m["dz"]} for m in meta],
        "clear": {"x1": -62, "x2": 62, "z1": -62, "z2": 130, "height": 70, "depth": 30},
        "forceload": {"x1": -64, "x2": 64, "z1": -64, "z2": 132},
        # where the cutscene starts, the route the guards drag the player along, and where everyone ends up
        "town_start": [0.5, 0, 66.5],
        "spawn": [0.5, 0, 60.5],
        "waystone": [0.5, 0, 63.5],
        "waypoints": [[0.5, 0, 52.5], [0.5, 0, 44.5], [0.5, 0, 30.5], [0.5, 0, 6.5], [0.5, 0, -4.5],
                      [0.5, 0, -14.5], [0.5, 0, -22.5]],
        "king": [0.5, 2, -28.5],
        "throne_front": [0.5, 0, -22.5],
        "guards": [[-4.5, 0, -10.5], [4.5, 0, -10.5], [-6.5, 0, -22.5], [6.5, 0, -22.5], [-4.5, 0, 36.5], [4.5, 0, 36.5],
                   [-6.5, 0, 44.5], [6.5, 0, 44.5]],
        "villagers": [[-8.5, 0, 74.5], [8.5, 0, 76.5], [-6.5, 0, 80.5], [6.5, 0, 80.5], [-11.5, 0, 70.5], [11.5, 0, 82.5]],
    }
    return ("// Generated by tools/gen_castle.py. Do not edit by hand.\n"
            "global.CASTLE = " + json.dumps(layout, indent=2) + "\n")


def floor_plan(w, y=0, step=2):
    rows = []
    for z in range(-50, 126, step):
        line = ""
        for x in range(-52, 53, 1):
            c = w.t.cells.get((x, y, z))
            ground = w.t.cells.get((x, -1, z))
            g = ground[0].split(":")[1] if ground else ""
            if c and c[0] != AIR:
                n = c[0].split(":")[1]
                ch = ("#" if any(k in n for k in ("brick", "cobble", "planks", "log", "deepslate", "terracotta", "stairs", "andesite"))
                      else "=" if "carpet" in n else "+" if "door" in n else "T" if "leaves" in n
                      else "w" if any(k in n for k in ("wheat", "carrot", "potato")) else "o")
            elif "water" in g:
                ch = "~"
            elif g:
                ch = ","
            else:
                ch = " "
            line += ch
        rows.append(line.rstrip())
    return "\n".join(rows)


def main():
    w = build()
    if not walkable(w, (0, 0, 112), (0, 0, -22)):
        raise SystemExit("castle is not walkable from the town street to the throne; fix the layout")
    meta, ymin, ymax = write(w)
    LAYOUT_JS.write_text(layout_js(meta, ymin, ymax), encoding="utf-8")
    total = sum(m["blocks"] for m in meta)
    print(f"{len(meta)} tiles, {total} blocks, height {ymin}..{ymax}; walkable gate to throne: yes")
    return w


if __name__ == "__main__":
    main()
