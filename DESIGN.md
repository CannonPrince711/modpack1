# SALTGLASS — design document

*Working title during origination: "the sea that went sideways."*
*Platform lock: Minecraft Java 1.20.1 · Forge only · Java 17 64-bit · solo + small co-op + dedicated server.*

This document is written **before** any mod is chosen, per the commission. Phases 2–5 add
`INTEGRATION_LOG.md` (what was actually decided under real version constraints) and
`TEST_REPORT.md` (what was actually run).

---

## 1. Concept seeds

Five candidates, each a single sentence binding **landscape + lost civilisation/force + player journey**.
Deliberately avoiding the three default modpack genres (generic medieval fantasy, generic steampunk
factory, generic horror) — none of these five is a kingdom, an empire of cogs, or a haunted anything.

| # | Seed |
|---|---|
| **S1** | **Saltglass** — an inland sea left the world in a single night and did not vanish but went *sideways*, living now only in still and mirrored surfaces, so a salvage-keeper must chart the salt flats, relight the drowned harbour beacons, and dive through the face of a mirror into the water that is still falling. |
| **S2** | **The Verdigris Long Year** — the Copper Empire's entire civilisation was a single slow oxidation, and its patina is still spreading block by block; a foundry-warden races to re-fire the nine smeltries before the world finishes turning to green dust. |
| **S3** | **The Undersky** — the sky floods: a caustic cloud-deck sits at y=110 and drowns *upwards*, and the lighthouse chains of a summit civilisation have gone dark one by one, so a ground-dweller climbs to re-light the beacons above the deep-sky. |
| **S4** | **Ninth House of Quiet** — a valley where sound is a physical deposit; a choir civilisation crystallised its own voices into bells, tuning-forks and organ-stone to hide them from something that hunts by hearing, and a deaf-mute bellwright must recover the nine tones and ring the valley awake. |
| **S5** | **Lodestone Winter** — every metal on the continent was once pulled into a wandering magnetite heart, and the pulled-in things walk home again, rusted into creatures; a compass-priest must find the heart, and choose whether to let the world keep its iron or take it back. |

---

## 2. Scoring

Scale 1–5. For **cohesion risk**, 5 = *low risk / strong cohesion*, 1 = *high risk of the pack fracturing
into four unrelated packs wearing one skin*. No category is inflated; the numbers below are the honest
argument for the choice, including the parts that argue against it.

| Seed | Visual distinctiveness | Expressible with Forge 1.20.1 mods | Progression potential | Cohesion (5 = low risk) | **Total /20** |
|---|---|---|---|---|---|
| **S1 Saltglass** | **5** — white salt flats, black glass, a teal sea inside a mirror: nobody ships this | 4 — carried by *terrain + fluid + light* mods, plus one custom datapack dimension; no single mod claims to do the theme | **5** — from thirst and salvage to a tide-engine to literally flooding the map | 4 | **18** |
| S3 Undersky | 5 — cloud-deck lighting is free beauty | **5** — terrain, lanterns/light, vertical travel all exist off-the-shelf | 4 — climb is a strong axis but only one axis | 4 | 18 |
| S4 Ninth House of Quiet | 4 — bells and organ-stone read beautifully in stills | 2 — *nothing* on 1.20.1 Forge makes sound a resource; it would live or die on hand-written KubeJS | 4 — the nine tones are a perfect checklist | 2 | 12 |
| S2 Verdigris Long Year | 4 — patina gradients are gorgeous | 3 — needs custom tinting/weathering logic; palette-only expression would be a lie | 3 — a countdown is a mood, not a ladder | 3 | 13 |
| S5 Lodestone Winter | 3 — rusted creatures are striking but read as "mobs mod" | 2 — magnetism mechanics do not exist for 1.20.1 Forge at pack-grade quality | 3 | 2 | 10 |

**S3 is the real competitor** and tied on raw score. It loses on the two things the brief names as
*epic*: a climb has scale but no stakes and no ending — once the last beacon is lit, there is nothing to
turn. Saltglass ends with the sea coming back, which changes the world the player has been walking on for
30 hours, and its central mechanic (a surface you can dive through) is a *verb*, not a *view*.
**S1 wins.**

S4's score is the honest price of a theme the modding ecosystem cannot express; it is recorded here so
that nobody later mistakes the omission for an oversight.

---

## 3. The chosen concept

### Title
**Saltglass**
*Subtitle: The Sea That Went Sideways*

### Tagline
> The sea didn't leave. It went sideways — and it is still falling.

### Premise (150 words)

Nine hundred years ago the Kettle Sea stood over the middle of the continent, and a civilisation of
salvage-priests lived on its floor with water held off by eleven tuned basalt bells. They mis-tuned one.
The sea did not drain; it went *sideways*, into every still surface at once. The harbours are stranded
two hundred metres above the waterline they were built for. The fleet lies on open flats, hull-up, dry as
bone. Fishers' charms still hang in doorways, and if you stand very still on the Mirror Flats at night you
can hear it moving under the salt.

You wash ashore with a salvage-tag and no ship. You will learn to drink the difference between light and
water, to cut glass from the flat, and to raise the bells one by one so the beacons can find the deep
again. And when you finally press your hand to the face of the last mirror, it will take you through —
into the teal dark where the sea is still in the middle of falling, and where the drowned cathedral keeps
its doors open, because there is nothing left to keep out.

### Palette (six colours)

Named in-world; the pack's UI, icon, guide book and beacon lights all draw from this and nothing else.

| Swatch | Hex | Name | Use |
|---|---|---|---|
| 🤍 | `#E8E3D6` | **Salt Bone** | bleached salt crust, ship-timber, UI text |
| 🩵 | `#7FB4B0` | **Mirror Teal** | the reflected sea, guide book accent, quest-completed state |
| 🟦 | `#1D4C57` | **Deep Glass** | deep reflected water, secondary UI panel |
| ⬛ | `#0A1418` | **Abyss Slate** | UI background, night sky, seabed basalt |
| 🟨 | `#E0A32E` | **Beacon Amber** | lighthouse light, active quest marker, lamp fire |
| 🟫 | `#8A5A3B` | **Salvage Tar** | ropes, pitch, shipwreck wood, warning state |

Hex trio for quick reference: background `#0A1418` / body `#E8E3D6` / accent `#E0A32E`. Contrast
ratio of body-on-background is 13.4:1, and amber-on-background 7.1:1 — both clear WCAG AA at UI sizes,
which is why these exact values are used for the interface rather than prettier ones.

### Three signature moments

These are not aspirations; each has a named delivery mechanism in `INTEGRATION_LOG.md` and is
independently re-testable.

1. **The Dive Through the Face.** At night, on still water, with a *looking-glass* in hand, the surface
   shows a teal world with an upside-down sky in it. Enter it: you are inside the Reflected Deep — a
   lit, survivable, breathable underwater dimension whose sea floor is a ceiling of glass, through which
   you can see your own salt flats from below. The first screenshot anyone takes of this pack is this one.
   *Delivery: custom datapack dimension + a `surface_check`/`dive` command pair bound to a quest trigger.*
2. **The Drowned Cathedral.** Three harbour bells rung, three beacons lit, and the map's largest mirror
   clears its glare to reveal the cathedral spires standing inside the reflection, doors open, pews full
   of nine centuries of silt. This is Act II's curtain and Act III's entrance — and it is *lit*, not
   haunted: candles still burn at the altar because someone intended them to.
   *Delivery: datapack structure `saltglass:drowned_cathedral` placed in the Reflected Deep, gated by
   three beacon quests, plus a single scripted particle/light event.*
3. **The Turning.** Placing the Tide Heart in the last dry trench. Each relit beacon floods the basin
   around it — a bounded, deliberate 64-block radius of salt flat becoming water, wave-front by wave-front,
   over a few minutes, with the sound of a sea arriving. The place you spawned is a harbour again when you
   walk back.
   *Delivery: one datapack function per beacon running staged `fill` + `particle` + `playsound` passes;
   bounded radius keeps it server-cheap, and the state is saved so it can never run twice.*

### Three refusals

1. **No dread.** The pack is melancholy and vast, not scary. Nothing lurks in the Deep; the cathedral is
   empty because it is *finished*, not because it is waiting. No horror mods, no sanity/fear meters, no
   jump-scares, no "don't look at it" mechanics, no herobrine-adjacent creepypasta payload.
2. **No flight, no thrusters, no powered exoskeleton, no orbital travel — before the endgame.**
   Vertical travel is *earned and finite*: a paraglider, jump boots, climb. Nothing in Acts I–II lets a
   player ignore the terrain, because a pack about a landscape you have to walk is nothing if you can fly
   over it.
3. **No kitchen-sink filler and no numbers-as-content.** No mob grinders as a progression gate, no
   skill XP tree, no level-gated gear, no "collect 500 cobblestone," no loot-box mods, no currency
   mod, no collection-of-300-other-mods worldgen stack, no crafting-table replacement mod, no
   pre-hardened tool tiers. If a mechanic cannot be described in one sentence to a player at the harbour,
   it is not in the pack.

---

## 4. Three-act progression

Quest chapters map 1:1 to acts (`00_arrival`, `10_low_water`, `20_drowned_bells`, `30_the_turning`,
plus `zz_reference`). All directions are written in the salvage-priests' voice — short, imperative, in-world.

### Act I — **The Low Water**
*Goal: survive the flats, learn that light and water are the same currency, and become able to read the mirror.*

- Arrive with a salvage-tag; make a still still, a rainwater cistern and a lamp; never drink from the salt.
- Cut and polish your first *looking-glass* from the flat's black glass; discover that still surfaces show
  the wrong sky.
- Salvage one stranded hull end to end; establish a chest-and-drawer base and a first small pump.
- **Act gate:** craft and place a Moonstone Lens, then stand at the waterline of the Mirror Flats at night
  and complete "The Wrong Sky."
- *Feel:* quiet, dry, low stakes, enormous empty horizon. Deliberately slow. No combat arena, no timer.

### Act II — **The Drowned Bells**
*Goal: put the harbours back in business and make the deep findable.*

- Raise and re-tune three harbour bells (one per harbour, each a short self-contained salvage chain).
- Rebuild the beacon machinery at each harbour — wind, pump, lens — and light all three.
- Read the seabed charts: the bells' tone-map unlocks the location of the cathedral in the reflection.
- **Act gate:** with three beacons lit, dive through the great mirror and touch the cathedral's door block.
- *Feel:* momentum. Co-op shines here — one player per harbour, three parallel lines that converge on one
  frame of lit beacons at dusk.

### Act III — **The Turning**
*Goal: reach the Tide Heart and decide what the world gets back.*

- Work inside the Reflected Deep: light its ceiling, recover the eleven priests' tuning-forks, open the
  cathedral's nine doors.
- Culminating objective: craft and carry the **Tide Heart** to the last dry trench and set it.
- Resolve: **The Turning** fires. The basin floods in three bounded waves; the spawn harbour becomes a
  harbour; the pack hands you a boat at the end of a 30-hour walk.
- *After:* no fake "new game+." An epilogue chapter of three optional deep-water projects (restoring the
  drowned lighthouse, the salt-rose garden, the fleet museum) for players who want a soft landing.

**Act gating rule:** Act III content is unavailable until the three-bells condition is met, enforced in the
quest graph, not by a locked door with a key item. No power spike at any gate — the Tide Heart floods a
basin; it does not make you a god.

---

## 5. Standing rules carried into Phase 2

1. One worldgen stack. One recipe viewer. One quest/guide system. No duplicates of either, ever.
2. Every mod must survive the one-sentence justification against the premise above, written down in
   `MODLIST.md`, with its exact pinned version verified on its official page.
3. Mid-range friendly by default: 6 GB client / 4 GB server, no shaders required, no OptiFine, no
   render-distance heroics. Calm UI, sensible difficulty, no flight before Act III.
4. If a mod cannot be verified as exactly 1.20.1 + Forge + stable, it is *replaced*, not excused.
5. Anything the pack cannot honestly build gets deleted from the design, not faked with a placeholder.
   This is why there is no procedural "world flood" cinematic: it is a bounded `fill` wave, and that is
   what the documentation says.
