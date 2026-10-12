# L Lane L5 — bounded contextual experience → differing read-only candidate

**Authority**: Learning #426, Product #537, Science #544.
Exact L4 #612 parent: `28b90ad2f2d204a808610a36a8b619f2c194be73`.
This child changes **L-owned files only**. S10 #611, S9 #609, R6 #610,
V1 #595, other parent L1–L4, frozen World/RSEE/original receipts and
main stay unchanged and unmerged.

## Motivation: the S10 negative control is correct

S10 #611 showed that S3 historical Memory `RECALL` currently does
not change the original `NormalWorldL0` selection: the read-only hint
is logged but **not consumed by the L0 policy**. An operator-reported
S9 two-Action/two-Memory experiment does not imply adaptive cognition,
and R6's host original byte readback only audits bounded raw/Memory
continuity; it does not attest source-native goals, R1/R2, or causation.

This L5 increment creates the first **non-authorizing memory-dependent
Action *candidate suggestion*** for explicit future S-owned review.
It does not call L0, S10, S11, S49 authorization, physical World,
S9 consumed grant, model, GPU or Minecraft.

## Scope of the shadow learning calculation

`src/relay_self/contextual_shadow.py` reuses L3's original L1
`_samples` validator (private but unchanged; no duplicated evidence
authority) for S16 executed observations and **externally supplied**
goal receipt labels admitted by S/R/V.

A caller predeclares **exactly two binary cue tags** and **exactly two
S-provided Action reference IDs**, not arbitrary executable commands.
For each of four tag-presence configurations, the L5 learner needs
at least two independent successful/failure-labeled original observed
sessions **for each candidate Action**. Equal goal-success rates or
incomplete cells force abstention. Source session, original action hash,
goal hash, Memory ID, current observation ID, and candidate vocabulary
must not be reused or drift. A SHA string or a Python goal-label
instance does **not** authenticate its original bytes; S/R/V provide
that independent verification later.

At current observation (a *source pointer*, not L-authenticated native
bytes), a single bounded historical two-feature lookup returns a
**shadow Action reference only**. Its output includes
`action_authority=false`, `habit_grants=0`,
`learning_updates=0`, `goal_improvement_attested=false`,
`memory_causal_benefit_established=false`. Never serialize or
install its inferred table as an S11 Habit or an L0 policy.

## Three cheap comparisons on identical information

1. The actual S-owned **no-memory L0 reference** for the same current
   event, supplied by the separate S owner; L5 cannot call `decide`
   and must not invent what L0 chose.
2. **Exact-cue goal-rate majority** from exactly the same L1 + external
   goal-labeled source set; abstain if no exact matched examples.
3. **Each current singleton cue's goal-rate majority**, and **global
   goal-rate majority** over exactly the same admitted examples. These
   are deliberately stronger than comparing only against *no Memory*.

If simple lookup already proposes the same choice, output
`CHEAP_EQUIVALENT`; if no-memory reference agrees, output
`NO_MEMORY_EQUAL`; if all simple cheap controls abstain or differ,
output `SHADOW_DIFFERENCE` **only**. A two-feature cheap lookup is by
construction capable of reproducing L5's learned mapping, so
`SHADOW_DIFFERENCE` is never a claim of model superiority or net
utility. It only proves that this particular bounded historical
cross-cue computation can produce a *different proposal*.

The included **source-shaped synthetic XOR** (two tag features, four
contexts, two candidate Actions, at least two independent original
episodes per Action/cell) forces cheap exact/singleton/global majority
to abstain on a new nuisance cue, while two-feature L5 proposes a
different Action than the externally supplied no-memory control.
The test intentionally uses abstract `OPTION_A/OPTION_B`, not an
unsafe real Minecraft Action. Positive synthetic results are
engineering only; they do NOT attest the user-host S9 World.

## Path to a real test (owned by S/R/V)

- **S** owns original current native source (same probe for both arms),
  safe candidate vocabulary and L0's independently observed original
  choice. A shadow proposal must be visibly distinct but **must not**
  override reflexes. Never allow a learned `WAIT` to suppress L0
  immediate hazard protection.
- **R** qualifies original native bytes/HEAD/session/replay and existing
  R1/R2 handoff; the host R6 S9 audit reported checksum continuity
  but did not attest goals or Memory causality.
- **V** predeclares task-goal measurements, safe matched heldout World
  resets, equal resource budgets and strongest cheap two-feature
  comparator. In particular the two-feature lookup can be implemented
  as a cheap table, making an L5 model advantage impossible to claim
  without measured savings. V controls all empirical causal/science GO.
- **L4** provides the later paired retained-vs-cheap trial outcome
  review. L5 itself never issues World Actions or certifies training.

No repeated new "L6" stage is justified merely because a synthetic
candidate changed; the next material milestone is an S-owner safe,
predeclared heldout decision-path trial **after** R/V source and goal
gates have actually been satisfied.

## Offline-only verification on existing shared RSEE

From a clean L5 worktree on the WSL2 host, no package installation:

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
test -x "$BASE/venv/bin/python" || exit 1
"$BASE/venv/bin/python" -m pytest -q \
  tests/test_contextual_shadow.py tests/test_learning_contrast.py \
  tests/test_habit_shadow.py tests/test_forecast_bridge.py \
  tests/test_experience_bridge.py tests/test_self_s10_memory_ablation.py
"$BASE/venv/bin/python" -m pytest -q
"$BASE/venv/bin/ruff" check src tests experiments adapters observability
"$BASE/venv/bin/python" tools/check_repository.py
```

**Important:** `tests/test_self_s10_memory_ablation.py` exists only
on the independent S10 #611 branch, not on the L5 ancestry.
Run S10 original tests in a **separate exact-SHA S10 checkout**;
do not merge S10 into L5 or expect its test filename locally.
L5 CI checks its own L1–L5 + S11 inherited tests only.
GitHub CI is ephemeral—not the operator's actual shared RSEE.

No prior S8/S9 permission may be reused; no new permission inferred
from an instruction to progress with offline work.

Terminal ceiling even after green CI:
`L5_OFFLINE_CONTEXTUAL_SHADOW_DIFFERENCE_ONLY /
S10_L0_NEGATIVE_CONTROL_PRESERVED /
CHEAP_TWO_FEATURE_EQUIVALENT_BY_CONSTRUCTION /
GOAL_AND_SCIENCE_NO_GO / NO_S11_OR_ACTION_GRANT`.
