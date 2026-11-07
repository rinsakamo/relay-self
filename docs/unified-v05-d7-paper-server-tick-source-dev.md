# D7-B — Paper server-owned per-tick STOP source (read-only)

> **DEV implementation; NOT a STOP certificate and NOT an EAT grant.**
> Parent [D7-A #781](https://github.com/rinsakamo/relay-self/pull/781), Bug-0 [#742](https://github.com/rinsakamo/relay-self/issues/742), original S owner [#537](https://github.com/rinsakamo/relay-self/issues/537), first natural-zero→new S49 kill→loot pickup World [#780](https://github.com/rinsakamo/relay-self/pull/780). No change to S49's sole physical issuer or WorldBody physics.

## Exact missing evidence

S15's native `clear_controls applied` and S16 MOVE OUTCOME are not Paper server-effective release or a continuous STOP. The D7-A S50 direct client `getControlState` snapshots of seven inputs similarly observe CLIENT state and CLIENT physicsTick, not Paper's own clock.

D7-B augments the existing **read-only** `zombie_drop_witness_dev` Paper plugin with an opt-in (default false) `D7PaperServerTicks` observer:

- Once per **Paper main-thread scheduled tick**, log actual `Bukkit.getCurrentTick()`, exact player UUID/World UUID, all seven `player.getCurrentInput()` **last-received server inputs**, live Paper position x/y/z, velocity vx/vy/vz, and onGround. Log actual `PlayerInputEvent` input updates as separate events. Read-only only.
- Record a bounded lifetime: READY; at most 8192 server tick rows and 512 update events; TRUNCATED on cap; STOP with original counts. No commands, packets, position corrections, new player/bot, extra S49 Action or World rule changes.
- Only opt in when the D7 original same-World S50 sidecar is enabled under `D7_PASSIVE_CONTROLS_WORLD_ONLY=1`; the standard D4/D5/D6 witness plugin remains disabled for this observer by default.
- Separate `tools/bug0_d7_paper_server_tick_post.py` independently joins prior **genuine D6** physical/Intent audit and original S50 source; requires exact Paper World and stable player UUID, sequential server tick labels and ordinals, no truncation, finite positions/velocity, complete boolean controls, count-matched READY/STOP and no EAT issuance. It reports observed input active/off counts and a **diagnostic only** longest near-stationary streak, *not* a STOP decision.

## Why this does not automatically unlock EAT

`Player.getCurrentInput()` is the last input **received** by Paper; it does not identify when the original S49 `clear_controls` receipt was applied at the server. A quiet streak might occur *before* the original Action or after unaccounted control writes. D7-B has **no attested causal matching** of the S15 clear action ID/nonce to Paper's input release tick, and it never establishes a per-action, authenticated owner EAT resume grant. Even a 100% all-off tick sequence leaves:

- `server_effective_original_S49_clear_tick=NOT_CAUSALLY_ATTESTED`
- `body_physically_stopped_proven=false`
- `authenticated_S_owner_EAT_resume_grant=false`
- `original_EAT_issued=false`

**No external code may treat these read-only booleans as authorization.** The existing `_post_move_settling_unqualified=True` stays active. A Paper client input event need not occur for every `clear_controls` (historical S50 reports had none), so absent events must not be fabricated.

## Next smallest S-owner implementation

1. Inspect an independent D7-B one-use World artifact with both client S50 and Paper tick streams. Determine whether Paper ever reports a server-observed input-on→off transition around the genuine original MOVE.
2. If insufficient, add the smallest **original S-owner authorized action-to-server source correlation** (not a new Action issuer): e.g. authenticated exact original action/clear marker plus server-side timestamp/ack under established S49 physical process, with no duplicate input channel. Confirm tick-level original Paper position/velocity + seven controls remain gap-free **after** that proven effective release.
3. Couple only an owner-held, single-use, session/Intent/native source/revision/deadline-bound terminal STOP decision with a fresh food/inventory/health/threat observation and existing original EAT PROPOSE/ISSUE and S51 equip+consume physical fence. UNKNOWN, lack of causal tick join, stale World or post-clear input reactivation fail closed.
4. One fresh, disposable DEV real World proves original **ATTACK→natural drop→S49 MOVE→Paper PICKUP→server STOP→original S49/S51 EAT**, with food/inventory actual changes, physical journaling, independent audit, then next Intent. Two full food cycles and longitudinal training are later independent gates.

## Audit invariants and no claims

No synthetic examples are elevated to actual S49 permission. Strict negative tests cover missing/foreign Paper UUID, tick gaps, duplicated ordinals/events, malformed/nonfinite body/controls, tampered owner/source verdict, false EAT claim and capped trace. Reuse existing C1 MOVE and original S49 ATTACK/EAT durable fences; do not call cross-file persistence exactly-once.

**Classification:** `DEV_ONLY / D7_B_SERVER_PAPER_TICK_SOURCE_READ_ONLY / PHYSICAL_STOP_NOT_YET_CERTIFIED / EAT_NOT_ISSUED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
