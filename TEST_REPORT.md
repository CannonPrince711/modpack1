# TEST_REPORT — Saltglass 1.0.0

**Read this first.** The environment this pack was built in has **no Java runtime** and **no
network access** to Modrinth, CurseForge, Mojang or any mod CDN (only GitHub and the package
registries are reachable). Therefore:

> **No Minecraft client or server was launched. No world was created. No signature moment was
> played through. Phase 5 as specified — launch to menu, create a world, play an early loop,
> trigger a moment, launch a clean server — was NOT executed.**

That is the honest, complete answer, and it is the single largest limitation of this delivery.
What follows is what *was* actually run, in the order it was run, with the real numbers. Nothing
below is described as "tested" that was not executed by a command whose output is quoted here.
`MODLIST.md`, the manifests, the datapack and the quest book were all machine-validated; the
*gameplay* was not played.

---

## 0. What was run, and where

All commands were run from the repository root on 2026-10-07.

| # | Command | Result |
|---|---|---|
| 1 | `python3 tools/make_icon.py export/saltglass-icon/icon.png` | PASS — 3/3 composition checks |
| 2 | `python3 tools/gen_structure.py` | PASS — 3 `.nbt` structures written |
| 3 | `python3 tools/gen_content.py` | PASS — 17 functions, 7 quest files, 9 datapack JSONs |
| 4 | `python3 tools/tests/test_fetch_mods.py` | PASS — 9/9 resolver checks |
| 5 | `python3 tools/gen_docs.py` | PASS — MODLIST.md regenerated from the lockfile |
| 6 | `python3 tools/build_pack.py` | PASS — validation + export verification, then writes `export/` |
| 7 | zip integrity + `.nbt` reload check | PASS — both archives intact, all structures parse |

---

## 1. What could not be done, and why (limitations)

| Item | Status | Cause |
|---|---|---|
| Launch the game to the main menu | **NOT DONE** | no `java` in the environment |
| Create a world, confirm the custom dimension generates | **NOT DONE** | as above |
| Play the Act I loop | **NOT DONE** | as above |
| Trigger the Dive Through the Face in-game | **NOT DONE** | as above |
| Trigger the Drowned Cathedral / The Turning in-game | **NOT DONE** | as above |
| Launch a clean dedicated server and connect a client | **NOT DONE** | as above |
| Import the `.mrpack` through the Modrinth App | **NOT DONE** | no GUI and no launcher in the environment |
| Download the 23 mod jars | **NOT DONE** | `api.modrinth.com`, `cdn.modrinth.com` and `edge.forgecdn.net` are unreachable from the sandbox |
| Audit a real `latest.log` for mixin failures / missing assets / recipe conflicts | **NOT DONE** | requires a launch |
| Verify `ars_nouveau` / `create` behaviour against a running client | **NOT DONE** | requires a launch |

**Consequence for the export:** the `.mrpack` carries real, publisher-published download URLs,
`sha1` and `sha512` for **20 of its 23 entries** (all Modrinth-hosted). The three FTB libraries
(Quests, Library, Teams) are CurseForge-only and carry a pinned `edge.forgecdn.net` URL from
CurseForge's own CDN with **no hash** — because a hash this project cannot verify would be worse
than a missing one. A launcher will download all 23 files and check the 20 hashes it has.

**A human should run this first** (this is the acceptance test this report cannot give):

```
# 1. sanity-check the export without launching anything
python3 tools/build_pack.py                      # must print: validation ok + export verification ok

# 2. resolve + fetch the jars yourself (needs open network), server subset
python3 tools/fetch_mods.py --resolve
python3 tools/fetch_mods.py --download /tmp/sg-server --server

# 3. then: import export/saltglass-1.0.0.mrpack in the Modrinth App, allocate 6 GB,
#    create a world, and confirm this line appears in chat:
#      [Saltglass] The sea is still falling.
#    If it does, the datapack loaded and the deep exists. Then: lay 4 tinted glass,
#    stand on it, crouch, at night — and you are through the face.
```

---

## 2. Static verification — what each check proves

### 2.1 Icon integrity (§Phase 3 deliverable)

`tools/make_icon.py` draws the icon procedurally and then *verifies its own output* — the check
would fail loudly on a composition that had been broken by an edit, which is exactly what happened
on the first attempt (a vignette pass flooded the whole image grey; see the note in
`INTEGRATION_LOG.md`):

```
icon composition check:
  [ok] upper half brighter than lower (top=212 bottom=75)
  [ok] amber lantern light present (1141px)
  [ok] deep-glass reflection present (13168px)
```

512×512 RGBA, plus 256/128/64/32 renders; the 256 px version is embedded as a data URI in the
`.mrpack` (`icon` field present and non-empty).

### 2.2 Structures are real NBT, not placeholders

```
drowned_cathedral.nbt: size=[111, 46, 61] blocks=31890 palette=17 DataVersion=3465
beacon_tower.nbt:      size=[33, 40, 33]  blocks=2472  palette=10 DataVersion=3465
tide_trench.nbt:       size=[25, 12, 25]  blocks=2486  palette=9  DataVersion=3465
```

Each was written with `nbtlib` and then **re-opened and re-parsed** by the check above.
`DataVersion 3465` is Minecraft 1.20.1. Palette material names are vanilla only.

### 2.3 Quest book conforms to the FTB Quests 1.20.1 format

This is the check with the highest chance of having been wrong, because the format is widely
documented *incorrectly* (most public examples are 1.16-era **JSON**). The field names, task type
ids, reward type ids and file layout were read out of the FTB Quests **1.20.1 source**
(`1.20.1/dev`):

* `BaseQuestFile.readDataFull()` reads `data.snbt` + `chapters/*.snbt` — **SNBT, not JSON**
* `BaseQuestFile.VERSION = 13`; every emitted chapter carries `version: 13`
* task types available: `item, custom, xp, dimension, stat, kill, location, checkmark,
  advancement, observation, biome, structure, gamestage, fluid`
* reward types available: `item, choice, all_table, random, loot, command, custom, xp, xp_levels,
  advancement, toast, gamestage`
* `DimensionTask` field `dimension`; `CommandReward` field `command`; `ItemTask` fields
  `item`/`count`/`consume_items`; `StageTask` field `stage`

The generator then enforces, and the build re-checks:

* every emitted `.snbt` file **round-trips through a strict SNBT parser** written for this project
  (`tools/gen_content.py`) — a malformed file fails the build rather than being shipped;
* every quest id is unique within its chapter;
* every quest **dependency resolves to a quest that exists in the same file**;
* every item id used in a task is on an explicit whitelist of ids verified to predate 1.20.1
  and not renamed since — so the book cannot ask a player for an item that does not exist;
* every `ftbquests:command` reward that calls a function **calls a function that exists**;
* every task type and reward type begins with `ftbquests:`, and the type is one of the ids above.

### 2.4 Datapack validity

Checks that ran and passed:

* all 9 datapack JSON files parse (`pack.mcmeta`, dimension, dimension type, 2 predicates,
  3 advancements, function tags, `datapack_load_order.json`);
* all 17 `.mcfunction` files have balanced `{ }` and `[ ]` on every line that is not a comment;
* **no dead code:** every function is either `load`/`tick`-tagged or called from another function
  *or from a quest reward* (the check counts quest rewards as callers — this is the check that
  caught six uncalled functions including all three signature moments);
* **every `fill` is inside vanilla's 32,768-block limit**, computed from the literal coordinates
  in the command (this caught wave 4 at 97×4×97 = 37,636 and split it into two half-slabs);
* every `place structure saltglass:<id>` references a `.nbt` file that exists;
* the dimension type uses the 1.20.1 keys (`min_y: -64`, `height: 384`, `monster_spawn_light_level`
  as a uniform int provider, `monster_spawn_block_light_limit`, `has_skylight: false`).

### 2.5 Mod pins are publisher-verified

Every mod was resolved through the registry API on 2026-10-07 with the filter
`loaders=["forge"] & game_versions=["1.20.1"] & version_type=release`, and the newest release's own
filename, URL, `sha1`, `sha512` and size were recorded in `pack/mods.lock.json` under `pins`.

```
23 mods in the lockfile
  20 with publisher URL + sha1 + sha512
   3 without (CurseForge-only FTB libraries)
```

**Eleven pins changed as a result of actually checking**, and two project ids and one dependency
were wrong. They are listed in §3 because a verification that changes nothing was not a
verification.

### 2.6 The resolver's logic is unit-tested

`api.modrinth.com` is unreachable from the build environment, so the resolver could not be run
against the live registry. Instead its decision logic was tested against synthetic payloads shaped
exactly like Modrinth's `/project/{id}/version` response:

```
[ok] picks the pinned version, not the older one
[ok] ignores the fabric build with the same version
[ok] ignores the build for another Minecraft version
[ok] takes the primary file, not the sources jar
[ok] carries the publisher's sha1 through
[ok] carries the publisher's sha512 through
[ok] keeps the download URL from the API
[ok] unknown pin raises instead of silently picking another build
[ok] curseforge pin resolves offline to the pinned CDN url
9/9 resolver checks passed
```

The eighth one matters most: a pin that cannot be found must **fail loudly**, never fall back to
"some other build of the same mod".

### 2.7 Export verification — the artifacts were re-opened and inspected

`tools/build_pack.py` re-opens what it just wrote, as a launcher would:

```
export verification: ok (mrpack structure, index schema, datapack payload, server manifest)
built: 23 mod files, 23 mrpack entries
```

```
export/saltglass-1.0.0.mrpack: 53 entries, corrupt=None
export/saltglass-1.0.0-server.zip: 37 entries, corrupt=None
```

| Property | Value |
|---|---|
| mrpack entries | 23 mod files + 52 override files + `modrinth.index.json` |
| entries with `sha1` **and** `sha512` | 20 of 23 |
| entries with a `downloads` URL | **23 of 23** |
| declared payload size | 128.6 MiB |
| `dependencies` | `minecraft: 1.20.1`, `forge: 1.20.1-47.4.10` |
| embedded icon | yes (256 px PNG data URI) |
| envs split | 16 both-required · 4 client-required/server-unsupported · 2 client-required/server-optional · 1 client-optional/server-required |
| datapack inside overrides | `pack.mcmeta` + 3 `.nbt` structures + 17 functions + quest book, all present |
| server export contents | `server.properties`, `jvm_args.txt`, `README-SERVER.md`, `server-mods.tsv`, `fetch-server-mods.sh`, `fetch_mods.py`, `defaultconfigs/saltglass_datapack/` |
| client-only mods leaked into the server manifest | none (asserted against a name blocklist) |
| CurseForge manifest | `manifestType: minecraftModpack`, loader `forge-47.4.10`, 4 FTB entries, overrides + `defaultconfigs/` |

---

## 3. Defects found and fixed during verification

Ordered by how badly each would have hurt a player on first launch.

| # | Defect | Consequence if shipped | How it was caught | Fix |
|---|---|---|---|---|
| 1 | **FTB Quests was going to be written as JSON.** The 1.20.1 mod reads **SNBT** from `data.snbt` + `chapters/*.snbt` | The entire quest book would have silently not loaded — no error, no quests, no progression. The pack's only direction-of-travel, gone. | Reading `BaseQuestFile.readDataFull()` in the 1.20.1 source before writing a line of it | SNBT emitter + strict SNBT parser in the build |
| 2 | **Alex's Mobs' dependency was wrong**: it needs **Citadel**, not GeckoLib | Crash on launch (`Mod alexsmobs requires citadel`) | Querying Alex's Mobs' own dependency list in the registry | GeckoLib removed, Citadel added at 2.6.3 |
| 3 | **`modernfix 5.26.1+mc1.20.1` is not listed as a 1.20.1 release** by the registry | A resolver filtering release+MC+loader never finds it; the install fails | Querying the release-filtered version list | Re-pinned to `5.27.83+mc1.20.1` (432,024 downloads) |
| 4 | **Wave 4's flood was a 37,636-block `/fill`** | `/fill` above 32,768 does nothing — the final wave of the pack's climax silently fails | Build check computing each fill's volume | Split into two half-slabs (and the same treatment applied to every wave) |
| 5 | **The cathedral's doors were built as air** | The Act II "the doors open" moment opens nothing | Cross-reading the structure generator against the function | Doors built as tinted glass; `cathedral/open` replaces them |
| 6 | **Six functions had no caller**, including all three signature moments | The datapack's climax was unreachable — the functions existed and were never invoked | Dead-code check over functions *and* quest rewards | Wired as quest rewards; the check now counts reward callers |
| 7 | **The datapack was installed to `config/worlddata`**, which loads nothing | No dimension, no cathedral, no depth task — "The Wrong Sky" would never complete | Tracing how a bundled datapack actually reaches a new world | Moved to Paxi's `config/paxi/datapacks/`, one copy |
| 8 | **`ars_nouveau-1.20.1-4.12.7.jar` is not the Forge download**; it is the `-all` jar | Launcher fetches a filename that does not exist for that loader | Registry file list | Filename corrected to `-all.jar` |
| 9 | **Oculus' project id was wrong**, and its jar name was guessed | Manifest entry unresolvable | Registry lookup | Corrected to project `GchcoXML`, file `oculus-mc1.20.1-1.8.0.jar`; also confirmed it *requires* Embeddium |
| 10 | **Xaero's Minimap renamed its files** (25.x → 26.x scheme) | Pinned filename 404s | Registry file list | Re-pinned `forge-1.20.1-26.5.0` |
| 11 | `dive/exit` teleported the player onto the dive gate, re-triggering the dive | An inescapable bounce loop between two dimensions | Walking the state machine on paper | Exit lands 3 blocks east and 2 up of the gate, a 10-second cooldown score, and crouch required to dive |
| 12 | Fifteen Modrinth project ids were not verifiable | Invented ids look identical to verified ones and produce a manifest that downloads nothing or the wrong jar | Attempting to write them down | All unverifiable ids deleted; resolution by slug + exact version string, then replaced with registry-verified ids |
| 13 | Tombstone 9.1.4 was pinned on a download figure that does not hold on Modrinth | A year-old build for no reason | Registry metadata | Re-pinned 9.1.5, which the author's own file banner marks *Recommended* |
| 14 | A mod-list entry asserted a filename that the project page never showed | A false claim of verification in the deliverable | Writing the rule down and applying it to every row | That row is now `official-page-verified` **with the registry URL and hash recorded** |

Six of these fourteen (2, 3, 4, 5, 6, 9) would each on their own have produced a pack that either
crashes, silently loses content, or fails at its climax. This is the argument for the build checks
existing at all, and the reason §1's "not launched" limitation is stated so bluntly: the checks
above catch *structural* faults, and cannot catch a shader conflict, a mixin failure, a texture
that did not ship, or a mechanic that is simply not fun.

---

## 4. What is verified vs. what is assumed

**Verified (executed, output quoted in §2):** icon composition · structure NBT validity ·
datapack JSON validity · mcfunction syntax balance · dead-code absence · `fill` volume limits ·
structure references · SNBT round-trip · quest id uniqueness · quest dependency closure ·
quest→function reference closure · item-id whitelist · resolver logic (9 cases) · archive
integrity · manifest schema · mrpack env splits · server/client file separation ·
publisher hashes present for 20/23 entries.

**Assumed, not verified (requires a launch):** that the flat dimension generates as intended; that
`place structure` succeeds at the cathedral's coordinates in a live world; that the tick function's
predicates fire as expected; that Alex's Mobs runs against Citadel 2.6.3 and GeckoLib's absence
breaks nothing; that Create 6.0.8 and Ars Nouveau 4.12.7 coexist with Embeddium/Oculus/ModernFix;
that Farmer's Delight 1.3.4's EMI plugin loads against EMI 1.1.24; that FTB Quests 2001.4.22 renders
the chapters as authored; that the three moments *feel* like moments.

**The first person to run this pack is the first person to test it.** If you are that person, the
acceptance sequence in §1 is the one to follow, and the failure modes to expect are listed in
`README.md` under Troubleshooting — the first two (a stray Flywheel jar, a second renderer) are
the two most likely ways a player breaks this pack before seeing the sea at all.
