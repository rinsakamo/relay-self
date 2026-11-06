# Bug-0 D2 natural zombie loot: one disposable Paper World trigger (2026-11-06)

Exclusive one-shot trigger commit message: `run-bug0-d2-natural-drop-once-20261106`.
This commit changes **only this document**.

Exact preworld source HEAD `4a6860ced9d4a2174b3e0c519e86554aeb55d5f5`
passed [offline CI #42188794933](https://github.com/rinsakamo/relay-self/actions/runs/42188794933),
which includes real D2 runner lint/compileall, original repo contract, independent
negative source audit tests, Paper 1.21.8 zombie natural-loot witness compilation
and fixed 600 server tick World-owned respawn gate compilation.

One new disposable pinned Paper World/session only, no automatic retries.
Enabled independent World-side plugins: original R1 fixed 600-tick zombie
respawn plus read-only natural drop witness. Original D1 pickup and
respawn evidence SHA sources immutable.

Grant **one operator-side zombie teleport to player and one console kill**,
strictly not the Self S49 ATTACK or MOVE. Require genuine zombie
EntityDeathEvent (with unaltered random vanilla rotten_flesh drop) →
genuine ItemSpawnEvent and new item UUID → genuine player
EntityPickupItemEvent → correlated native Mineflayer inventory gain →
600 server tick new zombie and new native entity ID. If rotten_flesh count
is zero, stop and retain **NO_LOOT**, do not force extra drops, repeat,
or relabel operator activity as autonomous.

Source only: no S49 issued actions, EAT, L0/L1/L2 decision, Energy debit
or learning. Private Paper truth stays operator-only. After one World,
stop and independently verify raw log, JSON, SHA256 artifact and cleanup.
No claim of unlimited survival or formal qualification.

`DEV_ONLY / D2_WORLD_ONCE / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
