# Q8 — Independent Paper main-thread ↔ original Native/WAL two-MOVE audit

2026-11-22, Q [Issue #1088](https://github.com/rinsakamo/relay-self/issues/1088), [Draft PR #1089](https://github.com/rinsakamo/relay-self/pull/1089); unified I [Draft #1124](https://github.com/rinsakamo/relay-self/pull/1124).

## Pinned I source, exact-head CI and actual result boundary

- Examined immutable unified I U19 **`920cf48db24e194076aa6c0058b6abab8cf8ce58`**, 42 commits beyond Q7's `ef01e697` snapshot. [I exact-head Actions #45031282369](https://github.com/rinsakamo/relay-self/actions/runs/45031282369) **5/5 SUCCESS / 3,002 pytest PASS**, including Ruff, repository contracts, Node/Mineflayer and Paper tick witness.
- Original I now has a real **code path**, not simply synthetic S2 APIs: `src/relay_self/i_lane_i4a_s1_owned_native_runner_dev.py` (actual original Stage26 L1→S1), `continue_original_s1_to_s2_owned_native_dev` (fresh Owner L1 and original S2), `experiments/i_unified_u17_original_two_place_trial_dev.py` (single-process two-PLACE caller, original stdin/stdout/WAL/Paper/host/process-exit archive + manifest) and `src/relay_self/q4_original_paper_position_dev.py` (original owned-Paper actor position readback, U19 frozen S1→new S2 Paper prefix).
- Actual **disposable local Paper+Gemma+Bridge bootstrap and two World experiments have NOT run**, per current I original report and direct Q tool access. No actual seven-source manifest produced, no real S1/S2 motor positions, no real STOP-fault exit observed. [I U18/U19 report](https://github.com/rinsakamo/relay-self/pull/1124#issuecomment-7080369998). Never classify green CI as World evidence.

## Independent Q8 implementation (Q-owned code only)

New [`experiments/q_lane_q8_paper_native_two_move_audit_dev.py`](../../experiments/q_lane_q8_paper_native_two_move_audit_dev.py), [`tests/test_q_lane_q8_paper_native_two_move_audit_dev.py`](../../tests/test_q_lane_q8_paper_native_two_move_audit_dev.py).

- Accepts the **actual original owned Paper process log** alongside original B WAL and original Native stdin/stdout. Reuses *Q's own* Q7 three-way and Q5 WAL+Native checks; **does not call or trust I's Paper position-window verifier**.
- Parses the Java Paper plugin's literal `P0D_RESIDENT_READY` boot marker and `P0D_RESIDENT event=JOIN|MOVE|PRESENT|QUIT` main-thread lines, requiring exactly one boot/actor/world/name, no mid-run QUIT or reJOIN, strict source fields/canonical UUID, finite positions and monotonically ordered Paper ticks/lines.
- Finds **two separate original Paper position windows**, in order, one for each fresh canonical original PLACE Action. Requires a real Paper `MOVE` record, 0.1–1m Paper displacement from the correct origin (S1 JOIN; S2 first settled Paper position), independent 8–200 tick spacing on both successive windows, <=0.06m late drift, and Paper vs original Native STOP/first/settled geometry within <=0.25/0.16/0.12m.
- Keeps Paper main-thread tick and Native day-clock separate, never invents a clock conversion or attributes individual effects causally to Paper. It does **not** prove actual motor elapsed host times, original source ownership authentication or an injected STOP-fault child exit; those are separate real-world original evidence.
- One synthetic positive, 19 hostile mutations and one check that original files are never written. Malicious cases include a replayed old S1 window, missing fresh S2 Paper movement, no MOVE record, >=200 tick gaps, mixed actor/World/boot, quit/rejoin, Paper position mismatch, late drift, NaN, duplicate Paper fields, truncated final line and tick rewind.
- Q implementation HEAD **`b9a6766d0ecbea51004d798baefa0a8e6741c4ae`**: [Q exact-head Actions #45032850062](https://github.com/rinsakamo/relay-self/actions/runs/45032850062) **4/4 SUCCESS, 1,242 pytest PASS** independently checked from original job log (lint/contracts/Node adapter all SUCCESS).

Read-only example **after real originals exist**:

```bash
python experiments/q_lane_q8_paper_native_two_move_audit_dev.py \
  --wal /absolute/trial/original-owner-wal.json \
  --native-stdout /absolute/trial/original-native-stdout.jsonl \
  --native-stdin /absolute/trial/original-native-stdin.jsonl \
  --paper-log /absolute/trial/original-paper-process.log
```

Output remains `Q8_PAPER_NATIVE_TWO_MOVES_CPU_CORRELATED` with `real_world_dev_pass: false` and `causal_native_to_paper: false`. Run Q6 manifest file hashes separately and independently inspect original actual host time and fault-run Node exit if a real World verdict is sought.

## Focused I code-review observation (small remedy, not a new gate)

At U19 `src/relay_self/q4_original_paper_position_dev.py` the Paper sample selection in `_build_window` (roughly lines 151–165) checks `first.tick - stop.tick >= 8` and `settled.tick - first.tick >= 8`, but not the existing `<=200` upper bound used by the original Q4/NATIVE settled contracts. On source-shaped input with arbitrarily late Paper samples, the function can classify this Paper window positive (if positions otherwise match). Q8 independently rejects both gaps over 200. The smallest aligned I follow-up is to require `8 <= PaperGap <= 200` on **both** legs, with one near-201-tick hostile fixture. The owner/issuer/WAL contract need not change. This is a **bounded witness contract discrepancy**, **not proof of an unsafe physical motor** or a claim that Paper actually emitted this pattern.

## Disposition

**`Q8_PAPER_NATIVE_RAW_CORRELATION_CPU_PASS`**, I U19 source/CI code review PASS for the stated narrow scopes. **`Q4_REAL_WORLD_TWO_MOVE_NOT_RUN / Q4_REAL_STOP_FAULT_NOT_RUN / PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`** remain, because no genuine original World manifests were available for Q to consume. Keep I and Q PRs Draft, avoid expanding QUAL historic cryptographic requirements into the limited DEV experiment. Prioritize the one-Self isolated Paper+Node+Gemma launcher and two short real physical runs.
