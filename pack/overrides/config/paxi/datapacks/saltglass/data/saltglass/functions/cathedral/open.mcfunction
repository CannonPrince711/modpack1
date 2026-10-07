# Act II curtain — called by the quest that lights the third beacon.
execute if score #cathedral_open sg_state matches 1.. run return fail
scoreboard players set #cathedral_open sg_state 1
execute in saltglass:reflected_deep run fill -52 -45 -11 -50 -40 -7 minecraft:air replace minecraft:tinted_glass
execute in saltglass:reflected_deep run fill -52 -45 -2 -50 -40 2 minecraft:air replace minecraft:tinted_glass
execute in saltglass:reflected_deep run fill -52 -45 7 -50 -40 11 minecraft:air replace minecraft:tinted_glass
execute in saltglass:reflected_deep run fill 33 -44 -8 33 -42 8 minecraft:air replace minecraft:tinted_glass
playsound minecraft:block.beacon.activate master @a 0 -45 0 4.0 0.5
tellraw @a [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"Three bells, three beacons, and the third door of the cathedral is open. Somebody intended it to be.","color":"#7FB4B0"}]
