# RelaySelf — L0 autonomous goal: real Minecraft threat interruption (DEV)

2026-10-28 JST. **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Aim

Advance the proven L2/L1-style typed goal → one bounded L0 native XZ observe/act loop. In the previous official Minecraft 1.21.8 DEV World, a fixed 2.6m World goal was approached via three original typed S16 Actions, then stable WAIT_VERIFY → REACHED, within L1-style 0.364m tolerance and without a new zombie event. L2 was an explicit DEV operator, and L1 tolerance was a deterministic policy, **not a live L2 model or learned L1**.

This step tests whether a **real new threat observed by the same native Mineflayer reader** interrupts an otherwise ongoing goal without being confused with goal completion, without any additional Action issuance, and leaves a source-identified goal handoff for higher layers. **No higher-layer replan is executed** here.

## Isolated development, two fresh World cases

1. BASELINE: same original vanilla Mojang 1.21.8 / Java21 / Mineflayer4.39.0, same 2.6m fixed XZ goal, no zombie injected, preserve native S16 and stable REACHED.
2. INTERRUPT: same goal and native single-action owner. After the **first original S49 S16 OUTCOME is closed**, the DEV test operator sends a normal Minecraft server console command to summon a frozen zombie about 0.65m from the real player. This command is merely a World stimulus and **does not attest** any native observation. On the next correlated native `probe`, L0 checks untruncated entity coverage, actual zombie entity ID/distance and World XZ before deciding. A real threat within the goal's 1.5m danger threshold must yield `INTERRUPT`, not another `MOVE`.
3. The interrupt branch must end with exactly one native S16 Action, no open Action, no follow-up issue; store original typed goal ID/intent ID/session, unchanged XZ goal, L1 tolerance, real probe sequence/request/provenance, observed threat entity ID and distance and current remaining goal error. Do not call the marker a successful escape or an L2/L1 replan.

This experiment probes **between Actions**, not asynchronous interruption of an already-in-flight Action. The existing L0 danger check has first priority over reaching its goal at an observation, but has not been tested against very fast mid-Action projectiles or ambushes. To support the latter, S49 would need its existing true L0 physical control-clear preemption integrated into this goal loop. The World stimulus is intentionally a single stationary zombie, not a proof of general obstacle avoidance.

## Proof obligations

- Two fresh independent vanilla Minecraft sessions, actual native S16 and exact original Action owner, no extra native packet reader or issuer.
- Python3.12 focused, Ruff, Node22 before any World; original clean Node/Server exits and exact original source reports in artifact.
- Fail closed if real zombie not observed; a console summon alone is insufficient.
- Negative tests for missing source report, stale or untrusted probe, and danger while already within target tolerance; genuine `INTERRUPT` wins.
- BASELINE REACHED and INTERRUPT handoff must both succeed. Any incomplete/faulted World retained as failure; no substitute synthetic outcome.

Files: `adapters/mineflayer/s49_goal_loop_real_dev.py` (opt-in real DEV World stimulus and verified handoff), `adapters/mineflayer/s49_goal_real_threat_review_dev.py` (two-World evidence reviewer), `tests/test_s49_goal_real_threat_dev.py`, `.github/workflows/self-goal-threat-interrupt-dev.yml`.

No modifications to main, PR #545/#634, S18 historical blob, real QUAL/SCIENCE, or product default path.
