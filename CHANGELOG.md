# CHANGELOG — Saltglass

## 1.0.0 — 2026-10-07

First release. 23 mods, Forge 47.4.10, Minecraft 1.20.1, Java 17.

### Added

**Concept**
* Saltglass, chosen from five originated seeds. Full reasoning, scores and the two rejected
  runners-up are in `DESIGN.md`.
* Three-act progression: **The Low Water** → **The Drowned Bells** → **The Turning**, plus an
  Epilogue chapter for after the water comes back.
* Palette of six colours (`#E8E3D6` Salt Bone, `#7FB4B0` Mirror Teal, `#1D4C57` Deep Glass,
  `#0A1418` Abyss Slate, `#E0A32E` Beacon Amber, `#8A5A3B` Salvage Tar) used consistently across the
  icon, the guide text and the moment narration.

**Content**
* The **Reflected Deep** — a flat-generator dimension: 29 blocks of water under a four-block ceiling
  of glass, no skylight, ambient light 0.32, no drown timer.
* **Drowned cathedral**, 111×46×61, 31,890 blocks, generated as a real `.nbt` structure file.
  Nine bays, an altar with nine lit candles, three doors of the Kettle Sea, three spires that pierce
  the glass ceiling, and a drowned fleet at the anchorage. Not a ruin — it is *finished*.
* **Beacon towers** (33×40×33) placed by the three harbour quests, and the **last dry trench**
  (25×12×25) for the Tide Heart.
* **17 datapack functions** implementing the three signature moments, plus `load`/`tick`.
* **Three advancements** for the signature moments.
* **24 quests** across six chapters, in SNBT, written in the salvage-priests' voice.
* **Pack icon**, 512×512 generated procedurally in the palette, plus 256/128/64/32 sizes.

**Packaging**
* Modrinth `.mrpack` with overrides, generated from `pack/mods.lock.json`.
* CurseForge tree with `manifest.json` (overrides + `defaultconfigs/` + `mods/`).
* Dedicated server export: server mod manifest (`server-mods.tsv`), `server.properties`,
  `jvm_args.txt`, `README-SERVER.md` and the datapack under `defaultconfigs/`.
* `resolved-manifest.json` — the exact file list both launcher formats were built from.

**Tooling**
* `tools/build_pack.py` validates before it builds: version-pin rules, dependency closure, one
  worldgen stack, one recipe viewer, licence recorded, no placeholders, SNBT well-formedness,
  quest dependency closure, quest-to-function cross-references, datapack JSON validity,
  mcfunction brace/bracket balance, structure-file existence, and the vanilla 32,768-block `/fill`
  limit. It refuses to build on failure.
* `tools/gen_content.py` round-trips every quest file through a strict SNBT parser and checks every
  item id against a verified whitelist.
* `tools/gen_structure.py` writes real NBT structure files via `nbtlib`.

### Defects found and fixed before release

* Wave 4's flood was a 37,636-block `fill`, above vanilla's 32,768 limit → split into two half-slabs.
* The cathedral's doors were built as air, so the Act II "doors open" moment would have opened
  nothing → doors are now tinted glass and the function replaces them.
* Six functions, including all three signature moments, had no caller → they are now fired as quest
  rewards, and the dead-code check counts reward callers.
* The bundled datapack was installed to a path that loads nothing → switched to Paxi's
  `config/paxi/datapacks/` and reduced to a single copy.
* `dive/exit` would have re-triggered the dive on landing → exit offset, cooldown score, and crouch
  required to dive.
* Fifteen Modrinth project IDs were unverifiable → deleted rather than guessed; resolution is by
  project slug plus exact version string.

### Known limitations

* **Nothing was launched.** No JVM and no reachable mod CDN in the build environment. See
  `TEST_REPORT.md` — it lists what was verified statically, what was not, and what a human should run
  first.
* The wave-based flood is a bounded `fill` at three harbours with a maximum radius of 48 blocks, not
  a whole-map sea level change. That is the design, and it is documented as such in `DESIGN.md`
  rather than described as something larger.
