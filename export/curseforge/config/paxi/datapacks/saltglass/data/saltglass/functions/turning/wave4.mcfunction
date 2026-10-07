# Turning wave 4 — radius 48 around each raised harbour.
execute at @e[tag=sg_harbour_1,limit=1] run fill ~-48 ~-2 ~-48 ~48 ~1 ~0 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_1,limit=1] run fill ~-48 ~-2 ~1 ~48 ~1 ~48 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_1,limit=1] run particle minecraft:bubble ~ ~ ~ 48.0 0.5 48.0 300 0.6 normal
execute at @e[tag=sg_harbour_2,limit=1] run fill ~-48 ~-2 ~-48 ~48 ~1 ~0 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_2,limit=1] run fill ~-48 ~-2 ~1 ~48 ~1 ~48 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_2,limit=1] run particle minecraft:bubble ~ ~ ~ 48.0 0.5 48.0 300 0.6 normal
execute at @e[tag=sg_harbour_3,limit=1] run fill ~-48 ~-2 ~-48 ~48 ~1 ~0 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_3,limit=1] run fill ~-48 ~-2 ~1 ~48 ~1 ~48 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_3,limit=1] run particle minecraft:bubble ~ ~ ~ 48.0 0.5 48.0 300 0.6 normal
tellraw @a [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"The Kettle Sea is shallow, cold and back. Your first camp is underwater. Walk back at dusk and you will see what you did.","color":"#E0A32E"}]
playsound minecraft:block.conduit.activate master @a ~ ~ ~ 4.0 0.4
title @a title [{"text":"THE TURNING","color":"#E0A32E"}]
title @a subtitle [{"text":"the sea came back sideways","color":"#7FB4B0","italic":true}]
give @a minecraft:oak_boat 1
scoreboard players set #turning_wave sg_state 4
scoreboard players set #turning_done sg_state 1
