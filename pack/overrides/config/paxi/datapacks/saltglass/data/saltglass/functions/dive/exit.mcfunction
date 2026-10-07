execute if score @s sg_divecooldown matches 1.. run return fail
scoreboard players set @s sg_divecooldown 200
execute at @e[tag=sg_gate_return,limit=1,sort=nearest] run tp @s ~3 ~2 ~
particle minecraft:splash ~ ~ ~ 0.8 0.3 0.8 24 0.3 normal
playsound minecraft:entity.player.splash master @s ~ ~ ~ 1.2 1.1
effect clear @s minecraft:water_breathing
effect clear @s minecraft:dolphins_grace
title @s actionbar [{"text":"You surface into dry air.","color":"#E8E3D6","italic":true}]
