# RelaySelf L — Zombie movement prediction / Stage Z0

Date: 2026-11-02. Stacked after Draft #689. **Offline only**. Parent #689 physical A=PASS_DEV and B1-U=limited PASS_DEV; B1-N/Q not established. Preserve its H1/H2 and all originals.

## Discovery from existing code

The original S49 real runner executes "kill @e[type=minecraft:zombie]" and restages a new zombie between stages. It cannot be reused as evidence of the SAME zombie's 20-tick trajectory. Native Mineflayer nearby-entity observations include an integer ID, entity name/type, position, native seq and bounded coverage, but do NOT include stable spawn-instance/UUID binding or exact server ticks in the same observation. Native seq is NOT a Minecraft tick. A world time packet is only a sample and cannot be silently equated to the exact tick of every position.

**Physical same-zombie motion prediction therefore requires a NEW source owner** to independently authenticate exact Paper tick, entity UUID and spawn generation, Mineflayer observed client position, world/session identity and source chronology. A shaped JSON row with a SHA is not proof of original Minecraft provenance.

## Stage plan

Z0 (this PR): readonly future x/z position forecast at an exactly 20-server-tick horizon, using a strict typed source contract. Frozen before the future tick. Reject cross-identity, changed spawn generation, missing/truncated entity coverage, nonfinite coordinates, teleport, stale seq, inconsistent SHA, source beyond prior window, missing exact target tick. Horizontal Euclidean error in meters. CHEAP baseline controls: stationary versus prior 2-sample constant velocity. Also an opt-in L2 unadmitted shadow numeric prediction or explicit abstention. Never generate any Action or invoke Gemma. **Every review remains tagged source_authenticated=false** until an independent actual Paper/source auditor is implemented. Hence never claim actual World ability or B1.

Z1 (future independent work): one disposable Paper1.21.8 World, one real persistent zombie in a safe controlled arena, player behind verified barriers and existing L0 safety interrupts intact, with no combat. Collect precisely attested entity position and identity at first/second prediction-time samples, then after exactly +20 Paper server ticks. Do not kill/respawn the target in a trajectory. Wrong entity, missing target time, or observer detachment -> DEFER/FAIL with raw preserved; do not interpolate to force a successful score. Identify whether line-of-sight, enclosure or no-AI toggles altered motion; never confuse scripted movement with learned prediction.

Z2 (future): actual Gemma-4 GGUF/llama.cpp strict JSON Schema ON and Reasoning OFF after a fresh real preflight. Freeze numeric x,z at 20-tick horizon or abstain before observing the future; independently verify original source and compare against CHEAP_STATIONARY and CHEAP_CONSTANT_VELOCITY. Existing original S49 is sole actor; L2 does not choose or issue Actions.

Z3 (future): separately predeclared different conditions (obstacles, active chase, relative player motion, limited sensing); compare causal applicability and holdout, and only later attempt L1 acquisition. B2 independent improvement and C self-selected experiment require separate evidence. No L0 automatic promotion.

Skeleton attack/proj prediction should follow only after the zombie source and safe motion predictions qualify.

## Z0 code and limits

Module: adapters/mineflayer/l_zombie_20tick_shadow.py

- parse_zombie_source: exact bounded original-shaped JSON row bytes plus SHA; typed entity UUID, spawn instance, entity ID, world UUID, session, native seq, server tick, coordinates, complete coverage.
- baseline_forecasts: stationary and constant-velocity 20 tick point positions, frozen SHA and source IDs; no learning.
- shadow_forecast: optional L2 candidate position or explicit abstention, no actual L2 call.
- review_forecast: only exact target server tick and identical entity lineage and later native seq, horizontal Euclidean error (m). All outputs remain source_authenticated=false.
- No changes to S49, native L0, physical action executor, Mineflayer player controls, Gemma, Paper plugin or persistent SelfMemory.

Synthetic unit tests and old L/S49/SelfWorld regressions run on CI. No real zombie, no physical Minecraft World, no real Gemma model, no automatic retry. Separate local World grant will be necessary for Z1.

Classification: ZOMBIE_Z0_OFFLINE_CONTRACT_ONLY / REAL_NEW_WORLD_0 / REAL_NEW_GEMMA_0 / PHYSICAL_IDENTITY_AND_TICK_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
