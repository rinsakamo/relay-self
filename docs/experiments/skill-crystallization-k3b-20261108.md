# RelaySelf K3-B — constraint-aware Skill revision (DEV)

Status: **implementation + offline fixture validation only**. This child of Draft PR #790 does not claim a new real Gemma revision call or real Minecraft execution. The previous #790 raw Gemma responses, evidence, and SHA256 manifest remain unchanged.

## Parent and constraints

- Parent Draft PR: https://github.com/rinsakamo/relay-self/pull/790
- Exact parent SHA: `3fadeaa63dfe1e6f5903463c7e6bbc45ddaf9232`.
- Source of earlier input: `evidence/l431-gemma-20261108/first-report.json` and `revision-continuation.json`.
- #790 proposed five actions but the existing bounded mock runner permits only **1–4**. That proposal is correctly rejected and must not be relabeled successful.
- The wire schema now enumerates permissible values **1, 2, 3, 4**, while the independent Python Validator retains the original bound.
- K3-B response is a closed object `{status,reason,skill}`; status is `SKILL`, `ABSTAIN` or `UNSATISFIABLE_WITHIN_BUDGET`. Non-SKILL response requires `skill=null`; a SKILL proposal requires existing valid C3-style cues, observed evidence IDs, original Action and budget.
- `UNSATISFIABLE_WITHIN_BUDGET` is **Gemma's tentative judgment, not a mathematical proof** about World/Body physics.

## Offline reproduction

At repository root on the proposed child branch:

```bash
python -m pytest -q tests/test_skill_crystallization_dev.py tests/test_skill_crystallization_k3b_dev.py
python -m ruff check experiments/skill_crystallization_dev.py experiments/skill_crystallization_k3b_dev.py tests/test_skill_crystallization_k3b_dev.py
```

The K3-B tests use in-process fixture proposals and HTTP mocks; **they do not call real Gemma**. Independent `jsonschema` validation runs when that optional package is installed. No automatic retry or extra World step is part of the test.

If the pinned local Gemma server is available, **preflight** exact GGUF SHA256, model id, running process, llama.cpp build 10874, 8192 context, 1 slot, Strict JSON ON, Reasoning OFF and GPU ownership. Only then issue **one** new DEV call:

```bash
python -m experiments.skill_crystallization_k3b_dev \
  --mode gemma \
  --first evidence/l431-gemma-20261108/first-report.json \
  --prior evidence/l431-gemma-20261108/revision-continuation.json \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model YOUR_VERIFIED_SERVED_MODEL_ID \
  --out /tmp/l431-k3b-real-gemma.json
```

Use the exact endpoint for the verified owned process; do not assume a server is already running or terminate unrelated processes.

To run without a model, use `--mode fixture --proposal-file PATH`. Report fixture successes as **fixture-only**, not `SKILL_REVISED` by Gemma. Example fixture response:

```json
{"status":"ABSTAIN","reason":"Insufficient grounded evidence for a bounded new skill","skill":null}
```

## Protocol and evaluation

1. Read and validate the old skill only against its original training experience IDs.
2. Preserve existing `shift_observations` from #790. If the last two genuinely observed attempts are failures, **do not append new simulated post-suspension trials**. Otherwise continue with revision seed 20261111, checking fresh applicable cues.
3. Only after two consecutive observed failures, mark the old mock skill `SUSPENDED` and set the fixed-L0 rollback **marker**. Before suspension, rollback must be `null` and no Gemma request may occur.
4. Send the fixed observed training + failure traces and current constraints to Gemma. Never send the hidden world motion generator, CHEAP rule, future effects, validation or holdout results.
5. Classify `SKILL`, explicit `ABSTAIN`, explicit `UNSATISFIABLE_WITHIN_BUDGET`, rejected Validator, or HTTP/protocol failure separately. Always preserve response records on HTTP/protocol failures.
6. Independently validate any SKILL against source IDs and 1–4 bounded actions. Only validated candidates proceed to **reserved reevaluation seed 20261112**, not previously used in a model prompt.
7. On the independent synthetic shift holdout, compare fixed L0 / existing CHEAP / new candidate with common trial effects. Record success, selection, simulated Action count, no-match, invalid-cue selection and Python nanosecond overhead. The latency values are host interpreter measurements; Action counts are **not measured bodily energy**.
8. Do not use validation/holdout outcomes to repair the same proposal; each new model attempt would require an explicitly recorded new experimental stage and disjoint holdout.

## Acceptance interpretation

- `PROPOSAL_VALIDATED` means only that the structured candidate/abstention passed bounded checks.
- `EXPLICIT_ABSTENTION_ACCEPTED` is a valid decision, **not Skill repair or proof of impossibility**.
- `NEW_SKILL_MOCK_EVALUATED` means the candidate passed the Validator and the independent mock holdout was run; report its actual outcomes, including failures.
- `SKILL_REVISED` and `RECRYSTALLIZATION_VALIDATED` are **not claimed** unless a new real Gemma response produces a valid independently tested Skill.
- No changes to main, S49, Minecraft, actual WorldBody, Memory/Habit owners or autonomous L0 installer. DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
