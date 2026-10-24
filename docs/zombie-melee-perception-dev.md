# Zombie melee cue sensing before L0/L1 reflex work — isolated DEV

**Status: SOURCE_STAGED / PYTHON3.12_UNVERIFIED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Authority: Adaptive Cognition #426 (AC-1/3/5/6), SelfWorld #633, integrated Self #537, S18 #354. Not a zombie combat runtime implementation or a modification to Draft PR #634.

## User-scoped first step

Instead of projectiles/skeletons, begin with a zombie:

- L1 target: observe arm raise/attack preparation, choose an anticipatory response;
- L0 target: sense that a close melee attack is about to connect, produce a quick reflex;
- L2 target, later: choose terrain/spacing where those cheap behaviors work.

These targets are **hypotheses**, not current source capabilities. A wind-up is not implied by a mob label, nor is an imminent hit confirmed by mere proximity.

## Existing product source audit (PR #634 HEAD 0ceb75bbc41066b63d84037271e2b69159fc86df)

- adapters/mineflayer/bridge.mjs attaches entitySpawn, entityGone, entityHurt, move, forcedMove, time, inventory etc.; it does **not** subscribe to entitySwingArm, entityMoved, or attack wind-up.
- adapters/mineflayer/protocol.mjs::nearbyEntityObservation samples a 16-block bounded registry, capped at 16 entities. It includes id/name/type/distance/current 3D position and coverage; no enemy velocity, server-time-aligned target position, attack state, arm pose or line-of-sight. snapshotFromBot includes self position but no detailed terrain blocks.
- adapters/mineflayer/python_protocol.py MineflayerEntityFact = id/name/type/distance/position; no motion or attack flag.
- adapters/mineflayer/present_projection.py preserves positive probe id/name/distance/position but not entity_type or animation.
- Current product S49 host focuses on positively observed zombie witnesses and owner-authorized MOVE_AWAY, not dodge/hit prediction.
- Mineflayer public API has entitySwingArm(entity), representing a **swing animation**, not necessarily an earlier raised-arm phase or guaranteed damaging strike. Timing/coverage in pinned Mineflayer 4.39.0 + Java 1.21.8 remain unverified through real World source.
- Source labels (mineflayer) are producer-local provenance, not independent raw native attestation. No raw animation packet or attack timing proof was obtained.

## Additive DEV implementation

- experiments/zombie_melee_perception_dev.py: review_zombie_melee consumes existing correlated typed MinecraftPresent via immutable ZombieMeleeFrame. Two positive positions for the same zombie within bounded **native seq-gap** are compared. If closing and current distance <= explicit experiment-supplied radius, returns **L0 POSSIBLE_CONTACT**, not confirmed hit or attack intent. One reading/occlusion/missing entity/source gap -> UNKNOWN, not safety.
- L1 optional input is strictly a typed **SyntheticArmSwing** fixture and yields **ARM_SWING_OBSERVED_SYNTHETIC**, not pre-impact WINDUP_DETECTED. Missing swing -> UNKNOWN rather than no attack. Synthetic event cannot claim a native source.
- tests/test_zombie_melee_perception_dev.py: source-bound positives and negative controls for missing entity, static/receding/too-far, truncated coverage with positive entity, unknown type, wrong entity ID, stale seq, duplicate/cross-Self/session request, fake provenance, contradictory distance, future/stale/forged arm cue, source replay and Action non-promotion.
- No motor owner, command, S17/S10/Memory writer, L0 gate change, observation packet schema change, Java/Node server. NOT_INDICATED does not mean safe.

**Causal warning:** even if a native swing event arrives, it may coincide with or follow damage. Do not elevate it to a predictive L1 wind-up trigger without independent source-time ordering and held-out real hit/no-hit samples. Mineflayer seq does not establish game ticks, duration or velocity.

## Correct next source gate before physical dodging

1. Verify pinned Mineflayer 4.39.0 entitySwingArm implementation and Minecraft 1.21.8 animation packet identity against installed source in independent worktree; isolate mock event injection first.
2. In a separately owner-authorized disposable DEV World with a raw capture, independently check whether zombie swing arrives **before** damage/hurt; record hit/no-hit, distances, cue recall and precision. If absent/too late: L1_WINDUP_NOT_ATTESTED.
3. Determine a timed, source-qualified possible-contact cue. Existing range alone cannot prove imminent impact; false alarms/misses and observation gaps must be reported.
4. Only after source validation, add a narrowly scoped, opt-in read-only perception tap with versioned source contract; preserve frozen probe shape and S49 Action owner.
5. Evaluate L0 rapid dodge that can fail at cliffs, L1 anticipatory movement, and later L2 battlefield choice in separate steps. Do not automatically activate a reflex from offline synthetic cues.

## Local validation and adoption

Independent WSL2 worktree pinned to exact candidate HEAD; Python **3.12.3** focused candidate plus existing S49/SelfWorld/Action/S18 guards, Ruff and contracts, original protected82 and historic770 hashes before/after. **Tests not locally executed by this author: no PASS asserted.** CI/FULL/real-model/Minecraft/Action/OUTCOME/S10/SCIENCE/QUALIFICATION not performed. Do not fast-forward Draft PR #634, alter #545 or main; future adoption needs explicit owner review.
