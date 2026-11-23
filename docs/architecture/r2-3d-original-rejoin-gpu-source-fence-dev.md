# R2-3d — Original first-reJOIN registered Question request: attached GPU lane CPU fences

**Parent:** R2-3c Draft #1139 exact base HEAD
`01ea80865e16709df52d5ab7b956797797b7d68d`. No edits to I/B/C/E,
Stage28 issuer or persistent/physical store. This is an opt-in R-lane DEV seam,
not production L1 migration.

## Problem and current boundary

R2-3c creates and weakly registers an ORIGINAL Owner
`R23CFrozenOriginalRejoinL1` with an actual
`BoundedChoiceRequest` using the existing Question
`ADOPT/HOLD/DECLINE` choices. Its original CPU comparison correctly
**refuses** an attached GPU lane. R2-3d requires Source preflight and terminal
job readback *after* the one existing Original `ResidentLlamaInferenceLane`
has been attached, without pretending Stage28's original first-login Source
remains valid on reJOIN.

## New original Bridge attachment seam

The previous Stage28 `attach_observation_only_bounded_l1` requires current
WorldBody observations to be the **same object as the initial login probe**.
The original A-first-reJOIN/B-continuing fixture legitimately has newer
original Native observations; Stage28's method rejects it. This is
**not a failure of the reJOIN source**, nor should the test overwrite
`last_login_observations` or assign `bridge.inference_lane` directly.

An explicitly separate original method,
`OwnedResidentPhysicalBridge.attach_original_first_rejoin_question_l1_dev`,
accepts only **two already-registered Original Owner frozen R2-3c A+B
Question turns**, under the same Original Resident lock. It rechecks
A/B original source, Paper, Native/Physical session match, owner identity,
Native probe, active action absence, lifecycle, no login in flight and
current original GPU lane emptiness, verifies the backend single slot
idle, rechecks both frozen requests/source, then binds the **same existing
lane** and attaches via the original Bridge. The old Stage28 attach remains
unchanged and still rejects this reJOIN source. No direct GPU submit or
physical issuance takes place.

A current Paper/Native source can change outside the lock: this does not
constitute a durable capability or proof of permanent external source
stability. Future real issuer must still bracket submit and result readback
under the original Owner and fence after failure.

## Implementation

- R2-3c original `_original_source` and registered comparison accept an
  **explicit identity-matched lane** parameter. The default still demands a
  disconnected lane, so existing R2-3c fail-closed behavior is unchanged.
- `preflight_r23d_original_rejoin_cpu`: Under the original Resident RLock
  **and** original GPU-lane lock, requalify original reJOIN A/B Native/Paper/
  Composite/Schema/Need/Inquiry, exact transient registered `turn`,
  Owner/cohort identity and scopes, Immutable Request, original Question
  choices, GPU lane identity and current non-fenced state, and absence of
  a prior submitted work ref. Repeat source verification before returning.
  The result is a CPU **diagnostic, not a GPU reservation**. A future issuer
  must recheck while it holds the same Original Owner lock over submission.
- `read_r23d_original_rejoin_result_cpu`: Require an already actually
  registered **Original ResidentLlamaInferenceLane** job and its identical
  ticket object, exact Self/work/request/epoch/native/world/backend,
  `BOUNDED` mode, no question-adoption/Memory consumption, terminal slot
  idle, full submitted request fingerprint and completed
  `ProviderDecision`. Normalize the completed result using the existing
  `RelayEngine`; recheck Source, request and job after reading. Returning
  ADOPT/HOLD/DECLINE is a **readback only** and cannot commit a Question,
  Intent, Memory or physical Action.
- The module intentionally has **no** `submit`, no `await_result` wrapper
  and no error-triggered automatic fence (because it does not own
  submission). The **future issuer** must fence both lane and Original
  per-Self cognition on failure **after** a real submission. A changed
  Source or ambiguous terminal state here returns HOLD, not a forged
  result. No stale Prompt/Context migration is declared complete.
- SHA-256 is an in-process request mutation detector, **not** Original
  Source authentication or cryptographic proof of backend ownership.
  Real `/slots` exclusivity remains an operator/lane qualification
  concern; no real `/slots` HTTP or model POST is issued in this stage.

## Synthetic CPU tests

The test fixture uses the real Original Owner/Bridge/ResidentLlamaInferenceLane
classes, synthetic Native and owned fake Paper event source and a stub
`LlamaCppRelayProvider.__call__`. The tests can call `lane.submit` on
the **synthetic** provider strictly to exercise the actual existing
job/ticket/terminal readback contract. They do **not** launch a real model
or real Minecraft World.

Positive A/B preflight; completed synthetic ADOPT/HOLD/DECLINE, unresolved and
out-of-set choice readback; no file/Intent/Memory/Physical mutations.
Negative tests cover duplicate submission, fake/copied/cross-Self/ticket,
changed request/hash, unfinished/non-idle/uncertain backend, job adoption,
original/foreign lane, changed original/peer owner epoch/probe, native session,
Paper append and cross-read race, Schema, second reJOIN, Intent and registry.

## Deliberate HOLD

This does **not** implement the actual L1 issuer, post-submission cancellation/
fencing, adopted Question persistence, physical Skill+Target L1 SELECT,
product prompt/context switch, or real World/Gemma qualification.

CI acceptance (full pytest/Ruff/contracts/Mineflayer/Paper):
`R2_3D_ATTACHED_ORIGINAL_LANE_CPU_SOURCE_FENCE_DEV_PASS` only.
Keep `R2_3D_REAL_GPU_ISSUER_HOLD`,
`R2_3_PRODUCT_L1_SWITCH_HOLD`,
`QUAL_NO_GO`, `SCIENCE_NOT_RUN`.
