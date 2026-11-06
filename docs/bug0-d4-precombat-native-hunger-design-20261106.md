# D4 native precombat Hunger DEV gate after original Paper natural pickup evidence

Exact prior real Worlds stay **FAIL** and immutable.
- [Original #42203574500](https://github.com/rinsakamo/relay-self/actions/runs/42203574500): first D4 native melee target ambiguity, original Action0.
- [Original #42205130594](https://github.com/rinsakamo/relay-self/actions/runs/42205130594): original S49 ATTACK2, native real rotten_flesh 0→1, Paper actual ItemSpawn+Pickup; L0 correctly deferred EAT while zombie remained visible; not a full D4 success. Separate SHA read-only audit [#42212798078](https://github.com/rinsakamo/relay-self/actions/runs/42212798078) SUCCESS.
- [Original #42207097822](https://github.com/rinsakamo/relay-self/actions/runs/42207097822): original S49 ATTACK2 and actual Paper natural rotten_flesh **2** + ItemPickup+native count2; vanished zombie reobservation worked, but native Food only fell **20→14** and L0 correctly remained NOT_HUNGRY (threshold 14 exclusive) until bounded observation ended. Separate SHA read-only audit [#42212860194](https://github.com/rinsakamo/relay-self/actions/runs/42212860194) SUCCESS. No original EAT in either World.

This child **does not change S49 food thresholds, native fatigue laws, true WorldBody private physics, original S51 or Paper 600tick respawn**.

DEV operator uses the already-present vanilla **Hunger** effect, but allows 70 seconds instead of 25 seconds, **before** the melee strikes. The original native observation is read-only; precombat waits until Food is actually below the original S46 `EatCursor.threshold=14` with health >15 and nontruncated native source. No food is added, no player is fed by operator, no S49 Action or grant is issued while waiting; L0 must independently decide ATTACK while zombie exists and EAT after true death, pickup and safe native observations. Fails before combat if Food never qualifies. The effect is cleared before EAT as in the existing D4 path.

One original S49 issuer, distinct ATTACK/EAT authorizations, genuine managed zombie Paper killer, unchanged natural rotten_flesh random drops 0..2, actual Paper Item Entity/pickup UUID, authentic native inventory+food changes, 600 server tick new zombie, cleanup and immutable SHA artifacts remain required. Real 0 drop => no meal claim; >0 scatter out of native pickup range => FAIL without staging meat.

**This design file is NOT a physical World trigger.** Separate exact offline CI must PASS on this source HEAD before creating a **docs-only** commit `run-bug0-d4-precombat-native-hunger-oneworld-once-20261106` at path `docs/bug0-d4-precombat-native-hunger-trigger-20261106.md`. One new World once, no automatic rerun if it fails.

Scope: DEV_ONLY / new World not yet run / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN; no Self MOVE to meat or autonomous long-term survival.
