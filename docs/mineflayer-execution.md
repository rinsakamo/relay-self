# S15 Issued-Action Mineflayer Execution Boundary

## Purpose

S15 qualifies the first bounded environment-execution bridge after the
existing RelaySelf cognitive, admission, Skill, Action proposal, authorization,
and supervised issuance boundaries.

The qualified chain is:

```
ATT -> BLF -> CNC -> {PRD -> PLAN, HABIT}
                     -> ROUTE
                     -> ControlCandidate
                     -> ADMISSION
                     -> ExecutionBinding
                     -> SkillExecution STARTED
                     -> ActionLifecycle PROPOSED
                     -> existing authorize(...)
                     -> AUTHORIZED
                     -> ActionSupervisor.issue(...)
                     -> ISSUED
                     -> exact ExecutionBindingResult join
                     -> MineflayerCommand
                     -> bounded Mineflayer I/O
                     -> WorldConsequence
```

S15 stops at `WorldConsequence`.

No consequence is automatically converted into BeliefEvidence,
LearningFeedback, Memory, Skill success/failure, Intent replacement, or another
Action.

## S15 is environment integration, not cognition

S15 performs no candidate selection, planning, arbitration, admission,
authorization policy selection, or language interpretation.

The S15 guard is:

```
world.issued_action_binding_guard
kind = CONTRACT_GUARD
```

There is no new cognitive orientation.

## Existing Action authority is reused

Authorization uses the existing:

```
ActionLifecycle.authorize(...)
```

Issuance with the stronger retained runtime guarantee uses the existing:

```
ActionSupervisor.issue(...)
```

S15 does not add an authorization token, issue boolean, second Action
lifecycle, or second deadline owner.

The Mineflayer adapter is strictly downstream of these transitions.

## Exact Action / binding join

Physical meaning remains outside ActionLifecycle.

S14 carries:

```
ExecutionBindingResult.action_ref = MOVE_BACKWARD
```

while ActionLifecycle carries:

- action_id;
- skill_execution_id;
- intent_id;
- lifecycle events/state.

`build_mineflayer_command(...)` requires:

```
ActionLifecycle.state == ISSUED
ActionLifecycle is current
ActionLifecycle.action_id == ExecutionBindingResult.action_id
ActionLifecycle.skill_execution_id == ExecutionBindingResult.skill_execution_id
ActionLifecycle.intent_id == ExecutionBindingResult.intent_id
ExecutionBindingResult.action_ref == MOVE_BACKWARD
```

Neither input alone is executable.

No meaning is inferred from `action_id`.
No naming convention, dynamic attribute access, eval, or arbitrary command
dispatch exists.

## Closed command mapping

S15 supports exactly one physical action:

```
MOVE_BACKWARD
    -> Mineflayer set_control(control="back", state=true)
    -> fixed 0.20 second bounded interval
    -> clear_controls
```

The command is represented by immutable `MineflayerCommand` metadata.

Movement cleanup has a distinct adapter-local action identity derived only to
clear the temporary control state. It is not a second cognitive/action-policy
decision.

No attack, inventory, crafting, chat, arbitrary JavaScript, or free-form
Mineflayer method dispatch is added.

## PROPOSED / AUTHORIZED / ISSUED

S15 preserves:

```
PROPOSED != executable
AUTHORIZED != executable
ISSUED alone != executable
ExecutionBindingResult alone != executable

ISSUED + exact ExecutionBindingResult
    -> eligible MineflayerCommand
```

Wrong action_id, Skill execution identity, Intent identity, missing binding
result, stale/non-current Action snapshot, unsupported action_ref, or malformed
command data fail before adapter I/O.

## Physical execution bound

`execute_mineflayer_command(...)` uses the existing Mineflayer session
interface.

The normal bounded transaction is:

1. request one structured pre-action probe observation;
2. send `set_control(back=true)`;
3. require the exact `effect_result` for the issued action;
4. wait the fixed 0.20 second control interval;
5. send `clear_controls` exactly once;
6. require its structured effect receipt;
7. request one structured post-action probe observation;
8. compare horizontal position.

There is no background movement loop, reconnect loop, retry, or autonomous
recovery.

If an applied movement may have left control state active and later processing
fails, S15 makes one best-effort `clear_controls` safety attempt. That attempt
is cleanup, not retry of the action.

## WorldConsequence

`WorldConsequence` is immutable structured environment evidence containing:

- action_id;
- binding_id;
- action_ref;
- EXECUTED / FAILED / UNDETERMINED status;
- Mineflayer session identity;
- structured before observation;
- exact dispatch receipt;
- exact cleanup receipt;
- structured after observation;
- observed horizontal movement distance;
- cleanup-attempted flag;
- explicit error when failed;
- provenance.

`EXECUTED` requires:

- applied dispatch receipt;
- applied cleanup receipt;
- before and after structured observations;
- horizontal position delta >= 0.05 blocks.

A command merely being written or acknowledged is not enough.

If both receipts and observations exist but movement is below the qualified
threshold, the consequence is `UNDETERMINED`, not fabricated success.

Adapter disconnect, command error, rejected effect, timeout, or I/O error
returns explicit `FAILED` consequence and never invents an after-state.

## ActionLifecycle consequence boundary

S15 deliberately does not close the ActionLifecycle.

The existing Mineflayer runtime-admission seam already supports explicit:

```
MineflayerEffectResult
    -> ActionSupervisor.record_outcome(...)
    -> OUTCOME
```

when a caller chooses to feed the receipt through that boundary.

S15 does not make the environment adapter own terminal Action state and does
not automatically invoke that closure. The S15 result therefore remains:

```
ISSUED Action
+ WorldConsequence
```

until a later explicit existing-owner call processes consequence evidence.

## WORLD_EXEC metadata

EpochPlan requires explicit capability identity for schedulable work. S15 adds:

```
WORLD_EXEC
```

as integration-only metadata.

It is not a cognitive capability, Action authority, scheduler, deadline owner,
or persistent world controller.

It depends on `EXEC_BIND`.

Operators:

```
world.build_mineflayer_command
    effect = READ_ONLY

world.execute_mineflayer_command
    effect = COORDINATION
```

The physical side effect is therefore not mislabeled READ_ONLY.

## ON/OFF isolation

With EXEC_BIND enabled and WORLD_EXEC disabled:

- Skill may be STARTED;
- Action may be explicitly AUTHORIZED and ISSUED through existing owners;
- Mineflayer command work is suppressed;
- no WorldConsequence is fabricated.

Thus:

```
issued authority != environment execution availability
```

## Provider boundary

ProviderExpression cannot become:

- ExecutionBindingResult;
- MineflayerCommand;
- authorization authority;
- WorldConsequence.

There is no natural-language action translation or model-based permission.

## LRN / MEM / BLF boundary

S15 preserves:

```
EXECUTED != positive LearningFeedback
FAILED != negative LearningFeedback

WorldConsequence != BeliefEvidence
WorldConsequence != Memory write
```

No risk weight, Habit rule, belief, or durable Memory changes automatically.

## ActionSupervisor

ActionSupervisor remains the owner of supervised issued-action retention,
outcome/unknown closure, and deadline processing.

S15 owns no timers or deadlines.

Epoch qualification preserves the existing rule that ActionSupervisor deadline
work runs before caller-owned S15 work.

## Live-field evidence

A live-field pass requires a genuine Mineflayer/Minecraft runtime receipt and
structured position observations from one fresh bounded action.

Deterministic adapter tests alone never justify a live physical-execution claim.
If the local Minecraft endpoint/runtime is unavailable, S15 must report the
live field as BLOCKED / NOT RUN rather than fabricating a result.

## No central executive

S15 introduces no persistent owner of cognition, route selection, admission,
Intent, Skill, Action authority, supervision, Memory, belief, learning,
scheduler timing, or World policy.

The existing adapter owns only target-local Mineflayer interaction semantics.

## Deferred functionality

S15 intentionally does not implement:

- autonomous multi-step play;
- background action loops;
- arbitrary Mineflayer commands;
- model-selected physical actions;
- natural-language action interpretation;
- automatic retries/reconnect;
- automatic LRN or Habit reinforcement;
- automatic Memory retention;
- automatic BLF update;
- learned action mapping;
- central executive;
- persistent world controller;
- Minecraft-specific high-level policy.
