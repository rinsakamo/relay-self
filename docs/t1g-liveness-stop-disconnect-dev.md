# T1g — S49/T1f long-run and terminal-custody DEV preparation

This file retains the preparation-stage record below. Subsequent Python 3.12,
32-MOVE native regression and disconnect/ACK fault results are recorded in
[the 2026-10-26 native DEV report](t1g-native-dev-results-20261026.md).

Refs: #150, #627, #537, #616, #626. Starting DEV_WORLD_OBSERVED source:
`self/dev-t1f-s49-t2-20261026` at `488fcd3576bb4f4f147dc37434bf71b51f0b02e4`.

**This is an isolated DEV source change, not a new native-World result.**
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.

## Corrected safety boundary

1. `t1f_continuation_dev.next_tick` now treats **existing native
   `connection_end`, `adapter_error`, `command_error` and unsolicited
   `shutdown_ack` as terminal conditions**, before considering another
   Paper snapshot. It also refuses a foreign Paper session. On terminal,
   source timeout, EOF or non-ADMITTED frame, it latches any attached
   `TickAccounting.failed` so that a later Action or WAIT_DEV energy/fatigue
   transition cannot be resumed on an old source.
2. Original `native.jsonl` terminal audit runs after the owned bridge has
   exited and its original stdout has been drained. One `shutdown_ack`
   followed by one `connection_end` in the same session with monotonic
   bridge seq is required for the **DEV bridge transport closure**.
   Unexpected disconnect, missing end/ACK, duplicate events, foreign
   session, or post-shutdown physical effects are not accepted as normal.
3. `bridge_transport_closed` is **not** `high_level_stop_ack_attested` or
   `paper_world_stopped_attested`, both of which are always false here.
   The existing Node shutdown command and process exit are not a new high-
   level S49 STOP authority and do not attest Paper whole-tick inactivity.
4. No new native reader, S49 action issuer, motor control effect, adaptive
   TPS actuator, L1/L2/model call or new P1 formula is added.
   `T2 WAIT_DEV` is still not R-qualified WAIT.

## Offline tests and gaps

- The isolated pure `t1g_terminal_liveness_dev.py` audit passed **9
  focused tests using local Python 3.13.5**, including normal bridge
  exit, unexpected disconnect, missing ACK/end, replay/foreign seq and
  post-shutdown effect rejection. The tested source SHA was independently
  checked against the pushed Git blob.
- `tests/test_t1g_next_tick_liveness_dev.py` tests the *integrated*
  Paper reader's disconnect, adapter error, unsolicited shutdown ACK,
  EOF, timeout, foreign source and non-admitted snapshot. They were added
  but **not run against a repository checkout** in this environment.
- **Not run**: Python 3.12 focused FAST, Node/JDK build, native Paper
  1.21.8 long-run, injected physical disconnect, actual STOP/STOP ACK,
  M0/P1 drift under sustained load, 2/200TPS motor. Prior T1f World
  result is not promoted to a qualification.

## Next LocalCodex DEV checks on Windows/WSL2

1. `python3.12 -m pytest -q tests/test_t1g_terminal_liveness_dev.py
   tests/test_t1g_next_tick_liveness_dev.py tests/test_t1f_t2_dev.py
   tests/test_t1e_native_dev.py`; repair regressions in the isolation
   branch and run module-completion FAST, Node focused and Java rebuild
   only if their modules change.
2. Run **isolated disposable** Paper/Mineflayer DEV with
   `--cases t2_loop --loop-moves 32` and a fresh `--output` as per
   `docs/t1f-s49-t2-dev.md`. Keep input/Body/Action and process custody
   bounded by existing source limits; record throughput, failure and
   no-credit shutdown-tail tick, no duplicate Action IDs and final cleanup.
   This is an engineering stress sample, not a universal longevity claim.
3. Inject controlled native disconnect during MOVE, between epochs, and
   during boundary WAIT; keep FAILED originals. No new Action may be
   issued after any disconnect/UNKNOWN and T2 must not credit missing
   ticks. Test clean shutdown separately: `shutdown_ack` and
   `connection_end` do **not** claim high-level STOP ACK.
4. Check P1 owner #626 before introducing non-WAIT recovery or gait-based
   rate adjustments. For the current profile preserve exactly the old
   WAIT-only recovery semantics; do not invent physiology. Physical high-
   TPS Motor and World TPS actuator remain disabled.

If a native fault is injected, only the disposable DEV World is affected.
Do not alter main, PR #545/#634, prior World evidence or consume R/V grants.
