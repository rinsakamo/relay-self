# S49 L1 → T2 owner Action boundary (2026-10-28)

**OFFLINE DEV CANDIDATE / NATIVE INTEGRATION NOT RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Base: actual L1 grid-refresh Minecraft DEV success `3b3bfa2721b2dbc95c41f8a81d6283e39428069a`.
Sibling body path: T1w `2672d0a1fe15584d16c2426540c528410bbb8c27`.
These diverged from the original S49 product ancestor. No merge/rebase of
the whole sibling history and no protected Draft/main edits.

## What this change actually connects

An explicit **existing** same-session T2 owner may opt into
`S49GoalExecutorDev.bind_t2_owner_dev(owner)` only *before* its first
Action, with `S49_L1_T2_BOUNDARY_DEV_ONLY=1`. It requires a pre-existing
ADMITTED consecutive Paper snapshot and an initialized fatigue state.
At every original `execute_goal_step` (including L1-generated waypoints
and subsequent grid refresh), the single original S49 supervisor first
issues the one Action. The boundary then calls the existing T2
`begin(action_id)` before external I/O; on genuine S16 OUTCOME or
source-honest S16 UNKNOWN with a verified original `clear_controls` ACK
and native readback it calls existing T2 `finish(consequence, terminal)`
exactly once. The UNKNOWN case has **no attested movement OUTCOME** and
no P1 credit from this bridge, but allows L1 wall replan once a fresh
same-session admitted Paper source arrives. Inconsistent terminal/ACK,
lost source, bad lineage or missing post-terminal Paper continuity
latches the owner and prevents additional Action.

This bridge does **not** create a T2 owner, read Paper snapshots,
post energy, advance P1, infer gait, authenticate movement packets,
establish R custody, or grant a new Action. T2's existing
`observe(frame)` and the original sole session native receiver are
still required for actual physical tick accounting. A new original
Paper snapshot newer than the prior native S16 terminal is necessary
before the next Action. Body exact E/F do not become SelfBody observations.

## Focused CI and next physical step

A new Python3.12-only CI checks positive and negative source
admission, native UNKNOWN, source continuity, original S49 opt-in
and L1 grid regressions. It does **not** claim an integrated Minecraft
run. Follow-on work must port the T1w original PaperSnapshot transport
and T2 owner into a *single* unified runtime while preserving L1
native voxel/Action protocol; do not replace whole `bridge.mjs` or
`python_protocol.py` from either sibling.

Then use one original session, one World, one S49 Action issuer,
one T2 ledger, first two original S49 movements, L1 detour,
midroute refresh, P1 original once-per-admitted-tick accounting and
M0 basal. Unknown gait remains UNKNOWN; never bill guessed WALK/DASH
or award unsupported WAIT. Native full-tick gait still requires
independent evidence and is not a prerequisite for minimum DEV routing.

Legacy default OFF. No main, #545, #634, #626, R/V, S18 or
historical evidence is changed; no full regression or SCIENCE.
