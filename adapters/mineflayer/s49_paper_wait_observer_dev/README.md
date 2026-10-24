# RelaySelf S49 Paper WAIT observer — isolated DEV source producer

**Status: JAVA_21_COMPILE_VERIFIED_DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
The isolated Java 21 / Paper API 1.21.8 plugin was built and its packaged
class, plugin.yml and default-disabled config.yml inspected in a compile-only
GitHub Actions runner. It has **not** been loaded, run, or tested in a real World.

This is an independent Paper plugin, not a patch to the protected
`RelayMetabolismPlugin`, `normal_action.py`, or S49 `qualify()` runner.

### Claimed S16 closure → Paper callback correlation

The plug-in is disabled by default. Only a primary-thread server console
operator can call `/relays49observe <action_id> <session_id> <player_uuid>`
after the operator has separately observed a closed S49
`NormalActionClosedReadback`. The action and session strings are **not**
independently authenticated by Paper; this command is a claim, **not a
handshake**. The player UUID and configured expected name merely select the
observed local Minecraft player, not the S49 session/owner identity.

A single command is consumed once per plugin lifetime. With a valid online,
living player, Paper logs an `S49_OBSERVER_SUBJECT` context row, an
`S49_DEV_BACK_WAIT_BEGIN` row, and then at most eight
`S49_DEV_BACK_WAIT_TICK` rows (indexes 1–8) from **sync Paper callbacks**.
Each row includes the asserted `marker_id=action_id-session_id`,
`action_id`, `session_id`, World UUID and `World.getFullTime()` value.
Any tick gap, disconnect, World switch, plugin shutdown or callback error
aborts the candidate with `S49_DEV_BACK_WAIT_ABORT`. No restart, partial
seal, automatic retry, command dispatch or World mutation is allowed.
Other mobs/entities are not a reason to reject the Self's physical rest.

The existing Python `s49_paper_backward_wait_dev.py` offline reviewer can
parse the BEGIN + eight-TICK rows. Context and provenance still require an
independent review. It does **not** prove native command release takes effect
before the first tick, full-tick inactivity, no other issuers, or R original
custody; neither record is a P1 recovery witness.

### Java 21 compile result (not real Paper execution)

The isolated build at [GitHub Actions #40100070963](https://github.com/rinsakamo/relay-self/actions/runs/40100070963)
completed successfully for commit `efc6d70ca8fbcb578a15bab0901b58ef88329a7a`.
The packaged DEV JAR measured 6,501 bytes with SHA-256
`987ecc19d3ea999a6186c807d4ca5a51897a3b7ef5446cb736261d3354ed64ea`
for that specific build. The compiled JAR is available as a short-retention
GitHub Actions artifact. Do not treat the artifact ZIP SHA as the JAR SHA.

The workflow compiles only this standalone observer using Java 21, audits the
JAR entries, ensures protected S49/P1 source blob identities, and does not
launch Paper, Minecraft, Mineflayer or any physical World. Installation,
console command execution, native S49 Action integration, or independent R
source qualification is **not approved or evidenced by this build**.

### Paper observer run identity and strict transcript DEV

Every explicit console observation now mints a fresh Paper-local UUIDv4
`run_id`, included in SUBJECT, BEGIN, all eight TICK callbacks, and COMPLETE.
COMPLETE also binds the claimed player UUID, World UUID and last Paper tick.
The DEV-only offline `review_s49_paper_transcript_dev` requires one ordered
SUBJECT → BEGIN → 8 TICK → COMPLETE transcript, rejecting ABORT, restart,
mixed-run samples, mismatched session/action/world/player, and forged
authority fields. The older nine-line parser still accepts legacy test
fixtures **only** as non-admitting source-shape candidates.

The `run_id` is not cryptographic attestation and the Paper log text is not
independently custodied. In particular, a server-side effective motor release
before BEGIN, comprehensive intra-tick Self inactivity, and the absence of
other Action issuers remain **NOT_ATTESTED**. No P1 WAIT source is minted.

The optional `project_s49_backward_paper_dev(...,
observer_transcript=..., expected_player_uuid=...)` joins this strict
one-run transcript review to the original S49 owner WAIT-shape projection.
The extracted BEGIN+8 callback slice must have the same normalized SHA-256;
a mismatch rejects and saves a non-admitting failure report once. Both digests
are **derived from caller-provided input** and remain untrusted for R custody.
The join never calls P1 `reconcile()` or constructs `SourceBoundTick(WAIT)`.

### Remaining qualification gate (not performed)

To turn a shape-only transcript into a physically source-bound WAIT,
an independent, preserved server-side custody chain must establish **in
order**: the sole S49 Action terminal OUTCOME and motor clear; the time at
which the server could no longer apply its motor effect; an interval of
complete Self inactivity on relevant World ticks; and an issuer boundary
covering other possible Action paths. The current Java observer does
**not** supply this causal/coverage chain, even after a same-run match.
Do not reinterpret eight consecutive Paper callbacks, stationary positions,
or other entities' movement as that proof. Keep P1 admission fields null/zero
until the owner/R qualification gate explicitly succeeds.

### Paper-reported server input boundary (2026-10-25, offline DEV only)

Paper API 1.21.8 provides `Player.getCurrentInput()` and
`PlayerInputEvent`. The isolated observer now checks all seven input flags
(forward/back/left/right/jump/sprint/sneak) on console arm and on each
callback. It passively registers a MONITOR-only input listener and a
PlayerMoveEvent listener for the selected Self. Input reactivation,
positional movement events, or changed Self coordinates at the callback
fail-close the **candidate**, while unrelated entities' movement does not.

It adds exactly one `S49_OBSERVER_SERVER_INPUT` row between SUBJECT and
BEGIN, with `input_idle=true`, `tick=<Paper world time>`, and
`s49_release_causality=NOT_ATTESTED`. BEGIN and all eight TICK rows must
also include `input_idle=true` for the strict full-transcript reviewer.
The source remains the default-disabled, one-shot, console-only, read-only
Paper observer. No gameplay action, native command or energy change.

**Evidence boundary:** Paper reports an idle *server-side input snapshot*
and absence of monitored input/move events within this one observer
lifetime; neither guarantees packet history or that the Mineflayer
`clear_controls` ACK caused the state transition. Movement packets and
client input flags are not interchangeable, and callbacks are not
continuous whole-tick coverage. Therefore `server_effective_control_release`
and `whole_tick_self_inactivity` remain `NOT_ATTESTED`. No
`SourceBoundTick(WAIT)`, P1 recovery or qualification is admitted.
The independent R source custody and an S49→Paper causal handshake
are still required before any live qualification gate.

In particular, `getCurrentInput()` reporting all-false at BEGIN
does not prove a preceding true→false transition: it can also be the
preexisting/default server input. The R gate must independently bind
a server-observed transition and the S49 original cleanup chronology;
the DEV parser must never infer such a transition from a UUID or
console action claim.

### Pre-action BACK edge (optional DEV path; not run in a World)

The existing `/relays49observe` *post-Action* read-only command remains
unchanged and is still available for its earlier source-shape checks. An
additional one-shot, console-only `/relays49preobserve <action_id>
<session_id> <player_uuid>` command is now intended **before** the sole S49
Executor issues MOVE_BACKWARD. This is an alternate observer mode, **not**
another issuer or an authorizer. Config `enabled: false` stays the default;
neither Java nor Python invokes the command automatically.

The pre-action mode requires server input idle at arm, then exclusively
BACK input true via a Paper PlayerInputEvent, followed at a *later World
tick* by all input flags false via a second event. It records
`S49_OBSERVER_PRE_ARM`, `S49_OBSERVER_BACK_TRUE`, and
`S49_OBSERVER_BACK_FALSE` with the same Paper-owned per-run UUIDv4,
claimed action/session, and server World UUID. After the BACK-off event it
begins the existing `SERVER_INPUT → BEGIN → 8 TICK → COMPLETE` idle
screen. Pre-arm watchdog timeout is 240 Paper ticks. A missing event,
foreign input, clock reset, Self world/session switch, new activity during
the idle window, or no complete 8 ticks aborts the candidate. Self movement
*during the actual backward Action* is expected and not a pre-arm veto;
movement after the observed release invalidates the idle window. No action
or physical input is changed by this plugin.

The independent `review_s49_preaction_paper_dev` rejects missing,
duplicated, reordered, cross-run, noncanonical, or forged claimed-edge
records and checks the existing S49 typed S16 closure/8-tick transcript
structure. All provided Java log lines are still *caller supplied* unless
independently custodied. Even a valid Paper-observed BACK true→false edge
cannot prove it was caused by the particular S49 native clear ACK. It
also does not establish all World-tick inactivity, coverage of all
other issuers, or any physical WAIT admission. P1 remains at zero
recovery and original protected files remain unchanged.

No real Minecraft/Paper server, physical Action, QUALIFICATION or SCIENCE
is run by the isolated Java compile / Python 3.12 FAST gates.

The existing S49 owner-local offline projection optionally enforces this
new gate via `project_s49_backward_paper_dev(...,
require_preaction_edge=True, observer_transcript=...,
expected_player_uuid=...)`. It requires the full pre-action transcript
review and byte-derived normalized callback digest agreement before
arming the owner WAIT fence. Even successful offline shape correlation
does **not** attest that the original S49 native clear caused the
server-observed edge or permit physical fatigue recovery.

### Two-buffer custody readiness contract (2026-10-25 DEV, offline)

The optional `S49PaperArchiveInputsDev` stores *separate caller-supplied*
byte buffers and SHA-256 declarations for (1) a canonical JSON encoding
of the **decoded typed S16** original Action evidence already captured by
the sole S49 executor, and (2) a complete UTF-8 Paper pre-action observer
transcript. The `review_s49_paper_archive_dev` validates the exact two
byte hashes, source mode, upper length bounds, canonical native typed
frame serialization and strict S16 frame order, Paper input and pre-arm
BACK true→false chronology, and source identity consistency. It refuses
corrupt, replayed, foreign, missing or forged-claim inputs. When explicitly
supplied, `project_s49_backward_paper_dev(..., require_preaction_edge=True,
custody_archive=...)` includes the non-admitting two-buffer review in the
original owner-local derived report, preserving the legacy behavior when
the optional archive is not supplied.

**Do not treat this as external source attestation**: the two reader names
are unauthenticated labels and the hashes could have been generated by the
same caller. The "native" bytes are a canonical *decoded representation*,
not the original Mineflayer protocol wire or an independently witnessed
receipt. No cross-host clock or host→Paper packet causality is proven by
this format. In particular, native S49 Action ordinal `at_ns` values
must never be compared to a Paper World tick as shared time. The contract
never creates P1 `SourceBoundTick(WAIT)` or admits fatigue recovery.

A future independent R qualification gate still needs original native
wire custody, Paper-side raw server record custody, independently
established issuer/process identity and epoch, server-effective control
release attribution to the original S49 Action, complete Self inactivity
per admitted World tick, and an issuer-complete no-Action boundary.
Never infer these from an input digest or a claimed reader label.

### Existing W3 / existing Paper collector producer-file replay (DEV)

The isolated read-only `review_s49_existing_w3_paper_files_dev`
accepts two **already produced** local original sources: a previously
sealed W3 Node-bridge-stdout capture directory, and a previously pinned
`W4CollectorCursor` for the existing Paper server-console-collector file.
It never launches a process, observes real World, reads the Java stdout
pipe, or sends an Action.

W3's `audit_w3_sealed_stdout` checks the complete original JSONL stream,
session, EOF and shutdown receipt. The DEV join re-decodes that same
saved JSONL through the existing protocol decoder and checks the four
exact original S16 typed frames (before, dispatch, clear, after) and their
sequence numbers. These are **Node→Python stdout bytes**, not Minecraft
TCP packet bytes or commands sent over stdin. The existing W4 collector
cursor records the file's inode/device/EOF offset before the candidate
activity. A separate read-only tail checks only bytes *after that offset*
on the same unchanged regular file; replacement, truncation, symlink
aliases, hardlinks, size overrun, incomplete trailing lines and altered
source windows are rejected. Log bytes must match the previously
reviewed full pre-action Paper transcript.

The optional `project_s49_backward_paper_dev(...,
w3_original_root=..., paper_collector_cursor=...,
custody_archive=..., require_preaction_edge=True)` writes a derived
`producer_file_review` into the original S49 owner-local report before
arming its WAIT fence. It requires all four arguments and never bypasses
the existing S16/owner checks.

**Limits:** Both producers remain locally owned, so their saved file
contents do not prove the independent origin, signature, OS process
identity, issuer epoch, or authenticity of either host. W3 receipt hash
and Paper inode are only local integrity/position evidence. These two
records do not carry an authenticated shared clock or proof that the
S49 clear ACK caused Paper BACK off. Full World-tick inactivity is still
unknown. Output status is
`LOCAL_PRODUCER_FILE_CONTENT_BOUND_ONLY`, always
`QUALIFICATION_NO_GO`, `SCIENCE_NOT_RUN`, zero physical WAIT and
zero P1 recovery.

Actual independent original native wire custody, independent Paper
source authentication and causal source binding require a distinct R
qualification gate and external trust anchor, not this DEV replayer.
