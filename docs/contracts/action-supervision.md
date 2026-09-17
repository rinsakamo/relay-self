# Action Supervision Contract

## Purpose

This document owns the executable runtime semantics for deterministic supervision of in-flight primitive actions across explicit runtime decision epochs.

It builds on [`action-lifecycle.md`](action-lifecycle.md), which remains the sole owner of legal Action Lifecycle transitions and same-root Action snapshot-lineage currentness. It refines the runtime-level closure obligation from `docs/runtime-principles.md` without claiming that a pure state machine can advance time or schedule itself.

The executable owner is `src/relay_self/action_supervision.py`; deterministic verification lives in `tests/test_action_supervision.py`.

## Grand Null result

The existing `ActionLifecycle` owns proposal, authorization, issuance, deadline, terminal transition legality, and whether a snapshot is current within one supported Action lineage.

Adding an "automatic timeout" method to that lifecycle would not create liveness: the method would still need an external caller. Embedding a wall clock, timer thread, or background loop inside the lifecycle would collapse lifecycle semantics with runtime scheduling.

A general Scheduler is also not yet justified.

The smallest independent responsibility remains **Action Supervision**:

> retain actions issued through the supervision boundary and deterministically process them when explicit monotonic runtime events or decision epochs arrive.

A future runtime driver also should not need to inspect Action Lifecycle event storage to discover when supervision next requires deadline processing. The supervisor therefore owns a derived next-deadline query for its retained open actions; this does not make the supervisor a clock or scheduler.

## Boundary

For actions managed by this boundary:

```text
current AUTHORIZED ActionLifecycle snapshot
  -> supervised issue
     -> current ISSUED snapshot retained by supervisor
        -> record outcome -> OUTCOME
        -> mark unresolved -> UNKNOWN
        -> advance epoch at/after deadline -> TIMEOUT
```

The supervisor does not reimplement lifecycle legality or lineage currentness. It delegates to Action Lifecycle operations.

`ActionLifecycle.issue` remains a valid lower-level transition API. The stronger retention, identity, batch-atomicity, and processing guarantees in this contract apply only to actions issued and later closed through `ActionSupervisor`.

## Supervised issuance and identity

`ActionSupervisor.issue(...)` accepts an `ActionLifecycle` and delegates issuance to the lifecycle owner.

Rules:

- the supplied lifecycle snapshot must be current in its same-root Action lineage;
- lifecycle issuance must itself be legal, including prior authorization;
- successful supervised issuance retains the exact issued snapshot under its `action_id` in the same operation;
- a stale authorized predecessor fails closed rather than being issued again;
- failed issuance does not register the action or advance supervisor time;
- an `action_id` may be supervised only once during one supervisor lifetime;
- terminal lifecycles remain retained so an identifier cannot silently be reused and so the final causal lifecycle remains inspectable;
- lookup of an unknown or malformed supervised identity fails explicitly.

This retained in-memory mapping is the current bounded runtime mechanism. It is not a durable event store, a global `action_id` registry, or a persistence contract.

### Retained snapshot currentness

The supervisor retains the Action snapshot it accepted or produced. Supported supervisor operations expect that retained snapshot to remain current in its Action lineage.

If a caller independently advances a retained snapshot through the lower-level Action Lifecycle API instead of the supervisor, the supervisor does **not** silently discover or adopt that external sibling. A later supervisor transition using its retained stale predecessor fails closed.

Therefore:

```text
supervised Action closure
  -> use ActionSupervisor.record_outcome / mark_unknown / advance
```

when the stronger supervision guarantees are required.

This is not a new ownership rule for all Action Lifecycle values. It is the consequence of combining immutable snapshot lineage with a supervisor that retains one explicit snapshot.

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

`next_deadline_ns` exposes the earliest outstanding issuance deadline among the supervisor's locally retained `ISSUED` snapshots.

The value is derived on read. It is not stored as a second mutable scheduling truth.

```text
if open supervised actions exist:
  next_deadline_ns = minimum issuance deadline among open actions
else:
  next_deadline_ns = None
```

Consequences:

- terminal retained lifecycles do not contribute;
- action identifier ordering does not affect the result;
- closing or timing out the earliest action exposes the next remaining deadline;
- reading the property does not advance supervisor time or mutate a lifecycle;
- an overdue obligation is reported unchanged rather than clamped away.

A stale retained snapshot may still locally display `ISSUED`; deadline discovery is therefore a view of supervisor-retained state, not proof that no external lower-level sibling snapshot exists. Supported supervisor mutation will detect such staleness and fail closed.

## Outcome and unknown closure

`record_outcome(...)` and `mark_unknown(...)` resolve one supervised action through existing Action Lifecycle transition methods.

Therefore:

- only a retained current snapshot that is legally closable by that lifecycle transition may close;
- provenance validation, lineage currentness, and terminality remain enforced by Action Lifecycle;
- a stale retained snapshot fails closed;
- a terminal action cannot be reopened;
- failed closure does not replace the retained lifecycle or advance supervisor time.

## Decision epochs and timeout closure

`advance(at_ns=..., provenance=...)` is the deterministic decision-epoch operation.

For one successful advance to time `t`:

1. supervisor time is validated as monotonic;
2. epoch provenance must be a valid `Provenance` value;
3. every locally retained action that still displays `ISSUED` is inspected in deterministic `action_id` order;
4. each due Action Lifecycle timeout snapshot is **prepared without advancing its lineage head**;
5. preparation must succeed for every due action, including stale-snapshot and lifecycle validation;
6. only after all due replacements are prepared are their lineage revisions committed;
7. all committed replacement snapshots are installed in supervisor retention;
8. supervisor time becomes `t`.

The resulting invariant is:

```text
After successful advance(t):
  no supervised open action has deadline <= t
```

Actions whose deadlines are later than `t` remain retained and open.

The supplied epoch provenance is recorded on every timeout generated by that epoch. If no action times out, the current implementation does not persist a separate epoch trace event; it only advances supervisor processing time.

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

The current Action Lifecycle contract permits `OUTCOME` after issuance regardless of whether the deadline has passed; the deadline makes `TIMEOUT` eligible when supervision processes an epoch. This contract does not silently rewrite that meaning.

If future environment semantics require event-time precedence independent of runtime processing order, that would be a separate contract change with an explicit event-order model.

## Atomicity and fail-closed behavior

Multi-action timeout processing must not partially commit one epoch.

The supervisor therefore separates **preparation** from **lineage commit** for due timeout transitions. Preparing an immutable replacement validates the Action transition but does not advance the current lineage revision. Only after every due replacement has prepared successfully are lineage heads and retained mappings advanced.

This matters for stale snapshots as well as malformed input. For example, if one due retained action has been independently advanced outside the supervisor and is now stale, `advance(...)` fails before another prepared due action consumes its lineage head.

Examples of explicit failures include:

- malformed or backward supervisor time;
- malformed epoch provenance;
- non-lifecycle issuance input;
- duplicate supervised action identity;
- unknown action identity;
- a stale retained Action snapshot;
- an underlying illegal Action Lifecycle transition.

A failed epoch does not apply prepared replacements and does not advance supervisor time.

The contract does not claim transactional behavior under concurrent multi-threaded mutation; concurrency remains a non-goal.

## Relationship to the eventual-closure obligation

The runtime principle remains:

```text
ActionIssued(a)
  -> eventually Outcome(a) | Timeout(a) | Unknown(a)
```

This contract implements deterministic parts of that obligation for supervised actions:

- it exposes the earliest outstanding locally retained supervised deadline;
- if the runtime supplies an `advance` epoch at or after an open action's deadline and all retained due snapshots are current/valid, that action cannot remain supervised and overdue after the epoch succeeds.

It does **not** prove that a deployed runtime will eventually call `advance`, that a host clock will continue running, or that an event loop will remain live. A future runtime driver or scheduler responsibility must consume the scheduling seam and provide those decision epochs.

## Deterministic verification obligations

Canonical pytest coverage must demonstrate at least:

- supervised issuance retains the issued lifecycle in the same successful operation;
- stale authorized predecessor snapshots are rejected by supervised issuance;
- `next_deadline_ns` is `None` with no open action and otherwise equals the minimum locally retained open issuance deadline;
- terminal retained lifecycles do not contribute to `next_deadline_ns`;
- reading `next_deadline_ns` does not mutate lifecycle or supervisor time;
- an overdue open deadline remains visible rather than being clamped;
- an epoch before a deadline leaves the action open;
- an epoch at or after a deadline closes due actions as `TIMEOUT`;
- one epoch closes only the actions that are due;
- outcome and unknown closure delegate to Action Lifecycle semantics;
- competing terminal transitions follow explicit processing order and terminality;
- supervisor processing time is monotonic and malformed time fails closed;
- duplicate and unknown identities fail explicitly;
- malformed epoch provenance fails even when no action is due;
- a failed multi-action epoch does not partially commit retained snapshots or consume prepared Action lineage heads;
- a stale due retained snapshot causes the epoch to fail without consuming another due action's current lineage;
- supervised issue delegates authorization, lineage-currentness, and transition legality to `ActionLifecycle`.

These are deterministic invariant facts only. They are not simulation results and do not prove autonomous scheduling, global Action identity uniqueness, durable lineage retention, concurrent linearizability, environment correctness, model quality, or physical execution.

## Non-goals

This contract intentionally does not define:

- a general Scheduler or Runtime Driver;
- wall-clock reads, timer threads, async loops, background workers, polling cadence, or autonomous epoch delivery;
- global `action_id` uniqueness across independent Action roots or supervisors;
- durable persistence or recovery after process restart;
- concurrent or multi-threaded mutation semantics;
- automatic reconciliation of lower-level Action snapshots advanced outside the supervisor;
- environment adapters, action transport, or command acknowledgement protocols;
- action payload schemas;
- authority-policy legitimacy beyond the existing Action Lifecycle seam;
- Current Intent, Skill, arbitration, viability, cognition, LLM, simulator, GPU, or device integration;
- package distribution or supported Python/dependency floors;
- simulation, model-quality, device, or physical qualification.

Those responsibilities should acquire owners only when current implementation requires them.
