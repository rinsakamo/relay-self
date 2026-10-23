# W4 SelfWorld local-model matched A/B (DEV/OFFLINE)

## Predeclared question

Does inclusion of already prepared SelfWorld observation/review context
change decisions, uncertainty, BOUNDED→THINK escalation, token use and latency
under the **same preexisting RelayEngine and same local llama.cpp adapter**?

- Arm A: `without_selfworld`: request's `context=()`.
- Arm B: `with_selfworld`: exact source-bound context.

Only context differs; request ID, wording, choices, model, decoding settings,
and other request fields are identical. Fixed counterbalanced order AB/BA
alternates across pairs. Warmups are logged, not included in summaries.
Measure two epochs and BOUNDED+optional THINK, plus separate OPEN; OPEN output
is hashed, **not scored** for safety/correctness.

### DEV rubric fixed before execution

- Original saved W4 run `1e86a714f3ea3374` (empty observed entity selection):
  prior/following `DEFER_RECHECK`; this does NOT imply physical absence.
- Synthetic MATCH (observed same label): prior/following `INSPECT_SOURCE`.
- Synthetic MISMATCH: prior `INSPECT_SOURCE`, following `DEFER_RECHECK`.
- Synthetic UNKNOWN (later target unobserved): same prior, following DEFER.
- Synthetic empty/empty: both `DEFER_RECHECK`.

These are *explicit source epistemic rubrics*, not World safety ground truth,
real improved performance, a learned physical law or a scientific result.
Synthetic fixture generation reuses `tests/` W3 builders with temporary
files. Do not silently use synthetic content as actual Minecraft evidence.

Observations include choice/status, per-pair order, model calls, THINK
escalations, completion/prompt token counts if returned, wall time,
unresolved and transport/protocol errors. Missing usage is null, not zero.
The record preserves hashes of request bodies and OPEN responses, rather
than logging free-text model expression. Every call (including warmups and
errors) is durably appended and fsynced into a new external
`<output>.journal.jsonl` witness; an interrupted run leaves incomplete
journal evidence, not a fake success report. The final report is exclusive-new
and contains that journal SHA256. Both output and journal are preflighted
before any model calls. The source archive is never written.

## LocalCodex execution after exact-HEAD local focused tests

The experiment does NOT launch llama.cpp or Minecraft. Use an existing
inference service explicitly preconfigured for the same model on 127.0.0.1.
Record separately the actual loaded model filename/digest, quantization,
runtime build, GPU, ctx, concurrency, temperature and run order.
This harness does not independently attest the model alias.

```bash
export PYTHONPATH=src:tests:.
export PYTHONDONTWRITEBYTECODE=1

python3.12 -m experiments.self_world_model_ab \
  --source real \
  --evidence-root /home/rinsa/work/w4-observation-dev-20261023/evidence/w4-observe-1e86a714f3ea3374 \
  --repo-root /ABSOLUTE/CLEAN/CHECKOUT \
  --expected-head EXACT_40_HEX_DEV_HEAD \
  --endpoint http://127.0.0.1:1234/v1/chat/completions \
  --model ACTUALLY_LOADED_MODEL_ALIAS \
  --output /ABSOLUTE/EXTERNAL/NEW-EVIDENCE/w4-real-model-ab.json \
  --repeats 4 --warmup-pairs 1 --confirm LOCAL_MODEL_DEV_ONLY
```

Run a separate synthetic arm with `--source synthetic` and no
`--evidence-root`, writing a distinct new output file. The local
executable requires Python 3.12, clean exact repository HEAD, explicit
confirmation, exact IPv4 loopback `/v1/chat/completions` endpoint and
exclusive-new output. No new Java/Node/Minecraft/physical Action/OUTCOME/
S10/Memory updates, CI, FULL or grants. Commit `[skip ci]` only.

### Interpretation and next gate

Pairwise comparisons are **descriptive**, including unresolved decisions,
missing token data and provider failures. No p-hacking, dropped cases,
automatic retries or cherry-picked successes. Candidate code and synthetic
tests need Python3.12 local execution plus SelfWorld/W4/S18/protected-v2
regression, Ruff/contracts and Node22 before adoption. Real archive hashes
and the historical 770-index must remain unchanged; W4 producer-local
provenance is not external independent custody.

No claim of real-model performance or science is possible until the actual
local runs complete. Even then this is DEV_ONLY, not SCIENCE, because the
sample and protocol are exploratory.

`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN / NO_NEW_WORLD_RUN`

### 2026-10-24 protocol audit

The CLI records each actual-model request hash separately for BOUNDED, THINK
and OPEN at the existing provider seam, including a durable start event before
transport and an end event on errors/interruption. Initial UNRESOLVED and THINK
results remain distinct. Failed THINK retains both attempted provider calls;
unknown token usage remains null. The unchanged RelayEngine owns escalation.
Pairwise B−A differences retain worsening and missing measurements. CLI transport
ignores proxy environment settings and refuses redirects beyond loopback.

The earlier request digest using `HASH_MODEL_PLACEHOLDER` is retained only for
fake-provider unit tests; actual CLI measurements use the fixed loaded alias.
Model artifact identity must still be independently pinned before measurement.
