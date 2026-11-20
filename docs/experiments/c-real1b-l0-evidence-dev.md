# C-Real1b L0 evidence investigation (DEV)

The prior isolated World `7c17d861-35f4-4509-8b72-11682ac83dbb` has a
canonical terminal `NATIVE_PLACE_MOVE_SETTLED` WAL row for `stage27c-A-33`
and native STOP/settling observations. It does not contain the actual L0
terminal step. The runner raised its C review gate before freezing that step.
The gate also rejected fewer than two Actions, so its error text alone does
not identify the L0 terminal status.

The original preset sets 4 actions, 15 seconds, 256 observations and 2 m.
The native source has 30 STOP probes (seq 54 through 89); the settled WAL
reports approximately 0.642 m. Assuming these are the complete original
sources used by the loop, the action count, displacement and the 60-probe
reservation for a subsequent action do not exhaust those respective limits.
The settled WAL status also does not select the explicit no-progress branch.
No subsequent native preflight probe is visible. Time exhaustion, target or
world-condition assessment cannot be determined from the surviving L0 source;
no unique stop reason is claimed. The pre-action checkpoint is not a
post-action checkpoint.

The C Stage27h opt-in runner now fsyncs an exclusive terminal diagnostic before
post-L0 review, plus an exit diagnostic in its exception/finally path. It
records the last returned L0 step, remaining budgets, last assessed and settled
native sequences, pending STOP reservation, validated and raw WAL hashes, and
any propagated error. A raw WAL hash does not certify a terminal physical
state. A process or machine failure before the snapshot remains outside this
mechanism; unresolved physical state must still HOLD.

This change does not implement non-arrival L1 review, independent Self
acceptance, failed/interrupted C1, or a post-action checkpoint. It must not be
used as a reason to perform another live World trial until those paths and
their safety gates are implemented and verified.

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
