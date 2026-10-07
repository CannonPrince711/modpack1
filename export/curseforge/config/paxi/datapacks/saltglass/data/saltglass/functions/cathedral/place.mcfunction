# Places the cathedral once, the tick after the first diver is inside the deep
# (by then the destination chunks are loaded).
scoreboard players set #cathedral sg_state 2
place structure saltglass:drowned_cathedral -55 -49 -30
playsound minecraft:block.conduit.activate master @a 0 -45 0 3.0 0.6
tellraw @a [{"text":"[Saltglass] ","color":"#E0A32E"},{"text":"Far east of the arrival shelf, something with spires is standing in the water, and its windows are lit.","color":"#7FB4B0"}]
