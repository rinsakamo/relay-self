# RelaySelf L / Gemma-4 native strict JSON Schema + Thinking OFF (2026-11-02)

DEV-only successor of #681, #680, #679. The prior #679 real World FAIL, model finish_reason=length at 512 tokens (valid OPEN 0), and both mandatory original audit FAILs remain unchanged. This branch has NOT executed a real Gemma model or new Minecraft World.

## Why this is a hard pre-World gate

Prior successful Gemma-4 12B Q4_K_M + llama.cpp configuration in the RTX3060 WSL host required native JSON Schema structured output ON and reasoning OFF. The prior L JournaledLiveLlamaProvider only requested json_object, while the canonical OPEN renderer already requested reasoning_effort none. This branch adds an opt-in native json_schema request and explicit runtime inspection for a real reasoning channel.

The llama.cpp server documentation lists response_format json_schema, reasoning_effort none, and chat_template_kwargs enable_thinking false:
https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

A real upstream Gemma-4 issue reported that JSON-Schema grammar could still allow a thought-channel prefix, even with enable_thinking false:
https://github.com/ggml-org/llama.cpp/issues/30256

Our source-only tests cannot determine whether the user's exact current build is affected.

## Exact implemented Gemma OPEN contract

- Opt-in original L2 evidence-ID selection requests native JSON Schema with strict true, exactly 10 response keys, no additionalProperties, bounded enum model-family/reconsideration/experiment IDs, and source-derived evidence ID enum.
- Explicit reasoning_effort none AND chat_template_kwargs enable_thinking false, temperature 0, seed 1, stream false, cache_prompt false and max_tokens 512.
- The legacy numeric-copy L2 mode still uses json_object and cannot be retroactively qualified as strict Schema.
- The canonical model provider still rejects finish_reason length. All response bytes are journaled before inspection.
- A reported nonempty reasoning_content, nonzero reasoning_tokens, or embedded thought marker is rejected. Even a literal $thought placeholder is conservatively rejected until the actual build is diagnosed, rather than silently claimed Thinking OFF.
- Strict JSON syntax is not physical truth and evidence-ID validity does not prove semantically correct hypothesis revision.

## Required local preflight before any new Minecraft World

The actual Gemma GGUF is available on the user's Windows11/WSL2 host, not on GitHub-hosted CI. First independently read actual llama.cpp build/launch command, GGUF path and SHA256, process mapping, GPU, n_ctx and n_slots. Known historical good reference, not a claim about the current process: RTX3060, Gemma-4 12B IT Q4_K_M, CUDA llama.cpp, -ngl 999 -c 8192 -np 1 --no-context-shift. Do not restart a healthy server or fetch new weights. Use the server's actual alias.

In a clean L child worktree, set PYTHONPATH to src:tests:. and run precisely one synthetic-only HTTP capability preflight in a NEW evidence directory:

    export PYTHONPATH=src:tests:.
    export L_MP11_GEMMA_PREFLIGHT_DEV=1
    python -m tools.l_mp11_gemma_structured_preflight \
      --endpoint http://127.0.0.1:8080/v1/chat/completions \
      --model "$ACTUAL_SERVED_GEMMA_ALIAS" \
      --evidence-root "$NEW_EVIDENCE/gemma-strict-wire-probe"

The preflight performs exactly one real local HTTP call with explicitly SYNTHETIC evidence, and uses the same exact JSON Schema/payload flags as the L original owner. On success, it exclusively saves the report gemma-structured-preflight.json; it also saves exact original HTTP request and response raw JSON, per-call receipts and SHA. The report status indicates only transport capability; it does NOT attest GGUF weights or an actual physical Paper World.

If the schema is unsupported, output ends with length, Thinking leaks, content is not valid strict JSON, or the selected synthetic ID is wrong, FAIL and stop BEFORE World. Preserve bad originals, diagnose llama.cpp version, grammar and template without enabling reasoning or falling back to plain JSON.

## Original physical trial, only after local preflight

Continue the already authorized single-World, no-retry L DEV model/World envelope. Set:

    L_MP11_LIVE_PREFIX_DEV=1
    L_MP11_LIVE_L2_DEV=1
    L_MP11_EVIDENCE_IDS_DEV=1
    L_MP11_GEMMA_STRICT_SCHEMA_DEV=1
    L_MP11_PAPER_EOF_DEV=1

Original S49 runner requires --l-mp11-evidence-ids-dev and a --l-mp11-gemma-preflight-report path into the immutable successful probe directory in addition to its prior --l-mp11-live-prefix-dev, --l-mp11-paper-eof-dev, actual local endpoint/model alias, original Paper/plugin configuration, raw stdout root, server-log, and result report.

The original S49 entrypoint independently checks the preflight raw request SHA, full original response SHA, exact structured schema/Thinking-OFF flags, model alias and completion before any physical World startup. A successful preflight does not guarantee the full live Paper prompt will fit the context or finish within 512 tokens; that still fails closed with original HTTP retained.

Original planned bounds: 1 disposable Paper World, at most 3 original S49 Actions, at most 2 real in-World OPENs, zero retries, no Action permission for L2, no learning or L0 promotion. Do not vary physical surface/input under L2 yet. Independent full G3, L prefix and L2 original feedback replay must all succeed before calling the whole World PASS. Evaluate A, B1, B2 and C separately.

Current classification: OFFLINE_DEV_PREPARED / ACTUAL_NEW_GEMMA_CALLS_0 / ACTUAL_NEW_WORLDS_0 / REAL_PREFLIGHT_NOT_RUN / HISTORICAL_WORLD_FAIL_UNCHANGED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
