# G4.4 DEV — same issued S49 Action RUN→JOG→WALK

Branch `self/dev-g44-intra-action-gait-transition-20261029` from G4.3 HEAD `882e2441544e21eca781876189dbe15f40a46547`.

Explicit opt-in `--g44-intra-action-gait-dev` and `S49_G44_INTRA_ACTION_GAIT_DEV_ONLY=1` with inherited G4.3/G4.2/G4.1/G4 gates. The same issued S49 original Action, S15 sole native reader/writer and original T2/P1/M0 ledger are retained, and no new S49 Action is introduced.

Only a native observed RUN Action can schedule JOG at clearance <=2.50m, then WALK at <=1.55m; if within tolerance it requests original CLEAR. Each new phase is a strict `g44_gait_transition_dev` sub-effect with exact original `parent_action_id`, index 1/2, from/to states and deterministic ID. Original Node verifies active sprint Action, forward held, exact ordered parent and phase. Local native `sprint=false` then `sneak=true` actually change movement input while the original S49 Action remains open. Original S15 serially awaits each typed applied source-sequenced ACK; failure runs original CLEAR and marks Action UNKNOWN. The transition is not a second executor or self-authorized Action.

Original S16 after CLEAR and G4.3 quiet native samples still control Goal arrival; in-flight decision does not attest REACHED. Existing T2 per-tick gait candidate is from original Paper/Node observations, not claimed by command ACK; no R qualification. Each S49 pulse is still <=0.35s, so some original RUN Actions may have zero or one transition depending on live observations.

Focused Python 3.12, Ruff, Node typed-protocol negatives and disposable Paper 1.21.8 comparative DEV Worlds preserve original source and retained evidence. No QUAL/SCIENCE or main/Draft PR promotion.

## Actual Java 21 / Paper Minecraft 1.21.8 DEV results — 2026-10-29

Exact **physically tested code/workflow HEAD**: `bebdb76a2d6110b5ba53e38286168d48e2917b0f`. Prior exploratory first-phase-only RUN→JOG source success `76396bbc35e8ae674ff69e87b34e589bc6066dd4` is preserved (one typed source ACK). The later DEV tuning requires **both** distinct typed native transition ACKs in **one single issued original S49 Action**, not just GOAL_REACHED.

### Primary enforced two-phase run

- [GitHub Actions #40848178726 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40848178726), [original artifact #12885891780](https://github.com/rinsakamo/relay-self/actions/runs/40848178726/artifacts/12885891780). Python 3.12 scoped unit/negative tests, Ruff, Node 22 typed parsing + regression, Java 21/Paper pinned 1.21.8 builds and original World probes all passed.
- G4 baseline disposable World: native GOAL_REACHED, **5** original S49 Action OUTCOMEs, **50** original T2 P1/M0 ticks, final XZ goal error **0.5209453504992041m**.
- G4.4 active disposable World: native GOAL_REACHED, **6** original S49 Action OUTCOMEs, **132** original T2 P1/M0 ticks, final XZ goal error **0.4522615965804535m**. One original T2 owner, no new S49 issuer or per-sub-effect P1/M0 debit, six closed original native S16 and original postclear passive tail windows.
- **Within the SAME exact issued Action `goal-approach-demo-step-2`:** RUN→JOG from independently sourced in-flight probe **seq 67** to typed native **applied ACK seq 68** (`goal-approach-demo-step-2-g44-1-jog`), then JOG→WALK from native probe **seq 71** to **applied ACK seq 72** (`goal-approach-demo-step-2-g44-2-walk`). This is an actual Mineflayer control-mode mutation without another S49 Action. A separate Action `goal-approach-demo-step-3` also applied RUN→JOG (probe seq 111 → ACK seq 112). Three source-correlated applied gait-change sub-effects total.
- G4.3 late quiet reference after all 6 S16 terminal Actions: native positional delta **0/6 nonzero** over nominal 550–800ms. Actual Paper speed on *each* intervening tick and exact packet-to-Paper input acceptance remain **unqualified**; typed applied ACK attests the original Node-local control effect, not World tick continuous speed.

### Independently rerun two-phase source branch

- [GitHub Actions #40848136796 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40848136796) / [artifact #12886200974](https://github.com/rinsakamo/relay-self/actions/runs/40848136796/artifacts/12886200974). Code with identical tuned thresholds and original S49 behavior, prior to the stricter workflow assertion.
- Active G4.4 World: **6 original S49 OUTCOMEs / 133 original T2 ticks / 0.452261589m final error**. The very same `goal-approach-demo-step-2` has **RUN→JOG applied ACK seq 69**, then **JOG→WALK applied ACK seq 74**; step 3 again has RUN→JOG seq 114. Six late quiet native windows all exactly zero movement. Independent physical World start position and scheduling; no synchronized run-to-run physical clock is claimed.
- Baseline G4 World had **6 Actions / 58 T2 ticks / final error 0.460113892m**; numbers are contextual only, not a causal performance comparison (different random absolute spawn and the G4.4 side intentionally adds passive 800ms observation windows).

### Interpretation and remaining gates

- **Verified G4.4 DEV success**: Two consecutive, source-correlated physical control changes from original RUN to JOG then WALK *inside a single issued S49 Action*, with typed ACKs and original CLEAR→S16 terminal, alongside the single existing T2/P1/M0 owner.
- **Not yet verified:** Paper per-WorldTick complete transition-boundary mapping and sustained physical gait for all ticks; physical stopping/settling cause; performance superiority; safe environmental obstacle response during stage switching; R QUAL or V SCIENCE.
- G4.4 policy thresholds in the successful tuned test are original RUN→JOG with L1 clearance <=**2.50m**; JOG→WALK <=**2.15m**. These are DEV control-policy thresholds, not measured guaranteed braking-distance envelopes. Original Action pulse remains <=**0.35s**.
- Next G4.5: strict joined original Node control generation + Paper tick native gait candidate *across each sub-effect boundary* with explicit initial/steady/transition phase outcomes; retain fallback UNKNOWN for unsupported tick frames. Test with hazard injected during an in-place gait stage and assert original S15 fail-closed CLEAR, no extra S49 issuer.

**Final DEV status:** `DEV_ONLY / G44_REAL_WORLD_TWO_PHASE_ACK_TWICE_PASS / ORIGINAL_S49_SINGLE_OWNER_P1_M0_T2_PASS / PER_TICK_CONTINUOUS_GAIT_NOT_ATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
