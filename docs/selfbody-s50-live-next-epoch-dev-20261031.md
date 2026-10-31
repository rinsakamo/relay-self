# SelfBody #632 / S50 #627 — route B: in-session Paper window + next original S49 L0 epoch

2026-10-31. **DEV OFFLINE / SOURCE_ONLY**, stacked on the successful route A
real-World source exact HEAD
`7aac3e73828895a646671ce2874c701e7f1e9594`.

## Source boundary: strict two-phase, no forged TRACE_END

In original route A, S50's entire Node sidecar gets a truthful `TRACE_END`
footer **only after the Mineflayer client has exited**. The original
`inspect_s50_client_packets` / `project_s50_body_motion_source` must
continue to reject incomplete Node traces and cannot be modified to
pretend that an in-session prefix is complete.

Instead, `adapters/mineflayer/m02_paper_dev/s50_live_paper_window.py`
offers a **different and explicitly weaker evidence class**:

1. While Paper Java World is running, after original S49 S16 and
   eight S50 `S50_DEV_WAIT_TICK` + eight `S50_DEV_INPUT_TICK`
   callbacks have actually arrived, capture a bounded,
   **newline-terminated byte prefix** of original Paper log. The
   `capture_s50_live_paper_window` validates the pre-forward/post-clear
   phase/order/bracket, native owner marker/session/World/subject,
   all eight contiguous callback positions and current-last-reported
   input flags with original S50 + L23 validators. It stores the
   **byte length and SHA256 of this exact prefix**, and the frozen
   eight sampled tick deltas. The source is
   `IN_SESSION_PAPER_CALLBACK_WINDOW_ONLY`. It does not contain
   Node packet history and `node_trace_complete=false`.
2. A new `LiveNextEpochLease(prior_body, live_window)` accepts the
   **original already-qualified typed S16/native SelfBodyView** of
   the previous S49 Action and the tentative Paper window. It
   consumes **one already-received original S49 `live_probe`**
   after that Action, with a strictly later event ID/native seq and
   the same session. Only *the new native probe* makes the current
   SelfBody/SelfWorld Present; past Paper delta stays a separate
   history diagnostic. It calls `read_previous_motion()` inside that
   new pre-L0 observer callback, and labels the source
   `PROVISIONAL_PAPER_ONLY`. L0's existing decision and Action
   selection are untouched. Wrong session, duplicate/replay, stale
   seq/event and foreign source fail closed.
3. After Java shutdown, compare the **exact original prefix hash**
   and size with the sealed final Paper log using
   `verify_s50_live_window_against_final_paper`. A positive prefix
   check verifies only Paper byte identity; run the original
   **complete S50 Node TRACE_END / independent L23/S16/World audits
   separately**. This is a later audit, NOT a retrospective claim
   that Node was fully authenticated at the time L0 consumed the
   provisional Paper-only signal.

These interfaces do not start Java, Node, a probe or an Action. They
do not increase native tick coverage, reconstruct S16 from JSON,
write model/memory or grant Goal, M/P1, L8, L10, S10, S11.

## What is not connected yet (important)

The original successful single-Action S49/L23 DEV host intentionally
has **two** L0 events: `WAIT -> MOVE_AWAY`, one S49 Action, and the
original post-S16 Paper + L22 observation windows. It does **not**
currently produce a next L0 event *after* that Action. Therefore
having the live Paper source and the `live_probe` consumer API in code
does **not** mean a real route B L0 epoch occurred.

A LocalCodex separate DEV integration must, WITHOUT a second Action
issuer, configure one **additional original** S49 native decision
event *after* the S50 eight-tick Paper callback window has closed.
A third safe/no-threat original event yielding **WAIT** is a possible
DEV design, but it requires independently demonstrating that it is
an actual original native S49 L0 epoch (not a manually requested
diagnostic probe), and that it does not change the original Stage-R,
S16/Goal, S49 owner or create a second Action.

A safe candidate test order in one **fresh disposable World**:

- Preserve the already validated one S49 Action, S15 clear and typed
  S16/after-probe before any live S50 window capture.
- Wait for all eight real Paper WAIT/INPUT callbacks with matching
  World/marker/session while Paper stays alive. Read a complete
  newline-terminated prefix (not a partial UTF-8 log line) and
  construct a tentative `S50LivePaperWindow` once; do not claim
  `TRACE_END` / complete Node source.
- In the existing S49 host's next independent native L0 decision
  (a **third** event with one prior Action, if admitted by its
  normal owner), pass that already-read `MineflayerObservation`
  through `LiveNextEpochLease.observe_original_l0_probe` as passive
  `live_probe`, then take exactly one source-linked readout.
  Do not call any new `send_observe` only to fill this witness.
- Let original Node and Java exit, seal normal S50 sidecar with
  `TRACE_END`, verify final Paper source prefix, and separately run
  the full original S50 producer's final Node/Paper readback. Reject
  a World mismatch, missing footer or unstable source even when
  the in-session Paper-only readout was observed.
- Preserve all FAIL originals, exact code/paper/config hashes, exit
  status, cleanup and native source sequence. Reruns are fresh
  Worlds only, not a second Action in one World.

Do not claim `LIVE_NEXT_L0_NATIVE_EPOCH_REFERENCED_PASS` unless the
live session actually delivered the post-Action L0 probe and the
original full final S50 source independently passed. A pure
post-shutdown retrospective (route A) is not route B.

## Archived real-World byte-prefix replay

The offline CI also replays the **actual** successful route A World
`docs/evidence/selfbody-postworld-epoch-20261031/run1/server.log`
and its bound `s49-report.json` from the preserved source HEAD.
It cuts the original byte prefix only after the actual eighth
`S50_DEV_INPUT_TICK` line. This prefix has Paper tick **253–260**
and sampled reported-input-OFF movement **253–255**. It validates
the original marker/session/World/subject and exact final-log
byte-prefix identity. This is physical **source replay**, not an
actual live Python `live_probe` at the time and not a real route B
World trial. Node complete trace authority is unchanged.

## Current evidence

Focused offline tests use synthetic original typed S16/native
sources and S50 Paper fixture: 8-tick bound, input flag correlation,
prefix hash, final original byte readback; malformed, missing,
foreign, duplicate, nonfinite, stale source rejection; current
SelfBody/SelfWorld native source and historical Paper separation.
They establish the software *source contract*, not actual World B.

Current source class:
`DEV_ONLY / B_PROVISIONAL_PAPER_WINDOW_OFFLINE /
REAL_NEXT_L0_EPOCH_NOT_OBSERVED / NODE_TRACE_IN_SESSION_NOT_COMPLETE /
NO_NEW_WORLD / NO_ACTION_POLICY_CHANGE / P1_WAIT_0 / L10_0 /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
