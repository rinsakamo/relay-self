# L Lane: offline source-bound retention to next-epoch L1 candidate

Scope: independent L DEV child of existing unmerged L5 PR #613 (exact parent
`17c5357fd5625274ee567ad979b780e77bf7b1e7`). No changes to S/G4.x,
source, native Action owners, frozen proof, #545/#634/main, or S10/S11 modules.

Existing L1 `qualify_episode` / `retain_observation` already encode S16 OUTCOME and
existing owner-local `PersistentCognition.Memory`. L3 `_samples` already gates
externally independently admitted Action and Goal source digests, and L5
`review_contextual_shadow` already returns a bounded conditional suggestion
against same-information cheap controls. This change only adds the missing
**epoch transition**: a prior qualified episode and externally admitted goal
label may be retained using the old Memory owner, then L5 is run against a
*different later current source* to yield a nonauthorizing L1 candidate.

`advance_learning_epoch()` accepts new S16-qualified terminal episodes plus
matching external S/V goal labels. It rejects non-executed, UNKNOWN,
source-unadmitted, duplicated, current-session, same/newer-revision and
mislinked entries before treating them as training. The original current
source needs separate S admission. Old historical memories are accepted only
through the existing L3/L5 validator; prior source-shaped records, including
synthetic ones, are not by themselves authentic World/Goal evidence.

A failure raises without returning an updated immutable Memory snapshot;
other missing/mixed historical admission causes L5 to abstain or reject.
Current cognition/identity is checked against the caller's specified self.
Memory retention is not a S10 governed preference update, and repeated
candidate review does not create S11 Habit. Source provenance remains
attached to existing Memory records; no new DB or graph.

## Controlled contrast (synthetic offline only)

- Retention OFF: same present -> S-owned fixed candidate `OPTION_A`.
- Retention ON: 16 source-shaped past, goal-labeled episodes -> two-feature L5
  contextual candidate `OPTION_B` in the next epoch and in a subsequent epoch.
- Cheap global, singleton and exact-cue controls are compared on the same
  episodes, with source admission and no-memory candidate held fixed.
- If a cheap control is equally good, route the candidate as `cheap_memory_rule`;
  there is no claim that a complicated learned rule is better.
- Contradiction, foreign self/current session, replay, future/stale source,
  absent Action/Goal admission, missing current original and UNKNOWN fail
  closed or return the S-provided baseline without adopting learned behavior.

All results are **offline engineering only**, not independently verified
Minecraft learning, not source authenticity, not learned performance advantage.
`action_authority=false`, `habit_grants=0`, `learning_updates=0` and
`physical_goal_improvement_attested=false` always. Do not wire the resulting
candidate to S49 without S-owned authorization/review. The eventual S handoff
must bind self/session/world revision independently and supply truly attested
Goal receipts; cross-session comparability is not proved here.

Local Python 3.12 focused command (no real World/LLM/GPU):

```sh
PYTHONPATH=src:tests:. python -m pytest -q \
  tests/test_learning_epoch.py tests/test_contextual_shadow.py \
  tests/test_experience_bridge.py tests/test_habit_shadow.py
ruff check src/relay_self/learning_epoch.py tests/test_learning_epoch.py
python tools/check_repository.py
```

The new branch's FAST workflow only runs the scoped offline tests and
contracts; FULL is left to an eventual integration/merge review. No new
micro-Issue or S10/Habit promotion is created.
