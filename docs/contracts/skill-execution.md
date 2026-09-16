# Skill Execution Contract

## Purpose

This document owns the first executable runtime lifecycle for one Skill execution instance.

It refines the ontology definition of Skill as a temporally extended feedback controller or embodied capability and the architectural flow `Current Intent -> Skill -> Action`. It does **not** define the persistent capability library, a closed-loop control policy, primitive Action generation, or general Skill scheduling.

The executable owner is `src/relay_self/skill.py`; deterministic verification lives in `tests/test_skill_execution.py`.

## Grand Null result

Skill Execution is not reducible to Current Intent.

Current Intent is the currently committed executable objective. A Skill execution is one runtime path used to pursue that objective. The Current Intent may remain unchanged while a particular Skill execution succeeds, fails, or is later replaced by another execution path.

Skill Execution is also not reducible to primitive Action Lifecycle.

Action Lifecycle owns one primitive effect command from proposal through authorization and issuance to terminal consequence closure. A Skill may remain active across zero, one, or many primitive Actions, so controller-level execution state cannot be represented by any one primitive Action lifecycle without collapsing the architectural boundary.

Therefore the independent distinction is:

```text
Current Intent commitment
  != Skill execution instance
  != primitive Action lifecycle
```

A separate executable owner is justified.

A full Skill controller is **not** justified in this first transaction. Current authority names initiation conditions, feedback policy, termination, yield points, interruptibility, duration/resource implications, success/failure evidence, side effects, and required authority as useful possible contract dimensions. Most of those need concrete environment/runtime semantics that do not yet exist.

The smallest current owner is therefore:

> identify one Skill execution instance associated with one intent and preserve its start-to-terminal success/failure lifecycle with monotonic time and causal provenance.

## Boundary

For one `SkillExecution`:

```text
STARTED
  -> SUCCEEDED

STARTED
  -> FAILED
```

`SUCCEEDED` and `FAILED` are terminal.

This first contract deliberately has no pause, resume, yield, interrupt, retry, or child-Action state.

## Execution identity and association

A Skill execution records immutable identity fields:

- `execution_id` — runtime identity of this particular execution instance;
- `skill_id` — identity/name of the Skill capability being executed;
- `intent_id` — identity of the Current Intent this execution is intended to serve.

These identifiers describe association only.

Starting a `SkillExecution` does **not** prove that:

- `skill_id` exists in a validated capability library;
- the referenced intent is currently committed;
- Skill initiation preconditions are satisfied;
- the Skill is authorized for execution;
- any primitive Action has been proposed, authorized, issued, or completed.

Those checks require future owners or explicit coupling contracts.

No global uniqueness or durable identity policy is defined here. `execution_id` is the identity of one execution object and causal trace.

## Start

`SkillExecution.start(...)` establishes one started execution with:

- non-empty `execution_id`;
- non-empty `skill_id`;
- non-empty `intent_id`;
- caller-supplied non-negative monotonic time;
- valid provenance identifying the source/reference for the start event.

The start event has no terminal reason.

`STARTED` means the runtime records that this Skill execution has begun. It does not mean a primitive Action has executed or that the environment has changed.

## Success and failure

A started execution may close exactly once as either `SUCCEEDED` or `FAILED`.

Both terminal transitions require:

- a non-empty reason;
- caller-supplied monotonic time;
- valid provenance for the terminal evidence/decision accepted by this boundary.

### `SUCCEEDED`

`SUCCEEDED` means the caller has closed this Skill execution as having satisfied its Skill-level termination condition.

This state is **not** primitive Action `OUTCOME`, and it is not external world truth by itself. A future closed-loop Skill controller or adapter must decide what evidence is acceptable for Skill success. This lifecycle only preserves the accepted terminal event and provenance.

Skill success also does not automatically complete the associated Current Intent. One successful Skill may be only one execution step under a larger committed objective.

### `FAILED`

`FAILED` means this Skill execution path has terminated unsuccessfully according to the caller-supplied reason/evidence.

Failure does not automatically fail or release the associated Current Intent. Current runtime authority lists Skill stall/failure as a possible reconsideration trigger, but whether a particular failure should request reconsideration remains an upstream policy decision.

The existing Current Intent Commitment `request_reconsideration(...)` seam can receive such a decision in a future coupling transaction. This contract does not call it automatically.

## Terminality

A terminal Skill execution cannot be reopened or transitioned again.

Consequences include:

- success cannot later become failure;
- failure cannot later become success;
- terminal events are append-only causal history rather than mutable result fields;
- a retry, alternate Skill, or replacement execution must be represented by another execution instance rather than rewriting the completed history.

This contract does not yet define who creates a replacement execution or how execution identities are allocated across a larger runtime.

## Time semantics

Skill events use caller-supplied non-negative integer monotonic time values.

Rules:

- successful events may share a timestamp or move forward;
- event time may not move backward inside one Skill execution;
- malformed or backward time fails closed;
- the lifecycle does not read wall-clock time and does not own a scheduler.

Equal timestamps permit a Skill to start and terminate in one runtime decision epoch without inventing sub-tick wall-clock ordering.

## Provenance

Skill events reuse the repository's current immutable `Provenance` value type.

This does not make Action Lifecycle the semantic owner of Skill Execution. It reuses one existing provenance representation rather than introducing a duplicate type solely for this boundary.

Provenance records where the start or terminal event came from. It does not by itself establish that the source was legitimate authority for Skill selection, initiation, or termination.

## Causal history

A Skill execution stores an immutable tuple of `SkillEvent` values.

Current state is derived from the final event rather than stored as a second mutable truth.

The minimum causal chain is therefore:

```text
execution_id + skill_id + intent_id
  -> STARTED provenance
  -> SUCCEEDED | FAILED provenance + reason
```

This is owner-local in-memory causal trace. It is not durable persistence, a repository-wide event store, or a restart-recovery contract.

## Relationship to Current Intent

This contract records `intent_id` as an association but does not hold or mutate an `IntentCommitment` owner.

Therefore:

```text
Skill SUCCEEDED
  != Current Intent COMPLETED

Skill FAILED
  != Current Intent FAILED
  != automatic reconsideration request
```

A future coupling contract may define how Skill outcomes influence Current Intent while preserving these distinctions.

## Relationship to primitive Action

This contract does not own primitive Action semantics.

It does not currently record child Action identities, generate Action proposals, authorize Actions, inspect Action outcomes, or infer Skill success/failure from Action closure.

The existing Action Lifecycle and Action Supervision owners remain the sole executable owners for their current primitive-Action responsibilities.

A future closed-loop Skill controller may consume observations and Action outcomes and emit new Action proposals, but that responsibility is not implemented by this lifecycle.

## Fail-closed behavior

Malformed data or illegal transitions fail with explicit Skill Execution errors.

Examples include:

- empty execution, skill, or intent identity;
- malformed provenance;
- negative or non-integer time;
- backward event time;
- empty terminal reason;
- a terminal-to-terminal or terminal-to-active transition;
- malformed recorded history.

The mechanism does not silently repair, reopen, retry, or reinterpret invalid execution history.

## Deterministic verification obligations

Canonical pytest coverage must demonstrate at least:

- start establishes immutable execution/skill/intent identity and `STARTED` state;
- success is an explicit terminal transition with reason and provenance;
- failure is an explicit terminal transition with reason and provenance;
- terminal execution cannot reopen or change terminal class;
- event time is monotonic;
- malformed identity/provenance/reason/time fails closed;
- event history is exposed as an immutable tuple;
- Skill failure does not automatically mutate or release a separately held Current Intent;
- Skill failure does not automatically create a Current Intent reconsideration request.

These tests are deterministic invariant evidence only. They do not prove useful Skill selection, valid preconditions, closed-loop control quality, environment correctness, successful primitive Actions, or physical execution.

## Non-goals

This contract intentionally does not define:

- a Skill capability library, persistent capability model, or Skill discovery;
- Skill selection, arbitration, ranking, or matching to Current Intent;
- initiation/precondition evaluation;
- closed-loop feedback/control policy;
- primitive Action generation, Action Lifecycle coupling, or Action Supervision coupling;
- automatic Skill-failure-to-reconsideration policy;
- yield points, pause/resume, interruption classes, cancellation, preemption, or retry policy;
- expected duration, resource-cost, side-effect, or performance models;
- Skill-specific authority policy;
- scheduler, wall clock, environment adapter, simulator, model, GPU, device, or physical integration;
- durable persistence or restart recovery;
- package distribution or supported Python/dependency floors;
- simulation, model-quality, device, or physical qualification.

Those responsibilities should acquire owners only when independent semantics and current implementation consequences justify them.
