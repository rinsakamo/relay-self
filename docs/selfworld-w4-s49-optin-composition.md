# W4 Phase-A — one-session, read-only original-owner opt-in composition

**Scope:** Existing SelfWorld #633 / Draft PR #634, original S49/S16/S18
contracts. **No original `qualify()` or `_new_session()` wiring.**
`W4_S49_ORIGINAL_OWNER_LIVE_LEASE_UNDETERMINED` and
`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` remain mandatory.

## What is linked in one synthetic session

The new `adapters/mineflayer/self_world_stage_w4_optin_offline.py`
`reconcile_w4_s49_optin_offline()` is *only a read-only auditor*. It cannot
launch a process, accept a server writer, create a grant, send a Minecraft
command, or mutate the retained S10 owner. It joins the following **already
created** producer-local evidence:

1. `W4DevLeasedSession` inherits the original decoder/stream, and
   `MineflayerProcessSession.launch()` / original `_await_spawn()`
   consume `adapter_started` and spawn from **one fake stdout**.
2. `W4PrehostOwnerBridge` consumes the exact source-bound native orientation
   probe with a once-only preworld ledger. Unsolicited preworld observations
   remain evidence, not later L0 stimuli.
3. The original `_ready_server()` Java collector and `_command()` are
   executed with patched **in-memory fake stdout/stdin**. The guarded logfile
   cursor sees two planned commands and a conditional tagged marker.
   It reads the collector file, never Java stdout itself.
4. Lease transfers `WORLD_WINDOW → HOST` after the marker. The original
   `NativeObservationOnly` and `NormalWorldL0.run_session()` interpret a
   new W4-target entity update, obtain an original correlated probe and
   issue a source-bound L0 candidate.
5. Only a separately supplied *synthetic independent grant* allows the
   **original** `NormalSessionActionExecutor.execute()` with its existing
   supervisor, typed admissions and S16 before/effect/clear/after collector.
   No grant or missing ISSUE is rejected before Action transport writes.
6. The original S16 closure observation tap, W4 seven-step placement-window
   readback, native lease decoded/delivered trace and target identity are
   compared on **the same local session**. The fake S16 closure is not an
   actual World OUTCOME. The session must quiesce and close under its own
   owner. These are independent software pathways but share untrusted local
   fake inputs.

The join requires:
- exact `W4DevLeasedSession` type, idle complete lease in HOST phase,
  marked collector and already transferred **identical** preworld ledger;
- strict one-session native DELIVER order, no DENY/ABORT or duplicate seq,
  no preworld event delivered as host stimulus, no receiver during WORLD_WINDOW;
- source-bound preworld frame, later native W4 target at planned XYZ, canonical
  command hashes/order/marker, L0 target and request correspondence;
- if L0 requested an Action, its exact original S16 closure/target/session
  must exist. If no Action was requested, no closure can be attached.

Receipt: `W4_S49_OPTIN_COMPOSITION_OFFLINE_V0`,
`SYNTHETIC_DEV_ONLY`, `live_owner_attested=false`,
`external_custody_qualified=false`, `physical_run_permitted=false`,
`s10_permission=false`, `science_qualified=false`.
The result checks **local producer self-consistency, not genuine external
Minecraft source custody, clocks or causation**.

## Failure and freeze policy

The same combined integration checks missing independent L0 or S16 ISSUE
authorization and selected readback witness tampering. Existing lease
50+ negative controls, 3.11/3.12 task delegation, W4 marker/window and
S18 freeze regression remain included in the original CI selection.
Full/physical workflow SKIPPED is not a pass. Failed/timeout/cancelled
CI must not be promoted to a qualification.

No S49, S34, S31A, process_session, normal_action, execution, S16/S17/S10,
S18 freeze or prior evidence file is modified. The fake test can never
be offered as new physical MOVE/S16/S10 evidence, and in particular cannot
turn W3's `+0.09595129995869334m` ×2 HOLD into 0.100m success.

**Completion ceiling:** a passing full-path offline test may qualify
`W4_S49_OPTIN_COMPOSITION_OFFLINE_PASS` ONLY. The genuine original
`qualify()` single-reader lease and source-bound real World staging still
need independent protection review and external custody/signer/global spend
qualification. Do not launch physical Java/Node or accept old grants.
