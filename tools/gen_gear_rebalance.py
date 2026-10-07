#!/usr/bin/env python3
"""Audit modded combat gear against the pack's iron / diamond / netherite tiers.

Inputs
  --stats  JSON list of {"id", "dur", "s": {"SLOT|attribute": amount}} dumped from a running server
           (ForgeRegistries.ITEMS -> Item#getDefaultAttributeModifiers for each equipment slot).
  --mods   directory holding the pack's mod jars (recipes are read straight from the jars).

Outputs
  balance/gear-tier-audit.csv                       one row per gear recipe (plus loot-only items)
  overrides/kubejs/server_scripts/recipes.js        recipe swaps and removals

Rules (the pack's tiers: overworld = iron, nether = diamond, end = netherite)
  weapon power = damage per second, (1 + attack_damage) * (4 + attack_speed), the vanilla formula.
  armor power  = armor + 0.75 * toughness per slot, compared with the vanilla piece for that slot.
  A craftable item may not outclass the tier of its raw materials:
    one tier over  -> swap the main material up a tier, 1:1 (metal -> diamond, diamond -> netherite),
                      the same scaling vanilla uses from an iron to a diamond to a netherite tool;
    two or more    -> crafting removed; the item is loot-only.
  Smithing upgrades and recipes that need a unique modded material (boss drops) are already gated and
  are left alone. Cataclysm and Iron's Spells gear is out of scope: boss materials and the Mage's casting set.
"""

from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = {"soulsweapons", "samurai_dynasty", "magistuarmory", "wom", "simplyswords", "born_in_chaos_v1",
         "paladins", "rogues", "wizards", "archers", "l2weaponry", "l2complements", "immersive_armors", "alexsmobs", "netherexp"}
WEAPON_CAPS = (10.5, 12.3, 14.1)  # iron 9.6 / diamond 11.2 / netherite 12.8 damage per second, plus ~10 percent
VANILLA_PIECE = {  # armor + 0.75 * toughness for iron / diamond / netherite
    "HEAD": (2.0, 4.5, 5.25), "CHEST": (6.0, 9.5, 10.25), "LEGS": (5.0, 7.5, 8.25), "FEET": (2.0, 4.5, 5.25)}
VANILLA_NS = ("minecraft", "forge", "c")
PLAIN_MOD = re.compile(  # generic materials from other mods; anything else (moonstone, cursium...) is a unique drop
    r"^((small|medium|large|heavy|light)_)?(iron|gold|golden|copper|steel|bronze|silver|tin|lead|chain|chainmail|netherite)(_ingot|_nugget|_block|_plate)?$"
    r"|(^|[_/])(plank|planks|stick|sticks|leather|string|rope|cloth|wool|bone|plate|plates|nugget|nuggets)([_/]|$)")
ACCESSORY = re.compile(r"earring|(^|_)rings?($|_)|amulet|necklace|charm|belt|glove|pendant|bracelet|talisman")
METALS = ("steel", "iron", "bronze", "silver", "copper", "gold", "tin", "lead")  # tie-break order
GATED_TYPES = ("smithing_transform", "smithing_trim", "smithing_reroll", "weapon_fusion")


def num(rec, key):
    value = rec["s"].get(key)
    try:
        return float(str(value).split("*")[0]) if value is not None else None
    except ValueError:
        return None


def classify(rec):
    """-> (kind, power, tier) or None when the item has no combat attributes."""
    for slot in VANILLA_PIECE:
        armor = num(rec, f"{slot}|generic.armor")
        if armor is not None:
            power = armor + 0.75 * (num(rec, f"{slot}|generic.armor_toughness") or 0)
            tier = next((i + 1 for i, v in enumerate(VANILLA_PIECE[slot]) if power <= v + 0.55), 4)
            return f"armor:{slot.lower()}", round(power, 2), tier
    damage, speed = num(rec, "MAINHAND|generic.attack_damage"), num(rec, "MAINHAND|generic.attack_speed")
    if damage is None or speed is None or damage <= 0:
        return None
    if damage > 100:
        return "weapon", round(damage, 2), 4
    power = (1 + damage) * (4 + speed)
    return "weapon", round(power, 2), next((i + 1 for i, cap in enumerate(WEAPON_CAPS) if power <= cap), 4)


def collect(node, out):
    if isinstance(node, list):
        for item in node:
            collect(item, out)
    elif isinstance(node, dict):
        for key in ("item", "tag"):
            if key in node:
                out.append(("#" if key == "tag" else "") + node[key].lower())
        for value in node.values():
            if isinstance(value, (list, dict)):
                collect(value, out)


def slots_used(recipe):
    """Ingredient reference -> number of crafting slots it occupies."""
    counts = collections.Counter()
    if "pattern" in recipe:
        used = collections.Counter(ch for row in recipe["pattern"] for ch in row if ch != " ")
        for ch, n in used.items():
            refs = []
            collect(recipe["key"].get(ch, {}), refs)
            for ref in refs[:1]:
                counts[ref] += n
    else:
        for ingredient in recipe.get("ingredients", []):
            refs = []
            collect(ingredient, refs)
            for ref in refs[:1]:
                counts[ref] += 1
    return counts


def material_tier(refs, gear=None):
    """Tier of the raw materials. An audited gear piece used as an ingredient (a lower armor piece upgraded with
    steel plates) counts at that piece's own tier, not as a unique material."""
    tier, special = 1, False
    for ref in refs:
        ns, _, path = ref.lstrip("#").partition(":")
        if gear and ref in gear:
            tier = max(tier, gear[ref][2])
        elif ns in VANILLA_NS and "netherite" in path:
            tier = max(tier, 3)
        elif ns in VANILLA_NS and "diamond" in path:
            tier = max(tier, 2)
        elif ns not in VANILLA_NS and not PLAIN_MOD.search(path):
            special = True
    return tier, special


def swap_target(ref, item_tier):
    """Replacement for the primary material when lifting it one tier."""
    path = ref.lstrip("#").partition(":")[2]
    if item_tier == 2:
        return "minecraft:diamond"
    if "diamond" in path:  # lifting diamond to netherite
        tail = path.split("diamond", 1)[1]
        return "minecraft:netherite_ingot" if tail in ("", "s", "_ingot", "/diamond") or path.startswith("gems") \
            else "minecraft:netherite" + tail
    return None


def primary_metal(counts, item_tier):
    candidates = []
    for ref, n in counts.items():
        path = ref.lstrip("#").partition(":")[2]
        if item_tier == 2 and any(m in path for m in METALS) and "diamond" not in path:
            candidates.append((n, -min(METALS.index(m) for m in METALS if m in path), ref))
        elif item_tier == 3 and "diamond" in path:
            candidates.append((n, 0, ref))
    return max(candidates)[2] if candidates else None


def load_recipes(mods_dir):
    found = collections.defaultdict(list)
    for jar in sorted(glob.glob(f"{mods_dir}/*.jar")):
        archive = zipfile.ZipFile(jar)
        for name in archive.namelist():
            match = re.match(r"data/([^/]+)/recipes?/(.*)\.json$", name)
            if not match:
                continue
            try:
                recipe = json.loads(archive.read(name))
            except ValueError:
                continue
            result = recipe.get("result")
            out = result.get("item") if isinstance(result, dict) else result if isinstance(result, str) else None
            if out:
                found[out].append((f"{match.group(1)}:{match.group(2)}", recipe))
    return found


def audit(stats, recipes):
    rows, gear = [], {}
    for rec in stats:
        item = rec["id"]
        if item.split(":")[0] not in SCOPE or ACCESSORY.search(item.partition(":")[2]):
            continue
        info = classify(rec)
        if info:
            gear[item] = info
    for item, (kind, power, tier) in sorted(gear.items()):
        mod = item.split(":")[0]
        entries = recipes.get(item, [])
        if not entries:
            rows.append([item, mod, kind, power, tier, "", "", "", "loot-only", ""])
        for rid, recipe in entries:
            rtype = recipe.get("type", "").split(":")[-1]
            refs = []
            collect({k: v for k, v in recipe.items() if k in ("key", "ingredients", "ingredient", "base", "addition", "template", "input")}, refs)
            mat, special = material_tier(refs, gear)
            action, detail = "keep", ""
            if rtype.startswith(GATED_TYPES) or special:
                action = "keep"
            elif tier > mat:
                gap = tier - mat
                counts = slots_used(recipe)
                primary = primary_metal(counts, tier) if gap == 1 and tier in (2, 3) else None
                target = swap_target(primary, tier) if primary else None
                if target:
                    action, detail = "swap", f"{primary}>{target}"
                else:
                    action = "remove"
            rows.append([item, mod, kind, power, tier, rid, rtype, mat, action, detail])
    return rows


def write_csv(rows):
    path = ROOT / "balance" / "gear-tier-audit.csv"
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["item", "mod", "kind", "power", "tier", "recipe_id", "recipe_type", "material_tier", "action", "detail"])
        writer.writerows(rows)
    return path


def write_script(rows):
    swaps = [(r[5], *r[9].split(">")) for r in rows if r[8] == "swap"]
    removals = sorted({r[5] for r in rows if r[8] == "remove"})
    lines = [
        "// Generated by tools/gen_gear_rebalance.py from balance/gear-tier-audit.csv. Do not edit by hand.",
        "// A craftable item may not outclass the tier of its raw materials (iron < diamond < netherite).",
        "const GEAR_SWAPS = [",
        *[f'  ["{rid}", "{old}", "{new}"],' for rid, old, new in sorted(swaps)],
        "]",
        "",
        "const GEAR_REMOVALS = [",
        *[f'  "{rid}",' for rid in removals],
        "]",
        "",
        "ServerEvents.recipes(event => {",
        "  GEAR_SWAPS.forEach(swap => event.replaceInput({ id: swap[0] }, swap[1], swap[2]))",
        "  GEAR_REMOVALS.forEach(id => event.remove({ id: id }))",
        "  console.info(`gear rebalance: ${GEAR_SWAPS.length} swaps, ${GEAR_REMOVALS.length} removals`)",
        "})",
        "",
    ]
    path = ROOT / "overrides" / "kubejs" / "server_scripts" / "recipes.js"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path, len(swaps), len(removals)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stats", required=True)
    parser.add_argument("--mods", required=True)
    args = parser.parse_args()
    rows = audit(json.load(open(args.stats, encoding="utf-8")), load_recipes(args.mods))
    csv_path = write_csv(rows)
    js_path, swaps, removals = write_script(rows)
    tally = collections.Counter(r[8] for r in rows)
    print(f"{csv_path.relative_to(ROOT)}: {len(rows)} rows {dict(tally)}")
    print(f"{js_path.relative_to(ROOT)}: {swaps} swaps, {removals} removals")


if __name__ == "__main__":
    main()
