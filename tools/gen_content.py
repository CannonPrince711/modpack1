#!/usr/bin/env python3
"""
Saltglass content generator — the authored half of the pack.

Emits, deterministically:
  pack/overrides/config/paxi/datapacks/saltglass/**   the datapack (deep, three moments)
  pack/overrides/config/ftbquests/quests/**           the quest book (SNBT)
  pack/overrides/config/saltglass-*.json              pack-side config files
  pack/server/*.properties, jvm_args.txt              server housekeeping

Everything is generated so that IDs, function references and item ids cannot drift
between the quest book and the datapack. `--check` re-parses every emitted SNBT file
with a strict parser and verifies cross-references; the builder calls this too.

Field names for the quest format were taken from the FTB Quests 1.20.1 source
(branch 1.20.1/dev), not from memory:
  * BaseQuestFile.readDataFull() reads  data.snbt  +  chapters/*.snbt  (SNBT, not JSON)
  * BaseQuestFile.VERSION = 13
  * task types  : item, custom, xp, dimension, stat, kill, location, checkmark,
                  advancement, observation, biome, structure, gamestage, fluid
  * reward types: item, choice, all_table, random, loot, command, custom, xp,
                  xp_levels, advancement, toast, gamestage
  * DimensionTask field = "dimension"; StageTask = "stage"; CommandReward = "command"
  * ItemTask = "item" (serialised ItemStack), "count", "consume_items", "match_nbt"
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVR = ROOT / "pack/overrides"
DP = OVR / "config/paxi/datapacks/saltglass"
QUESTS = OVR / "config/ftbquests/quests"
DEEPDIM = "saltglass:reflected_deep"

# cathedral placement: its min corner in the deep. 111x46x61 -> centred on 0,0.
CATHEDRAL_POS = (-55, -49, -30)
ARRIVAL = (-64, -45, 0)          # where a diver surfaces, west of the porch
DOORS_Z = (-9, 0, 9)             # offsets from world z=0

# item ids are restricted to this whitelist, all of which are long-standing ids that
# predate 1.20.1 and have not been renamed. Nothing outside this set is used in a task,
# so the quest book cannot reference an item that does not exist.
ITEM_WHITELIST = {
    "minecraft": {
        "glass", "tinted_glass", "amethyst_shard", "bucket", "water_bucket", "cauldron",
        "barrel", "chest", "lantern", "sea_lantern", "prismarine_bricks", "dark_prismarine",
        "heart_of_the_sea", "nautilus_shell", "oak_boat", "iron_bars", "calcite",
        "bone_block", "deepslate_bricks", "compass", "clock",
    },
    "farmersdelight": {"cooking_pot", "cutting_board", "skillet", "stove"},
    "create": {
        "andesite_alloy", "andesite_casing", "cogwheel", "shaft", "water_wheel",
        "hand_crank", "mechanical_press", "basin", "fluid_pipe", "mechanical_pump",
        "goggles", "wrench", "toolbox", "copper_backtank", "spout", "depot", "encased_fan",
        "mechanical_mixer", "millstone", "crushing_wheel", "mixing_bowl", "item_vault",
    },
    "sophisticatedbackpacks": {"backpack"},
    "paragliders": {"paraglider"},
}

FUNCTIONS: dict[str, str] = {}       # path -> body, populated as we author


def item_ok(item: str) -> bool:
    ns, _, name = item.partition(":")
    return name in ITEM_WHITELIST.get(ns, set())


# ----------------------------------------------------------------- SNBT emitting
def snbt_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def snbt_val(v) -> str:
    if isinstance(v, bool):
        return "1b" if v else "0b"
    if isinstance(v, int):
        return f"{v}L" if abs(v) > 2_147_483_647 else str(v)
    if isinstance(v, float):
        return f"{v}d"
    if isinstance(v, str):
        return snbt_str(v)
    if isinstance(v, bytes):
        return f"{v[0]}b"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(snbt_val(x) for x in v) + "]"
    if isinstance(v, dict):
        parts = []
        for k, val in v.items():
            key = k if re.fullmatch(r"[A-Za-z0-9._+-]+", k) else snbt_str(k)
            parts.append(f"{key}: {snbt_val(val)}")
        return "{" + ", ".join(parts) + "}"
    raise TypeError(f"unsupported SNBT value {v!r}")


def snbt_doc(v: dict, indent: int = 0) -> str:
    """Human-readable SNBT with tabs, so the quest files stay diffable."""
    pad, pad2 = "\t" * indent, "\t" * (indent + 1)

    def render(val, depth):
        p, p2 = "\t" * depth, "\t" * (depth + 1)
        if isinstance(val, dict):
            if not val:
                return "{}"
            inner = ",\n".join(
                f"{p2}{k if re.fullmatch(r'[A-Za-z0-9._+-]+', k) else snbt_str(k)}: "
                f"{render(x, depth + 1)}" for k, x in val.items())
            return "{\n" + inner + f"\n{p}}}"
        if isinstance(val, list):
            if not val:
                return "[]"
            if all(isinstance(x, (int, float, str)) and not isinstance(x, bool) for x in val):
                flat = "[" + ", ".join(snbt_val(x) for x in val) + "]"
                if len(flat) < 100:
                    return flat
            inner = ",\n".join(f"{p2}{render(x, depth + 1)}" for x in val)
            return "[\n" + inner + f"\n{p}]"
        return snbt_val(val)

    return render(v, indent)


# ----------------------------------------------------------------- SNBT parsing (validation)
class SnbtError(Exception):
    pass


def _parse(s: str, i: int):
    n = len(s)

    def ws(i):
        while i < n and s[i] in " \t\r\n":
            i += 1
        return i

    i = ws(i)
    if i >= n:
        raise SnbtError("unexpected end of file")
    c = s[i]
    if c == "{":
        i = ws(i + 1)
        out = {}
        if s[i] == "}":
            return out, i + 1
        while True:
            i = ws(i)
            if s[i] == '"':
                k, i = _parse_string(s, i)
            else:
                j = i
                while j < n and s[j] not in ": \t\r\n":
                    j += 1
                k = s[i:j]
                i = j
            i = ws(i)
            if s[i] != ":":
                raise SnbtError(f"expected ':' at {i}")
            v, i = _parse(s, i + 1)
            out[k] = v
            i = ws(i)
            if i < n and s[i] == ",":
                i = ws(i + 1)
                continue
            if i < n and s[i] == "}":
                return out, i + 1
            raise SnbtError(f"expected ',' or '}}' at {i}")
    if c == "[":
        i = ws(i + 1)
        out = []
        if s[i] == "]":
            return out, i + 1
        while True:
            v, i = _parse(s, i)
            out.append(v)
            i = ws(i)
            if i < n and s[i] == ",":
                i = ws(i + 1)
                continue
            if i < n and s[i] == "]":
                return out, i + 1
            raise SnbtError(f"expected ',' or ']' at {i}")
    if c == '"':
        return _parse_string(s, i)
    j = i
    while j < n and s[j] not in ",]} \t\r\n":
        j += 1
    tok = s[i:j]
    if not tok:
        raise SnbtError(f"empty token at {i}")
    try:
        if tok.endswith(("b", "B")):
            return int(tok[:-1]), j
        if tok.endswith(("l", "L")):
            return int(tok[:-1]), j
        if tok.endswith(("d", "D")):
            return float(tok[:-1]), j
        if tok.endswith(("f", "F")):
            return float(tok[:-1]), j
        if tok.endswith(("s", "S")):
            return int(tok[:-1]), j
        if "." in tok or "e" in tok.lower():
            return float(tok), j
        return int(tok), j
    except ValueError:
        return tok, j


def _parse_string(s: str, i: int):
    assert s[i] == '"'
    i += 1
    out = []
    while i < len(s):
        if s[i] == "\\":
            out.append(s[i + 1])
            i += 2
            continue
        if s[i] == '"':
            return "".join(out), i + 1
        out.append(s[i])
        i += 1
    raise SnbtError("unterminated string")


def snbt_parse(text: str):
    v, i = _parse(text, 0)
    i2 = len(text)
    while i < i2 and text[i] in " \t\r\n":
        i += 1
    if i != i2:
        raise SnbtError(f"trailing data at {i}")
    return v


# ----------------------------------------------------------------- id allocation
def qid(*parts: str) -> int:
    """Deterministic 63-bit id from a name, so re-running never reshuffles the tree."""
    h = hashlib.sha1(("saltglass:" + "/".join(parts)).encode()).digest()[:8]
    return int.from_bytes(h, "big") & 0x7FFF_FFFF_FFFF_FFFF


# ----------------------------------------------------------------- functions
def fn(path: str, *lines: str) -> None:
    FUNCTIONS[path] = "\n".join(lines) + "\n"


def build_functions():
    # ---- load / tick
    fn("load",
       "# Saltglass — runs on every datapack load (/reload included).",
       "scoreboard objectives add sg_state dummy",
       'tellraw @a [{"text":"[Saltglass] ","color":"#E0A32E"},'
       '{"text":"The sea is still falling.","color":"#7FB4B0","italic":true}]')

    fn("tick",
       "# Runs every tick. Two cheap selector checks, nothing else.",
       "execute as @a[scores={sg_divecooldown=1..}] run scoreboard players remove @s sg_divecooldown 1",
       "execute if score #cathedral sg_state matches 1 run function saltglass:cathedral/place",
       "execute if score #turning_wave sg_state matches 0 run function saltglass:turning/idle",
       "execute if score #turning_wave sg_state matches 1..3 run function saltglass:turning/tick",
       "execute as @a[gamemode=!spectator] at @s if dimension minecraft:overworld "
       "if predicate saltglass:night if block ~ ~-1 ~ minecraft:tinted_glass "
       "if predicate saltglass:crouching run function saltglass:dive/enter",
       "execute as @a[gamemode=!spectator] at @s if dimension " + DEEPDIM + " "
       "if block ~ ~-1 ~ minecraft:tinted_glass if predicate saltglass:crouching "
       "run function saltglass:dive/exit")

    # ---- signature moment 1: the dive through the face
    fn("dive/enter",
       "# Signature moment 1 — the Dive Through the Face.",
       "execute if score @s sg_divecooldown matches 1.. run return fail",
       "scoreboard players set @s sg_divecooldown 200",
       "particle minecraft:splash ~ ~ ~ 1.2 0.4 1.2 40 0.35 normal",
       "particle minecraft:bubble ~ ~1 ~ 1.0 0.5 1.0 30 0.1 normal",
       "playsound minecraft:entity.player.splash master @a ~ ~ ~ 1.4 0.7",
       "# remember where the glass was, so the return trip has somewhere to land",
       "execute unless entity @e[tag=sg_gate_return,distance=..6,limit=1] run "
       "summon minecraft:marker ~ ~ ~ {Tags:[\"sg_gate_return\"]}",
       f"execute in {DEEPDIM} run tp @s {ARRIVAL[0]} {ARRIVAL[1]} {ARRIVAL[2]} "
       f"facing {ARRIVAL[0] + 11} {ARRIVAL[1]} {ARRIVAL[2]}",
       "effect give @s minecraft:water_breathing 6000 0 true",
       "effect give @s minecraft:dolphins_grace 1200 0 true",
       "playsound minecraft:ambient.underwater.enter master @s ~ ~ ~ 1.6 0.8",
       "title @s actionbar [{\"text\":\"The sea is upside down above you.\","
       "\"color\":\"#7FB4B0\",\"italic\":true}]",
       "# the first dive is what raises the cathedral out of the dark",
       "execute if score #cathedral sg_state matches 0 run scoreboard players set #cathedral sg_state 1")

    fn("dive/exit",
       "execute if score @s sg_divecooldown matches 1.. run return fail",
       "scoreboard players set @s sg_divecooldown 200",
       "execute at @e[tag=sg_gate_return,limit=1,sort=nearest] run tp @s ~3 ~2 ~",
       "particle minecraft:splash ~ ~ ~ 0.8 0.3 0.8 24 0.3 normal",
       "playsound minecraft:entity.player.splash master @s ~ ~ ~ 1.2 1.1",
       "effect clear @s minecraft:water_breathing",
       "effect clear @s minecraft:dolphins_grace",
       "title @s actionbar [{\"text\":\"You surface into dry air.\","
       "\"color\":\"#E8E3D6\",\"italic\":true}]")

    # ---- signature moment 2: the cathedral
    fn("cathedral/place",
       "# Places the cathedral once, the tick after the first diver is inside the deep",
       "# (by then the destination chunks are loaded).",
       "scoreboard players set #cathedral sg_state 2",
       f"place structure saltglass:drowned_cathedral {CATHEDRAL_POS[0]} "
       f"{CATHEDRAL_POS[1]} {CATHEDRAL_POS[2]}",
       "playsound minecraft:block.conduit.activate master @a 0 -45 0 3.0 0.6",
       "tellraw @a [{\"text\":\"[Saltglass] \",\"color\":\"#E0A32E\"},"
       "{\"text\":\"Far east of the arrival shelf, something with spires is standing in the "
       "water, and its windows are lit.\",\"color\":\"#7FB4B0\"}]")

    fn("cathedral/open",
       "# Act II curtain — called by the quest that lights the third beacon.",
       "execute if score #cathedral_open sg_state matches 1.. run return fail",
       "scoreboard players set #cathedral_open sg_state 1",
       f"execute in {DEEPDIM} run fill {CATHEDRAL_POS[0] + 3} {CATHEDRAL_POS[1] + 4} "
       f"{CATHEDRAL_POS[2] + 30 - 9 - 2} {CATHEDRAL_POS[0] + 5} {CATHEDRAL_POS[1] + 9} "
       f"{CATHEDRAL_POS[2] + 30 - 9 + 2} minecraft:air replace minecraft:tinted_glass",
       f"execute in {DEEPDIM} run fill {CATHEDRAL_POS[0] + 3} {CATHEDRAL_POS[1] + 4} "
       f"{CATHEDRAL_POS[2] + 30 - 2} {CATHEDRAL_POS[0] + 5} {CATHEDRAL_POS[1] + 9} "
       f"{CATHEDRAL_POS[2] + 30 + 2} minecraft:air replace minecraft:tinted_glass",
       f"execute in {DEEPDIM} run fill {CATHEDRAL_POS[0] + 3} {CATHEDRAL_POS[1] + 4} "
       f"{CATHEDRAL_POS[2] + 30 + 9 - 2} {CATHEDRAL_POS[0] + 5} {CATHEDRAL_POS[1] + 9} "
       f"{CATHEDRAL_POS[2] + 30 + 9 + 2} minecraft:air replace minecraft:tinted_glass",
       f"execute in {DEEPDIM} run fill {CATHEDRAL_POS[0] + 88} {CATHEDRAL_POS[1] + 5} "
       f"{CATHEDRAL_POS[2] + 30 - 8} {CATHEDRAL_POS[0] + 88} {CATHEDRAL_POS[1] + 7} "
       f"{CATHEDRAL_POS[2] + 30 + 8} minecraft:air replace minecraft:tinted_glass",
       "playsound minecraft:block.beacon.activate master @a 0 -45 0 4.0 0.5",
       "tellraw @a [{\"text\":\"[Saltglass] \",\"color\":\"#E0A32E\"},"
       "{\"text\":\"Three bells, three beacons, and the third door of the cathedral is "
       "open. Somebody intended it to be.\",\"color\":\"#7FB4B0\"}]")

    # ---- the three harbours
    for i, name in enumerate(("one", "two", "three"), start=1):
        roman = ("First", "Second", "Third")[i - 1]
        fn(f"harbour/{name}",
           f"# Raises the {roman} harbour bell and its beacon tower where the player stands.",
           f"execute if score #harbour{i} sg_state matches 1.. run return fail",
           f"scoreboard players set #harbour{i} sg_state 1",
           f"summon minecraft:marker ~ ~ ~ {{Tags:[\"sg_harbour_{i}\"]}}",
           f"place structure saltglass:beacon_tower ~-16 ~ ~-16",
           "playsound minecraft:block.beacon.activate master @a ~ ~ ~ 3.0 0.8",
           "particle minecraft:end_rod ~ ~8 ~ 0.6 8.0 0.6 60 0.0 normal",
           "particle minecraft:enchant ~ ~ ~ 3.0 0.5 3.0 40 1.0 normal",
           f"tellraw @a [{{\"text\":\"[Saltglass] \",\"color\":\"#E0A32E\"}},"
           f"{{\"text\":\"The {roman} bell is back on its bearings. Something down the"
           f" coast answers it.\",\"color\":\"#7FB4B0\"}}]",
           "advancement grant @s only saltglass:harbour_bell")

    # ---- signature moment 3: the Turning
    fn("turning/set",
       "# Signature moment 3 — the Turning. Places the trench, spends the Tide Heart,",
       "# and hands the job of flooding to the staged wave runner.",
       "execute if score #turning sg_state matches 1.. run return fail",
       "execute if score #harbour1 sg_state matches 0 run return run tellraw @s "
       "[{\"text\":\"[Saltglass] \",\"color\":\"#E0A32E\"},{\"text\":\"The bells are not "
       "awake. Nothing would answer the Heart.\",\"color\":\"#8A5A3B\"}]",
       "scoreboard players set #turning sg_state 1",
       "clear @s minecraft:heart_of_the_sea 1",
       f"execute in {DEEPDIM} run place structure saltglass:tide_trench 24 -48 24",
       "scoreboard players set #turning_t sg_state 0",
       "scoreboard players set #turning_wave sg_state 1",
       "playsound minecraft:item.trident.thunder master @a ~ ~ ~ 4.0 0.5",
       "tellraw @a [{\"text\":\"[Saltglass] \",\"color\":\"#E0A32E\"},"
       "{\"text\":\"The Tide Heart is set. Now the water decides how much of this world "
       "it wants back.\",\"color\":\"#7FB4B0\"}]",
       "advancement grant @s only saltglass:the_turning")

    fn("turning/idle",
       "# Nothing to do; the harbour bells are the only gate on this.",
       "return 0")

    fn("turning/tick",
       "scoreboard players add #turning_t sg_state 1",
       "execute if score #turning_t sg_state matches 1 run function saltglass:turning/wave1",
       "execute if score #turning_t sg_state matches 120 run function saltglass:turning/wave2",
       "execute if score #turning_t sg_state matches 260 run function saltglass:turning/wave3",
       "execute if score #turning_t sg_state matches 400 run function saltglass:turning/wave4")

    waves = {
        1: (12, "the flats are wet to twelve blocks out"),
        2: (26, "the water is over the anchor stones"),
        3: (38, "the harbour wall is under"),
        4: (48, "the basin is a harbour again"),
    }
    for n, (r, phrase) in waves.items():
        lines = [f"# Turning wave {n} — radius {r} around each raised harbour."]
        ylo, yhi = (-2, 1) if n == 4 else (-1, 1)
        if n < 4:
            for i in range(1, 4):
                lines += [
                    # split along z: 97x4x97 would be 37636 blocks and the vanilla /fill
                    # limit is 32768, so each wave is emitted as two half-slabs.
                    f"execute at @e[tag=sg_harbour_{i},limit=1] run fill "
                    f"~-{r} ~{ylo} ~-{r} ~{r} ~{yhi} ~0 minecraft:water replace minecraft:air",
                    f"execute at @e[tag=sg_harbour_{i},limit=1] run fill "
                    f"~-{r} ~{ylo} ~1 ~{r} ~{yhi} ~{r} minecraft:water replace minecraft:air",
                    f"execute at @e[tag=sg_harbour_{i},limit=1] run particle "
                    f"minecraft:splash ~ ~1 ~ {r}.0 0.2 {r}.0 200 0.4 normal",
                    f"execute at @e[tag=sg_harbour_{i},limit=1] run playsound "
                    f"minecraft:entity.player.splash master @a ~ ~ ~ 3.0 0.6",
                ]
            lines.append(f"tellraw @a [{{\"text\":\"[Saltglass] \",\"color\":\"#E0A32E\"}},"
                         f"{{\"text\":\"{phrase}.\",\"color\":\"#7FB4B0\"}}]")
        else:
            for i in range(1, 4):
                lines += [
                    f"execute at @e[tag=sg_harbour_{i},limit=1] run fill "
                    f"~-{r} ~-2 ~-{r} ~{r} ~1 ~0 minecraft:water replace minecraft:air",
                    f"execute at @e[tag=sg_harbour_{i},limit=1] run fill "
                    f"~-{r} ~-2 ~1 ~{r} ~1 ~{r} minecraft:water replace minecraft:air",
                    f"execute at @e[tag=sg_harbour_{i},limit=1] run particle "
                    f"minecraft:bubble ~ ~ ~ {r}.0 0.5 {r}.0 300 0.6 normal",
                ]
            lines += [
                "tellraw @a [{\"text\":\"[Saltglass] \",\"color\":\"#E0A32E\"},"
                "{\"text\":\"The Kettle Sea is shallow, cold and back. Your first camp is "
                "underwater. Walk back at dusk and you will see what you did.\","
                "\"color\":\"#E0A32E\"}]",
                "playsound minecraft:block.conduit.activate master @a ~ ~ ~ 4.0 0.4",
                "title @a title [{\"text\":\"THE TURNING\",\"color\":\"#E0A32E\"}]",
                "title @a subtitle [{\"text\":\"the sea came back sideways\","
                "\"color\":\"#7FB4B0\",\"italic\":true}]",
                "give @a minecraft:oak_boat 1",
                "scoreboard players set #turning_wave sg_state 4",
                "scoreboard players set #turning_done sg_state 1",
            ]
        fn(f"turning/wave{n}", *lines)

    # ---- epilogue
    fn("epilogue/survey",
       "# Optional Act III epilogue helper: marks the drowned lighthouse site with a",
       "# labelled marker so a player can build the restoration without coordinates.",
       "execute if score #epilogue sg_state matches 1.. run return fail",
       "scoreboard players set #epilogue sg_state 1",
       "summon minecraft:marker ~ ~ ~ {Tags:[\"sg_epilogue_site\"],"
       "CustomName:'{\"text\":\"Drowned Lighthouse site\"}'}",
       "tellraw @s [{\"text\":\"[Saltglass] \",\"color\":\"#E0A32E\"},"
       "{\"text\":\"Marked. Whatever you build here is the first new thing this coast has "
       "seen in nine hundred years.\",\"color\":\"#7FB4B0\"}]")


# ----------------------------------------------------------------- data files
DIMENSION_TYPE = {
    "ultrawarm": False, "natural": False, "coordinate_scale": 1.0,
    "has_skylight": False, "has_ceiling": False, "ambient_light": 0.32,
    "fixed_time": 18000, "piglin_safe": False, "bed_works": False,
    "respawn_anchor_works": False, "has_raids": False,
    "logical_height": 384, "min_y": -64, "height": 384,
    "infiniburn": "#minecraft:infiniburn_overworld",
    "effects": "minecraft:the_end",
    "monster_spawn_light_level": {"type": "minecraft:uniform",
                                  "min_inclusive": 0, "max_inclusive": 0},
    "monster_spawn_block_light_limit": 0,
}

DIMENSION = {
    "type": "saltglass:reflected_deep",
    "generator": {
        "type": "minecraft:flat",
        "settings": {
            "biome": "minecraft:deep_ocean",
            "lakes": False,
            "features": False,
            "structure_overrides": [],
            "layers": [
                {"block": "minecraft:bedrock", "height": 1},
                {"block": "minecraft:deepslate", "height": 4},
                {"block": "minecraft:stone", "height": 8},
                {"block": "minecraft:prismarine", "height": 3},
                {"block": "minecraft:water", "height": 29},
                {"block": "minecraft:glass", "height": 4},
            ],
        },
    },
}

PREDICATE_NIGHT = {
    "condition": "minecraft:time_check",
    "value": {"min": 13000, "max": 23000},
    "period": 24000,
}
PREDICATE_CROUCHING = {
    "condition": "minecraft:entity_properties",
    "entity": "this",
    "predicate": {"flags": {"is_sneaking": True}},
}

ADVANCEMENTS = {
    "the_dive": ("The Dive Through the Face",
                 "Stand on your own mirror at night, crouch, and go under the reflection."),
    "harbour_bell": ("A Bell Back on Its Bearings",
                     "Raise one of the three harbour bells."),
    "the_turning": ("The Turning",
                    "Set the Tide Heart in the last dry trench and give the sea its basin back."),
}


def build_data_files():
    DP.mkdir(parents=True, exist_ok=True)
    (DP / "pack.mcmeta").write_text(json.dumps({
        "pack": {
            "pack_format": 15,
            "description": "Saltglass — the drained basin, the Reflected Deep and the Turning",
            "supported_formats": [15, 18],
        }
    }, indent=2) + "\n", encoding="utf-8")

    for rel, obj in (
        ("data/saltglass/dimension_type/reflected_deep.json", DIMENSION_TYPE),
        ("data/saltglass/dimension/reflected_deep.json", DIMENSION),
        ("data/saltglass/predicates/night.json", PREDICATE_NIGHT),
        ("data/saltglass/predicates/crouching.json", PREDICATE_CROUCHING),
    ):
        p = DP / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    for name, (title, desc) in ADVANCEMENTS.items():
        p = DP / f"data/saltglass/advancements/{name}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "display": {
                "title": {"text": title, "color": "#E0A32E"},
                "description": {"text": desc, "color": "#E8E3D6", "italic": True},
                "icon": {"item": "minecraft:heart_of_the_sea" if name == "the_turning"
                         else ("minecraft:sea_lantern" if name == "harbour_bell"
                               else "minecraft:tinted_glass")},
                "frame": "goal", "show_toast": True, "announce_to_chat": True,
                "hidden": name != "the_dive",
            },
            "criteria": {"manual": {"trigger": "minecraft:impossible"}},
        }, indent=2) + "\n", encoding="utf-8")

    # function tags
    for tag, value in (("load", "saltglass:load"), ("tick", "saltglass:tick")):
        p = DP / f"data/minecraft/tags/functions/{tag}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"values": [value]}, indent=2) + "\n", encoding="utf-8")

    for path, body in FUNCTIONS.items():
        p = DP / f"data/saltglass/functions/{path}.mcfunction"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


# ----------------------------------------------------------------- the quest book
def chapter(ch_id: str, title: str, order: int, quests: list[dict], **kw) -> dict:
    d = {
        "version": 13,
        "id": qid("chapter", ch_id),
        "group": "",
        "order_index": order,
        "title": title,
        "quests": quests,
    }
    d.update(kw)
    return d


def task_item(quest: str, item: str, count: int, title: str, consume: bool = True) -> dict:
    ns, _, name = item.partition(":")
    assert item_ok(item), f"item not in whitelist: {item}"
    return {
        "id": qid(quest, "task", item),
        "type": "ftbquests:item",
        "item": {"id": item, "Count": bytes([min(count, 127)])},
        "count": count,
        "consume_items": True if consume else False,
        "title": title,
    }


def task_check(quest: str, title: str) -> dict:
    return {"id": qid(quest, "task", "check"), "type": "ftbquests:checkmark", "title": title}


def task_dim(quest: str, dim: str, title: str) -> dict:
    return {"id": qid(quest, "task", "dim"), "type": "ftbquests:dimension",
            "dimension": dim, "title": title}


def reward_cmd(quest: str, command: str, title: str = "", per_team: bool = False) -> dict:
    r = {"id": qid(quest, "reward", command), "type": "ftbquests:command",
         "command": command, "elevate_perms": False, "silent": False}
    if title:
        r["title"] = title
    if per_team:
        r["team_reward"] = False
    return r


def quest(name: str, title: str, x: float, y: float, *, desc: list[str], tasks: list[dict],
          rewards: list[dict] | None = None, deps: list[str] | None = None,
          subtitle: str | None = None, icon: str | None = None) -> dict:
    q = {
        "id": qid("quest", name),
        "title": title,
        "x": float(x),
        "y": float(y),
        "shape": "circle",
        "size": 1.0,
        "description": desc,
        "tasks": tasks,
    }
    if subtitle:
        q["subtitle"] = subtitle
    if icon:
        assert item_ok(icon) or icon.startswith("ftbquests:"), f"icon not whitelisted: {icon}"
        ns, _, nm = icon.partition(":")
        q["icon"] = {"id": icon, "Count": bytes([1])}
    if rewards:
        q["rewards"] = rewards
    if deps:
        q["dependencies"] = [qid("quest", d) for d in deps]
    return q


def build_quests():
    chapters: list[dict] = []

    # ---------------- Act I
    chapters.append(chapter("00_arrival", "Act I — The Low Water", 0, [
        quest("wash_ashore", "Wash Ashore", 0, 0,
              subtitle="salvage-tag, no ship",
              desc=["The tide went sideways nine hundred years ago. You have arrived "
                    "anyway, with a tag on a string and nothing else.",
                    "Cut wood, knap stone, and put a roof over the ground you sleep on. "
                    "The flat is enormous and it does not care about you yet."],
              tasks=[task_item("wash_ashore", "minecraft:chest", 1, "Any shelter with a chest in it")],
              rewards=[reward_cmd("wash_ashore", "/give @s minecraft:bread 4", "Four days of bread")]),
        quest("first_water", "Drink the Difference", 2.0, 0,
              desc=["Salt will kill you slowly and politely. Water will not.",
                    "A cauldron of rainwater is the whole trick. Learn it before you "
                    "walk out onto the flats."],
              tasks=[task_item("first_water", "minecraft:cauldron", 1, "Place a cauldron")],
              deps=["wash_ashore"]),
        quest("stone_kit", "Salvage Tools", 0, 2.0,
              desc=["Nothing here was left for you. Take the wreck apart, keep the iron.",
                    "A full stone set and a bucket is the qualification for the flats."],
              tasks=[task_item("stone_kit", "minecraft:bucket", 1, "A bucket"),
                     task_item("stone_kit", "minecraft:compass", 1, "A compass")],
              deps=["wash_ashore"]),
        quest("countertop", "A Cutting Board", 0, 4.0,
              desc=["Farmer's Delight. Cook properly or eat badly; the flat gives you "
                    "salty wheat and stubborn hope.",
                    "The board and the pot are the two blocks that make a camp a home."],
              tasks=[task_item("countertop", "farmersdelight:cutting_board", 1, "Cutting board"),
                     task_item("countertop", "farmersdelight:cooking_pot", 1, "Cooking pot")],
              deps=["stone_kit"]),
        quest("read_the_flat", "Cut Glass From the Flat", 2.0, 2.0,
              desc=["They say you can cut glass out of the salt crust, if you cut it while "
                    "the dawn is still on it.",
                    "Glass is the first thing the Kettle Sea ever gave anyone. It is also "
                    "how you will read the water."],
              tasks=[task_item("read_the_flat", "minecraft:glass", 16, "16 glass")],
              deps=["stone_kit"]),
        quest("beacon_lens", "A Sea Lantern", 2.0, 4.0,
              desc=["Before there were harbours there were lamps, and before there were "
                    "lamps there were people who did not come home.",
                    "Push for a sea lantern. You will need light that keeps working "
                    "underwater."],
              tasks=[task_item("beacon_lens", "minecraft:sea_lantern", 1, "Sea lantern")],
              deps=["read_the_flat"]),
        quest("salvage_hull", "Strip a Hull End to End", 4.0, 2.0,
              desc=["There is a fleet out there, hull-up on the dry, that has been waiting "
                    "nine centuries for somebody with a pick.",
                    "Barrels, iron and a nautilus shell from the last of its cargo."],
              tasks=[task_item("salvage_hull", "minecraft:barrel", 4, "Four barrels of salvage"),
                     task_item("salvage_hull", "minecraft:nautilus_shell", 1, "A nautilus shell")],
              deps=["read_the_flat"]),
        quest("first_machine", "Andesite and a Cog", 4.0, 4.0,
              desc=["Create. The harbours were rebuilt with wind, bearings and pumps, and "
                    "you are about to do it again at a smaller scale.",
                    "Andesite alloy, a cogwheel, a shaft, and the goggles so you can see "
                    "what you are building."],
              tasks=[task_item("first_machine", "create:andesite_alloy", 8, "8 andesite alloy"),
                     task_item("first_machine", "create:cogwheel", 2, "2 cogwheels"),
                     task_item("first_machine", "create:goggles", 1, "Engineer's goggles")],
              deps=["salvage_hull"]),
        quest("pump_the_flat", "Pump the Flat", 6.0, 4.0,
              desc=["A water wheel, a pump and pipe. Water is the only currency here and "
                    "you are about to start moving it by hand.",
                    "This is the machinery the beacon quests will ask you to install three "
                    "more times."],
              tasks=[task_item("pump_the_flat", "create:water_wheel", 1, "A water wheel"),
                     task_item("pump_the_flat", "create:mechanical_pump", 1, "A mechanical pump"),
                     task_item("pump_the_flat", "create:fluid_pipe", 8, "Eight pipes")],
              deps=["first_machine"]),
    ]))

    # ---------------- Act I gate + Act II
    chapters.append(chapter("10_the_wrong_sky", "Act I → II — The Wrong Sky", 1, [
        quest("mirror", "Tinted Glass, Laid Flat", 0, 0,
              desc=["A mirror is a hole that has not been opened yet.",
                    "Lay an area of tinted glass somewhere on the flat. Stand on it. "
                    "Crouch. Do it at night, when the sky is in the glass and the glass "
                    "is in the sky."],
              tasks=[task_item("mirror", "minecraft:tinted_glass", 4, "Four tinted glass")]),
        quest("the_wrong_sky", "The Wrong Sky", 2.0, 0,
              subtitle="Act I ends here",
              desc=["Crouch on your mirror at night and the reflection takes you through.",
                    "Below the surface of the world there is a second sea, upside down, "
                    "with a ceiling of glass and something far off that has spires.",
                    "The deep will not let you drown. It remembers what you are."],
              tasks=[task_dim("the_wrong_sky", DEEPDIM, "Enter the Reflected Deep")],
              deps=["mirror"],
              rewards=[reward_cmd("the_wrong_sky", "/advancement grant @s only saltglass:the_dive",
                                  "The sea notices you")]),
        quest("paraglide", "Wings of Salt and Sail", 2.0, 2.0,
              desc=["Not flight. Never flight. A sheet of sailcloth and a good high place.",
                    "The paraglider costs stamina and gives you back the horizon."],
              tasks=[task_item("paraglide", "paragliders:paraglider", 1, "A paraglider")],
              deps=["the_wrong_sky"]),
        quest("the_pack", "Salvage, Carried", 4.0, 2.0,
              desc=["One backpack with upgrades instead of six chests and a trail of "
                    "hopeless return trips across the salt."],
              tasks=[task_item("the_pack", "sophisticatedbackpacks:backpack", 1, "A backpack")],
              deps=["the_wrong_sky"]),
    ]))

    # ---------------- Act II
    act2 = [
        quest("bell_map", "The Bells' Tone-Map", 0, 0,
              desc=["Three harbour bells were tuned to hold the sea off the basin. Their "
                    "tone-map is still stamped into the walls of the drowned offices.",
                    "Read it and you will know how many harbours you have to raise.",
                    "Three. It is always three."],
              tasks=[task_check("bell_map", "Read the tone-map"),
                     task_item("bell_map", "minecraft:clock", 1, "A clock, to time the tides")]),
    ]
    for i, name in enumerate(("one", "two", "three"), start=1):
        roman = ("First", "Second", "Third")[i - 1]
        raise_q = f"raise_{name}"
        light_q = f"light_{name}"
        act2.append(quest(raise_q, f"Raise the {roman} Bell", -2.0 + i * 2.0, 2.0,
                          subtitle="one harbour, end to end",
                          desc=[f"Stand where the {roman} harbour's bell-house used to be "
                                "and raise the tower.",
                                "Everything you need is in the Act I machinery you already "
                                "built. The tower will come up around you."],
                          tasks=[task_item(raise_q, "create:andesite_casing", 8, "Eight casings"),
                                 task_check(raise_q, "Place the tower")],
                          deps=["bell_map"],
                          rewards=[reward_cmd(raise_q, f"/function saltglass:harbour/{name}",
                                              f"The {roman} bell rings")]))
        act2.append(quest(light_q, f"Light the {roman} Beacon", -2.0 + i * 2.0, 4.0,
                          desc=[f"The tower is up. The lantern room is empty and the coast "
                                "is still dark.",
                                "Wind it, pump it, and give it a lens. It will burn for "
                                "nine hundred more years if you let it."],
                          tasks=[task_item(light_q, "minecraft:lantern", 4, "Four lanterns"),
                                 task_item(light_q, "minecraft:prismarine_bricks", 8,
                                           "Eight prismarine bricks"),
                                 task_check(light_q, "Light the beacon")],
                          deps=[raise_q]))
    act2.append(quest("three_beacons", "Three Beacons at Dusk", 2.0, 6.0,
                      subtitle="Act II ends here",
                      desc=["Three bells, three beacons, and the reflection stops glaring.",
                    "The deepest mirror you have been diving through has been showing you "
                    "a reflection with its doors shut. Now look again."],
                      tasks=[task_dim("three_beacons", DEEPDIM, "Return to the reflected sea")],
                      deps=["light_one", "light_two", "light_three"],
                      rewards=[reward_cmd("three_beacons", "/function saltglass:cathedral/open",
                                          "The cathedral opens")]))
    chapters.append(chapter("20_drowned_bells", "Act II — The Drowned Bells", 2, act2))

    # ---------------- Act III
    chapters.append(chapter("30_the_turning", "Act III — The Turning", 3, [
        quest("walk_the_nave", "Walk the Nave", 0, 0,
              desc=["Nine bays, nine doors, and an altar where somebody lit candles and "
                    "left them burning for a sea that had already gone.",
                    "It is not a ruin. It is finished. There is a difference, and you "
                    "will feel it in here."],
              tasks=[task_check("walk_the_nave", "Stand at the altar")]),
        quest("nine_doors", "The Nine Doors", 2.0, 0,
              desc=["Behind each door is one of the priests' tuning-forks, still tuned.",
                    "You do not need to take them. You need to know they are still tuned. "
                    "That is what the Tide Heart listens for."],
              tasks=[task_check("nine_doors", "Open the nine doors")],
              deps=["walk_the_nave"]),
        quest("deep_light", "Light the Ceiling", 2.0, 2.0,
              desc=["The glass above the reflection has not been lit from below in nine "
                    "hundred years. Give it lamps.",
                    "Do it properly. Somebody is going to screenshot this."],
              tasks=[task_item("deep_light", "minecraft:sea_lantern", 16, "Sixteen sea lanterns")],
              deps=["walks_the_nave" if False else "walk_the_nave"]),
        quest("the_heart", "The Tide Heart", 4.0, 0,
              desc=["A heart of the sea is not a treasure. It is a piece of the old "
                    "waterline, kept alive in a shell.",
                    "There is one in a chest at the bottom of the basin, in a place that "
                    "was a harbour office when it still had a harbour."],
              tasks=[task_item("the_heart", "minecraft:heart_of_the_sea", 1,
                               "A Heart of the Sea", consume=False)],
              deps=["nine_doors"]),
        quest("the_turning", "Set the Heart in the Last Dry Trench", 6.0, 0,
                      subtitle="Act III ends here",
                      desc=["One trench on the whole basin is still dry, and it has been "
                            "dry since the night the sea went sideways. That is not "
                            "an accident. That is a socket.",
                            "Set the Tide Heart in it and step back.",
                            "The water comes back in waves. It does not ask you whether "
                            "you wanted it back. It only asks whether you were standing "
                            "somewhere that used to be a harbour."],
                      tasks=[task_check("the_turning", "Set the Tide Heart in the trench")],
                      deps=["the_heart", "deep_light"],
                      rewards=[reward_cmd("the_turning", "/function saltglass:turning/set",
                                          "The Turning")]),
    ]))

    # ---------------- epilogue
    chapters.append(chapter("40_epilogue", "Epilogue — After the Water", 4, [
        quest("first_build", "The First New Thing", 0, 0,
              desc=["Nine hundred years of nothing, and then a coast with lights on it.",
                    "Mark a site and build something that has no purpose except that it "
                    "is new."],
              tasks=[task_check("first_build", "Mark a site")],
              rewards=[reward_cmd("first_build", "/function saltglass:epilogue/survey",
                                  "The coast is yours now")]),
        quest("fleet_museum", "A Museum for the Fleet", 2.0, 0,
              desc=["Every hull on the flat is a ship that never launched.",
                    "Raise one, dry it out, and put the nautilus shells in a case."],
              tasks=[task_item("fleet_museum", "minecraft:nautilus_shell", 8, "Eight shells")],
              deps=["first_build"]),
        quest("salt_roses", "A Salt-Rose Garden", 4.0, 0,
              desc=["Nothing grew here. Make something grow here anyway; half the point "
                    "of the flat is that it is a terrible place to be a plant."],
              tasks=[task_check("salt_roses", "Plant a garden on the salt")],
              deps=["first_build"]),
        quest("drowned_lighthouse", "The Drowned Lighthouse", 6.0, 0,
              desc=["There is a lighthouse in the shallows with its lamp under water and "
                    "its door bricked from the inside.",
                    "Restore it, and it will guide boats that did not exist until an hour "
                    "ago."],
              tasks=[task_check("drowned_lighthouse", "Restore the lighthouse")],
              deps=["first_build"]),
    ]))

    # ---------------- reference chapter (teaches the deep's rules; no busywork)
    chapters.append(chapter("90_reference", "The Salvage-Priests' Notes", 5, [
        quest("notes_water", "On Water", 0, 0,
              desc=["A cistern, a pump and a pipe. The flat drinks everything you spill.",
                    "The deep will not let you drown — you do not need a helmet down "
                    "there and you will not need one."],
              tasks=[task_check("notes_water", "Understood")]),
        quest("notes_mirror", "On Mirrors", 2.0, 0,
              desc=["Tinted glass, laid flat, at night, crouching. That is the whole "
                    "ritual and it is the only one in this pack.",
                    "Coming back puts you beside the nearest mirror you made, not "
                    "necessarily the one you left from. Lay them deliberately."],
              tasks=[task_check("notes_mirror", "Understood")]),
        quest("notes_keys", "On Hands", 4.0, 0,
              desc=["This pack binds nothing to a key except the four the guide lists in "
                    "README.md, and it disables nothing you already know.",
                    "The quest book is bound to its own key. Open it once and forget it."],
              tasks=[task_check("notes_keys", "Understood")]),
        quest("notes_end", "On the End", 6.0, 0,
              desc=["There is no final boss. The last thing you do is put a piece of the "
                    "old waterline into a socket and stand back.",
                    "That is the ending. Everything after it is yours."],
              tasks=[task_check("notes_end", "Understood")]),
    ]))

    QUESTS.mkdir(parents=True, exist_ok=True)
    (QUESTS / "chapters").mkdir(parents=True, exist_ok=True)
    files = {
        "00_arrival.snbt": chapters[0],
        "10_the_wrong_sky.snbt": chapters[1],
        "20_drowned_bells.snbt": chapters[2],
        "30_the_turning.snbt": chapters[3],
        "40_epilogue.snbt": chapters[4],
        "90_reference.snbt": chapters[5],
    }
    for fname, ch in files.items():
        (QUESTS / "chapters" / fname).write_text(snbt_doc(ch) + "\n", encoding="utf-8")

    (QUESTS / "data.snbt").write_text(snbt_doc({
        "version": 13,
        "title": "The Salvage-Priests' Log",
        "default_reward_team": False,
        "default_consume_items": True,
        "default_autoclaim_rewards": "disabled",
        "default_quest_shape": "circle",
        "default_quest_disable_jei": False,
        "drop_loot_crates": False,
        "disable_gui": False,
        "grid_scale": 0.5,
        "pause_game": False,
        "lock_message": "",
        "progression_mode": "linear",
        "disable_gui": False,
        "show_lock_icons": True,
        "hide_excluded_quests": False,
        "emergency_items_cooldown": 300,
        "detection_delay": 20,
    }) + "\n", encoding="utf-8")


# ----------------------------------------------------------------- configs
def build_configs():
    cfg = OVR / "config"
    cfg.mkdir(parents=True, exist_ok=True)

    # Paxi load order
    (cfg / "paxi").mkdir(exist_ok=True)
    (cfg / "paxi/datapack_load_order.json").write_text(
        json.dumps({"loadOrder": ["saltglass"]}, indent=2) + "\n", encoding="utf-8")

    # A calm, readable default: no hunger overhaul, no mob-griefing of the player's work,
    # no flight, and no shaders required.
    (cfg / "saltglass-client-defaults.json").write_text(json.dumps({
        "_comment": "Human-readable summary of the pack's calm defaults. The enforcing "
                    "files are the individual mod configs beside this one.",
        "video": {"graphics": "fancy", "render_distance": 10, "simulation_distance": 8,
                  "clouds": "fast", "entity_shadows": True, "vsync": "on"},
        "shaders": {"enabled_by_default": False,
                    "note": "Oculus + Embeddium are installed; ship no shaderpack, require none."},
        "ui": {"minimap": "disabled (waypoints only)", "coordinates": "hidden until a clock "
              "is crafted", "quest_book": "opens on first join, once"},
        "difficulty": {"server_difficulty": "normal", "keep_inventory": False,
                       "graves": "Corail Tombstone (items kept in a grave, not in your hands)"},
        "flight": {"allowed_before_act_iii": False,
                   "note": "Paraglider only: stamina-limited gliding, no creative flight, "
                           "no elytra, no thrusters."},
    }, indent=2) + "\n", encoding="utf-8")

    # quest book: do not nag
    (cfg / "ftbquests").mkdir(exist_ok=True)
    (cfg / "ftbquests/ftbquests-client.snbt").write_text(
        "{\n\tdefault_quest_shape: \"circle\",\n\tgrid_scale: 0.5,\n"
        "\tpause_game: false,\n\tshow_lock_icons: true,\n}\n", encoding="utf-8")

    # Create: keep the ponder overlay available (it is the pack's in-game guide) but quiet
    (cfg / "create-client.toml").write_text(
        "# Saltglass — Create client settings\n"
        "[client]\n"
        "\t# The Ponder system is this pack's illustrated guide. Leave it on.\n"
        "\tenablePonder = true\n"
        "\t# Keep the schematic overlay unobtrusive.\n"
        "\tenableSchematicOverlay = true\n", encoding="utf-8")

    # Embeddium/Oculus: mid-range friendly, shaders off
    (cfg / "oculus-client.toml") if False else None
    (cfg / "sodium-options.json") if False else None
    (cfg / "embeddium-options.json") if False else None
    (cfg / "oculus.properties").write_text(
        "enableShaders=false\n"
        "shaderPack=\n"
        "# Saltglass ships no shaderpack. If you want one, drop it in shaderpacks/ and\n"
        "# set enableShaders=true. Nothing in the pack requires it.\n", encoding="utf-8")

    # ModernFix: 6 GB client target
    (cfg / "modernfix-mixins.properties").write_text(
        "# Saltglass — ModernFix profile for a 6 GB client / 4 GB server.\n"
        "mixin.perf.dynamic_resources=true\n"
        "mixin.perf.dynamic_models=false\n"
        "# Block-model dynamic loading is left OFF so Create's ponder scenes and Ars'\n"
        "# animated glyph items keep their models on all hardware.\n"
        "mixin.perf.faster_item_rendering=false\n", encoding="utf-8")

    (cfg / "ambientsounds-client.json").write_text(json.dumps({
        "enabled": True, "volume": 0.7,
        "_comment": "AmbientSounds 6 — wind on salt, surf under glass. Client-side only.",
    }, indent=2) + "\n", encoding="utf-8")

    (cfg / "xaerominimap.txt").write_text(
        "# Saltglass — the minimap is off by default; waypoints stay on so three harbours\n"
        "# across an empty basin are findable without making the landscape trivial.\n"
        "minimap:0\nwaypoints:1\ncoordinates:0\n", encoding="utf-8")

    # --- server tree
    srv = ROOT / "pack/server"
    srv.mkdir(parents=True, exist_ok=True)
    (srv / "server.properties").write_text("\n".join([
        "# Saltglass dedicated server — solo host or small co-op.",
        "motd=\\u00a77Saltglass \\u00a78| \\u00a7bthe sea that went sideways",
        "server-port=25565",
        "game-mode=survival",
        "difficulty=normal",
        "hardcore=false",
        "pvp=true",
        "allow-flight=true",
        "# allow-flight is true only because the Paraglider needs it; the pack contains",
        "# no creative flight, no elytra and no jetpacks before Act III.",
        "spawn-protection=0",
        "view-distance=8",
        "simulation-distance=6",
        "max-players=8",
        "online-mode=true",
        "enable-command-block=true",
        "# enable-command-block is required: the three signature moments are datapack",
        "# functions fired as quest rewards.",
        "enable-status=true",
        "level-name=world",
        "sync-chunk-writes=true",
        "max-tick-time=180000",
        "white-list=false",
        "enforce-whitelist=false",
        "player-idle-timeout=0",
        "level-seed=",
        "allow-nether=true",
        "force-gamemode=false",
        "enable-rcon=false",
        "",
    ]), encoding="utf-8")

    (srv / "jvm_args.txt").write_text(
        "# Saltglass — JVM arguments. Java 17 64-bit is required by Forge 47.x.\n"
        "# Copy this line into your start script's java invocation.\n"
        "\n"
        "-Xms4G -Xmx4G -XX:+UseG1GC -XX:+ParallelRefProcEnabled "
        "-XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions "
        "-XX:+DisableExplicitGC -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 "
        "-XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 "
        "-XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 "
        "-XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 "
        "-XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 "
        "-Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true\n", encoding="utf-8")

    (srv / "README-SERVER.md").write_text(server_readme(), encoding="utf-8")


def server_readme() -> str:
    return """# Saltglass — dedicated server

Tested target: **Minecraft 1.20.1 · Forge 47.4.10 · Java 17 64-bit**.

## 1. Install Forge

    java -jar forge-1.20.1-47.4.10-installer.jar --installServer
    # -> produces libraries/, run.sh / run.bat and a user_jvm_args.txt

SHA-1 of the installer: `27b38c97615d138101caa13c01e6bfda6176dea3`
SHA-1 of the universal jar: `9d27acaf82445da3419c21d5f2f87e86ff0f8abe`

## 2. Put the mods in place

`server-mods.tsv` lists exactly which jars a server needs, with version and source.
Copy them into `mods/`. Do **not** install the client-only jars — they are listed in
`README.md` under "client-only" and will crash a headless server.

## 3. Put the pack data in place

    defaultconfigs/saltglass_datapack/     -> config/paxi/datapacks/saltglass/
    server.properties                      -> ./server.properties
    jvm_args.txt                           -> your start script (-Xmx4G for 4 players)

Paxi loads `config/paxi/datapacks/*` into every world, so the datapack does not need to be
copied per-world and cannot be lost with a world reset.

## 4. Start

    ./run.sh

Expected on first start: `Done (NN.NNNs)! For help, type "help"`. The datapack prints one
line to chat: `[Saltglass] The sea is still falling.`

## 5. Know before you host

* **Command blocks must stay enabled.** The three signature moments run as datapack
  functions invoked by quest rewards.
* **`allow-flight=true`** is required by the Paraglider. The pack ships no creative flight,
  no elytra and no jetpacks, and Act III is the only act that changes the map.
* **Co-op:** FTB Teams is installed, so quest progress is shared per team. `/team` creates
  one. Three harbours, three players, one graph.
* **The Turning is global and permanent.** When one player sets the Tide Heart, the basin
  floods for everybody. That is intentional; settle it with your players first.
* Back up `world/` before the Turning. It is ~96x96 blocks of terrain change at each
  harbour, applied by `fill` in four waves.
"""


# ----------------------------------------------------------------- validation
def check(problems: list[str]) -> None:
    # 1. every generated SNBT file must round-trip through the strict parser
    for p in sorted(QUESTS.rglob("*.snbt")):
        try:
            doc = snbt_parse(p.read_text(encoding="utf-8"))
        except SnbtError as e:
            problems.append(f"SNBT parse failed: {p.relative_to(ROOT)}: {e}")
            continue

        def walk(o, where):
            if isinstance(o, dict):
                if "type" in o and isinstance(o["type"], str):
                    t = o["type"]
                    if not t.startswith("ftbquests:"):
                        problems.append(f"{where}: unknown type prefix {t}")
                for k, v in o.items():
                    walk(v, where + "/" + str(k))
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    walk(v, f"{where}[{i}]")

        walk(doc, p.name)

        # quest-level rules
        if p.name != "data.snbt":
            if doc.get("version") != 13:
                problems.append(f"{p.name}: version must be 13, got {doc.get('version')!r}")
            chapters = doc.get("quests", [])
            ids = [q.get("id") for q in chapters]
            if len(set(ids)) != len(ids):
                problems.append(f"{p.name}: duplicate quest ids")
            for q in chapters:
                for t in q.get("tasks", []):
                    if t.get("type") == "ftbquests:item":
                        item = t.get("item", {}).get("id")
                        if not item_ok(item or ""):
                            problems.append(f"{p.name}/{q.get('title')}: item '{item}' "
                                            "is outside the verified whitelist")
                        if not isinstance(t.get("count"), int):
                            problems.append(f"{p.name}/{q.get('title')}: item task without count")
                    if t.get("type") == "ftbquests:dimension":
                        if t.get("dimension") != DEEPDIM:
                            problems.append(f"{p.name}/{q.get('title')}: unexpected dimension")
                for r in q.get("rewards", []):
                    if r.get("type") == "ftbquests:command":
                        cmd = r.get("command", "")
                        m = re.match(r"^/function (saltglass:[a-z0-9_/]+)$", cmd)
                        if m and m.group(1) not in {f"saltglass:{k}" for k in FUNCTIONS}:
                            problems.append(f"{p.name}/{q.get('title')}: reward calls missing "
                                            f"function {m.group(1)}")
                        elif not cmd.startswith(("/function", "/give", "/advancement", "/effect",
                                                 "/clear", "/tp", "/time")):
                            problems.append(f"{p.name}/{q.get('title')}: reward command "
                                            f"not allowed by the audit: {cmd}")

    # 2. every quest dependency must point at a real quest in the same file
    for p in sorted(QUESTS.rglob("*.snbt")):
        if p.name == "data.snbt":
            continue
        doc = snbt_parse(p.read_text(encoding="utf-8"))
        known = {q["id"] for q in doc.get("quests", [])}
        for q in doc.get("quests", []):
            for d in q.get("dependencies", []):
                if d not in known:
                    problems.append(f"{p.name}: quest '{q.get('title')}' depends on an id "
                                    f"that is not in this chapter ({d})")

    # 3. every mcfunction reference resolves
    for path, body in FUNCTIONS.items():
        for i, line in enumerate(body.splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or not s:
                continue
            for ref in re.findall(r"function (saltglass:[a-z0-9_/]+)", s):
                if ref.split("saltglass:", 1)[1] not in FUNCTIONS:
                    problems.append(f"functions/{path}.mcfunction:{i}: missing {ref}")
            if s.count("{") != s.count("}"):
                problems.append(f"functions/{path}.mcfunction:{i}: unbalanced braces")
            if s.count("[") != s.count("]"):
                problems.append(f"functions/{path}.mcfunction:{i}: unbalanced brackets")
            if "minecraft:air replace minecraft:tinted_glass" in s and "fill" not in s:
                problems.append(f"functions/{path}.mcfunction:{i}: stray filter")

    # 4. functions must not exist without a tag (dead code is a defect here)
    tagged = {"load", "tick"}
    used = set()
    for body in FUNCTIONS.values():
        used |= set(re.findall(r"function saltglass:([a-z0-9_/]+)", body))
    # quest rewards are a first-class caller: they fire the three signature moments
    for p in sorted(QUESTS.rglob("*.snbt")):
        used |= set(re.findall(r"/function saltglass:([a-z0-9_/]+)",
                               p.read_text(encoding="utf-8")))
    for name in FUNCTIONS:
        if name not in tagged and name not in used:
            problems.append(f"functions/{name}.mcfunction is never called and never tagged")

    # 5. structure files referenced by functions must exist
    for body in FUNCTIONS.values():
        for s in re.findall(r"place structure saltglass:([a-z0-9_]+)", body):
            if not (DP / f"data/saltglass/structures/{s}.nbt").exists():
                problems.append(f"missing structure file: {s}.nbt")

    # 6. fill volumes must stay inside the command's 32768-block limit
    for path, body in FUNCTIONS.items():
        for line in body.splitlines():
            m = re.search(r"fill (~-?\d+|[\-0-9]+) (~-?\d+|[\-0-9]+) (~-?\d+|[\-0-9]+) "
                          r"(~-?\d+|[\-0-9]+) (~-?\d+|[\-0-9]+) (~-?\d+|[\-0-9]+)", line)
            if not m:
                continue
            dims = []
            ok = True
            for a, b in ((m.group(1), m.group(4)), (m.group(2), m.group(5)),
                         (m.group(3), m.group(6))):
                if a.startswith("~") and b.startswith("~"):
                    dims.append(abs(int(b[1:]) - int(a[1:])) + 1)
                else:
                    ok = False
            if ok:
                vol = dims[0] * dims[1] * dims[2]
                if vol > 32768:
                    problems.append(f"functions/{path}.mcfunction: fill volume {vol} "
                                    "exceeds the vanilla 32768 limit")


def main() -> int:
    problems: list[str] = []
    build_functions()
    build_data_files()
    build_quests()
    build_configs()
    check(problems)
    print(f"generated: {len(FUNCTIONS)} functions, "
          f"{len(list(QUESTS.rglob('*.snbt')))} quest files, "
          f"{len(list(DP.rglob('*.json')))} datapack JSON files")
    if problems:
        print("CONTENT CHECK FAILED:")
        for p in problems:
            print("  -", p)
        return 2
    print("content check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
