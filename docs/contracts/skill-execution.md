# Skill Execution Contract

## Purpose

This document owns the executable runtime lifecycle for one Skill execution instance.

It refines the ontology definition of Skill as a temporally extended feedback controller or embodied capability and the architectural flow `Current Intent -> Skill -> Action`. It owns the Skill execution's immutable association to the Current Intent that was actually committed when the supported start seam ran. It does **not** define the persistent capability library, a closed-loop control policy, primitive Action generation, general Skill scheduling, or policy for what happens when the associated Current Intent changes later.

The executable owner is `src/relay_self/skill.py`; deterministic verification lives in `tests/test_skill_execution.py`.

## Grand Null result

Skill Execution is not reducible to Current Intent.

Current Intent is the currently committed executable objective. A Skill execution is one runtime path used to pursue that objective. The Current Intent may remain unchanged while a particular Skill execution succeeds, fails, or is later replaced by another execution path.

Skill Execution is also not reducible to primitive Action Lifecycle.

Action Lifecycle owns one primitive effect command from proposal through authorization and issuance to terminal consequence closure. A Skill may remain active across zero, one, or many primitive Actions, so controller-level execution state cannot be represented by any one primitive Action lifecycle without collapsing the architectural boundary.

Therefore the independent distinction remains:

```text
Current Intent commitment
  != Skill execution instance
  != primitive Action lifecycle
```

A separate Skill Execution owner is justified.

### Current Intent association strengthening

The first Skill Execution bootstrap accepted a caller-supplied `intent_id`. That preserved an association field but did not establish that the referenced intent was actually current. Once both Current Intent Commitment and Skill Execution existed as executable owners, leaving that validation entirely to a future orchestrator was no longer the smallest sufficient boundary: the supported Skill start seam itself could still create a contradictory started execution for an arbitrary, stale, or nonexistent intent.

A new Intent-Skill coupling owner is not justified for this relation. No independent state machine, persistence, scheduler, or policy remains after the start association is validated. The responsibility is lifecycle-local to Skill start because Skill Execution already owns the immutable `intent_id` association and `STARTED` event.

The smallest current rule is therefore:

> `SkillExecution.start(...)` reads an `IntentCommitment`, requires that it currently owns a Current Intent, and derives the new execution's `intent_id` from that owner rather than accepting the identity from the caller.

Current Intent Commitment remains the sole owner of whether an intent is current. Skill Execution reads that state but does not mutate it.

A pending reconsideration request does not by itself release the Current Intent. Therefore a Skill may still start for the same current intent while reconsideration is pending. Whether a runtime *should* choose to start another Skill in that situation is future orchestration/policy, not part of this lifecycle invariant.

This start-time validation also does not define what happens to an already-started Skill if its associated Current Intent is later completed, failed, invalidated, or released. That later coupling remains deferred.

A full Skill controller is still not justified here. Current authority names initiation conditions, feedback policy, termination, yield points, interruptibility, duration/resource implications, success/failure evidence, side effects, and required authority as useful possible contract dimensions. Most of those need concrete environment/runtime semantics that do not yet exist.

## Boundary

For one `SkillExecution`:

```text
STARTED
  -> SUCCEEDED

STARTED
  -> FAILED
```

`SUCCEEDED` and `FAILED` are terminal.

This contract deliberately has no pause, resume, yield, interrupt, retry, or child-Action state.

## Execution identity and association

A Skill execution records immutable identity fields:

- `execution_id` — runtime identity of this particular execution instance;
- `skill_id` — identity/name of the Skill capability being executed;
- `intent_id` — identity of the Current Intent that was current when the supported start seam established this execution.

`execution_id` and `skill_id` remain caller inputs. `intent_id` is not a caller-selected start input; it is derived from `IntentCommitment.current_intent`.

A successful supported start therefore establishes the deterministic relation:

```text
SkillExecution STARTED
  -> associated intent was Current Intent at Skill start
```

It does **not** establish:

```text
associated intent remains current for the whole Skill execution
```

Starting a `SkillExecution` also does **not** prove that:

- `skill_id` exists in a validated capability library;
- Skill initiation preconditions are satisfied;
- the Skill is authorized for execution;
- the Skill was a good or optimal execution choice for the Current Intent;
- any primitive Action has been proposed, authorized, issued, or completed.

Those checks require future owners or explicit coupling contracts.

No global uniqueness or durable identity policy is defined here. `execution_id` is the identity of one execution object and causal trace.

Direct construction of the immutable representation is not the supported runtime start operation. The executable start invariant is owned by `SkillExecution.start(...)`, analogous to the distinction between a value representation and the owner transition that establishes runtime state.

## Start

`SkillExecution.start(...)` establishes one started execution with:

- non-empty `execution_id`;
- non-empty `skill_id`;
- an `IntentCommitment` owner that currently has a Current Intent;
- caller-supplied non-negative monotonic time;
- valid provenance identifying the source/reference for the start event.

The start operation:

1. validates the Skill start event inputs;
2. validates that the supplied owner is an `IntentCommitment`;
3. reads `intent_commitment.current_intent`;
4. fails closed if there is no Current Intent;
5. derives `intent_id` from that Current Intent;
6. creates the new immutable Skill execution without mutating the Intent Commitment owner.

No caller-supplied `intent_id` is accepted by the supported start seam.

`STARTED` means the runtime records that this Skill execution has begun for the Current Intent observed at start. It does not mean a primitive Action has executed or that the environment has changed.

If reconsideration is pending but the intent remains current, start remains structurally valid under this contract. The existence of pending reconsideration is not equivalent to release.

If the intent has already been completed, failed, invalidated, or released, there is no Current Intent and start fails closed.

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

This transaction does not introduce a general cross-owner clock contract between Intent Commitment and Skill Execution. The association validation is based on the Current Intent state observed when `start(...)` runs. A future runtime/time owner may define stronger ordering across owner-local event traces when needed.

## Provenance

Skill events reuse the repository's current immutable `Provenance` value type.

This does not make Action Lifecycle the semantic owner of Skill Execution. It reuses one existing provenance representation rather than introducing a duplicate type solely for this boundary.

Provenance records where the start or terminal event came from. It does not by itself establish that the source was legitimate authority for Skill selection, initiation, or termination.

The Current Intent association is grounded structurally by reading `IntentCommitment.current_intent`; that does not turn the Skill start provenance into intent-selection authority.

## Causal history

A Skill execution stores an immutable tuple of `SkillEvent` values.

Current state is derived from the final event rather than stored as a second mutable truth.

The minimum causal chain is therefore:

```text
Current Intent owner state at start
  -> execution_id + skill_id + derived intent_id
  -> STARTED provenance
  -> SUCCEEDED | FAILED provenance + reason
```

This is owner-local in-memory causal trace. It is not durable persistence, a repository-wide event store, or a restart-recovery contract.

## Relationship to Current Intent

Current Intent Commitment owns whether an intent is currently committed. Skill Execution owns the execution instance and its immutable association.

The supported start seam requires a Current Intent and derives the association from that owner without mutating it.

Therefore:

```text
Skill STARTED
  -> associated intent was current at start

Skill SUCCEEDED
  != Current Intent COMPLETED

Skill FAILED
  != Current Intent FAILED
  != automatic reconsideration request

later Current Intent release
  != automatic Skill termination
```

The last relation is an explicit non-claim. This contract does not supervise the Current Intent after Skill start and does not automatically rewrite or terminate existing Skill history when the intent owner later changes.

## Relationship to primitive Action

This contract does not own primitive Action semantics.

It does not currently record child Action identities, generate Action proposals, authorize Actions, inspect Action outcomes, or infer Skill success/failure from Action closure.

The existing Action Lifecycle and Action Supervision owners remain the sole executable owners for their current primitive-Action responsibilities.

A future closed-loop Skill controller may consume observations and Action outcomes and emit new Action proposals, but that responsibility is not implemented by this lifecycle.

## Fail-closed behavior

Malformed data or illegal transitions fail with explicit Skill Execution errors.

Examples include:

- empty execution or skill identity;
- a malformed or absent `IntentCommitment` input;
- no Current Intent at Skill start;
- malformed provenance;
- negative or non-integer time;
- backward event time inside the Skill execution;
- empty terminal reason;
- a terminal-to-terminal or terminal-to-active transition;
- malformed recorded history.

The mechanism does not silently invent an intent association, repair, reopen, retry, or reinterpret invalid execution history.

Start validation never mutates the supplied Intent Commitment owner, whether validation succeeds or fails.

## Deterministic verification obligations

Canonical pytest coverage must demonstrate at least:

- start establishes immutable execution/skill identity and `STARTED` state;
- supported start accepts no caller-supplied `intent_id`;
- start derives `intent_id` from the actual Current Intent;
- start with no Current Intent fails closed;
- start after Current Intent release/terminal closure fails closed;
- a pending reconsideration request leaves the same intent current and does not by itself make Skill start invalid;
- successful and failed start validation do not mutate Intent Commitment history/state;
- success is an explicit terminal transition with reason and provenance;
- failure is an explicit terminal transition with reason and provenance;
- terminal execution cannot reopen or change terminal class;
- event time is monotonic inside the Skill execution;
- malformed local identity/commitment/provenance/reason/time fails closed;
- event history is exposed as an immutable tuple;
- Skill terminal state does not automatically mutate or release a separately held Current Intent;
- Skill failure does not automatically create a Current Intent reconsideration request.

These tests are deterministic invariant evidence only. They do not prove useful Skill selection, capability existence, valid preconditions, closed-loop control quality, continued intent validity during Skill execution, environment correctness, successful primitive Actions, or physical execution.

## Non-goals

This contract intentionally does not define:

- a Skill capability library, persistent capability model, or Skill discovery;
- Skill selection, arbitration, ranking, or matching policy beyond the start association invariant;
- initiation/precondition evaluation;
- closed-loop feedback/control policy;
- Skill-start authorization policy;
- automatic cancellation/termination when the associated Current Intent later changes;
- primitive Action generation, Action Lifecycle coupling, or Action Supervision coupling;
- automatic Skill-failure-to-reconsideration policy;
- yield points, pause/resume, interruption classes, cancellation, preemption, or retry policy;
- expected duration, resource-cost, side-effect, or performance models;
- Skill-specific authority policy;
- a cross-owner clock/scheduler contract;
- scheduler, wall clock, environment adapter, simulator, model, GPU, device, or physical integration;
- durable persistence or restart recovery;
- package distribution or supported Python/dependency floors;
- simulation, model-quality, device, or physical qualification.

Those responsibilities should acquire owners only when independent semantics and current implementation consequences justify them.
