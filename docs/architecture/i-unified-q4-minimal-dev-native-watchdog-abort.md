# Unified I Q4 — reduced real MOVE_PLACE DEV prerequisites (2026-11-22)

**Read Q-owned acceptance contract first:** [Issue #1088 Q4](https://github.com/rinsakamo/relay-self/issues/1088) and [Q4 independent plan](https://github.com/rinsakamo/relay-self/blob/57707f3a1a700da8ed28a4ea985d8badd05efcc2/docs/verification/q4-minimal-real-move-stop-repeat-dev.md). Q owns assessment; I owns only implementation. This document does NOT represent a real World trial.

## Bounded opt-in, no alternate issuer

The original consolidated B Owner, `PhysicalIssueAdmission`, original WAL, ActionPort and all existing Skill parent/child/ACK identities remain unchanged. B production recovery still has `observation_only` / PLACE OFF. No autonomous loop or new right to issue physical actions was created.

- `MineflayerProcessSession.launch(enable_q4_bounded_place_dev=True)` enables a **per-child**, opt-in Native watchdog; the ambient environment variable is always scrubbed on launches without the opt-in. The default remains OFF. The adapter owns the original Native process and reports the local launch mode; the flag is **not** Native/Paper source authentication.
- `Q4BoundedPlaceMotionGuard` in Node permits only WALK forward true / look / clear controls in opted-in sessions. One forward Action at a time. It polls the original bot position every 20ms using a monotonic clock, clears all controls and disconnects on **800ms forward interval** or an early **0.7m horizontal displacement** cutoff, sensor loss, malformed time or repeated START after a trip. These are *commanded* limits and early intervention; the real World acceptance bound is separately **observed displacement ≤ 1.0m**. Sampling, drift and settling may exceed this; a watchdog firing is abort/HOLD, not success.
- `run_q4_dev_place_with_watchdog` wraps an **existing** original Skill issuer, using an independent **2.0s maximum** `asyncio.wait` deadline (not `wait_for` that may block on uncooperative canceled-task cleanup), cancels the old task, and revokes/terminates without waiting for it to finish. It requires a scoped single-use `Q4DevOperatorPermit(self_id, native_session_id)`. It refuses non-opted Native children and multiple connected Self, and cannot create a physical lease or override its admission. The permit is in-process operator intent only, not cryptographic identity.
- The host can invoke `OwnedResidentPhysicalBridge.abort_place_after_start_dev` even **after the original Skill lease is canceled/released**. It synchronously revokes the original physical Self by quarantine, attempts the exact STOP if still allowed, and always terminates its owned Node/Mineflayer child unless it was already exited. Bounded TERM→KILL / readback is provided by `MineflayerProcessSession.force_terminate_owned`. A buffer write or STOP delivery without ACK cannot be called settled. The original WAL remains PREPARED_UNRESOLVED and no same-session rerun is permitted. If termination cannot be confirmed, return a HOLD and poison the original physical gate.

## CPU hostile regression

- JS `bounded_place_guard.test.mjs`: strict 800ms and early 0.7m stop, sensor/clock faults, simultaneous START, watchdog trip prevents session reuse, and normal control clear permits fresh second Action.
- Python `test_q4_native_launch_dev.py`: explicit per-launch guard even with hostile shell env, original TERM fallback to KILL, unkillable Node leaves HOLD.
- Python `test_q4_place_abort_dev.py`: actual cancellation after START but after lease's `finally` releases, attempted STOP denied then Node termination, no replay and unresolved WAL; STOP failure; STOP buffered but no native ACK → terminate; failed termination ⇒ gate HOLD; foreign Session, absent/reused permit, unbounded Native and multiple live Self rejected.
- Existing I U7 atomic submission and MOVE_PLACE source-lock regression suites, EAT/ATTACK/legacy MOVE suites remain under CI.

## Q4 real DEV evidence still required — *NOT RUN*

1. Host needs an actual locally launched **isolated freshly created flat World**, one original Self and explicit one-run opt-in; use original Q4 launcher with bounds enabled, host watchdog/killswitch, and real B opt-in only after preflight review. The current integrated code does **not** unlock observation-only B by default or provide a completed real trial runner.
2. Trial 1: approximate 0.5m WALK; record actual Native START/STOP IDs and ACK, Paper tick/body evidence, measured displacement ≤ 1.0m, forward time ≤ 800ms and two **8+8 tick** post-STOP stable windows. Report raw start/stop/settled positions and clock measurements.
3. Trial 2: same original Owner but genuinely new Action ID and fully terminal prior WAL/lease. Repeat moved, stopped and settled. Never restart after PREPARED_UNRESOLVED.
4. Fault trial: inject cancellation/STOP failure **after START**, verify exact original native neutralization or owned process termination and session revocation, keep WAL unresolved; no reissue. Unconfirmed kill is FAIL/HOLD.

For DEV only, do not block on full independent earlier S1 producer custody or R1/R2/longitudinal learning proof. Those remain separate and cannot be upgraded via a synthetic test.

**Classification pending exact-HEAD CI:** Q4 host+Native bounded abort CPU/offline DEV regression candidate. **Q4_REAL_WORLD_MOVE_STOP_REPEAT_HOLD / Q4_REAL_ABORT_FAIL_SAFE_HOLD / PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN**. Retain [Draft PR #1124](https://github.com/rinsakamo/relay-self/pull/1124) and Q [Draft #1089](https://github.com/rinsakamo/relay-self/pull/1089).
