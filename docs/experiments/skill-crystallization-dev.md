# RelaySelf Skill Crystallization — isolated DEV probe (2026-11-08)

**Scope:** L2-generated typed skill -> bounded L0-like rule interpreter -> independent synthetic outcome evaluation. Does **not** mutate `main`, WorldBody, S49, persistent Memory/Learning/Habit, or real Minecraft. This probe is not C1/C2/C3 runtime integration, autonomous L0 installation, R qualification, or V science.

This experiment is scoped by [Learning/Habit #431](https://github.com/rinsakamo/relay-self/issues/431), [development #426](https://github.com/rinsakamo/relay-self/issues/426), [S49 #537](https://github.com/rinsakamo/relay-self/issues/537), and Unified v0.5 C3/C4. Existing `src/relay_self/skill.py` only manages Skill execution lifecycle; it is not a generic Skill DSL runtime. No second physical Action issuer is introduced.

## Commands

From the repository root (Python 3.12+):

```bash
python -m pytest -q tests/test_skill_crystallization_dev.py
python -m experiments.skill_crystallization_dev \
  --mode proxy --seed 20261108 --out /tmp/skill-crystallization-proxy.json
```

`proxy` uses a deliberately transparent *non-LLM* rule synthesizer. It is only an interface/feasibility check. No model call is made.

To run **one** real Gemma call (only when a local llama.cpp chat completions service is already available, with Strict JSON Schema support and Reasoning OFF):

```bash
python -m experiments.skill_crystallization_dev \
  --mode gemma \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model YOUR_EXACT_SERVED_MODEL_ID \
  --seed 20261108 --out /tmp/skill-crystallization-gemma.json
```

Use the existing pinned Gemma-4-12B-it Q4_K_M, llama.cpp build identity and model hash validation from the L owner environment. The script requests `reasoning_effort=none` and rejects nonempty `reasoning_content`; verify server configuration separately. No automatic retries or World actions. Model protocol failure preserves HTTP/raw provider evidence when a response was returned. Connection failure is recorded as a failure, not a successful model call.

## Experiment design

- `train`: 16 simulated attempted Intent episodes (8 normal, 8 ice), each using a 2-move fixed baseline. L2 sees only observed before/after traces, cue, outcome and experience IDs—not the hidden physics generator, future steps or evaluation data.
- `validation`: 16 unseen scenarios. **Not** used to alter the frozen candidate.
- `holdout`: 32 unseen scenarios (16 normal, 16 ice), wider start-distance range. Baseline, candidate and predeclared cheap conditional comparator use paired synthetic physical effects.
- `shift`: 16 separately generated ice scenarios with changed motion outcomes; two consecutive failures suppress candidate use and mark L2 escalation. No actual second L2 call or new self-repaired skill is claimed.
- 9 guard/negative checks: a valid in-scope cue plus stale/unknown/wrong-session/incomplete-coverage, unbounded budget, invented action fallback, forged evidence and NaN guard.

All DSL candidates must be closed-schema JSON with `version`, `skill_id`, `surface`, `min_distance`, `max_distance`, `target_distance`, `max_actions`, `on_failure`, `evidence_ids`. `max_actions` is restricted to 1..4, `on_failure` to `ESCALATE`, the action to the existing synthetic `MOVE_AWAY` only. The runtime also rechecks move budget. `source_session`/sequence are fixture identity/freshness proxies, **not** native S49 receipts or a real authorization grant.

The fixed cheap comparator is an **a priori** human-specified rule: use up to 3 moves on ice, otherwise use the fixed 2-move L0. Matching the learned/proxy outcome is `CHEAP_EQUIVALENT`, not proof of useful learning or generalization.

## Observed first local offline run

- `pytest` focused: 13 PASS; no real model / World / Action / new owner writes.
- Seed 20261108, holdout: normal baseline/candidate 16/16; ice baseline 3/16, proxy candidate 16/16, cheap comparator 16/16.
- Across 20 fixture seeds: proxy candidate 16/16 ice in all 20; fixed baseline 0..5/16; cheap comparator 16/16 in all 20; in-scope negatives and shift suspension all passed.

These numbers reflect **one narrow synthetic physics generator with deliberately separable surfaces**. They show software feasibility and a Grand Null equality, not actual L2 synthesis, Minecraft generalization, real S49 integration, or scientific causal evidence.

## Next technical gate

1. Run with pinned real Gemma: exact model hash, one provider request, raw input/output and finish reason; classify malformed, rejected, no-match, cheap-equivalent separately.
2. Test Skill revision after a shift with a *new* L2 call, frozen separate evaluation seeds and no test-set leakage.
3. Review an integration adapter to existing L/Habit owner and S49 read-only shadow, then independently qualify physical Action admission. No new skill installer/physical issuer is implied by this experiment.
