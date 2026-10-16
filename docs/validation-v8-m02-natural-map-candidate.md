# V8 M0.2 — natural-map viability: **candidate design only** (2026-10-16)

Authority: V #619 / #625, S #537 / #545, R #575 / #610, M #616.
This **does not amend** the frozen V7 `0.005 block` paired-path rule,
change 20 V7 SCIENCE NOT_RUN slots, or start V8 SCIENCE.

## Why separate V8?

S new five DEV World sessions [#38850179491](https://github.com/rinsakamo/relay-self/actions/runs/38850179491)
and independent R [#38850421003](https://github.com/rinsakamo/relay-self/actions/runs/38850421003) established:
- directly logged BASAL write request: `0.001 exhaustion/player tick` or 0;
- actual Paper player coordinate WALK billing: `0.01 exhaustion/actual block` or 0;
- this tests source-side accounting **not** whether those costs improve/impair viability.

R independently reopened each real `level.dat` gzip-NBT in [World audit #38868318233](https://github.com/rinsakamo/relay-self/actions/runs/38868318233): all five **NBT seed =61021**, `Data.SpawnX/Y/Z=(0,-60,0)`; five saved `level.dat` hashes differ. This saved Spawn coordinate is **not the bot's physical start location**. In [native motion audit #38868635492](https://github.com/rinsakamo/relay-self/actions/runs/38868635492) every arm started from a *different* actual packet position (e.g., BASE_ON x=-9.5,z=10.5; SHAM_ON x=-4.5,z=-9.5). The 7- or 9-packet horizontal MOVE paths were straight (packet-integrated path = net displacement) and **not** observed detours around a confirmed obstacle. Cause of differing packet count/length not established. Therefore the old paired 0.005-block condition remains failed; nominal World seed alone does not match starting conditions.

## Candidate experimental question

**Does resource-consuming BASAL and locomotion WALK physics alter autonomous L0 survival/food accessibility under finite energy and finite terrain opportunities?** This is *not* a cognition-learning test, and will not mix enemies, other agents, reproduction or L1/L2 strategies yet.

In future **independent** natural/random World seeds, create a fixed immutable world clone per seed, including terrain/chunks (not just `level.dat`) and finite, transparently staged food opportunities. For each seed, start each of five cost-factor arms from the **same confirmed native XYZ, yaw/pitch, food/saturation/health, difficulty/time/weather and L0 policy**. Start intervention/observation at an independently bracketed native World tick, use the same action supervisor and protocol, preserve all attempts and process/STOP evidence. Only BASAL/WALK multipliers differ.

The candidate source [`v8_m02_ecology_candidate.py`](../experiments/validation/v8_m02_ecology_candidate.py) proposes 8 new seeds × 5 arms = 40 possible future independent sessions, maximum 24,000 player World ticks each. These values are **illustrative trial-planning placeholders**. They are **not** power calculations, ecological coefficient calibration or authorization. A cheaper DEV pilot must test whether difficulty=hard, finite food, resource visibility, and observation time actually create a discriminating and technically feasible viability task before any final protocol freeze.

**The key distinction:** do **not** match on realized MOVE distance. Physical distance is itself a potential result/mediator of policy × terrain × metabolism. A true collision, no-progress, detour, failed pickup, starvation, timeout and death must be retained, not discarded or selected post hoc. Before-action world state and source/clock identity must be controlled; native source billing is secondary. No `WALK charge/distance` computation is possible at zero walking distance; record `NO_WALK` not success or 0-rate.

## Candidate outcomes & limits

Primary: survival time measured in real World ticks, cumulative actual edible food acquired, and native food/saturation/health trajectories. Secondary: source BASAL requested/tick, WALK debit/actual source path, obstacle/blocked/no-progress, real distance, finite food affordances and L0 Action/OUTCOME. If all arms survive the time limit, report a viability-ceiling or weak-discrimination outcome, **not** proof of no effect. Host crash/timeouts are censored, not physical deaths. Same-seed arms must retain even divergent realized paths; source accounting and behavioral causal attribution are distinct.

A finite operator-placed cooked-food opportunity is an explicit experimental affordance, **not** naturally evolved foraging, and does not represent animal prey or an adversarial agent. Any ecological fitness/cognition benefit requires separate analysis and controls. 8 seeds alone are not a justified powered efficacy study.

## Gates — currently not met

1. **S DEV feasibility:** reproducible full World/chunk cloning and controlled real player starting pose; independent pre/post World tick boundary; actual finite-food and S50/S51 outcomes.
2. **R engineering:** **fresh** independent qualification of the *new JAR and changed profiles*, configuration identity, World source, PID/ports/STOP and source bytes. Existing R third one-shot grant is consumed and cannot be reused or upgraded from DEV.
3. **V science:** approved pre-registration with final endpoints, failure/censor/time horizon/sample-size justification, independent controls and separate explicit SCIENCE grant. The candidate code never grants it.
4. **G3/production:** remains NO_GO. V7 remains 0/20 SCIENCE, V6 remains 0/48.

Offline-only reference:

```sh
PYTHONPATH=src:tests:. python -m pytest -q tests/test_validation_v8_m02_ecology_candidate.py
PYTHONPATH=src:tests:. python -m experiments.validation.v8_m02_ecology_candidate
```

The V8 draft does not execute Paper/Java/Node/Minecraft/GPU/LLM and does not alter S, R, or frozen evidence.
