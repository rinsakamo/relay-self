# Bレーン Stage28c-2c — original A/B real Gemma BOUNDED DEV (one shot)

Parent [#966](https://github.com/rinsakamo/relay-self/issues/966);
stacked on original recovered A/B CPU L1 [#1021](https://github.com/rinsakamo/relay-self/pull/1021).
Stage28c2b #998 **already** independently proved real original A/B rejoin and
WorldBody adoption; do not claim that this also proves a new Gemma response.
All consumed past attempts/evidence remain immutable.

## Source contract / scope

- Original archived Paper World UUID
  `f9221410-b99e-417d-98f4-e98938586472`.
- Fork branch `fork-3883122c-6edb-4017-bd82-00fc4324aded`.
- Stage28b original 285/285 evidence SHA256
  `7a202d68f6d275a0031f9c7091e0e1e7f33c4976c4565461d425e040f87209f4`.
- Stage28b `COMMITTED.json` SHA256
  `d1425c49a5ef0ff03486931427907aeed6eccf568494efd8177ed96d3ce3f4ee`.
- Stage28c1 original 29/29 manifest SHA256
  `28d1a7548f98ab74d5e7359462e4a1f7baf5c43f80e4a9fbd4a2c74065e915c1`.
- Previous successful Stage28c2b real A/B rejoin evidence SHA256
  `5a684637746ebf7e9b406d8dd7ab67601055e01b01430d96afbadd87dcaedb84`.
  **Do not rerun its execution copy**
  `/home/rinsa/stage28c2b-reconnect-execution-20261119`.
- Stage28b original `W221`, new Bukkit process tick, native Minecraft World day
  time are **not** numerically interchangeable.

The Stage28b original Owner's saved `PatternRegistry` has no proven
EXPLORE+MOVE Preset in this generation. On the previous rejoin both native
worldbodies had food/health 20, empty inventory/nearby Entities and oxygen
UNKNOWN. This experiment therefore **does not inject MOVE/EAT/ATTACK**
targets or new innate Patterns merely to produce a motor choice. It offers
the CPU-derived `ESCALATE_L2` / `DEFER` numbered decisions; selecting
ESCALATE **does not actually submit a hidden L2 model request**.

**One new isolated Paper execution copy only**. A and B each send exactly
one genuine Gemma **BOUNDED /v1/chat/completions** request on a
single shared `ResidentLlamaInferenceLane`. No Jev, no THINK retry, no
L2, no Physical Action, no Skill start, no Intent commit, no peer send.
Model residency may persist; actual /slots idle is attested after calls
and during normal original A/B retirement. No 60s autosave claim.

### Source model preflight

Use the *already loaded* llama.cpp Gemma-4-12B-it Q4_K_M process, actual
GGUF (not filename guess), one RTX3060 owned PID, mapped model bytes
pinned to Stage24g SHA256
`c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`,
`/v1/models` alias, loopback socket owned by that PID, GPU PID from
`nvidia-smi`, and exactly one idle `/slots` slot. The original endpoint
must be `http://127.0.0.1:<actual-port>/v1/chat/completions`.
Model gate uses identical local endpoint for its two read-only arguments
but the actual provider is **ordinary strict JSON BOUNDED**, not a JEV call.
Do not change the pinned GGUF digest or fake slot evidence to satisfy the gate.

Preinstall locked Mineflayer and oxygen owner patch **before inspection**,
run targeted existing Stage28 tests, and verify Java21 and Node22.
Both source World jars must match Stage24g pinned SHA.

Read-only inspection (NO World, no model POST; actual model is already loaded
by operator):

```bash
PYTHONPATH=src:. python3 -m experiments.stage28c2c_real_original_l1_dev \
  --generation "$EXACT_STAGE28B_TYPED_GENERATION" \
  --restored /home/rinsa/stage28c1-restored-575198-20261118 \
  --stage28b-evidence /home/rinsa/evidence/stage28b-1dcd48-20261118 \
  --paper-jar "$STAGE24G_PAPER_JAR" --plugin-jar "$STAGE24G_PLUGIN_JAR" \
  --gguf "$ORIGINAL_LOADED_GEMMA_GGUF" --llama-pid "$ACTUAL_LLAMA_PID" \
  --model-alias "$ACTUAL_GEMMA_MODEL_ALIAS" \
  --llama-endpoint "$OWNED_LLAMA_CHAT_COMPLETIONS_URL" \
  --eula-accepted --inspect-only --java "$JAVA21_BIN" --node "$NODE22_BIN"
```

Expected: `STAGE28C2C_SOURCE_MODEL_INSPECT_PASS` with one idle slot,
source verified real PID and `world_started=false model_post=false`.
Inspection HOLD => no World started.

After exact-HEAD CI + all source/asset/model preflight PASS, one
**new** never-before-existing copy and evidence paths; no auto retry:

```bash
PYTHONPATH=src:. python3 -m experiments.stage28c2c_real_original_l1_dev \
  --generation "$EXACT_STAGE28B_TYPED_GENERATION" \
  --restored /home/rinsa/stage28c1-restored-575198-20261118 \
  --stage28b-evidence /home/rinsa/evidence/stage28b-1dcd48-20261118 \
  --paper-jar "$STAGE24G_PAPER_JAR" --plugin-jar "$STAGE24G_PLUGIN_JAR" \
  --gguf "$ORIGINAL_LOADED_GEMMA_GGUF" --llama-pid "$ACTUAL_LLAMA_PID" \
  --model-alias "$ACTUAL_GEMMA_MODEL_ALIAS" \
  --llama-endpoint "$OWNED_LLAMA_CHAT_COMPLETIONS_URL" \
  --execution-dir "$NEW_STAGE28C2C_EXECUTION_DIR" \
  --evidence-dir "$NEW_STAGE28C2C_EVIDENCE_DIR" \
  --eula-accepted --real-world-dev-grant --model-post-grant --execute-once \
  --java "$JAVA21_BIN" --node "$NODE22_BIN" \
  --timeout-s 180 --presence-timeout-s 12 --model-wait-s 60
```

The original user-approved Minecraft EULA/World DEV grants are already
permanent for RelaySelf. Do not re-ask. Each CLI opt-in flag is explicit.

**Run order:** immutable old source hashes -> separate saved World copy ->
new owned Paper process + tick/presence witnesses -> original A/B native
new sessions & request-correlated probes -> independently witnessed BOTH
PRESENT events and post-presence nonce ACK -> original Owner A/B adopt exact
new WorldBody -> saved Schema/Intent CPU candidate freeze (no new Pattern
or invented Target) -> verify actual model PID/GPU/1 slot idle -> attach
existing single GPU lane to ORIGINAL bridge -> A one model POST/response,
B one model POST/response -> verify exact source ticket and bounded
selection after provider thread terminates and /slots idle -> normal
A/B logout/retirement with GPU fence -> Paper QUIT + all dimension
save/stop & exit0. Never treat raw POST capture alone as completion.

**On timeout:** a Python HTTP timeout does NOT stop a llama.cpp request.
Do not retry the model call or reuse GPU; quarantine unretired owner scope.
If incomplete, report HOLD even if native/Paper cleanup was forced. Do not
terminate foreign llama PID; operator resolves backend uncertainty separately.

## Independent audit — fresh Python process only

```bash
PYTHONPATH=src:. python3 -m experiments.stage28c2c_independent_real_l1_audit_dev \
  --result "$NEW_STAGE28C2C_EVIDENCE_DIR/stage28c2b-recovered-world-result.json" \
  --generation "$EXACT_STAGE28B_TYPED_GENERATION" \
  --restored /home/rinsa/stage28c1-restored-575198-20261118 \
  --stage28b-evidence /home/rinsa/evidence/stage28b-1dcd48-20261118 \
  --execution-dir "$NEW_STAGE28C2C_EXECUTION_DIR"
```

The first runner's classification remains
`REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING`;
this is **not** L1 success.

Separate auditor first reruns full original Stage28c2b native/Paper/World
source, original Owner cognition, WAL and GPU retirement checks with
exactly TWO completed model POSTs. Then re-reads independent original
Gemma source preflight receipt (pinned GGUF hash), frozen per-Self request,
native probes and original saved `PatternRegistry`. Independently rebuilds
CPU Need/Goal summary and ensures no unobserved physical target or new
Pattern. Finally hashes ACTUAL `bounded-{1,2}-request/response-body.bin`
and reads real HTTP 200 receipts, compares exact strict-JSON original
rendered request to POST bytes and decodes the original response. Checks
both numbered answers, model usage, fresh scopes, original request IDs,
candidate hash, unchanged Identity/Owner state and Action/Skill/Peer=0.

Only after this passes can it emit:

`REAL_RESTORED_A_B_FRESH_GEMMA_L1_BOUNDED_CHOICE_DEV`.

Until actual local real Paper + actual model POST + independent audit:

`STAGE28C2C_REAL_RUNNER_OFFLINE_ONLY /
REAL_GEMMA_L1_NOT_RUN / PHYSICAL_ACTION_NOT_RUN /
60S_AUTOSAVE_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN`.

Capture all original byte files and SHA256SUMS with readback. Report
HEAD, CI, native/Paper/model PID, World UUID/fork, new session/request IDs,
native/world/Paper clock domains separately, exact choice count/status,
raw HTTP hashes, A/B retirement, all-dimension Paper save, independent
auditor result and HOLD reasons to parent Issue #966 and stacked PRs.
