# Turning wave 2 — radius 26 around each raised harbour.
execute at @e[tag=sg_harbour_1,limit=1] run fill ~-26 ~-1 ~-26 ~26 ~1 ~0 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_1,limit=1] run fill ~-26 ~-1 ~1 ~26 ~1 ~26 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_1,limit=1] run particle minecraft:splash ~ ~1 ~ 26.0 0.2 26.0 200 0.4 normal
execute at @e[tag=sg_harbour_1,limit=1] run playsound minecraft:entity.player.splash master @a ~ ~ ~ 3.0 0.6
execute at @e[tag=sg_harbour_2,limit=1] run fill ~-26 ~-1 ~-26 ~26 ~1 ~0 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_2,limit=1] run fill ~-26 ~-1 ~1 ~26 ~1 ~26 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_2,limit=1] run particle minecraft:splash ~ ~1 ~ 26.0 0.2 26.0 200 0.4 normal
execute at @e[tag=sg_harbour_2,limit=1] run playsound minecraft:entity.player.splash master @a ~ ~ ~ 3.0 0.6
execute at @e[tag=sg_harbour_3,limit=1] run fill ~-26 ~-1 ~-26 ~26 ~1 ~0 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_3,limit=1] run fill ~-26 ~-1 ~1 ~26 ~1 ~26 minecraft:water replace minecraft:air
execute at @e[tag=sg_harbour_3,limit=1] run particle minecraft:splash ~ ~1 ~ 26.0 0.2 26.0 200 0.4 normal
execute at @e[tag=sg_harbour_3,limit=1] run playsound minecraft:entity.player.splash master @a ~ ~ ~ 3.0 0.6
tellraw @a [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"the water is over the anchor stones.","color":"#7FB4B0"}]
