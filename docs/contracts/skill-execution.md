# Skill Execution Contract

## Purpose

This document owns the executable runtime lifecycle for one Skill execution instance.

It refines the ontology definition of Skill as a temporally extended feedback controller or embodied capability and the architectural flow `Current Intent -> Skill -> Action`. It owns the Skill execution's immutable association to the Current Intent that was actually committed when the supported start seam ran, distinguishes Skill success, failure, and explicit cancellation, and now owns same-root snapshot-lineage currentness for that execution.

It does **not** define the persistent capability library, transient Skill-candidate projection, Skill selection, general parameter requirements or binding policy, a closed-loop control policy, primitive Action generation, general Skill scheduling, or automatic policy for what happens when the associated Current Intent changes later.

The reusable Skill definition/capability exists conceptually upstream of this owner. Candidate admission, selection, and general parameter binding are likewise upstream/transient responsibilities unless future implementation demonstrates independent state, authority, or lifecycle. This contract begins only when the supported start seam records one concrete Skill execution instance.

The executable owner is `src/relay_self/skill.py`; deterministic verification lives in `tests/test_skill_execution.py` and the cross-lifecycle stale-snapshot regressions in `tests/test_lifecycle_linearity.py`.

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

A separate Skill Execution owner remains justified.

### Current Intent association strengthening

The first Skill Execution bootstrap accepted a caller-supplied `intent_id`. That preserved an association field but did not establish that the referenced intent was actually current. Once both Current Intent Commitment and Skill Execution existed as executable owners, leaving that validation entirely to a future orchestrator was no longer the smallest sufficient boundary.

A new Intent-Skill coupling owner was not justified. No independent state machine, persistence, scheduler, or policy remained after start association validation. The responsibility is lifecycle-local because Skill Execution already owns the immutable `intent_id` association and `STARTED` event.

The start rule is therefore:

> `SkillExecution.start(...)` reads an `IntentCommitment`, requires that it currently owns a Current Intent, and derives the new execution's `intent_id` from that owner rather than accepting the identity from the caller.

Current Intent Commitment remains the sole owner of whether an intent is current. Skill Execution reads that state but does not mutate it.

A pending reconsideration request does not by itself release the Current Intent. A Skill may therefore still start for the same current intent while reconsideration is pending. Whether a runtime *should* start another Skill then is orchestration/policy, not this lifecycle invariant.

### Cancellation classification strengthening

The initial lifecycle exposed only:

```text
STARTED -> SUCCEEDED | FAILED
```

That is insufficient when an execution is stopped for an upstream or external reason. Reusing `FAILED` would claim that the Skill execution path itself failed. Leaving the execution `STARTED` would lose explicit causal closure.

The independent information is:

```text
Skill FAILED
  != Skill CANCELLED
```

`FAILED` means the execution path terminated unsuccessfully according to accepted Skill-level reason/evidence.

`CANCELLED` means the caller explicitly closed this execution lifecycle because it should no longer continue for an upstream or external reason, without asserting Skill success or Skill failure.

This distinction stays inside Skill Execution because that owner already owns terminal classification. No new supervisor or Intent-Skill coupling owner is required.

Automatic Current-Intent-to-Skill cancellation is **not** implied. Current authority still does not define interruptibility classes, yield points, controller supervision, child Actions, or a cross-owner time contract.

### Snapshot-lineage strengthening

Immutable lifecycle snapshots exposed a smaller executable contradiction.

Before this strengthening, the following was possible:

```text
s0 = STARTED snapshot
s1 = CANCELLED snapshot derived from s0

s0 still locally says STARTED
```

Because `s0` remained an ordinary immutable value, a caller could otherwise use that predecessor to create another terminal branch or pass it to Action proposal admission even after `s1` existed.

The missing information is not a general Skill supervisor. For snapshots derived from one supported start root, Skill Execution itself can retain the minimum owner-local fact:

```text
which snapshot revision is current in this lineage
```

The accepted rule is therefore:

```text
one supported Skill start root
  -> one ephemeral snapshot lineage
  -> one current revision
```

A successful transition creates a new immutable snapshot and advances lineage currentness only after that snapshot validates. The predecessor remains inspectable but becomes stale for further supported transitions and for Action proposal admission.

A failed transition does not advance currentness.

No fifth executable owner, generic registry, Skill scheduler, or controller is introduced by this rule.

## Boundary

For one Skill execution lineage:

```text
STARTED
  -> SUCCEEDED

STARTED
  -> FAILED

STARTED
  -> CANCELLED
```

`SUCCEEDED`, `FAILED`, and `CANCELLED` are terminal for the current lineage.

This contract deliberately has no pause, resume, yield, resumable interruption, preemption, retry, child-Action collection, or Action-derived terminal state.

## Execution identity and association

A Skill execution snapshot records immutable identity fields:

- `execution_id` — caller-supplied identity of this execution root;
- `skill_id` — identity/name of the Skill capability being executed;
- `intent_id` — identity of the Current Intent that was current when the supported start seam established this execution.

`execution_id` and `skill_id` remain caller inputs. `intent_id` is derived from `IntentCommitment.current_intent`.

A successful supported start therefore establishes:

```text
SkillExecution STARTED
  -> associated intent was Current Intent at Skill start
```

It does **not** establish:

```text
associated intent remains current for the whole Skill execution
```

Starting a Skill also does **not** prove that:

- `skill_id` exists in a validated capability library;
- the Skill was admitted as a candidate by a supported candidate-generation path;
- the Skill was selected by a supported selector;
- Skill initiation preconditions are satisfied;
- required Skill parameters were completely or correctly bound;
- any bound prediction, retrieved value, or heuristic is authoritative external state;
- the Skill is authorized for execution;
- the Skill was a good or optimal execution choice for the Current Intent;
- any primitive Action has been proposed, authorized, issued, or completed.

### Lineage currentness versus global identity uniqueness

Within one supported `SkillExecution.start(...)` root, snapshots share private ephemeral lineage state. Exactly one revision is current after each successful transition, and predecessor snapshots cannot transition again.

This is deliberately narrower than a repository-wide current/latest registry.

RelaySelf still does **not** establish:

- global uniqueness of the textual `execution_id` across independently created start roots;
- a repository-wide owner choosing the latest root for that identity;
- durable identity allocation or restart recovery;
- currentness across serialization/process boundaries;
- thread-safe or linearizable concurrent mutation semantics.

Two separately created start roots may therefore use the same textual `execution_id` and remain independent lineages under this contract. That behavior is a bounded non-claim, not evidence that duplicate identities are desirable in a future deployed runtime.

Direct construction of an immutable representation is not the supported runtime start operation and does not establish global identity authority.

## Start

`SkillExecution.start(...)` establishes one root snapshot with:

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
6. creates the root immutable Skill snapshot and its owner-local ephemeral lineage without mutating the Intent Commitment owner.

No caller-supplied `intent_id` is accepted by the supported start seam.

`STARTED` means the runtime records that this Skill execution has begun for the Current Intent observed at start. It does not mean a primitive Action has executed or that the environment has changed.

If reconsideration is pending but the intent remains current, start remains structurally valid. If the intent has already completed, failed, invalidated, or been released, start fails closed.

## Terminal transitions

The current `STARTED` snapshot may close exactly once as `SUCCEEDED`, `FAILED`, or `CANCELLED`.

All terminal transitions require:

- the supplied receiver is the current snapshot in its lineage;
- a non-empty reason;
- caller-supplied monotonic time;
- valid provenance for the terminal evidence/decision accepted by this boundary.

The next immutable snapshot is validated before lineage currentness advances.

### `SUCCEEDED`

`SUCCEEDED` means the caller has closed this Skill execution as having satisfied its Skill-level termination condition.

This state is **not** primitive Action `OUTCOME`, and it is not external world truth by itself. A future closed-loop Skill controller or adapter must decide what evidence is acceptable for Skill success. Skill success also does not automatically complete the associated Current Intent.

### `FAILED`

`FAILED` means this Skill execution path has terminated unsuccessfully according to the caller-supplied reason/evidence.

Failure does not automatically fail or release the associated Current Intent. Whether a particular failure should request reconsideration remains an upstream policy decision.

### `CANCELLED`

`CANCELLED` means the caller has explicitly closed this execution lifecycle because it should no longer continue for an upstream or external reason, without classifying the Skill path as successful or failed.

Cancellation does **not** by itself prove that:

- the associated Current Intent was completed, failed, invalidated, or released;
- an external controller or physical process has already stopped;
- any issued or in-flight primitive Action was cancelled;
- cancellation was safe under an interruptibility or yield policy;
- another Skill or Current Intent should be selected;
- the associated Current Intent should be failed, released, or reconsidered.

Those remain separate responsibilities.

## Terminality and stale predecessors

A terminal current snapshot cannot reopen or transition again.

In addition, when a current `STARTED` snapshot successfully transitions, its predecessor becomes stale. Therefore the same root cannot later reuse the old `STARTED` snapshot to create an alternate terminal branch.

Consequences include:

- success cannot later become failure or cancellation in the same lineage;
- failure cannot later become success or cancellation in the same lineage;
- cancellation cannot later become success or failure in the same lineage;
- stale predecessor snapshots cannot create sibling terminal histories;
- terminal event histories remain immutable;
- a retry or replacement execution is another supported start root rather than reopening the completed lineage.

This does not define who allocates globally unique execution identities or which independently created root should be selected by a future larger runtime.

## Time semantics

Skill events use caller-supplied non-negative integer monotonic time values.

Rules:

- successful events may share a timestamp or move forward;
- event time may not move backward inside one Skill lineage;
- malformed or backward time fails closed without consuming the current snapshot;
- the lifecycle does not read wall-clock time and does not own a scheduler.

This contract does not introduce a general cross-owner clock contract between Intent Commitment, Skill Execution, and Action Lifecycle.

## Provenance

Skill events reuse the repository's current immutable `Provenance` value type.

This does not make Action Lifecycle the semantic owner of Skill Execution. Provenance records where a start or terminal event came from; it does not by itself establish that the source was legitimate authority for Skill selection, initiation, success, failure, or cancellation.

## Causal history and lineage state

Each Skill snapshot stores an immutable tuple of `SkillEvent` values. State for that snapshot is derived from its final event.

Snapshots from one supported root additionally share a private ephemeral lineage head used only to determine whether that snapshot may still advance.

The minimum causal chain is:

```text
Current Intent owner state at start
  -> execution_id + skill_id + derived intent_id
  -> STARTED provenance
  -> SUCCEEDED | FAILED | CANCELLED provenance + reason
```

The lineage head does not alter or duplicate event semantics. It is not durable persistence, a repository-wide event store, a global latest-execution registry, or a restart-recovery contract.

## Relationship to Current Intent

Current Intent Commitment owns whether an intent is currently committed. Skill Execution owns one execution lineage and its immutable association.

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

The final relation is intentional. A future runtime/orchestrator may explicitly call `cancel(...)` after an upstream policy decides the execution should end. This contract does not define that policy.

## Relationship to primitive Action

Primitive Action semantics remain owned by [`action-lifecycle.md`](action-lifecycle.md), not by this contract.

The supported `ActionLifecycle.propose(...)` seam may consume a Skill snapshot plus the `IntentCommitment` owner. It requires:

- the Skill snapshot is current in its supported lineage;
- the Skill state is `STARTED`;
- an actual Current Intent exists;
- the Skill's `intent_id` matches that Current Intent.

The Action then derives its immutable `skill_execution_id` / `intent_id` association without mutating Skill event history.

```text
current SkillExecution STARTED
  + matching actual Current Intent
  -> ActionLifecycle PROPOSED

stale predecessor SkillExecution STARTED
  -> ActionLifecycle proposal rejected
```

This does **not** move primitive Action ownership into Skill Execution. Skill Execution still does not generate Action payloads, retain child Actions, authorize/issue Actions, inspect outcomes, cancel issued Actions, or infer Skill terminal state from Action closure.

## Fail-closed behavior

Malformed data or illegal transitions fail with explicit Skill Execution errors.

Examples include:

- empty execution or skill identity;
- malformed or absent `IntentCommitment` input;
- no Current Intent at Skill start;
- malformed provenance;
- negative or non-integer time;
- backward event time;
- empty terminal reason;
- a stale snapshot transition attempt;
- a terminal-to-terminal or terminal-to-active transition;
- malformed recorded history or internal revision data.

The mechanism does not silently invent an intent association, repair, branch, reopen, retry, or reinterpret invalid execution history.

A failed transition leaves the current snapshot current. Start validation and Skill terminal transitions do not mutate a separately held Intent Commitment owner.

## Deterministic verification obligations

Canonical pytest coverage must demonstrate at least:

- start establishes immutable execution/skill identity and `STARTED` state;
- supported start accepts no caller-supplied `intent_id`;
- start derives `intent_id` from the actual Current Intent;
- start with no Current Intent fails closed;
- start after Current Intent release/terminal closure fails closed;
- a pending reconsideration request leaves the same intent current and does not by itself make Skill start invalid;
- successful and failed start validation do not mutate Intent Commitment history/state;
- success, failure, and cancellation are explicit distinct terminal transitions with reason and provenance;
- a successful terminal transition makes the predecessor `STARTED` snapshot stale;
- a stale predecessor cannot create a second terminal branch;
- stale Skill snapshots are rejected by Action proposal admission;
- a failed Skill transition does not consume the current snapshot;
- separately created roots with the same textual `execution_id` are not claimed to be globally canonicalized;
- event time is monotonic inside the Skill lineage;
- malformed local identity/commitment/provenance/reason/time fails closed;
- event history is exposed as an immutable tuple;
- Skill terminal state does not automatically mutate or release Current Intent;
- later Current Intent completion/failure/invalidation/release does not automatically mutate an already-started Skill snapshot;
- Skill failure does not automatically create a Current Intent reconsideration request.

Skill-to-Action proposal-admission invariants are verified by the Action Lifecycle tests because Action Lifecycle owns that admission seam.

These tests are deterministic invariant evidence only. They do not prove useful Skill selection, capability existence, valid preconditions, closed-loop control quality, repository-wide global latest-root selection, durable retention, concurrent linearizability, safe interruption, physical/controller cancellation, environment correctness, successful primitive Actions, or physical execution.

## Non-goals

This contract intentionally does not define:

- a Skill capability library, persistent capability model, or Skill discovery;
- transient Skill-candidate projection/admission;
- Skill selection, arbitration, ranking, or matching policy beyond the start association invariant;
- general Skill parameter schema, candidate generation, or parameter-binding policy;
- initiation/precondition evaluation;
- closed-loop feedback/control policy or primitive Action generation;
- repository-wide global uniqueness/latest-root selection for `execution_id`;
- durable Skill-lineage persistence, serialization identity, or restart recovery;
- thread-safe/concurrent mutation semantics;
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
- package distribution or supported Python/dependency floors;
- simulation, model-quality, device, or physical qualification.

Those responsibilities should acquire owners only when independent semantics and current implementation consequences justify them.
