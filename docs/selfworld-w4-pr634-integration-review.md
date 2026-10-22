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
