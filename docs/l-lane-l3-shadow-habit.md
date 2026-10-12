# L Lane L3 — guarded Habit shadow and independent goal-source admission

Owner #426. Base L2 #603 exact HEAD
`66360911c5e8c48ca85f2cf3331566f1218803a0`, whose parent is
L1 #594. Main and all sibling S (#605/#604/#601), R (#602), V (#595)
and legacy A/B/C Drafts are independent, unmerged and unchanged.
This is one **offline L3 Draft**, not a production S11 Habit implementation.

## Why this is a rejection gate, not automatic learning

L1 records an observed Action and L2 keeps a prospective predicted
consequence, optionally marking a mismatch. Neither is a signed goal
achievement. S4 physical one-shot had 181 outer frames, 0 qualified targets,
0 Action/OUTCOME/Memory. S5 identified the frozen #583 bootstrap saved
`doMobSpawning=false`. Even a later controlled zombie encounter may confirm
MOVE_BACKWARD and 0.627 m movement without independently confirming an
intended goal. No L0/S10/S11 promotion is justified by that alone.

`ExternalGoalLabel` is only an ephemeral reference to an *external*
goal-result receipt: existing L1 observed Memory ID, exact goal-original
SHA256, boolean result and provenance. Neither its dataclass nor the
passed `GoalSourceAdmission` independently authenticates bytes or signs
a claim. S/V must verify original Action/World/goal evidence and admit
actual digests from an independently owned process. Derived L2
`l2:comparison:` Memory, predicted success, movement, repeated narration,
a plausible digest string or S3 projection JSONL are **not** acceptable
goal-witness sources. R4 #602 remains the independent original-vs-derived
handoff owner. The GitHub tests construct explicitly synthetic
goal evidence solely to test fail-closed logic.

## Review procedure

- Link each label to one **original L1** Memory: exact S16 OUTCOME and
  `source_status=executed`, `reason_code=observed_execution`, source
  session, Action ID, cue and SHA; the original L1 `retrieve_experience`
  must independently return an admitted observation, not UNKNOWN or
  CONTRADICTORY.
- Require separately source-admitted original Action and goal-result SHA.
  A digest is an identity pointer, **not** proof of cryptographic
  authenticity. No implicit signed source is created by this wrapper.
- Predeclare training and independent holdout source sessions. No
  replayed/overlapping original observed Memory, session or digest is
  allowed. Minimum 3 independent training sessions and 2 holdout sessions
  by default (synthetic test thresholds only, not a scientific sample-size
  determination). Require the same exact cue and Action for the proposed
  rule, all observed training goal results for that Action successful,
  plus actual holdout evidence for that executed Action.
- Strongest cheap comparator: **the same exact cue, same training samples,
  success-rate majority** with ties abstaining. If its action agrees, build
  only an ephemeral `HabitRule` / `HabitRepertoire` and invoke the actual
  `relay_self.habit.select_habit` to verify source-cue selection. The
  shadow rule is NOT returned as a reusable production repertoire and is
  NEVER committed, persisted, authorized or issued.
- Holdout scoring happens *after* the training choice, never a lookahead.
  A mismatch yields `SHIFT_DETECTED`; an unexecuted candidate cannot
  obtain a counterfactual label. Matching cheap performance produces
  **CHEAP_NULL_EQUAL**, *not* a learning victory or S11 grant. Retained
  status reports always have `habit_grants=0`,
  `learning_updates=0`, `action_authority=false`.
- No automatic learned L0 reflex compilation, L1 policy deployment,
  resource allocator, S10 authority, L2 stop or S60 model work. A future
  S11 production rule would require an independently delegated
  authority/grant, distinct production tests, and actual World outcomes.
  This Draft cannot grant one under any synthetic or passed witness values.

## Negative controls and reduction

Synthetic fixtures: no goal labels; same Action physical movement but no
independently admitted goal SHA; S16 UNKNOWN; goal contradictions; an unseen
cue; training/holdout replay or session leakage; attempted label forged
from L2; same observed Action but unexecuted alternative in holdout;
distribution shift; mutated original L1 Memory; priority/cue selection;
cheap majority equality. If cheap exact-cue performance equals the shadow
S11 choice, prefer the cheaper solution. No new database/graph/habit owner.

Default offline-only shared RSEE worktree commands:

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
test -x "$BASE/venv/bin/python" || exit 1
"$BASE/venv/bin/python" -m pytest -q \
  tests/test_habit_shadow.py tests/test_forecast_bridge.py \
  tests/test_experience_bridge.py tests/test_habit_qualification.py
"$BASE/venv/bin/python" -m pytest -q
"$BASE/venv/bin/ruff" check src tests experiments adapters observability
"$BASE/venv/bin/python" tools/check_repository.py
```

No standalone pip/npm install or new venv, Java/Node World run, GPU, GGUF,
LLM POST, Action issue, arbitrary Minecraft target or historical Golden
replay. GitHub ephemeral CI is **not** the operator's WSL2 shared RSEE.
Real S/V goal-source attestation and scientific gain remain NOT_RUN.
Final ceiling if tests pass:
`L3_OFFLINE_SHADOW_HABIT_GATE_ONLY /
CHEAP_NULL_EQUAL / NO_S11_PROMOTION / NO_PRODUCTION_GO`.
