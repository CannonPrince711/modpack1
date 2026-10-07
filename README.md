# SALTGLASS
### The sea that went sideways

Minecraft **1.20.1** · Forge **47.4.10** · Java **17 (64-bit)** · solo and small co-op · dedicated server ready

---

Nine hundred years ago an inland sea did not drain. It went *sideways* — into every still surface
at once. The harbours stand two hundred metres above the waterline they were built for, the fleet
lies hull-up on the dry, and at night, if you crouch on a sheet of glass and the light is wrong,
you can go **through**.

You wash ashore with a salvage-tag and no ship. Three harbour bells are still on their bearings
somewhere out on the basin. The drowned cathedral is still open in the reflection, and the water
is still in the middle of falling.

> This pack is **melancholy and vast, not frightening.** There is nothing in the deep that hunts
> you. The cathedral is empty because it is finished, not because it is waiting for you.

---

## Install

### Modrinth App / Prism / ATLauncher (recommended)

1. Download **`export/saltglass-1.0.0.mrpack`**.
2. Drag it onto the Modrinth App (or *Add instance → From file* in Prism).
3. The launcher creates the instance, pulls **Forge 47.4.10** and all 23 mods by itself.
4. **Allocate 6 GB of RAM** in the instance settings. Java 17 is required; the launcher usually
   finds one, and if it does not, point it at any 64-bit JDK 17.
5. Play.

### Already have a Forge 1.20.1 instance

1. Install **Forge 1.20.1-47.4.10** ([installer](https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.1-47.4.10/forge-1.20.1-47.4.10-installer.jar),
   SHA-1 `27b38c97615d138101caa13c01e6bfda6176dea3`).
2. Copy everything in `export/curseforge/` into your instance folder — `config/` and
   `defaultconfigs/` included, because the datapack lives there.
3. Download the 23 jars listed in **`MODLIST.md`** into `mods/`.
4. Launch.

### Dedicated server

`export/saltglass-1.0.0-server.zip` contains the mod manifest, `server.properties`,
`jvm_args.txt` and a step-by-step `README-SERVER.md`. A helper script that downloads and
verifies every server mod is in it.

---

## First five minutes

You spawn on salt with nothing. Do these in order and the pack will teach you itself:

1. **Punch a tree, knap stone.** Nothing here was left for you.
2. **A cauldron of rainwater.** Salt will kill you slowly and politely. Water will not.
3. **A cutting board and a cooking pot** (Farmer's Delight). This is a pack where a proper meal
   is worth the time.
4. **Open the quest book.** *The Salvage-Priests' Log*, bound to `Q` by default. It is the only
   direction the pack gives you, and it is written in-world: no tooltips-with-attitude, no
   tutorial NPC, no "welcome to modded Minecraft" wall of text.
5. **Read the chapter called "The Wrong Sky."** That is where the pack actually starts.

---

## The three moments

| # | Moment | How you get there |
|---|---|---|
| 1 | **The Dive Through the Face** | Lay **tinted glass** flat on the flats, **stand on it, crouch, at night.** You pass through into the Reflected Deep — a lit, breathable, upside-down sea with a ceiling of glass. The deep will not let you drown. |
| 2 | **The Drowned Cathedral** | Raise the **three harbour bells** and light their beacons. The third one opens the cathedral's three doors and you walk in. Nine bays. The altar candles are still burning. |
| 3 | **The Turning** | Take a **Heart of the Sea** to the one trench on the whole basin that is still dry, and set it. The sea comes back in four waves — about fifteen seconds, ninety-six blocks of basin at each harbour. Your first camp goes under. |

There is no final boss. The last thing you do is put a piece of the old waterline into a socket and
stand back. Everything after that is the Epilogue chapter.

---

## What this pack refuses to do

* **No dread.** No horror mods, no sanity meters, no jump-scares, no "don't look at it."
* **No flight before Act III.** The Paraglider glides on stamina from a height you had to earn.
  No elytra, no jetpacks, no creative flight, no orbital anything.
* **No filler and no numbers-as-content.** No XP tree, no level-gated gear, no collection quotas,
  no loot boxes, no currency, no second storage family, no second recipe viewer, no second
  worldgen stack.

---

## Options and keys

The pack binds almost nothing, and disables nothing you already know.

| Key | Action |
|---|---|
| `Q` | FTB Quests — the Salvage-Priests' Log |
| `M` | Xaero's Minimap settings (waypoints only; the minimap itself is off) |
| `Ctrl`/`O` | EMI — search items, `R` for recipes, `U` for uses |
| `W` (hold) | Create's Ponder overlay, on any Create block — the illustrated guide |
| `Sneak` | the dive, when you are standing on tinted glass |

Everything else is the mod's own default. A full audited list, including what was deliberately
*not* rebound, is in `INTEGRATION_LOG.md`.

### Graphics

Mid-range friendly by default: **10 chunks render / 8 simulation**, fancy graphics, no shaders.
**Embeddium** and **Oculus** are installed so a shaderpack is *possible* — none is shipped and
none is required, and the pack looks the same for everyone without one. There is no OptiFine
support and there will not be.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Crash at startup mentioning **Flywheel** | You added a standalone Flywheel jar. Create 6.0.8 bundles it. Delete the extra jar. |
| Crash mentioning **Oculus** or a renderer | You added a second renderer (Sodium/Rubidium/OptiFine). Only Embeddium belongs in this pack. |
| **`[Saltglass] The sea is still falling.`** never prints in chat | The datapack did not load. Check that `config/paxi/datapacks/saltglass/` exists and Paxi is installed. |
| No deep, quest "The Wrong Sky" will not complete | Same as above — the dimension comes from that datapack. |
| Crouching on tinted glass does nothing | It must be **night** and you must be standing **directly on tinted glass**. The quest chapter "The Wrong Sky" says so in-world. |
| Server will not boot | You copied client-only jars into `mods/`. See the exclusion list at the end of `MODLIST.md`. |

---

## Repository layout

```
DESIGN.md                 the concept, the five seeds, the scoring, the chosen pack
INTEGRATION_LOG.md        every integration decision, and the pins that were rejected
MODLIST.md                all 23 mods, version, purpose, link, licence note, exclusions
CREDITS_AND_LICENSES.md   attribution and licence position
TEST_REPORT.md            exactly what was and was not run — read this one honestly
CHANGELOG.md              1.0.0
pack/mods.lock.json       the single source of truth every artifact is generated from
pack/overrides/           config/, defaultconfigs/, the quest book, the datapack
pack/server/              server.properties, jvm_args.txt, README-SERVER.md
tools/                    build_pack.py, gen_content.py, gen_structure.py, gen_docs.py, make_icon.py
export/                   the launcher artifacts
```

Everything shipped is generated from `pack/mods.lock.json` plus the generators in `tools/`, so the
manifests, the mod list and the docs cannot disagree with each other. Rebuild with:

```
python3 tools/gen_structure.py     # the .nbt builds
python3 tools/gen_content.py       # datapack + quest book + configs, with its own checks
python3 tools/gen_docs.py          # MODLIST.md
python3 tools/make_icon.py export/saltglass-icon/icon.png
python3 tools/build_pack.py        # validates the whole thing, then writes export/
```
