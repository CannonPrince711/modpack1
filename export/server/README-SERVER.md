# Saltglass — dedicated server

Tested target: **Minecraft 1.20.1 · Forge 47.4.10 · Java 17 64-bit**.

## 1. Install Forge

    java -jar forge-1.20.1-47.4.10-installer.jar --installServer
    # -> produces libraries/, run.sh / run.bat and a user_jvm_args.txt

SHA-1 of the installer: `27b38c97615d138101caa13c01e6bfda6176dea3`
SHA-1 of the universal jar: `9d27acaf82445da3419c21d5f2f87e86ff0f8abe`

## 2. Put the mods in place

`server-mods.tsv` lists exactly which jars a server needs, with version and source.
Copy them into `mods/`. Do **not** install the client-only jars — they are listed in
`README.md` under "client-only" and will crash a headless server.

## 3. Put the pack data in place

    defaultconfigs/saltglass_datapack/     -> config/paxi/datapacks/saltglass/
    server.properties                      -> ./server.properties
    jvm_args.txt                           -> your start script (-Xmx4G for 4 players)

Paxi loads `config/paxi/datapacks/*` into every world, so the datapack does not need to be
copied per-world and cannot be lost with a world reset.

## 4. Start

    ./run.sh

Expected on first start: `Done (NN.NNNs)! For help, type "help"`. The datapack prints one
line to chat: `[Saltglass] The sea is still falling.`

## 5. Know before you host

* **Command blocks must stay enabled.** The three signature moments run as datapack
  functions invoked by quest rewards.
* **`allow-flight=true`** is required by the Paraglider. The pack ships no creative flight,
  no elytra and no jetpacks, and Act III is the only act that changes the map.
* **Co-op:** FTB Teams is installed, so quest progress is shared per team. `/team` creates
  one. Three harbours, three players, one graph.
* **The Turning is global and permanent.** When one player sets the Tide Heart, the basin
  floods for everybody. That is intentional; settle it with your players first.
* Back up `world/` before the Turning. It is ~96x96 blocks of terrain change at each
  harbour, applied by `fill` in four waves.
