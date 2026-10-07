import csv
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "mods.lock.json"
AUDIT = ROOT / "balance" / "gear-tier-audit.csv"
KUBEJS = ROOT / "overrides" / "kubejs"
MOD_CAP = 150
ENV_VALUES = {"required", "optional", "unsupported"}


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LockAndBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.mods = cls.lock["mods"] + cls.lock["curseforge_mods"]

    def test_mod_count_stays_under_cap(self):
        self.assertLessEqual(len(self.mods), MOD_CAP)

    def test_no_duplicate_projects_or_files_and_all_dependencies_present(self):
        ids = [m["project_id"] for m in self.lock["mods"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len({m["filename"] for m in self.mods}), len(self.mods))
        needed = {d for m in self.lock["mods"] for d in m["required_dependencies"]}
        self.assertEqual(needed - set(ids), set())

    def test_every_pin_is_checksummed(self):
        for mod in self.mods:
            with self.subTest(mod=mod["name"]):
                self.assertEqual(len(mod["sha1"]), 40)
                self.assertEqual(len(mod["sha512"]), 128)

    def test_non_release_pins_are_documented(self):
        for mod in self.lock["mods"]:
            if re.search(r"(beta|alpha)", mod.get("release_filter_exception", ""), re.I):
                self.assertGreater(len(mod["release_filter_exception"]), 40, mod["name"])

    def test_env_values_are_valid_and_client_only_mods_stay_off_the_server(self):
        build = load_tool("build_pack")
        manifest = build.build_manifest(self.lock)
        by_path = {f["path"]: f["env"] for f in manifest["files"]}
        for mod in self.mods:
            env = by_path[f"mods/{mod['filename']}"]
            self.assertTrue({env["client"], env["server"]} <= ENV_VALUES, mod["name"])
            if "env" in mod:
                self.assertEqual(env, mod["env"], mod["name"])
        for slug in ("embeddium", "entityculling", "oculus", "mouse-tweaks"):
            mod = next(m for m in self.lock["mods"] if m["slug"] == slug)
            self.assertEqual(by_path[f"mods/{mod['filename']}"]["server"], "unsupported", slug)
        for mod in self.mods:  # singleplayer runs an integrated server: anything the server needs, the client install needs
            env = by_path[f"mods/{mod['filename']}"]
            if env["server"] != "unsupported":
                self.assertNotEqual(env["client"], "unsupported", mod["name"])
        for slug in ("noisium", "async-locator"):  # server-side mods must still install in singleplayer
            mod = next(m for m in self.lock["mods"] if m["slug"] == slug)
            self.assertNotEqual(by_path[f"mods/{mod['filename']}"]["client"], "unsupported", slug)


class GearBalance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with AUDIT.open(encoding="utf-8") as source:
            cls.rows = list(csv.DictReader(source))
        cls.script = (KUBEJS / "server_scripts" / "recipes.js").read_text(encoding="utf-8")

    def test_recipe_script_matches_audit_worksheet(self):
        swaps = {r["recipe_id"]: r["detail"] for r in self.rows if r["action"] == "swap"}
        removals = {r["recipe_id"] for r in self.rows if r["action"] == "remove"}
        scripted_swaps = {m[0]: f"{m[1]}>{m[2]}" for m in re.findall(r'\["([^"]+)", "([^"]+)", "([^"]+)"\]', self.script)}
        scripted_removals = set(re.findall(r'^  "([^"]+)",$', self.script.split("GEAR_REMOVALS")[1].split("]")[0], re.M))
        self.assertEqual(scripted_swaps, swaps)
        self.assertEqual(scripted_removals, removals)

    def test_swaps_lift_exactly_one_tier_and_removals_are_two_or_more(self):
        for row in self.rows:
            tier, mats = int(row["tier"]), int(row["material_tier"] or 0)
            if row["action"] == "swap":
                self.assertEqual(tier - mats, 1, row["recipe_id"])
                self.assertTrue(row["detail"].endswith(("minecraft:diamond", "minecraft:netherite_ingot")) or "netherite_" in row["detail"])
            if row["action"] == "remove":
                self.assertGreaterEqual(tier - mats, 1, row["recipe_id"])

    def test_kept_recipes_do_not_outclass_their_materials_unless_gated(self):
        for row in self.rows:
            if row["action"] == "keep" and row["recipe_type"] in ("crafting_shaped", "crafting_shapeless"):
                tier, mats = int(row["tier"]), int(row["material_tier"])
                # either within tier, or gated by a unique modded material (the generator keeps those)
                self.assertTrue(tier <= mats or tier > 1, row["recipe_id"])


class GearLoot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool("gen_gear_loot")
        with AUDIT.open(encoding="utf-8") as source:
            cls.audit = {r["item"]: int(r["tier"]) for r in csv.DictReader(source)}

    def test_every_listed_item_is_audited_and_in_a_matching_tier(self):
        self.tool.validate(self.audit)  # raises SystemExit on any mismatch

    def test_affix_entries_exist_for_each_listed_item_with_the_tier_rarity_range(self):
        root = KUBEJS / "data" / "apotheosis" / "affix_loot_entries"
        for tier, items in self.tool.GEAR.items():
            low, high = self.tool.TIERS[tier]["rarity"]
            for item in items:
                ns, _, name = item.partition(":")
                entry = json.loads((root / tier / f"{ns}_{name}.json").read_text(encoding="utf-8"))
                self.assertEqual(entry["stack"]["item"], item)
                self.assertEqual(entry["min_rarity"], f"apotheosis:{low}")
                self.assertEqual(entry["max_rarity"], f"apotheosis:{high}")

    def test_gear_tables_list_the_same_items(self):
        for tier, items in self.tool.GEAR.items():
            table = json.loads((KUBEJS / "data" / "ddo" / "loot_tables" / "gear" / f"{tier}.json").read_text(encoding="utf-8"))
            names = {e["name"] for pool in table["pools"] for e in pool["entries"] if e["type"] == "minecraft:item"}
            self.assertTrue(set(items) <= names, tier)

    def test_injection_script_uses_the_generic_loot_event(self):
        script = (KUBEJS / "server_scripts" / "gear_loot.js").read_text(encoding="utf-8")
        self.assertIn("ServerEvents.genericLootTables", script)  # chestLootTables silently prefixes "chests/"
        self.assertNotIn("ServerEvents.chestLootTables", script)
        for tier in ("overworld", "nether", "end"):
            self.assertIn(f'table: "ddo:gear/{tier}"', script)


class TrapVaultAndFit(unittest.TestCase):
    def test_vault_datapack_files_parse_and_reference_real_tables(self):
        base = KUBEJS / "data" / "ddo"
        for rel in ("worldgen/structure/trapvault.json", "worldgen/template_pool/trapvault/start.json",
                    "worldgen/structure_set/trapvault.json", "tags/worldgen/biome/has_trapvault.json",
                    "loot_tables/chests/trapvault_treasure.json", "loot_tables/chests/trapvault_cache.json"):
            json.loads((base / rel).read_text(encoding="utf-8"))
        self.assertGreater((base / "structures" / "trapvault.nbt").stat().st_size, 1000)
        for rel in ("trapvault_treasure", "trapvault_cache"):
            text = (base / "loot_tables" / "chests" / f"{rel}.json").read_text(encoding="utf-8")
            for name in re.findall(r'"name": "(ddo:gear/\w+)"', text):
                self.assertTrue((base / "loot_tables" / "gear" / f"{name.split('/')[1]}.json").exists(), name)

    def test_overlapping_structure_sets_keep_apart(self):
        strongholds = json.loads((KUBEJS / "data" / "minecraft" / "worldgen" / "structure_set" / "strongholds.json").read_text(encoding="utf-8"))
        self.assertEqual(strongholds["placement"]["exclusion_zone"]["other_set"], "betterstrongholds:stronghold")
        for name in ("villages_jungle", "villages_swamp"):
            data = json.loads((KUBEJS / "data" / "nova_structures" / "worldgen" / "structure_set" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(data["placement"]["exclusion_zone"]["other_set"], "minecraft:villages")

    def test_class_script_allows_backpacks_and_spell_engine_slots(self):
        classes = (KUBEJS / "server_scripts" / "classes.js").read_text(encoding="utf-8")
        self.assertIn('CURIOS_EXEMPT_NAMESPACES = ["sophisticatedbackpacks"]', classes)
        for slot in ("spell_book", "spell_scroll", "spell_trinket", "spell_quiver", "spellbook"):
            self.assertIn(f'"{slot}"', classes)
        self.assertIn("spell_power:generic", classes)


class BossShop(unittest.TestCase):
    COINS = {f"lightmanscurrency:coin_{m}" for m in ("copper", "iron", "gold", "emerald", "diamond", "netherite")}

    def test_shop_script_is_current_and_sells_every_loot_item_for_real_coins(self):
        shop = load_tool("gen_shop")
        script = (KUBEJS / "server_scripts" / "shop.js").read_text(encoding="utf-8")
        self.assertEqual(script, shop.render(), "run tools/gen_shop.py")
        loot = load_tool("gen_gear_loot")
        for item in [i for items in loot.GEAR.values() for i in items] + loot.MYTHIC:
            self.assertIn(f'"{item}"', script)
        for _item, count, coin, price in shop.trades():
            self.assertIn(coin, self.COINS)
            self.assertGreater(price, 0)
            self.assertGreater(count, 0)

    def test_boss_coin_rewards_use_real_coins_and_cover_every_campaign_boss(self):
        script = (KUBEJS / "server_scripts" / "progression.js").read_text(encoding="utf-8")
        for coin in re.findall(r'"(lightmanscurrency:coin_\w+)"', script):
            self.assertIn(coin, self.COINS)
        for boss in ("cataclysm:ancient_remnant", "cataclysm:netherite_monstrosity", "cataclysm:ender_guardian"):
            block = script.split(f'"{boss}": {{')[1].split("}")[0]
            self.assertIn("coins:", block, boss)
        self.assertIn("COIN_ONLY_BOSSES", script)


class CastleAndOpening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.castle = load_tool("gen_castle")
        cls.intro = (KUBEJS / "server_scripts" / "intro.js").read_text(encoding="utf-8")

    def test_throne_is_reachable_only_across_the_bridge_and_through_the_gate(self):
        start, goal = (0, 0, 112), (0, 0, -22)
        world = self.castle.build()
        self.assertTrue(self.castle.walkable(world, start, goal))
        no_bridge = self.castle.build()
        no_bridge.fill(-2, -1, 43, 2, -1, 49, "minecraft:water")
        self.assertFalse(self.castle.walkable(no_bridge, start, goal))
        sealed = self.castle.build()
        sealed.fill(-4, 0, 40, 4, 9, 40, "minecraft:stone_bricks")
        self.assertFalse(self.castle.walkable(sealed, start, goal))

    def test_committed_layout_matches_the_generated_tiles(self):
        layout = (KUBEJS / "server_scripts" / "castle_layout.js").read_text(encoding="utf-8")
        tiles = json.loads(layout.split("global.CASTLE = ", 1)[1])["tiles"]
        on_disk = {f"ddo:castle/{path.stem}" for path in (KUBEJS / "data" / "ddo" / "structures" / "castle").glob("*.nbt")}
        self.assertEqual({t["id"] for t in tiles}, on_disk)

    def test_rhino_quirks_stay_fixed(self):
        # Math.PI is undefined in KubeJS's Rhino: any angle built from it is NaN and the cutscene silently breaks.
        self.assertNotIn("Math.PI", self.intro)
        self.assertIn("const PI = 3.141592653589793", self.intro)

    def test_every_voice_line_has_a_registered_sound_and_a_real_clip(self):
        sounds = json.loads((KUBEJS / "assets" / "ddo" / "sounds.json").read_text(encoding="utf-8"))
        used = set(re.findall(r'"((?:king|guard)_[a-z]*_?\d+)"', self.intro))
        self.assertTrue(used)
        for clip in used:
            self.assertIn(f"voice.{clip}", sounds, clip)
            ogg = KUBEJS / "assets" / "ddo" / "sounds" / "voice" / f"{clip}.ogg"
            self.assertGreater(ogg.stat().st_size, 5000, clip)
            self.assertEqual(ogg.read_bytes()[:4], b"OggS", clip)

    def test_speech_waits_for_each_clip_and_guards_have_three_voices(self):
        seized = re.search(r"VOICE_SEIZED_SECS = \[([^\]]*)\]", self.intro).group(1).split(",")
        freed = re.search(r"VOICE_FREED_SECS = \[([^\]]*)\]", self.intro).group(1).split(",")
        self.assertEqual(len(seized), 6)
        self.assertEqual(len(freed), 4)
        for speaker in ("CAPTAIN", "VOSS", "DUNN"):
            self.assertIn(f"const {speaker} =", self.intro)

    def test_first_expedition_loop_is_wired(self):
        for needle in ("ddo_miniboss", "ddo_stage", "startExpedition", "freePlayer", "!dungeon", "!skipintro"):
            self.assertIn(needle, self.intro)


if __name__ == "__main__":
    unittest.main()
