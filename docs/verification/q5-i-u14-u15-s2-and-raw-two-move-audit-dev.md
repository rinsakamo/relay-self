# Q5 — Independent Q audit of unified I U14/U15 S2 CPU connection, and raw World-readback guard

Date: 2026-11-22. Q lane [Draft #1089](https://github.com/rinsakamo/relay-self/pull/1089), Q issue [#1088](https://github.com/rinsakamo/relay-self/issues/1088), unified I [Draft #1124](https://github.com/rinsakamo/relay-self/pull/1124).

## Exact sources examined

- **I U14 exact HEAD:** `76d9b91a482ec33aad3b63eb2be6741e64c6dd0d`. I [Actions #45018594749](https://github.com/rinsakamo/relay-self/actions/runs/45018594749): independently read 5/5 successful job conclusions and pytest job log `2934 passed in 156.68s`. The Q4 U9 Native fail-closed CPU review at `5695a7a2` remains valid: no change to the native motor guard after U9.
- **I U15 HEAD examined:** `e48948d4fab7cb73993c3e48001ada9934c138bc` = U14 + **one test-only commit**, `tests/test_i_unified_u15_unmocked_s2_boundary_dev.py`, 137 added lines. U15's newly added unmocked production `verify_i4a_s2_empty_run_boundary` and `verify_live_wal_history_anchor` are called after constructing a synthetic original S1/WAL fixture; 1 positive and 7 hostile variations are in the test. CI [#45019413560](https://github.com/rinsakamo/relay-self/actions/runs/45019413560) finished **4/5, pytest 2,934 PASS / 8 FAIL**. All eight new U15 tests fail with `AttributeError: I4AS2EmptyRunBoundary has no new_action_authorized` at production verifier entry, because the synthetic `object.__new__` fixture omits the dataclass default field. This is an **incomplete test fixture**, not demonstrated production S2 failure. No U15 qualification until fixed and rerun.
- Source inspected: original `PhysicalIssueAdmission` (`physical_issue_admission_dev.py`, blob `054a35ddcf582562c4c290f33ab01c9681228624`), `begin_physical_issue_dev`, synthetic `reserve_s2_first_original_move_synthetic_dev`, `i_lane_i4a_s2_run_boundary_dev.py`, staged-place receipt and repeat source checker, plus U14/U15 tests.

## B/Physical source code-review observations

1. The original physical gate `_lock` is a `threading.RLock`, permitting its nested `quiescent_wal_history_window`, `lease`, `require_original_i4a_s2_wal_window`, and consumption under the same Owner cohort lock. The original lock is held around synchronous, non-awaiting reservation; no new competing issuer has been introduced.
2. An S2 window requires an original live `CheckpointedCognitiveOwner`, a matching `I4AS2EmptyRunBoundary`, a single `ResidentLlamaInferenceLane`, the original ONLINE/physical opt-in, and `verify_i4a_s2_empty_run_boundary`. Its in-memory selected parent consumption precedes the common `begin_physical_issue_dev` original WAL CAS. On failure, the parent remains consumed for that live physical owner, and no Native child is bound.
3. The common issuer allows prior `NATIVE_PLACE_MOVE_SETTLED` history **only inside the active exact same Owner/boundary/action S2 window** and checks prefix count/digest/action IDs, old terminal Supervisor/Intent/Skill, fresh probe/parent and canonical WAL. Its `prepare_place_move` occurs before supervisor ISSUE. The U14 tests exercise positive synthetic WAL append and previous-history denial; old-S1 boundary verification is deliberately stubbed in those tests. U15 adds a separate actual-unmocked-verifier positive/negative test, but still synthesizes S1 source and old World receipts.
4. The I4a reservation adapter `require_i4a_offline_scripted_native` **explicitly denies real `MineflayerProcessSession`**, including a subclass retaining process/decoder resources. Retaining an original physical lease creates **zero** authorized PLACE Native child commands. A new process-backed S2 runner is genuinely missing; pretending the synthetic helper is a real runner is not permissible.
5. Previously identified U13 host motor 2s and 8+8 tick settlement split is a separate, opt-in synthetic path, and has not yet been exercised on the actual Node/Paper process.
6. The Q source review and U14 green CI do **not** independently authenticate historical S1 raw producer custody. Existing in-memory consumed IDs are not an independent persistent witness after crashes. For this narrowly scoped DEV, full historical external signing is intentionally **not** an entry criterion; any unresolved canonical WAL, stale Owner, Native session and real post-START kill uncertainty still deny continued physical issuance.

**Q scoped U14 disposition:** `Q5_I_U14_ORIGINAL_S2_CPU_SOURCE_AND_CODE_REVIEW_PASS` limited to original code paths and 5/5 exact U14 CI. `I4A_S2_ORIGINAL_LIVE_NATIVE_RUNNER_HOLD / Q4_REAL_WORLD_MOVE_STOP_REPEAT_NOT_RUN / Q4_REAL_ABORT_NOT_RUN / PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`. U15 is not silently covered by U14 CI.

## New independent raw evidence consumer (Q-owned; zero issuer authority)

- [`experiments/q_lane_q4_raw_native_wal_audit_dev.py`](../../experiments/q_lane_q4_raw_native_wal_audit_dev.py): read-only, stdlib-only CLI that consumes the **original exact Native stdout JSONL** (`MineflayerProcessSession.start_raw_source_audit`) and original canonical `PhysicalActionJournal` JSON envelope. It checks the WAL SHA256 digest; exact two terminal MOVE_PLACE rows, same session/distinct parent Actions, raw LOOK/START/STOP applied ACK identity and order, three unique later Native probe seq/source, 8+8 ticks, ≤0.06m late drift, 0.1–1.0m genuine displacement and WAL/result agreement. It refuses duplicate JSON keys, nonfinite values, missing/foreign source, duplicate Native sequences, unresolved WAL, overshoot, relabeled ACKs and replay.
- [`tests/test_q_lane_q4_raw_native_wal_audit_dev.py`](../../tests/test_q_lane_q4_raw_native_wal_audit_dev.py): 1 positive and 14 hostile synthetic checks. **These fixtures are explicitly not World evidence**.
- **Q auditor exact-HEAD** `5d7681b3897c816481524b358120aa68d042ff38` (before adding this report). [Q Actions #45019571728](https://github.com/rinsakamo/relay-self/actions/runs/45019571728) **4/4 SUCCESS** (pytest **1,181 passed** independently read from job log, Ruff, repository contracts, Node adapter). First intermediate Q CI at `662c6164` had lint-only FAIL for an unused import/formatting; corrected at this exact green HEAD with unchanged verifier behavior.

Run only after original I runner produces actual raw artifacts:

```bash
python experiments/q_lane_q4_raw_native_wal_audit_dev.py \
  --wal /path/to/original-final-physical-wal.json \
  --native-jsonl /path/to/original-native-stdout.jsonl
```

Passing emits only `Q4_RAW_NATIVE_WAL_TWO_MOVES_CPU_STRUCTURE_PASS` with `real_world_dev_pass=false`. **It cannot by itself authenticate Paper, the 800ms motor bound, source custody, a terminal Node exit or real-world movement.** Independent Paper tick+position, original host monotonic timing and a separate real abort trial remain mandatory for the limited World DEV verdict.

## Practical next I lane handoff — no new theoretical gates

1. Create the **real** one-Self original Owner S2 process-backed executor separate from `*_synthetic_dev`, retaining B canonical WAL/one-use selected Action, Source/window, same Native session, Q4 per-process guard and host abort. Do not globally turn on observation-only B.
2. Use new throwaway flat World; under an explicit once-only operator DEV permit, run **one** 0.5m-class WALK, Native ACK STOP, 8+8 ticks, terminal WAL. Next, same owner and a truly fresh Action after actual authenticated raw receipts, then repeat. Collect existing Native raw stdout, Paper source, host timing and WAL; do not fabricate missing observations.
3. One controlled failure trial after START: verify neutral controls or **original owned Node process exit readback**, revoke source/physical gate, unresolved WAL and no new Action after that failure. A forced bot quit *request* alone is not confirmed process termination.

Do not prolong DEV with full past-history cryptographic signer, long-run cognition, qualification science or R1 migration. These remain separately HOLD. **Q cannot run the user's local WSL/Paper/Mineflayer runtime from this connected GitHub-only environment**; no real World was launched or passed by Q.


## Subsequent I U15 process-backed runner (newer than U14 source review)

At U15 HEAD `7f2274faac448163ea3e9b5be73ce4af90be61e8`, after the report's original U14 snapshot, I added **one new real-process-capable** `src/relay_self/i_lane_i4a_s2_owned_native_runner_dev.py` (284 lines). This **changes the earlier "runner absent" status for that pinned newer source only**. Q has independently read this new module. It refuses ordinary fake/scripted Native subclasses, requires the original `OwnedResidentPhysicalBridge` session of exact `MineflayerProcessSession` type, a live owned PID, opt-in bounded Node guard, installed original atomic Native stdin effect sender, original B cohort/Owner/physical Source, an explicit local permit and World preflight. It uses the original S2 WAL window/one-shot parent and retains the lease across the original Stage27 LOOK/START/STOP + 8+8 settlement executor, with host phased motor timeout/abort and exclusive raw Native stdout evidence capture. No second issuer or separate Action writer was found in this first code review.

**Not yet qualified:** the module has no new corresponding positive real-native runner test in this one-file commit; CI for `7f2274fa` [run #45019820767](https://github.com/rinsakamo/relay-self/actions/runs/45019820767) had just started when read; the earlier U15 test-only commit had eight failures and later test-only fix is not independently confirmed PASS. Source identity, real native stdout, Paper tick/pos, actual first-run terminal and independent second rearm/World executions are still NOT witnessed. **New code presence is NOT PRE_WORLD GO.** Keep one isolated World test after an exact-HEAD green preflight and a minimal process-backed test; do not require full historical QUAL source signatures. Q raw Native/WAL auditor is ready to consume actual artifacts.
