# K3-H: Free bounded trial, mock Outcome and new L2 decision

**Classification: DEV_ONLY / REAL_GEMMA_NOT_RUN / NO_REAL_S49 / NO_SKILL_INSTALL / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

Parent: Learning #431, K3-G PR #797, frozen HEAD c2a22976d131868abddaf548481c39b5e6637d53. This branch excludes MySelf.SOUL #800 / PR #801 by design. No SOUL is injected into the model. The old K3-G PROBE / prediction UNKNOWN remains rejected in that earlier contract.

## Research question

Can L2 choose a small bounded trial while uncertain, observe the new physical-like mock result, and freely choose a next action or tentative Skill? A prior hypothesis or success prediction is **not mandatory**. The exercise does not demonstrate actual learning, physical skill competence or personality.

## Prospective choice and explicit Action envelope

L2 receives the same 28 original observations and source-qualified old Skill, plus an explicitly described **two-arm candidate World**:

- A: normal surface, reference movement regime, start distance 2.4m
- B: normal surface, possible changed movement regime, start distance 2.4m

Actual latent synthetic per-Action effects and future outcomes are withheld. Unlike K3-G, A/B allocation is declared before making a prediction and identical in the eventual mock executor.

Accepted decisions: TRY_MOVE (choose A or B, up to 10 MOVE_AWAY), COMPARE_ARMS (each of A/B up to 10 MOVE_AWAY), OBSERVE_ONLY (read already public cue; no new motion Outcome), DEFER (nothing). Zero Action applies only to OBSERVE_ONLY / DEFER. In all executing arms, stop as soon as Goal distance 3.2m is reached. A paired comparison can spend at most 20 mock Actions, 10 per arm. Model can voluntarily choose fewer.

The optional prediction field may be UNKNOWN and is **valid**. A specific prediction is saved prospectively, never invented after Outcome. Every execution requires independent JSON Schema PASS and semantic envelope PASS.

## Three separate, operator-invoked phases

1. PROPOSE: one real Gemma structured request (or offline fixture), raw request/response saved exclusively. No Action or mock Outcome. Do not treat model language as Action permission.
2. EXECUTE-MOCK: only after valid proposal and explicit --mock-grant. Verify raw model request SHA, original evidence and schema, raw response equals proposal, then run only selected synthetic arms. Persist source session, initial/final distance, trace, actual action count, Goal outcome and evidence IDs. DEFER creates no result; OBSERVE_ONLY provides a cue only, not fabricated physical knowledge.
3. REFLECT: before another one-shot L2 request, reconstruct Phase B deterministic mock result from source-qualified original proposal. Do not send unchosen arm outcomes, unspent motion effects or future trial seeds. L2 may choose TRY_MOVE / COMPARE_ARMS / OBSERVE_ONLY / DEFER and optionally propose a typed tentative Skill. Validate its evidence IDs and maximum 10 Actions. **Never install it or evaluate on hidden holdout in this phase.**

For real model trial only, reserve new synthetic seed **20261219**, unopened until Phase A is valid and Phase B receives explicit --mock-grant. Offline fixtures use separate exposed 20261217. Never consume prior reserved seeds 20261126 (K3-D), 20261205 (K3-E), 20261213 (K3-G). No real World/S49 action, Memory/Habit write, autonomous Skill install, or SOUL modification.

## Local preflight

From the exact K3-H branch, audit GitHub HEAD/PR, original evidence manifests and llama.cpp model identity. Test focused original and new tests, Ruff and repository contracts before any GPU spend.

Focus commands:

    python -m pytest -q tests/test_skill_crystallization_dev.py tests/test_skill_crystallization_k3b_dev.py tests/test_skill_crystallization_k3c_dev.py tests/test_skill_crystallization_k3d_dev.py tests/test_skill_crystallization_k3e_dev.py tests/test_skill_crystallization_k3f_budget_dev.py tests/test_skill_crystallization_k3g_ten_action_choice_dev.py tests/test_skill_crystallization_k3h_free_try_dev.py
    python -m ruff check experiments/skill_crystallization_k3h_free_try_dev.py tests/test_skill_crystallization_k3h_free_try_dev.py

Model constraints: Gemma-4-12B-it Q4_K_M, GGUF SHA256 c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed, llama.cpp build10874, context8192, slot1, strict JSON Schema ON, reasoning OFF, temperature0, dedicated PID/mmap/GPU checked. No auto retries; one explicit model HTTP POST per phase. Other lanes must remain unaffected.

Original reports:

    evidence/l431-gemma-20261108/first-report.json
    evidence/l431-k3b-gemma-20261108/report.json
    evidence/l431-k3d-gemma-20261108/report.json
    evidence/l431-k3e-gemma-20261108/proposal.json

## CLI instructions

Use one common argument set:

    --first evidence/l431-gemma-20261108/first-report.json
    --k3b-report evidence/l431-k3b-gemma-20261108/report.json
    --k3d-report evidence/l431-k3d-gemma-20261108/report.json
    --k3e-report evidence/l431-k3e-gemma-20261108/proposal.json

Phase A, explicit real model call:

    python -m experiments.skill_crystallization_k3h_free_try_dev --phase propose --mode gemma [COMMON] --endpoint http://127.0.0.1:8080/v1/chat/completions --model VERIFIED_MODEL_ID --record-dir evidence/l431-k3h-gemma-20261108/proposal/raw --out evidence/l431-k3h-gemma-20261108/proposal/report.json

If VALID_BOUNDED_CHOICE is missing, stop. If DEFER, no new experience / Phase C.

Phase B, explicit DEV-only mock grant, **not native S49**:

    python -m experiments.skill_crystallization_k3h_free_try_dev --phase execute-mock --mode gemma [COMMON] --proposal-report evidence/l431-k3h-gemma-20261108/proposal/report.json --mock-grant --out evidence/l431-k3h-gemma-20261108/outcome/report.json

Phase C, second explicit model call after qualified mock Outcome:

    python -m experiments.skill_crystallization_k3h_free_try_dev --phase reflect --mode gemma [COMMON] --proposal-report evidence/l431-k3h-gemma-20261108/proposal/report.json --outcome-report evidence/l431-k3h-gemma-20261108/outcome/report.json --endpoint http://127.0.0.1:8080/v1/chat/completions --model VERIFIED_MODEL_ID --record-dir evidence/l431-k3h-gemma-20261108/reflection/raw --out evidence/l431-k3h-gemma-20261108/reflection/report.json

Replace [COMMON] with the four exact switches above, and VERIFIED_MODEL_ID with the actual served model ID. Never overwrite a saved output or raw request/response, never add a model retry. Keep original SHA256SUMS files unchanged.

## Measurement and reporting

Report the raw Phase A proposal, optional prospective prediction, independent schema and semantic validity, model token/latency cost, phase B action count and observed traces, the relationship of predictions to observed outcomes when applicable, and raw Phase C reflection/Skill (if any). Distinguish valid hypothesis changes from merely changed prose. Even when a valid Skill is proposed, qualification for reusable L1/Habit requires **later independent gate and retained epoch evidence**; none is granted here.

Run independent source and mock replay audits; save manifests and report to Issue #431, child PR, and relevant #426. Main and other lanes remain unchanged. Confirm GPU release and repository CI. Classification stays DEV_ONLY / NO_REAL_WORLD / NO_FORMAL_LEARNING_UPDATE / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
