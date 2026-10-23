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
RelayEngine or provider. A separate checker rejects unknown, unadvertised or
substituted returned choices. Neither stage grants Memory/S10/Action authority.

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
