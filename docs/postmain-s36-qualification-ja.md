# RelaySelf S36 — bounded event-triggered cognition scheduler (Action authority excluded)

## Frozen authority
S35 Draft PR #372, exact HEAD `37965b61932930039360f09d5991c552c4229dfd`.
No changes to frozen S18–S35 artifacts or RelayTheory R6 / Paper2 MAIN40.
User chose to skip local WSL2 S31-B; no independent LocalCodex result claimed.
This is a **prospective** description; actual qualification only from CI dynamic `S36_REPORT`.

## What was missing in S35?
S35 received genuine unsolicited Mineflayer `entitySpawn` and manually called
existing native S34 cognition after a separate grant. S36 instead provides a
scheduler callback `BoundedEventCognitionScheduler.on_native_event` that
automatically converts a single admitted event into **one bounded cognitive
execution**, without an explicit cognition method call from the event consumer.

The new scheduler does **not** import ActionSupervisor, S15 or any Action
propose/authorize/issue API. A control plan may return `MOVE_AWAY/ADMITTED`;
that does not confer authorization to emit Minecraft commands.

## Qualified causal path
```text
real Minecraft server privileged /summon -> Mineflayer entitySpawn
    -> unchanged bridge emits unsolicited observation(kind=entities)
    -> host event loop feeds event to S36 on_native_event
    -> source-native candidate queue (coalesce/age/capacity/priority/fairness)
    -> scheduler automatically executes configured native re-probe
    -> separate externally supplied event-bound cognition-only grant
    -> existing S35 EventCognitionLedger admits ticket ONCE
    -> scheduler invokes frozen S34 ATT/BLF/CNC/PRD/PLAN/ROUTE/ADMISSION
    -> MOVE_AWAY / ADMITTED (no model call)
    -> no Action proposed / authorized / issued / physically performed
```

Real CI uses official Mojang Minecraft Java Edition 1.21.8, Mineflayer 4.39.0,
Java21, Node22, the frozen production bridge and a disposable loopback server.
The native `entities` event **must arrive without a prior observe command**.
The scheduler's separate real correlated probe must have a newer seq, same
session and exact original zombie ID, <4m geometry and complete entity registry.

The exact `EventCognitionTriggerGrant` is issued by an **independently
configured caller-supplied policy factory**, not fabricated by the scheduler
or embedded in the event. There is no Action-specific admission in S36.

## Resource and fairness policy — fixed prospective values

- `max_pending=4` — no evictions to admit unbounded work; saturation refuses.
- `max_epochs_per_batch=2` — strict bounded work attempts per callback.
- `max_total_cognition=2` — lifetime per in-memory scheduler budget.
- `max_event_age_seq=16` — only comparable seq within a session; no cross-
  session timestamp comparisons; stale pending event expires.
- `max_urgent_burst=2` — urgent distance <=2.5m gets priority, but a waiting
  farther event is served after at most two consecutive urgent attempts.
  FIFO within band; fairness conditional on continued caller event dispatch.
- `per_probe_timeout_s=10` — hard bound on the async source re-probe wait;
  timeout raises (FAIL), never counted as successful cognition.
- Newer events coalesce per **session+entity** and carry their new native seq;
  zombie disappearance/distance outside 4m invalidates older pending events.
- `EventCognitionLedger` retains one-shot rejection; stale exact event is
  ignored and cannot repeat cognition.

**Important:** This scheduler does not preempt arbitrarily expensive injected
synchronous cognition CPU work, and it is not a system-wide rate limiter.
The bounded counts/probe timeout apply in this serial, caller-owned process.
No pretense of durable exactly-once, interprocess/concurrent admission,
authenticated world clock or full real-time fairness.

## Test separation

**Live genuine World**: one unsolicited event -> automatic cognitional ticket ->
separate real correlated probe -> frozen deterministic policy -> MOVE_AWAY/
ADMITTED, zero Action owners, replay rejected, process shutdown exit0.

**Offline deterministic negative controls**: capacity overflow, same-target
coalescing, target loss invalidation, stale and out-of-order session seq,
urgent priority with guaranteed low-priority selection after two urgent
attempts, per-batch and global cognitive quotas, deadline timeout, denied
independent grant/wrong session/wrong target/old probe, valid rev1 ancestor
proof, zero Action owner.

The offline queue fairness tests are **not** claimed as independent
Minecraft-generated event workloads. Retained rev1 comes from frozen S19
governed *synthetic* FakeSession ancestry; no actual S36 learning.

## PASS/BLOCKED/FAIL
- Official server or dependencies unavailable → BLOCKED.
- Event absent/unqualified, wrong native correlation, bad authority, failed
  automatic bounded cognitive callback, new Action, or unclean teardown → FAIL.
- Dynamic `S36_REPORT.status=PASS` plus both exact-head all-job CI successes
  is necessary for
  `REAL_EVENT_AUTO_BOUNDED_COGNITION_WITHOUT_ACTION_QUALIFIED`.
- Static plan `PENDING_CI` is never observational PASS.

## Hard nonclaims
This is an **event-driven cognition callback within a supervised test runner**,
not an indefinitely running autonomous daemon, independent decision engine,
open-world threat discovery, self-generated objective, general hazard observer,
or physical Action controller. No Action4, no LLM inference or new learning.
The scheduler grants **no** proposal/authorization/issue authority. No
independent source attestation. S31-B explicitly skipped. Paper2 MAIN40
untouched.

Keep all S36 changes on Draft stacked PR; no merge.
