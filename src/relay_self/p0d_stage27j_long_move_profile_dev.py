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

# Empirical one-pulse admission envelopes, not guarantees against external
# World forces. A larger real displacement must HOLD, never reissue.
STAGE27J_WALK_ACTION_RESERVE_M = 0.75
STAGE27J_SNEAK_ACTION_RESERVE_M = 0.25
# Reserving time alone does not bound slow or blocked IO. The issued child
# must also carry the original absolute deadline (and be cancellable).
STAGE27J_CHILD_TIME_RESERVE_MS = 5000
