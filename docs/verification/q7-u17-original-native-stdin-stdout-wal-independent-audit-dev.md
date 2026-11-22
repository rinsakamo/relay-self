# Q7 — U17 Original Native stdin + stdout + WAL independent source audit (DEV only)

Date: 2026-11-22. Independent Q lane [#1088](https://github.com/rinsakamo/relay-self/issues/1088) / [Draft #1089](https://github.com/rinsakamo/relay-self/pull/1089); integrated original B/I [Draft #1124](https://github.com/rinsakamo/relay-self/pull/1124).

## Pinned code

- U17 source review began at I `3ceff588f95e3a85519ded5f8ea890156c97ea10` (`adapters/mineflayer/process_session.py` Git blob `b7313c50b695dea3b594742fb6882dfb8c4a2f2b`): five commits after U17's earlier no-caller HOLD, adding an exclusive, original-owned, continuous Native **stdin** FD alongside the existing stdout FD. Under original `_send`/original physical atomic callback, `_write_owned_stdin` writes to the one Node stdin stream and the original input transcript; no separate issuer or Native Action authority added. The archive means a buffered **attempt**, not Node reception/ACK.
- Later I `89d33a1424a0cecffdf60adab9d80d08d182e990` added a `rearm_original_place_after_q4_owned_native_dev` bridge to the pre-existing owner rearm. The bridge checks the live original Node session, FD-bound stdin+stdout frames and typed S1 Native receipts; it reads the owned Paper log but mere log presence is **not** corroborated Paper movement.
- At time of review, newer I `dc61cdcdd7976bc2395772a039f27596126d282c` adds a **new original S1 settled→Owner fresh L1 choice→S2 process-backed** call chain `continue_original_s1_to_s2_owned_native_dev`. It requires a pre-existing original Stage27h S1 loop, actual S1 terminal receipt, real original Paper tick receipts, original Native stream FD and host timing. Q inspected its source; there is **no real independent-world observation or exact-HEAD green CI for this new caller yet** (GitHub Actions run #45026893348 was queued at review). It is an implementation advance but does not itself start an isolated Paper World or obtain genuine Paper events.
- Original U16 [CI #45022943095](https://github.com/rinsakamo/relay-self/actions/runs/45022943095): **5/5 SUCCESS, 2,972 pytest PASS** independently verified in prior Q6. Later I HEADs require their own exact-HEAD checks; do not assume this earlier green run covers the new caller.

## New independent Q7 code and exact test result

- [`experiments/q_lane_q7_native_three_way_audit_dev.py`](../../experiments/q_lane_q7_native_three_way_audit_dev.py) is **read-only** and accepts original B `owner_wal`, original Native stdout JSONL and actual Python→Node stdin JSONL. It first reuses Q5's **independent** two-MOVE WAL/Native readback checker (two distinct terminal PLACE parents, 8+8 World ticks, ≤0.06m late drift, 0.1–1.0m displacement), then additionally checks:
  - Actual original Native seq=0 `adapter_started` and all stdout events sharing the same session; the WAL's S1/S2 before-LOOK probes match raw Native observations and original stdin `observe` request IDs.
  - Exactly two WALK actions' **six** original physical input commands, in order: LOOK, `set_control('forward', true)`, `clear_controls`, each with the expected unique parent/child identities; no unbound ATTACK, EAT, extra control, wrong gait, repeated START or malformed effect command.
  - Exactly six raw `effect_result` ACKs matching command identities/order with result `applied`, no forged/foreign ACK; six post-STOP settle probes are requested after the corresponding raw STOP and before any subsequent original PLACE.
  - Duplicate JSON keys, NaN, duplicate probe requests, missing/truncated stdin, wrong control, reordered effects, rejected/missing STOP, foreign Native session or extra native effect refuse.
- [`tests/test_q_lane_q7_native_three_way_audit_dev.py`](../../tests/test_q_lane_q7_native_three_way_audit_dev.py): **one positive fixture, 21 adversarial source variants, one read-only guarantee test**. The initial Q intermediate CI failed one test **because the fault was injected into a probe instead of the STOP ACK**; corrected the test index, not the auditor's result logic. A separate minor addition required the WAL pre-LOOK probe itself to appear in Native stdout.
- **Exact Q implementation HEAD `572c1047c0c6c67c2f90fbe566d15e472dde9d91`**, [Actions #45026814967](https://github.com/rinsakamo/relay-self/actions/runs/45026814967): **4/4 SUCCESS, 1,221 pytest PASS** from original CI logs (lint, repo contracts and Mineflayer adapter all successful). No Node/Minecraft World is launched by the independent Q7 test.

After and only after genuine original files are archived:

```bash
python experiments/q_lane_q7_native_three_way_audit_dev.py \
  --wal /absolute/original-owner-wal.json \
  --native-stdout /absolute/original-native-stdout.jsonl \
  --native-stdin /absolute/original-native-stdin.jsonl
```

The **only** possible positive classification is `Q7_STDIN_STDOUT_WAL_CPU_STRUCTURE_PASS` with `real_world_dev_pass=false`. File bytes being consistent does **not** authenticate original producer credentials, host monotonic 800ms, independent Paper UUID/position, actual physical STOP, or a separate STOP-fault child exit. It never unlocks a physical lease.

## Decision / minimal next step

- **`Q7_U17_NATIVE_STDIN_CODE_REVIEW_CPU_PASS`** and **`Q7_THREE_WAY_INDEPENDENT_SYNTHETIC_CI_PASS`** on the pinned source and Q exact HEAD.
- **`Q4_REAL_WORLD_TWO_MOVE_NOT_RUN / Q4_REAL_ABORT_NOT_RUN / PRE_WORLD_HOLD`**: no actual original Native/Paper logs have been submitted to Q. The newly connected `continue_original_s1_to_s2_owned_native_dev` still needs an original one-Self isolated World S1 producer/caller plus genuine Paper witness, original monotonic timestamps, continuous full archives and the separate fault-run. Real World must not be inferred from synthetic stdout/stin or green CI.
- Keep `QUAL_NO_GO / SCIENCE_NOT_RUN` and both Draft PRs. Do not add full old S1 cryptographic custody as a prerequisite of the agreed lightweight DEV experiment.

**Next I action:** exact-head CI of the new caller, minimal real Paper one-Self test harness, then two 0.5m-class MOVE+STOP+8+8 ticks under one owned Native source, plus separate STOP-fault World and raw evidence manifest. Q7/Q6/Q5 are ready to read independently.
