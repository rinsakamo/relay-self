# Stage26 — Restored 2-Self Preset → REAL bounded L1 on one original llama.cpp GPU lane

**Status: implementation / source-shaped HTTP contract DEV. No genuine local Gemma, Paper or Mineflayer run on this branch yet.** Stack: Stage25 real native checkpoint [Draft #923](https://github.com/rinsakamo/relay-self/pull/923) at independently qualified HEAD `a4fd1c1426c1e00a43df5ccbf88ae5c3848c3164` (one real Paper trial, one original World). Stage21 [Draft #898](https://github.com/rinsakamo/relay-self/pull/898) owns the existing resident one-slot GPU lane. Do **not** replace either original owner with a synthetic second facade.

## What changed

The Stage25 runner remains default **SCRIPTED**, reproducing the previously qualified source route exactly. New arguments `--real-gemma-l1 --gemma-l1-endpoint <loopback-URL> --gemma-l1-model <model-id>` opt in to a real existing llama.cpp endpoint **before starting any disposable Paper server**. The model endpoint must be `http://127.0.0.1:<port>/v1/chat/completions` or localhost and an existing exclusive /slots API must report one **idle slot id 0**. No port discovery, remote provider, external GPU owner, unowned inference, or automatic external llama-server process launch. Optional `--gemma-l1-jev` uses the original provider's same-endpoint SystemOne/JEV request/parse path. The installed Gemma weights/model SHA and exclusive process ownership are **operator evidence**, not established by trusting a `--gemma-l1-model` string.

The original `ResidentLlamaInferenceLane` is injected into the original `OwnedResidentPhysicalBridge` before any native login. A and B share **one** original `ResidentCognitiveWorkOwner`, one serialized provider lane, original PhysicalIssueAdmission (resident MOVE **disabled**), and original native A/B session. Every staged owner retired at the first World save is matched to its original Self's recovered source. Old native sessions, Intent/Skill execution, physical Action grant and old GPU results do not resume. Paper restarts from the same source World as Stage25 (the fork is only restored/staged offline).

After fresh A/B re-JOIN, each Self gets a new correlated native probe; the CPU Schema builds ONE completed MOVE@1 invocation from its own accepted Preset/Target and presents exactly THREE fully enumerated choices: `1=original MOVE invocation`, `2=ESCALATE_L2`, `3=DEFER`. The hypothetical 1m-east destination is from the current **new** native source; do not confuse it with traversable terrain. This is an operator DEV target, not autonomous Target discovery. The two requests are submitted before either is awaited. The original shared GPU worker serializes the calls, checks /slots idle both **before** and **after** each HTTP invocation. Both decision facts are from the authenticated original owner lane and are NOT scripted.

A new native probe is requested **only after** each actual bounded result and backend idle witness. A/B then recheck original native session, original cognitive epoch, recovered Registry and source-bound original Target + fresh WorldBody. A valid result may be `READY`, `DEFER`, `ESCALATE_L2`, or `RECONSIDER`; no choice is silently replaced by MOVE or promoted to physical Action. An illegal number/foreign/outdated target/old Self result is HOLD. Requests are unique by Self/native session and first native seq. Do not adopt an L1 choice into permanent Memory without separate Self evaluation.

No MOVE, EAT, ATTACK, physical parametric Skill or L2 generator call is made. On model timeout /slots still busy, the **original owner** remains uncertain; a client timeout or cancelled Future is not GPU cancellation, and no clean retirement is claimed.

## Windows 11 / WSL2 WDDM GPU-sharing preflight clarification (2026-11-17)

**Do not require exclusive ownership of the entire RTX 3060.** Windows Desktop Window Manager, Explorer, ChatGPT UI and NVIDIA Overlay can legitimately use its graphics/video resources while a local CUDA llama-server runs. Windows `nvidia-smi.exe` may label these processes `C+G`, which **does not by itself demonstrate an active competing LLM/CUDA inference job**. WSL `nvidia-smi` not listing Windows processes is a WSL observability limitation: it is neither proof of global GPU exclusivity nor a standalone reason to HOLD. The earlier Stage26 PRE_WORLD_HOLD correctly performed **no unsafe work**, but applied an overly broad interpretation of “GPU exclusivity.” That earlier HOLD and the unconsumed one-shot World budget remain historical evidence.

Two independent, narrower safety requirements apply instead:

1. **RelaySelf inference endpoint/slot ownership (mandatory).** Identify exactly one original or user-approved dedicated llama-server process: its actual PID, executable SHA/build, argv, loaded GGUF path/SHA, private loopback-bound port, model alias, `-np 1` and working one-entry `/slots` API. Ensure the RelaySelf runner is the sole **authorized inference client** of that specific endpoint throughout the bounded experiment. Confirm `/slots` idle before the experiment, before/after each provider request, and after shutdown/retirement; preserve server stdout and observed connection/listener ownership. Don't infer prevention of every possible external connection from loopback or `/slots` alone. If actual foreign requests to the same endpoint appear, or the server/port owner cannot be identified, **HOLD**.
2. **Practical GPU resource availability / non-interference (mandatory).** Before starting, capture both Windows and WSL GPU totals, used/free VRAM, compute utilization and available per-process or GPU-engine telemetry. Preserve the preexisting **desktop GUI baseline** and review evidence for a known active **competing compute workload** or insufficient free VRAM. Ordinary desktop `C+G` processes alone are **not a blocker**. Model loading must succeed with expected GPU offload and enough VRAM; compare post-load memory/usage with the baseline, and watch for OOM, interference, GPU faults or a newly admitted competing heavy compute job during the one-shot. If an actual compute contender cannot be bounded or the model cannot fit safely, **HOLD without stopping any other process**.

Suggested read-only inspection, adjusted to capabilities of installed WDDM/WSL drivers: `nvidia-smi.exe --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv` on Windows; `nvidia-smi --query-gpu=memory.total,memory.used,memory.free,utilization.gpu --format=csv` in WSL; host `nvidia-smi.exe --query-compute-apps=pid,process_name,used_gpu_memory --format=csv` where supported, and Windows GPU-engine counters if available. Unavailable WDDM per-process VRAM or a missing Windows↔WSL PID mapping must be recorded as **limited observability**, not silently turned into “zero processes” or “no possible inference.” Attribute source PIDs through owned /proc/port/argv and independent Windows process/listener records when obtainable.

**Operational qualification is bounded, not absolute**: prove exclusive control of this model server's *inference work lane* and adequate GPU capacity, not universal ownership of the graphics card. If GUI processes remain present but show no demonstrated conflict, all owned-model/slot and capacity checks pass, it is valid to continue to a **single** isolated real World DEV trial. This does NOT prove that no other Windows app could ever use CUDA or that VRAM is reserved. Do not label such evidence “global GPU exclusive.” If necessary source evidence for the narrower requirements is missing, remain PRE_WORLD_HOLD with a precise identified blocker. No restarts to circumvent HOLD, no killing desktop processes, and no invalidation of Stage25's original evidence.

## Owned llama-server original-source preflight command (Stage26)

A read-only repeatable source auditor now lives at
`experiments/p0d_stage26_local_model_preflight.py`. It must be run **after**
the previously approved dedicated RelaySelf llama-server is independently
started by LocalCodex and **before any Paper World**. It does **not** start
or stop a process, send inference, authorize a World trial or prove global GPU
exclusivity. The stdout/exclusive on-disk JSON receipt records the specific
Linux PID, binary bytes, GGUF SHA, exact argv, 8192 context, `-np 1`, positive
GPU offload, independently attributed `127.0.0.1` LISTEN socket, and one
idle `/slots` response; an optional Windows WDDM snapshot is hashed for
provenance but **never** automatically treated as model contention.

An example with the disk identities previously observed on the user host
(rehash both files and replace `ACTUAL_PID`, `ACTUAL_PORT` and paths after
independent process inspection; **do not assume this PID exists**):

```bash
PYTHONPATH=src:. python experiments/p0d_stage26_local_model_preflight.py \
  --pid ACTUAL_PID \
  --endpoint http://127.0.0.1:ACTUAL_PORT/v1/chat/completions \
  --executable /home/rinsa/src/llama.cpp-jev-paper2-162/build/bin/llama-server \
  --executable-sha256 ACTUAL_VERIFIED_BINARY_SHA256 \
  --gguf /home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf \
  --gguf-sha256 c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed \
  --windows-gpu-snapshot /ABSOLUTE/EXISTING/windows-gpu-before.txt \
  --output /ABSOLUTE/EXISTING/evidence/model-source-preflight.json
```

The tool restricts the endpoint to an explicitly loopback-bound IPv4
listener whose inode is attributable to that exact Linux PID. A wildcard,
foreign PID, ambiguous flag, different model, duplicate parallel slot, busy
slot or missing process source HOLDs. If the owned server was launched
with otherwise supported equivalent CLI flags but this inspector cannot
prove them, **record a preflight HOLD and improve the observer/test
offline**, not an inferred PASS or unrelated process stop. On WSL, if
`/proc/net/tcp` or `/proc/<pid>/fd` is not sufficiently observable, record
the limitation and corroborate with another independent owned-listener
source before any real World; never fabricate a matching PID.

The positive receipt is deliberately classified
`OWNED_MODEL_SLOT_IDLE_DEV_NOT_FULL_GPU_ATTESTATION`. It has false-valued
`gpu_capacity_attested`, `external_client_absence_attested` and
`gpu_wide_exclusivity_attested`: **do not interpret it as permission to
launch Paper**. LocalCodex must additionally check Windows+WSL VRAM
baseline/post-model fit and offload, no demonstrated heavy competing
compute, endpoint client access control and live slot stability. Only
after those additional original-source checks and existing exact-HEAD CI
may the one-shot real World runner start.

## Stage26 — private inference-client admission contract (post-BOUNDED HOLD)

The second original-host PRE_WORLD_HOLD independently qualified actual Gemma
BOUNDED inference (177 prompt, 17 completion, 194 total, finish `stop`),
but found an **unprotected** loopback llama-server allowing unauthenticated
clients, with open CORS. No Stage26 Paper trial or A/B decision was performed.
The JEV request sent to the chat endpoint returned HTTP 400, so **BOUNDED
is the qualified mode, NOT JEV**. Historical HOLD and the untouched one-shot
World budget remain unchanged.

The Stage26 **real-Gemma runner now fails closed before Paper** unless it
has `--gemma-l1-api-key-file ABSOLUTE_0600_PATH`. The original provider
reads this owner-owned, 0600-or-stricter file once into memory and adds
`Authorization: Bearer` to model POST requests; its original shared
`/slots` witness uses the same header. Scripted Stage25 does not need
this file and explicitly rejects it. Neither token nor Authorization header
is written to HTTP **body** evidence, source manifests, runner reports or
process argv.

**Server and client use the same dedicated file**. The actual llama.cpp
build must support `--api-key-file` and `--cors-origins localhost`;
verify `llama-server --help` on the candidate build BEFORE launching.
Never use `--api-key TOKEN` (which exposes the secret in argv), and
never place the private key in the repository, Paper directory, CI or
public evidence artifacts. Keep its parent directory private (0700),
file mode 0600, and generate it with a cryptographically secure random
generator, not a fixed string. Example one-time local provision after
checking that this is a fresh, private, owned directory:

```bash
umask 077
mkdir -p -m 700 "$HOME/work/stage26-private-auth"
python3 - <<'PY'
import os
import secrets
from pathlib import Path
p = Path.home() / "work/stage26-private-auth/llama-server.key"
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="ascii") as f:
    f.write(secrets.token_urlsafe(48) + "\n")
    f.flush()
    os.fsync(f.fileno())
print("private-key-created")
PY
```

Example existing verified server invocation must include (alongside the
independently reverified binary/model hashes, offload and context):

```text
--host 127.0.0.1 --port ACTUAL_PORT
-np 1 -c 8192 -ngl 999 --no-context-shift
--alias stage26-gemma
--api-key-file /home/rinsa/work/stage26-private-auth/llama-server.key
--cors-origins localhost
```

The **pre-World** owner inspector accepts
`--api-key-file /home/rinsa/work/stage26-private-auth/llama-server.key`
and verifies that the **original process argv** explicitly binds the
same file and localhost-only CORS. It first GETs `/slots` using the
private Bearer token, then performs three **unauthorized negative probes**:
anonymous GET /slots, wrong-token GET /slots, anonymous malformed
POST /v1/chat/completions. All must return **401 or 403**; a successful
or 400/500 response is HOLD. None of these tests request an accepted
inference. This checks actual server access control, rather than
assuming it from a start flag. Preserve the status code/headers in
local non-secret original evidence. Only after successful auth preflight
and already required GPU, owned PID and model checks may the real
World runner receive the same `--gemma-l1-api-key-file`.

**Boundaries**: CORS is a browser policy, not client authentication.
A 0600 file prevents access by other UIDs, **not same-UID adversarial
processes** or a compromised owner. Private loopback plus a fresh,
unguessable key prevents *unauthorized* accepted model calls under this
bounded single-owner DEV threat model but **cannot prove that a future
client with a stolen/shared valid token will never connect**. Preserve
server request activity and model `/slots` before/after each Self call;
HOLD if unknown authorized requests, unexpected GPU activity, or
key material exposure is observed. Keep Paper process environments
free of the key/token and do not use an ad-hoc namespace that breaks
its bootstrap asset resolution. No real Paper trial is authorized
**solely** because the preflight inspector returns success; the
operator must separately validate the credential guard and availability.

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
