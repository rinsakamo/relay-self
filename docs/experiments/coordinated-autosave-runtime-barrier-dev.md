# P0-D #860 — Runtime autosave barrier (stage 2, DEV)

This is a **hook-driven contract** after stage-1 generation bundling in PR #861. It is **not** a native Paper launcher, real 60-second unattended autosave, restored semantic Self owner, or Minecraft/Gemma evidence. It is stacked atop #861 and remains Draft.

## Decision

- 60 seconds between *successfully verified* generation commits, measured on the host monotonic clock.
- World plus **all** Self rollback together. No post-checkpoint causal replay, UUID reconstruction, or salvage of later Memory.
- Small save-time skew is acceptable. **No admission of new physical Action, cognition owner write, or unaccounted inter-Self message may cross the save cut.** This is a coarse quiescence boundary, not an atomic distributed World/WAL transaction.
- A save failure does **not** replace an older committed generation. A runtime failure during save/restart/rebind leaves the global admission gate closed. Operator intervention required; no automatic stale Action reissue.

## New runtime contract

Module: `src/relay_self/coordinated_autosave_runtime_dev.py`.

`CoordinatedAutosaveRuntime.run_if_due(now_monotonic)` performs the following **synchronously**, invoked from a host runtime polling loop:

1. Use `AutosaveGate` to test the 60-second policy. No internal background worker.
2. Call the runtime's **single global admission gate** to close *physical issue, cognition owner writes and message admission*. It must be real existing-owner fencing; the hook does not implement a gate.
3. Enumerate a fixed full Self roster. For every Self, require a freeze-and-flush receipt: no in-flight physical Action, no undelivered message, owner writes quiesced, physical issue blocked, plus files for PersistentCognition, physical WAL, and an owner-state file. An owner-state file is currently opaque and **insufficient to qualify full cognition**.
4. Call an **externally implemented** Paper stop-and-save hook. Require a clean exit code, all-dimensions-saved receipt, World and branch match.
5. Invoke the existing World+Self generation bundler; independently verify the completed generation marker and hashes.
6. Call an **externally implemented** restart hook for the *same source World*, requiring a different server session.
7. Ask every Self adapter to rebind, with new unique native sessions, old-session invalidation, cancelled/stale GPU outputs fenced, stale message queues discarded and physical issue **still blocked**.
8. Release the **single global gate** only after all participants report ready. This gate release is **not** a physical Action issue grant; existing ActionPort/WAL authorizations remain mandatory.
9. If any step fails, **hold** admission closed. The runtime cannot infer whether a partially executed stop/restart is safe. Previous committed generations remain eligible, and any partially created next generation remains ineligible.

An interrupted generation number is never reused. Do not delete an incomplete generation to make a retry look successful.

## Adapters and limitations

The callbacks are type-checked **external receipts**, not independent proof that Paper fully saved or Self truly quiesced. A real adapter must implement:
- Strict Paper process ownership and clean stop/save evidence (do not kill an unrelated Minecraft server).
- An actual action/LLM/cognition/message admission fence shared by the current Self owners; a symbolic bool is not enough.
- A full owner-state serializer (Goal/Intent/Skill, Log/Structured Memory, relationships and communication cut, Pending requests, Recent3Self). The stage-1 optional `owner-state.json` remains opaque.
- Native sessions fresh after every restart, and no old GPU task/Action command may race the newly opened gate.
- A single atomic/fenced release of admission for the entire roster; a partial release is unsupported and must HOLD.
- An actual host poll loop; no fake 60-second elapsed measurements.
- Crash test between generation boundaries and actual multi-Self recovery into a **new** World branch, verifying later memory/learning and World changes are gone.

## Deterministic fault suite

`tests/test_coordinated_autosave_runtime_dev.py` uses file-backed World/Self fixtures and callback fakes:
- A and B complete one generation, then another at 60s, with exact stop/freeze/restart/rebind/release ordering.
- No clock advancement before 60s.
- Later Zombie death and Self owner-state modifications do not appear after restoring a prior generation.
- Undelivered inter-Self message causes HOLD before World stop.
- Paper restart failure, Self stale-session rebind and wrong World receipt cause HOLD with no release.
- Interrupted/incomplete generation sequence is not reused.

These tests are **offline**; neither live Paper process behavior nor full self-owner recovery is thereby qualified.

## Proposed real World trial (after wiring)

Run on a disposable Paper 1.21.8 World with two actually running, independently recorded Self sessions. Save once, perform a real A attack witnessed by B and an independent B memory update, then crash before the second successful save. Recover the prior complete generation to a NEW branch. Both Self A and B must have neither event and the Zombie must be in the saved physical state. No stale Action/LLM result/message may be automatically reissued. Continue for at least two real 60s save cycles, measure wall and World clock skew, inspect raw logs/SHA256, and report exact HEAD/CI. Keep QUAL_NO_GO / SCIENCE_NOT_RUN.

**Qualification:** `OFFLINE_AUTOSAVE_BARRIER_DEV_PASS` only after same-HEAD CI; `REAL_LIVE_60S_NOT_ATTESTED` and `REAL_TWO_SELF_RECOVERY_NOT_RUN` until live adapters and controlled trial are complete.
