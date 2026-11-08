# SOUL #800 — K3-G matched L2 choice comparison (DEV pilot)

**Authority:** User requested testing whether MySelf.SOUL biases risk-taking in the same Skill learning task. This is a DEV-only **choice comparison**, not a persistent SOUL/Action or personality qualification. Parent: [K3-G PR #797](https://github.com/rinsakamo/relay-self/pull/797), verified head `c2a22976d131868abddaf548481c39b5e6637d53`. Prior identity A/B/C #220 reported **CLASS E / no reproducible effect** under its old trailing-datum context interface. Preserve that null result.

## Question

Can changing only a short value prior placed in the L2 **system prompt** alter the actual raw decision on the same task/evidence, and does the difference survive the independent schema/meaning validator?

Unlike #220, this experiment tests a provider-visible system prompt; it **does not yet attach the actual persisted** `IdentitySpecification` to a restartable Self. This is a bounded candidate projection, not a second identity authority nor a demonstrated stable-prefix or cache result (#264).

## Conditions and matched controls

Four conditions in predeclared initial order: **neutral → curious → cautious → bold**. These labels are used **only locally**; the provider receives just the value directive, without condition labels or instructions to choose a particular output.

- **neutral**: Exact original K3-G `system_instruction` (no added directive). Run again, do **not** treat the old K3-G transcript as an automatically matched neutral observation.
- **curious**: More relative value to learning from relevant uncertainty, while retaining viability/resource constraints.
- **cautious**: More relative value to preserving viability in poorly understood situations, while not forbidding learning.
- **bold**: More relative value to bounded trial-and-error and tolerated failure, without changing authority.

All 4 calls use the **same** code HEAD, source reports, `train_experiences` of 28 admitted rows, `revision_context`, system **task** instruction, JSON Schema, independent Validator, model, context8192, slot1, reasoning OFF, temperature0 and explicit 10 Action upper bound. The **only** model-facing change is the fixed directive line in the system message, so the rest must be byte identical. Log SHA256 of directive and both request/response originals. No prompt/KV cache reuse.

### Not a forced answer benchmark

Do not reward/favor any particular `SKILL / PROBE / ABSTAIN` result. A predicted pattern `UNKNOWN` remains **invalid for PROBE** under unchanged K3-G contracts. Report **raw** status and **validated** status independently; keep negative results. Do not patch missing predictions after the fact.

This is explicitly **not** a four-choice EXPLORE schema experiment; the common task/Schema is unchanged. A later K3-H may measure unstructured trial-and-error using a different design but must not be mixed into this four-condition matched pilot.

### No actions

Even a valid behavioral-changing Skill is **not executed**; `run_choice(..., evaluate_skill=False)` returns `SKILL_HOLDOUT_SKIPPED_MATCHED_SOUL_COMPARISON`. PROBE is never executed. Never open reserved seeds 20261126, 20261205, 20261213, nor reuse exposed 20261207/20261210 as a blind holdout. No Minecraft World, native S49, Learning/Habit, L0 install or SOUL persistence writes.

## Preflight

Run focused tests against actual parent modules, including:

```bash
python -m pytest -q tests/test_skill_crystallization_soul_matched_dev.py \
  tests/test_skill_crystallization_soul_audit_dev.py \
  tests/test_skill_crystallization_k3g_ten_action_choice_dev.py \
  tests/test_skill_crystallization_k3f_budget_dev.py
python -m ruff check \
  experiments/skill_crystallization_k3g_ten_action_choice_dev.py \
  experiments/skill_crystallization_soul_matched_dev.py \
  experiments/skill_crystallization_soul_audit_dev.py \
  tests/test_skill_crystallization_soul_matched_dev.py \
  tests/test_skill_crystallization_soul_audit_dev.py
```

Audit all historical SHA256SUMS with the existing K3-G `verify_input_manifests` gate. Confirm pinned GGUF sha256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`, llama.cpp build10874, one dedicated server process, GPU mapping, no other lanes stopped. Freeze exact HEAD before any model POST.

## Real Gemma one-shot commands

One **explicit one-shot invocation per condition**. No retry for any condition, and never auto-launch subsequent conditions from inside a model callback. Use a distinct `--record-dir` and `--out` (both exclusive-create) for each. Do not overwrite original K3-G response or its evidence.

```bash
# From the exact child branch with prepared local llama.cpp server.
# Verify the served model ID; substitute it below, without guessing.
for condition in neutral curious cautious bold; do
  python -m experiments.skill_crystallization_soul_matched_dev \
    --condition "$condition" --mode gemma \
    --first evidence/l431-gemma-20261108/first-report.json \
    --k3b-report evidence/l431-k3b-gemma-20261108/report.json \
    --k3d-report evidence/l431-k3d-gemma-20261108/report.json \
    --k3e-report evidence/l431-k3e-gemma-20261108/proposal.json \
    --endpoint http://127.0.0.1:8080/v1/chat/completions \
    --model VERIFIED_LOCAL_MODEL_ID \
    --record-dir "evidence/l800-soul-gemma-20261108/$condition/raw" \
    --out "evidence/l800-soul-gemma-20261108/$condition/report.json"
done
```

**Important:** The shell loop is a convenience example; a stricter protocol is to run one condition explicitly, audit its saved request/response, then invoke the next. If an essential model/process/source invariant changes between calls, stop the matched series and report the interrupted set rather than substituting other settings. Commands are not authorized to fabricate a live provider result in this ChatGPT environment.

## 4-condition independent read-only audit

After all four real model runs are saved, invoke the separate auditor (no HTTP, no mock trials or Action):

```bash
python -m experiments.skill_crystallization_soul_audit_dev \
  --neutral-report evidence/l800-soul-gemma-20261108/neutral/report.json \
  --curious-report evidence/l800-soul-gemma-20261108/curious/report.json \
  --cautious-report evidence/l800-soul-gemma-20261108/cautious/report.json \
  --bold-report evidence/l800-soul-gemma-20261108/bold/report.json \
  --out evidence/l800-soul-gemma-20261108/matched-audit.json
```

The audit compares request/response raw SHA and content against their saved provider records, requires identical request JSON except for exactly the predeclared identity system prefix, requires original neutral system text, rejects outcome/holdout usage, and separates raw-choice divergence from semantically admitted-choice divergence. Run `tests/test_skill_crystallization_soul_audit_dev.py` with focused pytest before model calls. Incomplete/raw-missing runs are a blocked comparison, not an invented null.

## Acceptance & comparison

Before comparing, independently decode the 4 saved raw requests and verify:
1. Same GGUF/model ID, same provider runtime envelope, same generation settings, same input observation/Goal/context/Schema and same task suffix.
2. System text has only the condition-specific identity line; the neutral system text equals the preexisting K3-G exact system instruction.
3. Four different raw directories, exclusive request and response, no auto retries, explicit condition hash and head.
4. Raw status, schema validity, semantic validator validity, source ID usage, selected Skill and branch if valid; also prompt/completion tokens and latency.

A difference in one or four outputs is a **pilot observation, not proof of stable personality**. One-shot random variability, order/time and unequal prompt length can confound. Temperature0 improves reproducibility but does not guarantee identical results. Follow with predeclared matched fresh scenarios or counterbalanced repetitions (with no retroactive prompt edits) only if the pilot warrants.

### Scope

No fixed MySelf SOUL was assigned to the real product Self; this compares *candidate* short value priors. If the four raw choices are the same, report the new local null without changing #220. If results differ, report whether those differences affect **valid choices**, not just the verbal explanation.

**DEV_ONLY / L2_CHOICE_ONLY / SOUL_EFFECT_NOT_PROVEN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
