# Saltglass — runs on every datapack load (/reload included).
scoreboard objectives add sg_state dummy
tellraw @a [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"The sea is still falling.","color":"#7FB4B0","italic":true}]
