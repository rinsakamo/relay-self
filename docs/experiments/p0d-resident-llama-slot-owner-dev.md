# P0-D Stage 21 — Resident llama.cpp single-slot owner (DEV)

Stack: #898 on #894 → #892 → #889 → #885. Exact source HEAD and CI runs are recorded in PR #898. This stage adds a **bounded, opt-in shared model execution lane**, not a new Self, memory owner or physical Action issuer.

## Decision: shared GPU model, not N copies

Target: RTX 3060 12GB, Gemma‑4‑12B‑it Q4_K_M, llama.cpp with `-np 1 -c 8192`. One model server is shared between all Self. L1 bounded choice and L2 open generation both use the existing `LlamaCppRelayProvider`; only **one generation request** may enter this owned lane at a time. A Self identity, work ref, current native session, original cognitive epoch, World epoch and backend ref are bound at submission.

The provider uses its existing JSON output/Structured Output handling. The exact current original `CheckpointedCognitiveOwner` is the only place where an admitted model result may be applied to retained memory.

## Stop is not cancellation

- Synchronous `quarantine` closes the **original PhysicalIssueAdmission** and original per-Self cognition writers, then marks the GPU lane's jobs for that Self nonadoptable, before any async wait. Queued unstarted work is canceled with its concrete `concurrent.futures.Future`.
- A running `urllib` HTTP inference is **NOT** disconnected/canceled by `Future.cancel` or `asyncio.wait_for`. The owned provider thread is deliberately allowed to complete. A new per-call `GET /slots` witness must observe one slot `id=0,is_processing=false` **after** that provider has completed (even after HTTP errors), in addition to the preflight idle probe. If the server is unavailable, a slot is busy, multiple slots appear, or an output times out without independent idle proof, the backend is marked uncertain, GPU admission is held, and the affected Self cannot become OFFLINE.
- A queued B request can be canceled and B may logout while A's already-running inference occupies the shared model. That does **not** imply the shared GPU has become free for new B work; it only proves B had no running model task.
- A's old result remains nonadoptable after logout/re-login even if it arrives late: adopting any Memory requires an already completed backend request, current Self/native/World/cognition epoch, and the original cognition owner's writer gate.
- On fully retired all-Self World-only checkpoint, the bridge requires original WAL/native/cognitive retirement and a **fresh idle /slots** probe before permitting World save/restart.

**Critical distinction:** `/slots` idle is evidence of no model *generation processing* in the observed exclusive backend. It is **NOT** evidence the model was unloaded, GPU context destroyed, KV cache cleaned, or VRAM returned. This stage records `vram_released=False` and `llm_model_unloaded=False` explicitly.

## Ownership/source assumptions

`LlamaCppSingleSlotWitness` is enabled only for explicit loopback `http://127.0.0.1:PORT` or `http://localhost:PORT`, with same host/port for the optional L1 SystemOne endpoint. It accepts only a singleton `/slots` response. The operator must independently ensure the endpoint is a dedicated **owned** llama-server process configured with `--parallel 1`, that the requested model and process identity match, and that **no other HTTP client** can bypass the lane. Without that independent process/port/endpoint ownership, a transient idle readback cannot prove a given generation stopped. The native Minecraft and physical bridge is not a backend ownership proof.

Current `llama.cpp` implementations may continue generating after HTTP client disconnect; the public `/slots` shape is a debug API and can change. Do not assume DELETE stream or TCP shutdown signals prove GPU stop. The test server in CI is only a controlled Python HTTP emulator, not llama.cpp.

## Offline verification

- Uses **actual existing `LlamaCppRelayProvider`** HTTP requests, both bounded structured L1 and open L2, against a Python HTTP server emitting response-compatible JSON and `/slots` states.
- Uses **actual original Python** cognitive owner, CPU work fence, PhysicalIssueAdmission and canonical WAL, with synthetic Mineflayer sensor stream and faux-Paper console OS process from earlier stages.
- N=2/10/100: current model result can be adopted through original cognitive owner, old token cannot be reused after logout/re-login, other Self continue physical EAT and cognitive Memory, one serialized backend request at a time.
- A active request: retirement deadline expires and only A stays QUARANTINED; A may later retire on actual provider completion. B retains World/CPU/physical rights but the global model slot is still occupied.
- B queued but not executing: pending future canceled on B logout, no B inference sent while A generation continues.
- Model HTTP success but `/slots` still busy: fail closed and taint GPU admission; two-slot/nonlocal endpoint refuses preflight.
- World-only archive permitted after all source-qualified original physical+cognitive+inference retirements and strict backend idle readback.

Tests are DEV simulations, not actual model/GPU measurements.

## LocalCodex real backend qualification gate

1. **First read repo, #828/#851/#860, #894/#898 and this document.** Use a clean dedicated worktree at exactly the HEAD of Draft #898. Do not edit unrelated branches.
2. Obtain explicit operator approval for a *real Gemma / GPU* execution, separately from any real Paper World approval. If absent, STOP before model startup with `HOLD_REAL_GPU_GRANT`. Do not start Paper or Mineflayer for this GPU-specific qualification.
3. Pin the existing `llama.cpp` binary build, actual GGUF model path, SHA256, GPU/CPU/VRAM, dedicated loopback port and no-other-clients isolation. Use a separately owned `llama-server` (one slot, `-np 1 -c 8192 --no-context-shift -ngl 999`) with `/slots` enabled. Never kill or reconfigure a server that the operator has not allocated for this test.
4. Implement an operator-gated **real** harness using the existing provider and new owner. Capture backend PID/start and exact log, initial `/slots` idle; L1 structured request output/schema; L2 open request output; `/slots` observed busy during model generation and idle *after* the backend returns; self/native/world task identity; monotonic timestamps; original cognitive memory adoption; model GPU use via `nvidia-smi`. Test A online→quarantine during slow L2, B retains CPU/physical mock permission, A late result cannot be adopted, A logout only after backend finish. Test queued B request cancellation without B model invocation. No unbounded generation or destructive interruption; an unresponsive inference is HOLD, not PASS.
5. Qualify exactly whether model-slot idle holds across at least two iterations on the allocated hardware. Explicitly distinguish model remains in VRAM from per-activity GPU memory release; do not claim GPU VRAM freed if the process/model stays resident.
6. Offline tests, CI and PR evidence; report actual local commands, process identity, source hashes, precise timestamps, errors, logs and source-qualified readbacks. Mark `REAL_LLAMA_SLOT_IDLE_DEV` only on real source proof; no real Paper, GPU cancellation/preemption, model unloading, external peer channel or QUAL/SCIENCE claims.

If real semantics differ from the mock, fix code + add regression before re-running the operator-approved source. If external cancellation is impossible or unsafe for the pinned llama.cpp build, **keep the wait-for-natural-completion design** and report the limitation instead of manufacturing a cancel receipt.
