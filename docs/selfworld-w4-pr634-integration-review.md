# W4 observation-only DEV — PR #634 bounded integration candidate

## Source and protected scope
- Target Draft PR #634 branch: self/product-self-one-command-selfbody-20261018
- Exact target parent before candidate: 1473c74e4448bb9a527747de0619c8e55ffbd827
- Original independent real DEV successful HEAD: 1b221d845e42ea0e8be003239525c50de20e7fef
- Original read-only observation proof: run 1e86a714f3ea3374; DEV_LOCAL_OBSERVATION_ONLY_PASS; Action/OUTCOME/S10 = 0/0/0
- The current integration is code only; no historical original observation archive is rewritten or retroactively requalified.
- Qualified original run is **not** evidence of this integration candidate's runtime correctness.
- Parent SelfBody / SelfWorld code, prior user-approved CI jobs and protected 19 original evidence objects must remain unchanged.

## Scope of source transfer
1. Seven self_world_observation_only_* modules and seven focused test modules from the exact successful W4 HEAD.
2. startup_process_ownership.py (new): bounded native child spawn/cleanup supervision used by the W4 session/collector.
3. process_session.py and s31a_real_server_ci.py from W4 HEAD: **PROTECTED original-owner changes** needed for cancellation custody and sole-Java collector raw capture. They require independent owner review before integration into PR #634.
4. Existing `.github/workflows/self-demo.yml` is based on PR #634; only explicit source allowlist, Python 3.12 FAST focused test names are inserted. Older SelfWorld one-shot review jobs and triggers remain, and FULL is not scheduled.
5. This document is an integration review manifest, not a scientific or DEV run authority.

## Exclusions
- NO automatic copy of all W4 commits, no merge of their Git history.
- NO copy of W4 versions of s49_normal_session_real_ci.py, s34_native_world_cognition_ci.py, or self_world_stage_w4_optin_offline.py.
- NO rewrite of existing SelfBody/SelfWorld source files, protected evidence, or earlier World run.
- NO local Minecraft/Node/java action, no CI dispatch/rerun, no FULL, no merge, and no PR head update until tests and owner review.

## PRE-MERGE REQUIREMENTS — remain UNVERIFIED
- Fixed candidate HEAD, clean detached WSL2 worktree, Python 3.12, local focused test suite for seven observation files and original S49 process cancellation/custody, S18 freeze regression, Node 37, Ruff, contracts.
- Confirm no unintended coupling to the excluded original S49/S34 owner changes; trace all subprocess startup/cancellation and single stdout collector paths.
- Confirm user-approved CI pause is respected. If the integration review later updates PR #634, keep Draft and use [skip ci]; no other branch may be touched.
- Compare source object hashes for exact transferred modules/test files, and entire original 1010-line workflow retained aside from narrow additions.

Status: **INTEGRATION_CANDIDATE_ONLY / NOT TESTED / NOT APPLIED_TO_PR / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.


## 2026-10-23: Independent source-level owner-API review (NOT runtime PASS)

Review of the target PR #634 HEAD and the exact donor W4 HEAD found:
- PR \`MineflayerProcessSession.launch\` and W4 candidate both preserve
  \`config, bridge_path, node_executable, startup_timeout_s,
  raw_capture_root, w4_native_orientation_dev\`.
  Candidate substitutes \`spawn_with_custody\` and catches
  \`BaseException\` to supervise startup cleanup, requiring direct cancellation
  regression rather than relying on matching signatures.
- Original PR \`s31a_real_server_ci._ready_server(root, jar, log_path)\` is
  source compatible with the candidate signature that adds
  keyword-only optional \`raw_stdout_path=None\`. A sole Java collector is
  maintained in source; failure/cancellation and PID ownership require
  actual focused tests after integration.
- Candidate does NOT incorporate W4 donor
  \`s49_normal_session_real_ci.py\`,
  \`s34_native_world_cognition_ci.py\`, or the older opt-in staging module.
  Existing S49/S34 are therefore protected from silent upstream replacement.
- The donor \`tests/test_s49_startup_ownership.py\` contains cases that
  exercise donor S34 \`_new_session\`/startup transfer. These cannot be
  copied blindly as evidence for the target PR S34, whose original code is
  intentionally retained. Native OS custody fixture similarly does NOT by
  itself attest the integrated target owner.
- No full repository bytes or installed WSL2 Python 3.12 runtime are
  available inside the current ChatGPT tool environment. The public repo
  cannot be cloned here. **No integrated source was executed here**.
  A static review is not a test result and cannot justify changing PR head.

### Exact-head LOCAL CODEX verification recipe

Check out \`self/w4-pr634-integration-review-20261023\` in a fresh clean
isolated WSL2 worktree at the exact HEAD written in the GitHub branch.
Use Python 3.12 and \`PYTHONPATH=src:tests:.\`; no CI dispatch and no physical
Minecraft. Focused tests must include:
- \`tests/test_self_world_observation_only_*.py\`
- \`tests/test_mineflayer_process_session.py\`
- \`tests/test_feature_s49_normal_runtime.py\`
- \`tests/test_self_body.py\`, \`tests/test_self_world.py\`
- \`tests/test_postmain_architecture_freeze.py\`
- \`tests/test_self_world_stage_w4_lease.py\`,
  \`tests/test_self_world_stage_w4_optin_offline.py\`

Before any promotion, add/evaluate focused cancellation tests on the
*retained target S49/S34* call sites and W4 native child-creation path,
including a real inert-process (NOT Minecraft) OS-PID cancel/reap test.
Use DEV fixtures, independent cleanup inventory, 0 FAIL, 0 SKIP.
Check \`ruff check src tests experiments adapters observability\`,
\`python tools/check_repository.py\`, and the existing Node adapter checks
under Node 22. Preserve receipt for the exact HEAD.

Only when these are verified and protected owner review is accepted:
1. Re-read PR #634 HEAD; require it still equals its frozen parent.
2. If candidate advanced during repair, independently review new diff and
   re-run exact-head verification before touching the PR branch.
3. Fast-forward PR HEAD using an expected-SHA lease; keep Draft and
   [skip ci] while the user has CI paused; do not merge.
4. Report local results and branch SHA; do not re-run historic World DEV.

Until then: \`STATIC_API_REVIEW_DONE / OFFLINE_EXECUTION_UNVERIFIED /
PR_UNCHANGED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN\`.


## 2026-10-23 isolated original-owner cleanup repairs (prospective, not yet qualified)

The previous LocalCodex exact HEAD 78899df900f03119139d5da46d870ac66f57c449
is **LOCAL ONLY and not accessible via GitHub**. Do not overwrite or
backfill its report. This new independent branch is based on the published
W4 PR634 integration candidate 557027be732362e021cceeb8aaa503f2f80acfe0.

- S34 _new_session(): local cleanup now calls the already-installed
  MineflayerProcessSession.abort_startup() after native spawn cancellation
  or any BaseException, preserving primary fault and treating cleanup
  failure as UNCONFIRMED rather than an owner success.
- S49 qualify(): existing decision/Action/S10 code is byte-for-byte kept.
  Owner-supplied cleanup and final-status logic are taken from the independent
  original-owner DEV implementation previously exercised at donor HEAD
  1b221d845e42ea0e8be003239525c50de20e7fef.
  This serially supervises staging, Node shutdown/terminate/reap,
  raw capture incomplete sealing, Java shutdown/reap, collector and temp,
  even after a preceding cancel/secondary exception. Cleanup faults revoke
  provisional PASS; original same-session report is atomically persisted.
- The donor synthetic cancellation tests for S34/startup and S49 cleanup are
  preserved as standalone test files, without modifying the original frozen
  evidence or adding a second owner.
- The historical W4 original-blob guard still contains all 19 exact
  pre-adoption SHA pins and **has not been modified or bypassed**.
  Prospective adoption of the 4 changed protected startup/owner blobs
  (S31A, ProcessSession, S34, S49) requires explicit owner review of exact
  baseline/candidate diffs. Until reviewed, the old W4 original-default
  test is **EXPECTED TO FAIL**, not skip/xfail, and integration to PR #634
  remains blocked. S18 architecture freeze is a separate static gate.
- This is a source repair only. Python 3.12, Node 22, Ruff, contracts,
  focused regression, and inert OS PID tests MUST be run on this new exact
  HEAD in WSL2. No current-head runtime PASS is claimed. No Minecraft,
  CI dispatch or physical Action is permitted for this review.


### S31A legacy collector early-failure correction

The earlier LocalCodex unpushed candidate reported a separate repaired
default S31A readiness gap. This branch independently implements the
minimal correction: both \`raw_stdout_path=None\` (old three-argument
owner) and opt-in raw capture now wait on the **same existing sole
collector's** ready-or-done event. If it has already ended, its error is
retrieved immediately and the original process is terminated/reaped.
No second Java reader or alternate server launcher is introduced.
A two-arm offline fault fixture (raw off/on) is added to
\`tests/test_s49_startup_ownership.py\`. These tests have NOT yet been
run against this candidate HEAD.
