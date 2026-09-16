# Skill Execution Contract

## Purpose

This document owns the executable runtime lifecycle for one Skill execution instance.

It refines the ontology definition of Skill as a temporally extended feedback controller or embodied capability and the architectural flow `Current Intent -> Skill -> Action`. It owns the Skill execution's immutable association to the Current Intent that was actually committed when the supported start seam ran, and it distinguishes Skill success, Skill failure, and explicit lifecycle cancellation. It does **not** define the persistent capability library, a closed-loop control policy, primitive Action generation, general Skill scheduling, or automatic policy for what happens when the associated Current Intent changes later.

The executable owner is `src/relay_self/skill.py`; deterministic verification lives in `tests/test_skill_execution.py`.

## Grand Null result

Skill Execution is not reducible to Current Intent.

Current Intent is the currently committed executable objective. A Skill execution is one runtime path used to pursue that objective. The Current Intent may remain unchanged while a particular Skill execution succeeds, fails, is explicitly cancelled, or is later replaced by another execution path.

Skill Execution is also not reducible to primitive Action Lifecycle.

Action Lifecycle owns one primitive effect command from grounded proposal admission through authorization and issuance to terminal consequence closure. A Skill may remain active across zero, one, or many primitive Actions, so controller-level execution state cannot be represented by any one primitive Action lifecycle without collapsing the architectural boundary.

Therefore the independent distinction remains:

```text
Current Intent commitment
  != Skill execution instance
  != primitive Action lifecycle
```

A separate Skill Execution owner is justified.

### Current Intent association strengthening

The first Skill Execution bootstrap accepted a caller-supplied `intent_id`. That preserved an association field but did not establish that the referenced intent was actually current. Once both Current Intent Commitment and Skill Execution existed as executable owners, leaving that validation entirely to a future orchestrator was no longer the smallest sufficient boundary: the supported Skill start seam itself could still create a contradictory started execution for an arbitrary, stale, or nonexistent intent.

A new Intent-Skill coupling owner was not justified for this relation. No independent state machine, persistence, scheduler, or policy remained after the start association was validated. The responsibility is lifecycle-local to Skill start because Skill Execution already owns the immutable `intent_id` association and `STARTED` event.

The start rule is therefore:

> `SkillExecution.start(...)` reads an `IntentCommitment`, requires that it currently owns a Current Intent, and derives the new execution's `intent_id` from that owner rather than accepting the identity from the caller.

Current Intent Commitment remains the sole owner of whether an intent is current. Skill Execution reads that state but does not mutate it.

A pending reconsideration request does not by itself release the Current Intent. Therefore a Skill may still start for the same current intent while reconsideration is pending. Whether a runtime *should* choose to start another Skill in that situation is future orchestration/policy, not part of this lifecycle invariant.

### Cancellation classification strengthening

After start association was grounded, one smaller lifecycle gap remained.

The initial lifecycle exposed only:

```text
STARTED -> SUCCEEDED | FAILED
```

That is insufficient when an execution is stopped for an upstream or external reason. Reusing `FAILED` would claim that the Skill execution path itself failed. Leaving the execution `STARTED` would lose explicit causal closure.

The independent information is the terminal class:

```text
Skill FAILED
  != Skill CANCELLED
```

`FAILED` means the execution path terminated unsuccessfully according to accepted Skill-level reason/evidence.

`CANCELLED` means the caller explicitly closed this execution lifecycle because it should no longer continue for an upstream or external reason, without asserting Skill success or Skill failure.

This distinction stays inside the existing Skill Execution owner because that owner already owns terminal classification for one execution instance. No new supervisor or Intent-Skill coupling owner is required.

Automatic Current-Intent-to-Skill cancellation is **not** justified by this distinction. Current authority does not yet define interruptibility classes, yield points, closed-loop controller supervision, child Actions, or a cross-owner time contract. A later Current Intent release therefore remains separate from the explicit Skill cancellation operation.

A generic `INTERRUPTED` state is also not introduced. Interruption may imply resumability, yield semantics, or controller-level behavior that the current runtime does not implement. `CANCELLED` is terminal for this execution identity.

A full Skill controller is still not justified here. Current authority names initiation conditions, feedback policy, termination, yield points, interruptibility, duration/resource implications, success/failure evidence, side effects, and required authority as useful possible contract dimensions. Most of those need concrete environment/runtime semantics that do not yet exist.

## Boundary

For one `SkillExecution`:

```text
STARTED
  -> SUCCEEDED

STARTED
  -> FAILED

STARTED
  -> CANCELLED
```

`SUCCEEDED`, `FAILED`, and `CANCELLED` are terminal.

This contract deliberately has no pause, resume, yield, resumable interruption, preemption, retry, child-Action collection, or Action-derived terminal state.

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

Those checks require other owners or explicit coupling contracts.

No global uniqueness, durable identity policy, or repository-wide current/latest Skill-execution registry is defined here. `execution_id` is the identity of one immutable execution value/history. A caller may therefore hold older immutable values; this contract does not provide a supervisor that proves which value is globally latest.

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

## Terminal transitions

A started execution may close exactly once as `SUCCEEDED`, `FAILED`, or `CANCELLED`.

All terminal transitions require:

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

### `CANCELLED`

`CANCELLED` means the caller has explicitly closed this execution lifecycle because it should no longer continue for an upstream or external reason, without classifying the Skill path as successful or failed.

Cancellation is terminal for this `execution_id` value/history. A later retry or restart is another execution instance rather than reopening the cancelled history.

Cancellation does **not** by itself prove that:

- the associated Current Intent was completed, failed, invalidated, or released;
- an external controller or physical process has already stopped;
- any issued or in-flight primitive Action was cancelled;
- cancellation was safe under an interruptibility or yield policy;
- another Skill or Current Intent should be selected;
- the associated Current Intent should be failed, released, or reconsidered.

Those are separate responsibilities.

## Terminality

A terminal Skill execution value cannot be reopened or transitioned again.

Consequences include:

- success cannot later become failure or cancellation;
- failure cannot later become success or cancellation;
- cancellation cannot later become success or failure;
- terminal events are append-only causal history rather than mutable result fields;
- a retry, alternate Skill, or replacement execution must be represented by another execution instance rather than rewriting the completed history.

This contract does not yet define who retains the globally latest value for an execution identity, who creates a replacement execution, or how execution identities are allocated across a larger runtime.

## Time semantics

Skill events use caller-supplied non-negative integer monotonic time values.

Rules:

- successful events may share a timestamp or move forward;
- event time may not move backward inside one Skill execution value/history;
- malformed or backward time fails closed;
- the lifecycle does not read wall-clock time and does not own a scheduler.

Equal timestamps permit a Skill to start and terminate in one runtime decision epoch without inventing sub-tick wall-clock ordering.

This contract does not introduce a general cross-owner clock contract between Intent Commitment, Skill Execution, and Action Lifecycle. Start association and later explicit cancellation use their respective owner/value state as supplied at the operation boundary. A future runtime/time owner may define stronger ordering across owner-local event traces when needed.

## Provenance

Skill events reuse the repository's current immutable `Provenance` value type.

This does not make Action Lifecycle the semantic owner of Skill Execution. It reuses one existing provenance representation rather than introducing a duplicate type solely for this boundary.

Provenance records where the start or terminal event came from. It does not by itself establish that the source was legitimate authority for Skill selection, initiation, success, failure, or cancellation.

The Current Intent association is grounded structurally by reading `IntentCommitment.current_intent`; that does not turn the Skill start provenance into intent-selection authority.

## Causal history

A Skill execution stores an immutable tuple of `SkillEvent` values.

Current state for that value is derived from the final event rather than stored as a second mutable truth.

The minimum causal chain is therefore:

```text
Current Intent owner state at start
  -> execution_id + skill_id + derived intent_id
  -> STARTED provenance
  -> SUCCEEDED | FAILED | CANCELLED provenance + reason
```

This is owner-local in-memory causal trace for the supplied execution value. It is not durable persistence, a repository-wide event store, a latest-execution registry, or a restart-recovery contract.

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

Skill CANCELLED
  != Current Intent FAILED
  != Current Intent RELEASED
  != automatic reconsideration request

later Current Intent release
  != automatic Skill cancellation
```

The final relation is intentional. This contract does not supervise the Current Intent after Skill start and does not automatically rewrite or terminate existing Skill history when the intent owner later changes.

A future runtime/orchestrator may explicitly call `cancel(...)` after an upstream policy decides the execution should end. The existence of this seam does not define that policy.

## Relationship to primitive Action

Primitive Action semantics remain owned by [`action-lifecycle.md`](action-lifecycle.md), not by this contract.

The supported `ActionLifecycle.propose(...)` seam may consume a supplied `SkillExecution` value plus the `IntentCommitment` owner to establish one Action's causal association. That proposal seam requires the supplied Skill value to be `STARTED`, requires an actual Current Intent, requires the Skill's `intent_id` to match that Current Intent, and derives the Action's immutable `skill_execution_id` / `intent_id` association without mutating this Skill value.

This creates a narrow causal seam:

```text
supplied SkillExecution STARTED
  + matching actual Current Intent
  -> ActionLifecycle PROPOSED
```

It does **not** move primitive Action ownership into Skill Execution. This contract still does not:

- generate Action payloads or decide when an Action should be proposed;
- retain child Action identities or a child-Action collection;
- authorize or issue Actions;
- inspect Action outcomes;
- cancel issued/in-flight Actions;
- infer Skill success/failure/cancellation from Action closure;
- prove that the supplied immutable Skill value was the repository-wide latest value for its `execution_id`.

If the associated Current Intent later closes, this Skill value is not automatically cancelled. However, the Action proposal seam can reject a new proposal when this Skill's associated Intent no longer matches the actual Current Intent.

A future closed-loop Skill controller may consume observations and Action outcomes and emit new Action proposals, but that control responsibility is not implemented by this lifecycle.

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

Start validation never mutates the supplied Intent Commitment owner, whether validation succeeds or fails. Skill terminal transitions, including cancellation, also do not mutate a separately held Intent Commitment owner.

## Deterministic verification obligations

Canonical pytest coverage for this owner must demonstrate at least:

- start establishes immutable execution/skill identity and `STARTED` state;
- supported start accepts no caller-supplied `intent_id`;
- start derives `intent_id` from the actual Current Intent;
- start with no Current Intent fails closed;
- start after Current Intent release/terminal closure fails closed;
- a pending reconsideration request leaves the same intent current and does not by itself make Skill start invalid;
- successful and failed start validation do not mutate Intent Commitment history/state;
- success is an explicit terminal transition with reason and provenance;
- failure is an explicit terminal transition with reason and provenance;
- cancellation is an explicit terminal transition with reason and provenance and is distinct from failure;
- cancelled execution cannot reopen or change terminal class;
- event time is monotonic inside the Skill execution, including cancellation;
- malformed local identity/commitment/provenance/reason/time fails closed;
- event history is exposed as an immutable tuple;
- Skill terminal state does not automatically mutate or release a separately held Current Intent;
- later Current Intent completion/failure/invalidation/release does not automatically mutate an already-started Skill value;
- an explicitly cancelled Skill can close after such an upstream change without reclassifying the Skill as failed;
- Skill failure does not automatically create a Current Intent reconsideration request.

Skill-to-Action proposal-admission invariants are verified by the Action Lifecycle tests because Action Lifecycle owns that admission seam. Those tests do not turn Skill Execution into a child-Action owner.

These tests are deterministic invariant evidence only. They do not prove useful Skill selection, capability existence, valid preconditions, closed-loop control quality, globally latest Skill-execution retention, safe interruption, physical/controller cancellation, child-Action cancellation, environment correctness, successful primitive Actions, or physical execution.

## Non-goals

This contract intentionally does not define:

- a Skill capability library, persistent capability model, or Skill discovery;
- Skill selection, arbitration, ranking, or matching policy beyond the start association invariant;
- initiation/precondition evaluation;
- closed-loop feedback/control policy or primitive Action generation;
- repository-wide latest/current Skill-execution retention or supervision;
- child-Action retention/collection, Action Supervision coupling, or child-Action cancellation;
- Action-outcome-to-Skill terminal inference;
- Skill-start authorization policy;
- automatic cancellation/termination when the associated Current Intent later changes;
- automatic Skill-failure-to-reconsideration policy;
- interruptibility classes, yield points, pause/resume, resumable interruption, preemption, or retry policy;
- expected duration, resource-cost, side-effect, or performance models;
- Skill-specific authority policy;
- a cross-owner clock/scheduler contract;
- scheduler, wall clock, environment adapter, simulator, model, GPU, device, or physical integration;
- durable persistence or restart recovery;
- package distribution or supported Python/dependency floors;
- simulation, model-quality, device, or physical qualification.

Those responsibilities should acquire owners only when independent semantics and current implementation consequences justify them.
