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

## Verified real Minecraft DEV result (2026-10-28)

[Actions #40659516287](https://github.com/rinsakamo/relay-self/actions/runs/40659516287) **completed/SUCCESS**, exact tested code HEAD `ce524ccaf41fc70120568e6d1e69d33a5f3f0c48`. Original Mojang 1.21.8 two independent disposable Worlds, Python3.12 focused **94 PASS**, Ruff PASS, Node22 syntax PASS, original Node/Server terminal source. Original S49 Action owner, real first-second S16 records, original fourth L0, typed native XZ source readback verified. No forced tick synchronization, extra issuer/reader or real model call.

### WALK World — fixed 2.0m WORLD-XZ relative goal

session `fbae271d-92e8-4143-95c7-841d0a65c61c`.
- First S16 after: (5.5, **−1.4698428355056374**) in (X,Z); locked goal (5.5, **+0.5301571644943626**) **before second S15**.
- Second S16 after: (5.5, **−0.32249783665424975**); true XZ goal error **0.8526550011486123m**, forward remaining +0.852655m.
- Fourth genuine fresh native probe: (5.5, **−0.019457114592288494**). Note another 0.303040722062m input-off displacement. Up-to-date forward remaining **+0.5496142790866511m**, cross-track zero, real native threat distance 2m.
- Original third S14 authorized `MOVE_FORWARD` WALK, hold **0.13353586597164563s**; true third S16 displacement **0.43023153716250867m**.
- Third S16 after: (5.5, **+0.4107744225702202**); **actual WORLD XZ target error 0.11938274192414239m**, improvement 0.7332722592244699m from second S16 after.
- **Scalar second+third movement sum=1.2452100826098884m**. Old scalar-vs-1.0m error 0.2452100826098884m would suggest worsening from old second-only 0.18502145m, but that comparator is **not the 2.0m fixed WORLD goal** and excludes inter-Action drift. Real XZ error improved as above. No absolute navigation objective inferred.

### WAIT World — fixed 1.0m WORLD-XZ relative goal

session `84aa792e-5da3-4de8-b21e-5ef17176be9b`.
- First S16 after: (−4.5, **+13.53015716449436**); fixed goal (−4.5, **+14.53015716449436**), before second S15.
- Second S16 after: (−4.5, **+14.677502163345748**); **0.14734499885138774m PAST the fixed target** (signed forward remaining negative).
- Original L0 re-evaluated its fourth native event seq **84**, chose `WAIT` with criterion `s49-locked-native-xz-stop-dev` after same-session fresh XZ probe. Actual physical Action count **2**, third Action **not issued**. No retroactive cancellation or synthetic WAIT. Note this is a DEV relative-distance STOP despite a zombie near 2m, not a general proof of safe combat behavior.

### Evidence and limits

Raw source artifact `s49-l0-native-xz-two-worlds-40659516287-1`, ID **12803047830**, ZIP SHA256 **e78be6f87d8e8135a6321c0d5e78432cecb411522d9f19e9398fb27dc64de6e5**. Both worlds source-consistent and distinct; `S49_L0_NATIVE_XZ_TWO_REAL_WORLDS_DEV_PASS`; no new packet readers/issuers, no force, no P1 recovery evidence, no standalone destination or arbitrary turn/obstacle generalization. In this experiment, X remains constant and WORLD's target-aligned forward is Z; negative controls cover reversed, lateral, stale, unbound and untrusted observations, but physical rotated-heading and obstacle tests have NOT been run.

Crucial result: input-off motion is real World behavior, not a reason to force Node/Paper tick synchronization. The feedback loop must compare actual location relative to a precommitted target using a fresh observation before a new Action.

**DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**. No change to main, #545/#634, production S49 default or paper certifications.
