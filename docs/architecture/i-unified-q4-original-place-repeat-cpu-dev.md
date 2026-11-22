# Unified I Q4 — original Owner second MOVE_PLACE lease gate

**Q independent milestone:** [Q4/U9 independent audit #1088](https://github.com/rinsakamo/relay-self/issues/1088#issuecomment-7077400791) confirms the prior three Native START/STOP/timeout exception defects are CLOSED **within CPU/Node scope**. Real isolated World, raw Native/Paper motor receipts and actual second physical Action are still NOT RUN.

## Narrow original-B change

The single existing `PhysicalIssueAdmission` previously consumed its Original B S1-bound MOVE_PLACE child admission once per Self lifetime; with no explicit renewal method, even a clean terminal first Action could not be followed by the genuinely new Q4 second Action in the same Native session.

The new `rearm_original_place_after_q4_settled(bridge, self_id, evidence)` is a **synchronous CPU DEV structural gate** in that **same original issuer**, not an alternate issuer. It never sends a Native command, creates a Skill/Goal, mutates the WAL or reuses an Action. It can only run **after the previous lease has finished** and the original bounded previous Action has one terminal WAL suffix.

Its custody conditions include: original B bridge/resident/Owner object identity; original active native, resident epoch, World scope and gate generation; previous frozen S1 prefix digest and exact rows; canonical WAL path and stable inode during readback; exactly one appended v2 `NATIVE_PLACE_MOVE_SETTLED` MOVE_PLACE row for the previously bound parent; a clean ActionSupervisor; no active lease; unrevoked per-Self physical gate; and the same Paper World session. It rejects PREPARED, cancelled, retried, quarantined or stale Owner source.

`verify_q4_previous_place_terminal_cpu` cross-checks *typed caller-supplied* original Native LOOK/START/STOP ACK Action IDs/seq/results, three distinct source probes, original WAL effect seq/tick/position records, separate same-Paper-session tick receipts with 8+8 intervals, horizontal/3-D settling <=0.06m, real-sounding but **caller-supplied** 800ms/2s time readings, and 0.1m–1.0m physical displacement. It cannot establish that these readbacks came from external Native/Paper, and therefore never marks real World/QUAL qualified. The second original S1 volatile anchor is captured under the **same resident→physical→canonical WAL locks**, only then is the old consumed-child bit cleared. Any failure keeps the one-shot barrier closed.

Original B production observation-only/PLACE OFF remains unchanged. Existing historical repeated Action ID/Intent/Skill/source checks remain in the original next-lease binder; a new L1 Action must have genuinely new native probe sequence, Intent, Skill execution, and Action parent. The next receipt itself needs a fresh real source. **This is readiness for a second Action, not a completed second Action.**

## DEV acceptance still required

The actual original B real physical runner is **not connected** by this method. A separate isolated one-Self, one-shot operator-controlled live integration must use `run_q4_dev_place_with_watchdog` and original canonical `prepare_place_move → bind_original_place_children → submit_native_effect → close_place_move`, with raw Native/Paper receipts and a host-owned abort on all failed/cancelled paths. No alternative issuer, direct native write, or unsigned WAL update is permitted. Two physically observed approximately 0.5m-class WALK actions with distinct parent IDs, Native START/STOP ACK, Paper-backed 8+8 settling and measured displacement <=1m must pass **before** `Q4_MINIMAL_REAL_WORLD_MOVE_STOP_REPEAT_DEV_PASS`.

**Current label if CI green:** `I_Q4_SECOND_ORIGINAL_PLACE_LEASE_TERMINAL_SOURCE_CPU_OFFLINE_DEV_PASS` only. `Q4_REAL_WORLD_MOVE_STOP_REPEAT_HOLD / REAL_NATIVE_PAPER_SOURCE_HOLD / PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`. Q owns independent review and raw evidence qualification. PR #1124 stays Draft, no merge.
