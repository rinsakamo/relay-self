# RelaySelf G3.1 — paper-armed original S49 Action scoped DASH expense

**2026-10-29 JST.** `DEV_ONLY / G3_SOURCE_BOUND_S49_ACTION_SCOPED_M0_P1 / FULL_TICK_PACKET_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## Existing G3 baseline (preserved)

G3 already had one original T2 P1 WorldTick state transition, one existing M0 ledger, a conservative fallback for unclassified/transition Paper snapshots, and an atomic DEV DASH extra charge (0.010 virtual M0 unit per full-power stable candidate WorldTick) on the same M0 MOVE step. Two earlier successful G3 real Worlds are documented in `docs/s49-g3-single-p1-m0-applied-gait-two-world-native-dev-20261029.md`. The Paper source alone did not bind a specific original S49 Action identifier to each charge.

## New G3.1 rule: observed modifier is not sufficient authorization

The original Paper DASH DEV plugin is explicitly armed by the disposable World runner for **the first original S49 sprint Action**. Only **after the Paper ARM acknowledgment** may the existing T2 owner receive `permit_g3_dash_action_dev(action_id)`. This operation **does not issue, authorize, or modify** the Minecraft Action or the Paper speed attribute. The original S49 supervisor independently issues and invokes `GoalT2ActionBoundaryDev.before_issue` which owns `TickAccounting.begin(action_id)`.

On every later admitted consecutive Paper source tick, a `STABLE_DASH_MODIFIER_FORWARD_CANDIDATE` is eligible for the single P1 gait advance and M0 additional charge **only if** the existing owner has a **non-null active_action matching that same one Paper-armed original action_id**. Otherwise T2 retains the original continuous WorldTick, conservatively falls back to the existing MOVE fatigue transition, and pays **zero** extra DASH M0 for that tick. An unverified control-clear/late modifier, foreign or second Action, or unarmed attribute pair never promotes extra payment. Other stable mode candidates can still advance the one P1; unrelated G1/G2 modes and default-off operation remain unchanged.

New observability in the sole T2 ledger/report: `g3_dash_source_action_scope_dev` for paid rows, `paper_armed_original_dash_action_id`, `dash_candidates_suppressed_without_active_s49_scope`. The negative source cases are covered by focused tests: no original action, foreign active action, already closed action, missing anchored source, duplicate paper-arm permit, and default-off T2.

## Exact native DEV verification

- **Exact tested code HEAD:** `80c8716ce594c6f09247826337abca31c083cf0f`, branch `self/dev-l1-t2-action-boundary-20261028`.
- [Real Minecraft Paper 1.21.8 G3.1 workflow #40807745065](https://github.com/rinsakamo/relay-self/actions/runs/40807745065): **SUCCESS**, one new disposable World, using the existing pinned Paper observer and existing S49 DASH plugin, not new Java physical motor code.
- [Original artifact #12868882535](https://github.com/rinsakamo/relay-self/actions/runs/40807745065/artifacts/12868882535); ZIP SHA256 `7a90a43a213154efc6d9d61512074a56075b5bfb99850cd2c59b08183a7c5931`. Contains the source-derived G1/T2 JSON, goal report, Paper server log and producer stdout (not entire Minecraft World or all raw Node stdout).
- [Same-HEAD focused CI #40807745082](https://github.com/rinsakamo/relay-self/actions/runs/40807745082): **SUCCESS**, 81 Python 3.12 focused PASS, 24 Node strict protocol tests PASS, Ruff/Python & Node syntax PASS. No FULL, QUAL or SCIENCE.

| Source-bound real-World result | Observation |
|---|---:|
| Original L2 Goal | REACHED |
| Final horizontal Goal error | **0.32540845761599524 m** (tolerance 0.55 m) |
| Original S49 S16-closed Action count / T2 receipts | **2 / 2** |
| Consecutive admitted original T2 P1/M0 rows | **34** |
| Single M0 virtual body tick | **34** |
| Paper DASH modifier-positive callbacks | **4** |
| G1 stable two-modifier forward candidate intervals | **2** |
| Real-World M0 additional DASH paid | **0.020000000000000004** virtual units |
| Exact paid World ticks | **29, 30**, each **0.010000000000000002** |
| Original Paper-armed Action ID | `goal-approach-demo-step-1` |
| Paid T2 row active_action and scope ID | **same `goal-approach-demo-step-1` for both ticks** |
| Stable other gait candidates / conservative unknown fallbacks | **8 / 26** |
| Original T2 owner failed | **false** |
| Full accepted packet→Paper WorldTick gait attested | **false** |

Artifact inspected independently: the derived T2 ledger has exactly 34 rows with monotonic M0 body tick 1→34. The only two `g3_extra_m0_paid_dev > 0` rows are ticks 29/30, and their `active_action` and `g3_dash_source_action_scope_dev` both match the same Paper-arm original S49 Action. The G3.1 real World suppressed-count was 0; **foreign/unarmed/closed negative cases are demonstrated by local focused tests only**, not an injected foreign speed-modifier in a real Paper World.

## Non-claims / next engineering boundary

The positive Paper attribute (0.195 vs vanilla sprint 0.130) and two-modifier G1 candidate are still *bounded physical observations*, not full client physics-step→outbound packet→accepted Paper movement tick authentication. The plugin's exact modifier key/power identity is still inferred from the isolated DEV plugin scenario and observed speed shape; the T1u `gait_dev` source currently reports **modifier count and effective speed**, not its exact key. Thus G3.1 is **an action-scoped partial DEV accounting improvement**, not complete gait/energy coverage, and uncertain/transition ticks deliberately produce no additional DASH expense. No trained L1 gait policy, fully calibrated 20s DASH fatigue profile, new P1 gauge, parallel M0 owner, or ungranted R/V test.

Remaining G3/G4 work should source-bind the modifier identity/power in the original Paper observation and improve continuous accepted-client-packet/WorldTick causal coverage before promoting complete fatigue/expenditure claims. All historical and protected blobs, main, Draft #545/#634, QUALIFICATION and SCIENCE remain unchanged.
