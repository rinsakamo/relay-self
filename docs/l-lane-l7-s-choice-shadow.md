# L7: Existing S42 World choice ↔ L1 next-epoch source-bound shadow contrast

Base: L6 exact `83fd338b1ed82d5b8bda809413021f8d608768e9`;
child branch `learning/l7-s-choice-shadow-20261030`.

## Why this is an interface rather than a new S controller

S49 `NormalWorldL0` inherits the S44 `ReactiveL0` route and uses the
existing S42 `select_world_conditioned_choice` from the original
`NativeThreat` and governed S10 `LearningPreferenceState`. S49
Action authorization and issuing are separate. Its `WAIT` vs `MOVE_AWAY`
selection is an established fixed S policy, not a learned L1 Habit.

L6 already retained L1 `QualifiedEpisode` with the existing
`PersistentCognition.Memory` owner and ran the existing L5 shadow against
independently admitted *claims* of Action and Goal source digests. L7 merely
binds that L1 result to the same exact S42 decision, recomputes S42's pure
choice from the S-owned native source and retained S10 snapshot and returns
a **read-only comparison**. It does not change S/G4 source, any native
observer, L0, Body/P1/M0, S16, S49, S10, S11 or the product S Draft.

To disallow accidental cross-epoch joins, L6's returned `LearningEpochResult`
now also carries the input `ShadowContext`, S-supplied no-memory candidate,
and S-supplied admitted-current-source digest set. The L7 comparison requires
the original session, native request ID, probe sequence, entity ID, and
source provenance to match S's World choice, requires current digest admission,
and rejects a different S-side recomputation. **No digest membership alone
independently authenticates native original bytes or World goals.**

## Offline control

Reuse S42's existing source-shaped Mineflayer near/far fixtures (via original
S42 `select_world_conditioned_choice`). Retention ON/OFF both get the
same immutable S-owned original choice.

- *Near*: S chooses `MOVE_AWAY`. Retention OFF has no L1 proposal. Retention
  ON, with 16 synthetic independent goal-labeled L1 episodes, L5 may suggest
  `WAIT`. **S keeps MOVE_AWAY**. This is a conflict visible to S, not
  a physically admissible override.
- *Far*: S chooses `WAIT`. Different synthetic cue conditions may make
  retained L1 suggest `MOVE_AWAY`; S still keeps `WAIT`.
- Cheap majority equality is explicitly reported, not mislabeled as
  a learned advantage. Contradiction returns no usable L1 suggestion.
- Foreign/stale and forged native/S-choice, wrong current admission,
  source-provenance drift, baseline disagreement and authority mutation
  reject before reporting an admissible comparison.

`action_issues=0`, `action_authority=false`, `habit_grants=0`,
`learning_updates=0`, `s_choice_kept=true` in every normal result.
The comparison cannot call the S49 issuer or grant a Habit.

## Limits / handoff

This branch is **OFFLINE_ONLY / DEV_ONLY**, with source-shaped synthetic
records and tests. It does NOT call the S49 continuous host loop, nor prove
real Minecraft retained behavior or goal benefit. Production handoff requires
S owner to supply authenticated native/source SHA, present and revision
scope, true S49 candidate and independently qualified goal result receipts,
with physical authorization remaining S's responsibility. S42 S10 retained
revision and L6 world_revision are different clocks; L7 compares them only
as separate typed fields and never equates them.

DEV FAST:
```sh
PYTHONPATH=src:tests:. python -m pytest -q \
  tests/test_l1_s_choice_shadow.py tests/test_learning_epoch.py \
  tests/test_contextual_shadow.py tests/test_experience_bridge.py \
  tests/test_habit_shadow.py tests/test_postmain_s42_world_contrast.py
ruff check src/relay_self/learning_epoch.py src/relay_self/l1_s_choice_shadow.py \
  tests/test_l1_s_choice_shadow.py tests/test_learning_epoch.py
python tools/check_repository.py
```

No FULL until merge review. No World/LLM/GPU/SCIENCE run. Main, G4, S Drafts,
other lane branches, frozen receipts and previous gates remain untouched.
