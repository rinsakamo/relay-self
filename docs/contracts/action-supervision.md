# Action Supervision Contract

## Purpose

This document owns the executable runtime semantics for deterministic supervision of in-flight primitive actions across explicit runtime decision epochs.

It builds on [`action-lifecycle.md`](action-lifecycle.md), which remains the sole owner of legal Action Lifecycle transitions. It refines the runtime-level closure obligation from `docs/runtime-principles.md` without claiming that a pure state machine can advance time or schedule itself.

The executable owner is `src/relay_self/action_supervision.py`; deterministic verification lives in `tests/test_action_supervision.py`.

## Grand Null result

The existing `ActionLifecycle` already owns proposal, authorization, issuance, deadline, and terminal transition legality.

Adding an "automatic timeout" method to that immutable state machine would not create liveness: the method would still need an external caller. Embedding a wall clock, timer thread, or background loop inside the lifecycle would instead collapse lifecycle semantics with runtime scheduling and contradict the current lifecycle contract.

A general Scheduler is also not yet justified.

The smallest independent responsibility that remains is therefore **Action Supervision**:

> retain actions issued through the supervision boundary and deterministically process them when explicit monotonic runtime events or decision epochs arrive.

A future runtime driver also should not need to inspect Action Lifecycle event storage to discover when supervision next requires deadline processing. The supervisor therefore owns a derived next-deadline query for its retained open actions; this does not make the supervisor a clock or scheduler.

## Boundary

For actions managed by this boundary:

```text
AUTHORIZED ActionLifecycle
  -> supervised issue
     -> ISSUED + retained by supervisor
        -> record outcome -> OUTCOME
        -> mark unresolved -> UNKNOWN
        -> advance epoch at/after deadline -> TIMEOUT
```

The supervisor does not reimplement lifecycle legality. It calls the existing `ActionLifecycle.issue`, `record_outcome`, `mark_unknown`, and `timeout` transitions.

`ActionLifecycle.issue` remains a valid lower-level transition API. The stronger supervision guarantees in this contract apply only to actions issued through `ActionSupervisor`.

## Supervised issuance and identity

`ActionSupervisor.issue(...)` accepts an `ActionLifecycle` and delegates issuance to the lifecycle owner.

Rules:

- lifecycle issuance must itself be legal, including prior authorization;
- successful supervised issuance retains the exact issued lifecycle under its `action_id` in the same operation;
- failed issuance does not register the action or advance supervisor time;
- an `action_id` may be supervised only once during one supervisor lifetime;
- terminal lifecycles remain retained so an identifier cannot silently be reused and so the final causal lifecycle remains inspectable;
- lookup of an unknown or malformed supervised identity fails explicitly.

This retained in-memory mapping is the current bounded runtime mechanism. It is not a durable event store or persistence contract.

## Explicit processing time

Supervisor processing uses caller-supplied non-negative integer values in the same monotonic nanosecond style used by the Action Lifecycle contract.

The supervisor records the last successfully processed time.

Rules:

- successful time-bearing operations may keep the same timestamp or move forward;
- processing time may not move backward;
- malformed time fails before supervisor state changes;
- a failed operation does not advance supervisor time.

The timestamp is an explicit runtime ordering input. The supervisor does not read wall-clock time.

## Next deadline scheduling seam

`next_deadline_ns` exposes the earliest outstanding issuance deadline among the supervisor's currently open `ISSUED` actions.

The value is derived on read from current supervised state. It is not stored as a second mutable scheduling truth.

Rules:

```text
if open supervised actions exist:
  next_deadline_ns = minimum issuance deadline among open actions
else:
  next_deadline_ns = None
```

Consequences:

- terminal retained lifecycles do not contribute to the value;
- action identifier ordering does not affect the result;
- closing or timing out the earliest action exposes the next remaining open deadline;
- reading the property does not advance supervisor time or mutate any lifecycle;
- the value may be less than or equal to `last_at_ns` when other runtime events advanced supervisor processing time without a timeout epoch; an overdue obligation is reported unchanged rather than clamped away.

This seam tells a future event-driven runtime **when Action Supervision next requires time-based attention**. It does not decide how a host clock, timer, event source, or scheduler delivers that future epoch.

## Outcome and unknown closure

`record_outcome(...)` and `mark_unknown(...)` resolve one supervised action through the existing Action Lifecycle transition methods.

Therefore:

- only an action that is still legally closable by that lifecycle transition may close;
- provenance validation and terminality are still enforced by the lifecycle owner;
- a terminal action cannot be reopened;
- failed closure does not replace the retained lifecycle or advance supervisor time.

## Decision epochs and timeout closure

`advance(at_ns=..., provenance=...)` is the deterministic decision-epoch operation.

For one successful advance to time `t`:

1. supervisor time is validated as monotonic;
2. epoch provenance must be a valid `Provenance` value;
3. every retained action that is still `ISSUED` is inspected in deterministic `action_id` order;
4. each still-issued action whose issuance deadline is `<= t` is prepared for a lifecycle `TIMEOUT` transition at `t`;
5. all prepared replacements are committed only after preparation succeeds for the entire epoch;
6. supervisor time becomes `t`.

The resulting invariant is:

```text
After successful advance(t):
  no supervised open action has deadline <= t
```

Actions whose deadlines are later than `t` remain `ISSUED` and retained.

The supplied epoch provenance is recorded on every timeout generated by that epoch. If no action times out, the current implementation does not persist a separate epoch trace event; it only advances the supervisor's monotonic processing time.

## Ordering of competing terminal events

The supervisor processes calls in explicit invocation order. Equal timestamps do not imply simultaneous mutation.

Consequently:

```text
record_outcome(a, t)
then advance(t)
  -> OUTCOME remains terminal

advance(t)
then record_outcome(a, t)
  -> TIMEOUT remains terminal
     later OUTCOME transition fails closed
```

The same principle applies when an outcome arrives after the nominal deadline but before a timeout transition has actually been processed. The current Action Lifecycle contract permits `OUTCOME` after issuance regardless of whether the deadline has passed; the deadline makes `TIMEOUT` eligible when supervision processes an epoch. This contract does not silently rewrite that existing lifecycle meaning.

If future environment semantics require event-time precedence independent of runtime processing order, that would be a separate contract change with an explicit event-order model.

## Atomicity and fail-closed behavior

Multi-action timeout processing must not partially commit one epoch.

The supervisor prepares all due lifecycle replacements before mutating retained state. If validation or a delegated lifecycle transition fails, the epoch fails without applying prepared replacements and without advancing supervisor time.

Examples of explicit failures include:

- malformed or backward supervisor time;
- malformed epoch provenance;
- non-lifecycle issuance input;
- duplicate supervised action identity;
- unknown action identity;
- an underlying illegal Action Lifecycle transition.

## Relationship to the eventual-closure obligation

The runtime principle remains:

```text
ActionIssued(a)
  -> eventually Outcome(a) | Timeout(a) | Unknown(a)
```

This contract implements deterministic parts of that obligation for supervised actions:

- it exposes the earliest outstanding supervised deadline without requiring callers to inspect lifecycle event internals;
- if the runtime supplies an `advance` epoch at or after an open action's deadline, that action cannot remain supervised and overdue after the epoch succeeds.

It does **not** prove that a deployed runtime will eventually call `advance`, that a host clock will continue running, or that an event loop will remain live. A future runtime driver or scheduler responsibility must consume the scheduling seam and provide those decision epochs.

Therefore the current evidence supports **deadline discovery plus decision-epoch closure**, not autonomous wall-clock liveness.

## Deterministic verification obligations

Canonical pytest coverage must demonstrate at least:

- supervised issuance retains the issued lifecycle in the same successful operation;
- `next_deadline_ns` is `None` with no open action and otherwise equals the minimum open issuance deadline;
- terminal actions do not contribute to `next_deadline_ns`, and closure recomputes the value from remaining open state;
- reading `next_deadline_ns` does not mutate lifecycle or supervisor time;
- an overdue open deadline remains visible rather than being clamped to supervisor processing time;
- an epoch before a deadline leaves the action open;
- an epoch at or after a deadline closes due actions as `TIMEOUT`;
- one epoch closes only the actions that are due;
- outcome and unknown closure delegate to Action Lifecycle semantics;
- competing terminal transitions follow explicit processing order and terminality;
- supervisor processing time is monotonic and malformed time fails closed;
- duplicate and unknown identities fail explicitly;
- malformed epoch provenance fails even when no action is due;
- a failed multi-action epoch does not partially commit;
- supervised issue delegates authorization/transition legality to `ActionLifecycle`.

These are deterministic invariant facts only. They are not simulation results and do not prove autonomous scheduling, environment correctness, model quality, or physical execution.

## Non-goals

This contract intentionally does not define:

- a general Scheduler or Runtime Driver;
- wall-clock reads, timer threads, async loops, background workers, polling cadence, or autonomous epoch delivery;
- durable persistence or recovery after process restart;
- concurrent or multi-threaded mutation semantics;
- environment adapters, action transport, or command acknowledgement protocols;
- action payload schemas;
- authority-policy legitimacy beyond the existing Action Lifecycle seam;
- Current Intent, Skill, arbitration, viability, cognition, LLM, simulator, GPU, or device integration;
- package distribution or supported Python/dependency floors;
- simulation, model-quality, device, or physical qualification.

Those responsibilities should acquire owners only when current implementation requires them.
