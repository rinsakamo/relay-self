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
   (24–48 lower-case ASCII alphanumeric characters), pre-registered before
   sending the command. The caller must also pass an explicit immutable
   `seen_tokens` ledger to the offline command/window validator. Reusing a
   token in either slot is rejected, including when slot labels differ;
   missing ledger input fails closed. This local caller-held set is **not** a
   global monotonic cross-host single-use authority. Attach a unique tag to *that* zombie's summon NBT;
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

## W4-WIN-LOG: existing collector's log cursor (subsequent DEV implementation)

A new **non-executing** helper,
`adapters/mineflayer/self_world_stage_w4_logtap.py`, closes part of the
source acquisition interface without changing the original S49 or
`s31a_real_server_ci.py` code:

- `capture_w4_collector_cursor(log_path)` records the current byte offset
  and original device/inode for an existing, absolute, non-symlink,
  single-hardlink regular log file **before** prospective World commands.
- `wait_for_w4_collector_marker(cursor,commands)` polls exclusively the
  existing collector's **file**, never the Java stdout pipe. It examines
  only complete, newline-delimited UTF-8 lines **appended after that
  offset**. It rejects replaced/truncated log files, symlinks, excessive
  data, duplicate/incomplete markers, mismatched marker content, and
  bounded timeouts.
- `marker_as_w4_window_event` converts the content witness to the
  prior typed W4-WIN event vocabulary. Its `server_pid` is *caller
  supplied*, not independently authenticated by the file; timestamp is
  the local **read** monotonic timestamp, not a server execution tick.
- Synthetic concurrent log appends, partial writes, prior marker replay,
  marker spoofing, log path replacement/truncation and multiple target
  W4-WIN/source/S16 content checks are in
  `tests/test_self_world_stage_w4_logtap.py`.

This is explicitly **not yet hooked into a live S49 session**. The
original `_ready_server()` stdout collector remains the only owner of
the Java stdout pipe. Future wiring must additionally show *how* the
existing World experimenter and native reader coordinate the
preplacement cursor, conditional marker receipt and postplacement
probe on exactly one reader lease. Do not start a new native consumer
to implement the handoff or silently delay the original S49 stage-world
task.

A matching local log line is an improvement over treating
`stdin.drain()` as World completion, but it is **not** authoritative
World-command acknowledgment, server tick, authenticated Minecraft TCP
source or independent archivist evidence. Thus
`W4_EXTERNAL_TRUST_NO_GO / NH1 PREWORLD_BLOCKED` remain; 0 physical
World/Action/S16 OUTCOME/S10 changes and no science qualification.

## W4-HANDOFF (2026-10-19): isolated async owner sequencing

`self_world_stage_w4_handoff.py` now exercises the prescribed causal
handoff end to end, but **only with internal synthetic ports**. The caller
passes two already-built original-shaped native observation fixtures and
optionally an original-shaped closed S16 witness; the routine creates its
*own disposable temporary log file*, simulates the original experimenter's
command-write/drain evidence, appends a fake conditional console marker from
an asyncio task, uses the W4-WIN-LOG byte-offset reader, and only then
delivers the simulated post-probe into W4-WIN and the original S16/Stage S
reconciler. It never receives a Java process, session object, World writer
callback, physical server log path, or Action issuer. No second native reader,
server stdout consumer, or World command is launched.

Its result records 2 synthetic native probe deliveries, one conceptual
native-reader owner, 0 Java stdout consumers, 0 physical server commands,
and exact seven-event order. The marker timeout, duplicate/partial/foreign
marker, stale source, replay token, wrong slot, reversed post-probe and
foreign original S16 closure are negative controls. A local log cursor
now refuses a **pre-existing unterminated partial line** so a later appended
marker cannot inherit its forged prefix.

**This does not implement or attest a live handoff.** It does not qualify
World timing, producer authenticity, closed-loop single-reader leasing, OS
process/file provenance, independent archive custody, global single-use,
external S10 signing, near-WAIT safety or any physical trial. Its receipt is
`SYNTHETIC_OFFLINE_ONLY / UNATTESTED_PREWORLD_BLOCKED`; the original S49
runner and Stage S criterion remain unchanged. A future guarded live
adapter must establish actual S49-host/native lease and active server
collector ownership before attempting any new disposable DEV World.

## W4-OWNER: original-reader pre-world observation authority gap

The audited original S49
`s49_normal_session_real_ci.qualify()` runs `stage_world()` concurrently
with `host.run_session(...probe=reprobe,...)`. The existing `reprobe`
callback is invoked only **after an event has already entered the original
host loop** (in particular, after the staged zombie exists). It is not a
pre-world native source. A passive `live_probe` called from that callback
cannot supply the required orientation before its own World placement.
Recategorizing that post-event probe as PREWORLD would be fabrication.

To make the missing admission boundary explicit, the new **offline-only**
`W4OwnerHandoffGate` defines:
- `before_world` accepts the original owner token and a genuinely earlier,
  session/request/source-bound oriented probe identified as
  `s49_original_owner_pre_world` in synthetic test data; it does **not**
  acquire such a real reading itself.
- `observe_existing_collector_marker` requires exactly one marker from
  the already-sealed cursor/collector candidate, in the permitted phase.
- `after_world` requires a newer, separate request in the same session
  from that *same in-process owner token*; duplicate reference, reused
  token, wrong order, unsolicited owner substitution and post-as-pre
  are rejected. A failure latches `BLOCKED`.
- The owner token is merely an in-process testing capability; it is **not
  evidence of the real native session's single-reader lease**, a filesystem
  principal, or a source signature. Every successful receipt explicitly
  marks `owner_attested=false`, `trusted_world_tick=false`,
  `physical_run_permitted=false`, and `s10_permission=false`.

The implementation does not import or change the frozen S49 runtime.
**Real use still requires a reviewed, opt-in owner-mediated native probe
before staged World changes**, without adding any competing consumer to the
native stream. This issue remains PREWORLD_BLOCKED until implemented and
independently witnessed. Do not infer a live admission from synthetic
`origin` strings or a passing CI result.

## W4-PREPROBE: one-shot owner-mediated source acquisition interface

Prior W4-OWNER implemented only admission *after an observation already
exists*. The new `W4OwnerPreworldProbePort` supplies a DEV-only, abstract,
single-shot async acquisition interface for the existing original reader:
the caller injects one already owned `async native_probe(request_id)`
coroutine, and must call it before the S49 host event loop or World staging
starts. The port does not construct/launch Mineflayer, server processes,
Node, a second receive loop, World commands, Action issuer or S10 grants.

The port sets `PROBE_IN_FLIGHT` *before awaiting* the callback; it binds
the calling asyncio task, rejects reentrant or concurrent invocation,
foreign owner tokens, wrong session/request ID, stale/non-probe/raw
unoriented observations, and any caller-admitted started host/World stage.
Errors, task cancellation and failed receipt attempts latch `BLOCKED`
without retry. Successful `W4OwnerPreworldProbePort.capture_pre_world`
passes the typed original-shaped observation to the existing
`W4OwnerHandoffGate.before_world` and yields a candidate World-only
command with `physical_run_permitted=false`. It does **not** run that
command. Source provenance is local typed Node observation, not an
independent issuer or network attestation.

Important authority limitation: injected callbacks, in-process owner
objects and boolean `host_loop_started/stage_world_started` are
**caller statements**, not source-authenticated runtime proofs. The
original S49 `_new_session()` currently launches without W4 native
orientation opt-in, and the original `stage_world()` begins concurrently
with `host.run_session()`. Neither original routine is changed by this
increment. To truly connect W4-NH1 later, the original S49 owner must
explicitly acquire the pre-World oriented probe before it schedules
staging or starts the host receive loop, while guaranteeing all unsolicted
Node events and original admission frames remain accounted for. Tests
for the new port are synthetic and do not attest that these conditions
are satisfied in a physical Minecraft session. W4/NH1 remains NO_GO.

## W4-PREHOST — loss-accounted, original-session preprobe (2026-10-20)

The original `_correlated_observe()` in S31A receives from the native
session and **discards every unsolicited observation until the matching
probe**. Reusing it directly for W4 pre-staging could lose world events,
silently changing the evidence used by the original host. This is a
distinct causal problem from just avoiding a second reader.

New `W4PrehostOwnerBridge` accepts an already-owned session-like
`send_observe/receive` port and a single owner token. It issues one
correlated observe BEFORE the host/World startup, reads the same stream
serially, checks all session IDs and strictly increasing seq, and retains
all interleaved nonhostile entity events / entity-hurt messages as a
bounded **pre-World evidence ledger**. Hostile zombies, unexpected message
kinds, wrong/stale probes, task cancellation and frame overflow fail
closed. Pre-World frames are **not replayed later as new post-placement L0
stimuli**, which would change their causal meaning. The ledger must be
taken exactly once before the bridge considers the phase handed off.
The bridge calls the existing W4-PREPROBE and W4-OWNER contracts for its
candidate plan; it adds no Java, Node, second reader, Action, or S10
issuance path.

The code is a connector *interface*, not connected to the original S49
`qualify()` or to actual Mineflayer. The original S49 runner still uses
unmodified `_new_session()`, `stage_world()` and `host.run_session()`.
Its claimed single-reader status remains **unattested**, and no
physical-run grant can be derived from matching observations. A future
separate guarded DEV runner must bind this bridge to the original session
and review the handling of all unsolicited pre-host observations without
mutating the historical S49 result or borrowing spent grants.

**CI maintenance:** A preceding exact HEAD's FAST pytest job exceeded
its former 10-minute job limit at about 88% completed and was cancelled,
rather than reporting an assertion failure. The existing pytest selection
is unchanged and this workflow raises only its time budget to 20 minutes.
SKIPPED full/physical jobs remain SKIPPED, not PASS.
