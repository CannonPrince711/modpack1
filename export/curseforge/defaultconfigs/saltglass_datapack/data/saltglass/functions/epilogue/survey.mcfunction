# Optional Act III epilogue helper: marks the drowned lighthouse site with a
# labelled marker so a player can build the restoration without coordinates.
execute if score #epilogue sg_state matches 1.. run return fail
scoreboard players set #epilogue sg_state 1
summon minecraft:marker ~ ~ ~ {Tags:["sg_epilogue_site"],CustomName:'{"text":"Drowned Lighthouse site"}'}
tellraw @s [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"Marked. Whatever you build here is the first new thing this coast has seen in nine hundred years.","color":"#7FB4B0"}]
