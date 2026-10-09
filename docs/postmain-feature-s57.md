# S57: owned llama-server process + real Minecraft World/LLM overlap

Authority: S56 Draft PR #411 exact HEAD `1633849b0d926c10978dc42b12a02fd9c7c4fa29`. S57 is stacked Draft. S18–S56 and RelayTheory R6/Paper2 MAIN40 remain unchanged.

S56 already provides a real native Minecraft Java 1.21.8 + Mineflayer 4.39.0 physical L0 outcome vs an HTTP inference attempt on a local provider, but an arbitrary pre-existing localhost server cannot independently establish which GGUF is loaded. S57 narrows that gap by **launching one operator-selected and SHA256-pinned llama-server executable itself** against one SHA256-pinned GGUF file and one exact loopback port, retaining a controlled process PID and exit receipt.

## LocalCodex / WSL2 opt-in command

Install Java 21, Node.js 22, Python 3.12/pytest. Use the already-controlled WSL2 llama.cpp binary and model files; do not download or publish weights or secrets. Never run this from GitHub Actions, and never use a public or cloud API in its place. The controlled llama-server command uses official CLI options `--model`, `--alias`, `--host`, `--port`, `--ctx-size`, `--parallel`, `--n-gpu-layers`, and does not allow arbitrary environment `LLAMA_ARG_*` overrides.

Determine the binary and model full SHA256 separately:

```bash
sha256sum /path/to/llama-server
sha256sum /path/to/actual/GGUF-model.gguf
npm ci --omit=dev --no-audit --no-fund --prefix adapters/mineflayer
```

Then invoke on the same WSL2 host, with a free loopback port (e.g. 12345):

```bash
export S57_ALLOW_OWNED_BACKEND=1
export PYTHONPATH=src:tests
python -B -m adapters.mineflayer.s57_owned_llama_backend \
  --llama-server /path/to/llama-server \
  --binary-sha256 "<64-hex-server-binary-sha256>" \
  --gguf /path/to/actual/GGUF-model.gguf \
  --expected-sha256 "<64-hex-actual-model-sha256>" \
  --model-alias relay-self-s57-model \
  --port 12345 --gpu-layers 50 --ctx-size 4352 \
  --timeout-s 100 \
  --report s57-artifacts/owned-world-receipt.json \
  --server-log s57-artifacts/private-minecraft.log \
  --backend-log s57-artifacts/private-llama-backend.log
```

Adjust `--gpu-layers` to the actual model/VRAM budget; the requested value alone does **not** certify actual GPU placement. This runner internally calls the S56 physical driver, which requires actual native far WAIT / two near physical escape Action OUTCOME events, exactly one genuinely in-flight local L2 generation during first terminal L0 outcome, late output discarded, and exact item/World/provenance lineage. If L2 finishes before L0 Action outcome, mark FAIL; do NOT slow down or fake HTTP responses to obtain PASS. Startup, model hash, binding, self-World authority and unknown physical Action all fail closed.

## Evidence and limitations

The sanitized receipt contains binary SHA256, model SHA256, server PID, exact command parameters without paths, health readiness, native S56 result status, and owned-server termination. Backend raw logs are **local only**, may contain absolute paths and prompts, and must not be uploaded verbatim.

Even a controlled command line with an exact model path, healthy PID and file hashes is not independent proof of which bytes the server ultimately loaded, nor proof of GPU execution/VRAM release. Corroborate with server startup logs and GPU process-level measurement on actual WSL2 hardware before promoting a stronger `MODEL_LOADED_BY_BACKEND` or `GPU_PREEMPTION` result.

The GitHub CI test contains only **fake executable and fake GGUF bytes** and runs safe negative controls. Its terminal status is `S57_OWNED_PROCESS_INSTRUMENT_IMPLEMENTED`, not actual physical execution. If missing real hardware, local model or necessary privileged source, explicitly record BLOCKED/UNEXECUTED under Issue #412 and retain all PRs Draft/unmerged.

The runner's purpose is *one exact owned process + one bounded physical World qualification*. It does not create general self-set objectives, learned L1, real cancellation, RAM/VRAM deallocation proof or Mineflayer multi-agent autonomy.