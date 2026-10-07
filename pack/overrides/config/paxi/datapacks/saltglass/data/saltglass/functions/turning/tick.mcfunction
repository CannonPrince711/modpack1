scoreboard players add #turning_t sg_state 1
execute if score #turning_t sg_state matches 1 run function saltglass:turning/wave1
execute if score #turning_t sg_state matches 120 run function saltglass:turning/wave2
execute if score #turning_t sg_state matches 260 run function saltglass:turning/wave3
execute if score #turning_t sg_state matches 400 run function saltglass:turning/wave4
