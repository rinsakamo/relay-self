# S55 — Actual local model receipt instrument (not an actual model test result)

Stacked on S54 PR #404. S55 is explicitly an **opt-in local physical qualification handoff**. It does not run a model in GitHub Actions.

On the user-controlled WSL2 environment, start an actual loaded `llama-server` or LM Studio model offering the OpenAI-compatible endpoint `http://127.0.0.1:1234/v1/chat/completions`.

From the repository root:

```bash
PYTHONPATH=src python -m adapters.mineflayer.s55_local_model_probe \
  --model "your-loaded-local-model-alias" \
  --gguf "/path/to/actual/model.gguf" \
  --expected-sha256 "<full-64-hex-model-digest>" \
  --endpoint "http://127.0.0.1:1234/v1/chat/completions" \
  --max-tokens 64 --timeout-s 60 \
  --report s55-artifacts/local-inference.json
```

`--gguf` is optional if the model binary is not available on that filesystem; without it, model-file identity remains less constrained. `--allow-think` permits exactly one extra THINK attempt only if the initial bounded choice is unresolved. The S47 CognitionBudget enforces the call budget; the S52 LoopbackChatProvider rejects non-loopback endpoints, proxy egress and redirects. Request and answer text are intentionally not exported in the receipt. The GGUF path is never copied to the report. SHA256 is computed locally and no GGUF is uploaded.

The JSON records actual local HTTP request receipt (if one occurred), per-call token data where supplied, roundtrip duration, finite-choice RESOLVED/UNRESOLVED result and GGUF file hash. **Neither a successful localhost response nor a matching on-disk GGUF hash proves that the server loaded that exact GGUF, used RTX GPU acceleration, stopped its generation, or released VRAM.** Independent runtime/model identity, physical local hardware measurements and S54 Minecraft World + real L2 concurrency remain mandatory before those physical claims can be promoted.

GitHub deterministic tests use a fake HTTP responder and deliberately fake `.gguf` bytes; their only conclusion is `LOCAL_PROBE_INSTRUMENT_QUALIFIED`, never that a real model was observed.

Next real-model gate, requiring LocalCodex on the target WSL2 machine:
1. Record installed llama.cpp version/commit, selected model path and exact SHA256, runtime model identifier and actual backend process/session with local network binding.
2. Start a real inference server with one selected GGUF and hard memory/token budget. Keep private model files/local secrets off GitHub.
3. Run the command above and preserve report + backend-side corroborating inference log. Fail closed if the actual model identity is unsupported or inconsistent; do not promote the receipt alone.
4. Execute native World (S54) while genuinely prolonged local model L2 is pending. Record wall-clock timestamps for native event, independent Action proposal/issue and terminal OUTCOME, original model completion, actual backend stop ACK and GPU release only if measured. Never confuse host async cancellation with GPU preemption.
5. Requalify on one exact HEAD and keep PR Draft until the actual local physical result is unambiguously PASS.
