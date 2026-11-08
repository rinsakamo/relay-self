# RelaySelf K3-D — guarded semantic Skill revision by real L2 (DEV)

**Status:** DEV implementation and isolated fixture verification. New real Gemma call **NOT_RUN** in the chat environment. No real Minecraft, S49, C1/Memory/Habit admission or self-installation.

- Parent: Draft PR #792 (HEAD `39ed05e49e433e554ab6ec2c10c3f261968024c2`)
- Parent experiments: #790 first real Gemma Skill; #791 first real Gemma constraint-aware correction (formally valid but execution-equivalent); #792 explicit ESCALATE and new-Intent mock handoff.
- Research owner: #431. Physics owner: #537.

## Question

Can Gemma, using previously **observed** shift failures and old structured Skill, propose a **behavior-changing guard or in-budget control** (or explicitly ABSTAIN) rather than renaming the unchanged policy? Does a narrower applicability guard improve failure selectivity without silently granting more Actions?

The #791 real revision's explanation incorrectly asserted the old Skill was single-action; both structured Skills allowed up to four MOVE_AWAY Actions and had exactly the same executable guard, target and failure policy. This is an explanation inconsistency, not knowledge of the hidden World physics.

## Implementation

`experiments/skill_crystallization_k3d_dev.py` reuses the already-established K3-B `prepare_revision`, JSON Schema and independent Skill Validator, and K3-C `semantic_delta` / `evaluate_comparison` (no second Action issuer).

1. Validate original Skill from #790's 16 training experiences. Verify K3-B's 12 shifted experiences against deterministic fixture traces. Require two terminal consecutive failed attempts and a K3-B proposal whose executable policy is unchanged.
2. Supply Gemma only the observed training+shift experiences and typed current/previous Skill, including the verified statement that the original Skill **already allowed four moves**. Previous holdout outcomes and hidden synthetic effects must never be included.
3. Make **at most one** actual local llama.cpp HTTP request (Strict JSON Schema, Reasoning OFF, temperature 0), accepting `SKILL`, `ABSTAIN`, `UNSATISFIABLE_WITHIN_BUDGET`. Preserve request and raw response; no retries.
4. Apply independent JSON Schema validation and existing Skill Validator, including max_actions 1..4, cited IDs, bounded guard and legal failure action.
5. ABSTAIN/uncertain UNSAT: retain previous Skill in suspended state, do not evaluate or install a replacement.
6. SKILL with execution fields equal to the old Skill: `NO_BEHAVIORAL_CHANGE`, **do not open the reserved holdout**. Updated provenance and explanation may still be saved as a candidate, not as new execution ability.
7. SKILL with changed execution fields: count how many **already observed** successful and failed traces its guard would select or exclude. Then perform a fresh paired synthetic comparison using K3-C, preserving its postfailure `ESCALATE` with zero automatic fallback Actions. A structural change is NOT proof of improvement.
8. Explicitly report paired changes to guard selection and Action traces; a change not exercised by the holdout is `behavioral_difference_observed=false`. Report goal success and mock actions independently.

## Sealed seed discipline

- Previously inspected/exposed seeds include 20261108–20261112 and 20261120. Do not reuse them as new holdout.
- **Fixture-only tests use seed 20261122**, now exposed. This seed is never an independent real-L2 holdout.
- **One real Gemma call reserves seed 20261126**. Fixture mode explicitly refuses to open it. The real mode opens it only after receiving a valid **execution-different** model proposal. Never include it, hidden physics, or evaluation results in the Gemma prompt. After a real run it becomes exposed and cannot be reused for another new proposal.

## Commands

From an isolated child worktree at the verified HEAD, Python 3.12+:

```bash
python -m pytest -q tests/test_skill_crystallization_dev.py \
  tests/test_skill_crystallization_k3b_dev.py \
  tests/test_skill_crystallization_k3c_dev.py \
  tests/test_skill_crystallization_k3d_dev.py
python -m ruff check experiments/skill_crystallization_k3d_dev.py tests/test_skill_crystallization_k3d_dev.py
```

To execute exactly one **new** Gemma call on the owner's local GPU host, first verify the GGUF SHA256, model API ID, llama.cpp build10874, process maps/argv, context8192, slot1, strict Schema support, Reasoning OFF and owned GPU process. Then:

```bash
python -m experiments.skill_crystallization_k3d_dev \
  --first evidence/l431-gemma-20261108/first-report.json \
  --k3b-report evidence/l431-k3b-gemma-20261108/report.json \
  --mode gemma \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model YOUR_VERIFIED_SERVED_MODEL_ID \
  --out /tmp/l431-k3d-one-real-gemma.json
```

The endpoint is only an example: use the actual verified owned local server. Do not start/stop or disrupt other processes. Save **exact request/response bytes, usage, latency, process identity and SHA manifest** in a new K3-D evidence directory. Inspect and verify #790/#791 immutable SHA256 manifests before and after. Fail closed if any input source is invalid.

Fixture mode uses `--mode fixture --proposal-file PATH`; this is not real Gemma learning. Recommended fixture: a Skill identical to the old one except `min_distance: 2.39`, `skill_id` and evidence IDs that refer only to prior observed shift experiences. Do NOT use that constructed example as an alleged Gemma output, and do NOT show it as a target answer to Gemma.

## Explicit non-claims and next gate

- The current one-dimensional motion simulator and independent tests are only software feasibility. Physical safety and energy usage are unknown.
- Seed 20261122 fixture behavior cannot demonstrate learned generalization. Even a changed Scope with fewer failures can lose total Goal success; measure both, and retain a cheap fixed comparator.
- The K3-C new-Intent recovery is a mock admission, **not native S49 authority**. Do not unconditionally issue fallback Actions after a selected Skill consumes its budget.
- An admissible, different Skill is a candidate; only separate independent holdout outcomes can support limited learned applicability. Formal Habit/Memory admission and autonomous L0 installation remain later gates.
- **No new real Gemma response is claimed** until a LocalCodex run actually performs the one-shot POST and preserves evidence.

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
