# Q3 independent U7 re-audit — emergency PLACE STOP / final Native buffer write

**2026-11-22 — Q lane / read-only inspection of unified I exact HEAD.**

- Target repository: `rinsakamo/relay-self`, integrated I Draft [#1124](https://github.com/rinsakamo/relay-self/pull/1124)
- **Immutable target SHA:** `38c989472dcdf6ed5f75740f27eb7d91b9aa7920`; previous Q2 baseline `4b08384dfd928f0e5788038ec721064df6353bff`.
- **Exact-HEAD CI:** [Actions #44988972137](https://github.com/rinsakamo/relay-self/actions/runs/44988972137), attempt 1 SUCCESS, **5/5** named jobs: pytest, lint, repository-contracts, mineflayer-adapter, paper-tick-witness. Independently read pytest log: **`2875 passed in 115.95s`**. Paper log says **`BUILD SUCCESS`**.
- This Q work is a **code, immutable Git object and CI audit**, not an independently executed real World/Native test. Source assertions below are limited to reviewed code and test semantics. No Q-owned trusted Original S1 or hardware witness was supplied.

## A. Original tree/diff integrity

GitHub recursive tree of baseline and target is untruncated. Baseline **625 blobs** to target **627 blobs**; **0 removed**, **2 added**, **7 modified**. The immutable compare has **12 commits, ahead 12 / behind 0**. Added paths are `tests/test_i_unified_u7_place_stop_atomic_native_dev.py` and `docs/architecture/i-unified-u7-emergency-place-stop-native-boundary-dev.md`. Modified paths:

- `adapters/mineflayer/process_session.py`
- `src/relay_self/owned_resident_physical_bridge_dev.py`
- `src/relay_self/physical_issue_admission_dev.py`
- `src/relay_self/r06_unified_context_preflight_dev.py`
- three existing I4a/U5/U5b PLACE regression test modules.

No Original Owner replacement, second physical gate or sibling WAL writer was introduced by these changes. Historical I4a/I2 branch suites excluded from integrated discovery are NOT qualified just because the included test set is green.

## B. Quarantined MOVE_PLACE STOP regression

Original `PhysicalIssueAdmission.submit_native_effect` now admits a **specific emergency STOP** even when original cognition has been fenced and physical WAL has drifted *after START*. The guard `_is_quarantined_place_stop_locked` requires:

- an already-held original B S1 place anchor and native child binding;
- original bridge/physical/resident/owner identity and the same native session, the same live MOVE_PLACE parent lease, and no global close/poison/observation-only;
- original resident state `QUARANTINED` with **exactly one physical epoch increase**;
- the exact `clear_controls` child and its original `set_control` child already **consumed** by the issuer, and unused STOP child;
- no new LOOK, START, duplicate STOP or foreign native/session/child.

`_require_native_effect_locked` applies the same narrow quarantined STOP exception to the original lease and one-shot child accounting. Normal post-quarantine children still fail. Positive and negative synthetic cases in `tests/test_i_unified_u7_place_stop_atomic_native_dev.py` cover pre-START STOP HOLD, quarantine after START, cognitively fenced/tampered WAL post-START, foreign/wrong IDs, replay, and fake Native JSONL LOOK→START→STOP. This is a **repair of the Q2 reproducible denial**, **not real physical STOP/settling evidence**.

**Boundary:** `lease(...)` deletes the bound STOP on exit. Consequently a cancelled/timed-out lease or dead process with START potentially still active has **no proven independent host emergency STOP route**. A consumed START means the gate accepted a write callback before native drain/ACK; it does **not** prove the Node bot moved. Neither a successful STOP callback nor `FakeProcess.stdin.drain` proves the Node motor stopped. No real Minecraft 8+8 tick settling or Paper ACK.

## C. Final check-to-buffer-write race

Original adapter `MineflayerProcessSession._send` now uses `_send_lock` over full frames and drain; if installed, `_atomic_effect_sender(session,effect,action, writer)` wraps the synchronous `stdin.write(data)`. Original owned resident bridge `login` permanently installs the atomic sender **after** the existing final-effect gate and **before** first Native probe, for an actual `MineflayerProcessSession`.

`PhysicalIssueAdmission.submit_native_effect` validates the original S1/WAL and exact PREPARED file identity/digest, lease, epochs, child and session under lock order **resident → physical → canonical WAL flock**, then consumes the one-time child and calls that writer **before releasing locks**. The old `require_native_effect` rejects active `MOVE_PLACE` (no check-only fallback); a missing atomic sender consequently fails closed for MOVE_PLACE. Concurrent physical-quarantine and cooperative WAL-writer tests verify those locks hold through a fake synchronous writer. Symlinked WAL lock and post-bind rehashed S1 tests fail closed. A simulated `BrokenPipeError` consumes the child without reopening an unsafe replay.

**Supported statement:** this closes the in-process issuer-to-Python `stdin.write` buffer insertion gap along the owned, hook-installed path against other cooperatively locking issuer/WAL operations.

**Unsupported statement:** truly atomic *cross-process* Native stdin delivery, asynchronous `drain()`, Node parse/read acknowledgement, Paper tick/World effects, source-producer provenance or external uncooperative file replacement. The `write` callback has a Python internal signature and is not a cryptographic transport receipt; no signed, independently held original issuer/Native proof is created. A failed drain or process kill may leave `PREPARED_UNRESOLVED`. Real World opt-in remains OFF.

## D. Previous stale R0.6 blocker

`R06_EXTERNAL_HOLDS` now accurately says `B_SCHEMA3_ORIGINAL_PRODUCER_AUTHENTICATION_NOT_ATTESTED` rather than incorrectly claiming that strict JSON source handling has not been integrated. R1 shadow remains disallowed; this is bookkeeping correctness, not independent Paper authentication.

## Q decision — bound exact SHA only

- **`Q3_U7_ORIGINAL_PLACE_EMERGENCY_STOP_GUARD_CPU_CODE_REVIEW_PASS`**: repaired previous Q2 code denial in the same bound active lease, with hostile synthetic tests.
- **`Q3_U7_OWNER_WAL_LOCKED_NATIVE_BUFFER_WRITE_CPU_CODE_REVIEW_PASS`**: synchronous in-process buffer write is protected by verified call-path locks; missing atomic hook denies PLACE.
- **`Q3_U7_TREE_PRESERVATION_AND_EXACT_HEAD_CI_PASS`**: 625→627, 0 deletions, 12 linear forward commits and CI 5/5 / 2875 PASS.
- **`Q3_REAL_EMERGENCY_STOP_AFTER_CANCELLATION_HOLD`** (binding/lease may be lost).
- **`Q3_REAL_NODE_RECEIVE_PAPER_ACK_AND_SETTLING_HOLD`** (no authenticated Native/Paper motor stop outcome).
- **`Q3_PRE_S1_ORIGINAL_OWNER_SOURCE_CUSTODY_HOLD`** (original Producer and independent S1 witness not authenticated).
- **`Q3_UNCOOPERATIVE_CROSS_PROCESS_STDIN_AND_WAL_HOLD`** (one trusted in-process writer does not prove remote receipt).
- **`PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`**. U7 does not authorize real B physical MOVE_PLACE, post-reJOIN shadow, R2 or Science.

**Operational recommendation:** keep I Draft #1124 unmerged and any real MOVE_PLACE grant disabled; a separately qualified host-side emergency STOP fallback with valid session after cancelled lease, a real Native acceptance/STOP ACK and 8+8 tick Paper/World settlement witness, and independently pinned Original S1 are prerequisites to re-elevating the boundary.
