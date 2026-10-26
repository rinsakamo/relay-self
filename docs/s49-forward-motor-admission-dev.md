# S49 forward motor admission — isolated DEV (2026-10-26)

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Scope

A separately gated variant of the **existing original S49 single Action issuer**
may now bind an S14 `MOVE_AWAY` choice to the explicit physical action
`MOVE_FORWARD`, which S15 transports using the Mineflayer `forward` control.
The default path continues to require `MOVE_BACKWARD` / `back`.
The binding is selected **before** issuance; it is never swapped after
`ISSUED`. The original S16 consequence checks binding, dispatch, cleanup,
and observation lineage for the actual bound action.

A forward transport command is **not** equivalent to a validated escape
direction: current original S49 L0 targets zombie **distance** rather than
proving the player's facing and the World-relative escape vector.
No automatic claim of avoiding the zombie is permitted here.

- New operator gate: `S49_FORWARD_MOTOR_DEV_ONLY=1` **and**
  `qualify(..., dev_forward_motor=True)` (CLI `--dev-forward-motor`).
- Incompatible with Stage R and original additional 4th/5th/6th epochs.
- No extra reader, issuer, World writer, physical teleport, or release bypass.
- **Not yet** a DASH motor: this variant does not issue Mineflayer sprint
  input, does not prove Paper's positive forward input, and does not produce
  speed, M0, or P1 settlement evidence.
- The Paper +50% modifier remains opt-in and is not armed by this patch.
- For DEV real-world testing, observe and compare source-bound tick speed,
  on/off windows, sprint controls, directional caps and safe cleanup first.

Do not merge to main / PR #545 / PR #634, update R qualification, or
reinterpret the previously recorded backward negative control.

S16 `self_action_evidence` now retains the historical strict default
`MOVE_BACKWARD`; forward evidence must pass an explicit DEV-only flag at
capture and subsequent verification. Previous consumers are unchanged.

## DEV forward+sprint under one issued Action

A distinct S14 `MOVE_FORWARD_SPRINT_DEV` binding produces the one-ACK
`set_forward_sprint_dev` effect with exact `forward=true,sprint=true`.
Both S49 DEV flags and `S49_SPRINT_MOTOR_DEV_ONLY=1` are required.
Bridge rejects missing opt-in and invalid pair. S16 still requires its
same-Action clear ACK. The historical decoded S16 reader needs separate
explicit forward+sprint opt-ins; defaults remain backward-only.

This permits a motor smoke test, **not** Paper-positive DASH, velocity
calibration, lateral cap proof, M0 posting, or P1 native settlement.
\n## Paper Input flag discrepancy / forward-vector DEV fallback\n\nFirst disposable Paper trial [40284347094](https://github.com/rinsakamo/relay-self/actions/runs/40284347094): original S49 forward+sprint 2/2 OUTCOME, ~0.815m per Action, but 0/5 Paper boost ticks. Diagnostic rerun [40284653105](https://github.com/rinsakamo/relay-self/actions/runs/40284653105): all Paper input flags false despite `player_sprinting=true`, and physically measured +Z motion (up to ~5.11 nominal m/s). The DEV Paper plugin therefore permits a separately labelled **MOTION_PROJECTION** speed modifier only when sprinting, the Paper input bitset is entirely empty, and actual XZ displacement strongly aligns with player yaw. Contradictory lateral/backwards movement is denied. This is NOT evidence that the client sent a forward Input packet, nor a qualified directional hard cap. Test actual motion and release with a new disposable World.\n
\n## 0.60-second targeted DEV sprint contrast\n\nThe original bounded S49 issued-action path now uses 0.60 seconds only for\n`MOVE_FORWARD_SPRINT_DEV`; all historical `MOVE_BACKWARD` / `MOVE_FORWARD`\ncontinue at 0.20s. A single fresh Paper trial compares two originally issued\nforward+sprint action distances: the first action is modifier-armed, the second\nis not. That distance contrast is **uncontrolled DEV evidence**, not a\nmatched-speed causal experiment, an authenticated Paper-to-client clock link,\nor established 8.42m/s.\n
## Measured 0.60-second real World outcome — 2026-10-26

Focused Python 3.12/Ruff/Node checks: [PASS run 40285529924](https://github.com/rinsakamo/relay-self/actions/runs/40285529924). Real disposable Paper 1.21.8 trial: [PASS for modifier/cleanup, run 40285529938](https://github.com/rinsakamo/relay-self/actions/runs/40285529938) on exact source `c09a8e98b860fff5ecb6c2235b8af92b292af707`.

S49 original issued Action and S16 OUTCOME 2/2; 13 Paper callback ticks,
11 modifier-on, all 11 categorized `MOTION_PROJECTION` rather than observed
forward packet Input. Node/Java exited 0, modifier removed.

**Physical-speed contrast did not improve:** first (modifier-armed)
`3.0301571644943626`m versus second (unarmed)
`3.030157164494363`m — delta effectively 0. Maximum Paper sampled
horizontal speed was approximately `5.6084`m/s (nominal 20TPS
calculation), not the design target `8.415`m/s. This is a same-run DEV
comparison, not a controlled scientific attribution; the null contrast
is an explicit reason **not** to assert native DASH speed gain.
The Paper attribute applied flag proves only modifier presence.

Next owner-bound work is to reconcile the Paper movement-speed attribute
with the pinned Mineflayer 4.39.0/prismarine-physics 1.11.1 motor model
without teleportation or a second issuer. Do not connect native M0/P1
settlement or claim physical directional caps before observing actual
World-effective velocity and authoritative tick correspondence.

## Root-cause evidence and source-bound physical speed fix (2026-10-26)

Pinned Minecraft 1.21.8 attribute `entity_update_attributes` frames decoded the
**player movement speed** as the misleading `generic.scale` key: base ~0.1,
`minecraft:sprinting` operation-2 +0.3, and the genuine Paper modifier
`relays49dashdev:forward_dash_only` operation-2 +0.5. The vendor physics
`prismarine-physics 1.11.1` instead looks for
`minecraft:movement_speed` and silently falls back to 0.1 if that key is
absent. This explains why the server registered its transient speed attribute
while Mineflayer remained near RUN speed.

DEV bridge `s49_speed_attribute_bridge_dev.mjs` permits the narrowly
identified packet source to be mapped **only** during the original issued
forward+sprint S49 Action when `S49_SPEED_ATTR_SYNC_DEV_ONLY=1` and
`S49_SPRINT_MOTOR_DEV_ONLY=1` and Minecraft=1.21.8. It rejects unknown
source base, modifier names, operations, duplicate or exaggerated bonuses.
It strips the raw `minecraft:sprinting` modifier because prismarine-physics
already applies its own local +0.3 sprint modifier. It does not
invent a client speed, bypass Paper source, send a new command, or
inject another Action issuer. The mapped attribute is removed on original
clear-controls and process shutdown. All default launch behavior is unchanged.
The exact mis-labelled packet bridge is **not** a broadly qualified
Minecraft compatibility fix.

[Real disposable Minecraft PASS — run 40293458189](https://github.com/rinsakamo/relay-self/actions/runs/40293458189)
at exact source HEAD `c5f9f805e99e0d1dad435a4ab3ab1eda74bb2176`:
- original S49 bound `MOVE_FORWARD_SPRINT_DEV` native 2/2 OUTCOME,
  Java/Node exit 0;
- first 0.60s first Action with Paper modifier: 4.264897828m;
  second 0.60s Action without Paper modifier: 3.030157205m;
  difference **1.234740623m**;
- Paper 11/13 ticks modifier present and removed, measured
  peak sampled 20TPS XZ speed **8.407958462m/s** vs 8.415 target;
- data-derived DEV evidence is a same-run **uncontrolled** ON/OFF contrast.
  Client input forward bits were empty; 11 boosted Paper ticks used
  labelled `MOTION_PROJECTION`, which does not qualify side/back hard caps.
- M0 ledger and native P1 expenditure each 0. R/SCI runs 0.

Subsequent focused CI adds fail-closed gates that require BOTH
real displacement gain (>=0.40m same-run) and Paper 20TPS peak
(>=7.5m/s), so merely observing the modifier cannot produce a green
speed-gain result.
