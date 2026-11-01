# WB lane — bounded SelfWorld / SelfBody cognition slices (2026-11-01)

**Status:** DEV implementation on a branch stacked on the existing [SelfBody/SelfWorld Draft #634](https://github.com/rinsakamo/relay-self/pull/634), which itself is stacked on S #545. No main merge or new Action authority. Owner Issues: [#632](https://github.com/rinsakamo/relay-self/issues/632), [#633](https://github.com/rinsakamo/relay-self/issues/633). Developmental-learning direction: [#537](https://github.com/rinsakamo/relay-self/issues/537), [#431](https://github.com/rinsakamo/relay-self/issues/431), MP11 [#653](https://github.com/rinsakamo/relay-self/issues/653).

## Problem and boundary

`SelfBodyView` and `SelfWorldView` already represent one source-bound, fallible decision epoch; the new need is **bounded presentation** to L0/L1/L2, not another mutable body/world model or a second place that learns physics. In simple familiar situations fixed L0 can and should remain the cheap path. Unfamiliarity or error may justify higher-level detail and experiment selection, but projection alone does not run an LLM, update beliefs or establish learning.

`relay_self.self_cognition_slice.project_cognition_slice` is a pure read-only helper. A caller must first construct a **qualified** `SelfWorldView` using the existing owner projection, with the optional exact `SelfBodyView` join. The helper checks identity/session/epoch and, where both native observations exist, sequence/request/provenance equality. This secondary check is **not independent native source attestation**. Source provenance is carried through to the returned immutable observations.

- **L0:** at most 2 observed body fields (health, food), 1 nearest observed exterior entity, no memory/model payload.
- **L1:** at most 4 observed body fields, 3 exterior entities, no hypotheses or retained content.
- **L2:** at most 6 body fields, 8 exterior entities, 4 own previously selected Memory **IDs**, 4 scenario **IDs**. No Memory content, private other-Self state, or hypothetical prediction is ever presented as physical observation.
- All tiers: `UNKNOWN` if there is no Present, otherwise `BOUNDED` or `TRUNCATED`. No implicit `CLEAR` state; zero visible entities does **not** prove global absence/safety. `detail_available` indicates bounded omission or alternate read-only evidence that may be explicitly requested from its existing owner; it does not authorize sensor polling or a physical LOOK.
- All tiers: `world_omitted`, `body_omitted`, `remembered_omitted`; a stable presentation order by distance is not a threat model or action priority.
- `source_attested=False` explicitly marks that upstream independent physical qualification has not occurred in this projection.

## Cross-lane contract

WorldBody and the single original S49/Action owner remain the sole physical interface. Existing native Present/S16 → SelfBody/SelfWorld → this bounded cognition slice → existing L0/L1/L2 consumers. Any extra detail is a **read-only local request** to existing views, not a new packet, observation, retained update, native reader, or external model call. S integration decides whether and when to expose the slice; it is **not wired to the live L0 selector by this DEV change**. Existing S10/S11 admission and L0 promotion gates remain untouched.

The L lane owns model family/applicability revision and experience crystallization. WB only preserves correct epistemic labels and bounded context from already qualified received information. M owns true energy/fatigue and resource accounting. WB does not turn Food into M Energy or predictions into actual capability.

## Verification and explicit gaps

Synthetic offline tests cover missing Body/World, L0 continuity, bounded tier size, full-vs-truncated coverage, provenance, cross-Self/session rejection and immutable outputs. Exact-source live Paper verification, effect on real L1/L2 decisions, budget/latency telemetry, native time/freshness revalidation, retention transfer, cognition-resource payoff and scientific value all remain **NOT_RUN** until separate owner-controlled integration. No real Minecraft or Gemma run is implied.

**Classification:** DEV_ONLY / OFFLINE_CONTEXT_SLICE / NO_NEW_SENSOR_OR_ISSUER / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.

## Next step implemented: existing L2 observer read-only hookup (DEV opt-in)

The already existing `LiveL2Observer` performs its own one native S49 Present → source-bound Body/World composition and review. When explicitly instantiated with `self_world_live=True, wb_cognition_slice=True`, or when the existing disposable native-selfworld DEV is launched with the **additional** `--wb-cognition-slice` flag (alongside its pre-existing `--live-think --self-world-live` requirements), the L2 **advisory-only prompt** now shows a bounded `observed` list (max 8) plus source/status/omission metadata from the shared WB projection. The prior model-review evidence and body health/food source remain in the prompt. There is no second native probe, no additional LLM call, and no change to the single original S49 Action owner. Invalid flags fail before World execution. The default-off path retains its legacy prompt.

The existing `S60` model-provider and L2 cancellation/expiry boundary is unchanged; only the optional **model-facing input** changes. The new `wb_cognition_budget` metadata explicitly states `source_attested=false`: a source-bearing projection is not independent physical attestation. An LLM response remains advisory, not a World fact or retained model update. More concise context is a candidate benefit, **not measured token, latency or cognitive-quality improvement**.

Synthetic tests use an in-process fake one-shot loopback provider to exercise the existing observer. This does **not** establish a real Gemma run, World experience, retained learning, L0 policy change, R qualification or V science. Physical integration remains NOT_RUN and any actual owner-run must be recorded separately.
