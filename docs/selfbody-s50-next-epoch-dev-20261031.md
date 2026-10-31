# SelfBody #632 — S50 prior-motion read in the NEXT original native S49 epoch

**2026-10-31: offline source-interface DEV only**, based on actual proven
SelfBody/S16/S50 physical join HEAD
`0ee72bc7fdabf26be905ba51779ecb1a1b1f1a99`.
No new Minecraft World, native probe, Action, S16 owner, P1/M/L8 update or LLM.

## Source and owner boundaries

The prior physical DEV result was
`DEV_WORLD_SELFBODY_S16_S50_JOIN_PASS`: one exact S49 Action, typed
S15/S16 and correlated native before/after probe, exact same-Action
SelfBodyView, producer-reviewed S50 Paper/Node original and
MotionCompanion, all in one original Python host process. Prior Paper
movement at ticks 249–251 despite server-last-reported controls OFF was
preserved. The S50 sidecar `TRACE_END` and independent readback passed.
**No later native cognitive epoch actually consumed this information.**

Existing original S49 API:
`s49_normal_session_real_ci.qualify(..., live_probe=callback)`
calls `await live_probe(reading)` on an **already-received original
correlated native observation, before original L0 decision**, without
issuing an extra observation. Existing SelfBody and SelfWorld owners
can construct native current-epoch Body/World views using this exact
same source. This is a *passive pre-L0 observer*, **not an L0 policy
input or proof that L0 used it for an Action choice**.

New module:
`adapters/mineflayer/self_body_s50_next_epoch_passive.py`.

- `SelfBodyS50NextEpochLease(previous_typed_companion)` holds only
  one prior S16-qualified typed SelfBody/S50 companion. Its prior
  original native after-probe seq and native source reference establish
  a freshness lower bound.
- `await lease.observe_existing_s49_probe(original_reading)` is
  suitable for an explicit S49 `live_probe` callback. Only the **next
  existing** same-session, source-correlated, higher-seq `s49-actual`
  event can qualify. If the prior Action ID follows original
  `s49-native-move-<event-seq>`, the later event number must be larger.
  Unexpected, foreign, replayed, non-probe or duplicate callback
  revokes the slot silently so original L0 is never vetoed.
- Original `project_mineflayer_present`, `project_body_present`,
  `compose_self_body_view`, `project_self_world_present` and
  `compose_self_world_view` produce **new** Body/World typed current
  native views with exact same native source. The prior S50 motion
  remains a **separate diagnostic** and is not merged into current
  native OBSERVATION. The prior S16 outcome is not replayed as the
  current Action outcome.
- `readout.read_previous_motion()` explicitly references prior
  Paper activity during that new native callback epoch, returning
  a bounded source-aware summary and zero action/model/memory/grant
  claims. `lease.take_readout_once()` consumes the readout; a second
  attempt fails, and `close()` expires an unobserved slot.
- Node and Paper clocks remain distinct; no effective S15 clear
  World tick, full-tick input idle, physical stability, Goal, P1
  recovery, L10 training, S10 update, or S11 grant is inferred.

### Important live-World engineering blocker

The 2026-10-31 successful one-Action DEV host sealed S50's **whole
client JSONL sidecar footer only when the Node session shut down**.
By that time a new **same-session** original `live_probe` cannot be
received from the terminated Mineflayer client.

Therefore this module's contract can be proven offline by injecting
synthetic original-typed `MineflayerObservation` fixtures into the
actual callback-shaped method, but **that is NOT an actual next
Minecraft cognition epoch**. The old sealed S50 JSON must not be
reused as a new-session source; this lease correctly rejects
different-session native Present. A future LocalCodex physical DEV
test must first decide which legitimate runtime boundary it wants:

A. A **new internal cognitive epoch after action/World shutdown**
   may read the already-validated old companion as *retained previous
   evidence* (without claiming a fresh native Present, live L0 decision
   or World tick). That requires a different explicit SelfBody owner
   cognitive-epoch read contract; it is not implemented by this module.

B. A **new original live S49 L0 decision epoch** can consume the old
   companion via this module, but first requires an S50 owner-approved
   **bounded, independently complete in-session source snapshot**
   *before* Node shutdown, or another source-qualified mechanism
   that avoids falsely representing a partial trace as `TRACE_END`.
   Also requires a same-session next native S49 L0 probe; do not
   request synthetic probes/Actions merely for the test.

Do not silently weaken the complete S50 sidecar validator, invent a
native Present from archived JSON, or start a new World/session and
treat it as same-session epoch continuation.

## DEV acceptance

Offline acceptance: original typed SelfBody and World projection
preserved, same native source/current epoch, separate previous S50
source, one explicit previous-motion read, no L0 authority, strict
negative tests for stale, foreign, wrong request, invalid source,
duplicate and no next probe. CI source test is not World evidence.

Next **physical** goal must be scoped to A or B above by SelfBody/S50
owners. The original one-Action DEV join evidence is not reclassified
as real next-epoch cognition just because this API exists.

`DEV_ONLY / NEXT_NATIVE_EPOCH_INTERFACE_OFFLINE /
REAL_NEXT_EPOCH_NOT_OBSERVED /
COMPLETE_IN_SESSION_S50_SOURCE_UNAVAILABLE /
EFFECTIVE_CLEAR_NOT_ATTESTED / PHYSICAL_STABILITY_UNPROVEN /
GOAL_UNDETERMINED / P1_WAIT_0 / L10_PAIRS_0 /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
