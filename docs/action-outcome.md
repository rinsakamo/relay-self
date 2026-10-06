# S16 World consequence to Action outcome closure

## Purpose

S16 qualifies one explicit boundary only:

```
WorldConsequence
    -> pure consequence interpretation
    -> existing ActionSupervisor terminal transition
```

It is Action closure integration, not cognition and not learning.

The full deterministic qualified route is:

```
ATT -> BLF -> CNC -> {PRD -> PLAN, HABIT}
                     -> ROUTE
                     -> ControlCandidate
                     -> ADMISSION
                     -> ExecutionBinding
                     -> SkillExecution STARTED
                     -> ActionLifecycle PROPOSED
                     -> authorize
                     -> AUTHORIZED
                     -> ActionSupervisor.issue
                     -> ISSUED
                     -> exact S15 Mineflayer binding
                     -> WorldConsequence
                     -> interpret_world_consequence
                     -> record_interpreted_action_outcome
                     -> existing OUTCOME / UNKNOWN terminal state
```

S16 stops at Action terminal closure.

## Existing Action semantics

RelaySelf currently has no separate Action `SUCCEEDED` or `FAILED` state.

The existing terminal states relevant here are:

- `OUTCOME`: an acceptable external result is known; this does **not** mean success;
- `UNKNOWN`: the issued Action cannot be resolved to an acceptable observed result;
- `TIMEOUT`: the ActionSupervisor deadline closed first.

This matters for S15 status mapping. S16 must not invent a binary success/failure
model that the Action owner does not have.

## Pure interpretation versus owner transition

S16 keeps interpretation and mutation separate.

Target-specific pure interpretation remains next to the Mineflayer consequence:

```
adapters.mineflayer.action_outcome.interpret_world_consequence(...)
    -> ActionOutcomeInterpretation
```

The generic Action-owner bridge lives in RelaySelf core:

```
relay_self.action_outcome.record_interpreted_action_outcome(...)
    -> ActionSupervisor.record_outcome(...)
       or ActionSupervisor.mark_unknown(...)
```

The Mineflayer adapter cannot mutate ActionLifecycle directly.

## Exact lineage

The interpreter first reuses the exact S15:

```
build_mineflayer_command(issued_action, execution_binding_result)
```

guard. Therefore Action must still be current and ISSUED, and action_id,
skill_execution_id, intent_id, and the closed physical action_ref must match.

It then additionally requires:

```
WorldConsequence.action_id == issued Action.action_id
WorldConsequence.binding_id == ExecutionBindingResult.binding_id
WorldConsequence.action_ref == ExecutionBindingResult.action_ref
```

Every structured observation/effect receipt present in the consequence must
belong to its declared Mineflayer session.

The dispatch receipt, if present, must name the same Action and exact S15
Mineflayer effect. The cleanup receipt, if present, must name the exact bounded
cleanup action and `clear_controls`.

Identity is never inferred from semantic similarity or identifier spelling.

## S15 status mapping

### EXECUTED

S15 `EXECUTED` already requires applied dispatch, applied cleanup, structured
before/after observations, and at least 0.05 blocks of observed horizontal
movement.

S16 maps this to:

```
ActionOutcomeDisposition.OUTCOME
reason = observed_execution
```

The owner transition is the existing `ActionSupervisor.record_outcome(...)`.

Again, `OUTCOME` means known result; S16 does not create a new Action success
state.

### FAILED

S15 FAILED is intentionally broader than one semantic Action failure. It can
mean an explicit adapter rejection or an unresolved transport/cleanup/error
condition.

Therefore S16 distinguishes two cases.

An exact rejected dispatch receipt is already a known target-local result under
the existing Mineflayer runtime contract:

```
FAILED + dispatch effect_result(rejected)
    -> OUTCOME
    -> reason = known_adapter_rejection
```

Other FAILED consequences do not establish whether the physical Action
succeeded:

```
FAILED without exact rejected dispatch result
    -> UNKNOWN
    -> reason = adapter_failure_consequence_unknown
```

The owner transition uses existing `ActionSupervisor.mark_unknown(...)`.

This is not a new failure state.

### UNDETERMINED

```
UNDETERMINED
    -> UNAVAILABLE
    -> no Action owner transition
    -> Action remains ISSUED
```

The ActionSupervisor may later receive better evidence or close the Action by
its existing timeout semantics.

S16 never turns insufficient evidence into success, failure, or UNKNOWN merely
to force closure.

## Provenance

`ActionOutcomeInterpretation` retains both:

- the WorldConsequence provenance;
- the separate S16 interpretation provenance.

When an Action owner transition occurs, the terminal ActionEvent uses the
WorldConsequence provenance. S16 does not replace environment evidence with its
own interpretation provenance.

The immutable interpretation object remains the audit record for the mapping
choice.

## Timeout and replay semantics

S16 adds no race manager and no replay ledger.

Existing ActionSupervisor / ActionLifecycle semantics remain authoritative.

```
outcome first
    -> OUTCOME terminal
    -> later deadline processing does not TIMEOUT it

timeout first
    -> TIMEOUT terminal
    -> later record_outcome/mark_unknown fails closed

first outcome closure
    -> terminal snapshot
    -> duplicate closure fails closed
```

Invocation order remains explicit.

## Skill boundary

Action closure does not mutate SkillExecution.

```
Action OUTCOME / UNKNOWN / TIMEOUT
    != Skill SUCCEEDED / FAILED / CANCELLED
```

S16 adds no Skill terminal transition.

## LRN, Memory, and Belief boundary

S16 preserves:

```
Action OUTCOME != positive LearningFeedback
Action UNKNOWN != negative LearningFeedback
Action terminal state != Memory write
Action terminal state != Belief update
```

No learning proposal/commit, Habit reinforcement, Memory retention, BLF update,
or Current Intent replacement occurs.

## ACTION_OUTCOME metadata

EpochPlan scheduling needs one narrow integration-only metadata ID:

```
ACTION_OUTCOME
```

It depends on `WORLD_EXEC`.

It is not cognition, an Action owner, a scheduler, a consequence queue, or a
background monitor.

Operators:

```
action.interpret_world_consequence
    effect = READ_ONLY

action.record_interpreted_outcome
    effect = OWNER_TRANSITION
```

Criterion:

```
action.exact_outcome_lineage_guard
kind = CONTRACT_GUARD
```

## ON/OFF isolation

With WORLD_EXEC enabled and ACTION_OUTCOME disabled:

- WorldConsequence remains available;
- the Action remains ISSUED;
- interpretation/closure work is suppressed;
- no terminal outcome is fabricated.

Therefore:

```
world consequence availability != Action outcome closure availability
```

## Provider boundary

ProviderExpression cannot become:

- WorldConsequence;
- ActionOutcomeInterpretation;
- Action terminal event.

Natural-language claims such as "the action succeeded" or "the action failed"
carry no outcome authority.

## No background monitor

S16 does not poll Mineflayer, wait for consequences, retry closure, store a
pending-outcome queue, own deadlines, or create a persistent result manager.

The caller/runtime supplies explicit consequence work.

## Live field status

S15 live field remains:

```
NOT RUN / BLOCKED
blocker = genuine Minecraft endpoint unavailable
```

S16 deterministic qualification uses structured fake Mineflayer evidence only
and makes no physical field claim.

## Deferred functionality

S16 intentionally does not implement automatic LearningFeedback, LRN updates,
Habit reinforcement, Memory logging, BLF update, Skill outcome propagation,
multi-step play, outcome retry, background consequence polling, model-based
success interpretation, a central executive, or a persistent world controller.
