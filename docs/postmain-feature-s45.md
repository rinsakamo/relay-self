# S45 SEEK waypoint feature slice

Adds source-checked, bounded target-local yaw and forward-distance **proposal** from genuine Mineflayer position probes. Goal is caller-specified. ARRIVED vs NEEDS_ROUTE prevents blindly treating height difference as simple horizontal movement. No collision/terrain pathfinding, walking command, physical arrival or autonomous goal formation is qualified. Existing Action authority remains mandatory. Refs #382.
