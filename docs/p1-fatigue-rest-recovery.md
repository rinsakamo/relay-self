# P1-A — Physical Fatigue recovers during Body WAIT (offline)

**Authority:** #620 solo-first P1; M #616, S #537, R #575, V #619.
**Revision:** 2026-10-16 user decision: P1 Fatigue is **physical/body fatigue**. The sole ordinary recovery mechanism is actual physical **WAIT**. **REST is not an Activity, independent Skill, Action, extra intent, or condition for recovery.** Prior REST-only semantics are superseded. **Status:** `P1_A_OFFLINE_BODY_PHYSICS / WORLD_ENFORCEMENT_NOT_INSTALLED / SCIENCE_NO_GO`.

## Body states and sources

The activity alphabet is `WAIT | MOVE | FIGHT`. Every `FatigueFrame` represents **one consecutive authentic Minecraft World tick**, not an action count, decision count, or wall-time. S/R must independently verify the full-tick physical state and source before constructing a frame. A missing action command alone does **not** prove a WAIT tick.

- **WAIT**: verified lack of motor/combat action over the whole tick; recovery `min(fatigue, wait_recovery_per_world_tick.value)` (candidate standard **0.10/tick**) irrespective of why Self is waiting. The World/Body does not select WAIT or implement a preferred wait policy.
- **MOVE**: accumulate actual source-measured **path blocks** × `move_per_block` (candidate 0.04/block); 0 distance on a blocked MOVE is **still MOVE**, with no distance accumulation and **no WAIT recovery**. Partial travel is billed only for actual distance. Neither requested 1 block nor native Paper WALK event count is a distance measurement.
- **FIGHT**: accumulate verified combat events × `fight_per_event` (candidate 0.2/event; 0–1 per single tick). A missed action is not silently reclassified as WAIT.
- **Fatigue**: opt-in dimensionless virtual Body state `[0, capacity]`; OFF default `enabled=False` never adds/reduces Fatigue and leaves mechanical efficiency 1.0. Move/combat impairment is the separate `capability` result; S must actually enforce it before real World execution. No optimal wait heuristic, cognitive-cost levy or learning agent in Body.
- Every `Rate` uses `standard × multiplier + additional` with finite nonnegative inputs. New profile field `wait_recovery_per_world_tick` supersedes `rest_per_world_tick` and changes the immutable profile SHA; old profile/receipt identities cannot be silently reused.
- `FatigueSensor` is a separately quantized optionally blinded projection. Only that observation may be passed to Self; evaluator's true fatigue stays private.

## Metabolism and distinction from REST

**WAIT still incurs M0/M0.2 basal charge every actual World tick**. In live Paper, M0.2 hunger/exhaustion/saturation and HP are authoritative; P1 never creates another Minecraft energy ledger or charges REST differently. P1 Fatigue is **not** Minecraft hunger/exhaustion, L1/L2 cognitive fatigue or compute-cost accounting. Waiting physically recovers only this Body variable. A blocked MOVE, stalled executor or absent World observation cannot claim recovery.

## Owner handoff and validity ceiling

- **S #537:** use actual WAIT state, not new REST intent/Action. Preserve S Action authorization for issued MOVE/FIGHT and existing L0/L1/L2 policies; apply prospective Body cap in existing executor. Choosing WAIT is Self policy; recovery while WAIT is Body physics.
- **R #575:** attest native consecutive tick, source identities, full-tick idle witnesses, actual MOVE path, action/tick correlations, profile hash and cleanup; separately prove solo World via P1-C full-scope census.
- **M #616:** source BASAL continues during WAIT, same as any tick; no double P1/M billing or M0.1 simulated debit atop Paper.
- **V #619:** compare cheap fixed WAIT, equal-sensor FSM, L1 and L2 against Fatigue OFF within matched authentic World and actual native WAIT ticks; retain null, host abort, invalid and contaminated trials. Current P1 tests do not prove scientific superiority.

**Offline check:** `python -m pytest -q tests/test_fatigue_p1.py`. A deterministic WAIT frame is only a unit-test input; no original World source, physical Body limit, real solo profile, genuine adaptation or SCIENCE qualification is claimed.
