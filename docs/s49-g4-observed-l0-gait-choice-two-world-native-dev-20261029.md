# RelaySelf G4 — observed Goal-distance L0 gait selection → original S49 → one T2 P1/M0

**2026-10-29 JST.** **DEV_ONLY / G4_OBSERVED_GAIT_TWO_REAL_WORLD_GOAL_REACHED / ORIGINAL_S49_S16_AND_SINGLE_T2_OWNER / FULL_PACKET_TICK_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Goal and exact implementation

After G3.2 verified Paper modifier identities and the one S49-Action-scoped T2 P1/M0 owner, G4 replaces G2's fixed first-three-Action gait switches with per-Action, **observation-driven** DEV L0 selection.

- Branch: `self/dev-l1-t2-action-boundary-20261028`. **Exact latest two-World-tested source HEAD:** `a359972001bc0c20f04551989bad8ff8d468f1e1`. No main or protected Draft PR #545/#634 changes.
- `adapters/mineflayer/g4_observed_gait_choice_dev.py`: select one requested **DASH/RUN/JOG/WALK** from the original native `L0GoalDecision` (fresh XZ, remaining forward distance), the original L1 distance-derived tolerance and the **same original T2 P1 fatigue fraction + M0 energy**. The model-only P1/M0 budget is an *advisory speed choice*, **never S49 issuance or a claim of physical application**. A short remaining clearance or depleted P1/M0 selects slower gait. DEV thresholds / assumed speeds are explicitly uncalibrated.
- `adapters/mineflayer/s49_goal_executor_dev.py`: maps that choice to the **same existing S49 supervisor**: DASH and RUN use original forward-sprint Action; JOG uses original forward `set_control`; WALK uses original `set_forward_sneak_dev`. The G4 mode is bounded by explicit DEV gates and the original live T2 owner; DASH requires the separately Paper-armed first S49 Action. No second Action issuer, native receiver, WorldTick owner, P1 dimension, or M0 debit path. There is a mandatory existing Node `S49_GOAL_G2_SNEAK_DEV_ONLY=1` gate on the G4 WALK path, now also refused **before S49 issuance** when absent.
- `adapters/mineflayer/s49_goal_loop_real_dev.py`: G4 runs after each original L0 native `MOVE` observation, before the original Action. The actual native S15 dispatch effect and whether its ACK was **applied** are saved alongside each chosen gait in `native_actions`. Original S16 and next fresh L0 observation—not nominal speed estimates—decide Goal progress/REACHED. G3 exact-modifier T1u and original single T2 accounting remain active.
- `.github/workflows/self-g4-observed-gait-goal-paper-dev.yml`: one disposable actual Paper 1.21.8 World per run. Strict G3/T2 scope, bounded schema checks, source-file hashes, every G4 choice→original S15 dispatch effect/APPLIED and original Action/T2 receipt equality. Python 3.12, Node 22, Java 21. Default-OFF. No FULL/QUAL/SCIENCE.

## Two independently repeated real Paper Worlds

| Original native result | World A | World B |
|---|---|---|
| Workflow | [#40812397064 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40812397064) | [#40812430686 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40812430686) |
| Exact tested HEAD | `43258feaa566f304819f72175bdc34381806581f` | `a359972001bc0c20f04551989bad8ff8d468f1e1` |
| Original Goal | **REACHED** | **REACHED** |
| Final horizontal XZ error, L1 tolerance 0.55m | **0.460108906837m** | **0.443079975202m** |
| Original S49 S16-closed Actions | **6** | **5** |
| L0 gait request sequence | DASH → RUN → WALK ×4 | **DASH → RUN → JOG → WALK ×2** |
| Native S15 effect ACK for each requested gait | **all 6 applied** | **all 5 applied** |
| Original admitted consecutive T2 WorldTick P1/M0 transitions | **58** | **53** |
| M0 final tick, exactly one per T2 row | **58** | **53** |
| G1 stable Paper sneak-forward candidates | **3** | **1** |
| G1 stable ordinary-forward candidates | 0 | **1** |
| G1 stable Paper DASH-key candidate intervals | 0 | **2** |
| Original T2-owner M0 DASH extra (DEV virtual units) | **0** (no stable eligible DASH; no inferred debit) | **0.020** (2 × 0.010) |
| T2.owner_failed | false | false |
| Fully R-qualified packet→Paper WorldTick gait | **false** | **false** |

### Original evidence and independent audit

- World A [artifact #12870668295](https://github.com/rinsakamo/relay-self/actions/runs/40812397064/artifacts/12870668295), ZIP SHA256 `0c8c45bc373686faa19ce4fb33946819334eac18b6cb89264152aed162770a52`.
- World B [artifact #12870499042](https://github.com/rinsakamo/relay-self/actions/runs/40812430686/artifacts/12870499042), ZIP SHA256 `a506453f3c82e07f8642c450a3b4fd81324a6aa8fe45cf10ece9ca59b86fe054`.
- Audited both ZIPs: all four derived G1/T2 JSON SHA256 hashes match the original `goal_report.json`; M0 body ticks are sequential 1→58 and 1→53, and every original P1 WorldTick equals its T2 source row's Paper WorldTick. In World B the **only** two extra paid ticks were Paper WorldTicks **34/35**, and both have `active_action == g3_dash_source_action_scope_dev == goal-approach-demo-step-1`. No extra debit in World A despite positive Paper DASH activation callbacks, because the adjacent stable exact-DASH candidate was missing.
- World B actual five original S49 dispatch effects: DASH=`set_forward_sprint_dev`, RUN=`set_forward_sprint_dev`, JOG=`set_control`, WALK×2=`set_forward_sneak_dev`. All original S15 dispatch ACKs applied; positive native S16 displacement and Goal closure. World A's 6 original S49 actions also all applied.
- [Focused CI #40812430638 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40812430638): **88 Python 3.12 focused PASS, 28 Node protocol PASS**, Ruff/Python syntax PASS. The exact physical-tested HEAD was also checked by physical workflow's focused gate. These tests are engineering DEV; no independent R/V grant.

## Retained failed original / correction

- [Failed physical World #40811969405](https://github.com/rinsakamo/relay-self/actions/runs/40811969405) is **not hidden**: original S49 first three DASH/RUN/JOG Actions achieved valid native S16 OUTCOME, then the L0 policy chose a **fourth WALK**. Its existing Node motor rejected `set_forward_sneak_dev` because `S49_GOAL_G2_SNEAK_DEV_ONLY` was OFF; the fourth Action therefore became UNKNOWN and the original T2 boundary correctly **latched/fail-closed**. 35 prior WorldTick rows remained source-bound; **no false Goal success** or automatic duplicate fourth Action.
- Fix: enable the existing Node sneak gate **only** for the explicitly opted-in disposable G4 World, and add S49 pre-issuance rejection when missing, plus a focused gate test. Do not add a new native sneak implementation. Reruns World A and B passed.
- Earlier focused failures (Ruff import spacing, a negative test's exception-message expectation) were scoped test corrections, not physical Goal pass claims.

## Limits / next

G4 now requests four different physical motor modes and uses real native Goal feedback, but the **mode selection thresholds and nominal gait speeds remain provisional hand-coded DEV policies**. G1 Paper snapshots are intermittent; the actual movement packet→Paper accepted-tick interval cannot yet be exhaustively attributed to each mode. The 0.55m tolerance does not certify precise stop at every desired coordinate; no learned L1 selection or autonomous live L2, no R-qualified per-physics-tick gait, no calibrated full 20-second DASH fatigue. Missing stable DASH snapshots correctly cause **zero M0 extra** and therefore possible physical undercharging, not invented source.

Next G4.1: improve bounded WALK near-target stopping efficiency and compare otherwise matched runs by physical native displacement and Action count, ensuring L0 handles oscillation/overshoot via observation rather than predetermined durations. Preserve original S49, G3 P1/M0 single owner, no force-push/main/Draft/QUAL/SCIENCE.
