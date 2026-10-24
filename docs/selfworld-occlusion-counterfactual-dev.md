# SelfWorld beyond observation: occlusion and counterfactual transfer (DEV)

**Status: SOURCE-STAGED / OPERATOR PYTHON3.12 NOT RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Authority: SelfWorld #633, S #537, Adaptive Cognition #426, S18 #354. Candidate extends the existing unadopted regularity-transfer branch. Draft PR #634, #545 and main remain untouched.

## Question

User-confirmed conceptual target: SelfWorld is a compressed, Self-local model of **"what this World is like"**, learned from experience. Its useful predictions should extend beyond immediate observations, particularly (1) when new observations are unavailable, and (2) when considering actions that are not actually executed.

This is **not** a claim that a saved observation or adding source JSON to a local LLM constitutes an acquired World model. Prior direct-context A/B on saved W4 hurt the rubric; the earlier label-persistence prototype merely tied cheap repeat prediction. We require separate counterfactual and observation-gap controls.

## Minimal isolated implementation

Files: experiments/self_world_occlusion_counterfactual.py and tests/test_self_world_occlusion_counterfactual.py. The experiment is **pure offline synthetic Python**. It does not launch Minecraft/llama.cpp, import Native World records, mutate SelfWorld/PRD/BLF/LRN/Memory, issue authorized Actions, create another semantic owner or alter production runtime.

- A PositivePosition is a positive, typed synthetic observation with Self, session, region, target, step, source reference and x coordinate. Its scope is literally SYNTHETIC_DEV. An absent reading is **not** a position x=0, known absence or physical safety.
- Two disjoint positive stationary-action transitions at different locations/targets can yield one immutable candidate for **relative per-experiment-step displacement** (delta_x). A conflicting transition, source replay or mixed Self/session fails induction or is rejected.
- A previously unseen region supplies a bounded pre-gap OccludedTask with **one or two** positively observed positions. After the pre-gap history, the next observation is deliberately withheld. The gap is explicitly OCCLUDED or UNOBSERVED, never "nothing exists".
- Three **independent** methods consume the **same task fingerprint**:
  - persist: predict the most recent observed x; never gated by learned-rule admission;
  - local: extrapolate the last two consecutive positive positions, or return UNAVAILABLE/None if insufficient history;
  - transfer: apply drift hypothesis from two different regions, or fail closed on foreign/reused evidence.
- Both counterfactual branches use the same explicitly *predeclared synthetic intervention assumption*: HOLD adds 0, NUDGE adds +2 relative to the unacted drift; NUDGE has artificial loss cost 1. **The action effect is not learned from data, and neither action is a Minecraft action.** Choice minimizes squared distance to a declared goal plus synthetic action cost, breaking ties toward HOLD.
- issue_forecast sees only the source-bound **pre-gap** task and optional allowed hypothesis, never hidden_drift or later outcomes. The returned SealedForecast includes predictions for BOTH interventions, selected branch, task fingerprint, rule pointer and SHA256 digest.
- A *separate* simulate_twin(task, hidden_drift, ...) builds paired hypothetical outcomes for HOLD and NUDGE. score_sealed matches task identity, synthetic scope, branch relationship and the previously computed forecast digest, reports absolute hidden-position error, two-branch prediction error, selected synthetic loss and regret against both synthetic clones. Unable/UNKNOWN predictions remain None and not zero-loss successes.

**Important time/provenance limitation:** This code separates issuance from evaluation and has no API for accessing future observations at issuance. A digest is not an externally timestamped, immutable third-party commitment or source attestation; an operator must save issuance and results in append-only external evidence before claiming genuinely prospective order. source_ref labels are synthetic assertions, not raw native Minecraft proof. The experimental step is not the native seq, server tick or elapsed seconds.

## Positive / negative synthetic cases

| Fixture | What can be learned |
|---|---|
| Training drift +1, new region 1 positive observation, next hidden drift +1 | transfer predicts hidden x; persist x is one step behind, local with one reading is UNAVAILABLE |
| Same task, two pre-gap observations | cheap local extrapolation ties learned transfer: no unique predictive value |
| Choice goal x=2 with starting x=0, hidden drift +1, NUDGE +2, synthetic NUDGE cost1 | transfer chooses HOLD; persist chooses NUDGE; synthetic cloned outcomes can compare regret |
| Hidden drift 0 (static) | cheap persist beats wrong +1 transfer |
| Hidden drift -1 (rule reversal) | transfer error is worse than cheap persist, so uncertainty/reversal matters |
| Missing reading, forged scope, cross-Self/session, old region/target, reused source, tampered forecast | missing -> UNAVAILABLE; invalid authority/evidence -> reject, not physical truth |

This example does not show the Counterfactual Action chosen in the real World. It also does not prove improvement over local extrapolation when two positives are available or over an amortized inexpensive rule with identical abstraction. Computational latency/tokens/Body energy and any causal product benefit are **NOT MEASURED**.

## Next operator verification and boundaries

1. Fetch isolated branch self/selfworld-occlusion-counterfactual-dev-20261024 into an independent clean WSL2 worktree; pin exact HEAD and check PR #634 remains Draft/unmerged.
2. Use **Python3.12 only** for the candidate's tests and relevant SelfWorld/PRD/Persistent Cognition/W4/S18 focused tests; Ruff + repository contracts. Fix any isolated DEV errors and rerun at the final exact HEAD. Node22 only if adapter dependencies actually changed (not expected).
3. Compare PR #634 HEAD to the branch, confirm six additive paths (the previous regularity three plus new three), and verify protected82/historical770 before/after, old evidence immutable. Report exact SHA and negative cases.
4. Do not use this synthetic experiment for QUALIFICATION, V SCIENCE, native World proof or actual physical Action/OUTCOME/S10. No CI/FULL/new Minecraft sessions, provider calls, new memory store, PR #545 or main updates.
5. Do not enable the learned rule in runtime. Future DEV should combine the two tested properties: **unvisited place transfer + positive predictive contribution under occlusion**; then independently compare prospective task outcomes under trusted source and cost gates.

**Acceptance language:** OFFLINE_SYNTHETIC_PREDICTION_PROBE once tests actually pass, NOT World adaptive-cognition qualified. A synthetic benefit relative to persistence is not proof of net value against the cheapest informative baseline. REGULARITY_VALUE_NOT_DEMONSTRATED for real World/runtime remains.
