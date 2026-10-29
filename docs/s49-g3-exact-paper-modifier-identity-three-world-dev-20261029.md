# RelaySelf G3.2 — exact Paper movement-speed modifier identity and G3 original-S49-owned P1/M0

**2026-10-29 JST**. **DEV_ONLY / G3_EXACT_PAPER_MODIFIER_IDENTITY_THREE_WORLD_OBSERVED / ORIGINAL_S49_ACTION_SCOPED_P1_M0 / FULL_PACKET_TICK_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Original native evidence

- Branch `self/dev-l1-t2-action-boundary-20261028`. **Exact three-World tested source HEAD** `c8aed7ceb063c8b1fc573a345c091c332cc3b328`.
- [Three independent disposable Paper 1.21.8 DEV Worlds — workflow SUCCESS #40809921310](https://github.com/rinsakamo/relay-self/actions/runs/40809921310). [Artifact #12869808111](https://github.com/rinsakamo/relay-self/actions/runs/40809921310/artifacts/12869808111), downloaded ZIP SHA256 `8f18297cdaf48914f6cebfa91d82647593e579800840e17b9bde77fea78e88f8`, **15 entries**; native Paper server logs, source-derived G1/T2 JSON, goal reports and producer stdout preserved. Complete Node stdout or disposable World images are **not** claimed.
- [Exact-HEAD focused CI SUCCESS #40809922287](https://github.com/rinsakamo/relay-self/actions/runs/40809922287): **86 Python 3.12 tests PASS, 28 Node tests PASS**, Ruff/Python/Node syntax PASS, no FULL.
- [Prior 1-World native SUCCESS #40809593148](https://github.com/rinsakamo/relay-self/actions/runs/40809593148) tested earlier HEAD `ffed38430a82811711542c4d992eb75b7157e2f7`. There the exact two modifiers occurred together in one Paper snapshot but there was no adjacent stable DASH candidate, so original T2 correctly charged **0** extra over **39** ticks; original Goal REACHED and action count **3**. [Artifact #12870210563](https://github.com/rinsakamo/relay-self/actions/runs/40809593148/artifacts/12870210563). This is retained as an important *no inferred charge* control.

## Implementation

1. The exact frozen T1w Paper snapshot implementation from commit `2672d0a1fe15584d16c2426540c528410bbb8c27` was adopted into the isolated working branch and extended in the existing `m02_paper_dev` Java file. It is compiled only in the new DEV G3.2 workflow. Its new flag `t1u-modifier-identity-dev: true` is **default-OFF**, requires the existing `t1u-gait-dev`/T1f observer, and adds an ordered bounded `speed_modifier_details` array **inside the same existing Paper tick callback / same Paper plugin message**. Each entry is actual Bukkit `AttributeModifier.getKey().toString()`, `getOperation().name()`, and `getAmount()`. No separate physical reader, owner, command authority or extra Node clock.
2. The sole original Node `paper_snapshot_admission.mjs` and Python `t1f_protocol.py` accept either the exact prior five-field gait or exact new opt-in six-field source; new data requires proper namespaced unique sorted keys, operation, finite bounded amount and exact modifier count. Malformed, repeated, unsorted, out-of-bounds or non-namespaced fields refuse. Existing source shape remains supported.
3. G1 applies *stable* candidate status only if all exact modifier detail fields agree across two adjacent admitted Paper snapshots, not merely the count/effective total. The opt-in `--g3-modifier-identity-dev` additionally gates G3: Paper's exact keys, `MULTIPLY_SCALAR_1` operations and amounts `minecraft:sprinting ≈ +0.3000000119`, `relays49dashdev:forward_dash_only = +0.5`, base≈0.1/effective≈0.195. A lookalike pair with the same apparent speed but foreign modifier key, wrong operation, wrong output or missing identity falls back to one conservative MOVE advance, **no extra DASH energy debit**.
4. The previous G3.1 original **Paper-armed S49 Action scope** remains compulsory to post an extra debit: the one T2 owner must hold `active_action == g3_dash_approved_action_dev != None` on that WorldTick. No new M0 owner, no second P1 fatigue state, no new L0 Action issuer. Unclassified/body-transition observations never mint a WAIT or an estimated DASH duration.
5. Tests: Node strict schema/negative shapes, Python exact key/power positive and wrong key/operation/power or absent-detail negative, Action owner scope negatives. All optional and default-OFF. Existing other DEV and main behavior unaffected.

## Three native Paper Worlds (same source HEAD)

| Real source-bound result | World 1 | World 2 | World 3 |
|---|---:|---:|---:|
| Goal | REACHED | REACHED | REACHED |
| Final native Goal error (m), within L1 tolerance 0.55 | 0.186687974 | 0.046484361 | 0.465716758 |
| Original S49 S16-closed Action count = T2 receipts | 3 | 3 | 2 |
| Consecutive original T2 P1/M0 WorldTicks | 40 | 40 | 34 |
| Paper DASH plugin positive modifier callbacks | 3 | 3 | 3 |
| Stable exact-ID G1 DASH candidate intervals | **1** | **1** | **1** |
| T2 owner DASH extra debit (virtual M0 units) | **0.010** | **0.010** | **0.010** |
| World tick of actual charge | 28 | 32 | 32 |
| Stable other applied gait candidate updates | 11 total | 11 total | 8 total |
| Conservative unknown fallback P1 updates | 29 | 29 | 26 |
| Existing T2 owner.failed | false | false | false |
| Full accepted packet→Paper tick attestation | false | false | false |

Independently extracted all three archived G1 and T2 JSON original files and checked each source hash against the original goal report. For **every one** of the 3 positive, unique charged WorldTicks: the immediately adjacent Paper source gait records precisely:
```json
[
  {"amount": 0.30000001192092896, "key": "minecraft:sprinting", "operation": "MULTIPLY_SCALAR_1"},
  {"amount": 0.5, "key": "relays49dashdev:forward_dash_only", "operation": "MULTIPLY_SCALAR_1"}
]
```
Paper `speed_value = 0.1950000046938658`; effective nominal base `0.10000000149011612`. The observed horizontal chord on those source intervals was 0.311843100m, 0.346623315m and 0.311843100m respectively; **not calibrated steady-state DASH speeds**. The original T2 `active_action` and `g3_dash_source_action_scope_dev` on **each debit** both equal `goal-approach-demo-step-1`. One debit per stable/eligible WorldTick, no repeated M0 body ticks and no double P1 transitions.

The first three-World experiment's completed source changed neither Paper/DASH physics model nor default G2/G3 behavior; these are read-only observations added to one existing Paper-to-T2 pipeline. The preceding one-World result of zero eligible stable candidate still correctly produced zero DASH extra; timing differences across trials are real and not papered over.

## Scope limits / next step

Even exact modifier key + power inside one Paper tick is **not** authenticated client physics-step → movement packet → Paper accepted player movement for all of that tick. The two-snapshot gait condition is intentionally conservative; it can **undercount physical DASH-positive moments** and should not be extrapolated as a fully paid duration. Paper modifier callback and Node applied controls need not occur at precisely the same client tick. The +0.5 speed attribute does not prove 50% actual displacement at matched speed or fatigue; the 20-second full DASH model, speed controller and L0 policy are not calibrated by these short runs. No R qualification or V science requested, no FULL, main or Draft PR #545/#634 touched.

**Engineering next**: use exact-ID observations to calibrate repeated matched gait trajectories, then add bounded L0 gait choice governed by Goal-distance tolerance and current single P1/M0 available budget. Keep narrow DEV opt-ins and preserve the existing Action and World owners.


## Post-run focused negative-control audit

After the three physical-World success (no change to the physical runtime code), two additional same-source focused cases were committed at `fcfaf486585a32e27d2b913e8a9665d42bcd22b6`:

- Both observed snapshots claim effective speed 0.195 and have the expected DASH key/power, **but the vanilla `minecraft:sprinting` modifier is +0.29 rather than +0.30**. The strict G3 candidate returns unknown, leaves original T2 ticking, and posts **zero** DASH extra.
- First snapshot carries DASH modifier +0.40 while second has +0.50, both still report 0.195 effective speed. The G1 consecutive modifier-identity stability gate rejects this transition; no DASH extra P1/M0 posting and no invented WAIT.

[Focused CI #40810483095 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40810483095): **88 Python 3.12 focused tests**, **28 Node** strict source/protocol tests, Ruff/Python syntax PASS. These are **offline negative controls**, not physically injected foreign modifier trials. The physical three-World source HEAD remains `c8aed7ceb063c8b1fc573a345c091c332cc3b328` and its archived SHA256s are unchanged.
