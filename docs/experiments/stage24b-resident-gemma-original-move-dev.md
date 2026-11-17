# RelaySelf Stage24b — genuine Gemma SystemOne → one bound MOVE → original WorldBody

Parent #911, Stage24a Draft #919, physical predecessor Stage23b PASS via #914 (exact `9085d56037919e8360ea1315121b7689d5c64c61`).

**Classification pending live test:** `STAGE24B_OFFLINE_DEV_ONLY / REAL_L1_WORLD_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN`.

## Implementation boundaries

The new opt-in `experiments/p0d_real_resident_presence_dev.py --b-autonomous-l1-dev` path retains Stage23b's exclusive Paper 1.21.8 disposable localhost World, two native B/A owners, A logout while B stays resident, real original physical issuer, WAL, START/STOP, full native stdout and Paper readback, A login and optional World-only restart. The Stage23b operator-selected flag is mutually exclusive; it is **not** used to select the Skill/Target.

The bridge's existing `ResidentLlamaInferenceLane` uses a real `LlamaCppRelayProvider` with `systemone_endpoint` (Jev/System One), plus exclusive one-slot `/slots` idle checks. LocalCodex must verify the exact owned process/PID/backend identity, same local port for endpoint and SystemOne, single `-np 1`, and real Gemma before the experiment; this runner does **not** launch a llama-server or take ownership of arbitrary open local ports. No fake provider can be injected via the real runner CLI.

After A quits, B's first read-only original native probe provides current Body/World data. Stage24a CPU Schema derives an eligible low-pressure exploration Goal and gives four prebound finite relative MOVE options (`forward/back/left/right`, **constant pulse 0.35s**) plus ESCALATE_L2 and DEFER. The four controls are WorldBody Action catalogue references, **not** observed safe destinations. No operator-selected MOVE option, no generated coordinates or budget.

One actual SystemOne request is submitted through the B self-owned single-slot inference lane. The returned typed ProviderDecision is checked by the existing RelayEngine bounded contract. **Two new native probes after inference** must belong to the same session and have distinct request IDs; the selected dependency is revalidated on the latest probe. Nonphysical options, invalid/unresolved response, stale selected body/goal/target, GPU busy/uncertain, WAL dirtiness and wrong owner cause **no new native issue** and an explicit HOLD with retained evidence; never silently replace with `forward`, never retry.

Before any original Action admission, a frozen `B-original-systemone-choice.json` is written exclusive/fsynced with actual accepted model decision, request choices+context, source refs, candidate set SHA256, inferred CPU epoch, post-inference readback and elapsed time. It records provider response *after parser* and call facts, **not archived raw HTTP bytes**. It does not itself grant physical permission.

After Self selects the option and the existing owner creates its Intent/Skill/Action IDs, the runner additionally freezes a separate `B-stage24b-preissue-binding.json` **before native issue**. Its typed `PhysicalActionBinding` includes the exact choice-file SHA256, selected number, original IDs, Goal, Skill, target, native sequence and request ID. The top-level report must reread this binding and verify the final native raw sidecar's selected probe identity. This improves source linkage but is still the same Python process, not independent external proof of model intent.

Only a qualified READY prebound option can call the **original** `CheckpointedCognitiveOwner.commit_intent`, `start_skill`, `propose_resident_l1_move` → original `PhysicalIssueAdmission.issue_move`, with two independent typed physical DEV grants, canonical fsynced PREPARED/WAL and one source-scoped START/STOP. The selected control/preset is forwarded unchanged. Stage23b native stdout and 8+8 tick stillness readback remain the same; the raw-native verifier explicitly cannot attest L1 selection. New finalizer additionally reads original frozen model evidence, checks SHA and Goal/Skill/Target/preset/choice against the physical action report; only then claims `REAL_PAPER_B_L1_SELECTED_MOVE_CORRELATED_WORLD_ONLY_DEV`. It **does not** claim Paper Action-ID causation, destination arrival, learning improvement or forced GPU preemption.

## Second attempt after pre-World SHA transcription HOLD (new provenance, never a replay)

Original HEAD `c3b1347b` **PRE_WORLD_HOLD_JAR_SHA_ARGUMENT_MISMATCH** is preserved under the evidence directory referenced in [PR #925](https://github.com/rinsakamo/relay-self/pull/925#issuecomment-6919173080) and Issue #911. Its exact-HASH failure occurred before any World creation/model call. Do NOT rewrite, erase or recategorize it.

The **separate opt-in DEV launch adapter** `experiments/stage24b_pinned_assets_launch_dev.py` eliminates manually copying any SHA256 argument. It independently hashes the real jar bytes, compares them with these source-grade original archival pins, and passes the *computed* digest to the **unchanged guarded original World runner**, which rehashes the assets itself:

- Official Paper 1.21.8 build60: original trusted `PAPER_1218_60_SHA256`.
- Archived P0BRecorder jar: `cabf144a275c1582ecbbdcb6fb394b311f0705f5ca7d330bb80659437abe324e` (64 lowercase hex digits).

The known 69-character mistyped plugin value **must fail** before creating any new World. A rebuilt plugin with different bytes is **not silently trusted**: independently check it and update the reviewed pin only if appropriately qualified. The adapter has no model, native, motor or Issue owner.

First run a **read-only** asset check (no GPU, no World and no grant flags):

```bash
PYTHONPATH=src:. python -m experiments.stage24b_pinned_assets_launch_dev \
  --paper-jar "$PAPER_JAR" --plugin-jar "$PLUGIN_JAR" \
  --scratch-parent "$ISOLATED_SCRATCH" --eula-accepted \
  --inspect-only
```

Verify **both** lines, `STAGE24B_ASSET_CHECK_OK` and `STAGE24B_RUNTIME_CHECK_OK`, with pinned hashes and an empty scratch folder. The inspect-only path now reuses the **exact original runner** `_verify_local_runtime(java,node)` gate: Java 21, Node 22 and installed Mineflayer `4.39.0` under **this checked-out worktree's** `adapters/mineflayer/node_modules/mineflayer/package.json`. An external `NODE_PATH` satisfying `require('mineflayer')` is **not evidence** of this original run contract. Inspect-only never installs dependencies or creates a World. Verify actual model PID, binary, GGUF SHA and single owned `/slots` *separately*.

The second Stage24b real DEV attempt on HEAD `c95b33d0` stopped **before World creation** with `PRE_WORLD_HOLD_LOCKED_MINEFLAYER_DEPENDENCIES_ABSENT`: the preflight checked external `NODE_PATH`, but the original runner requires the worktree-local locked package. This immutable HOLD and its SHA256 manifest (`6f8ca305c7cf16c8e272fc0664df86c29ad36c2205eab758784529a698cbab2e`) remain untouched; see [PR #925 report](https://github.com/rinsakamo/relay-self/pull/925#issuecomment-6931827673).

Before starting a **new** explicitly isolated attempt, LocalCodex should in its **new worktree only** verify `adapters/mineflayer/package-lock.json` and `package.json`, and if the dependency is absent, run the repository-standard locked installation:

```bash
npm ci --prefix adapters/mineflayer
```

This is a provisioning step, **not** a retry of the former World attempt. Do not use `npm install` to change the lock, create symlinks into external `node_modules`, bypass the original gate, alter `NODE_PATH` to conceal missing dependencies, or touch an unrelated worktree. Confirm exact version `4.39.0`, run the adapter's existing Node tests, then run **inspect-only again** and require both `*_CHECK_OK` receipts. Only afterwards prepare the independently owned real model process and invoke `--execute-once` in a fresh scratch/evidence scope. Failure is pre-World HOLD and the real runner must not start. A prior empty Jev HTTP 422 validates malformed input rejection **only**, not a real model choice.

After checking the exact HEAD/CI and ensuring that this attempt has a **new** evidence and scratch scope, authorize **one** original trial:

```bash
PYTHONPATH=src:. python -m experiments.stage24b_pinned_assets_launch_dev \
  --paper-jar "$PAPER_JAR" --plugin-jar "$PLUGIN_JAR" \
  --scratch-parent "$ISOLATED_SCRATCH" --eula-accepted \
  --execute-once --real-world-dev-grant --grant-real-llm \
  --llama-endpoint "$LLAMA_ENDPOINT" \
  --systemone-endpoint "$SYSTEMONE_ENDPOINT" \
  --model "$ACTUAL_SERVED_GEMMA_MODEL"
```

This delegates `b_autonomous_l1_dev=True`, `b_selected_move_dev=False`, `world_only=True`, `b_pulse_seconds=0.35` to the existing `run_real_resident_presence` function. It does not retry on `DEFER`, `ESCALATE_L2`, provider failure, WAL unresolved, native uncertainty, or Paper HOLD. Do not introduce a second physical owner or switch to the old operator-selected MOVE. The old direct runner CLI below remains supported and unchanged; the pinned launcher is preferred for this exact pre-World recovery.

## Operator-local real run (one new disposable World)

Preflight: repo / #828 / #843 / #904 / #911 / #919 / this Draft PR; verify exact HEAD and 5/5 CI; existing operator EULA and real World DEV approvals are valid without reasking. Real LLM execution is separately opt-in via `--grant-real-llm`. Verify exclusive local backend and no other clients. Use actual installed Paper 1.21.8 build60 and P0BRecorder jars; resolve their paths and verify SHA256 independently, never invent jar locations. Example placeholders below must be replaced after preflight:

```bash
PYTHONPATH=src:. python -m experiments.p0d_real_resident_presence_dev \
  --paper-jar "$PAPER_JAR" --paper-sha256 "$PAPER_SHA256" \
  --plugin-jar "$PLUGIN_JAR" --plugin-sha256 "$PLUGIN_SHA256" \
  --scratch-parent "$ISOLATED_SCRATCH" \
  --eula-accepted --real-world-dev-grant --grant-real-llm \
  --b-autonomous-l1-dev --world-only \
  --b-pulse-seconds 0.35 \
  --llama-endpoint http://127.0.0.1:8080/v1/chat/completions \
  --systemone-endpoint http://127.0.0.1:8080/v1/systemone \
  --model "$ACTUAL_SERVED_GEMMA_MODEL"
```

The real opt-in **does not include** `--b-selected-move-dev`; that is Stage23's operator choice. A model DEFER/ESCALATE is genuine cognition evidence, but not Stage24b physical PASS. Before any second trial on another World, report the original result as HOLD; never automatically retry ambiguous physical movement or dirty WAL.

Preserve the complete new source archive and SHA256s including model choice, native stdout and sidecar, original WAL/Intent/Skill/Action IDs, Paper quit/movement/join, World-only generation. Record CPU latency, model wall time, selected choice, Model/GPU slot state, Action admission/settling. Validate root/nested consistency. If nonphysical or stale and no MOVE is issued, classify without changing original evidence. Only if one actual model-selected physical Action matches the original WAL/native/Paper sources do we claim bounded DEV success.

## Offline regression

Include `tests/test_stage24b_pinned_assets_launch_dev.py`, which verifies read-only inspect, real byte pinning, 69-character typo refusal, source tampering/symlink refusal, missing grants, **the original worktree-local runtime gate and external NODE_PATH rejection**, and exact one-call delegation. This regression uses synthetic jars and does not run Minecraft.


```bash
PYTHONPATH=src:. python -m pytest -q \
  tests/test_stage24a_resident_l1_move_dev.py \
  tests/test_stage24b_resident_real_l1_integration_dev.py \
  tests/test_p0d_stage23_raw_source_audit_dev.py \
  tests/test_p0d_stage23_real_runner_adapter_dev.py
ruff check src tests experiments adapters observability
```

Offline synthetic tests do not constitute actual Gemma/SystemOne or native Paper evidence. Stage24b is a one-turn test; Stage25 is the separate multi-turn learning/evaluation experiment.
