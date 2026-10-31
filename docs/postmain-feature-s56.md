# S56: Genuine local L2 HTTP inference concurrent with actual Minecraft L0

## Authorities / freeze

Stacked on S55 [Draft PR #407](https://github.com/rinsakamo/relay-self/pull/407), exact HEAD `184e4ec6d452f1a39172e2e572d0dfa2a77130d3`. S54 [Draft PR #404](https://github.com/rinsakamo/relay-self/pull/404) proved genuine native World L0 Action vs a **FAKE** blocked localhost HTTP response. S56 is **different**: no fake server is supplied; local operator must independently start an **actual** llama.cpp / LM Studio model and permit the test. The physical success is NOT established by passing GitHub Actions.

## Run locally on the same WSL2 Linux network namespace as the model server

Prerequisites: Java 21, Node.js 22, Python 3.12 with pytest, Mineflayer dependencies installed with `npm ci --omit=dev --prefix adapters/mineflayer`, genuine Minecraft server download access and explicitly loaded local GGUF model in `llama-server` / LM Studio on **127.0.0.1:1234**.

First record the **actually loaded** model ID and server PID / build / exact GGUF path using independent local backend evidence. Compute the full SHA256 yourself and ensure `--model` equals the server's actual model alias. The on-disk model hash does **not**, on its own, attest the model loaded by HTTP server.

```bash
export S56_LOCAL_REAL_MODEL=1
export PYTHONPATH=src:tests
python -B -m adapters.mineflayer.s56_real_model_world_ci \
  --model "your-actual-server-model-alias" \
  --gguf "/path/to/your/actually-loaded-model.gguf" \
  --expected-sha256 "<full-64-hex-GGUF-digest>" \
  --endpoint "http://127.0.0.1:1234/v1/chat/completions" \
  --timeout-s 100 --max-tokens 768 \
  --report s56-artifacts/local-world-model.json \
  --server-log s56-artifacts/minecraft.log
```

This test will NOT run if `S56_LOCAL_REAL_MODEL=1` is missing, if GitHub Actions is the host, if the provided GGUF is unreadable or has a wrong SHA256, or if no localhost service is reachable. It does NOT upload model weights or print generated text, local file paths or a raw prompt in the JSON receipt. Public reporting of raw backend logs must be reviewed for secrets and model paths first.

## What successful execution establishes

- One official Minecraft Java 1.21.8 instance, unmodified Mineflayer 4.39.0, one live native session and single foreground native IO reader
- Experimenter-staged zombie far 10m -> L0 WAIT, then two distinct near 2m -> two distinct independently authorized MOVE_BACKWARD actions, measured native physical movement, terminal OUTCOME
- On first near World event only, one explicit, bounded, actual localhost `RelayEngine.open` call begins in the background. The L2 OPEN output is an **untrusted hypothesis**, never an Action permit. The configured local HTTP server must be still responding, not already finished, at the moment the first physical L0 Action closes
- `L0ModelOverlap` records monotonic model-entry, physical L0-entry and physical Action-closure time. Missing/model-early / no real movement -> FAIL, no optimistic replay
- After the native event loop, the model response may complete; S48/S53 invalidates and discards the stale L2 result. The received output is not reissued as an Action, retained state or World evidence
- `model_call` contains sanitized `elapsed_ms`, `prompt_tokens`, `completion_tokens`, `finish_reason` **only if supplied by the real provider**. Missing token values -> no PASS

The most that this local script itself may classify is `NATIVE_WORLD_AND_LOCAL_MODEL_HTTP_OVERLAP_BACKEND_ID_UNVERIFIED`. Separately independently corroborate backend loaded-model identity, process/server logs and hardware placement before making a stronger *real model* claim. The script does **not** cancel the backend, test GPU preemption, prove VRAM release, spontaneously form a goal, perform learned L1, acquire food or navigate around obstacles.

## Negative controls / CI

`python -m pytest -q tests/test_feature_s56_overlap.py`

The offline tests force absence of opt-in, early provider completion, non-terminal movement, duplicated model calls and Action identity mismatch. These tests do not need a model server or Minecraft and must **never** count as physical qualification. The existing 4-job workflow tests the new instrument on the full S49–S56 branch. Independent real physical evidence is required outside GitHub CI. Keep PR Draft/unmerged and Issue #410 open until actual local data and independent backend attestation arrive.