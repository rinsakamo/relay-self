# S50 × L23 native player_input source — LocalCodex Paper DEV handoff

Latest local execution: [実World結果](s50-l23-client-packet-real-results-20261031.md)
— two fresh Worlds, initial initialization FAIL then repaired DEV PASS.
The remaining handoff below records the pre-execution plan.

2026-10-31. S-owned packet witness is implemented and offline tested;
**new packet-witness real World has not been run in this integration**.

## Immutable sources and owner boundaries

- S-owned physical plugin and server-input observer: `dev/s50-paper-input-witness-20261031`, original physical evidence HEAD `3bb79ed57c4a0940bdc586c72976c7ece079319f` / measured code HEAD `62e02ec003e95c76f3060f356fa4eff15bd0f5b8`. The later S owner branch `33275fc5221fd18bbdc47b167fc0a83fe7cf8ad4` adds the **passive client packet** observer, without running a new World. Source owner remains [S #627 / Draft #642](https://github.com/rinsakamo/relay-self/pull/642).
- L23 real-world proven base: `d51b34b859cb18c4965681422163f9a1cfad3a8d`, [Draft #641](https://github.com/rinsakamo/relay-self/pull/641), **unchanged**. Its 8 consecutive Paper ticks and residual movement were observed using the older client bridge without the packet witness.
- Isolated L23 + S50 source-only integration branch:
  `dev/s50-l23-client-packet-integrated-20261031`, [Draft #643](https://github.com/rinsakamo/relay-self/pull/643), base L23. It overlays **only** the opt-in Node witness onto the otherwise original L23 bridge. Owner authority is unchanged, and this is not a main integration proposal.
- Exact-head offline check: [GitHub Actions #41186830273](https://github.com/rinsakamo/relay-self/actions/runs/41186830273): Node22 **5 PASS**, Python3.12 **72 PASS**, Ruff/compileall/repository contracts PASS. **No new World**.

## Why the trace exists

A prior new S50 Paper World had S15 clear seq28, S16 after seq29,
native post-S16 movement 0.240460137m, World tick 252–259 with
`S50_DEV_INPUT_TICK` (all seven server-last-reported flags OFF),
`S50_DEV_INPUT_EVENT=0`, but actual sampled pose movement 252–254.
This **does not** prove an effective S15 clear tick or full-tick idle.

The original Mineflayer client can send `position`, `position_look`,
`look`, `flying` without necessarily sending a serverbound
`player_input`. The new observer records returned calls to the
**same native** `bot._client.write`, local controls and original
effect returns. It must never issue a new `player_input` or alter
S49 Action/clear semantics. Its local Node ns is not synchronized to
Paper World fullTime. Even a logged write-return cannot prove wire
delivery or server acceptance.

## Prepare one local WSL DEV session

Use two **fresh isolated worktrees** or another equally isolated source
checkout. Keep any pre-existing user processes and World data intact.
Verify exact remote HEAD, git status, Java21, Node22, Python3.12,
Mineflayer4.39.0, Paper1.21.8 build60.

The authorized LocalCodex host can run one disposable DEV World using the
**existing S49/L23 runner** from the integration branch:

`python -m adapters.mineflayer.s49_normal_session_real_ci`

The S-owned 1.21.8 Paper plugin must be built from the S-owner physical
plugin source, not the L23 original JAR. Do not overwrite the S owner
branch or assume the historical plugin digest still matches.
Paper server JAR build60 known SHA256:
`8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`.
Independently hash all actual bytes used: server, newly built plugin,
*full* active M0.2 config.

Prepare the active config by copying the S-owner **entire native profile**
(16 action rules), enabling only in an operator-owned disposable copy:
`dev-enabled: true`, `s50-tick-meter-dev: true`,
`s50-input-witness-dev: true`. This Paper plugin actively changes
exhaustion; describe it as **metabolic intervention**.

Create an absolute, **new** evidence root, including an existing empty
`capture` directory **before** starting a World. All outputs and the
packet sidecar must live **outside** S49's internally deleted temporary
World directory. Check port25565 is unoccupied; do not kill other
services. Use the same `NODE_OPTIONS`-free process environment as the
predecessor run.

Example command shape (substitute actual preverified absolute file
paths and measured SHA256; do not use literal placeholders at runtime):

```bash
export S49_REAL_SERVER_CI=1
export PYTHONPATH=src:tests:.
export RELAYSELF_S50_PACKET_WITNESS_DEV="$EVIDENCE/client-packet-original.jsonl"
python -m adapters.mineflayer.s49_normal_session_real_ci \
  --report "$EVIDENCE/s49-report.json" \
  --server-log "$EVIDENCE/server.log" \
  --l16-capture-root "$EVIDENCE/capture" \
  --l16-goal-target-x 0 --l16-goal-target-z 0 \
  --l16-goal-tolerance-m 0.49 --l16-goal-stability-m 0.05 \
  --l16-confirm L16-S49-FIRST-ACTION-ORIGINAL-DEV \
  --l22-settling-probes 6 \
  --l23-paper-server-jar "$PAPER_JAR" \
  --l23-paper-server-sha256 "$PAPER_SHA256" \
  --l23-paper-plugin-jar "$S_PLUGIN_JAR" \
  --l23-paper-plugin-sha256 "$S_PLUGIN_SHA256" \
  --l23-paper-config "$S_PLUGIN_CONFIG" \
  --l23-paper-config-sha256 "$S_PLUGIN_CONFIG_SHA256"
```

The experimental active config, server JAR and plugin JAR SHA pins must
come from the **actual** bytes. For a source-diagnostic comparison,
predeclare the Goal and all other conditions before running. This
program uses the existing S49 sole Action issuer and L23 8-tick
callback guard. It does not grant a new action or STOP owner.

## Independent post-exit readback

Only after normal completion and sealing of sources, run from the
integration checkout:

```bash
PYTHONPATH=src:tests:. python tools/s50_l23_packet_world_readback.py \
  --report "$EVIDENCE/s49-report.json" \
  --paper-original "$EVIDENCE/server.log" \
  --client-sidecar "$EVIDENCE/client-packet-original.jsonl" \
  --capture-root "$EVIDENCE/capture" \
  --output "$EVIDENCE/s50-packet-readback.json"
```

This reader refuses a non-PASS S49/L23 original, extra Action,
incomplete node/Java cleanup, mismatched L23 Paper SHA, foreign native
session/marker/World, missing original S7/S16, missing/incomplete client
trace footer, unknown packet kind, false network-acceptance claim, and
not-exactly-eight Paper input snapshots. It outputs a SHA256 index and
classifies one of:

- `NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH`
- `PLAYER_INPUT_WRITE_SEEN_PAPER_CALLBACK_ABSENT`
- `BOTH_WRITE_AND_CALLBACK_SEEN_IDENTITY_UNPROVEN`

Interpret these as **whole observed client session** write-return
diagnostics. The Paper plugin has its own marker-bound observation
window. Total client write count and marker-window Paper event count
are not necessarily coextensive; never present them as same-packet
matches or exact client↔World tick alignment.

Check the sidecar's original `NATIVE_CONTROL_EFFECT_RETURNED` samples
and `PACKET_WRITE_RETURNED` indexes in actual order; keep `set_control`,
`clear_controls`, `shutdown_clear_controls` distinct. A
`player_input` write may occur before marker start; that is not
evidence Paper missed a packet. If no `player_input` write is
observed, distinguish it from the presence of position packet writes.
Even that observation is limited to the wrapped client write path.

Preserve every failed preworld attempt and any failed World original
under distinct new run IDs. Confirm normal Node/Java exit=0, owned
World/PIDs removed, and port rebind. Record the exact measured code
HEAD, all asset SHA and a manifest (not only an unverified report).
Avoid committing JARs or large World folders to Git; keep manageable
source originals and indexes separately.

## Acceptance ceiling

For this DEV step, success means original S49 Action/S16, L23 Paper
source, 8 Paper input ticks, complete client writer sidecar, separated
client packet vs Paper event diagnostics, and cleanup all pass.
This still **cannot** produce:

`EFFECTIVE_CLIENT_CLEAR_TICK_ATTESTED`,
`FULL_TICK_INPUT_IDLE`, `PHYSICAL_STABILITY_VERIFIED`,
`GOAL_ADMITTED`, `L10_PAIRS`, `P1_WAIT`, `QUALIFICATION` or `SCIENCE`.

Keep those explicitly `NOT_ATTESTED / UNDETERMINED / 0 / NO_GO`.
If original Node patch causes unexpected behavior, fail closed, preserve
sources, and fix only that patch before a new World; do not silently
switch to the S owner's different `bridge.mjs` or send new packets.

Report the measured result and SHA at
[S #627](https://github.com/rinsakamo/relay-self/issues/627),
[Draft #642](https://github.com/rinsakamo/relay-self/pull/642),
and [Draft #643](https://github.com/rinsakamo/relay-self/pull/643).
