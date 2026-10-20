# S49 cleanup protected-owner isolated review dossier — 2026-10-21

**Classification:** `DEV_ONLY_PATCH_REVIEW / PROTECTED_SOURCE_BLOB_GATE_NO_GO`

- Owner: original S49 Issue #392; related SelfWorld #633 and existing Draft PR #634.
- W4 parent baseline `4fb2a74410ec370aea327bab129a644ade3e9529`.
- Branch `self/product-self-one-command-s49cleanup-20261021` is isolated, not S #545 or W4 #634; NO auto-merge.
- Original S49 protected Git blob: `fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258`.
- Candidate S49 Git blob: `9064982380d1dc7fbc936939c9901ffecd9d8714`; protected change is NOT authorized.
- Existing W4 19-protected-blob test is UNCHANGED; do not rebaseline just to obtain CI green.

## Candidate scope

Original `s49_normal_session_real_ci.qualify()` still runs its original 3-decision/2-Action logic, explicit Stage R gate and issuer. The proposed isolated `finally` patch records bounded Node shutdown and secondary terminate, Java cleanup, temp cleanup and optional W3 capture. It then computes `status`, `rc`, `classification` together. Failures become `FAIL/1/S49_SESSION_NOT_QUALIFIED` and prior FAIL/BLOCKED remain non-PASS. No old receipts are rewritten.

## Synthetic test matrix

The fake-port original-`qualify()` test calls the real original function with all process/world/execution ports replaced. Conditions: Node exit 7, Node shutdown exception, secondary terminate exception with Java still closed, Java exit 8, Java cleanup exception, clean baseline, optional W3 complete capture, missing ACK, foreign session, and W3 nonzero process exit. No Java, Node, real Minecraft, physical action or retained learning is executed.

## Two distinct CI contracts

1. **Original self-demo.yml** (all 19 protected Git blobs): MUST FAIL on the isolated source-edit branch, as it did on run #39515683503. Its red status is intentional source protection and NOT a test to disable.
2. **s49-cleanup-review-dev.yml**: prospective DEV-only Python 3.11/3.12 fake-port contract. It does not disable, replace, or bypass the original protection gate. Green means only candidate behavioral tests passed, NOT authorization for merge, external source custody, qualification or science.

## S49-owner independent admission decision still required

Explicit protected-owner exception/rebaseline review must decide how to handle all frozen blobs and the much older S #545 target before applying this to the original owner branch. Review Stage R, W3 capture, secondary cleanup exception and immutable past runs; never update old expected SHA merely to turn the whole suite green.

Real World, Action/OUTCOME, S10, qualification/science, reused grants = 0. `W4_S49_ORIGINAL_OWNER_LIVE_LEASE_UNDETERMINED`, `W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` unchanged.
