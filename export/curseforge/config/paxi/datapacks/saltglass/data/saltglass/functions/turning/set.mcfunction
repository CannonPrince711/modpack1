# Signature moment 3 — the Turning. Places the trench, spends the Tide Heart,
# and hands the job of flooding to the staged wave runner.
execute if score #turning sg_state matches 1.. run return fail
execute if score #harbour1 sg_state matches 0 run return run tellraw @s [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"The bells are not awake. Nothing would answer the Heart.","color":"#8A5A3B"}]
scoreboard players set #turning sg_state 1
clear @s minecraft:heart_of_the_sea 1
execute in saltglass:reflected_deep run place structure saltglass:tide_trench 24 -48 24
scoreboard players set #turning_t sg_state 0
scoreboard players set #turning_wave sg_state 1
playsound minecraft:item.trident.thunder master @a ~ ~ ~ 4.0 0.5
tellraw @a [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"The Tide Heart is set. Now the water decides how much of this world it wants back.","color":"#7FB4B0"}]
advancement grant @s only saltglass:the_turning
