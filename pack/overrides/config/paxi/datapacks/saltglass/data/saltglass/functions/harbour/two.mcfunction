# Raises the Second harbour bell and its beacon tower where the player stands.
execute if score #harbour2 sg_state matches 1.. run return fail
scoreboard players set #harbour2 sg_state 1
summon minecraft:marker ~ ~ ~ {Tags:["sg_harbour_2"]}
place structure saltglass:beacon_tower ~-16 ~ ~-16
playsound minecraft:block.beacon.activate master @a ~ ~ ~ 3.0 0.8
particle minecraft:end_rod ~ ~8 ~ 0.6 8.0 0.6 60 0.0 normal
particle minecraft:enchant ~ ~ ~ 3.0 0.5 3.0 40 1.0 normal
tellraw @a [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"The Second bell is back on its bearings. Something down the coast answers it.","color":"#7FB4B0"}]
advancement grant @s only saltglass:harbour_bell
