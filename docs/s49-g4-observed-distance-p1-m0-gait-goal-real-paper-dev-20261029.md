# RelaySelf G4 — L0 observed-distance / single-P1 / M0 gait choice → original S49 → real Paper Goal

**2026-10-29 JST.** Classification: **DEV_ONLY / G4_OBSERVED_GOAL_GAIT_ACTION_BOUNDARY_REAL_WORLD_VERIFIED / PER_TICK_GAIT_FEEDBACK_NOT_IMPLEMENTED / FULL_PACKET_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Owner / implementation scope

- Branch `self/dev-l1-t2-action-boundary-20261028`. G4 World-tested exact code HEADs: `43258feaa566f304819f72175bdc34381806581f` (World A, #40812397064) and `a359972001bc0c20f04551989bad8ff8d468f1e1` (World B, #40812430686).
- DEV opt-in only: `--g4-auto-gait-dev`, `S49_G4_OBSERVED_GAIT_DEV_ONLY=1`, existing T1f/Node/Paper, G3 exact-modifier and S49 motor approvals. No other default motor behavior is changed. No new independent Action issuer or second P1/M0 owner.
- `g4_observed_gait_choice_dev.choose_g4_observed_gait_dev` consumes the **current original L0 Goal decision** (fresh native World-probe position, remaining distance), the **unchanged L1 tolerance** from the L2 Goal, and the **existing live original T2 P1 fatigue and M0 virtual energy**. It chooses a requested mode from **DASH / RUN / JOG / WALK** and a bounded original command duration 0.10–0.35s. No mode choice claims to be a measured applied WorldTick gait.
- Rule: far first action may choose full DASH only if single P1/M0 budget admits it; moderately far action RUN; closer goal JOG; within 0.60m of remaining L1 clearance, or severe P1/M0 limitation, WALK. This is a provisional deterministic DEV heuristic, **not trained L1 behavior**. The final Goal tolerance is tested using a new original World observation, not predicted from requested speed.
- The original S49 owner and its separate PROPOSE/ISSUE grants remain the sole issuance route. Original S49 effect ACK distinguishes RUN/DASH (forward sprint), JOG (ordinary forward), WALK (forward sneak); only G4 first DASH is separately Paper-armed. The original S49 S16 terminal, control clear ACK, Goal loop and original T2 P1/M0 source remain unchanged in ownership.
- Known limitations: not a continuously updated within-Action L0 motor governor; not automatic L0 speed learning, and not full packet/tick verified. DASH extra M0 only when G3 adjacent stable exact Paper modifier + original S49 identity evidence exists; positive Paper boost **can** still result in zero paid ticks, conservatively. Minimal 0.10s input can move more than nominal residual clearance, so real World observation closes Goal, not a synthetic final-stop promise.

## Two disposable real Paper 1.21.8 Worlds

| Physical source-bound observation | World A | World B |
|---|---|---|
| Workflow | [#40812397064 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40812397064) | [#40812430686 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40812430686) |
| Artifact | [#12870668295](https://github.com/rinsakamo/relay-self/actions/runs/40812397064/artifacts/12870668295) | [#12870499042](https://github.com/rinsakamo/relay-self/actions/runs/40812430686/artifacts/12870499042) |
| Original L2 Goal / final native S16 | **REACHED** | **REACHED** |
| Final native XZ Goal error | **0.4601089068365496m** | **0.443079975202223m** |
| L1 tolerance | **0.55m** | **0.55m** |
| G4 original requested gait sequence | DASH→RUN→WALK→WALK→WALK→WALK | DASH→RUN→JOG→WALK→WALK |
| Original issued/closed S49 Actions | **6** | **5** |
| Original Action receipts in single T2 | **6** | **5** |
| Original consecutive P1 + M0 source ticks | **58** | **53** |
| G3 stable gait model candidate ticks | **11** | **13** |
| Conservative unknown P1 fallback ticks | **47** | **40** |
| Atomic original M0 DASH extra cost (virtual units) | **0** | **0.020000000000000004** |
| Real Paper terminal modifier clear | **yes** | **yes** |
| T2 owner failed | **false** | **false** |
| Qualified packet→Paper World gait | **false** | **false** |

World B's source-derived artifact was independently inspected and SHA256-verified, with the original goal report matching both `l1_t2_ledger_dev.json` and `g1_applied_gait_observation_dev.json`:

- Original G4 request, native S49 dispatched effect and final S16 OUTCOME align for each of the 5 distinct original Actions: DASH→`set_forward_sprint_dev`; RUN→`set_forward_sprint_dev`; JOG→`set_control`; WALK×2→`set_forward_sneak_dev`.
- The one original T2 ledger has exactly **53** rows and terminal M0 body tick **53**. Its attributed model modes include **2 DASH**, **5 RUN**, **1 JOG**, **9 WALK**, **4 causally cleared WAIT** and **32 UNDETERMINED** rows. These are **not** all full-tick authenticated body modes.
- Only original Paper observed WorldTicks **34 and 35** posted G3 DASH extra, each `0.010000000000000002`, inside the correct Paper-armed first S49 Action ID `goal-approach-demo-step-1`. All five original Action receipts were closed, no second owner or duplicate debit.
- G1 observed stable physical gait candidate kinds on this World included two DASH, five sprint, one ordinary-forward and one sneak-forward intervals, but a *request* and *World-observed mode* are intentionally different fields; no blanket identity claim. G1 result remains `full_tick_gait_attested=false`.
- World B ZIP SHA256: `a506453f3c82e07f8642c450a3b4fd81324a6aa8fe45cf10ece9ca59b86fe054`. Original derived T2 SHA256: `af73ea0916e5d40dffdcedce80981b351f1776a74d0c564aeafae2c984d48668`. Original derived G1 SHA256: `0e3ed2ce36e467f798974bfa1b744170c3271c2932db97ef9192eb04846d6f44`.

## Local/focused tests and retained failures

[Exact G4 World B code HEAD focused CI #40812430638 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40812430638): **88 Python 3.12 PASS, 28 Node PASS**, Ruff/compile/Node syntax PASS. The focused G4 unit tests cover the first far-goal DASH policy, coarse RUN, near JOG/WALK, high P1 and limited M0 budget, within-tolerance refusal, dangerous source refusal, invalid mode, and absent T2 owner refusal.

Earlier G4 physical failures were retained (including #40812003537, missing native S16 after a short WALK; #40812336734, missing WALK DEV opt-in). Subsequent successful real runs were **not** retrospective reinterpretations of these failed worlds: workflow changed and new disposable Worlds were executed.

**No FULL or QUAL/SCIENCE**, protected evidence, main or Draft PR #545/#634 changed. Next G4 improvement should be a bounded within-Action distance observation and slow-down/stop loop, without additional independent S49 Action issuance, followed by matched-start A/B runs measuring Goal overshoot, travel and elapsed WorldTick. The present G4 is **per-Action observed receding distance selection**, not an already proven per-tick controller.
