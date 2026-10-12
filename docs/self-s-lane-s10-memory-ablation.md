# RelaySelf S10 — Memory present/withheld shadow negative control

Authority: S product [Issue #537](https://github.com/rinsakamo/relay-self/issues/537).
Exact frozen producer S9 [Draft #609](https://github.com/rinsakamo/relay-self/pull/609)
HEAD `916814742567f8ff396b5c078d22f897d8418927`. S9 user permission
**CONSUMED**. No S9 physical replay or modification. S10 is **offline only**.

## Why

S9's original operator report [#6120089028](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6120089028)
contains 2 distinct controlled native Action/OUTCOMEs, 2 observational
Memories and a read-only recall of the first. It proves neither Memory
caused an Action nor advantage over a cheap policy. V1 #595 has independently
reviewed these *reported* claims only; R6 #610 has a separate R-owned S9
read-only original-byte audit, whose **actual WSL2 result is not included
in this S10 implementation**. V scientific G3 remains NO-GO.

## One bounded product experiment: freeze the no-effect baseline

Use *one identical* source-qualified event and independently correlated
probe for both arms. Each arm is a new `NormalWorldL0` with the same session,
intent, unmodified retained preference state and policy. The A-arm S3 owner
has a separately S-qualified already-observed S16/S49 Memory; B is an empty
S3 owner of exactly the same identity. Compare the original `hint_for_next`
and **read-only** S49 `NormalWorldL0._check` result.

- A: original retained observation gives a `RECALL` of a historical
  Action reference. This does **not** authorize or select an Action.
- B: S3 history withheld, no recalled Memory for the same probe.
- Both: current fixed L0 action *selection* must be identical; if not,
  the check fails closed instead of claiming causal efficacy.
- The existing L1 `retrieve_experience` tag/full scan is the **cheap
  baseline**; seeing a match to that lookup is no improvement.
- Neither arm invokes `decide`, external grants, L1 learned Habit, the
  Action executor, model, Minecraft, Java, Node or a real-world session.

This is deliberately a **negative control** with expected
`RECALL_DIFFERENCE_NO_L0_DECISION_EFFECT`. It establishes a clear
before-state for later *prospective* interventions, but cannot estimate
a treatment effect on physical Action or goal outcomes. Cross-session S8
vs S9 is NOT a randomized matched control. Outcome differences observed
between S8/S9 are not Memory effects.

Reject unmatched sessions, event/probe source identity or sequence,
partial/truncated native entity observations, unqualified/fake retention,
unequal retained L0 state, prior decision/Action, absent positive recall,
and foreign or stale memory. All fixtures use existing S3/S49 deterministic
source-shaped tests, never recovered S9 originals.

## Gates for a future, separate controlled test

Before any new live Memory intervention, **R must independently audit
S9 originals** using its R6 owner and V must define outcome/Goal success
and corresponding same-information cheap policy, allocation, randomization
(or prespecified matched comparison), independent original-session splits,
action authority and resource costs. L owner supplies a separately tested
learnable candidate policy; S alone governs whether its proposed change
can become an S49 Action. Require same source/current World observation,
an explicit `no Memory` ablation, admissible independent Goal labels,
no prior training leakage, and equal budgets.

Until then: `MEMORY_RECALL_OBSERVED / CAUSAL_BEHAVIOR_EFFECT_NOT_RUN /
S10_SHADOW_ONLY / S10_UPDATES=0 / S11_HABIT_GRANTS=0 / G3_NO_GO /
NO_PRODUCTION_GO`.

## Verification

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
python -m pytest -q tests/test_self_s10_memory_ablation.py \
  tests/test_self_s3_experience.py tests/test_self_s8_two_epoch.py
python -m pytest -q
python tools/check_repository.py
```

New `.github/workflows/self-s10-offline.yml` performs inherited
Python tests, repository contracts, Ruff, Mineflayer protocol and exact
S9 ancestor check on the source-shaped PR. No physical or scientific
qualification follows from green CI.
