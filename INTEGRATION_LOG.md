# INTEGRATION_LOG — Saltglass 1.0.0

Every decision that changed the pack from "a list of mods" into "one deliberate game", plus the
pins that were **rejected** and why. Written while building, in order. `DESIGN.md` is the intent;
this file is what actually happened to it.

---

## 0. Environment constraint, stated up front

This pack was built in a sandbox with **no Java runtime and no network access to Modrinth, CurseForge
or Mojang** (only GitHub and the package registries are reachable). That has one hard consequence:

* **Mod jars could not be downloaded into the repository, so nothing was launched, no world was
  created and no moment was played through in-game here.** The complete, honest account of what
  *was* verified instead is in `TEST_REPORT.md`. Nothing in that file is claimed as "ran" that did
  not run.

Everything that *could* be verified without a JVM was verified, and several of those checks caught
real defects that would have made the pack fail on first launch. Those are recorded below as
"caught by the build check", because a validation that never finds anything is not a validation.

---

## 1. Version pinning decisions

| Mod | Chosen | Rejected alternative | Why |
|---|---|---|---|
| Forge | **47.4.10** (Recommended) | 47.4.26 (Latest) | 47.4.26 shipped 5 days before this build. The pack sits on the build the Forge download page marks *Recommended* for 1.20.1, so the loader is not the thing that surprises anyone. |
| Create | **1.20.1-6.0.8** | 6.0.6 (the version most community guides quote) | 6.0.8 is the last 1.20.1 file, 6.99M downloads, and 6.0.6 is superseded. Community guides are stale, not authoritative. |
| Farmer's Delight | **1.20.1-1.3.4** | 1.20.1-1.2.11a (this pack's own first pick) | Re-pinned after querying the registry: 1.3.x *is* the current 1.20.1 line, and 1.3.0 added a native **EMI plugin** — this pack's recipe viewer. The reason 1.2.11a was chosen (a Create-contraption fix) is subsumed by the newer line. |
| ~~GeckoLib~~ → **Citadel 2.6.3** | Citadel 2.6.3 | GeckoLib 4.8.2 | **GeckoLib was removed entirely.** It was in the pack on the assumption that Alex's Mobs needs it; the registry shows Alex's Mobs requires **Citadel**, and nothing else in the pack uses GeckoLib. Citadel 2.6.3's headline fix is a server-side memory leak in world-data loading — relevant to a pack with its own dimension. |
| Sophisticated Backpacks + Core | **3.23.1.1184 + Core 1.2.39.938** | 3.24.2.1341 + Core 1.2.84.1117 | The 3.24.x pair is newer but has ~1.4K downloads against 1.67M. Core and Backpacks are also kept as a *matched pair* rather than mixed across the two release trains. |
| Corail Tombstone | **1.20.1-9.1.4** | 9.1.5 (newest, released 2 days before this build) | 9.1.5 had 5.7K downloads against 9.1.4's 492K. A pack that must work on someone else's first launch does not take a two-day-old build. |
| ModernFix | **5.27.83+mc1.20.1** | 5.26.1+mc1.20.1 (this pack's own first pick), 5.27.85 | 5.26.1 is **not returned by the registry as a 1.20.1 release at all**, so a resolver filtering release+Minecraft+loader would never find it. The claim that it was "the Modrinth Release" came from a search snippet and was wrong. 5.27.83 is the most-downloaded release in the active 5.27 line (432,024). |
| FTB Quests | **2001.4.22** | 2001.4.21 | 4.22 is the newest 1.20.1 Forge file (May 2026) and its declared dependencies are exactly the three libraries shipped here. |
| Architectury | **9.2.14+forge** | 9.1.13 | 24.4M downloads, last 1.20.1 Forge build. |

### The pins that were **rejected outright**

| Mod | Why it is not in the pack |
|---|---|
| **OptiFine** | Cannot be verified against Embeddium + Oculus + Create 6 + Ars Nouveau as a stack, and it replaces the same render code Embeddium replaces. The brief's own rule ("OptiFine only if verified with the full stack") resolves to *no*. Excluded, and the README says so. |
| **Terralith 2.4.4** | Verified 1.20.1 Forge-capable and beautiful — and wrong. "Almost 100 new biomes" fights a landscape whose whole premise is that it has been *emptied out*, and it would be a second worldgen stack on top of the pack's own datapack dimension. Rejected for cohesion, not compatibility. This is the single biggest cut in the pack. |
| **YUNG's Better Dungeons** | Would have supplied the Act III location. The drowned cathedral is hand-built in the datapack instead, because a random dungeon generator standing next to a scripted one reads as two different packs. |
| **Cataclysm / Iron's Spellbooks / Mowzie's Mobs** | Each would supply a boss. The pack refuses a boss: the culminating objective is a place and a choice, and all three mods would also inject a combat-power curve before Act III. |
| **ExtraQuests / FTB Quests UI Overhaul** | Verified for 1.20.1 Forge and genuinely good. The two non-standard task types that would have justified ExtraQuests are replaced here by an `ftbquests:dimension` task and a datapack scoreboard flag; UI Overhaul re-skins the screen this pack restyles by config. |
| **FTB Chunks / Essentials / XMod Compat** | Claim protection and keybind tooling are host decisions for a 1–4 player pack and are documented in the README instead of shipped as three more jars. |
| **Sophisticated Storage / Functional Storage** | A second storage family would be superfluous next to a placeable backpack plus vanilla barrels. |
| **JEI / REI, Sodium / Rubidium, Iris** | Duplicate-purpose mods. One of each: EMI, Embeddium, Oculus. |
| **Flywheel / Ponder as separate jars** | **Bundled inside create-1.20.1-6.0.8.jar.** Installing a standalone Flywheel is the single most common way a Create 6 pack fails to start, so it is called out in the README troubleshooting table and in `MODLIST.md`. |
| **Curios API** | Would exist only to hold a bauble slot for the Paraglider, which uses a vanilla slot here. Re-check before any accessory mod is added. |

---

## 2. Integration decisions

### 2.1 The datapack is the pack's spine, and Paxi is why it works

The Reflected Deep, the cathedral, the three bells and the Turning are all **datapack** content:

```
config/paxi/datapacks/saltglass/
  data/saltglass/dimension/reflected_deep.json        flat water world, glass ceiling
  data/saltglass/dimension_type/reflected_deep.json   no skylight, ambient 0.32, end sky
  data/saltglass/structures/drowned_cathedral.nbt     111x46x61, 31,890 blocks
  data/saltglass/structures/beacon_tower.nbt          33x40x33
  data/saltglass/structures/tide_trench.nbt           25x12x25
  data/saltglass/functions/*.mcfunction               17 functions
  data/saltglass/predicates/night.json, crouching.json
  data/saltglass/advancements/*.json                  the three moments
```

**Paxi was added late and deliberately**: a datapack that a player has to copy into every new
`world/datapacks/` folder is a datapack that half the audience never loads. Paxi loads
`config/paxi/datapacks/*` into every world, on both sides, from the instance folder — so the deep
exists in every world by construction and there is exactly one copy of the datapack to keep in sync
between the client and server exports.

### 2.2 The dimension is a `minecraft:flat` generator, on purpose

The Reflected Deep uses a flat generator rather than a noise generator:

```json
layers: bedrock 1, deepslate 4, stone 8, prismarine 3, water 29, glass 4
```

* A **noise** generator would have meant hand-authoring a full 1.20.1 `noise_settings` router with
  density functions — large, fragile, and impossible to verify without launching the game.
* A **flat** generator is 12 lines, deterministic, and *thematically correct*: the reflection is an
  infinite still ocean under an unbroken sheet of glass. The cathedal's spires pierce that ceiling,
  which is visible from both sides.
* `features: false` and `structure_overrides: []` keep it deterministic, so the cathedral's
  position (`-55, -49, -30`) is a constant the functions and the docs can both rely on.

**Honesty correction carried into the design:** the first draft of `DESIGN.md` claimed that through
the glass ceiling "you can see your own salt flats from below". A flat dimension cannot do that.
The claim was rewritten to what the datapack actually builds — a lit ceiling the spires press
against — rather than left in as poetry the pack cannot deliver.

### 2.3 Arriving in the deep does not drown you, and that is a design decision

`dive/enter` grants 100 minutes of Water Breathing and 1 minute of Dolphin's Grace. The reason is
not convenience: refusal #1 says this pack is not a survival-horror game, and an air meter in a
dimension that is *entirely* water would turn fifteen screenshots into a panic mechanic. The effect
is visible and legible in the HUD, so the player understands why they are not drowning.

### 2.4 The three signature moments are quest rewards, and that is not a workaround

Each moment is a datapack function fired as an FTB Quests `ftbquests:command` reward:

| Moment | Trigger | Function |
|---|---|---|
| 1 — The Dive Through the Face | crouch on tinted glass, at night, in the overworld (a `tick` check against two predicates) | `saltglass:dive/enter` → `dive/exit` |
| 2 — The Drowned Cathedral | the "Three Beacons at Dusk" quest (dimension task + 3 light quests) | `saltglass:cathedral/open` |
| 3 — The Turning | the "Set the Heart in the Last Dry Trench" quest | `saltglass:turning/set` → `turning/wave1..4` |

Two details worth defending:

* **The dive is a real mechanic, not a button.** It is a `tick`-function check: you, crouching, on
  tinted glass, at night. The quest tells you the ritual in the salvage-priests' voice; the datapack
  is what actually opens the hole.
* **The Turning is staged across 400 ticks (~20 s) in four waves** at radii 12 / 26 / 38 / 48 around
  each harbour, with particles and a rising chat narration, because one instantaneous 96×96 flood at
  three places simultaneously is a lag spike and reads as a bug rather than a sea.
* **Every fill is split along z and audited.** The build check parses each `fill` in every function
  and fails the build above 32,768 blocks — the vanilla per-command limit. Wave 4 at radius 48 is
  97×4×97 = 37,636, so it is emitted as two half-slabs. *Caught by the build check.*

### 2.5 The cathedral is placed by the tick function, not during worldgen

`cathedral/place` runs from `tick` guarded by a score, the tick *after* the first diver is inside the
deep. Two reasons: chunks around the destination are unloaded until a player is standing in them, and
`place structure` silently does nothing in an unloaded chunk; and the reveal is better storytelling
when the player is already in the water and can see it appear at a distance.

### 2.6 Quest tasks reference only verified item ids

Every `ftbquests:item` task is checked at build time against a whitelist of item ids that predate
1.20.1 and have not been renamed (vanilla, Farmer's Delight, Create, Sophisticated Backpacks,
Paragliders). Nothing outside that list appears in a task, so the book cannot ask for an item that
does not exist — the classic failure mode of a hand-written quest pack. Where a mod's content is
central but its item ids were not verified (Ars Nouveau, Alex's Mobs, Tombstone), the quest
**describes** the goal and uses a `checkmark` task instead of guessing an id. That is a deliberate
trade of machine-checkability for correctness.

### 2.7 The quest format

Field names, task ids and reward ids were read from the FTB Quests **1.20.1 source** (`1.20.1/dev`
branch) rather than from memory or a wiki:

* files are **SNBT**, not JSON — `config/ftbquests/quests/data.snbt` + `chapters/*.snbt`
* `BaseQuestFile.VERSION = 13`
* task types: `item, custom, xp, dimension, stat, kill, location, checkmark, advancement,
  observation, biome, structure, gamestage, fluid`
* reward types: `item, choice, all_table, random, loot, command, custom, xp, xp_levels,
  advancement, toast, gamestage`
* `DimensionTask` field is `dimension`; `CommandReward` field is `command`; `ItemTask` fields are
  `item` (a serialised ItemStack), `count`, `consume_items`

Had this been written against the widely-copied 1.16-era JSON examples, the pack would have shipped
a quest book that FTB Quests silently ignores. The generator round-trips every emitted file through
a strict SNBT parser in the build check.

### 2.8 Calm defaults, and where each one lives

| Setting | Value | File |
|---|---|---|
| Render / simulation distance | 10 / 8 | exported as documented client defaults |
| Shaders | **off**, none shipped | `config/oculus.properties` |
| Minimap | off; waypoints on | `config/xaerominimap.txt` |
| Ambient audio | on, 0.7 | `config/ambientsounds-client.json` |
| Create Ponder (the in-game guide) | **on** | `config/create-client.toml` |
| ModernFix dynamic resources | on; dynamic **models** off | `config/modernfix-mixins.properties` |
| Difficulty | normal, `keepInventory=false` | `pack/server/server.properties` |
| Flight | `allow-flight=true` (Paraglider requires it) with no flight content shipped | `server.properties` + MODLIST |
| Command blocks | **enabled** — required, the moments are functions | `server.properties` |

ModernFix dynamic *models* is deliberately left off: Create's ponder scenes and Ars Nouveau's
animated glyph items load models at runtime in ways that dynamic model loading can disturb, and a
milestone pack should not trade correctness for a few hundred megabytes of heap.

### 2.9 Death, and not punishing the player for the landscape's size

Corail Tombstone, with vanilla `keepInventory=false`. The basin is deliberately enormous; losing an
hour of walking to one bad jump over water is not difficulty, it is tedium. Graves keep the salvage,
and the mod's souls/prayer system is the one place the pack lets the dead civilisation speak — which
keeps it inside the fiction rather than bolted on as insurance.

---

## 3. Defects found by the build checks

The first eight of these were found by the automated checks; the rest by actually querying the
registry instead of trusting project pages and search snippets. A verification that finds nothing
was not a verification, and this pack's first launch would have failed on defect 1 alone.

These are real, and each one would have broken something a player would have hit:

| # | Defect | How it was found | Fix |
|---|---|---|---|
| 1 | Wave 4's flood was a 37,636-block `fill`, over vanilla's 32,768 limit | build check parses every `fill` and computes its volume | wave 4 (and every wave) split into two half-fills along z |
| 2 | The cathedral's doors were built as **air**, so `cathedral/open` would have "opened" nothing | reading the structure generator against the function | doors built as `tinted_glass`; the function replaces tinted glass with air |
| 3 | Six functions — including all three signature moments — had no caller in the datapack | dead-code check over function bodies **and** quest rewards | queued as quest rewards; the check now counts reward callers as first-class |
| 4 | The datapack was being installed into two places (`config/worlddata`, which loads nothing) | tracing how a bundled datapack actually reaches a new world | switched to the Paxi path and dropped the second copy: one datapack, one location |
| 5 | A mod-list entry referenced a filename the project page never showed, presented as if verified | writing the verification rule down and applying it | that entry carries an explicit `filename-inferred` status and the resolver fills it |
| 6 | Cataloguing pins from memory produced **no** confident Modrinth project IDs for 15 of 23 mods | trying to write them down | every unverifiable ID was deleted from the lockfile rather than guessed; resolution is by project slug + exact version string |
| 7 | `dive/exit` originally teleported the player onto the mirror gate, which would have re-triggered the dive | walking the state machine on paper | exit lands 3 blocks east and 2 up of the gate, plus a 10-second cooldown score, plus crouch is required to dive |

Finding #6 is the one to take seriously: an invented project ID looks exactly like a verified one in
a manifest, and would have produced a launcher that downloads nothing or the wrong jar.

---

## 4. What was not done, and why

* **No shaderpack is bundled.** Oculus is present so a player *can* add one. Shipping one would make
  the pack's first impression depend on a GPU.
* **No custom textures or resource pack.** The pack's beauty comes from terrain, light and scale, not
  from a re-skin; and a resource pack would need per-mod patching to avoid breaking Ponder scenes.
* **The "Moonstone Lens" from the first design draft does not exist.** It would have required a
  custom item. The Act I gate is instead the *folded mirror* — tinted glass, laid flat — which is
  craftable in Act I, needs no new content, and is a physical object the player builds and recognises.
  `DESIGN.md` was updated to match.
* **No mob-grinder, no XP gate, no currency, no level-gated gear** — see refusals in `DESIGN.md` §3.
