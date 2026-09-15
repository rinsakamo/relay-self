# Action Lifecycle Contract

## Purpose

This document owns the executable transition semantics for RelaySelf's first Action Lifecycle boundary.

It refines the architectural distinction already owned by `docs/architecture.md` and the action-closure principle owned by `docs/runtime-principles.md`. It does not redefine Goal, Intent, Skill, Environment, or general authority policy.

The executable owner is `src/relay_self/action.py`; deterministic verification lives in `tests/test_action_lifecycle.py`.

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
| `PROPOSED` | An action has been proposed. No execution authority is implied. |
| `AUTHORIZED` | An explicit authorization decision permits this action to proceed to issuance. This is still not execution. |
| `DENIED` | An explicit authorization decision rejects the proposal. Terminal before issuance. |
| `ISSUED` | The authorized command has been handed to the execution boundary. Issuance is not success and is not consequence evidence. |
| `OUTCOME` | An acceptable consequence observation or result attestation closed the issued action. This state does not mean success unless the referenced outcome says so. |
| `TIMEOUT` | The issued action reached its explicit monotonic deadline without an observed outcome that closed it. |
| `UNKNOWN` | The issued action cannot be resolved to an acceptable observed outcome or timeout result, and the uncertainty is closed explicitly rather than inventing success. |

`DENIED`, `OUTCOME`, `TIMEOUT`, and `UNKNOWN` are terminal.

## Allowed transitions

The only allowed transitions are:

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
- issuance is not outcome;
- an issued action cannot close as an undeclared success state;
- a terminal lifecycle cannot be reopened or rewritten by another transition.

## Authority ownership

This contract owns **the lifecycle gate and its recorded authorization seam**, not the future policy engine that decides which real-world principal is authorized for which action.

An authorization decision therefore requires:

- explicit authorization authority identity;
- provenance identifying the source and reference for that decision.

The lifecycle implementation records that input and refuses issuance when the authorization transition is absent. It does not prove that an arbitrary authority string is legitimate in the outside world. That legitimacy belongs to a future authority-policy owner or boundary adapter.

Model or language output does not become execution authority merely by appearing in provenance. A caller that wants to promote a model proposal must first pass through the separate authorization responsibility.

## Provenance

Every lifecycle event records:

- `source` — the component or boundary that supplied the event;
- `reference` — an identifier that can be followed to the material source, decision, command, or observation.

Authorization decisions additionally record `authority`.

The lifecycle history is immutable. Current state is derived from the last event rather than maintained as a second mutable truth.

The minimum causal chain for an issued action is therefore reconstructable as:

```text
proposal provenance
  -> authorization provenance + authority
  -> issuance provenance + deadline
  -> terminal closure provenance
```

This is causal trace for this boundary only. It is not yet a repository-wide event store.

## Time and timeout semantics

Time values in this contract are caller-supplied non-negative integer values in one monotonic nanosecond domain.

The lifecycle does not read wall-clock time and does not own a scheduler.

Rules:

- event time must never move backward within one lifecycle;
- issuance requires an explicit `deadline_ns` strictly later than issue time;
- `TIMEOUT` is invalid before that deadline;
- `OUTCOME` may close an issued action before the deadline when consequence evidence is available;
- `UNKNOWN` may close an issued action when acceptable consequence resolution is unavailable and uncertainty must be represented explicitly.

The runtime-level liveness obligation remains:

```text
ActionIssued(a)
  -> eventually Outcome(a) | Timeout(a) | Unknown(a)
```

This pure state machine cannot make time advance by itself. The future scheduler/execution boundary must revisit issued actions and provide one of the terminal closure events. Requiring a finite deadline makes the timeout boundary explicit; it does not by itself prove that an external scheduler performed the revisit.

## Invalid data and invalid transitions

Malformed lifecycle data fails closed. Examples include:

- empty action identifiers;
- empty provenance source or reference;
- missing authorization authority;
- negative or non-integer monotonic time;
- backward event time;
- an issuance deadline at or before issue time;
- timeout before the issued deadline;
- a recorded event history containing an undeclared transition.

The implementation raises explicit `InvalidActionData` or `InvalidTransition` errors rather than silently repairing or skipping the invalid transition.

## Deterministic verification obligations

The canonical pytest coverage must demonstrate at least:

- authorized issuance can close with an outcome while preserving causal history;
- proposal-to-issued bypass is rejected;
- denied proposals cannot be issued;
- timeout is accepted at or after the deadline and rejected before it;
- unknown closure is explicit and terminal;
- terminal states reject further transitions;
- event time is monotonic;
- issue deadlines are strictly later than issue time;
- authorization requires explicit authority input.

These tests are deterministic invariant evidence. They are not simulation results and do not qualify a device, environment, model, scheduler, or external authority system.

## Non-goals

This contract intentionally does not define:

- action payload schemas or environment-specific commands;
- general capability or authority policy resolution;
- Current Intent or arbitration;
- Skill lifecycle or interruption semantics;
- automatic scheduling or background timeout execution;
- environment truth or consequence interpretation beyond explicit closure provenance;
- package distribution, supported Python-version floors, or external dependency floors;
- model, simulator, GPU, device, or physical qualification.

Those concerns should acquire their own owners only when current implementation requires them.
