# S49 startup subprocess custody — isolated owner review (2026-10-21)

## Authority and isolation

- #392 original S49; #633 SelfWorld; #634 W4 Draft; #545 S Draft; #354 S18 freeze.
- Base branch `self/product-self-one-command-s49cleanup-20261021`, exact base `c8edb2d42ab31934feda5f30024e68eeb016e100`.
- This is an **isolated protected-source candidate**, not permission to adopt protected changes.
- No new World, real Java/Node, W4 live lease, S10 grant, QUALIFICATION, SCIENCE, or old grant replay is authorized by this patch.
- Invariants: sole local owner at spawn, atomic process handoff, supervised cancellation/reap, no second stdout receiver, no PASS with unresolved cleanup.

## Pre-fix code-path witnesses (static audit, not evidence of a completed injected run)

1. `process_session.py:launch`: `await asyncio.create_subprocess_exec` can be cancelled before assignment. After successful assignment, `except Exception` around constructor/initial `session.receive()` does not catch `CancelledError`; neither termination nor raw capture closure is assured.
2. `s34_native_world_cognition_ci.py:_new_session`: after `MineflayerProcessSession.launch` returns, a second `await _await_spawn(session)` can fail/cancel while S49 still has no session handle; this is another pre-handoff orphan boundary.
3. `s31a_real_server_ci.py:_ready_server`: process spawn happens before local return to original S49; only TimeoutError/S31ABlocked cleanup was installed. Cancellation during spawn/readiness, collector creation error or reader failure could escape with an unreturned live Java handle.
4. `s49_normal_session_real_ci.py:qualify`: existing cancellation-safe finalizer only owns server/session handles that were *already returned* by those helpers; an absent handle is not proof of process nonexistence.

## Candidate patch responsibility

- `adapters/mineflayer/startup_process_ownership.py`: small function-based custody/cleanup contract, one shielded spawn task supervised until completion and a confirmed-reap helper with bounded wait + kill fallback; no background process manager or stdout consumer.
- `adapters/mineflayer/process_session.py` **protected original**: Node launch uses new custody; constructor/receive/startup cancellation and post-adapter abort call one confirmed cleanup and W3 aborted seal.
- `adapters/mineflayer/s31a_real_server_ci.py` **protected original**: Java launch uses new custody; readiness failure/cancellation settles original collector after terminate/reap.
- `adapters/mineflayer/s34_native_world_cognition_ci.py` **protected original**: `_new_session()` owns the Node session through `_await_spawn`; on exception/cancel it aborts and reaps the session before returning failure. The existing `_await_spawn` evidence interpretation is unchanged.
- `adapters/mineflayer/s49_normal_session_real_ci.py` **protected original**: emit explicit `startup_cleanup_unconfirmed` in fail-closed report where a helper supplied a custody fault. Original finalizer order remains unchanged.
- `tests/test_s49_startup_ownership.py`: fake-only fault injection with process spawn, post-spawn handoff, Node constructor/startup, Java readiness/collector, double cancellation, signal/wait errors, no confirmed reap.
- `.github/workflows/self-demo.yml`: add exact paths and targeted pytest to existing jobs; **no protected expected SHA, guard, trigger, or S18 fixture change**.

## Review gates

- Frozen S49 original blob: `fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258`.
- Cleanup-isolated S49 candidate blob: `b0b96c798593f0621ac63076929cc4ab287812e7`.
- Additional protected source candidates must be reviewed individually and compared with their **base Git blobs** from `c8edb2d4`; the fixed-19 manifest and expected SHA must not be changed merely to green CI.
- Check Python 3.11/3.12 targeted + full pytest, real CI exact HEAD statuses, Node adapter, Ruff, W3 capture, original fake-port, repository contracts and original 19-blob guard.
- Any guard failure is **expected protection** only when independently matched to the protected source diff; unrelated failures remain functional defects.
- A candidate that passes startup tests remains `DEV_ONLY / PROTECTED_SOURCE_CHANGE_NO_GO / QUALIFICATION NO_GO / SCIENCE NOT_RUN`.
- W4 original owner live lease remains disabled until independent protected-owner exception + all S49 custody/capture/cleanup, W4 single receiver, no duplicate issuer, lease receipt and World grant checks are passed.

## External authenticity

Synthetic fake-process assertions prove local control flow only. They do not attest a native process's OS identity, external custody, a Minecraft World, a user grant or a scientific measurement.

## CI candidate branch

- Non-merging CI evaluation copy: `self/product-self-one-command-s49startup-20261021`; upstream review candidate `self/s49-startup-ownership-review-20261021`. The push trigger evaluates the existing offline matrix; it is **not** adoption or a source-protection exception.


## Independent follow-up audit — 2026-10-21 (audit branch)

- Read-only baseline: `self/product-self-one-command-s49startup-bounded-20261021` at `84154cbda6ea0d4cea90cf3245243cfa6f001f6b`.
- Audited candidate: `self/product-self-one-command-s49startup-audit-20261021` (inspect exact HEAD from CI; do not assume tests on earlier HEAD apply).
- Source review found **one actionable fail-closed defect**: when `spawn_with_custody()` was cancelled during subprocess creation, `terminate_and_reap()` could correctly raise `StartupCleanupUnconfirmed` while the process object already had an integer `returncode`. The cancellation was re-raised **without** `startup_cleanup_unconfirmed`, allowing S49 to lose the custody diagnosis. Exit code is not a successful waiter-settlement receipt.
- New code marks *every* failed reap during cancelled spawn as unconfirmed regardless of `returncode`; confirms `process.wait()` integer equals `process.returncode` rather than merely checking both are integers.
- Added fake-only negative controls for post-cancel reaping failure despite integer `returncode`, and inconsistent `wait()` vs `returncode`. Both preserve failure rather than fabricate a clean exit.
- Still unresolved by fake tests: whether Python subprocess creation can expose a native child if OS spawn stalls indefinitely before `Process` handoff; actual Java/Node host PID, signal/wait, stdout capture, W3 closure, cleanup under live WSL2 and OS identity require separate qualification. A still-uncooperative async waiter/collector may remain pending after fail-closed reporting; this is explicitly **NOT** complete cleanup proof.
- The only existing protected original changed in this follow-up is **none** (helper, tests and this document only); four protected originals in the inherited candidate (S49/S31A/S34/Node session) **still require independent owner exception**. Do not alter protected expected hashes or treat CI's guard refusal as a waiver.
- Qualified scientific / W4 owner lease claim remains **NO_GO** until exact-head matrix, independent owner review, native custody and live grant checks; neither this review nor fake tests authorizes World execution.
