# S49 original Paper static ticks → DEV-only P1 body-WAIT model replay

2026-10-27 · DEV_WORLD_OBSERVED is permitted only with real fresh disposable
World receipt. **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

This implements the narrow DEV step requested in #537/#627: reuse the
source-reviewed original S49 2-action outcome, START/END Paper causal delivery,
Node all-controls-OFF callback samples, and exact Paper `getFullTime` movement
rows. Re-parse every Paper trail row and its predecessor for the conservative
static subwindow; reject gaps/repeats/foreign actor/action/world, >0.002 m XZ
movement, motor writes, modifier, action-edge markers, unauthorized WAIT/P1/M0
claims, or changed original reviewer guardrails. Retain one SHA256 over the
observed candidate source rows and a bounded report.

For each accepted **DEV body-static tick**, run the *existing single P1 gait*
`advance_gait_dev(..., GaitTickDev(...,"WAIT"))` on a local `FatigueState`
copy, maintaining existing 0.12/normalized-second WAIT recovery. Because the
fatigue value was last replayed at the first DASH end, and there are still
unclassified intervening ticks, this replay assumes it remains constant across
the gap. The result is **not proof of what actual fatigue did in the World**.
It is a DEV model-state progression conditioned on measured stillness and sampled
control-OFF—not a new fatigue dimension or a physically qualified WAIT record.

The report distinguishes `dev_wait_model_ticks_replayed` and
`p1_dev_model_recovered` from `r_qualified_wait_ticks=0`,
`r_qualified_p1_recovery=0`, `live_p1_owner_state_modified=false`,
`actual_physical_recovery_attested=false`, and `m0_posted=false`.
It creates no `SourceBoundTick`, changes no original S49 issuance and posts no
new World-tick M0 charge. Existing M0 Action-step basal logic continues to apply.

New opt-in `S49_P1_OBSERVED_WAIT_MODEL_DEV_ONLY=1` and
`--p1-observed-wait-model-dev` require the preexisting fenced shadow, causal
owner fence, original P1 Motor, original M0 outcome reviewer, and same-run source
checks. All non-DEV defaults remain OFF. Kept in fresh isolated branch
`self/dev-p1-observed-wait-frames-20261027`; no main/#545/#634 merge, FULL
or independent R/SCI claims.

The earlier real reference is run #40440197581, with 175 static Paper ticks,
but the new code must pass its own fresh World run before claiming
`DEV_WORLD_OBSERVED` for this step.
