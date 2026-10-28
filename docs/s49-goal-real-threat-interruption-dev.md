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

## Native Minecraft DEV result — 2026-10-28 verified

[Actions #40667336592](https://github.com/rinsakamo/relay-self/actions/runs/40667336592) **completed/SUCCESS** at source HEAD `db919b5c398b255adba10ca346b95d043fad3b45`. Python3.12 focused **20 PASS**, Ruff PASS, Node22 bridge syntax PASS; both independently started official Mojang 1.21.8 Java21 Minecraft servers / Mineflayer sessions; original Node and server exits 0. Real original S49 same inherited ActionSupervisor, typed S15/S16 outcome, no additional issuer/packet reader/model calls.

| Native evidence | BASELINE World | INTERRUPT World |
|---|---|---|
| Session ID | `82af385c-2c74-4f8c-8fd7-56e10b91595e` | `2ab6408d-113a-476c-ab5c-3a73010adb9a` |
| Original target offset | 2.6m +Z | 2.6m +Z |
| Physical original S16 Actions | 3 | **1** |
| Last L0 result | `REACHED` | **`INTERRUPT`** |
| Remaining real World XZ goal error | **0.01467334511079521m** | **1.2496299175366696m** |
| Extra Action after interruption | n/a | **0** |
| Observed zombie source | none | Mineflayer correlated native probe seq **24**, zombie entity ID **2**, distance **0.6964529460785192m** |

Original first S16 closed: Action ID `goal-approach-demo-step-1`, `s16_status=executed`, terminal `outcome`. Only then did the DEV World operator request `summon minecraft:zombie`; this **console command did not count as observation**. A later actual Mineflayer native probe with session ID, request ID, real coordinates and non-truncated entity registry supplied the observed threat that triggered L0. The goal still had 1.24963m remaining, so the interrupt was **not** a disguised arrival.

Verified original L0 handoff retained original `goal_id=approach-demo`, `intent_id=goal-navigate`, session, original target XZ (1.5,0.10000000000000009), L1-style tolerance 0.364m, current position (1.5,-1.1496299175366695), probe seq24/request ID/provenance, threat ID2/distance0.69645m, and no open Action. The old L0 controller closed this goal-following episode and issued no second MOVE. `upper_layer_replan_executed=false`: only an upper-level handoff, **no actual L1/L2 replan nor escape**.

Auditor verdict: `S49_GOAL_REAL_THREAT_INTERRUPT_DEV_PASS`, with `S49_GOAL_REAL_WORLD_S16_THREAT_HANDOFF_TWO_WORLDS_DEV` result. No Node/Paper tick lockstep, no world-fixed instant responses, no synthetic threat reader. Raw artifact `s49-goal-native-threat-two-worlds-40667336592-1`, artifact ID **12806033893**, ZIP SHA256 **67d529e1789c1b5dd452aa53dd9a5aa8f586b9c78649c3b2b107a1826327a2a2**.

**Constraints:** Interruption was measured **between** original Action completions, not while a motor command was physically running. The static zombie was DEV-injected, not a naturally attacking or moving enemy; no claim of dodge, interrupt latency, general hazard competence, or further plan formation. This is isolated engineering evidence, not qualification/science or trained L1.

**Next engineering step:** connect actual in-flight S49 L0 preemption (existing clear-controls authority) to a goal loop under moving hazard stimuli, then evaluate turn steering and obstruction with fixed target and the same true native XZ/error criteria. An actual learned L1 tolerance requires separate memory/experience integration and should not be claimed from deterministic source code.

main and Draft PR #545/#634 untouched. **DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
