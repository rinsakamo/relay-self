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

```bash
PYTHONPATH=src:. python -m pytest -q \
  tests/test_stage24a_resident_l1_move_dev.py \
  tests/test_stage24b_resident_real_l1_integration_dev.py \
  tests/test_p0d_stage23_raw_source_audit_dev.py \
  tests/test_p0d_stage23_real_runner_adapter_dev.py
ruff check src tests experiments adapters observability
```

Offline synthetic tests do not constitute actual Gemma/SystemOne or native Paper evidence. Stage24b is a one-turn test; Stage25 is the separate multi-turn learning/evaluation experiment.
