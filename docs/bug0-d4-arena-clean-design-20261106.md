# D4 arena source guard — exact first failure and child correction

The previous one-World source [#42203574500](https://github.com/rinsakamo/relay-self/actions/runs/42203574500)
ended **FAIL** (not a combat failure claim): genuine original Paper
R1 managed zombie at tick15, one valid native zombie ID82, but
native candidate_count **5** before operator melee staging. Original
S49 requires complete exactly-one entity coverage for ATTACK, so its
first pre-ATTACK probe refused as `one complete original native melee
zombie is required`. **Physical ATTACK0, killer/death0, meat0,
PICKUP0, EAT0, respawn not reached**. Java/Node exit0, cleanup true.
Original artifact [#13495572297](https://github.com/rinsakamo/relay-self/actions/runs/42203574500/artifacts/13495572297)
zip SHA256 `933952622182b1004f0574cd747a418518e8dce0daee61f8fc7c05b32be99d63`,
immutable independent SHA/original Paper/JSON readback
[#42204188878](https://github.com/rinsakamo/relay-self/actions/runs/42204188878) SUCCESS.

This child changes ONLY operator controlled DEV fixture preparation, not
S49 attack/food authorization: after gamerules and before the managed
zombie's melee placement, run exactly `kill
@e[type=!minecraft:player,type=!minecraft:zombie]`. Java Edition
selector excludes both actual players and **all zombies**, including the
original World-managed zombie and any upcoming 600tick successor. No
item is staged. Every observed other entity is removed from the DEV
arena, then the original S49 must still observe one complete fresh
native source and independently issue real ATTACK or fail closed.

Existing NoAI/Health1.6 target staging, 0.65m passive natural pickup,
operator induced Hunger-only stimulus, native food choice/sole S49
issuer/S51 consumption/600tick genuine new zombie requirements are
unchanged. Strict D4 post audit rejects a generic /kill capable of
deleting original zombies. No MOVE-to-loot or autonomous self-care claim.

The old real World is NOT retried and never relabelled PASS. Once
exact new preflight succeeds, a distinct disposable World may be
authorized with a different docs-only one-time trigger. No automatic
retry or total survival claim.

`DEV_ONLY / NEW_CHILD_WORLD_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
