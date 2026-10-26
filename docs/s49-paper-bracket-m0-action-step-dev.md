# RelaySelf: S49 issued MOVE → Paper P1 bracket → M0 Action step DEV

2026-10-26. Explicitly opt-in, disposable Minecraft World, isolated
`self/dev-s49-forward-motor-admission-20261026`. main and Draft PR
#634/#545 are NOT modified.

## DEV result

Tested source HEAD `a6e49fed4e208427c0d1054aa20493c2dfdec7f5`.
[GitHub Actions real Paper trial #40314945991 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40314945991).
Python 3.12 focused + negative controls, Ruff, Node 22 tests,
Java 21 Paper modifier compilation, one disposable Paper 1.21.8 real World,
original S49 S14/S15/S16 normal Action owner and both native OUTCOMEs,
Paper modifier disarmed, Java and Node clean exits PASS.

### Same-source native and Paper evidence

* Original S49 first `MOVE_FORWARD_SPRINT_DEV` action
  `s49-native-move-20` and original second action
  `s49-native-move-57`, both terminal S16 OUTCOME and
  native effect/cleanup ACK/observed movement.
* Paper ARM world fullTime **250**, callbacks at each of
  **251..263** (13 consecutive elapsed World ticks), OWNER_RELEASE **264**.
  Every Paper callback and release has the same Paper World UUID,
  player UUID, Action and Mineflayer session ID.
* A strict DEV-only bracket reviewer rejects missing/duplicated ticks,
  wrong actor/World/session, abnormal release, and boost-count
  inconsistency. P1 source callback replay 13/13 PASS.
* The Paper bracket is **producer-local**, not an external trust
  attestation. In particular the Mineflayer client's time-of-day
  updates are periodically refreshed, so they do not provide an exact
  per-tick native dispatch/cleanup clock edge. The interval ARM→RELEASE
  can include pre-dispatch or post-clear tick activity. No claims of
  independent cross-host tick custody, hard side/back speed ceiling,
  or qualified input-forward packet source are made.

### True B0 M0 owner mutation

The original S49 owner, rather than Paper or the wrapper, maintains
one ordinary `B0EnergyLedger` instance. With two separate DEV gates
(`S49_M0_DASH_DEBIT_DEV_ONLY=1` and
`S49_M0_ACTION_STEP_DEV_ONLY=1`), it verifies each native S16
Action receipt and uses the **existing** `metabolism_step(action="MOVE")`
exactly once per original closed Action. The P1/Paper boost extra is
added ONLY for the first Action. The resulting basal + MOVE + extra
debit is one atomic, replay-denying B0 owner mutation per Action.

| Measured value | First issued DASH Action | Second issued normal sprint Action |
|---|---:|---:|
| Original native movement | 4.0052922843 m | 3.0301572055 m |
| Basal in one existing B0 Action step | 0.500000 | 0.500000 |
| MOVE in one existing B0 Action step | 0.250000 | 0.250000 |
| Observed/P1-replayed DASH extra | 0.08633238849 | 0 |
| Total B0 owner debit | 0.83633238849 | 0.75000000000 |
| Existing B0 owner balance after | 11.16366761151 | 10.41366761151 |
| Owner M0 step | 0→1 | 1→2 |

P1 F = 0.600000 → 0.617712241, first/last applied motor
power 0.8021972523→0.7678689696; Paper sampled XZ maximum
7.784603 m/s at nominal 20 TPS. The second Action has zero
P1 boost charge and no Paper boost ticks billed.

Important units: B0's `basal_cost=0.5` and `move_cost=0.25`
are defined per **M0 logical step**, not per physical Paper World
tick. This DEV implementation charges one legacy M0 MOVE step per
closed issued Action. **It does not calculate, imply or post basal
charges for the 13 Paper callbacks**, nor for idle intervals,
unobserved time, or the interval between the two Actions. Separate
World-tick metabolic rate calibration and tick custody remain required
before physical per-World-tick basal accounting.

The DEV-only method
`B0EnergyLedger.post_s49_move_step_dev(receipt, invoice, native_evidence=...)`
rejects replayed/foreign Actions, wrong scope, missing or inconsistent
Paper P1 invoice, forged S16 effect or cleanup, NaN and oversized
energy, insufficient B0 energy, and second Action without the first.
Failures do not mutate the body state or mint food energy.
Legacy `B0EnergyLedger.step` and S49 no-DEV paths remain untouched.

**Classification: DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

Next: independently align *actual S49 native control-applied to
clear-controls* intervals against Paper tick boundaries, resolve
M0 energy expenditure's world-tick units and basal/cost calibration,
then consider stage-level integration. This report does not satisfy
R/SCI gates.
