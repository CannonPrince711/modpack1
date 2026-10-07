import csv
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "balance" / "difficulty-loot-balance.csv"
LOCK = ROOT / "mods.lock.json"
AFFIX_ROOT = ROOT / "overrides" / "kubejs" / "data" / "apotheosis" / "affix_loot_entries"


class BalanceRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with CSV.open(newline="", encoding="utf-8") as source:
            cls.rows = list(csv.DictReader(source))

    def test_every_class_survives_first_three_boss_envelopes(self):
        rows = [row for row in self.rows if row["record_type"] == "combat"]
        self.assertEqual(len(rows), 9)
        for row in rows:
            with self.subTest(player_class=row["class"], boss=row["boss"]):
                effective_health = float(row["effective_health"])
                incoming_dps = float(row["boss_incoming_dps"])
                fight_seconds = float(row["solo_ttk_seconds"])
                boss_health = float(row["boss_health"])
                class_dps = float(row["class_sustained_dps"])
                self.assertGreater(effective_health, 0)
                self.assertGreater(incoming_dps, 0)
                self.assertGreater(fight_seconds, 0)
                self.assertAlmostEqual(fight_seconds, boss_health / class_dps, delta=0.1)
                self.assertAlmostEqual(
                    float(row["solo_survival_seconds"]),
                    effective_health / incoming_dps,
                    delta=0.1,
                )
                self.assertLessEqual(
                    fight_seconds,
                    float(row["solo_survival_seconds"]),
                )
                self.assertLessEqual(
                    float(row["party_4_ttk_seconds"]),
                    fight_seconds * 1.8,
                )
        self.assertEqual(
            {row["boss"] for row in rows},
            {"Ancient Remnant", "Netherite Monstrosity", "Ender Guardian"},
        )
        self.assertEqual(
            {row["class"] for row in rows},
            {"Warrior", "Mage", "Ranger"},
        )

    def test_runtime_scripts_wire_classes_curios_and_campaign_bosses(self):
        classes = (ROOT / "overrides" / "kubejs" / "server_scripts" / "classes.js").read_text(
            encoding="utf-8"
        )
        progression = (
            ROOT / "overrides" / "kubejs" / "server_scripts" / "progression.js"
        ).read_text(encoding="utf-8")
        for class_name in ("warrior", "mage", "ranger"):
            self.assertIn(f"{class_name}:", classes)
        self.assertIn("getCuriosInventory", classes)
        self.assertIn("modifyAttribute", classes)
        for boss_id in (
            "cataclysm:ancient_remnant",
            "cataclysm:netherite_monstrosity",
            "cataclysm:ender_guardian",
        ):
            self.assertIn(boss_id, progression)
        self.assertIn("ddo_boss_xp", progression)

    def test_ftb_chapters_have_unique_ids_and_resolvable_dependencies(self):
        chapters = sorted(
            (ROOT / "overrides" / "config" / "ftbquests" / "quests" / "chapters").glob(
                "*.snbt"
            )
        )
        ids = []
        dependencies = []
        for chapter in chapters:
            content = chapter.read_text(encoding="utf-8")
            ids.extend(re.findall(r'\bid: "([0-9A-F]+)"', content))
            dependencies.extend(re.findall(r'dependencies: \["([0-9A-F]+)"\]', content))
        self.assertEqual(len(chapters), 3)
        self.assertTrue(ids)
        self.assertTrue(all(len(identifier) == 16 for identifier in ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(set(dependencies).issubset(ids))

    def test_tier_affix_rarity_is_exponential(self):
        tiers = {
            row["tier"]: float(row["target_top_rarity_probability"])
            for row in self.rows
            if row["record_type"] == "loot"
        }
        self.assertEqual(set(tiers), {"overworld", "nether", "end"})
        self.assertGreater(tiers["overworld"], tiers["nether"])
        self.assertGreater(tiers["nether"], tiers["end"])
        self.assertLessEqual(tiers["nether"], tiers["overworld"] / 3)
        self.assertLessEqual(tiers["end"], tiers["nether"] / 3)

        weights = {}
        for rarity in ("common", "uncommon", "rare", "epic", "mythic", "ancient"):
            path = ROOT / "overrides" / "kubejs" / "data" / "apotheosis" / "rarities" / f"{rarity}.json"
            weights[rarity] = json.loads(path.read_text(encoding="utf-8"))["weight"]
        self.assertEqual(
            [weights[name] for name in ("common", "uncommon", "rare", "epic", "mythic", "ancient")],
            [400, 180, 55, 14, 3, 1],
        )

    def test_mod_lock_contains_immutable_release_hashes(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["pack"]["minecraft"], "1.20.1")
        self.assertEqual(lock["modrinth_release_filter"]["loader"], "forge")
        self.assertGreaterEqual(len(lock["mods"]), 20)
        all_mods = lock["mods"] + lock.get("curseforge_mods", [])
        self.assertTrue(
            {"ftb-quests-forge", "ftb-library-forge", "ftb-teams-forge", "item-filters"}
            .issubset({mod["slug"] for mod in lock["curseforge_mods"]})
        )
        for mod in all_mods:
            with self.subTest(mod=mod["name"]):
                self.assertEqual(len(mod["sha1"]), 40)
                self.assertEqual(len(mod["sha512"]), 128)
                if "version_id" in mod:
                    self.assertIn("/versions/" + mod["version_id"] + "/", mod["url"])
                else:
                    file_id = str(mod["file_id"])
                    self.assertIn(f"/{file_id[:-3]}/{file_id[-3:]}/", mod["url"])
                    self.assertTrue(mod["url"].endswith(mod["filename"]))

    def test_ftb_required_dependencies_are_pinned(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        all_mods = lock["mods"] + lock.get("curseforge_mods", [])
        aliases = {
            "ftb-teams-forge": "ftb_teams",
            "ftb-library-forge": "ftb_library",
            "ftb-quests-forge": "ftb_quests",
            "item-filters": "itemfilters",
        }
        names = {mod["slug"] for mod in all_mods}
        names.update(mod["project_id"] for mod in lock["mods"])
        names.update(
            aliases.get(mod["slug"], mod["slug"].replace("-", "_"))
            for mod in all_mods
        )
        names.add("architectury")
        for mod in all_mods:
            for dependency in mod.get("required_dependencies", []):
                if isinstance(dependency, str):
                    self.assertIn(dependency, names, f"{mod['name']} missing {dependency}")

    def test_spellbook_runtime_dependencies_are_pinned(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        by_slug = {mod["slug"]: mod for mod in lock["mods"]}
        self.assertIn("irons-lib", by_slug)
        self.assertIn("playeranimator", by_slug)
        self.assertIn("9nfaJPtX", by_slug["irons-spells-n-spellbooks"]["required_dependencies"])
        self.assertIn("gedNE4y2", by_slug["irons-spells-n-spellbooks"]["required_dependencies"])

    def test_apotheosis_affixes_are_tier_gated(self):
        expected = {
            "overworld": ("apotheosis:common", "apotheosis:rare", "minecraft:overworld"),
            "nether": ("apotheosis:rare", "apotheosis:epic", "minecraft:the_nether"),
            "end": ("apotheosis:epic", "apotheosis:mythic", "minecraft:the_end"),
        }
        for tier, (minimum, maximum, dimension) in expected.items():
            paths = list((AFFIX_ROOT / tier).glob("*.json"))
            self.assertTrue(paths, f"No affix entries for {tier}")
            for path in paths:
                entry = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(entry["min_rarity"], minimum)
                self.assertEqual(entry["max_rarity"], maximum)
                self.assertIn(dimension, entry["dimensions"])
        self.assertFalse(
            (ROOT / "overrides" / "kubejs" / "data" / "dungeon_delvers").exists(),
            "Apotheosis registry data must use its own namespace.",
        )

    def test_apotheosis_rules_target_dungeons_with_tiered_drop_chances(self):
        config = (
            ROOT / "overrides" / "config" / "apotheosis" / "adventure.cfg"
        ).read_text(encoding="utf-8")
        for table in (
            "dungeons_arise:chests/.*|0.12",
            "betterdungeons:.*|0.12",
            "betterstrongholds:chests/.*|0.12",
            "cataclysm:chests/acropolis_treasure|0.01",
            "minecraft:chests/end_city.*|0.01",
            "cataclysm:chests/.*|0.035",
        ):
            self.assertIn(table, config)
        self.assertIn("the_nether|rare|epic", config)
        self.assertIn("the_end|epic|mythic", config)


if __name__ == "__main__":
    unittest.main()
