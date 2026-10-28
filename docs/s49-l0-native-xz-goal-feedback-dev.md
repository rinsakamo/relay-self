# RelaySelf — precommitted native XZ goal / L0 WALK or WAIT (DEV)

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**. Owner stays original S49 / S14→S15→S16. No tick lockstep, new native reader, extra Action issuer or model calls.

## Why geometry replaces scalar addition

The previous `S49_L0_OBSERVED_WALK_AND_REAL_WAIT_TWO_WORLD_DEV` reported second Action movement **0.8149785454473797m**, third WALK movement **0.24950809810395602m**, scalar sum **1.0644866435513358m** and scalar-to-1m error **0.06448664355133582m**. That is *not* the distance to the actual World target.

The former WALK World saved genuine S16 XZ:
- first after: x=-4.5, z=-1.4698428355056374
- second before: x=-4.5, z=-1.1374763821016294 (input-off drift +0.3323664534040080m)
- second after: x=-4.5, z=-0.32249783665424975
- third before: x=-4.5, z=-0.019457114592288494 (input-off drift +0.3030407220619613m)
- third after: x=-4.5, z=+0.23005098351166753

For a target **1.0m forward of the first native S16 after-position**, the actual target Z is **−0.4698428355056374**. Thus actual XZ error after second Action is **0.14734499885138765m past goal**, not the purported 0.1850m short by scalar metric; after third WALK the error is **0.699893819017305m past**. The S16 native positions are authoritative; the old scalar sum is NOT proof of target attainment. The input-off drift may include Minecraft momentum, server/client latency and effects after the native S16 observation; its exact mechanical decomposition is not proven.

## New DEV target + source rules

At **first original S16 close**, the first real before→after XZ vector is normalized to a unit forward direction. At **second original Action admission**, before its S15 physical dispatch, an explicit world-position target is committed: first-after + (unit forward × target offset). The target is immutable for the remaining source session, tied to first original native Action ID; it is not selected post hoc from final motor motion.

- **WAIT World**: precommitted target offset 1.0m, second input still observes previous S16 and proposes roughly 0.198s. The second native S16 after-position and fourth fresh L0 probe are both assessed against exact target XZ. If target has been passed (forward residual <=0) or currently within 0.20m, original L0 at next fresh zombie event chooses WAIT with *no* S14 grant or third Action. Native threat distance <1.5m retains original danger priority.
- **WALK World**: precommitted target offset 2.0m but second input remains a **1.0m calibrated incremental request**. The second S16 after-position is recorded. Third original L0 physical MOVE is independently authorized only after fresh fourth native probe. Third input duration is bounded based on **forward XZ residual at that fresh probe**, not second/third scalar travel sum. If passed/within 0.20m, lateral deviation >0.25m, stale or foreign session/probe or immediate threat: fail closed instead of issuing a harmful forward WALK. The native third S16 *end XZ* is compared against the precommitted target.
- Both modes require explicit `S49_L0_XZ_GOAL_DEV_ONLY=1`, existing original forward sprint S49 and bounded WALK/WAIT DEV gates. Previous non-XZ code paths remain available unchanged and default is disabled.

Metrics: target X/Z, first-native XZ bearing, second after XZ, fresh fourth native probe XZ, third before/after XZ, signed forward residual, lateral deviation and Euclidean error. Explicit negative tests reject reversed-direction, lateral, stale foreign source and false scalar goal success. No automatic direction reversal, heading controller, actual destination qualification or L2 authority.

All experimental Worlds are disposable official Minecraft 1.21.8 Mojang servers; owner single S49; Python 3.12 focused/Ruff/Node22 before run; always preserve exact raw reports. main/#545/#634 untouched.
