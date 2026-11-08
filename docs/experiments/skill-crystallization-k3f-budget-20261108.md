# RelaySelf K3-F — opt-in max 10 Action capacity comparison (DEV)

**Classification: DEV_ONLY / SYNTHETIC_SHADOW / NO_REAL_GEMMA / NO_REAL_WORLD / NO_NATIVE_S49 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

Parent: [Draft PR #794](https://github.com/rinsakamo/relay-self/pull/794), exact base HEAD `29b1f8c92ee950c76c6a3836b112b19cdd73cba6`. Research Issue #431.

## Decision

The experiment tests whether raising the original Skill's `max_actions` from **4 to 10** changes its ability to achieve `target_distance=3.2m`. Ten is a **maximum**, not a requirement to issue ten moves. A Skill immediately stops after reaching the Goal; failed Skills stop on their budget cap. No automatically issued postfailure fallback, no new Intent grant.

**Do not directly rewrite K3-B/K3-E historic Schema or S49 physical owner budget**. K3-F provides an opt-in `budget10_schema()` and `validate_budget10_shadow()` in an isolated new research module, preserving the original hard limit 4 in the historic DSL, prompt and runtime. Existing real Gemma original outputs are immutable.

Changing just the number in the original DSL is insufficient: the historical mock simulator generated only **five** prospective movement effects per trial. A ten-Action simulation attempting a sixth step would get `MISSING_PHYSICAL_OUTCOME`. K3-F therefore generates **fresh** deterministic simulated trials with ten potential effects, and does not invent sixth-to-tenth outcomes for any saved historical attempts.

## Predeclared synthetic experiment

- Exploratory seed **20261207**, now exposed and NOT available for another blind L2 assessment.
- 64 new paired trials in two regimes (32 each) sharing the old Skill's originally applicable normal-surface starting interval `[2.314917, 2.457525)`.
- `changed`: four-to-ten movement deltas are sampled from 0.18–0.23m per Action.
- `slow`: 0.09–0.14m per Action, a deliberately slower **synthetic stress condition**, **not** a claim about the physical Minecraft World.
- In each trial, compare the exact same start and effect sequence with Action caps **4 and 10**; also report the intermediate caps **5, 6, and 8**.
- Both compare with the existing fixed-two-Action baseline. These are Action-count proxies, **not** real energy or latency observations.
- Stop at Goal 3.2m immediately. Assert a common observed prefix for both budgets and no extra Actions when the four-Action policy already succeeded.
- Use original, saved `first-report.json` to validate the old Skill and its evidence IDs; do not synthesize or edit its source observations.

## Preliminary capacity results

The below values were independently reproduced by executing the previously retained K1 `MockIssuer`, `run_skill`, and `run_baseline` with the K3-F registered trial generator logic. This is a **local replay of the physics contract**; the brand-new K3-F module itself and the full real repository pytest/Ruff/CI have **not yet been executed** here.

| Regime (32 each) | Cap 4 | Cap 5 | Cap 6 | Cap 8 | Cap 10 |
|---|---:|---:|---:|---:|---:|
| Changed Goal success | 23/32 | 32/32 | 32/32 | 32/32 | 32/32 |
| Changed synthetic Actions | 128 | 137 | 137 | 137 | 137 |
| Slow Goal success | 0/32 | 0/32 | 0/32 | 32/32 | 32/32 |
| Slow synthetic Actions | 128 | 160 | 192 | 242 | 242 |

The fixed 2-Action baseline succeeds 0/32 in either regime (64 mock Actions each). At cap 10, the longest successful trial used **5 Actions** in changed-motion and **8 Actions** in the slow stress regime. There were no post-Goal actions, and no automatic escalation/fallback actions.

The two regimes and their movement ranges were chosen for capacity stress testing. The strong apparent gain is **not** evidence that ten real S49 Actions are appropriate, beneficial, affordable, or safe; it is only evidence that the simulator's four-Action constraint was preventing Goal completion under the chosen motion effects.

## Reproducibility (run with the real repo)

From the new child branch, Python 3.12+:

```bash
python -m pytest -q tests/test_skill_crystallization_dev.py \
  tests/test_skill_crystallization_k3b_dev.py \
  tests/test_skill_crystallization_k3c_dev.py \
  tests/test_skill_crystallization_k3d_dev.py \
  tests/test_skill_crystallization_k3e_dev.py \
  tests/test_skill_crystallization_k3f_budget_dev.py

python -m ruff check \
  experiments/skill_crystallization_k3f_budget_dev.py \
  tests/test_skill_crystallization_k3f_budget_dev.py

python -m experiments.skill_crystallization_k3f_budget_dev \
  --first evidence/l431-gemma-20261108/first-report.json \
  --seed 20261207 --n 64 \
  --out /tmp/k3f-budget4-vs10.json
```

The new CLI uses exclusive-create for output. Compare resulting metrics and Action traces against the historical old Skill, and verify previous evidence SHA256 manifests remain unchanged before claiming source admission.

## What this does not prove

- No real Gemma prompt has been updated to permit ten actions, and no fresh Gemma judgment has been elicited.
- Neither physical S49 permission nor actual per-Intent Action budgets were changed.
- The original 4-Action Skill remains suspended in the historical K3-D/K3-E setting. All original data retains its old 4-Action outcome.
- The separate K3-D Skill holdout seed **20261126** and K3-E real PROBE seed **20261205** remain unopened by this code.
- This does not establish an autonomous L2→L1→L0 crystallization, continuous survival, or real-world Goal improvement.

## Next gate

If integrated focused tests, Ruff, source SHA audit and CI pass, use a distinct **one-shot** local Gemma probe with an explicitly opt-in **1..10 Action** Schema and unambiguous budget instructions. Ask whether a previously failing Skill should extend its cap, narrow applicability, test motion effects or ABSTAIN. Make source evidence/physical permissions independent. Reserve a **new** unopened independent holdout for the revised Skill rather than reusing exploratory seed 20261207, K3-D holdout 20261126, or K3-E PROBE seed 20261205.
