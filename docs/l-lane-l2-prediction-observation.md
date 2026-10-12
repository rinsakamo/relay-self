# L Lane L2 — Prediction, independent observation and bounded reuse

Authority: #426 (L owner); former #421 A / #431 B / #432 C are frozen
research inputs; scientific #544 remains **G3 NO-GO**.
Base: L1 #594 exact HEAD `40db58d548ea31c4a70acabcc71b0954c7b6ce42`;
S3 #598, S5 #601, R4 #602, V1 #595 are **independent unmerged**
owners. This implementation does not alter their branches or write Minecraft
Action evidence. L2 extends only L1 in one Draft. L3 Habit and L4 adaptive
allocation are not in scope.

## Intended primitive (and strongest cheap null)

The existing `relay_self.prediction.predict_transition` already computes a
deterministic transition from `PredictionState` + `TransitionRule` (PRD S8).
No independent World Model is justified. L2 `ActionForecast` explicitly
requires the rule and original state to condition on `action_ref`; it
recomputes `predict_transition` to reject a modified output. The
`cheap_rule_comparator` calls this same existing mechanism with identical
information. **Equal by construction** is a null result, not model advantage.

For candidate actions, keep forecasts *prospectively* as distinct existing
`Memory` records marked `observed_world_fact=false` and
`executed_alternative=false`. They can be for alternatives that were never
issued. A hypothesized `WAIT` next state is NOT a factual World result when
`MOVE_BACKWARD` was actually executed. Nonmatching forecast/evidence yields
`counterfactual_not_observed`, never a fabricated negative/positive outcome.

Only when S independently qualifies its **original** physical Action/OUTCOME,
retains its L1 `QualifiedEpisode`, and projects independently sourced
`StateVariable` values should L call
`compare_forecast(forecast, admitted_observation, admitted_source_sha256=...)`.
L must *not* extrapolate observed variables from its own forecast or from
a narrative/LLM-generated explanation.

- Both S-owned forecast-source and outcome-source SHA256 must be admitted,
  with exact session, action kind AND cue tags, earlier forecast source
  sequence, and a bounded source-sequence lag (default 64; not proof of
  stable World state). The same Action in a changed cue context is UNKNOWN,
  never a scored hit/miss.
- OUTCOME/observed_execution is **physical Action result only**. It is
  still not goal success or feedback authority. A known adapter rejection,
  UNKNOWN, missing observation key, stale/future revision, unverified digest,
  incomplete PRD prediction, or unexecuted alternative is **not scored**.
- Compare only explicitly assigned PRD variable keys; do not infer
  unprojected goal variables. Mismatch yields a `SURPRISE` review hint,
  not an automatic parameter update or changed Action.
- Retaining a comparison requires original forecast Memory **and** existing
  source-qualified L1 observed Memory, plus immutable Memory owner. The
  review Memory records links, admitted digest, compared/mismatched keys and
  explicit no-learning/no-goal flags. It cannot call S10, S11 or L0.
- Historical surprise lookup returns only bounded Memory IDs for L2
  reconsideration, never an Action candidate/grant. The original L1 tag
  retrieval remains usable independently.

**Trust boundary:** `AdmittedObservation` is an S-owner-supplied projection
object; L2 does not prove that its variables came from actual native frames.
Its digest is a source identity reference, not a signature or independent
authentication. S must validate original native before/after frames and
provenance, project the observed variables, and supply the admitted digest
set; R #602 explicitly prevents treating derived S3 JSONL/Memory as original
raw evidence. The real S4 one-shot saw 181 outer frames, 0 Action, and 0
observational Memory. Its empty state is **not** an L2 measured match/surprise.
Frozen #583 World used `doMobSpawning=false`; S5 #601 diagnosed this
opportunity mismatch. L does not stage or change World conditions.

## Test coverage and result ceilings

Offline typed synthetic controls include:
1. forecast retained in original Memory, cheap equality, explicit observed
   comparison and exact save/reload;
2. independent mismatch/surprise with review only, no LearningFeedback;
3. never-executed alternative has no outcome;
4. wrong session, source revision, UNKNOWN, missing observed keys/digests;
5. forged PRD forecast, invalid cue, altered/absent original Memory,
   duplicate retention, untrusted comparison and foreign projection;
6. strict typed variable equality, no undocumented false success.

No actual LLM prediction, signed World-goal result, counterfactual
intervention/paired reset, retained S10 preference update or S11 Habit
acquisition. #544 science NO-GO remains. The maximum engineering result is
`L2_OFFLINE_PREDICTION_OBSERVATION_SEPARATION_ONLY`.

## Shared RSEE operator offline-only runbook

From a clean independent L2 worktree on the WSL2 host:

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
test -x "$BASE/venv/bin/python" || exit 1
"$BASE/venv/bin/python" -m pytest -q \
  tests/test_forecast_bridge.py tests/test_experience_bridge.py \
  tests/test_prediction_qualification.py
"$BASE/venv/bin/python" -m pytest -q
"$BASE/venv/bin/ruff" check src tests experiments adapters observability
"$BASE/venv/bin/python" tools/check_repository.py
```

No new venv/node_modules, pip/npm installs, GGUF copy, Java, Mineflayer,
Minecraft, llama-server, GPU, LLM POST or physical Action. GitHub Actions
runs on an ephemeral runner (not the actual user's shared RSEE); report
actual host validation as NOT_RUN if no WSL2 execution receipt exists.

## S/V handoff

S may later pass an admitted S16 episode **and independently projected**
after-World keys to compare one prospective PRD action forecast; S continues
to own every Action/OUTCOME and source receipt. V evaluates prediction
calibration and usefulness against the **same-evidence cheap PRD baseline**,
where actual predicted vs observed World keys exist. Neither a count of
hypotheses nor retrospective matching on toy fixtures is learning/science GO.
