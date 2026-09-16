# Action Lifecycle Contract

## Purpose

This document owns the executable transition semantics for RelaySelf's primitive Action Lifecycle boundary.

It refines the architectural distinction already owned by `docs/architecture.md` and the action-closure principle owned by `docs/runtime-principles.md`. It owns one primitive Action from grounded proposal admission through authorization and issuance to terminal closure. It does not own Current Intent commitment, Skill execution lifecycle, Skill selection/control policy, environment execution, or general authority policy.

The executable owner is `src/relay_self/action.py`; deterministic verification lives in `tests/test_action_lifecycle.py`.

Deterministic in-flight retention and decision-epoch timeout processing are owned separately by [`action-supervision.md`](action-supervision.md).

## Contract boundary

The lifecycle tracks one proposed primitive action from proposal through authorization and issuance to a terminal closure.

```text
PROPOSED
  -> AUTHORIZED
  -> ISSUED
  -> OUTCOME | TIMEOUT | UNKNOWN

PROPOSED
  -> DENIED
```

The states mean:

| State | Meaning |
| --- | --- |
| `PROPOSED` | An action has been admitted as a primitive effect proposal from a supplied started Skill execution whose associated intent matched the actual Current Intent at proposal admission. No execution authority is implied. |
| `AUTHORIZED` | An explicit authorization decision permits this action to proceed to issuance. This is still not execution. |
| `DENIED` | An explicit authorization decision rejects the proposal. Terminal before issuance. |
| `ISSUED` | The authorized command has been handed to the execution boundary. Issuance is not success and is not consequence evidence. |
| `OUTCOME` | An acceptable consequence observation or result attestation closed the issued action. This state does not mean success unless the referenced outcome says so. |
| `TIMEOUT` | The issued action reached its explicit monotonic deadline without an observed outcome that closed it. |
| `UNKNOWN` | The issued action cannot be resolved to an acceptable observed outcome or timeout result, and the uncertainty is closed explicitly rather than inventing success. |

`DENIED`, `OUTCOME`, `TIMEOUT`, and `UNKNOWN` are terminal.

## Skill / Current Intent proposal admission

The supported `ActionLifecycle.propose(...)` seam grounds the Action's causal origin in existing upstream semantics rather than accepting association IDs as caller-selected text.

Proposal admission requires:

- a real `SkillExecution` value;
- the supplied Skill execution is currently represented by that value in `STARTED` state;
- a real `IntentCommitment` owner with a Current Intent;
- `skill_execution.intent_id == intent_commitment.current_intent.intent_id`;
- a non-empty Action identity;
- caller-supplied non-negative Action event time;
- valid proposal provenance.

On success, the Action lifecycle derives and retains immutable association fields:

- `skill_execution_id` from `skill_execution.execution_id`;
- `intent_id` from the actual Current Intent owned by `IntentCommitment` at proposal admission.

The caller does not supply either association identity through the supported proposal seam.

The deterministic relation is:

```text
ActionLifecycle PROPOSED
  -> supplied SkillExecution was STARTED at proposal admission
  -> supplied Skill intent matched the actual Current Intent at proposal admission
```

Current Intent Commitment remains the sole owner of which intent is current. Skill Execution remains the owner of one execution lifecycle value and its immutable Intent association. Action Lifecycle reads those facts at proposal admission and does not mutate either upstream object.

A pending reconsideration request does not by itself release Current Intent. Therefore a proposal from a supplied `STARTED` Skill remains structurally valid while the same Intent is still current. Whether a runtime should emit more Actions while reconsideration is pending is orchestration/policy, not this lifecycle invariant.

If Current Intent has already completed, failed, invalidated, or been released, proposal admission fails closed. If another Intent has since become current, a Skill associated with the earlier Intent also fails proposal admission even when the supplied immutable Skill value still says `STARTED`.

Likewise, a supplied Skill value already in `SUCCEEDED`, `FAILED`, or `CANCELLED` state cannot produce a new Action proposal through the supported seam.

### Latest-execution non-claim

`SkillExecution` is currently an immutable lifecycle value. RelaySelf does not yet have a repository-wide Skill supervisor/current-execution registry that proves a supplied `SkillExecution` value is the latest branch/version for its `execution_id`.

Therefore this contract deliberately claims only what it validates from the supplied value and Current Intent owner. It does not claim global latest-Skill retention or eliminate the need for future runtime orchestration if concrete execution later requires such ownership.

Direct construction of the immutable `ActionLifecycle` representation is not the supported runtime proposal operation. The executable proposal-admission invariant is owned by `ActionLifecycle.propose(...)`, analogous to the distinction between an immutable representation and the transition that establishes valid runtime state.

## Allowed transitions

After successful proposal admission, the only allowed transitions are:

```text
PROPOSED   -> AUTHORIZED
PROPOSED   -> DENIED
AUTHORIZED -> ISSUED
ISSUED     -> OUTCOME
ISSUED     -> TIMEOUT
ISSUED     -> UNKNOWN
```

All other transitions fail closed with an explicit lifecycle error.

Important consequences include:

- a proposal cannot become issued without an explicit authorization event;
- denial cannot be bypassed;
- authorization is not issuance;
- issuance is not external execution or outcome;
- an issued action cannot close as an undeclared success state;
- a terminal lifecycle cannot be reopened or rewritten by another transition;
- the immutable `skill_execution_id` and `intent_id` association is retained across every Action transition.

## Authority ownership

This contract owns **proposal admission, lifecycle transition legality, and the recorded authorization seam**, not the policy engines that select Skills, decide which Actions to generate, or determine which real-world principal is authorized for which action.

An authorization decision therefore requires:

- explicit authorization authority identity;
- provenance identifying the source and reference for that decision.

The lifecycle implementation records that input and refuses issuance when the authorization transition is absent. It does not prove that an arbitrary authority string is legitimate in the outside world. That legitimacy belongs to a future authority-policy owner or boundary adapter.

Model or language output does not become execution authority merely by appearing in provenance. A caller that wants to promote a model proposal must first pass through the separate authorization responsibility.

Proposal admission also does not prove that a Skill was correctly selected, that its capability exists, that initiation preconditions held, or that a closed-loop controller actually generated a suitable effect command. Those remain distinct responsibilities.

## Provenance and causal association

Every lifecycle event records:

- `source` — the component or boundary that supplied the event;
- `reference` — an identifier that can be followed to the material source, decision, command, or observation.

Authorization decisions additionally record `authority`.

The lifecycle history is immutable. Current state is derived from the last event rather than maintained as a second mutable truth.

The Action lifecycle also retains the immutable Skill-execution and Intent identities established by the supported proposal seam. Those structural associations are not substitutes for event provenance; they answer different causal questions.

The minimum causal chain is therefore reconstructable as:

```text
actual Current Intent at proposal admission
  + supplied STARTED SkillExecution associated with that Intent
  -> action_id + derived skill_execution_id + intent_id
  -> proposal provenance
  -> authorization provenance + authority
  -> issuance provenance + deadline
  -> terminal closure provenance
```

This is causal trace for this boundary only. It is not yet a repository-wide event store or a Skill child-Action collection.

## Time and timeout semantics

Time values in this contract are caller-supplied non-negative integer values in one Action-local monotonic nanosecond domain.

The lifecycle does not read wall-clock time and does not own a scheduler or runtime supervisor.

Rules:

- Action event time must never move backward within one lifecycle;
- issuance requires an explicit `deadline_ns` strictly later than issue time;
- `TIMEOUT` is invalid before that deadline;
- `OUTCOME` may close an issued action whenever acceptable consequence evidence is processed before another terminal transition wins;
- `UNKNOWN` may close an issued action when acceptable consequence resolution is unavailable and uncertainty must be represented explicitly.

Proposal admission does not introduce a cross-owner clock contract between Intent, Skill, and Action histories. The seam validates the supplied owner/value states at the operation boundary; it does not compare their independent monotonic timestamps.

The runtime-level liveness obligation remains:

```text
ActionIssued(a)
  -> eventually Outcome(a) | Timeout(a) | Unknown(a)
```

This pure state machine cannot make time advance by itself. The current [`Action Supervision`](action-supervision.md) contract adds deterministic retention and explicit decision-epoch timeout processing for actions issued through that boundary. It still does not make future epochs happen autonomously; a future runtime driver or scheduler must supply those epochs.

Requiring a finite deadline therefore makes timeout eligibility explicit, while Action Supervision proves what happens when a qualifying epoch is actually processed. Neither fact alone proves deployed wall-clock liveness.

## Relationship to Skill Execution

Skill Execution owns one Skill execution lifecycle and its immutable `execution_id`, `skill_id`, and `intent_id` association. Action Lifecycle does not take over that lifecycle.

The proposal seam reads a supplied Skill execution only to establish one Action's causal association and admission validity at that moment.

Therefore:

```text
Skill STARTED + matching Current Intent
  -> Action proposal may be admitted

Action PROPOSED
  != Skill generated a correct command

Action OUTCOME
  != automatic Skill SUCCEEDED / FAILED

Skill CANCELLED
  != automatic child-Action cancellation

later Current Intent release
  != automatic Skill cancellation
  but blocks new proposals from a Skill associated with the released Intent
```

Action Lifecycle does not retain a collection of child Actions inside Skill Execution, infer Skill termination, select replacement Skills, or supervise a Skill controller.

## Invalid data and invalid transitions

Malformed lifecycle data fails closed. Examples include:

- empty action, Skill-execution, or Intent identifiers;
- empty provenance source or reference;
- malformed Skill Execution or Intent Commitment inputs at proposal admission;
- supplied Skill execution not in `STARTED` state;
- no Current Intent at proposal admission;
- supplied Skill's associated Intent not matching the actual Current Intent;
- missing authorization authority;
- negative or non-integer monotonic Action time;
- backward Action event time;
- an issuance deadline at or before issue time;
- timeout before the issued deadline;
- a recorded event history containing an undeclared transition.

The implementation raises explicit `InvalidActionData` or `InvalidTransition` errors rather than silently repairing or skipping invalid data or transitions.

Proposal validation is read-only with respect to the supplied Skill execution and Intent Commitment. Successful or failed validation does not mutate their histories/state.

## Deterministic verification obligations

Canonical pytest coverage must demonstrate at least:

- supported proposal derives `skill_execution_id` from a supplied `STARTED` Skill execution;
- supported proposal derives `intent_id` from the actual Current Intent and requires it to match the Skill association;
- supplied `SUCCEEDED`, `FAILED`, and `CANCELLED` Skill executions cannot produce new proposals;
- no-current-intent proposal fails closed;
- a supplied Skill associated with a replaced/released Intent cannot propose under a different Current Intent;
- pending reconsideration does not by itself block proposal while the same Intent remains current;
- successful and failed proposal admission do not mutate Skill or Intent state/history;
- Action transitions and Action Supervision preserve the immutable Skill/Intent association;
- authorized issuance can close with an outcome while preserving causal history;
- proposal-to-issued bypass is rejected;
- denied proposals cannot be issued;
- timeout is accepted at or after the deadline and rejected before it;
- unknown closure is explicit and terminal;
- terminal states reject further transitions;
- Action event time is monotonic;
- issue deadlines are strictly later than issue time;
- authorization requires explicit authority input.

These tests are deterministic invariant evidence. They are not simulation results and do not prove latest-Skill retention, useful Skill selection/control, environment correctness, physical execution, or model quality.

## Non-goals

This contract intentionally does not define:

- Action payload schemas or environment-specific commands;
- Skill selection, capability truth, precondition evaluation, or a closed-loop Skill controller;
- repository-wide latest/current Skill-execution retention;
- child-Action collections inside Skill Execution;
- automatic Action-outcome-to-Skill terminal inference;
- automatic Skill cancellation or cancellation of issued/in-flight Actions;
- general capability or authority policy resolution;
- Current Intent lifecycle or arbitration beyond reading Current Intent for proposal admission;
- Skill lifecycle semantics beyond reading the supplied Skill state/association for proposal admission;
- in-flight action retention or decision-epoch processing, which are owned by `action-supervision.md`;
- autonomous wall-clock scheduling or background timeout execution;
- environment truth or consequence interpretation beyond explicit closure provenance;
- cross-owner clock semantics;
- package distribution, supported Python-version floors, or external dependency floors;
- model, simulator, GPU, device, or physical qualification.

Those concerns should acquire their own owners only when current implementation requires them.
