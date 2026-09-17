# Mineflayer cognition llama.cpp physical transaction

This is an experiment-only physical qualification surface for #73 / #46. It is not a RelaySelf runtime provider API or semantic authority.

The transaction follows the current RelayLM v1 llama.cpp qualification carriage closely enough to keep the tested local model condition comparable:

```text
clean RelaySelf checkout
-> prove 127.0.0.1:1234 is free
-> verify ~/src/llama.cpp checkout and llama-server build identity
-> verify the pinned Gemma GGUF SHA-256
-> record NVIDIA GPU identity
-> launch exactly one owned llama-server
-> non-generatively attest /health, /v1/models, /props, /slots
-> require context=8192, slots=1, context shift disabled, Q4_K_M
-> run the fixed four-condition Mineflayer cognition probe
-> terminate only the transaction-owned process
-> retain evidence
```

The server condition is:

```text
-m <pinned GGUF>
--host 127.0.0.1
--port 1234
-ngl 999
-c 8192
-np 1
--no-context-shift
-lv 4
--log-timestamps
--log-file <transaction evidence root>/llama-server.log
```

Every cognition request additionally carries:

```json
{
  "reasoning_effort": "none",
  "cache_prompt": false
}
```

No request is retried, replayed, repaired, or sent to a fallback provider.

## Canonical WSL invocation

From a clean current RelaySelf checkout:

```bash
python -m experiments.mineflayer_cognition_llama_cpp_transaction
```

The current WSL defaults are derived from `$HOME`, not a username:

```text
llama.cpp root: ~/src/llama.cpp
llama-server:   ~/src/llama.cpp/build/bin/llama-server
GGUF:           ~/models/gguf/gemma-4-12B-it-Q4_K_M.gguf
port:           1234
repeats:        20
```

Override paths only when deliberately qualifying a different physical layout:

```bash
python -m experiments.mineflayer_cognition_llama_cpp_transaction \
  --llama-cpp-root /path/to/llama.cpp \
  --artifact-path /path/to/gemma-4-12B-it-Q4_K_M.gguf \
  --evidence-root /tmp/relay-self-mineflayer-evidence
```

If `--evidence-root` is omitted, a fresh root is created under `/tmp` and printed in the transaction summary.

The port must be free before the transaction starts. A pre-existing server is never reused or killed.

## Evidence

A successful or blocked transaction writes the evidence it owns under one root. When the corresponding phase was reached, the root contains:

```text
binding.json
runtime-attestation.json
llama-server.log
request-ledger.json
cognition-result.json
cleanup.json
transaction-summary.json
```

`request-ledger.json` contains the exact post-control request bodies and hashes in execution order. `cognition-result.json` contains raw model text, strict parsed plan ids, invalid-output records, and the existing semantic/neutral comparison summary.

This evidence is external model/system-quality evidence only. It does not establish a `Value`, `Emotion`, `Fear`, `Attention`, or `Focus` owner, and it must not be promoted to runtime semantics merely because the model shows a treatment effect.
