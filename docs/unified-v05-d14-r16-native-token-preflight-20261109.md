# D14 R16 — native-token bounded L2 preflight (no inference)

Base R15b Draft PR #824, exact validated source commit
31adeb6b7ee37d11d3cab1cd6d8e2c33db07affe.
Stage: DEV_ONLY / PREMODEL_READ_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.

## Failure kept immutable

The original R15b local one-shot Gemma-4-12B-it Q4_K_M model POST failed
HTTP 400: prompt 8,615 tokens against llama.cpp build10874 context 8,192,
zero generated tokens and no Skill. The prior World was an independently
audited 243-tick early Self death (original S49 Actions and S16 both 0).
Do not rewrite those source or failed raw HTTP evidence files.

## Design

R16 keeps the full action_catalog(), owner signatures and R11 source
projection unchanged, but uses a compact **inference-only** Catalog:
action name/kind, owner, source path, guard, binding, parameters,
preconditions, observations/limits, original Catalog SHA and per-owner
contract SHA. It does not forge new Action permissions or arguments.

Native original R12 Experience event objects are not rephrased:
first/last event, all genuine original S49 LIFE_ACTION events, their IDs
and content must remain exact. Remove oldest intermediate non-Action
decisions only until the model-native prompt fits. Omitted source IDs
are hash-accounted; the model may cite only source IDs it really saw.

Use llama.cpp local non-inference /apply-template and /tokenize to
measure the *exact* R12 chat request messages. Strict JSON Schema,
Reasoning OFF, original GGUF and model alias must remain unchanged.

Context 8192 / output reserve 1024 / safety reserve 256 gives a measured
input budget of 6912. If native tokenization is unavailable, model count
untrusted, original owner catalog mismatched, or mandatory source events
do not fit: stop before /v1/chat/completions. No character/token
heuristic acceptance, no unbounded retry or fabricated source.

Retained success records token_preflight.json beside raw request/response
and shadow_candidate.json; replay recomputes exact selected context from
the original source, validates source/catalog and saved budget/response.

## Read-only LocalCodex preflight

Use current exact R16 HEAD, original verified World and a new separate
output path. Run local llama-server for its **non-generative** native
tokenization endpoints only, with the real Q4_K_M GGUF, correct SHA,
build10874, ctx8192 / slot1 / Reasoning OFF, and a pinned model alias.
Verify no generated tokens and no inference endpoint POST.

    export PYTHONPATH="src:tests:."
    python -B -m tools.bug0_d14_r12_l2_shadow \
      --phase preflight \
      --report "$PRIOR/report.json" \
      --server-log "$PRIOR/paper_original.log" \
      --event-journal "$PRIOR/d14_natural_events.jsonl" \
      --nonmotion-fence "$PRIOR/original_s49_nonmotion_fence.json" \
      --motion-fence "$PRIOR/original_s49_motion_fence.json" \
      --endpoint "http://127.0.0.1:1234/v1/chat/completions" \
      --model "$MODEL_ALIAS" \
      --out "$NEW_SEPARATE_DIR/r16-prompt-preflight.json"

Phase preflight neither requires the R12 L2 generation grant nor calls
Chat Completions. Protect the earlier failed raw POST directory.
Readout records selected exact source IDs, model prompt token count,
request/catalog hashes, budget and reserved generation tokens.

## Later separately authorized model attempt

A future --phase propose recomputes native token count immediately before
its single L2 model POST; if admission fails, no model generation.
Only if a NEW operator grant explicitly authorizes inference, set
R12_L2_POSTWORLD_DEV_ONLY=1, use fresh exclusive raw paths, and follow
the original R12/R13 strict JSON format. An L2 DEFER/OBSERVE is valid.
Real model output/Strict JSON enforcement and R15 World are NOT_RUN
in this R16 branch. No World Action, Memory/Habit write or L0 promotion.

## Verification

Run focused R16/R15/R14/R13/R12 tests, Ruff, repository contracts and
exact-HEAD CI. Mock tokenizer tests are offline and cannot prove that
native build10874 chat count matches actual completion admission.
Keep that uncertainty explicit in the real readout.

DEV_ONLY / NO_MODEL_INFERENCE / NO_NEW_WORLD /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
