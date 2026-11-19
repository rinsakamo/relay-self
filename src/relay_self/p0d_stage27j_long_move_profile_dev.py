"""Stage27j DEV fixed operator long-range MOVE profile.

This is a narrowly accepted experiment Preset, not a new inherited reflex,
learned/autonomous Skill, or a mechanism for expanding physical permissions.
Values are bound BEFORE the original L1 numbered choice.
"""
from __future__ import annotations

STAGE27J_PRESET_ID = "OperatorLongWalkSneakAt075"
STAGE27J_TARGET_DISTANCE_M = 5.0
STAGE27J_ARRIVAL_M = 0.15
STAGE27J_WALK_SNEAK_THRESHOLD_M = 0.75
STAGE27J_PULSE_S = 0.15
STAGE27J_MAX_ACTIONS = 12
STAGE27J_MAX_DURATION_MS = 45000
STAGE27J_MAX_DISTANCE_M = 6.0
STAGE27J_MAX_OBSERVATIONS = 1024

# Operational IO watchdog only. Not the Self's 45s cognitive time budget:
# cancellation/uncertain STOP holds WAL unresolved; it is NEVER budget success.
STAGE27J_ACTION_IO_WATCHDOG_S = 30.0
