# P1 fatigue calibration DEV candidate — low-intensity movement and recovery (2026-10-28)

**DEV_ONLY / OFFLINE_IMPL_ADDED / PHYSIOLOGY_NOT_YET_QUALIFIED /
NEW_WORLD_NOT_RUN / SCIENCE_NOT_RUN.**

Starting point: T1r successful original Minecraft DEV HEAD
`61990393d29b4bdb18ec1361096ddf30f3efbd22`.
This is an **isolated candidate**, not an amendment to its 206 original
evidence files, main, #545/#634/#626, frozen S18, or science results.

## Why old physiology cannot drive next L0 behaviour

Original experimental P1 `FatigueProfile(enabled=True)`:
- WAIT `wait_recovery_per_world_tick = 0.10`, physical capacity 1.0,
  so at 20 reference World ticks/s **full capacity can clear in 0.5 s**.
- MOVE `move_per_block = 0.04`, so an ordinary 4 blocks/s WALK would
  reach max fatigue in **6.25 s** if continuous and without any moving recovery.
- An observed 0.03 fatigue in T1r recovered in the first DEV WAIT tick.
  That observation is correct **for the previous artificial model**, not
  a validated human recovery claim. No rollback or reinterpretation of
  historical T1r PASS.

Muscle phosphocreatine (PCr) recovery research reports
about 35–45-second time constants for particular exercises, with
substantial longer recovery after all-out sprints:
https://pubmed.ncbi.nlm.nih.gov/19088770/
https://pmc.ncbi.nlm.nih.gov/articles/PMC2636983/
https://pubmed.ncbi.nlm.nih.gov/7714837/

**PCr is not identical to subjective fatigue, local P1 virtual fatigue or
metabolic Energy.** The research motivates a plausible time scale, not a
direct mechanistic calibration. The following candidate rates and simple
model are **engineering hypotheses** requiring separate behavioural tests.

## New explicit candidate (T1s)

- **One original P1 owner**: `experiments/fatigue_p1.py` remains the
  same physics API and SOURCE-of-truth. Optional
  `recovery_time_constant_world_seconds` controls recovery law.
  `None` preserves the *exact original* constant-per-tick formula.
  Historical default profile SHA256 remains **exactly** identical by
  excluding the absent new field from its SHA JSON. New opt-in profiles
  carry the tau value inside their distinct hash.
- **Calibrated WAIT**: first-order exponential decline
  `F_next = F * exp(-1/(20*tau))`, tau=40 reference World seconds,
  one original admitted complete World tick per step.
  Existing `wait_recovery_per_world_tick` acts as a safety upper cap.
  From F=1: after 1 tick F≈0.99875; 1 second F≈0.9753;
  40 seconds F≈0.36788; 80 seconds F≈0.1353. There is no magical
  exact zero after one rest tick. The exponential tail is intentional.
- **Low-intensity WALK**: `move_per_block = 0.0001` normalized fatigue
  per measured block versus legacy 0.04. At 4 blocks/s this accumulates
  ~0.024 fatigue per minute; a 0.8-block short MOVE produces only
  0.00008 fatigue — **below T1q's 0.01 quantized P1 sensor resolution**.
  Do not increase the sensor or physical load merely to reproduce T1r's
  visibly nonzero fatigue.
- Speed-specific JOG/RUN/DASH load profiles and recovery during
  submaximal locomotion are **not implemented** in this isolated WALK
  calibration. A future DASH ~20s limit must be treated as an independent
  constraint; do not claim it follows from this WALK candidate.
- M0, Paper M0.2, Energy, L0/Action authorization, blocked MOVE rules
  and actual WAIT source gating are unchanged.
- `TickAccounting(..., fatigue_profile=...)` is optional. Default
  remains legacy, so all prior T1r tests/receipts keep their meaning.
  New **T1s disposable case `t1s_calibrated_body_loop`** selects the
  candidate explicitly and reuses the original T1p/S49/single reader
  two-MOVE runtime. This is a DEV demonstration, not production adoption.

## Verification / LocalCodex

First verify branch, HEAD, exact T1r base, protected blobs and clean worktree.
Run Python 3.12:

```bash
PYTHONPATH=src:tests:. python3.12 -m pytest -q \
  tests/test_p1_physiology_calibration_dev.py \
  tests/test_fatigue_p1.py \
  tests/test_t1f_t2_dev.py \
  tests/test_t1p_body_runtime_dev.py \
  tests/test_t1q_interoception_dev.py \
  tests/test_t1r_fatigue_timecourse_dev.py
```

If system python lacks pytest use the known Python3.12 virtualenv.
Fix focused failures rather than discarding strict negative controls.
Then impacted FAST, Ruff and repository contracts only. Record initial
failures with source hashes. No FULL or implicit World/QUAL/SCIENCE.

After offline PASS, an explicitly isolated **one new disposable World**
can run the existing DEV owner:
```bash
PYTHONPATH=src:tests:. python3.12 -m adapters.mineflayer.t1e_native_dev \
 --cases t1s_calibrated_body_loop --loop-moves 2 --node-trace off \
 --output /NEW/ABSOLUTE/T1S-001 \
 --paper /VERIFIED/PAPER.jar --plugin /VERIFIED/PLUGIN.jar \
 --bootstrap /VERIFIED/BOOTSTRAP \
 --confirm T1E-DISPOSABLE-DEV-ONLY
```
Reuse canonical original Paper/native logs, command/Action/OUTCOME,
T2 accounting, P1 new profile hash, all-positive source admission and
WorldTick continuity. Audit actual exact new modeled recovery over
consecutive source-qualified WAIT_DEV ticks against the exponential
formula; do not demand original T1r REST/READY sample counts or final
fatigue exactly 0. For short WALK, 0.0 **sensed** quantized fatigue can
be the correct outcome. No high fatigue fixtures, LLM, new Motor issuer,
synchronous Node timing trace, gifted food or TPS actuator. Preserve
cleanup, original logs, FAIL trials and all source SHA.

Only after actual World run, promote from NEW_WORLD_NOT_RUN to
DEV_WORLD_OBSERVED. Never promote to qualified physical WAIT,
independent native attestation, verified human physiological model,
scientific benefit or DASH 20s behaviour.

## Remaining calibration questions

Explicit speed-mode charge (WALK/JOG/RUN/DASH) and a fatigue/recovery
model that permits realistic continuous easy locomotion, while high
intensity sprinting might exhaust in ~20 s, require later owner-backed
physical mapping. Tune those using independent movement and recovery
bounds, not a chosen action trace or desired REST/READY result.
