# RelaySelf S59-A — exact-build backend stop admission audit (NO physical cancellation)

Authority:
- Issue #417 (S59 distinct in-flight cancellation / backend ACK / slot resource test)
- S57 genuine physical model/world qualification: Issue #412 comment 6082863237
- Exact frozen parent S57 Draft PR #413 HEAD `564b52cfead748258594be65927072489fee963d`
- S58 separate Draft PR #416 HEAD `afff12002ecf2954bcc4742f6c268b31e81cc7c6`, never modified here.
- Actual S57 binary SHA256 `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536` (llama.cpp build 10874 / 0.4.0-dev)
- Actual S57 stated llama.cpp build source SHA `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d` (public upstream commit; 2026-09-09).

## Exact source findings at this pinned HEAD

Read the canonical version of `tools/server/server-context.cpp` and `tools/server/README.md` at this exact source commit (NOT newer master):

1. A native `SERVER_TASK_TYPE_CANCEL` handler exists and releases the matching internally identified slot/task. The mere existence of internal machinery **does not** establish a supported authenticated HTTP stop endpoint or an independently observable per-request stop ACK.
2. The public `POST /v1/chat/completions/control` handler explicitly supports only `reasoning_end` and rejects every other control action. Ending a reasoning block is **not** equivalent to cancelling generation.
3. `POST /slots/{id_slot}?action=erase` operates on the prompt cache, and the server **defers** a request if the slot is processing. An erase command is not request cancellation, nor does it prove an in-flight stop.
4. `GET /slots` can observe busy/idle slots, but an idle reading is not itself an ACK that the server performed an authenticated stop. The HTTP adapter capturing a disconnect predicate is not evidence that the generation loop actually stopped.
5. S57 normal owned-process termination and aggregate VRAM 870 -> 8703 -> 870 MiB is a distinct qualified result. It **cannot** justify in-flight GPU preemption.

Read-only audit implementation `adapters/mineflayer/s59a_backend_stop_audit.py` requires the exact binary full SHA256, exact clean source checkout HEAD and these three canonical source files. It performs no inference, no HTTP sends, no stop commands, no node/Minecraft launch, and never changes the source checkout. Even successful static corroboration yields `BLOCKED / REQUEST_SCOPED_STOP_ACK_NOT_AVAILABLE_ON_QUALIFIED_PATH`, not a physical pass. A binary hash plus source HEAD is not a cryptographic build-provenance binding; `source_binary_build_binding_attested=false` remains explicit.

## LocalCodex read-only command

Only if the original S57 binary and exact SOURCE HEAD are still available on disk:

```bash
git -C /path/to/llama.cpp-source rev-parse HEAD
sha256sum /path/to/S57/llama-server
PYTHONPATH=.:src:tests python -B -m adapters.mineflayer.s59a_backend_stop_audit \
  --llama-server "/path/to/S57/llama-server" \
  --expected-binary-sha256 "ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536" \
  --source-checkout "/path/to/llama.cpp-source" \
  --report "s59-private/stop-admission.json"
```

This command intentionally returns exit code **2 (BLOCKED)** even if the static source matches: it is a controlled **negative** result establishing that no independently verified request-scoped backend-stop/ACK path has been qualified. It never tries a guessed endpoint, `/slots/...erase`, `reasoning_end`, host task cancel, client socket closure or full process shutdown as an ersatz stop.

If the source HEAD differs or a newer binary was built, create a **separate** fresh feasibility audit with that binary/source identity and the actually documented stop API; never promote features from master onto build 10874. Any backend implementation to expose true request-scoped stop (unique work ID, request generation, native ACK and slot reuse) belongs to a dedicated authorized backend repair lane, with negative tests, not to frozen RelaySelf S57/S58. Avoid consuming S31-B or #46 resources.

## Admission requirements for a future separate S59-B physical test

- Actual owned, attested model/server process/slot. A long *genuine* generation observed progressing via backend token/slot counters; no fake/blocked HTTP.
- Independently authorized, exact-generation request-scoped stop. Distinct timestamps for progress, urgent L0 trigger, stop request, native backend ACK, same PID slot idle and a follow-up real model call that completes. Client disconnect alone fails.
- Independent nvidia-smi GPU utilization samples before/after; distinguish compute quiescence from model-weight VRAM residency, KV/task buffer reclamation and whole-process shutdown. Request stop must leave server alive. A model completing naturally before stop does not count.
- Exact contract boundaries: `HOST_CANCEL_ONLY`, `TRANSPORT_CLOSED_NO_ACK`, `BACKEND_STOP_ACK_OBSERVED`, `SAME_PROCESS_SLOT_RELEASED`, `GPU_COMPUTE_QUIESCED`, `DYNAMIC_GPU_ALLOCATION_RELEASED_IF_MEASURED`, and `FULL_PROCESS_EXIT_VRAM_BASELINE_RESTORED` remain independent propositions.
- Physical qualification is unavailable and must remain BLOCKED when no real backend request-scoped stop endpoint or native ACK exists. The S59-A offline negative controls are **instrument-only**.

Do not alter S18–S58 frozen stage artifacts, PR Draft status, RelayTheory/Paper2 MAIN40, #46 scientific subject, or S31-B. Do not trigger real GPU/World usage from CI.