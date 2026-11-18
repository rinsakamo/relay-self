# Stage27f — original physical Outcome → L1 evaluation candidates (DEV)

Parent #951; stacked on Stage27e [PR #964](https://github.com/rinsakamo/relay-self/pull/964) real HEAD
`ad09a82013f93a191b7642eaabf713b4baf6afdb`.

## Source-first observation

Stage27e has one **real** A MOVE parent Action `stage27c-A-52` in World
`f745617c-d7b6-4160-8531-1bd0875c9084`, the original PREPARED bytes,
terminal native WAL `NATIVE_PLACE_MOVE_SETTLED`, native displacement
0.6418188768690243 m and independently observed Paper displacement
0.6282611404785712 m. This is positional correlation, not Paper Action-ID
causality. The old real-World evidence is immutable.

The original Stage26 exploratory TargetContract is a world-fixed PLACE
anchor 1m east of the initial native observation, with an `ArrivalCondition`
of horizontal `[0, 0.6]` metres and vertical tolerance 1m. If the anchor
was unmodified and the starting positions are the bound source, the Stage27e
settled pose is inside the **geometric** envelope: its native residual to
that anchor is ~0.358181m. This is a derived calculation, not an
independent Goal/Skill success claim.

The existing `FiniteSkillInterpreter.observe_action()` returns only
`YIELD_EVALUATION`, and the original `TargetAssessment` explicitly
keeps `goal_succeeded=False`, even when `CONDITION_OBSERVED`.

## Stage27f implementation scope

`src/relay_self/p0d_stage27f_l1_evaluation_dev.py` implements a read-only
`prepare_stage27f_outcome_evaluation` on the **current original** A
`CheckpointedCognitiveOwner`. It accepts original Stage26 immutable
Invocation and TargetContract, original Intent/Skill/L0, original
`PhysicalIssueAdmission` and canonical original journal, plus real source
`Stage27PlaceMoveReceipt` and settled native probe.

It refuses stale/foreign Self/native session/World epoch, wrong
Action/Invocation/Preset/Target ref, nonterminal or mismatched original WAL,
no actual `ActionState.OUTCOME`, incomplete L0 yield, altered owner
Intent/Skill, unresolved physical reservation or conflicting active issue.
It derives `evaluate_target(original_contract, original_native_settled)`
and packages the **observation** plus WAL/Action lineage into a typed,
bounded `BoundedChoiceRequest`. This is a pending L1 review request,
**not an actual model call or terminal cognitive state update**.

Numbered candidates are:
- `1 CONTINUE_INTENT`: continue cognition/reobservation only
- `2 REVIEW_COMPLETION`: offered **only** for settled MOVE with
  `TargetConditionStatus.CONDITION_OBSERVED`; explicitly not a success
  commitment
- `3 ESCALATE_L2`
- `4 DEFER`

For overshoot, only `3` and `4` remain: no automatic retry, success
candidate, or resource-budget extension. Unresolved/malformed model
results fail or remain RECONSIDER. A pure offline
`resolve_stage27f_evaluation_choice` maps a bounded provider result to a
non-authoritative proposal; it does not attest real Gemma.

## Stop line and following stage

No original Intent/Skill is completed/failed, no next physical Action is
issued, no new registered Goal or Skill is learned, and no other Self is
modified by this CPU path. A future real one-slot L1 evaluation must go
through the original resident lane, retain raw HTTP evidence and recheck
fresh WorldBody/owner status **after** the model answer before adopting
a proposal. Even a real L1 `REVIEW_COMPLETION` decision must not silently
seal Skill/Intent; that needs an explicit original-owner evaluation lifecycle.

**Stage27f is OFFLINE DEV only until independently run on original host**.
No new real Paper/llama/Mineflayer trial was performed by this GitHub
development step. QUAL and SCIENCE remain NO-GO.

Testing: synthetic original physical issue and A/B owners, terminal
native WAL, no-progress / overshoot and permitted completion candidate,
negative stale/foreign/false authority and B invariance.

## Optional real-runner observation hook

The original `experiments/p0d_stage27_real_place_move_dev.py` has an
explicit `--stage27f-cpu-evaluation` mode. This includes the Stage27e
independent Paper and PREPARED raw evidence capture and generates the
original `Stage27EvaluationFrame` strictly after actual L0
`YIELD_EVALUATION` and terminal original A WAL. It serializes the
model-facing numbered-choice request into the real report. **It does not
submit that request to Gemma**, accept a L1 evaluation result, mutate the
existing Skill/Intent, issue another MOVE or change default Stage27d/e
settings. A non-READY A model selection still causes no physical Action.

Example: add `--stage27f-cpu-evaluation` to the original Stage27d
fully source-verified host invocation instead of the Stage27e flag;
do not start a fresh World without the one-shot trial evidence rules.
