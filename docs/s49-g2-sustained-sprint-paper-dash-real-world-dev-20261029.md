# RelaySelf — G2 sustained sprint and actual Paper DASH modifier, original L1→S49→T2

Date **2026-10-29 JST**. **DEV_ONLY / G2_PAPER_DASH_MODIFIER_OBSERVED / ORIGINAL_S49_GOAL_REACHED / FULL_TICK_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Independent completed real DASH World

- [Completed GitHub Actions real Paper World #40778496179 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40778496179), exact World-tested HEAD `6bd765b5e7cfaaa722407f29ed9018701ac2e97d` (the later `d51795f4` changes focused test fixture only). GitHub-hosted disposable Paper 1.21.8, Node22, Java21, Python3.12. Node/Java process exits **0/0**.
- [Original artifact #12854649351](https://github.com/rinsakamo/relay-self/actions/runs/40778496179/artifacts/12854649351), downloaded ZIP SHA256 `8e49f07bf14f99724adc3a3ef3559a178ef4b99c9f3b8dcfeffa8920fbb07ca7`. Contains source-derived G1/T2 JSON, goal report, Paper server log and runner stdout. Hashes of both JSON files match the report. **Does not preserve the complete original Node stdout or entire disposable World**. Never represent source-derived views as independently authenticated movement packets.
- Pinned Paper build60 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`; original T1w Paper observer built from frozen source HEAD `2672d0a1fe15584d16c2426540c528410bbb8c27` (run JAR SHA256 `79bce86be3a502b003c061048612907a4c7c43bde3dbd781646318b6cc8c166d`); existing S49 Paper DASH DEV plugin built unchanged from branch (JAR SHA256 `aa681c0af55da9207b202dd4559b921af6b273ca79a4c632597778f6f036c61c`).
- Explicit opt-ins, default OFF: `S49_GOAL_G2_SPRINT_PREFIX_DEV_ONLY=1`, `S49_SPRINT_MOTOR_DEV_ONLY=1`, `S49_GOAL_G2_DASH_FIRST_DEV_ONLY=1`, `S49_SPEED_ATTR_SYNC_DEV_ONLY=1`, and existing original T1f/T2/G1 gates. Paper DASH plugin armed **once** before the first original S49 forward+sprint Action, then removed after its original S16 closure; no extra Action issuer, bot connection or native reader. Later Actions are original S49 sprint without DASH modifier.

## World outcome and observed applied body evidence

| Observed result | Original World |
|---|---:|
| Original S49 Actions, issued/APPLIED/S16 OUTCOME | **2** |
| Original L2 Goal | **REACHED** |
| Final native XZ error | **0.3254084576159908 m** (L1 tolerance 0.55 m) |
| Original single T2 consecutive ledger rows | **34** |
| Original S49→T2 Action boundary receipts | **2** |
| T2 owner failed / extra P1/M0 gait posting | **false / 0** |
| Paper DASH plugin positive modifier callbacks | **3** |
| G1 stable Paper + Node two-modifier forward candidates | **1 WorldTick** |
| G1 stable ordinary sprint-forward candidates | **6 WorldTicks** |
| Paper DASH plugin release COMPLETE | **observed** |
| Unqualified client-step→Paper-tick correspondence | **NOT PROVEN** |

The G1 source recorded Paper `sprinting=true`, speed `base≈0.10000000149`, `value≈0.19500000469`, `speed_modifiers=2` in two source snapshots; one pair satisfied the conservatively defined *stable candidate* condition. Paper movement-speed attribute while only ordinary sprinting was `≈0.13000000313`, one modifier. This represents **1.5x the ordinary sprint *attribute*** (not a separately proven 1.5x physical displacement rate). The stable DASH candidate chord was `0.3466233145572746 block/tick`; six stable vanilla sprint candidates averaged `0.24240171917660117 block/tick`. These are small, acceleration-dependent filtered samples, not terminal speeds or full accepted-gait frames.

Paper callback review independently saw three `S49_DASH_DEV_TICK` positive `modifier_applied=true` lines for exactly the original action/session. The report's `paper_complete_source_observed` means original plugin release reported `COMPLETE`, not a separate authenticated motor receipt. No new P1 gauge or free extra M0 debit. There is one existing T2 owner and original S49 ActionSupervisor.

## Sustained ordinary sprint experiment in comparison

- [Earlier five-World run #40777542954](https://github.com/rinsakamo/relay-self/actions/runs/40777542954), source HEAD `ec22bd31fb2cb84eef94ec81d18ff3a0b3b17c79`, **workflow FAIL (test bug), but all five physical goal reports PASS**. The first four Worlds carried previous native obstacle, stone refresh, single sprint, crouch/normal contexts; World5 had **three exact original S49 sprint Action APPLIED/OUTCOME**, Goal error `0.18477232902212748m`, original T2 **37** consecutive ticks, **10** stable vanilla sprint candidates, candidate mean chord **0.21825983937617605 block/tick** (median `0.22924656788850184`). [Preserved artifact #12856425064](https://github.com/rinsakamo/relay-self/actions/runs/40777542954/artifacts/12856425064).
- The five-World workflow wrongly assumed an ordinary forward movement interval must occur after three sprint Actions; the original L2 Goal had **already been reached**, so no fourth normal Action was appropriate. The auxiliary workflow assertion was corrected to recognize that result.
- [Later attempt #40778128275](https://github.com/rinsakamo/relay-self/actions/runs/40778128275) failed before any new Action due to a bootstrap pre-anchor T1f `UNADMITTED` frame reaching optional G1 (not T2 source promotion); G1 later skips **only** pre-anchor nonadmitted frames after original T2 correctly processes them, and remains strict on all admitted source and source discontinuities. Its dedicated negative and positive focused tests were added. [Final focused CI #40778563581 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40778563581) on `d51795f4b2b6dc75d523c131fae4f7fa91dd3a45`: **68 Python 3.12 PASS and 24 Node PASS**, Ruff/syntax checks PASS. No FULL.

## DASH validation failures retained

- [#40777627194](https://github.com/rinsakamo/relay-self/actions/runs/40777627194): native World `GOAL_REACHED` in **2** S49 Actions, **3** Paper modifier-positive callbacks and **1** G1 stable DASH candidate; workflow incorrectly required exactly three Actions, so overall FAILED.
- [#40777931151](https://github.com/rinsakamo/relay-self/actions/runs/40777931151): World `GOAL_REACHED` in **3** Actions, **4** Paper modifier-positive callbacks, **2** G1 stable DASH candidates; workflow incorrectly required exactly two Actions, so overall FAILED.
- [#40778247509](https://github.com/rinsakamo/relay-self/actions/runs/40778247509): World `GOAL_REACHED` in **3** Actions, three positive callbacks, one stable G1 DASH candidate; Python validation heredoc had escaped literal `\\n` introduced by test editing. Corrected source text, without changing Action or Paper physics.
- Final completed [#40778496179](https://github.com/rinsakamo/relay-self/actions/runs/40778496179) checks exact `reported_action_count == original_S49_to_T2_receipts`, bounded 1–3 first sprint Actions, physical-positive and Paper source modifiers, explicit release and same source-bound T2 accounting. Succeeded.

These are DEV physical source observations only. There is **no exact client physics step → delivered movement packet → accepted Paper movement → WorldTick correspondence** here. No R qualification or V science was requested. Do not use the candidate dash speed to update P1, infer extra M0 charge, automatically enable DASH, or treat unknown transitions as WAIT. Further work is repeated speed-calibration under fixed starting speed/position followed by evidence-based single-owner P1/M0 gait integration.

Main, protected Draft PR #545/#634, frozen evidence and qualified/science lanes are unchanged.