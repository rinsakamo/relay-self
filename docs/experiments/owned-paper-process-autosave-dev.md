# P0-D #860 — Owned Paper subprocess adapter (stage 3 DEV)

Base: P0-D runtime barrier Draft PR #862. This change is opt-in for a disposable server launched by the test host itself. It is not real Paper 1.21.8 qualification, live two-Self recovery, or an unattended daemon.

## Implemented

- src/relay_self/owned_paper_world_dev.py provides OwnedPaperWorld. It writes save-all flush / stop only to the stdin of a process started via its own subprocess.Popen handle; it never scans a port or attaches to an arbitrary PID.
- Requires an explicit executable and existing World/server/evidence directories. Startup waits for a per-session readiness marker in a unique log file. Timeout means uncertain; no blind kill, retry, or foreign process takeover.
- stop_and_save requires a session-scoped PaperTickReceipt supplied by the caller, sends save-all flush then stop, waits for clean exit, checks log save/stop markers and a World file. This is process/log DEV evidence; it does not attest complete atomic World/WAL state or authentication of the readback provider.
- A restart creates a fresh owned process/session. The resulting receipt can be directly passed to the WorldRuntimeHooks of PR #862.
- tests/test_owned_paper_world_dev.py launches real local Python subprocesses that simulate console messages (not Minecraft). Cases include start-stop-restart, missing save log refusal, duplicate process refusal, wrong tick session, and integrated A+B synthetic Self file checkpoint with two simulated 60s epochs and no-replay rollback.
- No second Action issuer or new Self owner. The existing generation integrity checks are reused.

## Required live DEV work

1. Use a disposable Paper 1.21.8 server actually launched and owned by the local test runner, never another user's already-running server. Keep real-world execution separately authorized.
2. Implement genuine server-qualified tick readback from a Paper-owned observer (main thread or proven source). The current receipt provider is an external callback, not a built-in Paper tick query.
3. Verify clean save/stop semantics and coverage of all dimensions for the exact Paper version. The all_dimensions_saved field currently means clean subprocess exit plus configured log markers, not cryptographic atomicity or full World event coverage.
4. Connect actual admission fences, full Self A/B freeze/flush and rebind including Goal, Intent, Skill, Structured/Log Memory, pending messages, world and native sessions. Current Self files in the integration test are synthetic/opaque.
5. Run at least two real 60-second cycles, crash between checkpoints, restore the last complete generation into a new World branch, and verify both actual Self histories and World roll back with no Action replay.
6. Report exact HEAD, real process logs, server tick receipts, World archive hashes, roster, new sessions, and failure modes. Preserve source evidence; no automatic resume after HOLD.

## Classification

OWNED_PAPER_PROCESS_ADAPTER_OFFLINE_DEV_PASS (only after exact-HEAD CI), REAL_PAPER_AUTOSAVE_NOT_RUN, REAL_TWO_SELF_OWNER_RECOVERY_NOT_RUN, QUAL_NO_GO, SCIENCE_NOT_RUN.

Policy remains: 60-second interval; small save-time skew allowed; all post-checkpoint histories discarded; no replay or UUID reconciliation.
