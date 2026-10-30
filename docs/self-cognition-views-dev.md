# SelfWorld / SelfBody — bounded cognition projection (DEV, 2026-10-30)

Owner: #632 / #633; product integration: #537; architecture: #636.
Base: PR #634 `087fe095a87594505392262da1d341cf0c65b2b2`.
This is an independent DEV branch, not a merge into PR #634/#545/main.

## Purpose

`relay_self.cognition_view.project_cognitive_view` is a read-only
per-epoch projection of existing `SelfWorldView` and its joined
`SelfBodyView`. It does **not** introduce a Model, Memory, Belief, Prediction,
native observation source, Action issuer or semantic owner. The existing
SelfWorld prediction review and W4 replay remain authoritative for their own
typed offline results. The new projection runs no prediction and makes no
outcome or retained learning update.

L0: at most 4 world and 4 body scalar facts, no Memory or predictions.
L1: at most 16 per category, source-qualified visible/remembered world
references and observed/interoceptive body scalars.
L2: at most 32 per category, optionally includes specifically source-bound
conditional PRD predictions and explicitly typed body hypotheticals.
All levels use the **same** source-joined view; the level only selects evidence.
No L2 per-tick scheduling or model call is introduced.

`CognitiveFact` preserves the exact epistemic origin and typed provenances
and reference ids; `CognitiveView` reports omitted items, original
observation refs, partial coverage, uncertainty of freshness and missing body,
and non-executable `information_options`. It does not expose full Memory
content in cheap summaries. Visible entities are *not* automatically hazards;
unseen entities are not absent or safe.

The existing `project_self_world_present` and `project_body_present`
remain the only target-specific translators. The caller is responsible for
qualifying the supplied source, monotonic epoch/sequence, clock and
source freshness. A caller-provided `inspected_at_ns/max_age_ns` filters
missing, future or expired observation timestamps; without one, status is
`UNVERIFIED_FRESHNESS` rather than a claim of physical freshness. Cached
views are never upgraded to observed truth by their prediction.

**Important missing source field:** native Present does not yet expose an
attested World revision. `world_revision=None` explicitly means no
revision-based invalidation guarantee. Sequence and time bounds do not replace
this. A revision-sensitive consumer must obtain a qualified revision signal
elsewhere or defer its decision.

## Decision effects vs physical results

A fixed present with different retained Memory or model forecast may generate
different `information_options`, without producing an Action. This verifies
only a *candidate information-selection difference*, not correct path
planning, actual action preference, improved World outcomes, genuine
learning, P1 WAIT recovery, or qualification.

The owner of physical execution and S16/S17 output remains unchanged.
P1/M resources remain read-only observations; no M energy or fatigue scalar
is fabricated from hypothetical body state. L Lane owns memory and habit
formation, and L0 safety continues to use its existing path even when
these optional views are UNKNOWN/STALE.

## Scope and current limitations

- Offline synthetic fixtures + focused pytest only. No Minecraft, GPU, LLM,
  S10 commit, R qualification, V scientific trial or original evidence mutation.
- Prediction/outcome comparison is reused from existing
  `review_self_world_prediction` (MATCH/MISMATCH/UNDETERMINED);
  mismatch does not supply an Action outcome.
- The forecast is only shown as PREDICTED if its scenario explicitly includes
  the current Present reference and external target reference. It is still
  a hypothesis conditioned on the PRD rule, not an observed World fact.
- This is a bounded projection, not a full adaptive attention or cost model.
  `emitted_facts` counts output, not tokens, compute latency or energy.
- No evidence that more detailed views outperform cheap fixed summaries:
  W4's previously observed negative A/B remains unchanged.
- Further work: bounded cost of scanning inputs, validated World revision
  source, L1/L2 consumer wiring to actual decisions, Body capability
  comparisons and offline saved-W4 replay controls; handoff to #537 for
  eventual authorized DEV end-to-end execution.

Classification: **DEV_ONLY / OFFLINE_ONLY / QUALIFICATION_NO_GO /
SCIENCE_NOT_RUN**.

## Existing RelayEngine connection (offline only)

`bind_cognitive_view_to_request` recomputes the frame directly from the
owner-local SelfWorld view and appends three reserved, typed
`CognitionDatum` keys (`self_cognitive_source`,
`self_cognitive_world`, `self_cognitive_body`) to an existing
`BoundedChoiceRequest` or `OpenCognitionRequest`. It rejects duplicate or
injected reserved keys. The content retains the per-fact epistemic origin,
source references and original provenance, plus explicit omission/freshness
metadata. This does not change request choices or model selection and does
not execute a model, choose an Action or authorize motor control. Existing
`bind_self_world_to_cognition_request` remains available and unchanged.
