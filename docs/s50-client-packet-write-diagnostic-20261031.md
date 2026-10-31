# RelaySelf S50 DEV — Mineflayer client.write × Paper InputEvent diagnostic

Status 2026-10-31: **OFFLINE IMPLEMENTATION ONLY / NEW CLIENT-PACKET REAL WORLD 0**.
Tracks S owner [#627](https://github.com/rinsakamo/relay-self/issues/627),
stacked [Draft #642](https://github.com/rinsakamo/relay-self/pull/642).

## Physical observation that motivates this

Earlier new Paper World (S50 source HEAD
`62e02ec003e95c76f3060f356fa4eff15bd0f5b8`, final evidence
HEAD `3bb79ed57c4a0940bdc586c72976c7ece079319f`) established:

- S49 original Action 1; S15 clear seq28 applied; S16 OUTCOME seq29.
- S16 after-motion 6 native move callbacks and 0.2404601368784256m.
- Paper `WAIT_TICK 252..259` and `INPUT_TICK 252..259`, eight each.
- All seven server last-reported input flags false in eight samples.
- Position changes with false input: fullTime252 0.051683904m,
  fullTime253 0.009966235m, fullTime254 0.005441564m; 255..259
  sampled zero.
- Paper `S50_DEV_INPUT_EVENT` zero: last input-update World tick unknown.

All-false input + residual motion **does not prove effective S15 clear or
complete idle**. `PlayerInputEvent=0` may mean no corresponding
serverbound `player_input` update, unchanged input, an event produced
before PRE_FORWARD's marker gate, or a trace/coverage discrepancy.
The prior real World is evidence of Paper sampled input, **not of packet
transmission**.

Official Minecraft Java 1.21.8 PrismarineJS protocol table defines a
serverbound `packet_player_input` (client API name `player_input`)
distinct from the regular `position`, `position_look`, `look`
and `flying` movement packets. Never infer that a Mineflayer
`setControlState` call automatically emits `player_input`.

## New local source (existing bridge only)

`adapters/mineflayer/s50_client_packet_witness_dev.mjs` follows the
existing T1w *passive* client write-return observation technique.
The existing `bridge.mjs` loads this only when
`RELAYSELF_S50_PACKET_WITNESS_DEV` is set to an absolute new JSONL
path and the configured protocol version is `1.21.8`.
**Default OFF.**

When ON:

- Observe existing `physicsTick` samples and seven locally applied
  Mineflayer control flags.
- Wrap the original `bot._client.write` exactly once; call the
  original with the same `this`, arguments and return/exception
  semantics. Log only *returned* writes from `player_input`,
  `position`, `position_look`, `look`, `flying` and
  `entity_action`.
- Record original set_control/clear_controls effects *after* applying
  them, with local-only Node ns, physics event index and sampled flags.
- Use a separate bounded, asynchronous, fresh `wx` sidecar with a
  completion/loss footer. No extra packet, alternate action issuer,
  STOP, clear, packet payload modifications or per-tick sync trace.

**Critical bounds:** a returned client `write()` is not proven wire
delivery or Paper acceptance. This instruments **one native write path**,
not all lower-level TCP/Netty frames or every source of movement.
The source is not a cross-clock causal anchor. No P1 WAIT/Goal/L10
promotion may result from this diagnostic.

Read-only `s50_client_packet_source.py` compares the sealed client
sidecar with an independently sealed Paper console original and
classifies:

- `NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH`:
  zero native `player_input` writes on the instrumented path
  (position writes may still occur).
- `PLAYER_INPUT_WRITE_SEEN_PAPER_CALLBACK_ABSENT`:
  client write returned but Paper event 0; **not** proof of wire
  delivery or server reception.
- `BOTH_WRITE_AND_CALLBACK_SEEN_IDENTITY_UNPROVEN`:
  each source contains an event, but there is no packet-level
  identity/cross-clock proof they describe the same event.

It rejects incomplete/lost sidecars, foreign sessions/markers/worlds,
duplicate/out-of-order client rows, unrecognized packets, false claims
of wire acceptance or fewer than eight input snapshots.
Node `source_coverage` remains
`ONE_EXISTING_CLIENT_WRITE_CALL_PATH_ONLY`.

## Integration boundary for the next LocalCodex World

The L23 working code at immutable
`d51b34b859cb18c4965681422163f9a1cfad3a8d`
has a different `bridge.mjs` blob from the S owner branch.
**Do not blindly replace the entire L23 bridge with the S branch
bridge**: it may change unrelated command behavior.

Use a fresh disposable integration worktree to stage **only** the
new S50 observer module plus the minimal opt-in import / attach /
post-original-effect receipts / shutdown footer hooks from the S-owned
bridge. Pin this test code's exact commit. Ensure all existing L23
S49/S16/clear/receipt semantics remain byte-equivalent except the
opt-in diagnostic wiring. Do not alter immutable L23 source/evidence or
merge to main.

LocalCodex procedure:

1. Verify HEAD, owner status, and previous S50 real DEV source; run
   Node22 `node --test
   adapters/mineflayer/s50_client_packet_witness_dev.test.mjs`,
   Python3.12 `pytest tests/test_s50_client_packet_source.py`,
   syntax/Ruff and S49/L23 focused contract tests.
2. Prepare a fresh immutable-hash-pinned new Paper1.21.8 build60 World,
   freshly built S plugin, full M0.2 active config with
   `s50-input-witness-dev: true` and
   `s50-tick-meter-dev: true`. Keep S49 the sole Action issuer.
3. Set `RELAYSELF_S50_PACKET_WITNESS_DEV` to a new absolute
   per-run sidecar JSONL path **before** spawning the existing
   Mineflayer bridge; do not use `NODE_OPTIONS` or an additional
   Mineflayer client. Ensure the path is not under the automatically
   deleted World directory.
4. One disposable World, retain all failures. After normal Node/Java
   shutdown audit sidecar footer/row count/Node events; compare
   source session ID with sealed S7/S16 and Paper World marker.
   Independently replay L23 and S50 input observer and inspect actual
   `client_player_input_write_returns`, native movement write count,
   local applied control transitions, Paper INPUT_EVENT count and
   eight Paper input snapshots.
5. SHA256-pin source code, JAR/config, original native JSONL, Paper
   stdout, sidecar, and readbacks. Verify Node0/Java0, World deletion,
   PID disappearance/port rebind, then commit/push only necessary
   DEV artifacts and report to #627 and Draft #642.

This diagnostic may show that Mineflayer never writes `player_input`
during normal WALK even while writing movement packets. In that case
keep the factual source label rather than inventing a new packet
sender. Do not inject `player_input` simply to obtain a server event
in this stage.

DEV_ONLY / EFFECTIVE_CLIENT_CLEAR_TICK_NOT_ATTESTED /
FULL_TICK_INPUT_COVERAGE_NOT_ATTESTED / STABILITY_UNPROVEN /
GOAL_UNDETERMINED / P1_WAIT_0 / L10_0 / QUALIFICATION_NO_GO /
SCIENCE_NOT_RUN.
