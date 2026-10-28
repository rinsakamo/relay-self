# RelaySelf S49 DEV — L2/L1 Goal Interface → Autonomous L0 Feedback Loop

2026-10-28 JST. **DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Architecture and scope

Previously, original S49 L0 controlled `MOVE_AWAY` following each independent zombie event, with 1–3 native S16 outcomes. The XZ feedback DEV proved the World can keep moving between Action terminals, that scalar movement totals do not equal coordinate goal error, and that the target must be locked before the next Action.

This branch adds a **persistent typed target** and a bounded self-contained L0 loop:

1. `L2GoalProposal` declares target World XZ, intent/session IDs, purpose, acceptable tolerance range, and emergency interruption distance. **In DEV this is supplied by a human/operator test program, not produced by a real L2 model.**
2. `compile_l1_goal_dev` selects a tolerance from the purpose and original XZ distance within the higher-level bounds, with an independent typed L1 provenance. **This is deterministic L1-style policy code, not a trained/habituated L1.**
3. `ObservedGoalL0` owns the same goal throughout the run. It uses each **fresh correlated native probe**, current XZ position, forward distance, lateral deviation, and a danger check to decide MOVE / WAIT_VERIFY / REACHED / INTERRUPT / NEEDS_REPLAN. A new zombie *event* is not needed for another MOVE. It requests upper-level reconsideration for overshoot, lateral error >0.30m, nonprogress or exhausted budgets.
4. The alternate DEV admission in `S49GoalExecutorDev` is **the same inherited NormalSessionActionExecutor ActionSupervisor**; PROPOSE and ISSUE grants are independently scoped per actual probe, and the existing `start_and_propose_bound_execution`, `ActionLifecycle`, `build_mineflayer_command`, `execute_mineflayer_command`, S15 ACK/CLEAR and S16 outcome are reused. The legacy S14 **zombie-specific S12/S13 route is NOT reused** or passed off as a goal planner. This is explicitly a provisional *goal-specific DEV* S14 admission path and cannot be called legacy-S14 qualified.
5. An L0 decision within tolerance does **not** immediately declare success. `WAIT_VERIFY` releases inputs and waits for another fresh probe, and only `REACHED` after stable XZ and within the L1 tolerance ends the foreground goal. The World is never paused, and no forced tick-phase alignment or always-on synchronous trace is used.

The DEV navigation primitive remains **forward-WALK along the native +Z orientation**, with max 6 Action attempts and max 18 observations, input duration 0.10–0.35s and explicit upper-level replan rather than blind forward driving upon sideways motion, overshoot, dangerous zombie or lack of progress. Arbitrary heading/turns, reverse, obstacles, dynamic L1 adaptation, learned L1 or an actual L2 planner are not implemented or claimed.

## Source files

- `src/relay_self/goal_navigation.py`: L2 proposal, deterministic L1 tolerance, L0 goal decision/capacity, stable stop and interrupts.
- `adapters/mineflayer/s49_goal_executor_dev.py`: opt-in goal-specific typed S14 DEV admission through the inherited original S49 supervisor/S15/S16, with fresh probe/independent grants.
- `adapters/mineflayer/s49_goal_loop_real_dev.py`: real Minecraft disposable World, real initial probe, predeclared XZ goal, autonomous L0 observation/Action feedback, terminal cleanup and raw original report.
- `tests/test_s49_goal_navigation_dev.py`: purpose-dependent L1 precision; no zombie event needed; repeated native observations; jitter/settling; upper-level escalation; threat interrupt; stale, foreign, truncated source denial.
- `.github/workflows/self-l0-autonomous-goal-dev.yml`: Python3.12 focused/Ruff/Node22 first; original Mojang 1.21.8 and Mineflayer4.39.0; final source/terminal checks and always-artifacts.

## Verified real Minecraft DEV (2026-10-28)

[GitHub Actions #40666370691](https://github.com/rinsakamo/relay-self/actions/runs/40666370691) **completed / SUCCESS**, tested exact HEAD `38d5c1c56016f083b535fba28f8c4fd9cec22428`. Python3.12 focused+Ruff PASS, Node22 syntax PASS, original official Mojang Java21 Minecraft1.21.8 server hash/source, inherited S49 Action supervisor, S15/S16 typed native outcomes and clean Node/server exits 0/0.

DEV operator L2 source `EXPLICIT_DEV_OPERATOR_NOT_LIVE_L2`; deterministic L1 `DETERMINISTIC_DEV_POLICY_NOT_LEARNED`; real provider/model calls 0. Session `520238ca-0abd-433f-a764-a7b185894327`.

| Field | Native source |
|---|---:|
| Start XZ | (3.5, −7.5) |
| Goal XZ fixed before physical Action | (3.5, −4.9) |
| L2 target offset (World units) | 2.6m forward |
| L1 tolerance | **0.364m** |
| First MOVE duration / S16 displacement | 0.350s / 0.9607229512m |
| Second MOVE duration / S16 displacement | 0.1968707671s / 0.6472025243m |
| Third MOVE duration / S16 displacement | 0.100s / 0.2643860028m |
| Post-third S16 XZ error | 0.2820061386m |
| Fresh WAIT_VERIFY probe XZ error | 0.1102320060m |
| Fresh stable REACHED probe XZ error | **0.0984718026m** |

Five real L0 decisions: **MOVE → MOVE → MOVE → WAIT_VERIFY → REACHED**. After last control-clear, two distinct native probes confirmed settling (XZ movement 0.01176m between the final probes), final error < L1 tolerance; no 4th Action issued. This is a real repeated observation-driven L0 goal loop, **not** a loop of new zombie stimuli. Native observer seq 2→19→32→43→46. 3 native Action OUTCOMEs; S16 status EXECUTED; original ActionSupervisor never left an open action. Node exit0, Server exit0.

Raw artifact `s49-autonomous-goal-dev-40666370691-1`, GitHub artifact ID **12806197647**, ZIP SHA256 **3ef75bec4e639a174161802d6c7fe9bdaed73d2056c9abb94574699f7b25111b**.

Prior fixed bugs: Actions #40666273652 failed at Ruff before any World (five test E701 + F401 and F841); source-only style correction and exact rerun #40666370691 success. The earlier source/experiment results remain intact.

**Limits/next steps**: Real L2 goal generation and L1 learned tolerance are *not* present; this DEV goal is x-constant, +Z native forward, no obstacle or threat during this one World. Need future physical XZ turns, danger interruptions, STOP under changing threats, time-budgeted plan reconsideration and real L1 habit retention. Do not conflate an execution route which uses explicit goal-specific provisional admission with fully integrated production S12/S13/S14 qualification. No local World besides this isolated DEV, no QUAL or SCIENCE grant, main/Draft #545/#634 unchanged.
