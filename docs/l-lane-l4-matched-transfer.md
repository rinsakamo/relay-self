# L Lane L4 — prospective matched learning/cheap-control transfer review

Owner #426, product #537, V science #544. Exact L3 #606 base
`8d0ad7a834b768165ee527f3a90e7f986cdb30ee` (L2 #603 and L1
#594 ancestors). This is ONE L-owned Draft. Frozen S9 #609, R6 #610,
V1 #595, historic S1-S8, R1-R5, old A/B/C, original WSL2 RSEE and
protected main remain read-only/unmerged.

## Why this milestone is needed

S9's operator-reported bounded real Minecraft trial:
- 1 physical owned session, 2 controlled NoAI zombie encounters with
  distinct S49 executed Actions and 2 S3 observed Memories;
- one read-only historical Memory recall; 0 S10 learning updates,
  0 S11 Habit grants, no separate authenticated task-goal outcome;
- no matched cheap-control condition, independent intervention/randomization,
  heldout different session or source-equivalent resource measurement.

Two successful physical movements do **not** establish Memory causality.
S8 and S9 have different code and physical sessions, so comparing their
Action counts (1 vs 2) also **cannot** be a matched cheap-control result.

R6 #610 can read original S9 bridge/S3 bytes only on the user's host;
GitHub CI does not independently attest actual host bytes. V1 #595
reports G3 science NO-GO; this L4 slice does not replace either owner.

## Contract: separate source, hypothesis, comparator, goal and cost

`src/relay_self/learning_contrast.py` provides immutable
`ProspectiveTrial` records for a FUTURE independently executed experiment.
Each pair has one predeclared RETAINED-memory arm and one same-source
CHEAP exact-cue arm (cheap baseline is a true executed comparator, not
a hypothetical value). Both require independently attested original
decision, S49 Action, task-goal and work-measurement SHA256, plus a shared
predeclared plan SHA; a digest alone is **not** a signature.

Pair comparability: same exact code HEAD, original World initialization
digest, goal specification, candidate set, cue and plan. The two physical
World sessions must be distinct, as must original evidence receipts.
Across pairs no session/source receipt may be recycled. The retained
arm must reference a known original, separately source-admitted L1
Memory from a PRIOR independent successful training session. The cheap
arm has no retained Memory. Current implementation only validates
reported identifiers and declared digests; independently verifying
experimental conditions and that cheap did not see hidden Memory is
S/R/V's responsibility.

Train and holdout cannot share source sessions or original action
identity. Independent training goal receipts are required, not the
S16 `observed_execution` flag alone and not an L2 match/surprise.
At least 2 heldout matched pairs by default (engineering only, not
statistical power justification), with at least one cue **not** in prior
training. No lookahead from heldout to train. A non-overlapping cue
comparison is a *candidate* transfer stratum, not proof of valid
out-of-distribution generalization.

The same physical measures must carry calibrated consistent work-unit
meaning to interpret difference. Here `measured_work_units` is a
declared nonnegative integer and **does not automatically equal joules,
watts, VRAM cost, tokens or task utility**; S/R/V must qualify what was
measured, calibration and proper resource pricing.

L4 returns one of:
- `NO_MATCHED_HOLDOUT` / `NO_GOAL_SOURCE` / `UNVERIFIED` / `NON_MATCHED` /
  `NO_TRANSFER`: no paired value claim;
- `CHEAP_NULL_EQUAL` or `CHEAP_DOMINATES`: no distinctive retained value;
- `REVIEW_LIFT_ONLY`: a *synthetic or externally supplied candidate* with
  more goal successes and no more declared work; **independent V scientific
  qualification still required**.

Every output has `science_qualified=false`,
`action_authority=false`, `learning_updates=0`, `habit_grants=0`.
No code can issue an Action, provision the experiment, create an R1 envelope,
turn an S9 operator report into actual original bytes, launch a model,
assign a research permit, authorize S10 or register S11 Habit.

## Synthetic negative controls / no new physical trial

One L4 test models the S9 situation as two observed outcomes with no
matched cheap pair or task-goal witness; it **must** return no matched
holdout, not a learning score. Another constructs source-shaped favorable
pairs but **only** returns review-only, never science/production GO.
Tests also check source mismatch, replay, training/holdout leakage, absent
separate goal/plan/work receipts, heldout leakage, unseen cue absence,
cheap tie and dominance, excessive cost, malformed or unqualified
retained Memory and wrong Action arm.

Use existing shared host runtime only, from a clean L4 independent
worktree, **offline**:

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
test -x "$BASE/venv/bin/python" || exit 1
"$BASE/venv/bin/python" -m pytest -q \
  tests/test_learning_contrast.py tests/test_habit_shadow.py \
  tests/test_forecast_bridge.py tests/test_experience_bridge.py
"$BASE/venv/bin/python" -m pytest -q
"$BASE/venv/bin/ruff" check src tests experiments adapters observability
"$BASE/venv/bin/python" tools/check_repository.py
```

No package manager/install/World stage, Java/Node/Minecraft, llama/GPU,
LLM POST, new Action or reuse of consumed Golden/S9 permits. Hosted GitHub
CI is ephemeral, not the user's operator-host RSEE qualification.

## Next handoff

S product must design and predeclare the actual task-goal semantics and
two-arm matched experiment, including physical safe rollback and independent
original Action/Goal/Cost receipts. R owners independently authenticate
original source bytes and matched source profile. V owns statistical
discrimination, chance uncertainty, comparator fairness, measurement
calibration and external scientific admission. L4 only exposes strict
reviewable conditional evidence once those owners have actually produced
it; prior S9 is an engineering result, not a positive learning witness.

Terminal ceiling even with green CI:
`L4_OFFLINE_MATCHED_TRANSFER_CONTRACT_ONLY /
S9_CONTROLLED_TWO_OUTCOMES_NOT_CAUSAL_LEARNING /
G3_SCIENCE_NO_GO / NO_S11_PROMOTION / NO_PRODUCTION_GO`.
