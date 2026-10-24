## 2026-10-24 — Original P1 reconciled-tick sensor exporter (DEV)

The new pure P1-owner file `experiments/p1_selfbody_export.py` adds
`export_p1_sensed_tick(profile, before, reconciled_tick, sensor)`.
It **recomputes the existing** P1 `reconcile` result against its original
prior state/profile/source (zero movement tolerance) before exporting the
quantized `sensed_for_self` reading. It exports session, profile SHA256,
World tick, activity, World source pointer and optional WAIT interval pointer;
it never publishes evaluator-private true fatigue or physical capacity.

The returned `P1SelfBodyReadout` carries the mandatory
`P1_PRODUCER_LOCAL_NOT_WORLD_ATTESTED` scope. P1 cannot independently
authenticate the external S/R tick or inactivity from source strings; the
exporter **does not** prove a genuine physical WAIT/recovery event. A blocked
MOVE still cannot recover fatigue; attempted forged transition/profile/tick,
missing WAIT witness or stray Action is rejected in synthetic tests.

The corresponding product **consumer** is isolated in S Draft #634 and
fails closed if this original P1 exporter is not yet present in its checkout.
Neither side creates another P1 physics owner, Self policy, Action issuer,
native probe or reward. Python3.12 focused validation and later owner-approved
integration remain required before physical DEV adoption; R/V separate.

---

# P1-B — Source-correlated physical WAIT / fatigue Body interface (offline)

**Authority:** P1 #620, S #537, R #575, M #616, V #619.
**Revision:** 2026-10-16. P1 Body **WAIT replaces REST**. No REST choice ref, REST Activity or distinct REST action remains. **Status:** `P1_B_OFFLINE_CORRELATION_CONTRACT / S_R_PHYSICAL_ENFORCEMENT_PENDING / SCIENCE_NO_GO`.

## Contract

`experiments/fatigue_p1_boundary.py` is a pure evaluator-side *shape/correlation* gate, not an Action authorizer or original-source authenticator.

1. `SActivityRequest`: an existing S-proposed `MOVE/FIGHT` action with normal authorization by S; or no-action `WAIT` candidate. WAIT is a **Body state**, not a special Self-ordered REST command. It may follow a deliberate policy, a safety cancellation, or unprompted inactivity. Candidate WAIT without physical evidence is not enough to recover.
2. `preflight`: returns evaluator-private movement/combat capacity. Limit must be implemented by S **prospectively** per authentic World tick. It is not permission to issue an Action, and does not overwrite an actual excess distance. Exactly the already-issued S Action can span multiple ticks.
3. `SourceBoundTick`: matches genuine session / consecutive World tick / actual path (not nominal block nor count of Paper exhaustion events). MOVE and FIGHT require existing S Action/effect correlation and optional true terminal OUTCOME. **WAIT must carry an independent `wait_interval_ref`**, standing for the entire tick's no-movement/no-combat source attestation and no issued Action; missing ref or smuggled combat/travel/action fails closed. A source string alone is **not** attestation. Original bytes and lifecycle belong to S/R.
4. `reconcile`: only after a real verified WAIT tick advances P1 Fatigue with recovery; a blocked or 0-distance MOVE is still MOVE and cannot recover. Wrong state/profile/tick/action, missing WAIT witness, extra MOVE distance, forbidden mixed state and forged caps are rejected. No new REST signal is accepted.
5. `sensed_for_self`: quantized `FatigueObservation` only, never raw fatigue or evaluator capacity/true source. Fatigue OFF retains legacy behavior with no bonus.

## Time and M0.2 invariants

One authenticated **World tick** advances this Body state once. No missing ticks, no replayed tick, no conversion from Action count or process wall clock. P1 WAIT does not suspend Paper-native M0.2 BASAL, and never adds another hunger, exhaustion or energy debit. No special permission, reward or motivation arises merely from the physiological recovery.

## Handoff

- **S #537:** expose authentic Body WAIT classification and constrain real MOVE/FIGHT before execution via existing Action control; no new REST action, Skill or forced optimal waiting.
- **R #575:** source-verify full-tick WAIT inactivity, Action-free interval, session continuity, original native movement, S Action outcomes and RSEE cleanup. Source refs supplied to the pure function are not themselves proofs.
- **M #616:** M0.2 single live Paper metabolism ledger; BASAL including WAIT; physiological Fatigue separate from energy/cognitive cost.
- **V #619:** candidate fixed WAIT / sensor-only FSM / actual L1/L2 conditions, all observed WAIT time as outcomes, no outcome-driven equal-distance matching.

**Ceiling:** Offline deterministic interface only. No verified Paper/Java/Node real World movement cap or authenticated idle interval or scientific result.
