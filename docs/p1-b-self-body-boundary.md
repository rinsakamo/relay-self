# P1-B — S/R owner handoff: Fatigue Body admission and sensor-only view

**Status:** `P1_B_OFFLINE_BOUNDARY_READY / ACTUAL_S50_S49_ACTION_ENFORCEMENT_NOT_INSTALLED / REAL_REST_NOT_ATTESTED / SCIENCE_NO_GO`.
**Authority:** #620, P1 Draft #626. S #537 owns Action, S45/S50 movement, skill and policy; R #575 owns original World source; M #616/#617 owns metabolism/M0.2 Paper; V #619 independently preregisters science. No owner replacement.

## Contract — not production integration

`experiments/fatigue_p1_boundary.py` is deliberately a standalone **evaluator-only** adapter spec that imports only `experiments.fatigue_p1`, not S/R runtime or Java/Paper. Its source-shape validation is not cryptographic or native attestation. Constructing a `SourceBoundTick` with a string ref cannot prove Minecraft, S Action issuance, or REST execution. S/R must validate genuine immutable source bytes, issuer evidence, native tick, and World outcome **before** constructing the descriptor. No newly minted action grant, controller policy, persistent memory owner or native executor is added.

1. `SActivityRequest` is the externally chosen action/intent and its S-proposed `action_ref`. REST requires an **explicit Self choice ref**; WAIT has neither Action nor REST choice. P1 does not invent a REST Skill or choose between WAIT and REST.
2. `preflight(profile, state, request)` validates exact session, one World-tick envelope, the M-independent Fatigue state/profile, and nominal one-block steering. An ordinary requested MOVE may be reduced to `allowed_blocks`, so **S must use that bound in its already authorized movement mechanism**, otherwise the Body limit is not enforced. High fatigue may make FIGHT mechanically unavailable. Preflight does not authorize/issue/complete any action.
3. `SourceBoundTick` is a typed **post-observation correlation only**: World session/tick, original World source ref, actual measured traveled blocks, optional blocked outcome, S Action ref, per-tick `action_effect_ref`, optional genuine terminal Action `action_outcome_ref`; REST instead requires the exact Self rest selection ref **and separately validated physical idle interval ref**, and must show zero issued Action/movement/combat. WAIT must have neither. A source ID string can be forged; validating the original bytes/lifecycle belongs strictly to S/R.
4. `reconcile` recomputes preflight to reject caller-modified caps, demands the exact next World tick, correlates activity and receipts, enforces actual movement within cap (default **zero** tolerance; an explicit ≤0.05 block allowance is possible for measurement discrepancies, *never* an implicit exemption), and calls the unchanged P1-A `advance`. Overrun/unknown/duplicate/missing evidence fails closed and remains a source-side failure to diagnose; P1 never clips original displacement to pretend compliance.
5. `sensed_for_self` outputs only `{world_tick, reading}` from an independently configured sensor. S must never route private `FatigueState`, `BodyCapability`, `BodyPreflight`, `SourceBoundTick` or `P1ReconciledTick` into L0/L1/L2. A blind sensor (`gain=0`) leaves true state hidden.

## Important time distinction: one S50 Action is not one World tick

Existing S45 `SeekWaypoint.max_step_m=1.0` is a **proposal cap per steering step**. Existing S50 issues an Action using `ActionSupervisor`, `execute_seek_step` and correlated native observations. It can span multiple Minecraft World ticks; `action_id` is not a tick counter. P1-A fatigue math is *per consecutive World tick*. For each actually observed tick while a MOVE is in flight, S/R must admit a tick-local original path displacement and apply the prospective cap on the native movement actuator. The same in-flight Action ref may recur over multiple ticks with fresh tick-specific `action_effect_ref`; `action_outcome_ref` occurs only at real terminal closure. If the current native bridge cannot provide tick-local actions/path controls and authenticated World ticks, P1 integration must **BLOCK**, not substitute one Action=one tick or spread distance evenly after the fact.

Nominal S50 one-block `step_distance_m`, actual observed displacement, actual path distance, and action outcome status are distinct. Existing M0.2 Paper derives **actual land path** from `PlayerMoveEvent`; P1 should consume S/R-attested equivalent traveled blocks without recomputing Minecraft exhaustion. Under obstacles, `blocked=True` with zero movement charges zero distance-related fatigue, while partial motion is billed for its observed blocks. This P1 model does not yet include failed effort, collision energy, flight, teleport, combat effort without an original event, or fatigue-related cognitive cost.

## Energy & REST

- M0.2 controls live Minecraft food, exhaustion, saturation and HP. P1 never updates any of them, and must not layer simulated M0.1 energy over Paper hunger. During REST/WAIT, M0.2 **BASAL** continues once per *actual* World tick, including uninterrupted idle periods.
- A valid REST tick requires **both** a Self decision selecting REST and external evidence that the actor did not move/act throughout the tick, within a live World clock. An unissued WAIT is not a proof of REST and never recovers fatigue. Neither may be inferred from 20ms wall time, Action count, missing probes or a fabricated S16 OUTCOME.
- The current S Action/REST issuer has no qualified implemented REST interval. P1-B provides the receiving boundary only. Scientific claims remain NO_GO.

## Owner acceptance before P1-B can become physical

- **S:** existing owner opts in to the P1 preflight limit *before* issued S50 movement and fails closed on non-enforcement. It maps an explicit Self-selected REST to an admissible idle interval without misrepresenting WAIT/issued Action, preserves Action/Memory/L0-L2 ownership, and keeps designed baseline policy distinct from learning.
- **R:** supplies a source-authenticated consecutive World tick with actual path delta (not Paper exhaustion event count), source and agent session identity, tick-level Action correlation, and original immutable REST interval; validates eligible solo profile and cleanup separately. Unexpected gaps/teleports/entities block solo scientific admission.
- **M:** existing Paper server stays the sole live energy/saturation/hunger authority with basal charged even in REST; separate non-physical P1 Fatigue ledger is explicitly opt-in and separately hashed.
- **V:** choose preregistered cheap fixed REST vs L1/L2 + Fatigue OFF controls before independent SCIENCE trials. Engineering tests do not prove behavioral utility, fatigue physiology or a novel cognition mechanism.

## Offline verification

`PYTHONPATH=. python -m pytest -q tests/test_fatigue_p1.py tests/test_fatigue_p1_boundary.py` checks both phases, offline. No remote World, native plugin, S/S50 source change or science run is triggered.