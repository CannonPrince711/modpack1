# Signature moment 1 — the Dive Through the Face.
execute if score @s sg_divecooldown matches 1.. run return fail
scoreboard players set @s sg_divecooldown 200
particle minecraft:splash ~ ~ ~ 1.2 0.4 1.2 40 0.35 normal
particle minecraft:bubble ~ ~1 ~ 1.0 0.5 1.0 30 0.1 normal
playsound minecraft:entity.player.splash master @a ~ ~ ~ 1.4 0.7
# remember where the glass was, so the return trip has somewhere to land
execute unless entity @e[tag=sg_gate_return,distance=..6,limit=1] run summon minecraft:marker ~ ~ ~ {Tags:["sg_gate_return"]}
execute in saltglass:reflected_deep run tp @s -64 -45 0 facing -53 -45 0
effect give @s minecraft:water_breathing 6000 0 true
effect give @s minecraft:dolphins_grace 1200 0 true
playsound minecraft:ambient.underwater.enter master @s ~ ~ ~ 1.6 0.8
title @s actionbar [{"text":"The sea is upside down above you.","color":"#7FB4B0","italic":true}]
# the first dive is what raises the cathedral out of the dark
execute if score #cathedral sg_state matches 0 run scoreboard players set #cathedral sg_state 1
