# SelfBody #632 — original typed S49/S15/S16 closure to S50 motion companion

Status: 2026-10-31, DEV **offline source-path test**. No new Minecraft
World, original Action, native probe or GPU/model call in this PR.

Sources and ownership:

- S49 original `adapters/mineflayer/normal_action.py` has a pre-existing
  `observe_closed_native_actions` context manager. Its callback receives
  `NormalActionClosedReadback` *after* S49 ActionSupervisor S16 terminal
  transition, and contains exact in-process typed S15
  `WorldConsequence`, S16 `ActionOutcomeInterpretation`, original
  action terminal and native decision probe. This callback is already
  used by the S49 Stage-R owner and is **one context-local slot**;
  do not attempt to overlap with Stage-R or multiple action issuers.
- SelfBody original typed owner
  `adapters/mineflayer/self_body_projection.py` already has
  `project_body_action_readback(consequence, outcome)`. It requires
  original typed, executed, session/action/binding/provenance-matched
  S15/S16 and *ordered genuine native before/after probe*. This
  must **never** be reconstructed from the saved JSON report.
- SelfBody original `compose_self_body_view` binds existing native
  Present with the same typed original S16 OUTCOME.
- S50 producer [Draft #645](https://github.com/rinsakamo/relay-self/pull/645)
  supplies separately reviewed Paper World and client-local movement
  diagnostics, from the original input-OFF/motion World in
  [Draft #643](https://github.com/rinsakamo/relay-self/pull/643).
  A source-only archived replay **does not** make original typed
  WorldConsequence and original native Present accessible in process.
- Consumer [Draft #646](https://github.com/rinsakamo/relay-self/pull/646)
  joins the existing SelfBodyView with this separate, immutable S50
  diagnostic, without modifying BodyOrigin, physical truth, Action or policy.

## Implemented in this isolated branch

`adapters/mineflayer/self_body_s50_original_closure.py`:

`SelfBodyS50ClosedOwnerLease` is an opt-in single-Action, single-epoch
typed lease. Use the **existing** source callback with
`observe_original_s49_selfbody_closure(lease)` around an already
authorized original S49 Action executor invocation (never introduce
another executor). Inside the callback, the lease checks:

1. original terminal is current, real typed OUTCOME, with S16
   `observed_execution` and source status executed;
2. Action ID and exact session join S16/S15 and original decision probe,
   with before/after ordered native source;
3. original `project_body_action_readback` accepts **the same**
   typed S15/S16 instances, no decoded/forged JSON;
4. original `compose_self_body_view` returns a BodyObservation with
   the original exact Action/World consequence provenance.

One original terminal source is retained only for the requested
one-Action DEV lifetime; duplicate/foreign/UNKNOWN sources revoke
the lease. Caller independently seals the S49 and S50 DEV originals,
then calls `lease.consume_s50_once(source)` with S50 producer-reviewed
`physical_body_diagnostic` dict. On success the existing
`SelfBodyS50MotionCompanion` is returned; the lease is consumed.
On failure the lease is also revoked to prevent trial-and-error
source aliasing. The original Action owner never sees failure.

`lease.close()` must be called at the end of every run/epoch,
including exceptions; it drops the transient typed World source
pointer. The sole closure callback only observes original objects;
it cannot send packets, issue/clear any Action, launch a model,
write S10 or mint M/P1 energy/fatigue.

### Suggested local host installation — explicit DEV opt-in

The existing S49 original **L23 one-Action** runner is the suitable
physical owner for the next integration; the standalone original S49
`qualify` normally performs *two* original Actions and will revoke a
one-slot lease on a second terminal. Use the same single original
L23 Action and do not change its S49 action/clear/receipt code.

For an **authorized disposable DEV World** on LocalCodex:

1. Pin three separate immutable owner SHAs: S49/L23 code (latest
   qualified owner), S50 Paper plugin and readback source,
   and SelfBody #647 consumer. Do not overwrite protected past
   evidence or S/S49/Goal/L/M/P1 worktrees.
2. In a **fresh isolated integration worktree**, install the S50
   observer as a context around the already existing **single**
   `NormalSessionActionExecutor.execute` invocation. Only this
   context-local callback sees original `NormalActionClosedReadback`
   and may call `lease.observe_original_closed`; do not reconstruct
   original `ActionOutcomeInterpretation` from `report.json`.
   Do not overlap with Stage-R's own `observe_closed_native_actions`.
   The original L0, S49 authorization and S16 effect owner remain
   byte-equivalent.
3. Capture the single original Action, exact original S49 S16 and the
   new full SHA-pinned Paper/Node S50 sidecar in that same fresh World.
   Require normal exit/cleanup, 8 exact Paper input samples and L23
   readback; do not start another native probe to satisfy this lease.
4. After closing/sealing the original S50 records, call the original
   S50 producer validator on its genuine source and pass its
   `physical_body_diagnostic` dict to
   `lease.consume_s50_once(...)` in the **same Python process**
   before the typed lease expires. Check
   `joined.self_body.observation.source_ref`, original same-Action
   S16 provenance and `cognitive_summary()`.
   Always call `lease.close()` during final cleanup.
5. Save failure originals and exact host/asset/plugin/code hashes,
   negative cases and cleanup audit. If any owner source does not
   correlate, mark `SOURCE_NOT_ADMITTED`, not a PASS.

This is a proposed physical integration procedure, **not evidence
of its execution**. If L23 runner has already exited as a separate
process, the typed original S49 closure is gone and cannot be
legitimately recovered by re-parsing archived JSON into pretend
native Present.

## Offline verification boundary

The test
`tests/test_self_body_s50_original_closure.py` constructs synthetic
but legitimate **original owner typed** S49/S15/S16 classes,
native-probe-shaped snapshots and ActionLifecycle transitions.
It tests original existing SelfBody `project_body_action_readback`
and `compose_self_body_view` without rebuilding source from JSON,
then consumes a synthetic S50 source dict through the preexisting
consumer. It tests duplicate/foreign/out-of-order/missing/UNKNOWN,
one-use consumption and expiration. Existing SelfBody / passive
S49-World tests must remain unchanged.

**These tests do not run the actual original S49 executor with live
Minecraft IO**, even though they exercise its exact typed callback
shape. Only a later in-process real-World run can demonstrate
real host acquisition of the typed owner closure.

`DEV_ONLY / OFFLINE_TYPED_CLOSURE_SHAPE_PASS /
REAL_S49_TYPED_CLOSURE_WORLD_0 /
EFFECTIVE_CLEAR_TICK_NOT_ATTESTED /
PHYSICAL_STABILITY_UNPROVEN / GOAL_UNDETERMINED /
P1_WAIT_0 / L10_PAIRS_0 / QUALIFICATION_NO_GO /
SCIENCE_NOT_RUN`.
