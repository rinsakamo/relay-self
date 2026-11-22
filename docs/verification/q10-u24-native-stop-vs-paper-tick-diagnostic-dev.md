# Q10 — U24 failed-S1 Native STOP clock vs independent Paper progress

**2026-11-23**, independent Q [Issue #1088](https://github.com/rinsakamo/relay-self/issues/1088), [Draft PR #1089](https://github.com/rinsakamo/relay-self/pull/1089); original I [Draft PR #1124](https://github.com/rinsakamo/relay-self/pull/1124).

## Current source and actual World boundary

- Original I HEAD **`cb43dad53c345a81a68b688a1504a58318044888`**. [Exact-head CI #45043870760](https://github.com/rinsakamo/relay-self/actions/runs/45043870760) 5/5 SUCCESS. The I lane did execute two **separate** original B disposable World DEV trials at U24 on local WSL: nominal S1 `stage27c-B-7` obtained genuine Native LOOK/START/STOP applied ACK, then consumed 24 STOP probes without qualifying 8+8 settlement; the canonical WAL remained `PREPARED_UNRESOLVED`, and S2 was not attempted. In the separate STOP-fault World, S1 `stage27c-B-14` received genuine START ACK, suppressed STOP with one-shot injected failure, and original owner Node process exit was recorded as `-15`, with unresolved WAL. Neither result is 2-MOVE PASS. Source: [I→Q U24 handoff](https://github.com/rinsakamo/relay-self/issues/1088#issuecomment-7082117380).
- Exact local original source directories: `/home/rinsa/evidence/i-u24/u20-final-two-moves-evidence` and `/home/rinsa/evidence/i-u24/u20-stop-fault-evidence`. The tarball mentioned in I's handoff is a *portable copy* whose device/inode changes; **Q6's original-file manifest identity check requires the unmodified WSL directories**, not an extracted copy. Q ChatGPT's cloud GitHub connector cannot read those WSL files directly.
- Q9 already implements read-only original seven-role manifest verification followed by native stdin/stdout/WAL and 24-probe analysis; [Q9 exact-head CI #45084107129](https://github.com/rinsakamo/relay-self/actions/runs/45084107129) 4/4 SUCCESS, 1,259 pytest PASS. Q9 was **not** run on actual U24 WSL evidence by this cloud process.

## Q10 independent implementation (read-only)

[`experiments/q_lane_q10_u24_paper_clock_diagnostic_dev.py`](../../experiments/q_lane_q10_u24_paper_clock_diagnostic_dev.py) calls independent Q9 first; when its exact seven-original role/manifest plus original Native ACK/STOP probe/WAL result is consistent, it separately parses **original raw Paper main-thread** `P0D_RESIDENT_READY` and `P0D_RESIDENT event=...` lines (no reliance on I Paper parser). Checks one real boot marker, continuous actor/world/name with one JOIN, optional final QUIT, finite numeric position, monotonic Paper main-thread ticks and distinct progress. Reports:

- `native.native_stop_tick_span`, distinct STOP world-time samples, original 24-probe count and STOP endpoint displacement from Q9.
- `paper.paper_observed_tick_span`, distinct Paper main-thread samples, number of Paper MOVE records, boot/world/actor IDs, last sampled main-thread tick and optional QUIT.
- A strictly bounded **diagnostic hypothesis**, never an unqualified verdict: `NATIVE_STOP_CLOCK_SHORT_WITH_PAPER_RUN_PROGRESS` when Native post-STOP WORLD clock span is below 16 while Paper's **whole-run** main-thread sample span is at least 16; `NATIVE_STOP_CLOCK_SHORT_PAPER_PROGRESS_INCONCLUSIVE` otherwise when Native is short; `NATIVE_ADVANCED_BUT_NO_SETTLED_8_PLUS_8` when Native advanced >=16 but the original STOP algorithm found no stable window.
- Paper main-thread ticks and Native world day/time are different clocks. This audit **does not** prove Paper progressed *during the exact 24 Native STOP probes*: its Paper span may include earlier/pre-STOP events. The classification is a prompt for checking source clock semantics/gamerule, **not** proof of a frozen gamerule, causal motor issue or authorization to increase probe quota.
- For the fault run, Q10 independently reads Paper actor timeline, preserves Q9's limited STOP-fault record consistency and **does not** assert actual OS termination or WAL resolution.

[`tests/test_q_lane_q10_u24_paper_clock_diagnostic_dev.py`](../../tests/test_q_lane_q10_u24_paper_clock_diagnostic_dev.py) contains a nominal contrast, Paper/Native both short/inconclusive, separate STOP fault and 16 hostile Paper source edits (foreign World/actor/boot, duplicate/missing READY, reJOIN/QUIT, after-QUIT sample, time regression, malformed NaN/duplicate fields, torn line, missing source, noncanonical UUID), plus a read-only bytes check. All fixtures are **synthetic**.

Intermediate first Q10 CI at `f6d890f5`: pytest 1,279 PASS, lint-only I001 import order failure; fixed import-only at `639790b836c9714c4831c59c9bf5db8546f6005b`. [Q code-head CI #45084585847](https://github.com/rinsakamo/relay-self/actions/runs/45084585847) requires checking its final completion before claiming exact-head success.

## Local invocation (no World or new Gemma POST)

Run on the preserved *unmodified* U24 originals with the independent Q branch checked out locally:

```bash
PYTHONPATH=src:. python -m experiments.q_lane_q10_u24_paper_clock_diagnostic_dev \
  --root /home/rinsa/evidence/i-u24/u20-final-two-moves-evidence \
  --manifest /home/rinsa/evidence/i-u24/u20-final-two-moves-evidence/original-u17-two-moves-manifest.json \
  --trial two_moves

PYTHONPATH=src:. python -m experiments.q_lane_q10_u24_paper_clock_diagnostic_dev \
  --root /home/rinsa/evidence/i-u24/u20-stop-fault-evidence \
  --manifest /home/rinsa/evidence/i-u24/u20-stop-fault-evidence/original-u17-stop-failure-manifest.json \
  --trial stop_failure
```

No change to original physical issuer, owner, WAL, native callback, actual World test or resource budgets. Do not change the 24-probe limit from synthetic findings. Read the actual U24 tick/position statistics first; if Native STOP tick span <16 while Paper does advance, check Minecraft day-clock sampling and gamerules vs main-thread tick source **before** trying 48 probes. If Native STOP span >=16, investigate the original per-probe drift and first/stable reset dynamics instead. No real-source Q10 invocation or classification is claimed by this GitHub-only run.

**Status:** `Q10_DUAL_CLOCK_DIAGNOSTIC_CPU_ONLY`; **`Q4_REAL_WORLD_MOVE_STOP_REPEAT_HOLD / PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`**. U24 STOP-fault producer capture is independently *unverified* until Q9/Q10 are actually run on originals. Keep Q and I PRs Draft.
