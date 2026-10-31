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


## W4 recovery 2026-10-23 — protected adoption candidate v2 (NOT ADOPTED)

DEV / ENGINEERING VALIDATION only. No World, Minecraft server, bridge,
Action, grant spend, OUTCOME, S10, qualification or science execution.

Starting PR head: `1473c74e4448bb9a527747de0619c8e55ffbd827`.
Preserved unpushed candidate: `78899df900f03119139d5da46d870ac66f57c449`.
Recovered repair branch head: `f31b1a7415cf5244fcdf469aadbee659965480eb`.
Independent recovery branch: `dev/w4-recovery-20261023`.
Worktree: `/home/rinsa/work/relay-self-w4-recovery-20261023`.
Evidence root: `/home/rinsa/w4-recovery-evidence-20261023`.

### Engineering changes and old failures

The actual `f31b1a74` commits supply original S34 `_new_session` abort and
S49 supervised cleanup; the prior `78899df9` reproductions are retained as
new tests without rewriting the old files or logs. Both S34 cancel/exception
paths now reap and seal before ownership returns. Both S49 fault paths
continue to Java cleanup. A normal exception is an existing `rc=1 / FAIL`
report; cancellation is re-raised after cleanup. The old reproduction that
required a leaked ordinary cleanup exception now directly asserts FAIL,
Java cleanup, zero native Actions and atomic report publication instead.

Two additional failures were reproduced before repair, with logs:
- caller cancellation racing a spawn OSError was lost at `await shield`;
  retrieve the spawn terminal under the original cancellation instead;
- Node shutdown could return 0 while the same process exited 7; compare
  the helper result, owned process returncode and confirmed wait result,
  attempt fallback cleanup on disagreement, and reject unconfirmed reap.

Existing opt-in tests explicitly documented the old S49 false-PASS witness
and directed inversion after repair. They now require `FAIL / rc=1 /
S49_SESSION_NOT_QUALIFIED` for the same nonzero/exception faults. Their
synthetic Process supplies the native wait contract. No guard is weakened.

S31A is the original Java readiness/collector owner. The existing recovered
repair monitors ready-or-collector-done in default and raw opt-in routes,
so a collector exception cannot leave the default caller waiting 190 s.
One collector still reads stdout. Existing raw byte capture remains opt-in.

### Formal adoption authority — BLOCKED

Procedure reviewed at exact commits:
- `5e03f7c02cff635996c86c8a850071bb7d639f20`,
  `docs/s49-protected-owner-decision-packet.md`, Decisions A/B/C;
- `f2722a2d0b423fee53272a34b3bbb7f06367beee`,
  `docs/s49-scoped-adoption-v1.md`;
- `175e6ebd62ba5698a4afcb4eb08613c0db96a546`, previous exact variant gate.

A requires a separate authenticated source-owner disposition for EACH
exact protected before/after blob with identity/authority, date, scope,
independently inspected evidence and residual risks. B separately requires
repository/workflow-owner path authority. C requires W4/test-owner approval
of the versioned guard migration. Historical v1 candidate permission is not
approval for different v2 blobs. Current PR reviews are empty; the latest
owner-repair PR comments explicitly retain adoption NO_GO. The user permits
preparing this candidate and executing the procedure, but does not waive
independent approvals. No such exact-candidate receipts were found.

Disposition: **PROTECTED_BLOB_ADOPTION_BLOCKED**. For all four rows below,
source owner / authenticated reviewer / approval date / accepted risk /
receipt URL are **UNDETERMINED**, not supplied by this agent or its tests.
W4 guard-migration approval and new-test path authority are also missing.
No candidate is installed into `PROTECTED_BLOBS`, and that historical guard
continues to FAIL on the proposed sources.

| Protected path | Original SHA256 | Proposed v2 SHA256 |
|---|---|---|
| `adapters/mineflayer/s49_normal_session_real_ci.py` | `0b89333e4d2e74268fdfafbac5e10c6aa6d82398475b3c5160468448d788bc8a` | `e240c6d310254d0e54099a1af9759cc53def817c01e80643fdee51d7ca87b84c` |
| `adapters/mineflayer/s34_native_world_cognition_ci.py` | `b0b6596b4b70924d15d06f53159b56a3e2629677a448f372d50e3c159e26ef38` | `a72beb27d7b5d4730275419b44da2d4a861c317c9acc6d28768f0ee5019c90cc` |
| `adapters/mineflayer/s31a_real_server_ci.py` | `87317a4b9805801f3a36a5f33db8388796fd0e5c1929150f9c73b303fb85c478` | `ef1ee8af15bd88472696a62e27b71138da5b80c7b7b28191403dade2d5d6a1f9` |
| `adapters/mineflayer/process_session.py` | `4c71be38551033cb71839c856e97fb37767047ea9f4bb05a142b36b3a58ee5da` | `8ea47ab2341bfac8bb35531dfae5c35825efb0fb019f5b2e2ab76fabc3967e5a` |

The full 19-file inventory, Git blob IDs and before/after diff are retained
in `protected-manifest.json` and `protected-original-to-proposed.patch` at
the evidence root. Immutable old bytes are preserved under
`original-protected/`; their hash must still match the Git object. The
remaining 15 protected blobs, including S18 manifest, docs, regression and
Action/S10 owners, remain identical. SelfBody/SelfWorld core sources remain
identical to the PR. Historical original evidence SHA256SUMS (72 entries)
was rechecked successfully; no past result is retroactively qualified.

New historical-guard controls accept the original 19 inventory and reject
each of 19 individually substituted hashes. They simulate hashes only to
exercise the unchanged rejection rule, not to authenticate an owner or
accept the actual candidate. Real-tree protected equality remains FAIL.

### Native verification and claim ceiling

Fixtures execute real inert Node 22.22.2 / JVM 21 subprocesses on this
Windows 11 build 26200 / WSL2 Ubuntu 24.04 host, with Python 3.12.3.
The existing JDK was explicitly bound after preserving a javac-PATH failure.
Independent observer PID/starttime acknowledgments gate child handoff,
with signals, wait/returncode, disappearance, collector settlement and
pending-task records. Tests cover original S34 normal/cancel/exception
ownership and original S49 native Node-fault cleanup through both real
processes; Java readiness strings and Node JSONL are synthetic fixtures,
not Minecraft readiness or qualified native World evidence.

CI/FULL/Minecraft were not run. The self-demo push branch filter matches
PR #634; workflow configuration is untouched by this recovery. No push is
attempted because formal adoption is incomplete. PR remains Draft and
unchanged. Final exact-commit commands, JUnit counts, tool versions and
exit codes are external evidence; no all-test pytest or matrix is used.

Required next step: authenticated exact v2 source-owner A dispositions,
repository path-policy B disposition and W4 versioned-guard C disposition.
Only then apply the approved receipt and reverify the guard, contracts and
focused integration at a new exact HEAD before considering any PR push.
W4 external custody/signer trust and fresh World authority remain separate.


## 2026-10-23 prospective v2 adoption update

The preceding NOT ADOPTED/BLOCKED section is the retained pre-migration
record at `f34ccc0bf86f271849034c21abd254e5e3de780f`, not the current
authority disposition. Repository Owner/Admin has since explicitly approved
the four-path adoption, scoped path policy and two-layer guard migration.
Current procedure and immutable historical/prospective hash manifest are
[Adoption v2 Record](w4-protected-adoption-v2.md) and
[v2 manifest](w4-protected-adoption-v2.json). Exact adoption commit results
are recorded in the new external evidence root; earlier failed logs and
World DEV evidence are unchanged. No new World or scientific qualification
is authorized or claimed.
