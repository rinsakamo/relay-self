# S #537 S2-D — strict schema + exact llama-server process preflight (offline DEV)

**Parent:** [S2-C Draft #700](https://github.com/rinsakamo/relay-self/pull/700)
exact `6c10ff9c21ee0db67b08f817b7d0e5599b338de1`.
**No new real World or real Gemma is executed in this change.**

## Why S2-D is needed

The original S60-B1 accepts only a five-field chat request and free text
response. S2-C previously could not honestly claim any strict JSON Schema
or Reasoning OFF request configuration. This independent S2-D increment
adds **explicit opt-in** structured mode to the same S60-B1 transport.
Default S60 callers and historical results retain their exact five-field
contract.

Structured mode adds a **sixth** request field:

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "schema": {
        "type": "object",
        "properties": {
          "status": {"type": "string", "enum": ["ADVISORY", "DEFER"]},
          "observation": {"type": "string", "minLength": 1, "maxLength": 320},
          "uncertainty": {"type": "string", "minLength": 1, "maxLength": 320}
        },
        "required": ["status", "observation", "uncertainty"],
        "additionalProperties": false
      }
    }
  }
}
```

**Build10874 compatibility correction (S2-E, 2026-11-03):**
Preworld audit in [Issue #537](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6593612373)
found the prior flat `response_format.schema` ignored by the local
`tools/server/server-common.cpp` at `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`.
The build10874 parser selects `response_format.json_schema.schema`; a
missing wrapper yields the unrestricted empty object schema. The new nested
wrapper is fixed in the S60-B1 source and negative-tested before a POST is
ever allowed. This is a **static contract correction only**; no real
build10874 HTTP, backend grammar-enforcement or physical World is proven.
The preserved PR #704 BLOCKED_PREWORLD evidence is not reclassified.

The same S60-B1 response validator checks a **JSON object with exactly
these three keys**, bounded strings, permitted status, stop finish reason,
no non-empty `reasoning_content`, duplicate JSON key or `<think>`
content; malformed or truncated response is unconfirmed, never an Action.
No unseen model result is assumed valid merely because llama.cpp received
`response_format`. The json_schema request format is documented in
llama.cpp server README; compatibility with the *actual local build* must
be confirmed before physical DEV.

**Reasoning OFF is a separate server flag**: `--reasoning off`. In
particular `--reasoning-format none` changes how thought text is
represented, and by itself **does not** disable thinking. This branch
does not treat it as equivalent. Confirm `llama-server --help` for the
actual binary. Do not alter the existing S60-B1 request envelope with
unverified, model-specific reasoning options.

## Same-process preflight — before new World

The S2-C one-World CLI now requires:

- `--model-pid`: real **same-user** process in `/proc`;
- `--llama-server`, `--binary-sha256`: actual executable and its expected bytes;
- `--gguf`, `--gguf-sha256`: exact Gemma-4 Q4 GGUF and its expected bytes;
- `--model-alias`, `--model-port`: exact process arguments;
- `--gpu-layers`: actual exact `--n-gpu-layers` value, within the existing
  `OwnedBackendSpec` range (0–120); **`-ngl 999` is not accepted by this
  preflight** and must not be silently converted or reported as 99.
- exact `--ctx-size 8192`, `--parallel 1`, `--host 127.0.0.1`,
  `--model`, `--alias`, `--port` and **`--reasoning off`**
  in `/proc/PID/cmdline`, with a live `/proc/PID/exe` matching the binary
  path, same user UID, no duplicate flags.

The bytes are hashed using the original S57 spec; a changed PID/argv
or mismatched binary/GGUF file fails closed **before Minecraft begins**.
This checks actual process **startup identity**, not independent proof that
the model bytes are loaded on GPU, exact runtime inference mapping,
process longevity throughout the World, provider STOP ACK or GPU release.
Those remain external evidence requirements.

Example LocalCodex command, **only with separately verified applicable
World1/model1 DEV grants and already-owned matching llama-server**:

```bash
export PYTHONPATH=src:.:tests
export S49_REAL_SERVER_CI=1
export S49_COMPLETED_L0_DEV_ONLY=1
export S537_S2C_LIVE_L2_DEV_ONLY=1
python -m tools.s537_s2c_live_s60_shadow_dev \
  --m-owner-dir "$M_OWNER_DIR" \
  --wb-owner-dir "$WB_OWNER_DIR" \
  --report "$EVIDENCE_DIR/s49.json" \
  --server-log "$EVIDENCE_DIR/server.log" \
  --s2c-report "$EVIDENCE_DIR/s2c.json" \
  --model-alias "$MODEL_ALIAS" --model-port "$MODEL_PORT" \
  --model-pid "$MODEL_PID" --llama-server "$LLAMA_SERVER" \
  --binary-sha256 "$LLAMA_SHA256" \
  --gguf "$GGUF" --gguf-sha256 "$GGUF_SHA256" \
  --gpu-layers "$GPU_LAYERS" \
  --max-tokens 256 --timeout-s 45 --live-world-dev
```

After one original World only, use the independent S2-C auditor (which
permits **one** model attempt while preserving original S2-B zero-call
defaults):

```bash
python -m tools.s537_s2c_async_source_audit \
  --s49 "$EVIDENCE_DIR/s49.json" \
  --s2c "$EVIDENCE_DIR/s2c.json" \
  --output "$EVIDENCE_DIR/s2c-source-audit.json"
```

Original S49 may reach the next Action/S16 before the completion. That
leads to stale/displaced result, **not a false cognitive acceptance**.
Evidence still requires raw HTTP/mapping metadata, before/after process
ownership, one-shot no-retry, native S16 readback and full cleanup.
No Action/Learning/Energy owner changes.

## Boundaries

Offline positive tests are synthetic and use fake local HTTP. No
Gemma/World inference, independent Paper/W3 source attestation,
learned behavior, self-model correction or quality evidence is claimed.

`DEV_ONLY / S2D_STRICT_REQUEST_AND_PROCESS_PREFLIGHT_OFFLINE_ONLY /
REAL_WORLD_NOT_RUN / REAL_GEMMA_NOT_RUN / SOURCE_UNATTESTED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.


## S2-E local single-HTTP preworld check (separate from physical World)

The new tools.s537_s2e_real_schema_probe_dev is an independent DEV-only,
one-POST synthetic-observation diagnostic. It does NOT run Minecraft,
modify S49/S60 runtime authorities, or start/stop llama-server. It uses
the same strict schema and the original S60-B1 response validator,
and checks same-user PID, binary/GGUF SHA, alias, port, and reasoning-off
process arguments before any HTTP POST.

This consumes a SEPARATE model grant from any later optional S49 one-World
integration. Never count the probe and World inference as one model call.

Command (only with the independent local model DEV grant and clean HEAD):

```bash
export PYTHONPATH=src:.:tests
export S537_S2E_SCHEMA_PROBE_DEV_ONLY=1
python -m tools.s537_s2e_real_schema_probe_dev \
  --model-pid "$MODEL_PID" \
  --llama-server "$LLAMA_SERVER" --binary-sha256 "$LLAMA_SHA256" \
  --gguf "$GGUF" --gguf-sha256 "$GGUF_SHA256" \
  --model-alias "$MODEL_ALIAS" --model-port "$MODEL_PORT" \
  --gpu-layers "$GPU_LAYERS" \
  --max-tokens 128 --timeout-s 45 \
  --evidence-dir "$FRESH_EVIDENCE_DIR" --one-shot-dev
```

No auto-retry, proxy, fallback, World creation or extra Action. Preflight
failures stay BLOCKED_PREWORLD. A POST attempt writes request.json,
response.raw, result.json and SHA256SUMS even when the completion is
rejected. A transport exception is NOT proof of HTTP completion; an
invalid HTTP response is NOT a valid S60 structured advisory. Client
disconnect does NOT establish backend STOP ACK or GPU release.

Success proves a limited real-response compatibility result together
with static pinned source evidence, not universal grammar enforcement.
Only after a separate probe PASS and a fresh independently applicable
S49 World+model DEV grant can the single-World integration be attempted.
