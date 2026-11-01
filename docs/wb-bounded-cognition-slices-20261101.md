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

## 2026-11-01 WB DEV integration result

Fresh remote/PR/owner readback confirmed #669 at `31df88b7ab71609f2aa824d55b87106daa9e8e78` and the #537 DEV disposable-World rule. Its FAST pytest failed four tests. The repair at `bb4098666877808bf13aa5baa1f42aae584afa94` keeps the default-off `_run_disposable` call signature unchanged (only opt-in passes the WB keyword), and corrects the new test's Body reference to `native-probe:…`; World references remain `present:…`. No source reference was rewritten to make a test pass. An additional omission regression checks that a prior target outside the nearest eight observations still has its prediction review retained, including an observed mismatch.

### Actual World and model boundary

One fresh vanilla Minecraft 1.21.8 World, Mineflayer 4.39.0, Java 21 / Node 22, run `dee27145998f4713896094f4ee8bacb9`, session `8b60ffd8-48d1-4d6c-8529-c38999262d79`. The existing `self_demo --mode DEV --dev-scenario native-selfworld` entrypoint used `--live-think --self-world-live --wb-cognition-slice`. S49's only three decision probes were seq **10,21,51**; decisions WAIT, MOVE_AWAY, MOVE_AWAY. Exactly **two** original S49 MOVE_BACKWARD Actions reached OUTCOME: `s49-native-move-20` (before/after seq22/30, movement 0.7342911432182309m) and `s49-native-move-50` (seq52/59, 0.6269065734210617m). WB issued zero Actions and added zero native probes. L0 did not wait for L2. The existing S16 offline source audit found two positive label-persistence comparisons; this does not establish learned dynamics or Goal success.

The existing S60-B1 observer submitted **one actual Gemma inference**, not a fake provider: existing llama.cpp build10874/e2d2c0d6a, binary SHA256 `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`, Gemma4 12B Q4_K_M SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`. Backend log records 1153 prompt tokens, 96 generated tokens, 3929.65ms total backend evaluation. **S60 provider status is UNCONFIRMED, accepted text is null.** Real inference occurred; successful usable Gemma completion is NOT established. The original strict transport/completion gate was preserved. The exact rejection subcause is UNDETERMINED; no speculative diagnosis is reported as fact. S49's own `real_model_calls=0` excludes the separately enabled L2 observer.

The live source pair seq10→21 had different zombie IDs; the original target was unobserved, so prediction review correctly stayed `undetermined / target_or_property_unobserved`. Energy/fatigue remained UNKNOWN. No model output entered Action, learning, Memory, M/P1 or L0 promotion.

### Same-source comparison (offline, no additional inference)

The same three already received immutable callback objects were copied for evidence; the first two were projected after the World run with WB off/on. No replay into the live observer, extra native receiver or World effect was introduced. Two `/tokenize` calls used the loaded model tokenizer, without inference.

| Metric | WB off | WB on |
| --- | ---: | ---: |
| Current source seq | 21 | 21 |
| Observed exterior cues | 2 | 2 |
| User prompt UTF-8 bytes | 1819 | 2317 |
| User prompt tokenizer tokens (no chat template) | 840 | 1118 |
| Projection time, single offline sample | 0.341ms | 0.524ms |
| Omitted current entities | 0 | 0 |

Body health/food and UNKNOWN energy/fatigue, observer/source metadata and the complete prediction-review object compare equal. Entity identity/label/position/distance are preserved; Both retain origin and visible-action fields; WB adds explicit budget metadata. No important received cue was lost in this two-entity case. The synthetic ten-entity regression deliberately omits two entities, including the farther prior target, while retaining its mismatch review. It does not prove those omissions harmless for other decisions. At low density WB costs **278 extra tokens (+33.1%)**. Neither efficiency nor decision-quality superiority is established. Only WB-on had live inference; model latency/quality of WB-off is NOT_RUN. The two projection times are not a controlled performance benchmark.

### Custody, cleanup and unresolved work

Original evidence is outside the checkout: `/home/rinsa/evidence/wb-669-20261101/` (failed initial CI log, local checks, received probes, prompts, tokenizer comparison, model process lifetime and backend log); World receipt/native report/logs and original manifest are `/home/rinsa/work/wb-669-world-20261101-01/`. Physical runtime HEAD was `bb4098666877808bf13aa5baa1f42aae584afa94`; `git_dirty=true` is retained, not silently changed: generated untracked Python caches existed at launch, and the later omission-only test was added during the run. Runtime source was not edited during execution. Later test/documentation commits are not represented as a new physical run.

Java and Node exited 0, the fresh World directory was removed, and the owned Gemma process exited 0 after SIGTERM without SIGKILL. Native STOP ACK remains **UNATTESTED**; process cleanup is not physical idle or GPU-release qualification. Unresolved: usable S60 Gemma completion/rejection diagnosis, actual L0/L1 slice consumers (this change wires only advisory L2), grounded omission importance across larger scenes, controlled token/latency payoff, source-independent qualification and scientific evaluation. **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.** Main and all other lanes/frozen evidence remain unchanged; no merge.
