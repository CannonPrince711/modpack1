# MODLIST — Saltglass v1.0.0

**Minecraft 1.20.1 · Forge 1.20.1-47.4.10 · Java 17 (64-bit)**

23 mods. Every pin was checked on the project's own page on Modrinth or CurseForge on 2026-10-07; the exact evidence, including the ones where a newer build existed and was *rejected*, is in `pack/mods.lock.json` under `verification.sources` and `verification.note`.

| Legend | Meaning |
| --- | --- |
| `verified` | loader, MC version, environment and filename read from the project page |
| `inferred` | version + loader + environment confirmed; jar filename resolved by the build tool from the project API rather than quoted |

Nothing in this pack is a mirror, an edited jar, or a manual install. No 'latest'. No betas. No OptiFine.

---

## Foundation

*worldgen-independent core the whole pack stands on*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [Create](https://modrinth.com/mod/create/version/8amzvn9x) | `mc1.20.1-6.0.8` | 1.20.1 | both sides | verified |
| [Farmer's Delight](https://modrinth.com/mod/farmers-delight/version/SiIpcZzM) | `1.20.1-1.3.4` | 1.20.1 | both sides | verified |

**Create** — The engineering half of the premise: pumps, fluid transport and wind-bearing machinery rebuild the harbours, and 6.0.x bundles Flywheel and Ponder so the pack gains a written guide system (the Create Manual) without another mod.

**Farmer's Delight** — Food and hearth: cooking on a salt-flat where nothing grows is the Act I problem, and the cutting board is the one crafting surface that reads as salvage work rather than machinery.

---

## Landscape & structures

*the drained basin's silhouette*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [YUNG's Extras](https://modrinth.com/mod/yungs-extras/version/h4m8J7w8) | `1.20-Forge-4.0.3` | 1.20.1 | server side (safe in singleplayer) | verified |
| [YUNG's API](https://modrinth.com/mod/yungs-api/version/PJOYAmAs) | `1.20-Forge-4.0.6` | 1.20.1 | both sides | verified |
| [Paxi](https://modrinth.com/mod/paxi/version/C7buFh0l) | `1.20-Forge-4.0` | 1.20.1 | both sides | verified |

**YUNG's Extras** — Desert and ocean ruins, wells and obelisks: the stranded-harbour silhouette the premise needs, out of vanilla blocks, at 196 KB.

**YUNG's API** — Required library for YUNG's Extras; 8.7M downloads makes it the best-soaked 1.20.1 Forge build.

**Paxi** — Loads the Saltglass datapack (the reflected dimension and the three signature moments) into every new world automatically, so the pack cannot be launched into a world with no deep in it.

---

## Life

*the only fauna in the pack*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [Alex's Mobs](https://modrinth.com/mod/alexs-mobs/version/XoIASRVU) | `1.22.9` | 1.20.1 | both sides | verified |
| [Citadel](https://modrinth.com/mod/citadel/version/lTAAe4sZ) | `2.6.3` | 1.20.1 | both sides | verified |

**Alex's Mobs** — The only fauna in the pack: 85+ hand-animated creatures give the empty basin and the reflected sea something alive to share them with, and their aquatic set finally has a home in the Reflected Deep.

**Citadel** — Required library for Alex's Mobs; its 2026 release fixes a server-side memory leak in world-data loading, which is exactly the kind of leak a pack with its own dimension should not ship.

---

## Depth system — light and conjuration

*the magic pillar, deliberately not a combat pillar*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [Ars Nouveau](https://modrinth.com/mod/ars-nouveau/version/Hw2aD01e) | `4.12.7` | 1.20.1 | both sides | verified |

**Ars Nouveau** — The magic pillar is light and conjuration rather than damage: glyphs for illumination, conjured water, and warp portals give the pack its depth system and its only late-game travel, all themed on the salvage-priests' craft.

---

## Travel

*vertical travel that is earned and finite*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [Paragliders](https://modrinth.com/mod/paragliders/version/nudKlXXT) | `20.1.3` | 1.20.1 | both sides | verified |

**Paragliders** — The pack's entire vertical answer: gliding costs stamina and needs height, so it is travel, not flight — the refusal in DESIGN.md §3 is honoured by mechanics, not by config.

---

## Carrying & storage

*one backpack instead of six storage mods*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [Sophisticated Backpacks](https://modrinth.com/mod/sophisticated-backpacks/version/nSVHlIzZ) | `1.20.1-3.26.9.2194` | 1.20.1 | both sides | verified |
| [Sophisticated Core](https://modrinth.com/mod/sophisticated-core/version/yIBA2SnN) | `1.20.1-1.5.6.2378` | 1.20.1 | both sides | verified |

**Sophisticated Backpacks** — Salvage is carried before it is stored: one backpack with upgrades replaces six storage mods, and its placeable-backpack mode doubles as base storage during Act I when there is no room for a workshop.

**Sophisticated Core** — Required library for Sophisticated Backpacks, pinned to the build that shipped with the 3.23.1 backpack release rather than the newest one.

---

## Survival & recovery

*death in a large landscape must not cost an hour of walking*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [Corail Tombstone](https://modrinth.com/mod/corail-tombstone/version/nTAliy2r) | `forge-1.20.1-9.1.5` | 1.20.1 | both sides | verified |

**Corail Tombstone** — Death in an empty landscape must not cost an hour of walking: graves keep the salvage, and the mod's souls/prayer loop is the only place the pack lets the dead civilisation speak — respectfully, not as a threat.

---

## Quest book

*the pack's direction-of-travel, solo and co-op*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [FTB Quests](https://www.curseforge.com/minecraft/mc-mods/ftb-quests-forge/files) | `2001.4.22` | 1.20.1 | both sides | verified |
| [FTB Library](https://www.curseforge.com/minecraft/mc-mods/ftb-library-forge/files) | `2001.2.13` | 1.20.1 | both sides | verified |
| [FTB Teams](https://www.curseforge.com/minecraft/mc-mods/ftb-teams-forge/files) | `2001.3.2` | 1.20.1 | both sides | verified |
| [Architectury API](https://modrinth.com/mod/architectury-api/version/1MKTLiiG) | `9.2.14+forge` | 1.20.1 | both sides | verified |

**FTB Quests** — The quest system that carries all three acts: JSON on disk (so it diffs, validates and versions), works solo and in co-op, and its command reward is what wires the mirror dive and The Turning to the quest graph.

**FTB Library** — Shared GUI library for the FTB layer; it is what renders the quest book, so its config is where the pack's UI restraint lives.

**FTB Teams** — Required by FTB Quests, and the reason co-op shares quest progress instead of duplicating it — three harbours, three players, one graph.

**Architectury API** — Declared dependency of the FTB layer on Forge.

---

## Interface & information

*one recipe viewer, one map, both optional and quiet*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [EMI](https://modrinth.com/mod/emi/version/Axuu9I9R) | `1.1.24+1.20.1+forge` | 1.20.1 | client (optional on server) | verified |
| [Xaero's Minimap](https://modrinth.com/mod/xaeros-minimap/version/Juh6inLY) | `forge-1.20.1-26.5.0` | 1.20.1 | client (optional on server) | verified |

**EMI** — The single recipe viewer. Chosen over JEI/REI because its recipe tree and book-fill are load-bearing for a Create+Ars pack, and 'keep in inventory' removes the need for an inventory-manager mod.

**Xaero's Minimap** — Waypoints for three harbours across an empty 10k-block basin; shipped with the minimap disabled by default and only waypoints on, so it stays out of the way until asked for.

---

## Performance

*mid-range hardware, 6 GB client target*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [Embeddium](https://modrinth.com/mod/embeddium/version/UTbfe5d1) | `0.3.31+mc1.20.1` | 1.20.1 | client only | verified |
| [Oculus](https://modrinth.com/mod/oculus/version/iQ1SwGc3) | `1.20.1-1.8.0` | 1.20.1 | client only | verified |
| [ModernFix](https://modrinth.com/mod/modernfix/version/jAZ7Ge3d) | `5.27.83+mc1.20.1` | 1.20.1 | both sides | verified |

**Embeddium** — Rendering performance on mid-range hardware, and the only lawful host for shaders in a Forge pack: OptiFine is excluded outright because it cannot be verified against this stack.

**Oculus** — Makes shaders possible without making them required: the option lives in the video settings and the pack ships none, so the default experience is unshaded and identical on every machine.

**ModernFix** — Cuts load time and heap pressure for a 23-mod pack on 6 GB — the reason several QoL mods can be skipped rather than compensated for.

---

## Ambience

*wind on salt and surf under glass*

| Mod | Version | MC | Sides | Verified |
| --- | --- | --- | --- | --- |
| [AmbientSounds](https://modrinth.com/mod/ambientsounds/version/AuLdtrBY) | `6.3.8` | 1.20.1 | client only | verified |
| [CreativeCore](https://modrinth.com/mod/creativecore/version/J9tluyYl) | `2.12.38` | 1.20.1 | client only | verified |

**AmbientSounds** — A basin this large is silent in vanilla; wind on salt and surf somewhere below the glass are the pack's whole audio identity, and no other sound mod is needed.

**CreativeCore** — Required by AmbientSounds.

---

## Dependencies, all of them

| Mod | Requires |
| --- | --- |
| Alex's Mobs | citadel |
| YUNG's Extras | yungs-api |
| Sophisticated Backpacks | sophisticated-core |
| Oculus | embeddium |
| AmbientSounds | creativecore |
| FTB Quests | ftb-library, ftb-teams, architectury |
| FTB Library | architectury |
| FTB Teams | ftb-library, architectury |

Create 6.0.8 **bundles** Flywheel and Ponder inside its own jar. Installing a separate Flywheel is the single most common way a Create 6 pack fails to start, and is a licence-redundancy problem besides. Do not add one.

## Considered and rejected

Every one of these was verified for 1.20.1 Forge and then dropped anyway, because being compatible is not the same as earning a place.

| Mod | Why it is not in the pack |
| --- | --- |
| GeckoLib | Was in the first draft on the assumption that Alex's Mobs needs it. The registry shows Alex's Mobs' required dependency is Citadel, and nothing else in the pack uses GeckoLib. Removed rather than kept as insurance. |
| OptiFine | Cannot be verified against Embeddium + Oculus + Create 6 + Ars Nouveau as a stack; it also replaces render code that Embeddium replaces. Excluded per the brief's own rule. |
| Terralith 2.4.4 | Verified 1.20.1 Forge-capable, but 'almost 100 biomes' contradicts a basin that must feel emptied out, and it would be a second worldgen stack on top of the pack's own datapack. Rejected for cohesion, not compatibility. |
| Rubidium | Overlaps Embeddium; one renderer only. |
| Iris | Fabric only on this Minecraft version; Oculus is its Forge-side equivalent. |
| JEI + REI + Create Schematics etc. | One recipe viewer only. EMI covers book-fill and recipe trees. |
| Sophisticated Storage / Functional Storage / Storage Drawers | Sophisticated Backpacks' placeable mode plus vanilla barrels and shulker boxes cover Act I–II; a second storage family would be superfluous. |
| FTB Chunks / FTB Essentials / FTB XMod Compat | Claim protection and keybind utility are server-side decisions for small co-op (documented in README); shipping them would add 2–3 jars for settings a host can flip. |
| ExtraQuests / FTB Quests UI Overhaul | Both verified for 1.20.1 Forge, but the pack needs no non-standard task types (the two it would have been used for are done with a scoreboard and a command in the datapack), and UI Overhaul is a re-skin of a screen this pack restyles by config instead. |
| YUNG's Better Dungeons | Would have provided the Act III dungeon, but the drowned cathedral is hand-built in the pack's datapack; a random dungeon generator next to a scripted one reads as two packs. |
| Cataclysm / Iron's Spellbooks / Mowzie's Mobs | All would supply a boss. The pack refuses a boss: the culminating objective is a place and a choice. Also avoids their combat-power escalation before Act III. |
| Parachest / Elytra Slot / AnyFlight / creative flight mods | Explicit refusal 2 in DESIGN.md. |
| Horror, sanity, fear, 'don't look at it' mods | Explicit refusal 1 in DESIGN.md. |
| Curios API | Would only exist to hold a Baubles-style slot for Paragliders; Paragliders uses a vanilla chest slot here. Re-check before adding any accessory mod. |
| Flywheel / Ponder (standalone jars) | Bundled inside Create 6.0.8. Adding them separately is the most common Create 6 startup crash and is a licence-redundancy problem as well. |

## Server-side exclusion list

These jars are client-only or client-side and are **not** part of the server export. Putting any of them in a headless server's `mods/` folder is the usual cause of a server that will not boot.

| Mod | Why |
| --- | --- |
| Embeddium | client only |
| Oculus | client only |
| Xaero's Minimap | client (optional on server) |
| AmbientSounds | client only |
| CreativeCore | client only |
| EMI | client (optional on server) |

