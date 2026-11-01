# M cognitive lifecycle — read-only cost and coverage (2026-11-01)

Owner: [M #616](https://github.com/rinsakamo/relay-self/issues/616). Aligns with [#537 developmental learning](https://github.com/rinsakamo/relay-self/issues/537) and [#431 L retention](https://github.com/rinsakamo/relay-self/issues/431).

## Scope

Existing original S49/S/L8/M taps already produce an optional **completed-epoch**, bounded, allowlisted `SLM_PASSIVE_DEV_AUDIT_V1` diagnostic. They do NOT count real L2/model calls. This addition reads the row **after the original S owner returned** and, when provided, an independently supplied cognitive-use receipt. It never calls S/LLM, reissues Action, updates Energy or changes Memory/Habits.

- `experiments/metabolism_cognitive_lifecycle.py`: `CognitionCostSample`, `CognitiveWorkReceipt`, `summarize_cognitive_lifecycle`.
- M accepts **RECORDED** rows from `bounded_s_l_m_audit_row(observe_optional_s_l_m_dev(...))`, verifying the existing audit allowlist, original session/request/probe, strictly increasing seq and bounded ≤64 epochs. It rejects unauthorized grants, foreign World/task/session, duplicated meter/epoch/source, unsafe extra keys, stale, zero-metric and contradictory readings.
- Four *externally supplied* stages: `EXPLORE`, `FAMILIAR`, `SHIFT`, `RECOVER`. No automatic attribution of learning, habituation, model improvement or success. Task, condition and outcome annotations remain unqualified.
- Provider calls, input/output tokens, wall-time ns, CPU-time ns and GPU-time ns are **separate units**. No conversion to Minecraft food/health, true B0/M0.1 energy, P1 fatigue or M0.2 exhaustion; no intrinsic reward/complexity bonus.
- An absent meter or absent per-metric measurement remains **unknown**. `observed_sum` is the sum of just the measurements supplied; `complete_total` is populated only when every epoch in that stage has that metric. Explicit `provider_calls=0` requires an external meter; a missing meter never becomes zero.
- `measurement_scope=DECLARED_DEV_NOT_SOURCE_ATTESTED`, `source_attested=False`, and `interpretation=DESCRIPTIVE_DEV_ONLY_NOT_LEARNING_OR_CAUSAL_PROOF` are invariant. Structural source matches and externally claimed measurements are **not physical attestations**. Counts do not prove cost savings without condition/task/outcome matching and independent qualification.

## Example DEV flow

1. Original S owner completes one DecisionEpoch and passive S/L8/M tap. Obtain allowlisted row using existing `bounded_s_l_m_audit_row(tap_result)`.
2. From an **independent owner meter**, optionally associate a `CognitiveWorkReceipt` with exactly the same `session_id`, `probe_seq`, `request_id`. Without it, leave `usage=None`.
3. Assemble bounded epoch samples with explicit task/condition/phase and `UNKNOWN` outcome when there is no qualified Goal.
4. Summarize across consecutive probes **within one session**. Unknown, missing receipts and differing conditions stay visible; do not infer L2 costs from L8 candidate presence.
5. Future matched DEV longitudinal trials may observe exploration cost versus familiar cheap execution and re-escalation after shift, but only source-qualified S/model receipts and independent V designs can support behavioral learning or causal efficiency claims.

## Engineering checks and remaining work

`PYTHONPATH=. python -m pytest -q tests/test_metabolism_cognitive_lifecycle.py`

Local module prototype on Python 3.13: **29 PASS**. GitHub Actions on exact pushed branch must separately establish Python 3.12, Ruff, and owner contract compatibility. **No real World, GPU or LLM invocation in this increment; no main merge.**

Next dependency: S/model owner must expose a bounded source-linked cognitive usage receipt and a separately authorized real-world integration hook. M cannot self-issue or manufacture provider/model call receipts. User's standing M-lane DEV World grant is not a substitute for an executable host/World in this environment.
