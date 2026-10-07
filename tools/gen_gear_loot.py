#!/usr/bin/env python3
"""Generate loot for the modded combat gear added to the pack.

Reads the curated lists below, checks every item against balance/gear-tier-audit.csv so an item can only
drop in the tier its stats belong to, then writes:
  overrides/kubejs/data/apotheosis/affix_loot_entries/<tier>/<mod>_<item>.json   (new affix base items)
  overrides/kubejs/data/ddo/loot_tables/gear/<tier>.json                         (chest-ready gear tables)

Tiers follow the pack: overworld = iron-class, nether = diamond-class, end = netherite-class (plus a few
mythic extras). Weights keep the original vanilla entries (80 / 35 / 12) the larger share of drops.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "balance" / "gear-tier-audit.csv"
AFFIX = ROOT / "overrides" / "kubejs" / "data" / "apotheosis" / "affix_loot_entries"
TABLES = ROOT / "overrides" / "kubejs" / "data" / "ddo" / "loot_tables" / "gear"
SCRIPT = ROOT / "overrides" / "kubejs" / "server_scripts" / "gear_loot.js"

# Per tier: audit tier the items must belong to, Apotheosis rarity range / weight / quality, chest enchant levels.
TIERS = {
    "overworld": {"audit": 1, "rarity": ("common", "rare"),
                  "weight": 10, "quality": 2.0, "enchant": (8, 18)},
    "nether": {"audit": 2, "rarity": ("rare", "epic"),
               "weight": 5, "quality": 8.0, "enchant": (18, 30)},
    "end": {"audit": 3, "rarity": ("epic", "mythic"),
            "weight": 3, "quality": 18.0, "enchant": (28, 40)},
}
DIMENSIONS = {"overworld": "minecraft:overworld", "nether": "minecraft:the_nether", "end": "minecraft:the_end"}

GEAR = {
    "overworld": [
        # warriors
        "magistuarmory:iron_bastardsword", "magistuarmory:steel_morgenstern", "born_in_chaos_v1:great_reaper_axe",
        # rangers / rogues
        "samurai_dynasty:kama", "samurai_dynasty:sai", "magistuarmory:longbow",
        # mages
        "wom:stone_staff", "wizards:staff_fire", "wizards:staff_frost",
        # RPG Series (Paladins & Priests, Rogues & Warriors, Archers)
        "paladins:iron_mace", "paladins:iron_claymore", "rogues:iron_dagger", "rogues:iron_glaive", "archers:iron_spear",
        # chest pieces
        "magistuarmory:crusader_chestplate", "samurai_dynasty:iron_samurai_chestplate",
        "samurai_dynasty:steel_ninja_chestplate", "soulsweapons:soul_robes_chestplate",
        "paladins:paladin_armor_chest", "rogues:warrior_armor_chest", "rogues:assassin_armor_chest",
        "wizards:wizard_robe_chest", "archers:ranger_armor_chest",
    ],
    "nether": [
        "magistuarmory:diamond_katzbalger", "magistuarmory:diamond_estoc", "simplyswords:diamond_halberd",
        "born_in_chaos_v1:sharpened_dark_metal_sword", "magistuarmory:heavy_crossbow",
        "magistuarmory:gothic_chestplate", "samurai_dynasty:blue_samurai_chestplate",
        "born_in_chaos_v1:spiny_shell_armor_chestplate", "soulsweapons:forlorn_chestplate",
        "paladins:diamond_claymore", "paladins:diamond_mace", "rogues:diamond_dagger", "rogues:diamond_glaive",
        "paladins:crusader_armor_chest", "rogues:berserker_armor_chest",
    ],
    "end": [
        "samurai_dynasty:katana", "samurai_dynasty:odachi", "magistuarmory:netherite_bastardsword",
        "magistuarmory:netherite_estoc", "magistuarmory:netherite_katzbalger",
        "samurai_dynasty:netherite_samurai_chestplate", "magistuarmory:maximilian_chestplate",
        "paladins:netherite_claymore", "paladins:netherite_mace", "rogues:netherite_dagger", "rogues:netherite_sickle",
        "wizards:staff_netherite_fire", "wizards:staff_netherite_frost",
        "wizards:netherite_fire_robe_chest", "archers:netherite_ranger_armor_chest",
    ],
}
# Chests that receive each tier's gear table, as (regex over the full loot table id, chance of one extra roll).
# Resolved against the live server's loot table list (--loot-tables) because KubeJS modifies exact ids only.
INJECT = {
    "overworld": (0.20, [r"dungeons_arise:chests/.*", r"betterdungeons:.*", r"betterstrongholds:chests/.*",
                         r"idas:chests/.*", r"betterdeserttemples:chests/.*", r"betterjungletemples:chests/.*",
                         r"betteroceanmonuments:chests/.*", r"dungeoncrawl:chests/.*", r"paladins:chests/.*", r"rogues:chests/.*",
                         r"wizards:chests/.*", r"archers:chests/.*",
                         # Dungeons and Taverns reuses vanilla chest tables for its strongholds, mansions and ruins
                         r"minecraft:chests/(stronghold_.*|simple_dungeon|abandoned_mineshaft|illager_mansion/.*"
                         r"|desert_pyramid|jungle_temple|woodland_mansion|pillager_outpost|underwater_ruin_.*"
                         r"|shipwreck_.*|village/.*)"]),
    "nether": (0.20, [r"betterfortresses:chests/.*", r"netherexp:(chests|brazier_chest)/.*",
                      r"incendium:(lab|pipeline|reactor|sanctum|quartz_flats)/.*(treasure|rare|common_loot|piglin_loot).*",
                      r"minecraft:chests/(nether_bridge|bastion_.*|ruined_portal|ancient_city.*)"]),
    "end": (0.25, [r"minecraft:chests/end_city_treasure", r"mes:(end_.*|mega_ship_treasure)", r"cataclysm:chests/.*",
                   r"bosses_of_mass_destruction:chests/.*", r"mowziesmobs:chests/.*"]),
}
# Beyond-netherite weapons: rare mythic extras in the End.
MYTHIC = ["samurai_dynasty:katana_netherite", "samurai_dynasty:wakizashi_netherite"]
# Staves, robes and spears get their strength from spell power or range, which melee damage per second and armor
# points cannot see (the audit files them all under tier 1). Their loot tier follows the material in the item id.
MATERIAL_TIERED = {"wizards:staff_fire", "wizards:staff_frost", "wizards:wizard_robe_chest",
                   "wizards:staff_netherite_fire", "wizards:staff_netherite_frost",
                   "wizards:netherite_fire_robe_chest", "archers:ranger_armor_chest",
                   "archers:netherite_ranger_armor_chest", "archers:iron_spear", "wom:stone_staff"}
# Bows and crossbows carry no attack attributes, so the stats dump (and the audit) cannot tier them.
UNAUDITED = {"magistuarmory:longbow", "magistuarmory:heavy_crossbow"}


def load_audit():
    with AUDIT.open(encoding="utf-8") as source:
        return {row["item"]: int(row["tier"]) for row in csv.DictReader(source)}


def validate(audit):
    problems = []
    for tier, items in GEAR.items():
        for item in items:
            if item in UNAUDITED:
                continue
            if item not in audit:
                problems.append(f"{item}: not in the audit worksheet")
            elif item in MATERIAL_TIERED:
                word = "netherite" if "netherite" in item else "diamond" if "diamond" in item else None
                if (word == "netherite") != (tier == "end") or (word == "diamond") != (tier == "nether"):
                    problems.append(f"{item}: material in the id does not match the {tier} tier")
            elif audit[item] != TIERS[tier]["audit"]:
                problems.append(f"{item}: audited tier {audit[item]} but listed under {tier}")
    for item in MYTHIC:
        if audit.get(item) != 4:
            problems.append(f"{item}: mythic extras must be audit tier 4, got {audit.get(item)}")
    if problems:
        raise SystemExit("gear loot lists disagree with the audit:\n  " + "\n  ".join(problems))


def affix_entry(item, tier, weight, quality):
    low, high = TIERS[tier]["rarity"]
    return {
        "dimensions": [DIMENSIONS[tier]],
        "min_rarity": f"apotheosis:{low}", "max_rarity": f"apotheosis:{high}",
        "weight": weight, "quality": quality, "stack": {"item": item, "count": 1},
    }


def chest_table(tier, items):
    low, high = TIERS[tier]["enchant"]
    entries = [{
        "type": "minecraft:item", "name": item, "weight": 1,
        "functions": [{"function": "minecraft:enchant_with_levels", "levels": {"min": low, "max": high}, "treasure": True}],
    } for item in items]
    return {"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": entries}]}


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def write_script(table_ids):
    lines = ["// Generated by tools/gen_gear_loot.py. Adds the tiered gear tables to dungeon chests.",
             "// KubeJS modifies exact loot table ids, so the targets are listed out; re-run the tool after adding structure mods.",
             "// genericLootTables, not chestLootTables: the chest event silently prefixes `chests/` to every id it is given.",
             "const GEAR_INJECTIONS = ["]
    total = 0
    for tier, (chance, patterns) in INJECT.items():
        rx = [re.compile(p) for p in patterns]
        targets = sorted(t for t in table_ids if any(r.fullmatch(t) for r in rx))
        total += len(targets)
        lines += ["  {", f'    table: "ddo:gear/{tier}", chance: {chance}, targets: [']
        lines += [f'      "{t}",' for t in targets]
        lines += ["    ]", "  },"]
    lines += ["]", "",
              "ServerEvents.genericLootTables(event => {",
              "  let injected = 0",
              "  GEAR_INJECTIONS.forEach(injection => {",
              "    injection.targets.forEach(id => {",
              "      event.modify(id, loot => loot.addPool(pool => {",
              "        pool.setBinomialRolls(1, injection.chance)",
              "        pool.addLootTable(injection.table)",
              "      }))",
              "      injected++",
              "    })",
              "  })",
              "  console.info(`gear loot: injected into ${injected} chest tables`)",
              "})", ""]
    SCRIPT.write_text("\n".join(lines), encoding="utf-8")
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--loot-tables", help="JSON from a server dump with a lootTables list; regenerates gear_loot.js")
    args = parser.parse_args()
    validate(load_audit())
    for generated in (TABLES,):
        shutil.rmtree(generated, ignore_errors=True)
    # Remove only the entries this script owns (named <mod>_<item>), never the original vanilla ones.
    for tier in TIERS:
        for old in (AFFIX / tier).glob("*_*.json"):
            if not old.name.startswith(("iron_", "diamond_", "netherite_")):
                old.unlink()
    count = 0
    for tier, items in GEAR.items():
        cfg = TIERS[tier]
        for item in items:
            ns, _, name = item.partition(":")
            write(AFFIX / tier / f"{ns}_{name}.json", affix_entry(item, tier, cfg["weight"], cfg["quality"]))
            count += 1
        write(TABLES / f"{tier}.json", chest_table(tier, items))
    end_cfg = TIERS["end"]
    for item in MYTHIC:
        ns, _, name = item.partition(":")
        write(AFFIX / "end" / f"{ns}_{name}.json", affix_entry(item, "end", 1, 30.0))
        count += 1
    # The End chest table also carries the mythic extras, very rarely.
    end_table = chest_table("end", GEAR["end"])
    low, high = end_cfg["enchant"]
    end_table["pools"].append({"rolls": 1, "entries": [{
        "type": "minecraft:item", "name": item, "weight": 1,
        "functions": [{"function": "minecraft:enchant_with_levels", "levels": {"min": high, "max": high + 5}, "treasure": True}],
    } for item in MYTHIC] + [{"type": "minecraft:empty", "weight": 9}]})
    write(TABLES / "end.json", end_table)
    print(f"wrote {count} affix entries and {len(TIERS)} gear loot tables")
    if args.loot_tables:
        ids = json.load(open(args.loot_tables, encoding="utf-8"))["lootTables"]
        print(f"wrote {SCRIPT.relative_to(ROOT)}: {write_script(ids)} target chest tables")


if __name__ == "__main__":
    main()
