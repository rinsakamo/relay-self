# Current Intent Commitment Contract

## Purpose

This document owns the first executable semantics for RelaySelf's Current Intent commitment boundary.

It refines the ontology definition of Current Intent as the action-level objective currently committed for execution and the runtime principle that Intent is commitment rather than a per-tick winner. It does not define arbitration, candidate scoring, reconsideration-trigger detection, Skill execution, or primitive Action semantics.

The executable owner is `src/relay_self/intent.py`; deterministic verification lives in `tests/test_intent_commitment.py`.

## Grand Null result

A plain Current Intent value object is not enough to enforce commitment. A caller could simply replace that value with a newly selected candidate every decision epoch.

An arbitration engine is also not required to solve this problem. Candidate ranking answers which intent might be selected; commitment answers whether the already-selected intent may be replaced at all.

Likewise, this first contract does not need to decide which observations or conditions should trigger reconsideration. The runtime principle already names examples such as viability change, invalidated preconditions, important new evidence, blocker change, skill failure, deadline pressure, or material environment change. Detecting those conditions belongs to future upstream mechanisms.

The smallest independent responsibility is therefore:

> retain at most one Current Intent and require an explicit lifecycle operation before that commitment can be cleared or replaced.

## Boundary

For one `IntentCommitment` owner lifetime:

```text
NO CURRENT INTENT
  -> COMMIT(intent)
     -> CURRENT INTENT
        -> COMPLETE -> NO CURRENT INTENT
        -> FAIL -> NO CURRENT INTENT
        -> INVALIDATE -> NO CURRENT INTENT
        -> RECONSIDER(CONTINUE) -> SAME CURRENT INTENT
        -> RECONSIDER(RELEASE) -> NO CURRENT INTENT
```

A subsequent intent may be committed only after the current intent has been explicitly released or terminally closed.

This contract does not define how the first intent or any later candidate was generated or ranked.

## Current Intent state

A committed intent records:

- `intent_id` — runtime identity of the commitment;
- `objective` — the action-level objective currently committed for execution;
- commit monotonic time;
- provenance for the commit transition.

`current_intent` is derived from the owner's immutable event tuple rather than stored as an independent mutable field.

The event tuple is an in-memory causal trace for this bounded owner. It is not durable Persistent Cognition, a persistence contract, or a repository-wide event store.

Constructing a `CurrentIntent` value directly does not establish runtime commitment. Only successful mutation of an `IntentCommitment` owner changes that owner's current intent.

## Commitment and silent replacement

`commit(...)` is valid only when no Current Intent is active.

If an intent is already current, another `commit(...)` fails closed and leaves the existing commitment and event history unchanged.

Therefore an ordinary alternative, newly scored candidate, or model suggestion cannot silently dethrone the current intent through this boundary. A caller must first perform an explicit release or terminal closure operation.

An `intent_id` may be committed only once during one owner lifetime. Terminally closing or releasing an intent does not make its identity reusable.

Identity non-reuse keeps the causal trace unambiguous. This is not a durable global identifier policy.

## Reconsideration decision

Reconsideration is represented as an explicit decision about the current intent, not as automatic replacement merely because another candidate exists.

The current contract supports two decisions:

### `CONTINUE`

`reconsider(..., decision=CONTINUE, ...)` records that reconsideration occurred and retains the same intent identity and objective.

This is important because reconsideration does not imply abandonment. The runtime may inspect a meaningful change and deliberately reaffirm the current commitment.

### `RELEASE`

`reconsider(..., decision=RELEASE, ...)` records the decision and clears the Current Intent.

A later `commit(...)` may then establish another intent.

The caller supplies a non-empty reason and provenance. This contract records the decision but does not decide whether the upstream trigger was sufficiently important or whether a replacement candidate is preferable.

## Terminal release

The current intent may also be cleared explicitly as:

- `COMPLETED` — the executable objective is considered complete by the caller;
- `FAILED` — the current objective cannot be completed through the current execution path;
- `INVALIDATED` — the commitment is no longer valid, for example because an assumed precondition no longer holds.

Each transition requires a non-empty reason and provenance.

These states describe Current Intent commitment closure only. They do not define Skill success evidence, Action consequence evidence, or persistent Goal lifecycle semantics.

## Time semantics

Intent commitment events use caller-supplied non-negative integer monotonic time values.

Rules:

- successful events may share a timestamp or move forward;
- event time may not move backward inside one owner lifetime;
- malformed or backward time fails before history changes;
- failed operations do not advance owner time.

The owner does not read wall-clock time and does not own a scheduler.

Allowing equal timestamps permits an explicit release followed by a new commit in one runtime decision epoch without inventing sub-tick wall-clock ordering.

## Provenance

Intent events use the repository's existing immutable `Provenance` value type.

This transaction intentionally does not duplicate another provenance representation. The current Python bootstrap type is still defined in `relay_self.action`; reusing that value type does not make Action Lifecycle the semantic owner of Current Intent or Reconsideration.

Moving the shared value type into a new module is not required for this commitment invariant and would also change the ownership of existing Action validation errors. That refactor should occur only in a separate bounded transaction if a concrete benefit outweighs that migration cost.

A provenance record does not by itself prove that a model, user, policy, or external source was authorized to select the intent. General intent-selection authority is not defined by this contract.

## Fail-closed behavior

Operations fail without changing event history when, for example:

- another intent is already current;
- an intent identity is reused;
- there is no current intent to reconsider or close;
- a caller targets an intent other than the current intent;
- time is malformed or moves backward;
- the reconsideration decision is not declared;
- required text or provenance is malformed.

The mechanism raises explicit commitment errors rather than silently repairing, replacing, or skipping invalid transitions.

## Deterministic verification obligations

Canonical pytest coverage must demonstrate at least:

- commit establishes one Current Intent;
- a second commit cannot replace an active intent and does not mutate history;
- reconsideration `CONTINUE` retains the same intent identity and objective;
- reconsideration `RELEASE` clears the current intent;
- completion, failure, and invalidation each clear the current intent explicitly;
- a new intent may be committed after explicit release or terminal closure;
- an intent identity cannot be reused inside one owner lifetime;
- the wrong intent identity cannot be reconsidered or closed;
- operations requiring a current intent fail when none exists;
- malformed or backward time fails without mutation;
- malformed reconsideration or provenance input fails without mutation;
- event history is exposed as an immutable tuple;
- current intent is derived from causal history rather than maintained as duplicate mutable state.

These tests are deterministic invariant evidence only. They do not show that the chosen intent is useful, optimal, safe, or grounded in a correct world model.

## Non-goals

This contract intentionally does not define:

- arbitration scores, candidate ranking, concern projection, or winner selection;
- detection of reconsideration triggers;
- viability policy, hysteresis, minimum commitment duration, or preemption policy;
- atomic preemption-and-replacement semantics;
- Skill lifecycle, interruption, yield points, or action generation;
- Action Lifecycle or Action Supervision integration;
- durable Goal / Commitment persistence or a Present Projection compiler;
- authority policy for who may select an intent;
- LLM/model inference or automatic promotion of model output into Current Intent;
- wall-clock scheduling, environment adapters, simulation, GPU, device, or physical execution;
- durable persistence or restart recovery;
- package distribution or supported Python/dependency floors.

Those responsibilities should acquire owners only when current implementation requires them.
