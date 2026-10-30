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


## Stage 2: observational SelfBody forward prediction review (DEV)

`review_self_body_prediction(prior_body, later_body, ...)` reuses existing
PRD `PredictionState`, `TransitionRule`, and `predict_transition`.
It requires the same scoped Self/session, two distinct decision epochs, two
ordered native Mineflayer source references, an explicit maximum native
sequence gap, and a prior hypothesis with exact `native-probe:` and
`body-field:<key>` source binding. The corresponding PRD initial field must
also equal the native initial observation: a forged source-reference string
cannot validate an imagined starting body state. It independently replays the PRD rule
and checks Action-correlated observations against S16 OUTCOME lineage.

The result is an immutable `BodyPredictionReview`:
`MATCH / MISMATCH / UNDETERMINED` plus source refs, predicted/observed
values, reason, and original prediction/native provenances. Position, health,
food and saturation are comparable *only when genuinely exposed by the
current native Present adapter*. Existing PRD values are integers/strings/
booleans; numeric comparison with native float values requires an explicit
finite absolute tolerance (default 0). A missing value, excessive native
sequence gap, non-comparable type or unavailable PRD value remains
`UNDETERMINED`. Missing source binding, foreign Self/session, replay,
counterfeit rule, or false S16 success are rejected. The result never
credits M0 energy, P1 recovery, Action success, learning or a verified
world-physics law.

`bind_body_prediction_review_to_request(prior_world, current_world, ...)`
rechecks both World/Body Present source joins, recomputes the Body review,
and attaches `self_cognitive_body_review` to an existing L1 or L2
`BoundedChoiceRequest` / `OpenCognitionRequest`. This slot is reserved
against input spoofing. A typed, **non-executable** information candidate
is attached: `COMPARE_MODEL_WITH_OBSERVATION` (match),
`REASSESS_BODY_MODEL` (mismatch), or
`REQUEST_ADDITIONAL_BODY_EVIDENCE` (undetermined). The review is never
routed to motor authority by the view. With a fixed observation and
two different prior model predictions, an offline deterministic
RelayEngine test can choose different existing cognitive choices;
this is input sensitivity, not demonstrated real-world decision
improvement, generalization, learned habit or better viability.

At this stage there is still no authoritative World revision in Present,
independent sensor/custody proof, or qualified physical body prediction
score. S-owned DEV World and V scientific comparison remain separate gates.


Verification contract for this candidate: Python 3.12 focused
`tests/test_self_body.py` and `tests/test_cognition_view.py`,
Ruff, repository contracts, and the existing S/W4 FAST workflow.
Historical W4 model A/B evidence and protected provenance records are not
rewritten. FULL/main and real Minecraft run remain outside this DEV phase.


## Stage 3: W4 saved-source context comparison (DEV)

`prepare_w4_cognitive_context_comparison` is an **optional**, nonexecuting
adapter in `adapters/mineflayer/self_world_cognitive_w4_compare.py`.
It accepts the existing `W4OfflineEpochReplay` generated from
operator-pinned W3 Node stdout / Java collector / report bytes, runs the
**unchanged** `prepare_w4_offline_cognition_inputs` source, ATT and
conditional PRD review gates, and keeps the original bounded/open
`BoundedChoiceRequest` and `OpenCognitionRequest` as the fixed baseline.

The new arm adds exactly three reserved, explicitly source-typed
`self_cognitive_*` context items to each existing request; original
context entries, allowed choices, instruction, THINK admission and request
identity remain byte-for-byte unchanged. Both modes consume exactly one
corresponding view per epoch. All L0/L1/L2 projections retain
`UNVERIFIED_FRESHNESS` for unclocked saved native Present, `UNKNOWN`
SelfBody (older W4 source has none), and `world_revision=None`. They do
not claim that an omitted entity is absent, safe, or physically impossible.

The comparison records context JSON UTF-8 payload bytes and emitted facts
as **cost proxies**, not measured model tokens, runtime latency or physical
M0/P1 energy. The deterministic offline stub test demonstrates only that
a source-sensitive consumer can choose a different allowed *cognition*
option with the additional frame; it does not show that the rich frame
performs better than the old source-provenanced W4 context. Historical
W4 A/B negative findings remain negative and untouched.

Focused tests use synthetic W3/W4-shaped locally sealed records (including
positive-match, positive-mismatch and unobserved / undetermined cases),
validate preserved source hashes, and reject forged authority, source
mixing, counterfeit reviews and changed report pins. **The CI does not
contain or re-run the operator's real saved W4 raw bytes.** A subsequent
operator-pinned read-only replay of those actual files, then a matched
real-model comparison, is required before any real-evidence or effect claim.

No new World/Java/Node launch, provider call, actual Action, S16/S17 outcome,
S10 learning, Memory write, R qualification or V science is made here.
