# Runs every tick. Two cheap selector checks, nothing else.
execute as @a[scores={sg_divecooldown=1..}] run scoreboard players remove @s sg_divecooldown 1
execute if score #cathedral sg_state matches 1 run function saltglass:cathedral/place
execute if score #turning_wave sg_state matches 0 run function saltglass:turning/idle
execute if score #turning_wave sg_state matches 1..3 run function saltglass:turning/tick
execute as @a[gamemode=!spectator] at @s if dimension minecraft:overworld if predicate saltglass:night if block ~ ~-1 ~ minecraft:tinted_glass if predicate saltglass:crouching run function saltglass:dive/enter
execute as @a[gamemode=!spectator] at @s if dimension saltglass:reflected_deep if block ~ ~-1 ~ minecraft:tinted_glass if predicate saltglass:crouching run function saltglass:dive/exit
