# S49 → S50 → P1: World-first DEV boundary (2026-10-25)

Status: **DEV_ONLY / OFFLINE MODEL REPLAY IMPLEMENTED / WORLD NOT RUN /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

This deliberately reduces the development target. The goal is to run an
existing S49 physical MOVE, observe a settled idle interval with an existing
Paper observer in the **same disposable World/session**, and demonstrate
P1 WAIT recovery by the unchanged `experiments.fatigue_p1.advance`.

## What is implemented here

`adapters/mineflayer/s49_s50_p1_wait_replay_dev.py` reuses the existing
`review_s49_preaction_paper_dev` for typed S16 MOVE_BACKWARD closure,
Paper-reported BACK true→false, idle input and no observed Self movement,
same Paper run/subject/World, eight consecutive callbacks and COMPLETE.
It excludes the ambiguous BACK-off boundary tick, and only replays the eight
subsequent World ticks into P1 `FatigueFrame(WAIT)`.

The caller must provide an **existing** P1 enabled profile and FatigueState
at the preceding World tick. The replay will not create or infer a fatigue
state from a missing source, skip a tick, treat blocked MOVE as WAIT,
alter the M0 basal calculation, issue any Action, or commit an evaluator state.

For a synthetic log its result is **OFFLINE_WAIT_MODEL_REPLAY**,
`world_run_verified=false`. The independent R fields stay unchanged:
`source_bound_tick=null`, `wait_interval_ref=null`,
`wait_ticks_admitted=0`, `p1_fatigue_recovered=0`.
A separate `dev_fatigue_recovered` is the result of model replay, **not**
an externally qualified physical recovery or a World observation.

Focused local test:

```bash
PYTHONPATH=src:tests:. python3.12 -m pytest -q \
  tests/test_s49_s50_p1_wait_replay_dev.py
```

## Real World next: minimum owner integration, no R-grade attestation

**Important architectural gap:** The original S49 `qualify()` currently
downloads/boots a Mojang vanilla server. Vanilla cannot load the separately
built Paper 1.21.8 observer. The repository already has the S-owned disposable
Paper DEV launch path `m02_paper_dev.s51_paper_physics_dev`, but it runs an
S50/S51 governed flow, not the original S49 `execute()`. Therefore two
existing independent runs CANNOT be spliced into a successful SAME-WORLD
S49→P1 DEV demonstration.

The smallest practical next implementation is an **opt-in S-owned DEV
harness** which:
1. Reuses the existing Paper DEV server lifecycle and SHA-pinned observer JAR,
   in a fresh private World, port and run output root. No main/Golden reuse.
2. Invokes the existing original S49 single Action issuer/Executor in that
   Paper World; does not invent a second motor controller.
3. Enables the observer before MOVE (when using the preaction stream),
   captures original S16 closure/clear and the subsequent Paper server
   input-idle/movement callbacks in that SAME run.
4. Acquires/maintains legitimate P1 state up to the last pre-WAIT tick
   (including MOVE state evolution); does not fabricate a starting fatigue
   level. If no such state exists, record WAIT observed but fatigue result
   UNDETERMINED instead of an invented recovery.
5. Runs the pure replay/advance, records the observed World and P1 before/
   after/recovered in DEV-only fields, preserves both raw original logs,
   closes/reaps Java and Node and keeps failed attempts. If input resumes,
   the player moves, an Action remains open, or the source is missing,
   reject the interval. Boundary tick unknown? Drop it.
6. Reports `DEV_WORLD_OBSERVED` only if the actual **single session**
   World receipts and P1 transition were collected; this report alone never
   makes `QUALIFICATION_GO` or `SCIENCE_GO`.

**Not a DEV prerequisite:** external custody, independent OS signing,
W4 epoch attestation, raw TCP-witness certification, or proving ACK caused
each Paper packet. Retain these as distinct R/V qualification work.

## Present limitation

This branch is not a Paper plugin installation, World launcher change or a
real Minecraft run. It supplies the P1 calculation seam plus regressions, and
records the concrete server mismatch to fix next. Do not label a synthetic
fixture WORLD PASS; do not reuse historic paper/v7 evidence as this run.

## 2026-10-25: same-run Paper opt-in implementation

Two modules now stage the minimal **single-run** owner path:
`s49_paper_postwait_dev.py` joins S49 original S16 clear and original
Paper 8-tick post-action input/position observer; `s49_paper_world_first_dev.py`
is an explicit S-owned disposable wrapper for the unchanged S49 `qualify()`.
Only its Paper server asset/config are substituted, and an inherited original
S49 Executor sends the read-only Paper console observation **after the second
original S49 MOVE** has closed. The original S49 cleanup still owns Java,
Node, collector, and World. No separate issuer, direct native control, W4
external custody, or new SourceBoundTick is installed.

The pre-action BACK-on/off observer is **not** a DEV prerequisite: this first
run uses the existing post-action observer and omits the uncertain boundary
tick. Model fatigue begins at a clearly labeled synthetic configured initial
value (0.5), not inferred biological exertion. The Paper and original S49
receipts must be from the **same** newly created session/run.

Operator command (NOT EXECUTED IN THIS SESSION):

```bash
PYTHONPATH=src:tests:. python3.12 -m adapters.mineflayer.s49_paper_world_first_dev \
  --output-dir /ABSOLUTE/FRESH/OWNED/s49-paper-p1-001 \
  --paper-jar /ABSOLUTE/VERIFIED/paper-1.21.8.jar \
  --paper-sha256 FULL_64_HEX_SHA256 \
  --observer-jar /ABSOLUTE/VERIFIED/relay-s49-wait-observer-dev-0.1.0-dev.jar \
  --observer-sha256 FULL_64_HEX_SHA256 \
  --confirm S49-P1-DEV-DISPOSABLE-PAPER-WORLD
```

JAR SHA identities are mandatory. The observer is normally disabled and is
enabled only in the new disposable World. An actual successful run would be
labeled `DEV_WORLD_OBSERVED_WITH_SEEDED_P1_MODEL`; R-qualified
`p1_fatigue_recovered` remains 0 and V science remains unrun. Failure
on a new Paper server is a DEV debugging input, not a recovered Golden run.

## 2026-10-25: native last MOVE distance → P1 fatigue → Paper WAIT

DEV acceptance no longer uses an arbitrary `initial=0.5` on the World-first
runner. `fatigue_mode="MOVE_DISTANCE"` now starts at `initial=0.0` and
checks the last original S49 `MOVE_BACKWARD` Action's decoded immutable
before/after native poses, issued/control-clear ACK and reported movement
distance using existing `verify_native_action_evidence`. It computes one
explicit P1 `advance(... FatigueFrame(activity="MOVE",
observed_blocks=actual_distance))` **model step** at zero starting fatigue.
Only then does the existing post-clear Paper callback interval (excluding the
boundary callback tick) feed eight real Paper tick indices to
`advance(... FatigueFrame(WAIT))`.

**Critical time precision:** The S49 Action evidence contains geometric
*per-Action* distance, not separately located per-World-tick MOVE distance.
Therefore P1's MOVE model_step=1 is a **local virtual evaluation index**
and is never advertised as the Action's actual Minecraft World tick. The
model fatigue after that MOVE is explicitly rebased to the first verified
Paper idle callback boundary, with no claim that unobserved intervening
World ticks were WAIT or MOVE. The earlier S49 MOVE is not added because
it is separated by an unobserved interval which might have permitted rest.
This is a verified Action-displacement-driven **DEV model replay**, not a
fully source-timed long-lived Body state or a continuous World-tick ledger.

The expected retained fields include `dev_move.movement_m`,
`dev_move.fatigue_accumulated`, `dev_fatigue_before`,
`dev_fatigue_recovered`, `dev_fatigue_after`, and
`dev_model_phase_bridge=ACTION_AGGREGATE_MODEL_STEP_REBASED_TO_PAPER_BEGIN_WITHOUT_GAP_INFERENCE`.
The run is successful only for positive actual MOVE fatigue and positive
subsequent Paper WAIT recovery. The old `SEED` mode remains available
for backward-compatibility offline fixtures, but is **not** the World-first
run mode. R-qualified `source_bound_tick` remains null, and R-qualified
`p1_fatigue_recovered` remains zero; no S10 learning or production
FatigueState mutation occurs. M0 BASAL remains independent/unchanged.

## 2026-10-25: P1 DEV → SelfBody cognitive interface (read-only)

`adapters/mineflayer/s49_p1_self_body_dev.py` reuses the existing
`review_postaction_wait_dev()` source check rather than accepting arbitrary
reported fatigue numbers. After the last actual S49 MOVE + Paper's 8 WAIT
ticks, it produces **two immutable `SelfBodyView` epochs** representing
the state immediately after the MOVE model step and after the WAIT model
replay, then emits a bounded `self_body_dev` next-cognition readback in
`world_first_dev_report.json`.

- The existing P1 `observe()` sensor is quantized (0.01 units) before
  exposing integer percent levels through `BodyHypothesis` /
  `SelfBodyView.hypothetical("p1-dev-distance-wait", ...)`. This is a
  modeled body image, *not* a physical fatigue measurement or full-tick
  R-authenticated sensory readout.
- No corresponding **native Present** arrives after the Paper 8-tick
  window. Consequently `SelfBodyView.observation=None` and
  `sensed("p1_fatigue_sensor")` / `observed("p1_fatigue")` return
  UNKNOWN; promoting the Paper-only data to `BodyInteroception` would
  falsely claim native correlation. Missing original native data is not
  synthesized, and no second Mineflayer command reader is introduced.
- The readback includes before/after P1 model sensor levels, capability
  estimates, session, Action, Paper World/run SHA references, and explicit
  `actual_next_l0_decision_consumed=false`. Future Cognition can access
  the two model epochs, but **this run does not alter L0's real choice**,
  learn anything in S10, mutate a persistent SelfBody owner, or grant
  permissions to execute an Action.

This is the minimal DEV interface needed before wiring post-WAIT native
Present to P1's actual `BodyInteroception` and feeding it into a *future*
real cognition epoch. No qualification/science claim is implied.

## Post-Paper native Cognition epoch with shared SelfWorld/SelfBody

A further DEV-only extension requests exactly one correlated native probe
**after** the Paper observer reports all eight WAIT samples. The request
is performed by the original MineflayerProcessSession while the S49
`on_action_request` callback has suspended the outer host reader.
There is no parallel JSONL receiver, second Mineflayer process, native
Action, or change to the original S49 qualification routine.

The existing `compose_s49_p1_postwait_native_dev` builds an immutable
SelfBodyView with genuine native health/food/position from this later probe
and the **P1 hypothesized** fatigue copied from the Paper replay. The
`compose_postwait_native_self_world_dev` companion builds SelfWorldView
from that *same typed native probe* and checks the exact session, request,
sequence, provenance, epoch, and that `world.self_body is body`.
The disposable World report preserves `next_cognition_native_dev` and
`next_self_world_dev` separately, and verifies their source agreement.

The newly requested post-WAIT native probe is **later than** the last
S49 Action's native after-probe, but no native protocol-to-Paper callback
clock alignment is available. Thus the exact Paper tick corresponding to
the probe remains unknown. The post-WAIT probe is genuinely observed, while
P1 fatigue remains a fallible SelfBody **hypothesis**, not a P1 sensor
attested by S/R and not a World Observation. The historical real
`NormalWorldL0` is unchanged and `next_l0_consumed=false`; this is
a read-only next-Cognition input, NOT evidence that L0 used the hypothesis
to select a new Action. No S10 or learning owner is mutated.

## 2026-10-25: L0/S42 shadow comparison on one post-WAIT native probe

The original S49 owner already samples one correlated native probe after the
Paper WAIT callback series (no second receiver or issuer). A separate
`s49_p1_l0_shadow_dev.preview_postwait_l0_dev()` now asks the **unchanged
S42 World-conditioned chooser** what its fixed frozen rev1/value4 policy would
select on that **same typed post-WAIT probe**. Separately it reads the two
P1/SelfBody model capability values (after MOVE vs after WAIT).

This is a deliberately **read-only comparison**. It does **NOT** call
`ReactiveL0.decide()`, fabricate its required fresh entities-event/probe pair,
use the P1 hypothesis to change S42's actual score, mint an Action grant,
or execute another MOVE. Outputs explicitly record
`original_l0_entities_event_consumed=false`,
`actual_reactive_l0_decide_called=false`,
`fresh_action_grant_issued=false`,
`s42_has_p1_input=false`, and `p1_changed_original_s42_selection=false`.
It compares native geometry (actual Paper/Mineflayer) with a hypothetical P1
body image and preserves the difference between actual native food/health/
position and estimated fatigue/capability. Original L0 remains unchanged.

The next engineering step, **after** this shadow check, is an opt-in fatigue-
aware L0 candidate evaluator that can operate on an actual fresh native
entities event followed by an independent correlated probe. It must remain
separate from the existing S49 native Action issuer and must not imply that
P1 is externally attested or that old S42 choices were modified.

## 2026-10-25: post-WAIT P1-aware candidate gait comparison (DEV)

The optional `s49_p1_l0_capability_dev` reuses the **same real post-WAIT
native probe**, frozen S42 choice, and validated S49+Paper+P1 SelfBody
model. It compares two *possible* one-tick movement capability envelopes:

- After the last original S49 MOVE: P1's virtual fatigue model predicts
  lower maximum movement than `FatigueProfile.nominal_move_limit_blocks`
  (existing default 1 block / World tick), so a nominal-gait MOVE
  would need **scaling** in that model.
- After eight Paper WAIT callbacks: the model recovers toward the same
  nominal capacity. The original frozen S42 choice is unchanged and never
  receives a P1 sensor input; a WAIT choice remains WAIT in both models.

**Temporal counterfactual:** The actual live native geometry belongs to
the **post-WAIT** snapshot alone. Applying the *earlier* after-MOVE model
capability to that later geometry is explicitly hypothetical, not an actual
native observation or an earlier L0 decision. The original S49 measured MOVE
distance aggregates an Action spanning unknown native ticks and is **not**
passed off as a measured one-tick demand. The one-tick nominal demand comes
from P1's preexisting profile, not a new physical measurement.

This candidate evaluator returns the read-only tags
`MOVE_AWAY_SCALE_TO_CAPACITY_MODEL_ONLY`,
`MOVE_AWAY_NOMINAL_GAIT_MODEL_ONLY`, or `S42_WAIT_UNCHANGED`. It
does **not** modify `ReactiveL0.decide`, execute a MOVE, create a second
receiver/issuer, update S10/M0/P1 production, or qualify Paper WAIT.
This prepares an eventual opt-in actual L0 integration after independent
source and actuator constraints are separately met.

## 2026-10-25: one-World P1 fatigue-rate knockdown (DEV)

`s49_p1_l0_sensitivity_dev.compare_p1_knockdown_dev()` reuses the exact
*same* original S49 Action receipts, Paper eight post-clear WAIT callbacks,
and ONE already received post-WAIT native probe for two separate independent
P1 model replays. It first uses the existing original `FatigueProfile`
defaults, then a deliberately uncalibrated high-fatigue DEV rate
`move_per_block=Rate(6.0)` with identical WAIT recovery. Both start with
`initial=0.0`; no artificial fatigue is injected. Model ownership and
physics implementation are unchanged.

The high-rate condition is a **sensitivity/knockdown scenario**, not a
biological measurement, not a production P1 setting, and not World evidence
of greater exertion. Baseline ~0.627-block final MOVE accrues ~0.025 model
fatigue; eight observed WAIT callbacks return it to zero. The same MOVE at
stress-rate saturates the model capacity 1.0, and eight WAIT model steps
recover 0.8, leaving a modeled ~0.2. On the *same* native geometry, the
unchanged S42 `MOVE_AWAY` selection remains the same; the P1-aware,
read-only one-tick gait assessment differs between `NOMINAL_GAIT` and
`SCALE_TO_CAPACITY`. S42 is never given this model as a new physical input.

No new server, native read/receiver, Action issuer, L0.decide(), physical
MOVE, M0/P1 production mutation, or S10 learning is performed by the
knockdown itself. Never infer actual per-tick MOVE displacement, a causal
effect of physical fatigue on L0 behavior, or a qualified WAIT from this
model-only intervention. The World runner records `next_l0_sensitivity_dev`
beside the original native/SelfWorld/SelfBody/capability reports.
