# S #537 S2-D — original S2-C model HTTP structured output / Reasoning OFF preflight

Parent: [Draft #700](https://github.com/rinsakamo/relay-self/pull/700),
offline exact HEAD `6c10ff9c21ee0db67b08f817b7d0e5599b338de1`.
S2-B real-World original owner source [Draft #696](https://github.com/rinsakamo/relay-self/pull/696)
exact HEAD `8949e64717b938418c9ecf624615fb87347810da`.

## Contract (only new opt-in S2-D requests)

- Original S60-B1 **five-field chat request is retained unchanged by default**.
  Only `structured_profile="S537_S2D_READ_ONLY_JSON_V1"` permits the three
  additional, exact request keys `response_format`, `chat_template_kwargs`,
  `reasoning_effort` at the original S60-B1 request validator.
- `response_format = {"type":"json_schema","schema":...}` with a **fixed**
  object requiring exactly three string fields, each bounded 1–240 characters:
  `assessment`, `uncertainty`, `next_observation`. No additional properties.
- `chat_template_kwargs = {"enable_thinking":false}` and
  `reasoning_effort = "none"`; the latter is documented by llama.cpp as a
  request setting that disables reasoning. These fields are not proof of a
  particular Gemma build's behavior; separately require the **owned server**
  to be launched with `--reasoning off`. Do **not** conflate
  `--reasoning-format none` (output parsing) with Reasoning OFF.
- Original S60-B1 requires a single HTTP completion, `finish_reason="stop"`,
  no `reasoning_content` key, exact JSON parsing with no duplicate keys,
  exact required fields, no truncation, no `<think>`, and canonical bounded
  JSON. Reject extra keys, fabricated content, invalid/long fields, non-JSON,
  `length` finish and all unknown-status transport. The result remains a
  **read-only advisory string** until S60-A validates the current lease.

The only new source/profile modules are:

- `adapters/mineflayer/s537_s2d_strict_json_contract.py`
- `tools/s537_s2d_backend_identity.py`

Source-bound S2-C runner is extended in the **S2-D child branch** to
require `--strict-json-reasoning-off`, `S537_S2D_STRICT_JSON_DEV_ONLY=1`,
and a verified local owner PID/binary/GGUF mapping before World startup.
This does not modify Action, Learning or Energy owners.

## LocalCodex DEV preflight, not a grant

Local process must be user-owned `llama-server` with exact `--model`
GGUF path, `--alias`, `--host 127.0.0.1`, `--port`,
`--ctx-size 8192`, `--parallel 1` and **`--reasoning off`**
(or locally supported equivalents). The preflight reads
`/proc/<pid>/status`, `/proc/<pid>/cmdline` and `/proc/<pid>/exe`,
hashes the executable and GGUF directly, and verifies PID/exe/argv again
after hashing; mismatches DEFER **before** launching any World. Actual
inference/GPU placement/loaded weights are not attested merely by this gate.

Use a fresh exact-head isolated S worktree and pinned M/WB originals.
Before running, verify the separate applicable real World/model DEV grant,
idle service ownership, model SHA/build10874, slot1/context8192,
backend runtime CLI `--reasoning off`, and that real Gemma-4-12B-it
Q4_K_M supports the S2-D request profile. No synthetic HTTP backend is
permitted in a physical test, and no preflight model call should consume the
single-call budget.

Suggested one-World, one-model **budget proposal**, not authorization:
original S49 Action <=2, 1 S60 request, max_tokens 256,
timeout <=45s, no automatic retry, L0 never awaits model response.
The original S16 after-probe will typically displace the in-flight
L2 result; this is expected **STALE**, not valid current reasoning.

```bash
export PYTHONPATH=src:.:tests
export S49_REAL_SERVER_CI=1
export S49_COMPLETED_L0_DEV_ONLY=1
export S537_S2C_LIVE_L2_DEV_ONLY=1
export S537_S2D_STRICT_JSON_DEV_ONLY=1

python -m tools.s537_s2c_live_s60_shadow_dev \
  --m-owner-dir "$M_OWNER_DIR" --wb-owner-dir "$WB_OWNER_DIR" \
  --report "$EVIDENCE_DIR/s49.json" \
  --server-log "$EVIDENCE_DIR/server.log" \
  --s2c-report "$EVIDENCE_DIR/s2c.json" \
  --model-alias "$MODEL_ALIAS" --model-port "$MODEL_PORT" \
  --backend-pid "$BACKEND_PID" \
  --binary-path "$LLAMA_SERVER_PATH" \
  --gguf-path "$GGUF_PATH" \
  --binary-sha256 "$LLAMA_SERVER_SHA256" \
  --gguf-sha256 "$GGUF_SHA256" \
  --max-tokens 256 --timeout-s 45 \
  --strict-json-reasoning-off --live-world-dev

python -m tools.s537_s2c_async_source_audit \
  --s49 "$EVIDENCE_DIR/s49.json" \
  --s2c "$EVIDENCE_DIR/s2c.json" \
  --output "$EVIDENCE_DIR/s2c-audit.json"
```

Do not execute the second command if S2-C did not create admitted evidence.
The S2-C auditor verifies row/POST/expiry consistency, but no physical
HTTP replay, no independent Paper/W3 source custody and no backend STOP.
Record model HTTP response metadata, raw payload and SHA where legally/
contractually permitted; never claim invalidated response as current.
Store original S49 native receipts and S2A/S2B source chronology,
PID/port cleanup, World deletion, and independent SHA manifest.

Classification until real LocalCodex experiment:
`DEV_ONLY / S2D_STRUCTURED_S60_OFFLINE_ONLY /
NEW_REAL_WORLD_NOT_RUN / REAL_GEMMA_NOT_RUN /
SOURCE_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
