# Turning wave 3 — radius 38 around each raised harbour.
execute at @e[tag=sg_harbour_1,limit=1] run fill ~-38 ~-1 ~-38 ~38 ~1 ~0 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_1,limit=1] run fill ~-38 ~-1 ~1 ~38 ~1 ~38 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_1,limit=1] run particle minecraft:splash ~ ~1 ~ 38.0 0.2 38.0 200 0.4 normal
execute at @e[tag=sg_harbour_1,limit=1] run playsound minecraft:entity.player.splash master @a ~ ~ ~ 3.0 0.6
execute at @e[tag=sg_harbour_2,limit=1] run fill ~-38 ~-1 ~-38 ~38 ~1 ~0 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_2,limit=1] run fill ~-38 ~-1 ~1 ~38 ~1 ~38 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_2,limit=1] run particle minecraft:splash ~ ~1 ~ 38.0 0.2 38.0 200 0.4 normal
execute at @e[tag=sg_harbour_2,limit=1] run playsound minecraft:entity.player.splash master @a ~ ~ ~ 3.0 0.6
execute at @e[tag=sg_harbour_3,limit=1] run fill ~-38 ~-1 ~-38 ~38 ~1 ~0 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_3,limit=1] run fill ~-38 ~-1 ~1 ~38 ~1 ~38 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_3,limit=1] run particle minecraft:splash ~ ~1 ~ 38.0 0.2 38.0 200 0.4 normal
execute at @e[tag=sg_harbour_3,limit=1] run playsound minecraft:entity.player.splash master @a ~ ~ ~ 3.0 0.6
tellraw @a [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"the harbour wall is under.","color":"#7FB4B0"}]
