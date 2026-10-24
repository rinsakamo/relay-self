# W4 S49 DEV native reader lease — offline implementation

Authority: SelfWorld #633 / Draft #634, SelfBody #632, S integration #537,
Physical Control #627, Adaptive Cognition #426, S18 freeze #354, R #575.
Design baseline: [owner lease audit](selfworld-w4-s49-owner-lease-audit.md).
Start remote subject: `7dec3aa0b72a351bd254c7ac51decb63437fb343`.
LocalCodex implementation ancestor: `0a46a4107ece338891f36a3cb85dabb82c88cadf`.

This document describes DEV offline engineering. No live route is installed.
`W4_S49_ORIGINAL_OWNER_LIVE_LEASE_UNDETERMINED` and
`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` remain mandatory.
The final commit, exact-head CI results, local results and readback-confirmed
GitHub report are recorded on existing PR #634 and Issue #633. An engineering
PASS is conditional on all those final checks; this document alone grants none.

## Implementation and actual asyncio boundary

`adapters/mineflayer/self_world_stage_w4_lease.py` adds a genuine
`MineflayerProcessSession` subclass. It inherits the original `launch()` and
calls the original `receive()` for every native read. The same original stream
decoder validates session, sequence and native schema; a thin decoder guard
also rejects a JSONL fragment without its terminating newline. No second
stdout reader, task factory, global patch, lock waiter or ContextVar exists.

The local CPython 3.12.3 `wait_for()` uses `asyncio.timeout` and directly awaits
its coroutine for positive timeouts. CPython 3.11.17 creates child Tasks.
Tests therefore execute the **same original paths on both versions**. On 3.11
startup/spawn have different issuing and reading Tasks, and the four original
S16 `_receive_until()` calls have distinct child readers. On 3.12 inline await
is also legal. A wait_for call by itself is not claimed as proof of a Task switch.

The owner capability belongs to one session instance and its constructing Task.
An immutable `ReadOperation` binds session identity, increasing epoch, phase and
operation/request/action binding. `receive()` is deliberately a synchronous
coroutine factory: authorization occurs at CALL time, before scheduling; it
reserves the sole pending read and returns a one-use coroutine. That coroutine
may execute in its issuer or as the **exact root coroutine** of an explicitly
created child Task. A foreign Task invoking receive, or wrapping/stealing a
capability in another coroutine, is rejected before original receive is called.
A copied ContextVar conveys no permission. Python's coroutine single-use rule
and exact operation object identity prevent reuse across epochs.

`delegate(owner, operation, invoke)` separately reserves and hands off an
operation to its exact coroutine Task. The old actor cannot read during the
handoff. Nested delegation is explicit and stack-scoped: the HOST loop delegates
the **original** `NativeObservationOnly.receive()` using
`W4DevNativeObservationPort`; the reprobe callback similarly delegates the
**original** `_correlated_observe()`. This port does not replace the session
passed to S16: `isinstance(session, MineflayerProcessSession)` still succeeds.
There is no implicit permission for arbitrary descendants of a legitimate Task.
The original host's `asyncio.wait_for(host.run_session(...), 95)` is exercised
with this explicit DEV outer wrapper, not claimed to be wired into `qualify()`.

## Ordered owner handoffs and accounting

Implemented local phases:

`STARTUP → PREWORLD → WORLD_WINDOW → HOST ↔ ACTION_READ → QUIESCE → SHUTDOWN → CLOSED`.

Construction opens STARTUP for inherited launch. Original `_await_spawn()` must
consume spawn before PREWORLD. `capture_preworld()` uses the unchanged
`W4PrehostOwnerBridge` on this very session and owner capability. It binds the
explicit probe request, retains every interleaved frame, and obtains source-bound
native yaw/pitch via the unchanged preprobe/owner gate. Captured frames are
transferred once as `PREWORLD_EVIDENCE_ONLY_NOT_L0_STIMULUS`. WORLD_WINDOW is
unavailable until that ledger transfer; no native read is allowed in the window.
The unchanged handoff gate must accept the existing collector's marker content
before HOST can open. A separate integration fixture uses original
`_ready_server()`'s collector, `_command()` and logtap with fake Java pipes.
No real server process or World staging happens.

Typed immutable `ReadAudit` records include session ID, epoch, phase, binding,
issuing/reading Task references, decoded/delivered sequence and terminal reason.
References are per-session monotonically assigned labels with retained local
Task references, so recycled Python object IDs do not masquerade as one Task.
`DECODED` is recorded before rejection; `DELIVER` only after authority checks.
A frame decoded while cancellation is being suppressed remains accounted but
is never delivered to L0. The original decoder/raw capture remains the only
native byte-reading route. Fixture transport read counts prove rejected readers
did not consume bytes. Malformed/partial frames are terminal, not valid evidence.

A pending or active receive prevents phase change. Host delegation must return
before QUIESCE. Cancel/timeout, malformed stream, foreign terminal frame or
unexpected EOF permanently latch BLOCKED. Tests include a transport that ignores
cancellation: it cannot hand off while unfinished, and cannot deliver after it
finally returns. No stale task or old epoch is revived. BLOCKED has no recovery
transition; terminate delegates to original process cleanup and also latches BLOCKED.

Without raw capture, DEV shutdown calls original `shutdown()`. The base capture
shutdown contains a private `until_eof()` coroutine with no delegation seam, so
**only the DEV subclass's capture shutdown** performs an explicit delegated
EOF-drain through the original receive, then the original process wait/seal/
termination primitives. EOF is accepted only in SHUTDOWN; nonzero exit or timeout
blocks and terminates. CLOSED additionally requires actual successful shutdown;
a caller cannot replace process wait with a phase label. The default base
shutdown implementation is byte-identical.

## Action and S18 boundary

The lease creates no grant, Intent, Skill, ActionSupervisor, issued Action,
OUTCOME, S10 commit or learning owner. ACTION_READ can reference an **existing**
original supervisor; allowed S15 backward/clear writes require its current
ISSUED snapshot and exact action/cleanup identity. Other World commands fail
closed. The actual normal executor still validates independent L0, PROPOSE and
ISSUE grants and performs issuance itself. The integration test supplies explicit
**fixture** grants outside the lease, invokes original S14 binding/admission,
original `NormalSessionActionExecutor.execute()` and original S15/S16 collection,
interpretation and closure. Missing PROPOSE/ISSUE rejects before Action writes.
The fixture S16 OUTCOME is not real World evidence. Host retained S10 identity
stays unchanged throughout that integration.

No semantic owner moves: PersistentCognition, IntentCommitment, SkillExecution,
ActionLifecycle, ActionSupervisor, LearningPreferenceState and HabitRepertoire
remain original. S18's deterministic transaction/explicit learning/STOP regression
is run unchanged. Its own historical synthetic learning fixture is not a live
S10 write by this DEV lease. No default R/V or original S49 imports this module.
The original startup environment opt-in tests and default-route identity checks
remain in regression.

Rejected alternatives: lifetime Task ID pin (breaks 3.11 wait_for); ContextVar
inheritance (permits unauthorized descendants); Lock-only serialization (queues
unauthorized readers); session proxy (fails original executor type check);
global asyncio task factory/monkeypatch (changes default semantics); frozen
original-source edits (not needed). Explicit wrappers are required in the DEV
composition; they are not an automatically installed live interception layer.

## Test matrix and claim ceiling

The new test module exercises these required categories without reducing any
existing tests:

| Category | Actual test route / expected result |
| --- | --- |
| startup / host / S16 wait_for | inherited launch + original spawn; original host/filter/reprobe; original normal executor and four S16 receive-until stages; both Python versions |
| competing / foreign / copied context | reservation and actor checks; zero additional transport reads |
| old epoch / token replay / foreign session | stale or foreign operation object and owner capability; decoder session rejection |
| Action before HOST / PREWORLD extra reader / WORLD_WINDOW read | illegal phase or foreign actor rejected before read |
| stale/foreign request | exact request binding, duplicate pending request rejection and preworld source rejection |
| unsolicited accounting / bad classification | original complete ledger + gap/kind failures; no preworld replay to host |
| cancel / timeout / stale child | reader and host tests, plus cancellation-resistant transport; no surviving read authority |
| partial / malformed / EOF / Node exit | decoder framing and terminal latch; no delivery of invalid frames |
| shutdown order / close reopen | active reader, delegated host, forged close, timeout, nonzero exit, closed reopen all reject |
| missing Action authority | lease-only command send and original executor missing-PROPOSE/ISSUE negatives |
| default S49 / R/V / S18 | original blob identity, base-class and default import identity, startup opt-in regressions, unmodified freeze suite |

This is cooperative in-process Python exclusion. It does not secure private
attributes from hostile code, prove OS custody or authenticate Mineflayer TCP.
Unscheduled abandoned capabilities keep the reservation occupied and prevent
handoff; they are not automatically reclaimed or silently reused. No daemon,
cognitive scheduler, retained World state, second Action owner or retry is added.

Final successful offline tests plus exact-head CI may support only
`W4_S49_DEV_LEASE_OFFLINE_ENGINEERING_PASS`.
Original `_new_session()` still launches the base class and `qualify()` still
uses its original route: **live owner integration remains UNDETERMINED**.
External custody, native source attestation, independent issuer, pre-acquisition
pin and global monotonic spend-once remain unqualified. Physical execution,
QUALIFICATION, SCIENCE and main/Draft merge remain prohibited in this task.

Next minimum work: review this exact DEV composition and its explicit wrapper
seams for a separately authorized original-owner opt-in. It does not itself
satisfy the independent trust/placement gates or authorize a live run.

## Protected originals — before/after Git blob SHA

All entries are measured against start remote HEAD; the new freeze regression
also checks these literal blobs. No protected source or frozen test was edited.

| Protected path | Before = after Git blob SHA |
| --- | --- |
| `adapters/mineflayer/s49_normal_session_real_ci.py` | `fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258` |
| `adapters/mineflayer/s34_native_world_cognition_ci.py` | `eaecb117ad26059d6d2abb2c12bca61b2dce1f01` |
| `adapters/mineflayer/s31a_real_server_ci.py` | `7ee3e95af66e1b981f72509a3dd661d79ef95744` |
| `adapters/mineflayer/process_session.py` | `6eec8f80621c581d47154f7c76e72303e00c04f0` |
| `adapters/mineflayer/normal_action.py` | `0ded8fa296c92076a643de08cd6fc360061e1d08` |
| `adapters/mineflayer/execution.py` | `2af25bc6808f8a4199fe2ee500d1c1dfbea25de2` |
| `adapters/mineflayer/action_outcome.py` | `502a14304c8ab9f5e37bff4a054cf2a21730d294` |
| `src/relay_self/intent.py` | `f4ef9500cd7941e5e9e07fd41ac2b6e4b4d5ac25` |
| `src/relay_self/skill.py` | `61885956810b4125721f685d449b361262b71120` |
| `src/relay_self/action.py` | `869e761cfa2646f48f12e5e8088375ae64f04607` |
| `src/relay_self/action_supervision.py` | `3320caab19d05afa74f046e3e0f143bc1aad5821` |
| `src/relay_self/learning.py` | `9fd949e94e91ded1c070d359378833f354fba577` |
| `src/relay_self/habit.py` | `edc8904753421ef836843ae736f194f5a3a39168` |
| `src/relay_self/action_feedback.py` | `8ae84e2e555550128a59a23c342f67a032a0c859` |
| `src/relay_self/action_outcome.py` | `d28bbc1745104bcd7872061bef2fe6222ceccb2a` |
| `docs/postmain-architecture.json` | `e8419c55b5535d451346fd2a9a3c42326a80aa29` |
| `docs/postmain-architecture.md` | `62b8e807d1b35a7f06d15b61e411434f57fe111d` |
| `tests/test_postmain_architecture_freeze.py` | `d343aa052541b4ee9d2ce3e00653cc1a56d681ce` |
| `src/relay_self/persistent_cognition.py` | `5d4fff3fa10bad78f98118758c8a22d53e8390fb` |
