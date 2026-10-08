# Optional mods

Mods just outside Dungeon Delver's Odyssey: not in `mods.lock.json`, close enough to the theme (class-based action RPG,
dungeons, bosses, villages) that you may want them. None are tested with the pack.

Pack size: **142 of 150** mods, so 8 slots free.

Every row was checked against Modrinth on 2026-10-07 for a **Minecraft 1.20.1 Forge release**. "Client / Server" is the side
the mod declares (req = required, opt = optional, - = unsupported). Versions are the latest release at that check and drift.

## How to add one

1. Add it to `mods.lock.json` with the same fields as the other entries (project and version IDs, URL, SHA-1, SHA-512,
   size, `required_dependencies`) and pull in its required dependencies.
2. Add an `env` entry (`{"client": ..., "server": ...}`) copied from the table below. `tools/build_pack.py` writes it into
   the `.mrpack`, so client-only mods stay off the dedicated server. Mods that run server-side keep client `optional`
   at least, because singleplayer runs an integrated server from the client install.
3. Run `python3 tools/build_pack.py`, then start a **new world**. Worldgen mods do not change existing chunks.
4. New structure mods: add their chest tables to `overrides/config/apotheosis/adventure.cfg`, then re-run
   `tools/gen_gear_loot.py --loot-tables <server dump>` so they also get tiered gear. Weapon or armor mods: run
   `tools/gen_gear_rebalance.py` first (see `README.md`).

## Performance alternatives (the pack already has ModernFix, FerriteCore, Embeddium, Entity Culling, ImmediatelyFast, Noisium, Async Locator, Clumps, Memory Leak Fix, spark)

| Mod | Slug | Client / Server | Notes |
| --- | --- | --- | --- |
| Canary | `canary` | opt / opt | Lithium-style server tick and AI optimisation. 0.3.3, last updated 2024-02. Untested with this many mods. |
| Saturn | `saturn` | opt / opt | Memory optimisation. 0.1.3, last updated 2024-02. Overlaps ModernFix. |
| FastSuite | `fastsuite` | req / req | Faster crafting. Needs one more mod. |

## Immersion and interface (client side; install per player)

| Mod | Slug | Client / Server | Notes |
| --- | --- | --- | --- |
| Xaero's Minimap | `xaeros-minimap` | req / opt | Alternative to JourneyMap, which is in the pack. Pick one. |
| Xaero's World Map | `xaeros-world-map` | req / opt | Pairs with the minimap. |
| Chat Heads | `chat-heads` | req / - | Player heads in chat. |
| Shoulder Surfing Reloaded | `shoulder-surfing-reloaded` | req / - | Over-the-shoulder camera. Overlaps Better Third Person, which is in the pack, and Epic Fight's own camera. |
| Not Enough Animations | `not-enough-animations` | req / - | Player animation changes. **Likely to clash with Epic Fight and Player Animator.** Untested. |

## Economy add-ons (the pack has Lightman's Currency)

| Mod | Slug | Client / Server | Notes |
| --- | --- | --- | --- |
| Create: Numismatics | `numismatics` | req / req | A second currency system on Create. Do not run both currencies. Needs Create, which is in the pack. |

## Bigger content (heavy)

| Mod | Slug | Client / Server | Notes |
| --- | --- | --- | --- |
| Alex's Caves | `alexs-caves` | req / req | Large underground biomes and bosses. Needs Citadel. Competes with YUNG's Better Caves and current dungeon density. |
| Iron Chests | `iron-chests` | req / req | Overlaps Tom's Simple Storage and Sophisticated Storage, both in the pack. |

## Do not combine

| Mod | Slug | Why |
| --- | --- | --- |
| Better Combat | `better-combat` | Replaces the attack system. Do not combine with Epic Fight. |

## Parked until something changes

| Mod | Slug | Why |
| --- | --- | --- |
| Battle Arts and Battle Arts API | `battle-arts`, `battle-arts-api` | Battle Arts 20.14.16.10 crashes against the pinned Epic Fight 20.14.17 (`NoClassDefFoundError: ExCapBuilderCreationEvent`). The only stable API for it (20.14.16.1) has a malformed Minecraft version range. Revisit if the Epic Fight pin changes. |
| Presence Footsteps (Forge) | `presence-footsteps-forge` | No stable Forge 1.20.1 release found. |
| Minecolonies, Sound Physics Remastered, Eating Animation | | No Forge 1.20.1 release found. |
| Cobblemon | `cobblemon` | Available, but a different game. |
| Sodium | `sodium` | No Forge 1.20.1 release; Embeddium is the Forge route and is in the pack. |

## Now in the pack

These started on this list or were requested, so they are no longer optional.

| Group | Mods |
| --- | --- |
| Storage | Tom's Simple Storage, Sophisticated Storage and Sophisticated Backpacks (with Sophisticated Core). Backpacks sit in the Curios `back` slot; `classes.js` exempts them from the class slot restriction. |
| Structures | Dungeons and Taverns plus its Ancient City, Pillager Outpost, Stronghold and Swamp Hut overhauls; CTOV - Create: Structures and Create: Structures (a 2023 beta, pinned with a `release_filter_exception`). |
| Classes | Paladins & Priests, Rogues & Warriors, Wizards, Archers (RPG Series), with Spell Engine, Spell Power Attributes, Structure Pool API and Armor Model API. Villager Recruits. Ars Nouveau. |
| Currency | Lightman's Currency, plus its Tech machines and Villager Tycoon addon. |
| Performance | Embeddium, Entity Culling, ImmediatelyFast, Dynamic FPS (client); Clumps, Memory Leak Fix, spark (both); Async Locator, Noisium (server). |
| Interface | Entity Model Features (with Entity Texture Features; client only), JourneyMap, Oculus, Mouse Tweaks, Controlling (with Searchables), Betthttps://github.com/CannonPrince711/modpack1er Third Person. |
| Immersion | AmbientSounds (with CreativeCore), Falling Leaves, Sodium Dynamic Lights (with Sodium Options API) on the client; Immersive Weathering and Visual Workbench on both sides. |
| Content | Alex's Mobs (with Citadel), Dungeon Crawl, Immersive Armors, L2 Weaponry (with L2 Library and L2 Complements). Their gear went through `tools/gen_gear_rebalance.py`. |
| Dimensions | Jaden's Nether Expansion (with Elysium API) and Incendium Legacy; Nullscape and Moog's End Structures (with Moog's Structure Lib). |
| Colonies | MineColonies with Structurize, BlockUI and Domum Ornamentum. There are no pre-built colonies: a colony needs a player to place a Town Hall. |
| Voices | ElevenLabs library voices for the opening (see `README.md`). |
