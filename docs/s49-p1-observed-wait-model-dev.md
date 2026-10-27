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

## Real disposable Minecraft result — source-exact

- **Workflow:** [#40446269000 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40446269000)
- **Tested code HEAD:** `c63c3688c593fe2a0f978b10bf2c8a22c49974a8`
- Python 3.12 focused tests and Ruff passed; Node 22 tests and Java 21
  plugin `BUILD SUCCESS`; original S49 Java/Node cleanup and two native
  S16 OUTCOMEs passed.
- Original S49 Actions: `s49-native-move-18` and `s49-native-move-56`.
  Paper START delivery tick 258; END delivery tick 443. Newly captured
  conservative **static Paper ticks 263–438 inclusive: 176/176**,
  each re-screened from its native log line and predecessor.
  Maximum Paper XZ per-tick delta in accepted candidate: `0.0m`.
- Original Node all-control-OFF callbacks: 188 physicsTick samples.
  Original host owner 9240.290249ms unissued interval; Node 9360ms
  local input-OFF sample duration, differing by about -119.71ms.
  Clocks are NOT synchronized or converted between these sources.
- Original first DASH P1 finished tick 255 at model fatigue
  `0.6177122410202606`; intervening 7 ticks before tick 263 remain
  unclassified. A held-state assumption remains explicit.
- DEV copy-only P1 gait replay: 176 assumed WAIT ticks / 8.8 normalized
  World-seconds. `p1_dev_model_before=0.6177122410202606`,
  `p1_dev_model_after=0.2148677493585419`,
  `p1_dev_model_recovered=0.40284449166171865`.
  This matches the independent earlier aggregate shadow computation.
- Exact row-evidence SHA256:
  `69e1133518d07c603d51d3e3b83ef1dda38e8cc902c44ccbf7a4ca498b65d039`.
  This fingerprint detects changes to the reviewed raw row bytes; it
  does not constitute independent source authentication.
- Real original M0 end balance: `10.413667611509306`, no new
  per-World-tick M0 posting. `live_p1_owner_state_modified=false`,
  `r_qualified_wait_ticks=0`, `r_qualified_p1_recovery=0`,
  `actual_physical_recovery_attested=false`,
  `source_bound_tick_created=false`. No R qualification/SCI/FULL.

**Final:** `DEV_WORLD_OBSERVED` for the tick-local single-P1 *model*
replay; `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN` for
physical WAIT, state posting, independent custody and causal science.
The next engineering goal is a bounded, source-preserving DEV sidecar
handoff to SelfBody or next action preflight, without pretending this
model recovery is an R-qualified physical observation.
