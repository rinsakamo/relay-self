# RelaySelf — W4-WIN: World placement-window content contract (DEV only)

Authority: SelfWorld #633, Draft #634, original S49 #537, Physical Control
#627, prior immutable W4-NH1 preregistration
`SELFWORLD-W4-NH1-DEV-PROSPECTIVE-20261019-v0`.

**Status: offline shape implemented; NO live console coordination; no native
World run; no trust upgrade.**

## Precisely what was missing

Original S49's independent `stage_world` asyncio task issues server-console
`kill` / `summon` commands through `_command(server,...)`,
`await server.stdin.drain()`, then sleeps. `drain` only observes producer
pipe backpressure. Sleeping is not proof the server executed the command, and
a Mineflayer `seq` cannot establish the server command's effective World tick.
The Node stdout stream is not a witnessed Minecraft TCP transcript. Claiming
native-source placement based only on these timestamps would be unsound.

## Instrumentation protocol for a *future* separately gated DEV experiment

A **single existing World experimenter** and the **one existing native
observation reader** must coordinate using explicit barriers. Never create a
second Mineflayer reader, add a second S49 Action issuer, or let the World
experimenter move or rotate the avatar.

1. At each prespecified near slot, the existing native reader obtains the
   original `probe(request_id)` with same-snapshot player
   `position/yaw/pitch`, source `session:seq`, and records a unique
   before-position/source.
2. The experimenter fixes the preregistered 2m horizontal forward position
   from that source. Generate a fresh per-run/slot restricted token
   (24–48 lower-case ASCII hex-like characters), pre-registered before
   sending the command. Attach a unique tag to *that* zombie's summon NBT;
   keep the original entity type, position, NoAI/Silent/Persistence/Invulnerable
   flags unchanged. Tagging is an instrumentation amendment, not a new
   favorable geometry, intervention, endpoint or Stage S threshold.
3. The existing server-console writer records **raw command bytes**, their
   SHA256 and monotonic write/drain boundaries (plus the same Java process
   identity). Never treat `drain` alone as World execution evidence.
4. Issue the subsequent conditional console command
   `execute if entity @e[type=minecraft:zombie,tag=...,limit=1] run say ...`
   with a unique `W4NH1_READY_..._S{slot}` marker. This emits a marker
   *only if* a tagged entity exists server-side. The existing server stdout
   collector (not a new console reader) records its raw log line,
   process identity, time and order. A missing/duplicate/wrong-source marker
   ends the attempt with explicit UNKNOWN/BLOCKED.
5. Only after the marker appears does the original native reader issue a
   **new correlated** `probe(request_id)` and check a fresh zombie
   `entity_id` unique within a non-truncated entity registry at the
   preregistered XYZ. The post-probe must be newer and from the same
   session as the prior orientation sample. It is the same probe that the
   original S49 decision may later use; do not create a second stream.
6. Retain a strict ordered evidence chain: native before → summon bytes
   write/drain → conditional confirm bytes write/drain → server log marker →
   native post. Relate the same original native post-probe to original S49
   closure, S16 original Action evidence and frozen Stage S same-target 3D
   distance comparison. The original non-HOLD threshold stays exactly 10cm
   with minimum movement 5cm.
7. Keep both near slots, failures, unknowns and non-issued Actions. Do not
   resample/choose a successful slot or convert a near WAIT into an Action.
   Existing no-retry and one-owner/one-reader rules apply.

**Authority limits.** A valid server log string can be spoofed by the same
producer; raw log lines and caller-supplied order/time are *not* an external
attestation. The conditional marker establishes a stronger **content-based
existence witness** than `drain`, but by itself does **not** prove an
independently witnessed World tick, absence of malicious actor interference,
uniqueness of all entities outside a truncated registry, native emitter
completeness or authenticated producer/custody. A future coordinator must
document the exclusivity of the native reader, log collector identity,
causal ordering across event loops, replay resistance of the token, and
independent archivist handoff before granting any qualification.

The implemented **pure read-only** contract is in
`adapters/mineflayer/self_world_stage_w4_window.py`:

- `build_w4_window_commands`: deterministic world-only tagged summon and
  conditional console marker commands; content SHA256 (including newline)
- `reconcile_w4_window_offline`: fail-closed checks over same-session
  native before/after, monotonic single coordinator order, same server PID,
  command bytes, raw marker text, and unique new zombie ID/XYZ
- `join_w4_window_and_s16_offline`: requires the same original S49 probe,
  existing S16 typed Action closure and unchanged Stage S readback

All receipts keep `physical_run_permitted=false`,
`command_dispatch_attested=false`, `s10_permission=false` and
`science_qualified=false`. Their label is
`DEV_PRODUCER_CONTENT_CORRELATED_ONLY` /
`UNATTESTED_PREWORLD_BLOCKED`. The raw log and source dates are not
accepted as remotely authenticated just because they match.

## Gates not removed by this change

- No live S49 opt-in runner/physical argv/server-console marker collector
  wiring is implemented in this increment. The original S49 staging,
  `_command`, S49 owner, original native reader and Action executor remain
  byte-identical.
- External archivist identity, independent pre-acquisition original custody,
  pinned trust anchor, signer private-key isolation/process authorization,
  and globally monotonic single-use grant authority remain
  `W4_EXTERNAL_TRUST_NO_GO`.
- Existing W3 HOLD×2 under the fixed 10cm threshold remains frozen.
  W4-NH1 has 0 physical World trials / 0 new Actions / 0 S16 outcomes /
  0 S10 grants or commits. No R/V science promotion.
- Before executing any actual new W4-NH1 trial, the W4/W4-WIN implementation,
  independent trust contracts, exact SHA, source-bound placement-capture
  coordination, new disposable one-shot grant/root and final reviewed argv
  must be locked and admitted separately. Do not infer authorization from
  passing these offline tests.
