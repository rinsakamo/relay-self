# P0-D #860 — Paper main-thread tick witness for owned-world checkpoints (stage 11 DEV)

Stack: #870 → #869 → #868 → #867 → #866 → #865 → #864 → #863 → #862 → #861 → #859. Preserve 60-second World+all-Self generations, discard post-generation history, **no replay**. This slice is a source-evidence prerequisite for a real Paper trial; it is **not** a completed real Paper autosave.

## Why

OwnedPaperWorld.stop_and_save had a caller-provided PaperTickReceipt callback. That callback could return arbitrary integers from Mineflayer time, a fake server or a stale host session. A clean Popen exit and text 'Saving worlds' are not independent evidence of Bukkit's main-thread tick. This stage adds a dedicated request-response path in an existing Paper plugin and a source log join.

## Paper plugin

- Extends existing experiments/p0b_paper_recorder's passive plugin with TickWitness.java, initialized from Recorder.onEnable without changing ATTACK ticket logic or issuing Minecraft Actions.
- On each Bukkit main-thread scheduler tick it processes strictly one-use nonce requests in the plugin's local p0d-ticks/requests spool, requiring a loaded World UUID and the supplied host-owned Paper session label. It writes an exclusive ACK (boot UUID, request nonce, Paper Bukkit.getCurrentTick(), source=PAPER_MAIN_THREAD, current World UUID and echoed session) then emits a P0D_TICK_ACK log on the same process; P0D_TICK_READY identifies this plugin boot.
- No native Action authorization, World mutation, save command or restart command is added. The spool is a DEV file bridge and lacks cryptographic authenticity.

## Python owned-process verification

- src/relay_self/paper_tick_witness_dev.py: PaperMainThreadTickReader is a synchronous, bounded callback for the existing OwnedPaperWorld(tick_readback=...) interface.
- Creates a fresh UUID request using exclusive O_NOFOLLOW, fsync file and directory; requires one matching ACK with exact typed keys, canonical UUIDs, World UUID, current owned Paper process session label, new plugin boot ID, canonical Paper tick and PAPER_MAIN_THREAD source.
- Independently reads only the **same owned Popen process log** through OwnedPaperWorld.read_owned_log(session_id), not a global server.log or a Mineflayer-reported tick. Requires matching P0D_TICK_READY for that boot **before** the exact P0D_TICK_ACK line. Accepts a boot once for each new process; rejects a reused boot across new Paper Popen sessions, any reused host session, foreign World/nonce, corrupt fields, symlinks, uncorrelated logs or timeouts.
- Returns the existing PaperTickReceipt with source_ref naming boot nonce and SHA256 digest of the ACK. OwnedPaperWorld now enters HOLD on tick-provider exception (the externally owned process is not forcibly killed) and does not issue save-all flush when the witness is absent.
- Existing Paper stop_and_save still requires clean exit, configured log markers and a World directory file. These are **not** proof that all dimensions or Self owners were atomically persisted.

## Offline tests and Java build

- tests/test_paper_tick_witness_dev.py: fresh matching ACK + owned-process log and many mismatched reply cases; real subprocess emulating Bukkit tick spool/readiness/save/stop across two new process boots. This subprocess is explicitly NOT Paper.
- Existing tests for wrong source tick callback must continue to reject, and full existing regression suite must remain green.
- .github/workflows/ci.yml adds a 5th CI job to compile the existing plugin with Java 21 and Maven from the **exact PR HEAD**, alongside existing Python tests/lint/contract and Node adapter checks. Java build only qualifies compile, not actual Paper 1.21.8 plugin runtime.

## Example wiring in an exclusively owned disposable World

Use a live Paper 1.21.8 server with plugin jar built and installed in its OWN server directory before start. Configure the matching World UUID from a separate server-world identity check; create `reader = PaperMainThreadTickReader(spool_dir=<owned_server>/plugins/P0BRecorder/p0d-ticks, expected_world_uuid=<uuid>, read_owned_log=lambda session: owned_paper.read_owned_log(session))`, and pass it to the same `OwnedPaperWorld(tick_readback=reader)` host. The Python side must not create spoof ACKs. Run only on a disposable authorized server, never attach to another active server. The filesystem bridge and owned process log must be preserved as DEV evidence.

## Remaining P0 before REAL DEV/QUAL

- Actually launch Paper 1.21.8 with this plugin on an owned disposable World and prove the ACK came from a Bukkit main-thread task by collecting the plugin jar hash, server log and raw ACK file. Test save-all flush/stop and full dimension coverage; the current Python fixture only mimics it.
- Authenticate and fence every live Self A/B Mineflayer session and stale GPU/transport events. Integrate per-Self STOP PREPARED/VERIFIED into the canonical Action journal, and finish missing Goal/Skill/Log Memory owners.
- Stage 10's explicit 60-second loop must still run with real elapsed time, live two-Self actors and WorldBody readback. Crash and restore must roll back the complete cohort without replay; no QUAL/SCIENCE promotion.

Expected classification after exact HEAD CI: PAPER_MAIN_THREAD_TICK_WITNESS_OFFLINE_DEV_PASS / REAL_PAPER_WITNESS_NOT_ATTESTED / REAL_LIVE_60S_AUTOSAVE_NOT_RUN / REAL_TWO_SELF_CRASH_ROLLBACK_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN.
