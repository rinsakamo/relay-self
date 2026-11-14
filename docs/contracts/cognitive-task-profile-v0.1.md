# RelaySelf Cognitive Architecture v0.1 — Cognitive Task / Profile Selection Contract (04)

> Child [#835](https://github.com/rinsakamo/relay-self/issues/835) of frozen [#828](https://github.com/rinsakamo/relay-self/issues/828). Stacked dependencies: [Common I/O Draft #830](https://github.com/rinsakamo/relay-self/pull/830) → [Schema Draft #832](https://github.com/rinsakamo/relay-self/pull/832) → [3Self/Present Draft #834](https://github.com/rinsakamo/relay-self/pull/834).
> **DRAFT / PURE OFFLINE CPU CONTRACT / NO WORLD, GEMMA, PHYSICAL ACTION OR REAL GPU GRANT / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

## 1. Owner audit / reuse, not duplication

| Current source | Reused interface | Boundary |
| --- | --- | --- |
| `main:relay_engine.py` | `BoundedChoice`, `BoundedChoiceRequest`, `OpenCognitionRequest`, `DecisionStatus.UNRESOLVED` | Actual L1 provider and L2 inference remain external to this purely CPU selector; no model call or fallback is performed |
| `main:runtime_coordination.py` | `coordinate_decision_epoch`: existing action deadline supervision → optionally caller-owned decision step and RelayEngine invocation | This function is **not** a hardware scheduler. #835 does not create another recurring decision loop |
| `main:intent.py`, `skill.py`, `action.py`, `action_supervision.py` | Original Intent/Skill/Action ownership and S49 physical action boundary | A selected cognitive profile never authorizes, selects or issues an Action; Task creation does not commit/release an Intent |
| `#830:common_io.py` | `FastCue`, `fast_cue_eligible`, `CognitiveTask`, `TaskRequirement`, `Profile`, `ProfileDecision`, `select_profile`, `CognitionResultReceipt`, `result_is_current` | **No competing ProfileSelector implementation**. #835 wraps existing `select_profile` with current owner/resource-budget predicates; #830 `result_is_current` still fences outputs |
| `#832:innate_schema.py` | Schema activation/current revision and source-dependent signals | Selecting a compute Profile is NOT activating a Schema, adopting a Goal or setting temperament |
| `#834:three_self_present.py` | `PresentFrame` and previously adopted owner refs | Already active Question/Goal/Intent is used as a *reference*, not an invitation for Profile Selector to select the Self's goals |
| `#634` SelfBody/SelfWorld read-only views and `#718` Unified B | Inspected historical design branches, remain **unmerged on separate base(s)** | Not claimed as current main or copied into new databases |

## 2. Logical I/O and authority matrix

| Boundary | Input | Output | Authority / failure |
| --- | --- | --- | --- |
| Present → Task | Current `PresentFrame` (self/session/source/epoch), an explicitly already-active Question/Goal/Intent ref and its owner revision; host-monotonic deadline; bounded choices when applicable | `BoundCognitiveTask` containing the **existing** `CognitiveTask` | Existing Self semantic owner decides which question needs work. Invalid/foreign/unadopted owner ref rejected; no implicit Goal adoption |
| Task → CPU Selector | Requirement FAST_REACTION/SELECT_FINITE/OPEN_REASONING; exact task generation and owner/Present/Schema rev; explicit estimate; resource readout and expiry | `ProfileRoute(ProfileDecision)` with L0/L1/L2/DEFER, reason, optional preemption *hint* | CPU checks only. It never acquires hardware, changes Goal/Intent, interprets World, launches LLM or issues physical Action |
| L0 native Fast Path | Existing source-qualified `FastCue` + installed CPU rule + current timestamp/scope/source | Existing `fast_cue_eligible` boolean | No Present/3Self/Memory/LLM/GPU dependency for **emergency direct L0**. Original Intent/Skill/Action and S49 supervision still required before physical issue |
| L1 finite execution | Fixed, verified two-or-more `BoundedChoice` alternatives, owner-supplied context bounds and provider resource constraints | Existing `RelayEngine` bounded request/result, or unresolved receipt | `UNRESOLVED` does not invent a choice, fallback automatically to L2, issue Action or erase the originating Question |
| L2 open execution | Qualified open Question/Goal/Intent task, backend/budget estimate, actual admission later | Model reasoning *candidate* or cancelled/stale output | Same epistemic HYPOTHETICAL/INFERRED contract; no World truth or Memory promotion. Preempted work can be retried via a **new owner-assigned generation** only |
| L1 requests GPU occupied by L2 | Snapshot says GPU_BUSY_L2 + owner ref | DEFER, reason `L2_PREEMPTION_REQUIRED`, preemption target *hint* | #828/05 owns actual cancel, output fence, backend stop, verified GPU release, L1 admission. This component does **not** claim hardware released |
| All routes → output admission | Existing #830 result receipt, matching profile/task/generation/source/deadline, owner-supplied verified compute grant | Accepted or rejected cognitive output **for further owner consideration** | Original `result_is_current` remains; successful cognition still needs original Skill/Action authorization |

## 3. Pure implementation values

`src/relay_self/cognitive_profile_contract.py` contains:

- `TaskOrigin(kind, ref, owner_revision)` — one already active Question/Goal/Intent, not the highest-scoring schema candidate.
- `BoundCognitiveTask(task, origin, present_revision, schema_registry_revision)` — reference binding with exact context. `Goal` is preserved in **origin** (rather than secretly altering #830's `CognitiveTask` fields); `Question` / `Intent` use the existing named refs.
- `bind_present_task` — validates origin membership in `PresentFrame.active_*_refs`, same Self/session, monotonic host reception, deadline after reception, reused `CognitiveTask` finite-choice rules. It is an offline task constructor, not an owner-admission token. The actual Self owner must supply the chosen origin and authoritative current revision.
- `ProfileCostEstimate(profile, estimated_duration_ns, required_vram_mib, prompt_tokens, output_tokens, context_limit_tokens, provenance, installed_l0_rule_ref?)` — caller-supplied conservative estimate. In initial v0.1, L0 is installed CPU rule, GPU/LLM tokens zero; L1/L2 are GPU-backed; their exact provider cost and performance **are not measured by this contract**.
- `ResourceReadout(scope, revision, captured_at_ns, expires_at_ns, provenance, cpu_l0_ready, installed_l0_rule_refs, l1_backend_ready, l2_backend_ready, gpu_state, available_vram_mib, gpu_l2_owner_task_ref?)` — caller-supplied bounded readout. `GPUState=FREE/BUSY_L2/BUSY_OTHER/UNKNOWN`; an L2 busy state must name its owner. This is **not an authoritative GPU scheduler** or admission grant.
- `route_bound_task` — checks source/self/session/owner/Present/registry/task-generation/current resource revision, host timestamps, deadline slack, model token context and VRAM estimate; calls **existing** `select_profile` once for positive selection. If prerequisites absent, returns `DEFER` and explicit reason without automatic alternative profile or repeated work.
- `ProfileRoute` — retains original `ProfileDecision.resource_admission=PENDING` on a positive route; DEFER is `NOT_REQUESTED`. The optional `preemption_target_task_ref` is only a reasoned suggestion for #05; it cannot stop the GPU or clear the cache.
- `note_l1_abstention` — source-qualified non-Action `FiniteAbstentionReceipt(status=DecisionStatus.UNRESOLVED)`, reusing existing RelayEngine status. Actual provider abstention must come from existing RelayEngine; this function records it on a selected L1 route and **does not make it happen**.

### Routing decision order

1. Owner references and source-bound Present/task must be current; the same owner-supplied revision must match. No Question/Goal/Intent status is changed on fail.
2. Host clock and deadline (strict finish **before** deadline) checked; v0.1 estimates are upper-bound *assumptions*, not measured real-time guarantees.
3. Resource snapshot provenance, scope, revision and expiry checked; these fields are supplied by the owner and need independent integrity in production.
4. Requirement maps **exactly**: `FAST_REACTION→L0`, `SELECT_FINITE→L1`, `OPEN_REASONING→L2`. No hidden L2 escalation for a finite but unavailable L1, nor L0 falling back to model under emergency.
5. For model profiles, predicted prompt+output tokens must fit configured context, GPU state must be FREE and estimated VRAM sufficient. Under GPU_BUSY_L2, an L1 task yields `L2_PREEMPTION_REQUIRED` hint and DEFER; actual preempt state machine is #05.
6. A valid selection returns `PENDING` resource admission, and original result currentness checks remain. No implicit Skill, Action, learning, Memory write, native probe or Goal/Intent authority.

**Resource expiry is not a lease**: the hardware owner must revalidate all readouts at actual admission. **Provenance pointer ≠ authority attestation**; a fabricated `GPUState.FREE` bool cannot prove available VRAM. This is a fail-closed *consistency contract over supplied trusted inputs*, not GPU synchronization.

## 4. Scenario matrix (offline-only)

| Test family | Expected result / negative control |
| --- | --- |
| 04-A Emergency L0 | Existing valid `FastCue` + installed CPU rule qualifies without Present or GPU; expired/uninstalled rejected; no Action issue |
| 04-B Bound L0 | Intent-origin CPU task routes L0 even if GPU UNKNOWN; missing installed rule yields DEFER |
| 04-C Known-food L1 | Two finite choices, Goal-only origin preserved, L1 route returns PENDING; existing `result_is_current` requires actual compute admission and a member choice |
| 04-D Abstention | `DecisionStatus.UNRESOLVED` yields no choice, Action or implicit L2; current Intent unchanged |
| 04-E Exploratory L2 | Active Question routes L2 only under qualified source/budget/resource; no automatic selected physical Action or Memory write |
| 04-F L1/L2 conflict | GPU occupied by L2 → DEFER + `L2_PREEMPTION_REQUIRED`; later independently supplied FREE revision can return L1 PENDING, **not** grant |
| 04-G Invalid present | Wrong Self/session, old source/owner/Present/Schema/task generation → DEFER or construction rejection |
| 04-H Hardware | GPU unknown/other busy/insufficient VRAM, stale snapshot/owner revision, backend absent → DEFER |
| 04-I Budget | No cost estimate, deadline reached, estimated cost too close, context overflow, duplicate profile estimates → DEFER/reject |
| 04-J Continued Question | Work deferred or interrupted; existing Question/Goal/Intent refs survive. New generation may reroute after genuine requalification. No automatic retries |
| 04-K Anti-forgery | Task referencing unadopted Goal/Question or foreign scope cannot be built; negative/invalid cost and fake resource shapes rejected |

## 5. Constraints and next handoff

This is **not** a real distributed hardware scheduler, a real CPU L0 latency qualification, an integrated Minecraft runtime, a Jev inference service or a longitudinal cognition experiment. Original `runtime_coordination.coordinate_decision_epoch` still handles action-supervisor deadlines before optional cognition; the production owner must determine safe scheduling, current clock and fairness. **DEFER is legitimate**, including no cognition at all; do not launch a mandatory periodic L2 retry loop.

Unresolved for follow-up:
- **#828/05 Runtime/Preemption:** actual resource lease/admission, real backend L2 cancel/ACK, out-of-date output fencing, release verified by GPU owner, L1 resume. This pure routing hint has no cancellation side effects.
- **#828/03 Present owner integration:** `PresentFrame.active_question_refs` and current owner revision need to be read from the real Question/Goal/Intent semantic owner; PR #834 has only immutable projection, not a production Goal registry. No admission without authentic currentness.
- **#828/07 Embodiment:** L0, L1 and L2 output candidates all pass original S49/Intent/Skill/Action authorization, never issue directly. Avoid a second physical issuer.
- **#828/06 Learning:** cancellation and insufficiency can be logged with source, but only qualified Action→Consequences→Experience→governed MemoryRevision can alter learned habits or knowledge.
- **#828/08 Integration:** compare actual latency and GPU occupancy on user hardware before claiming real-time feasibility or reproducible autonomous behavior.

**Status:** owner-neutral pure CPU routing interface and deterministic negative controls; DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN. Historic evidence from other lanes unchanged.
