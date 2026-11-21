# P0-D #860 — Bounded CoordinatedCheckpointHost (stage 10 DEV)

Stack: #869 → #868 → #867 → #866 → #865 → #864 → #863 → #862 → #861 → #859. This is a host orchestration / contract slice, NOT a real Paper 1.21.8 trial, autonomous two-Self world launch or qualified crash recovery.

## Goal and sequence

1. Reuse the shared strict PhysicalIssueAdmission for all registered Self IDs/current native sessions and scoped EAT/ATTACK/STOP leases.
2. Run prepare_stop_before_autosave for the full A/B cohort: exact-session native STOP ACK, initial 8-tick settling and next >=8-tick 3D stable displacement <=0.06m, fsynced STOP preissue/verified evidence, fail-closed on any missing B.
3. Immediately call the existing synchronous CognitionOwnerCohort freeze, typed World+all-Self generation capture, and owned Paper stop/save/restart/rebind via CoordinatedAutosaveRuntime. No awaited operation separates validated STOP from the synchronous committed cut.
4. Reopen physical issues only after the original runtime rebinds every registered Self to new native sessions. The next checkpoint is due 60 monotonic seconds after the prior verified generation. No historical replay.

## Implementation

- src/relay_self/coordinated_checkpoint_host_dev.py: explicit cycle_if_due(now) and foreground awaited run_bounded(max_cycles=N). No unattended background daemon or new native Action issuer.
- Requires CoordinatedAutosaveRuntime(strict_typed_owner_cut=True), the SAME CognitionOwnerCohort instance that owns runtime.admission.close/release, one shared PhysicalIssueAdmission(require_neutral_stop=True), exact full Self roster, and fresh native session provider. It also checks each cognition owner's new WorldBody observation has been obtained before another checkpoint.
- Optional owned_paper parameter rejects an absent/uncertain/unowned process or mismatched World/branch, and requires the new owned process session after every successful cut. Never attaches to another Paper PID/port.
- If due and any preflight, STOP, capture, rebind or readback fails, host physically HOLDs for operator review. This is an admission fence, not proof an already-active external Action stopped.
- First pulse produces initial generation at t=0, then subsequent generations at t>=60 seconds; non-due polls do not issue STOP.

## Offline test evidence

- Actual existing A/B mutable cognition owners and typed generation, plus an actual Python subprocess only emulating Paper console (not Minecraft), and synthesized typed Mineflayer STOP readback.
- Two successful simulated 60s generations t=0 and t=60 with t=30 no STOP, owned subprocess stop/restart twice, A/B rebind + new WorldBody observation, verified full A/B generation each time.
- Missing B, stale/unobserved new native Self session, or B body perpetually drifting: HOLD before any partial World save/COMMIT; previous full generation remains available.

## Real-world and qualification blockers

1. Live native participant provider/rejoin still comes from unqualified external callbacks; no real Paper 1.21.8 tick readback, real two Self actor processes, or real elapsed 60s continuous loop was run.
2. The actual native Mineflayer bridge and legacy S49/L0 direct effects are not globally inventoried/fenced; Python-only gate is not a distributed authority. No independent proof of obsolete GPU/transport cancellation.
3. STOP audit is separate from canonical physical Action WAL. Full Goal graphs, Skill IR and Log Memory owners still need semantic persistence/rebind. No actual crash/rollback qualification.
4. All failures/unknown native effects must HOLD; do not automatically replay old actions, infer old UUIDs, or promote partial generations.

Policy: 60-second synchronized full World + every-Self autosave, small stop/save skew accepted, discard checkpoint-intermediate histories, no replay.

Classification after exact HEAD green CI: EXPLICIT_TWO_SELF_HOST_PULSE_OFFLINE_DEV_PASS / LIVE_NATIVE_SESSIONS_NOT_ATTESTED / REAL_PAPER_60S_AUTOSAVE_NOT_RUN / REAL_TWO_SELF_CRASH_ROLLBACK_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN.


## Stage 14: asynchronous native A/B rejoin seam (offline DEV)

The baseline runtime's rebind callbacks are synchronous, but the actual
`MineflayerProcessSession.launch` and process shutdown are asynchronous.
`CoordinatedAutosaveRuntime.run_if_due_async` now reuses the exact same
STOP/freeze/World-stop/save/capture/World-restart cut and awaits a bounded,
external `prepare_rejoin(self_id, new_paper_session, old_native_session)`
callback **while all admission gates remain closed**. Only after the entire
roster's returned native session identities match each corresponding existing
Self-owner rebind receipt does it release the original admission gate and advance
the 60s success timer.

`CoordinatedCheckpointHost` passes this optional preparer through while
keeping the original synchronous fake-process tests intact. Missing B,
unmatched native session IDs, exceptions, and cancellation all HOLD with
no automatic retry/replay. A COMMITTED generation may exist after a rejoin
failure; this is inert durable state and **not a physically resumed World**.
The preparer has no independent physical authority and must eventually be
backed by verified Mineflayer bridge processes, WorldBody readbacks, and real
GPU/transport disposal. All new tests use fake callbacks, not live Paper or A/B.

The async preparer is awaited for at most 15 seconds per Self by default
(configurable bounded 0..180 seconds). Timeout poisons the runtime; it is not a
retry signal. The local callback cannot by itself attest native source,
actual GPU task completion, or cancelled external transport work.
