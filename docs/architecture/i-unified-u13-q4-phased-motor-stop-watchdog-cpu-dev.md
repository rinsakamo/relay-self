# U13 — Q4 phased original START→STOP watchdog / settling (CPU DEV only)

Starting exact U12 HEAD: `966b0943fbfb181e9f999287109be5bca3b11d37`. U12 [HOLD record](i-unified-u12-q4-partial-reservation-hold.md) identified that the existing 2s `run_q4_dev_place_with_watchdog` incorrectly enclosed the **entire** original PLACE execution, including the later 8+8 tick STOP settling period. This patch creates a **separate opt-in interface**, rather than weakening the older safety gate or claiming a World trial.

## Original issuer instrumentation

`complete_prepared_place_move_dev(..., motor_boundary=...)` accepts an optional `Q4DevMotorBoundary` from the host-owned `run_q4_dev_place_with_motor_deadline`. No callback means the existing historical behavior stays unchanged. For a qualified invocation, the same original Stage27 executor:
- invokes `before_native_start` *before awaiting* the original `send_set_control(forward=true)` (the host motor deadline includes any native send/ACK latency);
- records the original, source-strict applied START ACK from `_native`, denying wrong session, ID, effect, result or replay;
- records the original applied STOP ACK only **after** `send_clear_controls` and the strict `_native` result; it must be newer than START and originate from the same original owner-task, session and parent Action;
- then performs `_settled` 8+8 tick probes and original canonical WAL terminal update **after the 2s motor phase** and under a separate bounded settlement deadline.

No model callback, native writer, Action author, WAL author or Body skill policy was introduced. The host milestone object is a **local in-process observation of the issuer callback**, not independently authenticated raw Native or Paper evidence.

## Host phases and failure treatment

The new host wrapper requires the **same original** bridge session, exactly one live Native, explicit `bounded_place_dev_mode`, a one-use `Q4DevOperatorPermit`, a fixed parent Action ID, pre-START bound (default ≤2s), START→STOP ACK bound (default ≤2s), and post-STOP settlement bound (default 30s; caller ≤120s).

Missing START, missing/foreign/replayed ACK, STOP late beyond its *original monotonic mark*, incomplete/forged terminal receipt, invalid/nonterminal/mismatched canonical WAL, over-1m/under-0.1m movement, cancellation, stale host source, or late settlement **cannot return a successful result**. Failure cancels the original work task without awaiting potentially stubborn cleanup, quarantines the issuer, attempts its one prebound STOP, and terminates the owned Node child even if STOP bytes were buffered but ACK is unknown. Neither quarantine nor kill is proof of Paper STOP or terminal movement. A failure *after* a terminal WAL is also an operator HOLD, not an invitation to reuse the old native session.

The final original Owner disk readback checks the exact parent/Native, `NATIVE_PLACE_MOVE_SETTLED` terminal WAL, matching digest/action/receipt/displacement, live current physical session, no outstanding lease, and identical original START/STOP ACK source IDs, types and sequences. **Typed ACKs and synthetic fixture rows can still be forged by a co-resident test process**; this is structural DEV coverage, not external producer authentication.

The previous `run_q4_dev_place_with_watchdog` remains unmodified and still bounds the entire coroutine conservatively. The newly defined phased wrapper is **not wired to a real original I4a S2 runner** and cannot authorize real motor by itself. U12's other blockers are unchanged: original S2 reservation/consume APIs absent, prior-terminal issuance cannot yet qualify, real owned Native S2 runner absent, and the prior U10 typed second-action rearm is not independently sourced.

## CPU tests / DEV decision

`tests/test_q4_phased_motor_deadline_dev.py` covers valid synthetic STOP ACK followed by settling lasting longer than the motor deadline; missing/fake START; unacknowledged/foreign STOP; late post-STOP settling; incomplete terminal WAL; foreign Native receipt or swapped ACK sequence **even with a terminal WAL**; second Self before issue; cross-task forged signal; and physically quarantined lease-replay refusal. No real Node/Paper position, World, Gemma or operator DEV attempt occurred.

**Disposition:** `I_U13_Q4_PHASED_START_STOP_SETTLE_CPU_OFFLINE_DEV_PASS` **only if exact-HEAD CI completes successfully**. Always retain `I4A_ORIGINAL_REAL_S2_HOLD / REAL_NATIVE_PAPER_SOURCE_HOLD / Q4_REAL_WORLD_MOVE_STOP_REPEAT_HOLD / PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`; Q independent re-audit must validate this exact source/CI before World DEV. Prior local interrupted full-pytest failure markers from U12 are not retroactively classified.
