# I Lane I2e — original raw OPEN L2 / BOUNDED L1 capture and independent audit (DEV)

Parent: Issue #1078. Original Draft: PR #1080. This is implemented on I2's existing branch only; B #1050, I integration #1076, D #1035 and C/I4a #1067 have not been merged.

## Evidence boundary

Prior I2d is a **CPU/offline state machine**, not a real-Gemma observed decision. For a later original authenticated Paper/Native trial, I2e adds a strict two-POST raw HTTP capture adapter, a request/result/Owner readback manifest, and a separate-process verifier. I2e does **not** connect to the user's Windows/WSL2 Paper instance, local RTX 3060 or GGUF; GitHub CI uses monkeypatched urllib HTTP fixtures, not a real inference endpoint.

The historical Stage28b generation has no recorded exploration activation, and older cognition can lack a durable PatternRegistry. Never install exploration FULL or a saved Registry by heuristic to pass preflight. The **future new v3 source gate** added here requires BOTH A/B to have an actual original same-generation recorded empty SchemaSnapshot (no learned EXPLORE Pattern yet) and a persisted, matching PatternRegistry. No old generation is upgraded, and no qualified real World exists in GitHub Actions.

## Code paths

- src/relay_self/i_lane_i2e_future_original_preflight_dev.py: calls the unchanged Stage28c2a original Owner source/generation verification and I2c recorded Schema rebootstrap; checks complete A+B roster, exact committed-source and restored files, empty exploration modules, no pre-existing learned exploration, no active Intent/Question, no pending Action, physical observation-only and both Selves OFFLINE. Returns only OFFLINE Owner handles; no World/Native/GPU/Paper permission. Refuses historical v1/v2, partial A/B and modified files.
- experiments/i_lane_i2e_original_dual_model_raw_dev.py: a genuine LlamaCppRelayProvider subclass, reusable by the original ResidentLlamaInferenceLane, permits exactly **one OPEN L2 followed by one BOUNDED L1** in this order; no JEV/THINK, no third POST, no automatic retry, explicit model alias, owned fresh raw directory. Saves the exact UTF-8 bytes submitted to urllib and the response entity body bytes, status, size and SHA-256, using exclusive writes. It cannot claim socket packets/wire headers. Network errors cause HOLD and retain partial proof.
- The separate run_i2e_original_dual_raw function requires the same original attached bridge/lane and observation-only authority; calls the existing I2d submit/await/result/Owner acceptance. It writes exact pre/post cognition JSON bytes and a typed request/ticket/handoff/result report only after two completed HTTP calls and durable readback. Partial evidence on failure remains HOLD, never success or retry. It does not start a World.
- experiments/i_lane_i2e_independent_dual_model_audit_dev.py: **separate-process read-only CLI** taking --raw-dir. It validates the *exact* nine-file roster, excludes symlinks, rehydrates typed L2 OPEN and L1 BOUNDED requests, re-renders request JSON as actual llama.cpp provider would, checks both HTTP body bytes and receipts, reconstructs the original I2 handoff prompt fingerprint, verifies A/B Self scope and original ticket uniqueness, independently extracts L2 output and L1 decision, checks that the actual L2 proposal was the L1 context, and computes the exact durable Owner PatternRegistry delta from before/after cognition. DEFER/UNRESOLVED require no saved change. No synthetic response or model-choice flag is treated as independent real-World provenance.

CLI read-only inspection (after externally qualified capture):

    PYTHONPATH=src:. python3 -m experiments.i_lane_i2e_independent_dual_model_audit_dev --raw-dir /ABSOLUTE/OWNED/I2E-RAW

A successful model-bundle audit reports **I2E_DUAL_RAW_MODEL_AND_OWNER_CPU_BUNDLE_AUDITED** and explicitly sets original_native_paper_world_independently_verified=false and real_world_dev_pass=false. Raw entities and their digests are not a cryptographic authentication of the actual originating model process and cannot replace new original Native/Paper/World log receipts. A mocked provider fixture can exercise this exact mechanism without proving actual hardware/World observations.

## Pre-World blocked gates

The existing Stage28c2b real runner hard-pins the **historical Stage28b source** and cannot accept a newly created v3 original A/B source as-is. This code does **not** change the existing runner's pins, past I1 evidence or original historical immutable manifests to trick the gate. A separate fully source-pinned runner/admission that accepts the new v3 generation and invokes I2e preflight before World creation is still required. Then the operator environment must independently verify:
- actual new typed future A/B original Owner generation plus COMMITTED pin, new fork, Paper archive and historical Native denylist;
- exact original supervised Node/Mineflayer 4.39.0, oxygen owner patch, Paper 1.21.8 and Java/JAR provenance before creating a World;
- exclusive original llama-server process, GGUF SHA (Stage24g pinned), RTX 3060 compute PID/socket owner, one idle slot, endpoints/models; do not assume GitHub Actions has GPU;
- one isolated real Paper World (at most one trial, no automatic retry); A/B original JOIN, fresh request-correlated Native/Paper/WORLDBODY, then original L2 & L1 real HTTP POST bytes; one actual model-driven Owner result and if accepted a later same-generation typed v3 cut;
- independent *second-process* raw Native/Paper, GGUF/HTTP, Owner/WAL, retired GPU/CPU and checkpoint comparison. Do not label a model bundle as authenticated World or historical old Pattern as new.

## HOLD statuses

**I2E_REAL_WORLD_NOT_RUN / I2E_REAL_GEMMA_NOT_RUN / I2E_OLD_SCHEMA_RESTORE_HOLD / I2E_NATIVE_PAPER_INDEPENDENT_SOURCE_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN**.

Never set REAL_WORLD_DEV_PASS from the model-only audit; physical Actions are zero and the learned exploration GOAL is initially unbound with no Skill or Target.
