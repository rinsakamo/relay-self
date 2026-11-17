# Stage26 — Restored 2-Self Preset → REAL bounded L1 on one original llama.cpp GPU lane

**Status: implementation / source-shaped HTTP contract DEV. No genuine local Gemma, Paper or Mineflayer run on this branch yet.** Stack: Stage25 real native checkpoint [Draft #923](https://github.com/rinsakamo/relay-self/pull/923) at independently qualified HEAD `a4fd1c1426c1e00a43df5ccbf88ae5c3848c3164` (one real Paper trial, one original World). Stage21 [Draft #898](https://github.com/rinsakamo/relay-self/pull/898) owns the existing resident one-slot GPU lane. Do **not** replace either original owner with a synthetic second facade.

## What changed

The Stage25 runner remains default **SCRIPTED**, reproducing the previously qualified source route exactly. New arguments `--real-gemma-l1 --gemma-l1-endpoint <loopback-URL> --gemma-l1-model <model-id>` opt in to a real existing llama.cpp endpoint **before starting any disposable Paper server**. The model endpoint must be `http://127.0.0.1:<port>/v1/chat/completions` or localhost and an existing exclusive /slots API must report one **idle slot id 0**. No port discovery, remote provider, external GPU owner, unowned inference, or automatic external llama-server process launch. Optional `--gemma-l1-jev` uses the original provider's same-endpoint SystemOne/JEV request/parse path. The installed Gemma weights/model SHA and exclusive process ownership are **operator evidence**, not established by trusting a `--gemma-l1-model` string.

The original `ResidentLlamaInferenceLane` is injected into the original `OwnedResidentPhysicalBridge` before any native login. A and B share **one** original `ResidentCognitiveWorkOwner`, one serialized provider lane, original PhysicalIssueAdmission (resident MOVE **disabled**), and original native A/B session. Every staged owner retired at the first World save is matched to its original Self's recovered source. Old native sessions, Intent/Skill execution, physical Action grant and old GPU results do not resume. Paper restarts from the same source World as Stage25 (the fork is only restored/staged offline).

After fresh A/B re-JOIN, each Self gets a new correlated native probe; the CPU Schema builds ONE completed MOVE@1 invocation from its own accepted Preset/Target and presents exactly THREE fully enumerated choices: `1=original MOVE invocation`, `2=ESCALATE_L2`, `3=DEFER`. The hypothetical 1m-east destination is from the current **new** native source; do not confuse it with traversable terrain. This is an operator DEV target, not autonomous Target discovery. The two requests are submitted before either is awaited. The original shared GPU worker serializes the calls, checks /slots idle both **before** and **after** each HTTP invocation. Both decision facts are from the authenticated original owner lane and are NOT scripted.

A new native probe is requested **only after** each actual bounded result and backend idle witness. A/B then recheck original native session, original cognitive epoch, recovered Registry and source-bound original Target + fresh WorldBody. A valid result may be `READY`, `DEFER`, `ESCALATE_L2`, or `RECONSIDER`; no choice is silently replaced by MOVE or promoted to physical Action. An illegal number/foreign/outdated target/old Self result is HOLD. Requests are unique by Self/native session and first native seq. Do not adopt an L1 choice into permanent Memory without separate Self evaluation.

No MOVE, EAT, ATTACK, physical parametric Skill or L2 generator call is made. On model timeout /slots still busy, the **original owner** remains uncertain; a client timeout or cancelled Future is not GPU cancellation, and no clean retirement is claimed.

## LocalCodex operator-authorized trial

User has previously granted **standing explicit Minecraft EULA consent and real disposable World DEV approval** in this project; do not ask again. Always pass `--eula-accepted --real-world-dev-grant`. Validate actual model/process owner, Gemma GGUF Q4_K_M SHA256, exact model bytes, exclusive llama-server PID/port/args and n_parallel=1, original Paper+plugin SHA, JVM, Node and CI exact HEAD. Run a disposable localhost World **once** only, no blind reruns on HOLD.

One example after an existing *independently verified* local llama-server is started (replace paths, model alias and plugin hash with actual owned values; do not silently start second server):

```bash
PYTHONPATH=src:. python experiments/p0d_real_preset_checkpoint_dev.py \
  --paper-jar /absolute/verified/paper-1.21.8-build60.jar \
  --paper-sha256 8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e \
  --plugin-jar /absolute/built/P0BRecorder.jar \
  --plugin-sha256 ACTUAL_SHA256_FROM_BUILD \
  --scratch-parent /absolute/new-disposable-parent \
  --eula-accepted --real-world-dev-grant \
  --real-gemma-l1 \
  --gemma-l1-endpoint http://127.0.0.1:8080/v1/chat/completions \
  --gemma-l1-model ACTUAL_VERIFIED_MODEL_ALIAS
```

If the currently configured llama.cpp instance supports the existing SystemOne/JEV structured format, add `--gemma-l1-jev` explicitly; do not assume the backend can parse that format. Do not use an offline HTTP stub to claim actual GPU Gemma evidence. Under real-JEV mode, `render_llama_cpp_jev_request` and the original parser must be observed functioning on the actual model.

## Required independent evidence and honest classifications

Save actual Paper stdout/PID/boot IDs, A/B actor UUID, plugin/Paper verified SHA, every World+Self cognition/owner/WAL and committed generation manifest, same-source Paper restart, the model server PID/model file SHA, /slots before/after each model call (the original lane witnesses slot state), source-correlated native first/recheck stdout, request IDs, serialized completion token counts/finish reason, model-chosen number and selection status, live physical Action count and unresolved WAL count. No global GPU-idle/VRAM-release claim beyond witnessed exclusive `/slots`. For model data, the typed ProviderDecision and call facts are sufficient; do not record unneeded private model reasoning traces.

Qualifying classification when real sources agree: `REAL_PAPER_2SELF_PRESET_LLAMA_L1_OBSERVED_DEV`, with per-Self `READY/DEFER/ESCALATE_L2/RECONSIDER` exactly as actually observed. Only report **real Gemma model-qualified** if process/loaded weights are independently corroborated. A non-READY model answer is not physical readiness. A Paper/Fork reconstruction is not attested merely because the same original source World restarted. Existing multi-owner autosave timing gaps remain DEV, not atomicity.

CI tests deliberately use a controlled local HTTP server and synthetic native source, and establish only `STAGE26_L1_BACKEND_OWNER_OFFLINE_DEV`; they **do not** start real Minecraft or Gemma. **`QUAL_NO_GO / SCIENCE_NOT_RUN / PARAMETRIC_PHYSICAL_ISSUE_HOLD`** remain unchanged. When the real local one-shot trial has not been performed, report `REAL_STAGE26_NOT_RUN` explicitly.


## Stage26 model HTTP original-source audit (post-HOLD patch)

The first pre-World HOLD identified a real gap: original model HTTP response-body bytes had not been saved and missing token counts/finish_reason were accepted. The Stage26 opt-in model provider now arms an **exclusive empty original-model-http directory** in the one-shot evidence tree before starting Paper. Each actual L1 request ID is hashed into an independent filename; the exact serialized HTTP request body and **original response body bytes** are saved with exclusive create, file mode 0600, flush and fsync. An independent fsynced source manifest records request ID, both SHA256 hashes and response-body byte count *before* response parsing. Each completed A/B selection reads those original source files back, compares digest/length to the committed manifest and places exact file paths + hashes in its per-Self witness. A duplicate request ID, missing response file, modified source or malformed JSON cannot be reported as successful evidence. This captures **HTTP bodies, not the HTTP header stream or socket-level packet trace**; errors/oversize responses HOLD rather than yielding a success classification.

For Stage26 BOUNDED, `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens` and `choices[0].finish_reason="stop"` are all required; total must equal prompt + completion. If the real backend omits any of them, preserve raw bytes and **HOLD without a second World**. Stage26 JEV SystemOne has a distinct no-generated-token protocol; this strict evidence mode requires `usage.input_tokens`, `usage.output_tokens=0` and explicit `finish_reason="stop"` (and records their original source). A JEV server that does not expose an explicit finish_reason **cannot qualify this Stage26 path** merely by passing the ordinary provider parser. Use standard BOUNDED only when independently confirmed compatible; never silently switch between JEV and BOUNDED after World creation. Both routes are original llama.cpp provider operations; no synthetic provider may be used to assert real Gemma.

Previous user-host preflight **did not find the owned dedicated llama-server process**. This source-audit fix does not change that physical requirement. Do not spawn a second/unowned model server or proceed to Paper without independently verifying a model process, actual GGUF path/SHA, exclusive PID and single idle /slots, appropriate model protocol, and original Paper/plugin jar SHA. The standing Minecraft EULA + isolated World DEV approval remains valid. This patch was **offline-only** until an owner-qualified real trial is reported.
