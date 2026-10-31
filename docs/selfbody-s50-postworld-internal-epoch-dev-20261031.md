# SelfBody #632 — post-shutdown INTERNAL cognitive epoch reads one previous S50 experience

2026-10-31. **DEV / optional host path**, based on preserved actual physical
`DEV_WORLD_SELFBODY_S16_S50_JOIN_PASS` source
`0ee72bc7fdabf26be905ba51779ecb1a1b1f1a99`.

This is selected strategy **A** from [SelfBody #648](https://github.com/rinsakamo/relay-self/pull/648).
It is NOT the alternative strategy B (next live same-session native/L0 epoch).
The original complete S50 Node JSONL sidecar is sealed on Node shutdown, so a
same-session original `live_probe` cannot legitimately occur after it.

## What the internal epoch actually is

New read-only `PostWorldInternalEpochLease` is constructed with a previously
in-process typed `SelfBodyS50MotionCompanion`. It requires original
same-Action typed S16 OUTCOME/native Present and the bounded S50 sampled
motion; it never deserializes a report to mint either source.

After the **existing owner host** has observed both Node and Java exit0,
`enter_after_owner_shutdown(node_exit=0, java_exit=0)` consumes the one slot:

- It invokes existing `compose_self_body_view` and `compose_self_world_view`
  with **new internal epoch ID**, SAME Self/session and **NO observation**
  and **NO outcome**. Current Body/World native state is UNKNOWN, *not*
  physically still, disconnected, Goal reached or current source data.
- A separate `PostWorldInternalEpochReadout` retains previous typed
  companion and calls `read_previous_experience()` **during the new internal
  epoch**, producing only original source SHA/Action/previous-native-ref and
  S50 sampled motion ticks. The old S50 displacement is never copied to
  `SelfBodyView.observed()` or `SelfWorldView.observation`.
- The previous typed pointer is dropped from the lease upon use, and the
  lease is one-shot/ephemeral. Missing/failed exits, duplicate, wrong typed
  source or exception revoke/fail closed. No S49 Action/Node/Paper query,
  L0 decision, P1 recovery, M energy change, L10/S10/S11 learning, LLM or
  filesystem memory is performed.

**Important:** shutdown status is a *host-owned local process* observation
supplied at this callsite, not independent PID/port or World source
attestation. The original host's separate shutdown/cleanup and original
S50 source audits remain the actual DEV evidence.

## Integration into existing single-Action DEV host

The existing `adapters.mineflayer.self_body_s50_world_dev` has a new default
OFF `--selfbody-postworld-internal-epoch-dev` flag. When enabled, its
preexisting finalization does this in the same process:

1. The original S49 one Action and typed S15/S16/after Native
   `SelfBodyS50ClosedOwnerLease` work exactly as before.
2. Original Node and Paper Java shut down. The original S7/S16/L23/S50
   independent original-source audit and original typed
   `lease.consume_s50_once(...)` must PASS.
3. **Only if** Node/Java return codes both0, cleanup has no reported
   errors and the original S50 typed companion has been joined: construct
   `PostWorldInternalEpochLease(joined)`, call
   `enter_after_owner_shutdown()` **once** and save the bounded
   returned summary under `selfbody_postworld_internal_epoch` in the
   existing report.
4. The report's preexisting `selfbody_s50_join` records
   `next_cognitive_epoch_referenced=true` with
   `POST_SHUTDOWN_INTERNAL_EPOCH_PRIOR_EXPERIENCE_ONLY`. This flag says
   *internal retrospect only*: **not** new L0/native epoch, independent
   memory retention or successful adaptive cognition.
5. The new lease closes regardless of failure; original S49 lease and
   World temp cleanup remain in their existing `finally` block.
   Default OFF produces original report and qualification behavior.

The original [real World3](https://github.com/rinsakamo/relay-self/blob/0ee72bc7fdabf26be905ba51779ecb1a1b1f1a99/docs/selfbody-s16-s50-world-results-20261031.md)
has been run before this flag existed, thus its `next_cognitive_epoch_referenced`
remains **false**. That original DEV World is not reclassified.

## LocalCodex DEV physical next step

In an isolated new worktree, pin this source branch's exact HEAD and owner
assets/hash from prior World; run original one-Action S49/L23 host with the
**extra** `--selfbody-postworld-internal-epoch-dev` CLI flag and the
same validated Paper plugin/M0.2 config and sealed Node S50 diagnostic.
Fresh disposable World **one attempt** initially. Do NOT run an extra
Action/native probe or a second post-run client. Record the new output's
`selfbody_postworld_internal_epoch.classification =
DEV_POSTWORLD_INTERNAL_EPOCH_PRIOR_EXPERIENCE_READ_PASS`
only if original live Action, all physical source validation, complete
shutdown and the separate new internal read all pass. The classification
is DEV only and explicitly NOT fresh native/L0 cognition.

Preserve previous World3 and failure originals. Do not claim
EFFECTIVE_CLIENT_CLEAR_TICK, full-tick input coverage, physical stability,
Goal, P1 WAIT, L10, R/SCIENCE, nor any model or learning benefit.

## Current confidence

The Python3.12 focused test builds *synthetic original-typed*
S16/native/S50 companion, creates the no-Present post-shutdown internal
epoch and dereferences previous motion; asserts one-shot, zero new native
Present, independent current UNKNOWN state and fail-closed exit/source
negatives. It also tests existing owner body/world API shapes. **This is
offline only**; actual new World host opt-in still needs LocalCodex run.

`DEV_ONLY / POSTWORLD_INTERNAL_EPOCH_INTERFACE_OFFLINE /
NEW_REAL_WORLD_NOT_RUN / FRESH_NATIVE_PRESENT_0 /
NEW_L0_ACTION_0 / P1_WAIT_0 / L10_PAIRS_0 /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
