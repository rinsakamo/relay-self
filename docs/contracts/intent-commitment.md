# Current Intent Commitment Contract

## Purpose

This document owns the executable semantics for RelaySelf's Current Intent commitment boundary.

It refines the ontology definition of Current Intent as the action-level objective currently committed for execution and the runtime principle that Intent is commitment rather than a per-tick winner. It also preserves the causal distinction between a runtime condition that requests reconsideration and the later reconsideration decision itself.

The executable owner is `src/relay_self/intent.py`; deterministic verification lives in `tests/test_intent_commitment.py`.

This contract does not define arbitration, candidate scoring, reconsideration-trigger detection, Event Admission policy, Skill execution, or primitive Action semantics.

## Grand Null result

A plain Current Intent value object is not enough to enforce commitment. A caller could simply replace that value with a newly selected candidate every decision epoch.

An arbitration engine is not required to solve that problem. Candidate ranking answers which intent might be selected; commitment answers whether the already-selected intent may be replaced at all.

A general reconsideration-trigger detector is also not yet justified. Current authority names possible trigger sources such as viability-class change, invalidated intent preconditions, important new evidence, new affordances, blocker changes, Skill stall/failure, deadline pressure, and material environment change, but those source mechanisms do not yet have executable owners in this repository. A generic detector would currently only re-label caller declarations.

One smaller independent fact is required now: **the cause that requested reconsideration and the later decision to continue or release are distinct causal information.** They must not be collapsed into one event if RelaySelf is to reconstruct why reconsideration happened separately from what the runtime decided.

The smallest implementation therefore remains one `IntentCommitment` owner with an explicit reconsideration-request seam. Trigger detection and trigger-admission policy stay upstream and deferred.

## Boundary

For one `IntentCommitment` owner lifetime:

```text
NO CURRENT INTENT
  -> COMMIT(intent)
     -> CURRENT INTENT
        -> COMPLETE -> NO CURRENT INTENT
        -> FAIL -> NO CURRENT INTENT
        -> INVALIDATE -> NO CURRENT INTENT
        -> REQUEST_RECONSIDERATION
           -> PENDING RECONSIDERATION
              -> RECONSIDER(CONTINUE) -> SAME CURRENT INTENT
              -> RECONSIDER(RELEASE) -> NO CURRENT INTENT
```

A terminal completion/failure/invalidation may also close the current commitment while reconsideration is pending. In that case no pending reconsideration remains because the target Current Intent no longer exists.

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

## Reconsideration request

`request_reconsideration(...)` records that an upstream runtime responsibility determined that the current intent should be reconsidered.

The request requires:

- the current `intent_id`;
- a non-empty trigger reason;
- caller-supplied monotonic time;
- provenance for the upstream condition or event that caused the request.

A request does **not** decide whether the current intent should continue or be released.

At most one reconsideration request may be pending for the current intent. A second request while one is pending fails closed instead of silently replacing, merging, or obscuring the first causal trigger.

`pending_reconsideration` is derived from event history. It is not stored as a second mutable state field.

This seam starts **after** upstream trigger detection/admission. Calling `request_reconsideration(...)` asserts that some external mechanism has already decided the condition is meaningful enough to enter reconsideration. This contract does not validate that upstream policy choice.

## Reconsideration decision

Reconsideration is represented as an explicit decision about the current intent, not as automatic replacement merely because another candidate exists.

`reconsider(...)` requires a pending reconsideration request for the same current intent. Calling it without a pending request fails closed.

The current contract supports two decisions:

### `CONTINUE`

`reconsider(..., decision=CONTINUE, ...)` consumes the pending request, records separate decision provenance/reason, and retains the same intent identity and objective.

Reconsideration therefore does not imply abandonment. The runtime may inspect a meaningful change and deliberately reaffirm the current commitment.

### `RELEASE`

`reconsider(..., decision=RELEASE, ...)` consumes the pending request, records separate decision provenance/reason, and clears the Current Intent.

A later `commit(...)` may then establish another intent.

The causal chain remains inspectable as:

```text
commit provenance
  -> reconsideration-request provenance + trigger reason
  -> reconsideration-decision provenance + decision reason
```

This contract records the request and decision but does not decide whether the upstream trigger was sufficiently important or whether a replacement candidate is preferable.

## Terminal release

The current intent may also be cleared explicitly as:

- `COMPLETED` — the executable objective is considered complete by the caller;
- `FAILED` — the current objective cannot be completed through the current execution path;
- `INVALIDATED` — the commitment is no longer valid, for example because an assumed precondition no longer holds.

Each transition requires a non-empty reason and provenance.

If one of these transitions occurs while reconsideration is pending, the terminal transition closes the commitment and the derived pending state becomes empty. The earlier request remains in causal history; it is not rewritten or silently removed.

These states describe Current Intent commitment closure only. They do not define Skill success evidence, Action consequence evidence, or persistent Goal lifecycle semantics.

## Time semantics

Intent commitment events use caller-supplied non-negative integer monotonic time values.

Rules:

- successful events may share a timestamp or move forward;
- event time may not move backward inside one owner lifetime;
- malformed or backward time fails before history changes;
- failed operations do not advance owner time.

The owner does not read wall-clock time and does not own a scheduler.

Allowing equal timestamps permits a request and decision, or an explicit release and a new commit, inside one runtime decision epoch without inventing sub-tick wall-clock ordering.

## Provenance

Intent events use the repository's existing immutable `Provenance` value type.

This contract intentionally does not duplicate another provenance representation. The current Python bootstrap type is still defined in `relay_self.action`; reusing that value type does not make Action Lifecycle the semantic owner of Current Intent or Reconsideration.

A reconsideration request and its decision deliberately carry separate provenance. The request provenance grounds what caused reconsideration to become pending; the decision provenance grounds the later continue/release decision.

A provenance record does not by itself prove that a model, user, policy, or external source was authorized to select or reconsider an intent. General intent-selection and trigger-admission authority are not defined by this contract.

## Fail-closed behavior

Operations fail without changing event history when, for example:

- another intent is already current;
- an intent identity is reused;
- there is no current intent to request reconsideration or close;
- a caller targets an intent other than the current intent;
- a second reconsideration request arrives while one is already pending;
- `reconsider(...)` is called without a pending request;
- time is malformed or moves backward;
- the reconsideration decision is not declared;
- required text or provenance is malformed.

A failed decision does not consume the pending request. A failed request does not create pending state.

The mechanism raises explicit commitment errors rather than silently repairing, replacing, merging, or skipping invalid transitions.

## Deterministic verification obligations

Canonical pytest coverage must demonstrate at least:

- commit establishes one Current Intent;
- a second commit cannot replace an active intent and does not mutate history;
- reconsideration request is recorded separately from a decision and leaves the Current Intent active;
- only the current intent may receive a reconsideration request;
- at most one reconsideration request is pending at a time;
- reconsideration without a pending request fails without mutation;
- reconsideration `CONTINUE` consumes the request while retaining the same intent identity and objective;
- reconsideration `RELEASE` consumes the request and clears the current intent;
- trigger provenance and decision provenance remain separately inspectable;
- completion, failure, and invalidation each clear the current intent and any derived pending state;
- a new intent may be committed after explicit release or terminal closure;
- an intent identity cannot be reused inside one owner lifetime;
- malformed, wrong-target, or backward-time input fails without partial mutation;
- a failed reconsideration decision leaves the pending request intact;
- event history is exposed as an immutable tuple;
- current intent and pending reconsideration are derived from causal history rather than maintained as duplicate mutable state.

These tests are deterministic invariant evidence only. They do not show that a trigger was useful, correctly detected, sufficiently important, or that the chosen intent is optimal, safe, or grounded in a correct world model.

## Non-goals

This contract intentionally does not define:

- reconsideration-trigger detection or Event Admission policy;
- a trigger taxonomy, trigger priority, threshold, or scoring model;
- viability, blocker, affordance, evidence-importance, Skill failure, or deadline detectors;
- periodic reconsideration cadence;
- arbitration scores, candidate ranking, concern projection, or winner selection;
- viability policy, hysteresis, minimum commitment duration, or preemption policy;
- atomic preemption-and-replacement semantics;
- Skill lifecycle, interruption, yield points, or action generation;
- Action Lifecycle or Action Supervision integration;
- durable Goal / Commitment persistence or a Present Projection compiler;
- authority policy for who may select an intent or admit a reconsideration trigger;
- LLM/model inference or automatic promotion of model output into Current Intent;
- wall-clock scheduling, environment adapters, simulation, GPU, device, or physical execution;
- durable persistence or restart recovery;
- package distribution or supported Python/dependency floors.

Those responsibilities should acquire owners only when current implementation requires them.
