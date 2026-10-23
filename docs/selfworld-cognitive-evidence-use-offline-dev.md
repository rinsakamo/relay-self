# W4 SelfWorld — Goal-conditioned evidence-use (source-only DEV)

Status: **IMPLEMENTED_IN_ISOLATED_BRANCH / NOT_EXECUTED / NOT_QUALIFIED**.

`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`

Design register: https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6365811426
Parent: `ca0f95ef4cf879fa571cb6c97c6747c5e58a1607`.
Module: `experiments/self_world_cognitive_evidence_use.py`.
Test: `tests/test_self_world_cognitive_evidence_use.py`.

## Independent authority boundaries

The unchanged strict saved replay plus ATT/PRD verifier and
`experiments/self_world_host_two_axis.py::read_epoch` are the only source
entry. The new adapter rechecks record keys, exact source pin, both
source-bound digests, positive provenance category, review binding and
comparison scope. A caller-supplied `claimed_record` must equal a fresh read,
including opaque source identities; it cannot provide independent source
authority.

The host alone determines *admissible* evidence-use strategies:

| Strategy | Host eligibility | Cognitive meaning |
| --- | --- | --- |
| USE_CURRENT_POSITIVE | Positive ATT-selected observation only | Use current source-bound positive; absence of selection != world absence |
| USE_MATCHED_FORECAST_SCOPE | MATCH for identical positively observed target/property/value | Only bounded comparison support; not a World law |
| REQUEST_MORE_EVIDENCE | Cognitively possible | Proposal only, with a fixed nonzero additional-cost placeholder; NEVER an Action |
| WITHHOLD_UNSUPPORTED_CLAIM | Cognitively possible | Do not assert unsupported claim; do not discard positive source |

`GoalSpec(kind, importance, max_additional_cost)` is explicitly *not*
evidence; cost is a DEV cognitive constraint, not metabolic debit.
`available` is the intersection of host-admissible strategies and cost
budget. The host must not choose the optimal strategy. When the goal is absent
or fewer than two choices remain, `request=None,status=DEFER`.
Otherwise it emits the **existing** `BoundedChoiceRequest`, without invoking
RelayEngine or provider. A separate checker **re-reads the original strict source** at selection acceptance,
regenerates the entire candidate/request/custody record, and rejects unknown,
unadvertised, goal-substituted or wholly forged request/manifest records.
This is not a one-time delivery/consumption lease: an identical reply to an
identical static DEV request cannot be distinguished without an existing
lifecycle owner. Neither stage grants Memory/S10/Action authority.

## Separation of custody and model-facing surface

`custody_manifest` preserves full binding and source, observation and review
digests at the host only. Never pass this dataclass or its manifest to the
renderer/model. Only `prepared.request` is potentially model-facing, with
fixed pseudo-provenance (not real World evidence), sanitized positive
properties, review status, limited MATCH scope and distinct goal. Raw
`self_id/session_id/epoch_id/entity_ref/source_ref/provenance/receipt SHA`
are not projected. Model answers cannot re-enable ineligible strategies,
certify the source, infer World absence or success, or issue real actions.

For MISMATCH following, skeleton is usable as *current positive* while the
old zombie forecast is *not* usable as matched support. MATCH following can
make matched support available *only* for the compared property/target.
UNKNOWN following remains zero selected positives + UNDETERMINED; prior
forecast NO_REVIEW can coexist with a real forecast but cannot imply MATCH.
The existing RAW 20/40 -> SEM 36/40 rubric and all its evidence remain
historical and unchanged; this code does not re-score it.

## Gates before further use

Run on a separate real Linux/WSL2 worktree with Python 3.12:

1. Confirm exact base HEAD, 3-file DEV allowlist, no edits to reader/core,
   renderer/RelayEngine/provider/action/learning/CI owners.
2. `python3.12 -m pytest -q tests/test_self_world_host_two_axis.py tests/test_self_world_cognitive_evidence_use.py`,
   plus existing focused dependencies; Ruff and repository contracts.
3. Strict source fixture 10 epochs x 2 goals; source/provenance, digest and
   protected metadata leak negatives. If any test fails, correct only new DEV
   files, record failed evidence and rerun locally.
4. Create a new repo-external exclusive output directory and attest untouched
   82 protected blobs, 770 historical index, prior A/B/factorial/neutral,
   SEM and two-axis original files, with before/after SHA. No overwrites.
5. Confirm Draft PR #634 still at its original HEAD, unmerged. No merge of this
   branch and no claim that source-only DEV constitutes actual LLM performance.

CI, FULL regression, GPU/LLM, Minecraft, Action, OUTCOME, Memory/S10,
qualification and science are **not authorized for this step**. New isolated
branch commits carry `[skip ci]`. Python 3.12 runtime and source file
integrity are NOT verified in the GitHub-only implementation session. The
result remains `SOURCE_ONLY_NOT_QUALIFIED` until independent host execution.

## Independent Windows / WSL2 DEV validation (2026-10-23)

The source-audited remote HEAD was `337a9b7df7cf64ad4661d400a71dbed2d723b12e`.
Its immediate parent is `8d52ca10939697c52f0f2143eda4ef5101584143`;
`ca0f95ef4cf879fa571cb6c97c6747c5e58a1607` is the registered comparison base
(ten preparation commits), with exactly the three permitted added files.
An independent detached worktree was used. Runtime: Ubuntu 24.04.4 / WSL2,
Python 3.12.3, existing RSEE venv, pytest 9.1.1 and Ruff 0.16.7.

Initial focused validation found one redaction-test failure: the fixture's
single-letter self ID `A` also occurs inside fixed strategy names such as
`CLAIM`. The repaired test recursively checks complete JSON string values
for short IDs, retaining substring checks for longer identities and digests.
This changes no evidence eligibility or model-facing content. Ruff also found
one import-format error, corrected only in the new adapter. Additional negative
controls directly verify fresh source reload at selection acceptance, full
candidate/custody regeneration, and independent goal-kind/cost constraints.
Initial failures and repaired runs are retained in an exclusive external root:
`/home/rinsa/verification-evidence/w4-cognitive-independent-20261023T140100Z`.

The real saved source `1e86a714f3ea3374` was loaded through unchanged strict
replay; four original synthetic factories supply the other cases. Each of ten
epochs was checked with `EXPLAIN_OBSERVED` (budget 0) and `ASSESS_FORECAST`
(budget 0.5). Every available strategy in every READY request was accepted only
after re-reading the fixed source and rederiving the entire envelope. A sole
remaining strategy produces DEFER, preserving the existing two-choice contract.

| Case / epoch | Positive | Review | Current / matched eligible | Explain, cost 0 | Assess, cost 0.5 |
| --- | --- | --- | --- | --- | --- |
| saved-empty / prior | 0 | NO_REVIEW | no / no | DEFER: W | READY: R,W |
| saved-empty / following | 0 | NO_REVIEW | no / no | DEFER: W | READY: R,W |
| match / prior | 1 zombie | NO_REVIEW | yes / no | READY: C,W | READY: C,R,W |
| match / following | 1 zombie | MATCH | yes / yes | READY: C,M,W | READY: C,M,R,W |
| mismatch / prior | 1 zombie | NO_REVIEW | yes / no | READY: C,W | READY: C,R,W |
| mismatch / following | 1 skeleton | MISMATCH | yes / no | READY: C,W | READY: C,R,W |
| unknown / prior | 1 zombie | NO_REVIEW | yes / no | READY: C,W | READY: C,R,W |
| unknown / following | 0 | UNDETERMINED | no / no | DEFER: W | READY: R,W |
| synthetic-empty / prior | 0 | NO_REVIEW | no / no | DEFER: W | READY: R,W |
| synthetic-empty / following | 0 | NO_REVIEW | no / no | DEFER: W | READY: R,W |

C=current positive, M=matched target/property/value only, R=request more evidence,
W=withhold unsupported claim. These are eligibility sets, not optimal-strategy
labels. NO_REVIEW does not establish forecast absence or MATCH; UNDETERMINED
and zero positives establish neither prediction failure nor World absence/safety.
Goal kind and importance are independent request inputs; only the explicit cost
budget filters availability. No cognitive optimality or measured cost is claimed.

The historical SEM archive was reconciled read-only and exactly reproduced the
prior audit (RAW 20/40, SEM 36/40 unchanged). Integrity checks cover 82 protected
targets in the new worktree and original locations, all 770 historical entries
and their index, seven prior evidence trees including original SEM and host
two-axis, and ten additional source/authority path hashes. Full per-file hashes,
initial/final test logs, JUnit counts and the 20-row matrix remain external.

No CI, FULL regression, real LLM, GPU, Minecraft, physical Action, new physical
OUTCOME, retained Memory/S10 update, qualification or SCIENCE was executed.
Dependency tests use offline fixtures and fake providers only. Static identical
responses still require a future existing-owner consumption lifecycle; this
adapter creates no one-use authority. Future real-LLM necessity and scientific
validation require separate review and registration after this DEV result.

Final independent gate: **245 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, Ruff **PASS**,
repository contracts **PASS**. Initial focused run: 242 PASS / 1 FAIL / 0 ERROR /
0 SKIP; repair-only run: 29 PASS. Initial Ruff failure is retained. SHA before /
after comparison **PASS**. Completion:
`W4_SELF_WORLD_COGNITIVE_EVIDENCE_USE_OFFLINE_DEV_RESULT`.
`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
