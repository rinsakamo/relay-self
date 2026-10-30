# L Lane L8 — existing S decision-epoch *returned* result → L1 shadow observer

**Scope:** child of L7 exact `a56547076624921f05743e16e6e3aacb11cc964c`. This is L-only, independent DEV branch; no writes to the S-owned `runtime_coordination.py`, `epoch_plan.py`, S42/S49, S10/S11, G4.x, #545/#634 or main. Historical qualification and R/V authority remain unchanged.

## Actual S seam inspected

The existing S `coordinate_decision_epoch` runs `ActionSupervisor.advance` **before** caller-supplied decision work and returns `DecisionEpochResult` with `cognition_requested`, `cognition_result`, `timed_out_actions`, `next_action_deadline_ns`. The separate `coordinate_planned_epoch` returns `PlannedDecisionEpochResult` wrapping the original decision and executed work IDs. L8 **consumes only these completed typed returns**; it does not call either coordinator, wrap S with a new scheduler, invoke a model, or issue an Action.

`observe_s_epoch_l1()` requires an actual returned `WorldConditionedChoice` from S's cognition seam, no timeout/UNKNOWN action closed in that epoch, no open action deadline, and nonempty work provenance when a planned result is supplied. It then delegates to the original L7 compare, which re-runs S42's deterministic choice validation from the existing NativeThreat and owner-local S10 preference snapshot. Its result is an audit-only `SEpochL1Observation` with the original S epoch object, source-bound difference, work IDs, and fixed zero Action/Habit/Learning-authority counts.

This validation does NOT authenticate an actual S49 native source or independently prove that an object was emitted by S rather than reconstructed; source admission and original bytes are separately S/R/V-owned. An L1 conflict cannot mutate S42 selection, grant Action permissions or be treated as physical outcome.

## Focused DEV offline controls

- Run **the existing S** `coordinate_decision_epoch` with its actual `select_world_conditioned_choice` as the caller's sole cognition runner, then read its returned result through L8 (rather than feeding a fabricated SChoice to L directly). Compare same S epoch with retention ON/OFF and prove no second S cognition call is made by L.
- Exercise **the existing S** `coordinate_planned_epoch` with its declared `ctl.bounded_cognition` binding; it runs its own single cognition invocation and L8 reads the completed `PlannedDecisionEpochResult` after the fact.
- Near S `MOVE_AWAY` against retained L1 `WAIT` and far S `WAIT` against retained L1 `MOVE_AWAY`: retain S choice. Different cognition result, forged S choice, wrong native/provenance, absent S original admission, foreign self, false authority and retention mismatch refuse comparison.
- S supervisor with pending Action deadline or already-timed-out Action cannot be used to treat L1 candidate as a clean successor epoch. Re-reading has no new Action/Memory effect.

The offline tests use **synthetic source-shaped World and Goal fixtures**, not independent real Minecraft receipts. This is an **actual existing S coordinator API invocation under test**, not the S49 product host loop, not source attestation, and not observed physical learning.

Python 3.12 FAST (no World, Java, Node, GPU or LLM):
```sh
PYTHONPATH=src:tests:. python -m pytest -q \
  tests/test_l1_epoch_observer.py tests/test_l1_s_choice_shadow.py \
  tests/test_learning_epoch.py tests/test_contextual_shadow.py \
  tests/test_experience_bridge.py tests/test_habit_shadow.py \
  tests/test_postmain_s42_world_contrast.py tests/test_epoch_plan.py \
  tests/test_runtime_coordination.py
ruff check src/relay_self/l1_epoch_observer.py tests/test_l1_epoch_observer.py
python tools/check_repository.py
```

**Next owner handoff:** S #537 may opt into a read-only hook after its *actual* S49 product epoch has a typed output and independently qualified source/goal attestations. Neither S49 itself nor a real World is changed here; FULL only at merge review. No auto L0 distillation.
