# RelaySelf S59-B — typed native stop ACK, slot reuse and GPU proof separation

Authority: RelaySelf S59 Issue #417; S59-B Issue #419; frozen S59-A Draft PR #418 exact HEAD `c67c832551fed5c57cd5ade8af8d6594bf3b3a8d`; RelayLM backend source-design owner [#3037](https://github.com/rinsakamo/relay-lm/issues/3037#issuecomment-6089387986). S59-B is a sibling new stacked Draft, not an in-place change to S59-A, S58 or physical S57.

## What is newly implemented

`adapters/mineflayer/s59b_stop_ack_contract.py` contains a strict finite-state **evidence-shape** checker, not a live control plane:

```text
ADMITTED -> GENERATING (real progress observed)
         -> STOP_REQUESTED (independent operator; exact subject)
         -> NATIVE_ACK (worker processed exact request, slot released)
         -> SLOT_IDLE (independent observer, same process)
         -> SLOT_REUSED (new distinct completion on same PID+slot)
```

`NativeStopSubject` must bind: owner session, work ID, completion ID, work generation, backend PID, native worker task ID, slot ID, slot generation, World sequence. STOP is impossible until monotonic observed generated tokens progress. Stop authorization is independent of the model's text. A worker ACK must include that exact subject, exact full completion ID, **the same** native worker task ID as the subject, native worker provenance, `processed=true` and `slot_released=true`. These strings and values require runtime attestation; a local test can fabricate them, so passing this checker **cannot prove physical stop**.

The same process/slot result is a separate stage. It requires independently observed slot idle with same backend PID and a new different completion ID and increasing slot generation that actually completes tokens. A process restart or whole-backend kill never qualifies request-scoped stop or slot reuse.

`GPU_COMPUTE_QUIESCED` cannot be inferred from the native ACK alone, and `VRAM_RELEASED` cannot be inferred from either: loaded model-weight residency is expected to continue when the server remains alive. S57 normal whole-process exit VRAM recovery is a different claim. The entire S59-B offline snapshot therefore unconditionally sets `physical_qualification=false`, `in_flight_backend_preemption_qualified=false` and `runtime_stop_command_sent=false`.

## Why the S57 binary remains blocked

The exact S57 llama.cpp build 10874 source has an internally queued `SERVER_TASK_TYPE_CANCEL`, but the handler (`tools/server/server-context.cpp:2454-2463`) doesn't publish a completion ACK, and the HTTP reader destructor queues a cancel (`tools/server/server-queue.cpp:602-621`) without waiting for worker execution. The public `reasoning_end` control and busy slot `erase` are **not** request stop endpoints. See RelayLM #3037 for the narrowly scoped proposed extension.

No S59-B tool sends stop traffic or invokes a real model, native Minecraft, CUDA or VRAM instrumentation. Tests use synthetic timestamps, task IDs and fake native ACK objects to reject wrong/foreign/stale identity and missing worker processing. They qualify only the checker logic.

## Qualification and handoff

Offline command:

```bash
PYTHONPATH=.:src:tests python -m pytest -q tests/test_feature_s59b_stop_ack_contract.py
```

The physical experiment remains **BLOCKED** until a separately authorized RelayLM implementation supplies an independently attestable exact request-scoped worker stop ACK, a real slot observer and same-server reuse measurement. When such a backend becomes available, integrate it in another explicit physical LocalCodex lane with independent GPU utilization sampling. Never mutate existing S57/S58 results, forge a completion ID, fake slow inference, or use RelayLM #46 or S31-B resources.

Issue #417 stays open, S59-A Draft #418 remains frozen and S59-B Draft stays unmerged. No model output can grant Action authority.
