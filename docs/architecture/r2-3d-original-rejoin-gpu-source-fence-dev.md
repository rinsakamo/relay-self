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

## Existing Original Bridge attachment (no replacement)

The original Stage28 `attach_observation_only_bounded_l1` requires
`PhysicalIssueAdmission.observation_only` and current Owner WorldBody probe
identity to equal the original Bridge's last login observation. It does
**not** inherently reject first A reJOIN; its checks must be satisfied by the
current original runtime.

The imported B reJOIN fixture normally constructs a **physical-enabled**
resident gate. With that gate, the Original Bridge correctly refuses GPU
attachment. The R2-3d synthetic fixture instead constructs its original
Physical gate in `observation_only=True` **from boot**, prior to any
login/reJOIN. The existing Original Bridge attachment succeeds unchanged
when the correct current A/B login Body identity also holds. No new Bridge
attach method, gate downgrade, direct assignment of `inference_lane`, or
fake current/native source is used. In a live system with later Native
WorldBody updates that break the original login-probe identity, original
attachment **remains HOLD** until that distinct case is reviewed.

Paper/Native source changes are outside the Python lock: attached Source
preflight and readback do not constitute durable capabilities. A future real
issuer must still bracket submit and result readback under Original Owner
and fence on a submitted failure.

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

The imported Original Native/Paper B fixture normally boots a **physical-enabled**
resident gate. The R2-3d tests instead create their **original**
`PhysicalIssueAdmission` with `observation_only=True` *at construction*,
before any login or reJOIN; they do not mutate an in-flight gate or manually
assign `bridge.inference_lane`. Physical-enabled post-reJOIN GPU attachment\nstays HOLD. The existing Stage28 method is reused unchanged after\nthe original observation-only qualification.

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
