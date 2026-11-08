# RelaySelf K3-E — experience → falsifiable hypothesis → bounded probe → reassessment

Status: **DEV_ONLY / LOCAL_FIXTURE_ONLY / NEW_REAL_GEMMA_NOT_RUN / NO_REAL_WORLD / NO_S49 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

Parent Draft PR #793, exact parent HEAD ab1eaf5b7d9d2bde499df0558478e51f6e28b3f3.
Learning/Habit #431; physical Action owner #537.

## Why this experiment exists

K3-D's real Gemma returned ABSTAIN, with a partly accurate observation of four MOVE_AWAY actions and failed end distances, but with the unsupported claim that its current Skill was "already optimized". K3-E tests whether L2 can propose a **falsifiable question** and interpret new controlled outcomes instead of repeatedly producing the same Skill.

It does not require learning improvement on one episode, does not assert optimality or physical impossibility, and does not allow an LLM-generated Skill to become executable autonomously.

## Two-stage protocol (each model call separately optional)

Phase 1: PROPOSE

- Input: #790 first observed training evidence, #791 verified shifted observations, #793 ABSTAIN reason and existing old Skill. No hidden physical generator, probe outcomes or unopened holdout.
- One real Gemma response (if run locally) with a closed strict JSON Schema: status PROBE/ABSTAIN, source-supported hypothesis, one of two pre-registered probe identifiers, a falsifiable expected pair pattern, rationale, and observed evidence IDs.
- Permitted hypotheses: START_MARGIN_SENSITIVE, MOTION_EFFECT_CHANGED, INDETERMINATE.
- START_MARGIN_PAIR compares start 2.32m (A) with start 2.44m (B) under the **same** synthetic changed-motion effects, max four moves each.
- MOTION_REGIME_PAIR compares reference (A) and changed (B) motion regimes at the **same** start 2.40m, with shared sampled quantiles and max four moves each.
- Never expose the hidden effect magnitudes or future outcomes before a validated proposal.
- On ABSTAIN: no probe execution; mark stage as PROBE_ABSTENTION_ACCEPTED.
- On invalid Schema, unknown evidence, inconsistent hypothesis/probe/prediction: no probe.
- On PROBE: the isolated MockIssuer executes **two fresh trials**, at most four MOVE_AWAY each, with an explicit mock-only grant, recording original mock trace, source session, Outcome and the predicted-vs-observed classification.
- A pair result does not establish a general causal mechanism; a correct one is not yet an autonomous Skill revision.

Phase 2: REASSESS (separate invocation, only if an actual phase-1 PROBE report exists)

- Deterministically reconstruct the probe from its original fixed seed and compare every retained observation byte-equivalent at the data-object level. Tampered success flags, traces, forged evidence IDs and mode mismatches are refused before any model request.
- Pass the new **observed** A/B experience and the prior hypothesis to L2 for another single structured RESPONSE: UPDATE or ABSTAIN, current hypothesis and explanation, cited experience IDs, optional bounded typed Skill candidate.
- An optional Skill candidate uses the existing 1..4 Skill Validator and execution-semantic comparator, but **is not executed, installed, or passed to the K3-D reserved holdout**.
- No new C1 owner, S49 issuer, actual native WorldBody Action, persistent Habit/Memory update or automatic Skill promotion.

Both local model requests use the existing one-shot llama.cpp POST client, with a new explicit system_instruction to avoid the old "you must generate Skill" prompt. Existing client preflight, HTTP/raw evidence and no-retry protections are retained.

## Frozen seeds and contamination discipline

- The earlier K3-D unseen Skill evaluation seed **20261126 remains unopened** and is never referenced by a World generator here.
- **20261124** is the exploratory fixture probe seed, now examined and ineligible as any new blind test.
- **20261128** was unintentionally opened in an early mocked-endpoint test of the proposed K3-E harness; it is **retired** and must never be claimed unseen.
- **20261205** is the replacement **real Gemma probe seed**. The unit tests only inspect this number as a reserved value; they never materialize its World trials. Phase 1 may open it only after an actual accepted PROBE proposal.

Fixture observations at seed 20261124:
- START_MARGIN_PAIR: prediction A_FAILS_B_SUCCEEDS, observed A_FAILS_B_SUCCEEDS; total 8 synthetic Actions.
- MOTION_REGIME_PAIR: prediction A_SUCCEEDS_B_FAILS, observed BOTH_SUCCEED; total 6 synthetic Actions. This is a deliberate falsified-prediction negative control, not a learning success.
- A separate fixture UPDATE cites the two new mock experience IDs. This is not real Gemma self-correction.

## Local reproduction and original-source check

Use a clean child worktree at the exact K3-E HEAD. Python 3.12 and jsonschema required for independent wire validation.

~~~bash
python -m pytest -q \
  tests/test_skill_crystallization_dev.py \
  tests/test_skill_crystallization_k3b_dev.py \
  tests/test_skill_crystallization_k3c_dev.py \
  tests/test_skill_crystallization_k3d_dev.py \
  tests/test_skill_crystallization_k3e_dev.py

python -m ruff check \
  experiments/skill_crystallization_dev.py \
  experiments/skill_crystallization_k3e_dev.py \
  tests/test_skill_crystallization_k3e_dev.py
~~~

Verify immutable SHA256SUMS in evidence/l431-gemma-20261108, evidence/l431-k3b-gemma-20261108, evidence/l431-k3d-gemma-20261108 before any new HTTP request. K3-E's deterministic replay is a mock-fixture check, **not independent Minecraft source attestation**.

Before actual Gemma POST check GGUF SHA256 c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed, llama.cpp build10874, owned process/maps, GPU, served model ID, context8192, slot1, Reasoning OFF and Strict JSON Schema wiring.

If the verified model is available and specifically run from the LocalCodex host, **one** phase-1 POST, no automatic retries:

~~~bash
python -m experiments.skill_crystallization_k3e_dev \
  --phase propose --mode gemma \
  --first evidence/l431-gemma-20261108/first-report.json \
  --k3b-report evidence/l431-k3b-gemma-20261108/report.json \
  --k3d-report evidence/l431-k3d-gemma-20261108/report.json \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model VERIFIED_LOCAL_SERVED_MODEL_ID \
  --record-dir evidence/l431-k3e-gemma-propose-20261108 \
  --out evidence/l431-k3e-propose-20261108.json
~~~

Only if the response is PROBE and the original mock observations are verified, a separately initiated second L2 call can reassess them:

~~~bash
python -m experiments.skill_crystallization_k3e_dev \
  --phase reassess --mode gemma \
  --first evidence/l431-gemma-20261108/first-report.json \
  --k3b-report evidence/l431-k3b-gemma-20261108/report.json \
  --k3d-report evidence/l431-k3d-gemma-20261108/report.json \
  --proposal-report evidence/l431-k3e-propose-20261108.json \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model VERIFIED_LOCAL_SERVED_MODEL_ID \
  --record-dir evidence/l431-k3e-gemma-reassess-20261108 \
  --out evidence/l431-k3e-reassess-20261108.json
~~~

The localhost endpoint is illustrative; use only the server/process independently verified as user-owned. The CLI output uses exclusive-create, and the underlying client uses exclusive raw request creation to prevent accidental replay. Verify cleanup and manifests, and report call counts accurately. The stage 2 call must not occur on a rejected or abstained Stage 1.

## Interpret outcomes precisely

- PROBE_PROPOSED: admissible structured next test, not proven useful.
- MOCK_PROBE_OBSERVED: two synthetic Outcome traces recorded, not actual S49.
- PREDICTION_MATCHED / PREDICTION_FALSIFIED: observation-to-forecast comparison only.
- REASSESSMENT_VALIDATED: L2 structured response independently accepted. This does **not** establish that its reasoning is true.
- SKILL_CANDIDATE_ONLY_NOT_EXECUTED: tentative revised skill, not a new installed L0 or evidence of Goal improvement.
- ABSTAIN: valid restraint, neither optimality nor physical infeasibility proof.

Unchanged: old real-model responses, immutable evidence, and unopened seed 20261126.

## H1: source handoff, prediction/understanding markers (2026-11-08)

Follow-up code on this same Draft PR, without a new model POST or new physical actions:

- Report `PREDICTION_MATCHED` / `PREDICTION_FALSIFIED` independently from whether a hypothesis is later kept, changed, or withheld.
- The reassessment stage records `HYPOTHESIS_CHANGED`, `HYPOTHESIS_RETAINED` or `HYPOTHESIS_WITHHELD`. None of these labels proves that the reason is correct; `reason_truth=NOT_INDEPENDENTLY_VERIFIED` is explicit.
- A report labeled `mode=gemma` is not sufficient authorization to reach stage 2. The saved one-shot provider record must contain HTTP 200, finish stop, no reasoning content, a matching request SHA256, the exact input observations, strict probe Schema and the returned proposal matching the original response message. It must then also pass the unchanged deterministic mock-observation replay.
- These checks only establish **local data self-consistency**. They do not independently authenticate the original provider, native S49 observation, model memory mapping or user CPU/GPU. Actual run evidence and the original request/response bytes must still be independently audited.
- Both real-model phases require an explicit raw-record directory (`--record-dir`), and the client exclusively creates raw request evidence; no raw-less Gemma call is admitted by K3-E.
- Negative controls reject forged report mode, request hash, response text and omitted raw-record directory *before* accessing the reserved real probe seed.

The H1 changes were checked in a local Python 3.13 worktree using test-only shims for K3-B/C/D: **24 focused tests PASS**, syntax compilation PASS. This is **not** integrated repository CI, Ruff or a real Gemma run. Github CI remains unconfirmed for the child Draft branch; do not replace this with a blanket PASS claim.

Additional gates for the eventual LocalCodex run: use the exact K3-E GitHub HEAD; run focused pytest against the real parent modules and Ruff; audit #790/#791/#793 evidence manifests; verify pinned GGUF hash, build10874, context8192, slot1, model ID, reasoning OFF and owned GPU/server. Run phase 1 only once and allow phase 2 only if phase 1's PROBE was accepted and observations verified. Do not open seed 20261205 in a dry-run or before the actual accepted real L2 PROBE. Reserve K3-D Skill holdout seed 20261126.

## Real Gemma Phase A (2026-11-08)

DEV_ONLY. Inference HEAD 46b38ac4; original evidence and runtime readback are in `evidence/l431-k3e-gemma-20261108/`. One POST returned a schema-valid ABSTAIN, INDETERMINATE / NONE / UNKNOWN. The explanation repeated an unsupported assertion that the old Skill was optimized. This is not evidence of optimality. Phase B and C were not run under the stop rule; neither the reserved probe seed nor the K3-D holdout was opened. No cognitive loop, Skill improvement, real World, S49 Action, Memory/Habit update, qualification or science is claimed. Raw request/response, independent readback, resource and cleanup evidence are retained. The CLI now separates proposal from mock execution so the raw proposal can be audited before opening the probe seed.
