# RelaySelf v0.5 — Contract A: Cognitive Intent Slots / Physical Action Authority

> **Status: A ARCHITECTURE_DESIGN_COMPLETE / 2026-11-07 DESIGN FROZEN / OWNER API REVIEW + IMPLEMENTATION PENDING / NOT EXECUTABLE.**
> This resolves the architectural choice, not the owner-specific acceptance tests: see [v0.5 freeze handoff](../unified-v0.5-design-freeze-20261107.md). Historical design-proposal labels within this document describe earlier iterations.
>
> Parent [#717](https://github.com/rinsakamo/relay-self/issues/717); review on [Draft PR #718](https://github.com/rinsakamo/relay-self/pull/718). This refines [Unified Architecture v0.5](../unified-architecture-v0.5.md), not `main` executable contracts. `main@4348a614900c1d0828581a8eec2c523ba5ae237f` is the audited baseline.
>
> **Authority boundary is fixed:** existing S #537 / S49 is the only Minecraft physical Action issuer. No model, cognitive slot, Plan, WB view, scheduler or newly invented Intent owner gains Action / Learning / Body-energy debit authority. This document does not approve real World, LLM/GPU, R/QUAL or V/SCIENCE runs.

## 1. Problem and design result

We need multiple independent or interdependent cognitive activities (L0/L1/L2) to pursue Needs/Goals/Questions and temporally construct Plans, *while keeping exactly one lawful physical Action execution boundary*.

The target design distinguishes **cognitive task commitments**, **body-directed execution commitments**, and **the sole physical dispatch authority**. It does **not** require all body-directed commitments to collapse into one global Intent or one owner:

1. **Cognitive task Intent (slot scope)**: one active task commitment associated with a transient cognitive execution slot, or no Intent if only monitoring/reflexing a source. It can reason, retrieve, propose and possibly contribute to a body-directed Intent; slot possession alone never confers physical authority.
2. **Body-directed Execution Intents (per-commitment scope)**: **zero, one or many** currently valid commitments may require bodily effects. They can coexist, overlap in time, or compete for the same WorldBody channels. A given Intent can be related to one or several Goals; arbitrary aggregation into one giant Intent is neither required nor preferred. Each bodily effect must be linked to a legitimate **live, owner-validated** commitment and admitted separately for its actual resources and authority. The initial S49 adapter presently exposes only one current Intent through one `IntentCommitment` owner; that is a compatible first stage, **not the final architectural upper bound**.

**The labels Cognitive and Execution describe the work's effects and admission scope, not ontologically separate subclasses or automatically new owners.** One Intent may involve both thought and body action, and multiple independent Intent commitments may remain concurrent. The *single S49 issuer* is a constraint on who may dispatch/authorize effects, **not how many intentions can be held**. This design does **not** change today's `IntentCommitment.current_intent` implementation; a multi-owner/currentness registry and owner-derived bindings require explicit S review and implementation.

```text
MySelf / SelfWorld / SelfBody -> relevant Goals, Needs, Questions
                  |
           Goal Arbitration / Composition
                  |
         L0/L1/L2 cognitive execution slots
                  |
       task/Plan/Skill proposals (no physical grant)
                  |
       multiple valid body-directed Execution Intents
              |            |             |
         dodge/move    jump/terrain    attack/defense
              \            |             /
          one S49 issuer: action admissibility,
          owner/currentness + per-channel arbitration
                          |
               body-specific ControlFrame(s)
                          |
       authorized Skill/Action binding and supervision
                          |
         WorldBody execution / separate causal outcomes

CURRENT S49 DEV: one active IntentCommitment owner,
                 serial MOVE-only admissibility (unchanged).
TARGET DESIGN:   multiple live Intent commitments,
                 one physical issuer; compatible channels may overlap.
```

The diagram describes a proposed connection, **not** integrated implementation. The present S49 `escape-threat` is one physical Current Intent. Multi-Intent arbitration, concurrent controls and Goal composition have **not** been demonstrated by that test.

## 2. Distinct objects and relationships

| Concept | Scope / lifetime | May cause a physical issue directly? |
| --- | --- | --- |
| Need / Goal / Question / persistent Commitment | Owner-specific durable or transient cognition; may outlive all slots | No |
| Plan candidate / temporal Goal graph | Source/revision-scoped reasoning product; not necessarily persisted | No |
| Cognitive slot | Self-created bounded runtime work capacity; not a personality or semantic owner | No |
| Slot-local task / Cognitive Intent | At most one currently committed task per slot when needed; can be paused, reconsidered or released independently | No |
| Body-directed Execution Intent(s) | Zero or more bounded live commitments targeting physical effects; each needs real owner/currentness validation; initial S49 implements one | Not by itself |
| SkillExecution | One started, immutable physical Intent association and lifecycle | No |
| Action proposal | One primitive requested effect, source and causal scope | No |
| Authorize / issue | Existing legitimate S49/S14-S16 owner seam; independent policy gate and one issuer | Yes, only after admission |

Multiple Goal or Question objects can be simultaneously *relevant* while zero, one or several **cognitive** slots are ACTIVE. There is no requirement to keep one heavyweight slot occupied per Goal. A slot may perform multiple successive tasks, but may not silently replace its committed task without the appropriate release/reconsideration event. A cognitive Goal graph may be a DAG rather than a fixed L2 > L1 > L0 hierarchy; dependency edges need explicit provenance and cannot create an Action grant.

### No accidental identity equivalence

For later API exploration, candidate binding identities should be explicitly scoped by:
- `self_instance / physical_body / world_session`;
- `slot_instance` plus `slot_generation`, if derived from a slot;
- zero or more **owner-derived, live `execution_intent_refs`** with explicit command/channel-to-Intent binding; never IDs selected as authority by a model;
- `goal_refs` and `plan_revision` (if supplied); capability/skill binding;
- `observation_source / native_seq / world_revision`, expiry/deadline;
- `physical_issuer_id`, grant/authorization origin and action/resource scope.

These are **contract fields to be minimized/verified against real owners in implementation**; they are not claims that corresponding live fields currently exist. An equal string `intent_id` in two independently constructed owners is **not proof** of a legitimate physical association. Provenance alone is evidence attribution, not actual permission.

## 3. Slot lifecycle and resource admission (conceptual, not a new enum)

Proposed ephemeral slot operational states:

```text
UNALLOCATED
  -> PENDING (work retained, capacity not yet allocated)
  -> ACTIVE (admitted compute budget and versioned task)
      -> SUSPEND_REQUESTED -> SUSPENDED (new output fenced)
      -> TERMINATED (done/abandoned/expired)
  -> ACTIVE from SUSPENDED only after revalidation
```

- `PENDING` is normally **work or Goal retained outside an ACTIVE slot**, not a memory-consuming permanent "pending slot" object.
- `SUSPENDED` preserves valid work/commitment if the owning state still exists but must **immediately fence further side effects/output promotion**. It does **not** prove that GPU kernels, a model-server request, control inputs, physical movement, or an issued Action have stopped.
- `SUSPEND_REQUESTED` distinguishes interrupt request from confirmed logical halt. If the backend remains active, resources remain **occupied/UNKNOWN** until independently observed; the runtime cannot reallocate capacity based only on a requested cancellation.
- An existing slot can resume without recommitting its local task if the same bounded owner/commitment is still current and source/authority/cost constraints pass. If only a durable Goal survives process restart, reconstruct a **new** runtime task/commitment after admission; never invent a continuation of an unavailable in-memory `IntentCommitment`.
- No automatic `IntentCommitment` release, `SkillExecution.CANCELLED`, or `ActionLifecycle.TIMEOUT/OUTCOME` occurs merely because a slot becomes suspended. Distinguish cognitive yield, Plan replacement, Intent reconsideration, Skill cancellation and physical Action closure.

**Capacity rule:** initially fixed conservative `ACTIVE` upper bounds per L0/L1/L2 may be used; these are **implementation defaults, not ontology**. Later use measured host compute, actual free resources, deadline/slack, synchronization overhead, WorldBody constraints, estimated uncertainty and prior deadline misses. Reserve urgent L0 responsiveness and require admission before L2 can consume its budget. Different L-level tasks can share a physical CPU/GPU only if resource use is actually supported; tasks are not assumed to be separate OS processes.

**Concentration** denotes adaptive narrowing of concurrent work to satisfy measured deadlines and outcomes. A deadline miss is evidence, not automatically evidence that count was the sole cause; retain load, task type, contention, world context, cancellation status and UNKNOWN.

## 4. Temporal Goal/Plan changes without Intent churn

- A Plan revision changes **how** current Goals are pursued; it does not necessarily change **what is committed**. A local phase failure, new affordance, safer route or timing change may replace a Plan/Skill while keeping the relevant one or several Execution Intents in place.
- A new proposed Plan must not expand an Intent beyond its admissible meaning, authority or viability scope. Broad objective strings like "survive" are **not wildcard Action permission**. Source-grounded action applicability and actual grant scope remain necessary.
- If the goal/commitment's meaning, feasibility, authority or viability is materially challenged, request **reconsideration** with its own triggering source. Only the separate `CONTINUE` / `RELEASE` decision changes the commitment, or a valid terminal success/failure/invalidation closes it.
- New cognitive slots may create prospective work while old physical Action is still executing; their outputs are advisory until admitted at a source-current physical boundary. Do not retroactively alter an already issued command.
- Goal-level incompatibility (protect X vs destroy X), resource conflict (two operations need same input), and time-sliceable order (eat then attack) are distinct. Re-evaluation can choose composition, sequencing, deferral or escalation, with possible zero-action WAIT.

Example (conceptual): **Intent A:** gain distance from a nearby threat. **Intent B:** recover hunger. **Intent C:** neutralize the threat. They may coexist while **Plan P1** orders A -> B -> C or **Plan P2** prioritizes C -> B. The physically issued subset can change over time without collapsing all three into a synthetic 'survive' Intent. Each phase is guarded by actual observation, authority and outcome. Minecraft capability for movement+eating or attack+eating must be **empirically verified**, not inferred from Goal coexistence.

## 5. One physical issuer and admission sequence

**Mandatory physical path** (conceptual layers; the actual existing owners still execute their established interfaces):

1. Read the **current** source-qualified observation and actual physical owner state; record relevant WorldBody resources, deadline and uncertainty. Missing or stale inputs fail closed or yield UNKNOWN.
2. Form candidate bounded Plan/Skill/Action and any support from cognitive slots. L2 recommendations, value gradients and apparent Goal urgency are **not** grants.
3. Only the **existing S49 owner/adapter** decides whether to admit candidate physical effects, based on actual live/authorized Intent owners and their currentness, actor/skill capability, source/currentness and channel conflict. It may choose a compatible subset, none (WAIT), defer or use an already tested cheap L0 path. **Current implementation** can inspect just its one `IntentCommitment`; multi-Intent admission is **future owner-reviewed API work**.
4. **Physical execution binding:** for each proposed primitive effect derive the relevant Intent ID(s) from **real authorized live owners**, preserve source Goal/Plan refs, and check allowed action/channel scope, not matching strings. The current `SkillExecution.start(...)` and `ActionLifecycle.propose(...)` continue to use their **actual existing one-owner `IntentCommitment`** interface until the S owner implements validated multi-Intent routing. Do not pass a freely created cognitive slot owner to bypass S49. A multi-Intent frame must not use an ungrounded composite ID; the frame's per-channel causal lineage must remain auditable.
5. Before issuance, check the authorized principal and grant's real scope, current source/epoch, actor, body capability, action resource reservation, deadlines, and exclusivity. `ActionLifecycle.authorize()` remains the **recorded lifecycle transition** and does not authenticate a fabricated `authority` string by itself. Avoid second issuers or independent authorizers minted by cognition.
6. Original S49-issued command passes existing S14/S15/S16 / ActionSupervisor processes. Final OUTCOME/UNKNOWN/TIMEOUT **and** source-bound consequence are passed to the next cognitive epoch as evidence; physical motion settling and control-clear must not be inferred from `OUTCOME` alone.

A possible transient **PhysicalAdmissionRecord** is a *typed, bounded source-and-owner join*, **not** a second authorizing owner: it might record `world/session, channel/Action -> live owner-derived Intent ref(s), slot/plan generations, skill/action identity, admitted capability/resource scope, original grant/authorization source and expiry`. Exact fields need a local S owner Grand Null and tests; if existing `ExecutionBinding` and S49 traces suffice, **do not create a new record type**.

### Explicit non-authority edges

```text
Cognitive Intent  -X-> ActionLifecycle.propose as free-standing physical owner
L2 / S60 advice  -X-> S14 grant or S49 input stream
SelfWorld/Body estimate -X-> World/WorldBody truth
Action OUTCOME state -X-> proof of actual effect or physical rest
Slot suspended -X-> cancellation of Action or proof of GPU release
Same textual intent_id -X-> proof of same owner/epoch/physical authority
```

## 6. Physical resource conflict, exclusivity and cleanup

**S49 compatibility policy (current DEV implementation only):** the present MOVE-only executor admits **one in-flight primitive Action**; it rejects new proposals when `ActionSupervisor.open_actions` is nonempty. This protects existing tested S49 behavior, **not** a permanent one-Action-per-body or one-input-channel ontology rule. The target architecture supports **one physical issuer emitting an admitted multi-channel control frame**, whose channels may overlap physically when independently proven compatible. Until the multi-channel protocol, grant scopes, atomic conflict resolution and source-qualified outcomes are implemented and tested, S49 continues to use its existing single-action policy.

Future controlled physical concurrency is possible only after:
- actuator/resource set and conflict relations are declared by body-specific owner (not abstract Goal graph);
- disjoint/compatible controls and native protocol behavior are independently verified;
- atomic reservation/issue/closure avoids two mutually exclusive grants;
- source, time, capacity, physical input state, clear/STOP ACK, lingering motion and individual Action outcome are independently accounted for;
- emergency suppression and cleanup prevent deadlock, hidden action replay, or duplicate issuer.

**Crucial:** the same WorldBody can still move during post-S16 settling. A terminal `OUTCOME` receipt is not by itself proof that an actuator/input resource is physically quiescent. Release a reservation only when the qualified execution owner can justify release with existing S15 clear and sufficiently current physical state or an explicit conservative settling bound. Otherwise keep the resource unavailable/UNKNOWN.

**No inferred cancel:** on Intent RELEASE, Slot SUSPEND, task stop or Plan replacement:
1. fence all *new* admissions from obsolete generations;
2. supervise every already issued Action until actual closure, current owner cancellation path with qualified STOP/CLEAR, explicit UNKNOWN, or deadline handling under existing contracts;
3. preserve exact original Action ID/session/source and any unresolved physical effect;
4. allow a successor to issue only after its required resources are actually released, reserved with verified overlap capability, or conservatively blocked.

Fair scheduling may avoid starvation among ordinary Goal/Plan candidates; however viability, current actual actuator state, protected emergency L0 and deadlines are **admissibility constraints**, not arbitrary numerical priorities.

## 7. Worked cases

### Case A: eat after retreat
- SelfWorld threat Goal and SelfBody hunger Goal are simultaneously active; cognition proposes P1 `retreat -> assess safe distance -> eat -> re-approach -> attack`.
- Distinct body-directed Intents for distance management, nutrition and defense can remain valid during phase changes. The currently eligible bodily effect still needs an actual owner-derived commitment and S49 authorization. **Current S49 does not yet implement multiple such commitments.**
- A movement Skill proposes `MOVE_BACKWARD`; original S49 authorizes/issues/closes and verifies physical evidence. Eating can be attempted only when an implemented and authorized `USE_ITEM` path and preconditions exist. **Current S49 does not prove or provide that path.**
- Enemy closes distance during attempted eating: fence new eat proposals, preserve already issued results, revalidate, revise Plan locally; request Intent reconsideration only if its objective is materially challenged.

### Case B: eliminate before eating
- In a different verified context, P2 `attack -> confirm threat removed -> eat` can be favored by evidence and value gradients, **without assuming universal superiority**.
- Attack availability and actual success evidence are missing in current S49 MOVE-only proof; planning remains cognitive/read-only until physical action is independently admitted.

### Case C: L2 delay and urgent L0
- L2 slot proposes an improved path but exceeds a local budget while native threat arrives.
- Protected L0 can continue existing S49 cheap path; stale L2 output cannot authorize/issue even if later returned. A logical cancel is not backend STOP/VRAM release.
- If the cognitive estimate of capacity is wrong, the discrepancy is source-qualified experience for later allocation learning, not an excuse to violate hard runtime caps.

### Case D: two conflicting L0 candidates
- Movement and combat slots can own distinct valid body-directed Intents while requesting different controls. Identity alone grants no physical authority.
- The one S49 issuer admits **both if channels are verified compatible** (future ControlFrame), or resolves actual conflicts by sequencing/defer/deny. Current MOVE-only S49 still dispatches just one in-flight Action. No unqualified second issuer or fabricated "parallel" success.

## 8. Contract invariants (for later executable owner review)

| ID | Required invariant | Proposed negative control |
| --- | --- | --- |
| A-01 | Slot is transient cognitive capacity, never physical Action authority | L2-only slot tries direct issue |
| A-02 | Slot identity, Intent identity, and physical issuer authority are not interchangeable; multiple live Intent owners require independently validated scope/currentness | same textual ID, foreign owner |
| A-03 | No silent replacement of committed Intent | alternative Plan causes hidden COMMIT |
| A-04 | Local Plan/Skill revision need not break Intent | phase/route change without RELEASE |
| A-05 | Goal/Plan candidate carries bounded provenance/currentness | stale world/native seq or replay |
| A-06 | One physical issuer and required valid grant | second issuer, fake authority string |
| A-07 | Each physical primitive binds to the actual current authorized Intent owner(s); existing single-owner Skill/Action API is not silently weakened | cognitive slot owner passed as Action parent |
| A-08 | Resource exclusion is **per conflicting channel**, not global to the WorldBody; current S49 has the separate initial one-in-flight implementation guard | incompatible same-channel requests; post-S16 settling |
| A-09 | Slot suspension is not automatically Skill/Action cancellation | suspended L2 returns stale output |
| A-10 | In-flight issue closes via real evidence/deadline/UNKNOWN | RELEASE during MOVE; no STOP ACK |
| A-11 | Runtime budget/actual deadlines bound concurrency; emergency L0 remains available | L2 task saturates GPU/CPU or exceeds deadline |
| A-12 | Physical outcome is separate from commit/Plan success and learning | OUTCOME without effect, untrusted WB view |
| A-13 | Reconsideration trigger and CONTINUE/RELEASE carry distinct provenance | new affordance silently replaces intent |
| A-14 | Source-matched WorldBody/capability required for proposed actuation | phantom USE_ITEM or stale body capability |

## 9. Staged implementation path (owner S #537, not authorized by this document)

**A0 — Offline, read-only boundary:** derive source-bound Goal -> multiple body-directed Intent candidates from fixed L0/L1/L2 slots and demonstrate disjoint vs conflicting channel demands. Distinguish commitment count from physical issuer count; exercise stale/foreign-owner rejection; **0 new Action**. Reuse current S49 unchanged.

**A1 — Local physical-admission proof, still one physical action at a time:** at original S49 owner, validate candidate-to-actual-live-owner `ExecutionBinding`, source/epoch/deadline and actual grant scope. Test mismatch/fake authority/replay and sequential source-bound actions, with a roadmap for independently referenced multiple Intents. Keep original MOVE-only behavior and no automatic learning.

**A2 — Cognitive scheduling and guarded Plan revisions:** preserve concurrent valid body-directed Intent candidates, transient tasks, suspended/resumed cognitive work and local Plan revisions without forcing a single global Intent; enforce resource budgets. Add source-bound tests for protected L0 amid slow L2 and post-outcome physical settling/clear. No body-command expansion is implied.

**A3 — Multi-channel motor composition, initially opt-in and offline:** expand body-specific capabilities only after typed channel controls, per-channel grant semantics, controller lease/currentness, bounded command frame, dispatch/clear and source-qualified outcome tracing are independently tested. The single existing physical issuer composes compatible locomotion/jump/orientation/attack requests into one frame without granting cognitive slots direct physical rights. Mixed channel effects, individual completion and emergency override require separate evidence; no simultaneous physical operation is assumed implemented. Eating/attack and concurrent physical operations are separate opt-in feature qualifications, **not** an A0–A2 completion gate.

### Completion statuses

- **DESIGN_DRAFTED**: this document is complete as a proposal and reviewed against current main/S49 sources.
- **DESIGN_ACCEPTED**: owner review confirms lawful scope, conflict rules and migration invariants; Issue #717 A may then be marked designed.
- **IMPLEMENTED_OFFLINE**: owner code + negative tests pass on exact HEAD; a design document alone is not this.
- **DEV_WORLD_OBSERVED / QUALIFIED / SCIENCE**: separate real owner provenance and gates. Never infer from other lane World trials.

## 10. Non-goals and remaining review choices

**Non-goals:** rewrite protected `main` action lifecycle in this Draft; run Minecraft/Gemma; add an executable central `SlotManager`, new Intent/Action owners, new Learning grant, per-slot physical issuer, or unverified actuator concurrency.

**Owner review choices before A is accepted:**
1. Whether slot-local commitments actually require their own ephemeral `IntentCommitment` instances or can be represented by existing task/Question commitment references, *without allowing them into physical Action admission*.
2. Whether original S49 `ExecutionBinding` and trace already suffice to represent the cognitive-to-physical Plan association, avoiding a new `PhysicalAdmissionRecord`.
3. The body-specific evidence required to declare actuator resources quiescent after S16 (including post-clear settling), and negative tests for release/UNKNOWN.
4. Exact source/owner generation token representation and plan revision bounds; avoid adding globally mutable ID registries without demonstrated need.

These are bounded implementation choices under the v0.5 conceptual decision, **not** permission to relax existing fail-closed behavior.

## 11. Source references

- [Intent commitment](intent-commitment.md), [Skill execution](skill-execution.md), [Action lifecycle](action-lifecycle.md), [Action supervision](action-supervision.md)
- [Runtime principles](../runtime-principles.md), [Ontology](../ontology.md), [v0.5 gap audit](../unification-gap-audit-v0.5.md)
- [Product S #537](https://github.com/rinsakamo/relay-self/issues/537), [parallel cognition #367](https://github.com/rinsakamo/relay-self/issues/367), [S49 completed original owner #674](https://github.com/rinsakamo/relay-self/pull/674), [cross-lane #636](https://github.com/rinsakamo/relay-self/issues/636)

## 12. Multi-channel motor decoding from multiple Execution Intents (2026-11-03 revised design)

> **STATUS: DESIGN PROPOSAL / SUPERSEDES ANY READING OF §6 AS A PERMANENT SINGLE-ACTION LIMIT.** The single issuer is an **authority singularity**, not a single motor command or single control channel. Existing S49's `open_actions` exclusion is a current MOVE-only DEV implementation limit, not the v0.5 target. No physical concurrency is currently demonstrated or authorized by this amendment.

### 12.1 Hierarchy and source of control requests

```text
multiple valid body-directed Execution Intents
 (e.g. MOVE_AWAY, JUMP_OVER, ATTACK_TARGET)
     |               |              |
 guarded Plan(s) and Skill controllers (no direct issuer)
     |            |            |              |
 locomotion    jump        orientation     attack/use
     \            |            |              /
        Body-specific Motor Decoder / Control Composer
           * validate actual capabilities and dependencies
           * resolve channel conflicts / temporal guards
           * stage a bounded ControlFrame and owner-bound grant
                         |
              existing sole S49 physical issuer
                         |
             WorldBody adapter / real input channel effects
                         |
       bounded per-channel evidence + composite outcome association
```

An Execution Intent **does not output native buttons directly**. Multiple Intents can remain current while their Plans/Skills propose bounded channel requests. A request must carry its **originating, live owner-validated Intent reference**, not become authorized just because a frame includes it. The Motor Decoder uses **WorldBody capability and actual control state** to merge compatible requests into one control frame or safely defer/deny some. All physical dispatch remains with one S49 issuer; it is the **authority/dispatch bottleneck**, not the owner of all goals or a single global Intent.

A new top-level `MotorDecoder` *owner* is **not presumed**: first attempt the minimal body-specific controller-composition boundary inside the existing S/WorldBody adapter. Add independently persisted/authorized state only if Grand Null shows no existing owner can retain it.

### 12.2 Proposed typed ControlFrame (design type, not current API)

```text
ControlFrame {
  physical_body, world_session, source_revision, frame_sequence,
  physical_issuer_id, channel_intent_bindings: {channel: [live_owner_intent_refs]},
  channel_plan_revisions: {channel: plan_revision},  // when applicable
  valid_from, valid_until, control_lease_generation,
  held_controls: {locomotion: FORWARD, ...},
  event_pulses: {jump: REQUEST, attack: REQUEST(target_ref), ...},
  continuous_targets: {orientation: TRACK(target_ref), ...},
  channel_grants_and_requirements: [...],
  preconditions, abort_conditions, expected_channel_outcomes
}
```

**Held control** (e.g. moving forward over a bounded period), **event/pulse** (e.g. discrete attack request; jump may be implemented as state or edge depending on body adapter), and **continuous controller target** (e.g. track the entity) have distinct timing/closure semantics. They are **not** four primitive `ActionLifecycle` objects already verified at the same tick. One frame is an *owner-validated emission plan/coordination unit*, not automatically an atomic Minecraft/protocol transaction or an evidence-backed collective success.

### 12.3 Per-channel ownership, composition, and compatibility

Initially define a **body-specific capability map**, not universal assumed axes:

| Channel class | Example controls | Primary conflicts / dependencies |
| --- | --- | --- |
| Locomotion | forward/backward, strafe, throttle | competing speed/direction controllers, collisions, fatigue |
| Vertical/stance | jump, crouch, posture | grounding, collision/headroom, movement interaction |
| Orientation | yaw/pitch, tracking | camera owner contention; attack may need aim |
| Interaction | attack, use/eat, item switch | hand/input exclusivity, cooldown, item inventory/target constraints |
| Global stop/safety | clear/abort/STOP, emergency override | preempts or inhibits lower-priority channels according to verified control semantics |

A compatibility decision is **not** just comparing resource labels: there can be conditional cross-channel constraints (e.g. jump needs room, attack needs target/range/aim; using an item may interfere with sprint or attack). Requested simultaneous `move + jump + attack` is a *candidate* frame only if relevant dependencies, actual game version/body adapter behavior, native capability and execution deadline have been checked.

If two Skills/Intents propose incompatible values for the **same** channel, resolve **before** issuing using source-qualified feasibility, viability/emergency constraints, **all relevant live Execution Intents**, urgency, deadlines, value/Plan commitments and current leases. Non-selected proposals remain deferred/denied; do **not** create an invisible extra Action issuer. Explicit fairness is subordinate to bounded safety and deadlines.

### 12.4 Timing, authority, observation and cancellation

1. **Prepare:** evaluate candidate channel requests against a source-qualified observation and **the set of actual live Intent owner commitments**; test capability, cross-channel dependencies, conflicts, source freshness and deadlines. No global single-Intent reduction is required. A later L2 advisory cannot mutate a previously prepared/issued frame without a new admission.
2. **Authorize:** the one real physical issuer performs scoped authorization for the *whole frame and each admitted channel with its own owner-derived Intent lineage*. No channel may be added after authorization. A valid authority string alone is insufficient. The frame is not released as a union of independent, out-of-order authorizations.
3. **Dispatch:** send the bounded set of controls via the existing WorldBody adapter with an observable ordering/window. **Do not claim atomic same-tick execution** from separate JS/native calls absent wire/World evidence. Some control state persists between events; track transitions and lease expiration explicitly.
4. **Observe:** record source-correlated per-channel ACK/clear/World effects and the outer frame's state. Attack intent, attack call success, hit/target damage and death are separate; movement and post-clear inertia are separate. If evidence is missing, the affected channel/frame is UNKNOWN, not collective OUTCOME success. An outer frame outcome must not erase unresolved child effects.
5. **Stop/replan:** fence future frames from obsolete `slot_generation / plan_revision / source_generation`. Request S15/native clear where supported; keep channel reservations until release is supported by actual clear/physical quiescence or conservative bound. Already dispatched attack pulses cannot be retroactively revoked. Emergency control can override future outputs but cannot falsify already in-flight effects.

**Existing `ActionLifecycle` owns primitive effect commands bound to its current one-owner Intent.** A future owner-approved extension must make each per-channel primitive's source Intent and currentness separately attestable, while allowing a frame to aggregate independently admissible commands. The exact relationship between a frame/episode, one-or-several Intent owner snapshots and individually supervised primitive effects is an **open owner API choice**. Do not silently recast an atomic `ActionLifecycle` as a compound action; test causal association and whether a composite frame record is truly needed. Keep `ActionSupervisor` actual outcome and deadline semantics unchanged until owner-reviewed.

### 12.5 New negative tests (contract A expansion)

- **A-15:** same issuer + multiple channels can be proposed but no independent issuer, no channel without real scoped authority.
- **A-16:** `move + jump + attack` is admitted only with a valid capability map, dependency checks, source freshness and bounded dispatch window; unsupported target/range/grounding fails closed.
- **A-17:** conflicting same-channel controls (`forward` vs `backward`, two camera owners, `attack` vs `use` if incompatible) never produce contradictory live output.
- **A-18:** a held movement input continues/clears according to an explicit lease and real ACK; jump/attack pulses have event identity and no replay on retries or Plan changes.
- **A-19:** frame dispatched through several native calls is **not** reported as same-tick atomic without separate evidence; partial execution, unknown attack result, and physical settling cannot be normalized to full success.
- **A-20:** a new urgent L0 collision-avoidance proposal may preempt conflicting future channel output without altering already issued receipts or bypassing the physical issuer.

### 12.6 Implementation sequencing and review questions

Keep current S49 sequential MOVE route untouched for compatibility. First add **offline source-bound control-frame decoding and collision/authority tests**, with a synthetic WorldBody capability matrix. Only later stage opt-in real World tests of individual controls, simple compatible pairs, and finally movement+jump+attack with independently recorded native/tick outcomes. These are separate features and grants under S #537, not part of this documentation write.

**Still to resolve before DESIGN_ACCEPTED:** (a) model/registry for **multiple independently live body-directed IntentCommitment owners** and validation across S49 without widening permission; (b) can the frame be a transient `ExecutionBinding`/existing adapter structure instead of another owner; (c) exact per-Intent/per-Action vs frame causal mapping; (d) body-specific control/lease and native timing evidence; (e) safe quiescence/abort for partially dispatched frames. There is **no mandatory single global physical Intent**. This section does not mark A accepted.

### 12.7 Multiple-Intent examples and guarded compatibility

- Intent `move_to_cover` can remain current while Intent `jump_obstacle` requests a time-limited jump; both may produce **one compatible ControlFrame** through one issuer if source/physics/dependency checks succeed. Neither must be renamed or fused into a global Intent.
- Intent `attack_threat` can also remain current while locomotion and jump are active; the attack pulse requires its own current authority, target/range/aim/cooldown checks. The composite frame records **which source Intent justified each channel**; shared causal outcomes may be linked to several but are not double-counted as independent successes.
- Intent `eat_food` can stay committed but **temporarily unrunnable** while hand-use conflicts with `attack_threat`. It can be deferred/suspended without treating its Goal as invalid or forcibly changing the other Intent.
- An emergency L0 Intent/viability guard can override specific competing **channels**, not necessarily revoke all other Intents. Actual cancellation/clear evidence and in-flight outcomes remain independently necessary.

**Architectural correction:** the global invariant is **single authoritative body-issuer per controlled WorldBody**, together with bounded concurrent Intent owners and channel-level arbitration. In general, `Intent count != cognitive slot count != concurrently issued control count != issuer count`. The existing S49 implementation is a narrower serial special case and does not establish a global one-Intent invariant.

---

## 13. A resolution proposal — minimal owner binding and phased acceptance (2026-11-05)

> **PROPOSED / OWNER S #537 REVIEW REQUIRED / NOT DESIGN_ACCEPTED.** Resolve the four review choices from §10 and the additional frame questions from §12.6 conservatively. This is docs-only: no additional authority, real World, model, Action or main change.

### A-R1 — Slot-local cognition is capacity, not a physical Intent owner

A slot is a bounded runtime binding to a cognitive task: task reference, slot instance/generation, current source, deadline and compute admission. Goal, Question, durable Commitment and memories remain at their existing semantic owners. **Do not create an independent IntentCommitment per slot by default.** If a real task demands independent commitment transitions that existing owners cannot express, require Grand Null and owner review; that owner still cannot issue physical Actions.

Slot SUSPEND_REQUESTED fences new output promotion; SUSPENDED does not establish that an LLM/GPU process stopped, a physical Action was cancelled, or its control inputs cleared. Resume requires fresh generation/source and actual resource admission. A Goal surviving restart cannot revive an old runtime slot or in-memory IntentCommitment.

### A-R2 — S49 validates live physical owners, not matching IDs

**A0/A1:** preserve the current one Current Intent per existing S49 IntentCommitment, SkillExecution.start, ActionLifecycle.propose and one open physical primitive guard.

**Future multi-Intent:** multiple independent body-directed commitments may be live, but only owner-created/accepted references from the legitimate S runtime context can bind them to admission. Candidate references require same World/session/body, owner instance and current commitment revision, live Intent ID, source generation, exact capability scope, issuer principal/grant and expiry. **Matching text IDs, user-created owner instances and authority strings are not evidence of legitimacy.** Each effect must validate its own real owner/currentness and scope. Today's single-owner Skill/Action seam must not be bypassed to accept future multi-Intent frames; defer additional effects until a reviewed extension exists.

**Grand Null default:** reuse S49 authority, binding/trace and S14/S15/S16 evidence. No durable PhysicalAdmissionRecord, universal owner registry or second issuer by default. A transient decision-epoch join may group validated references but cannot authorize itself. If existing ExecutionBinding is absent or insufficient, identify exact missing information before creating a new owner.

### A-R3 — Version and reconsideration scopes

Fence future admissions independently on (a) physical context: self instance, world session, body actor, source/native sequence, issuer and scoped grant; and (b) cognitive context: slot instance/generation where applicable, genuine live Intent owner/revision, plan ID/revision, and eventually channel command/lease generation. These are **local generations**, not one global counter. Reject prior-session, stale model output, expired Plan or foreign owner.

Plan revisions record a trigger, predecessor and new future method. They **do not** automatically RELEASE and recommit the same Intent; a material commitment change uses the existing REQUEST_RECONSIDERATION then CONTINUE/RELEASE events with separate provenance. New Plans may not broaden the live Intent's permitted Action scope. Already issued Action history cannot be retrospectively altered.

### A-R4 — Channel conflicts, settling and partial dispatch

**Current:** sequential S49, single in-flight Action. Multiple goals/Intents can remain advisory without implying same-tick physical concurrency.

**Future ControlFrame:** S49 alone validates an exact per-channel capability/conflict map, owner-scoped authority, cross-channel dependencies, bounded control leases and deadlines. Reserve compatible resources at the one issuer before dispatch. A frame is a source/correlation/admission envelope, **not automatically one atomic ActionLifecycle**. Record which channel effects were issued/ACKed/cleared and what each independently observed; any failed/UNKNOWN part forbids a frame-wide success claim. Discrete ATTACK-like pulses are not replayed after uncertainty.

Action OUTCOME, S15 clear, input release and post-clear physical settling are distinct. Keep conflicting resources unavailable until sufficient same-session original clear/input/settling evidence, or conservatively UNKNOWN. A fixed eight-tick sample is not universal proof of quiescence. L0 emergency may fence new conflicting output and ask the sole issuer for supported stop/clear, but cannot retroactively cancel a pulse or assert physical stoppage without evidence.

### A-R5 — Admission order

1. Read current World/session/body and qualified source, then require a valid observation/currentness window.
2. Validate producer generation, live Intent owner from authentic S context, Plan revision, required capability and bounded deadline.
3. Validate exact physical issuer principal, scoped grant and each effect's actual channel/resources; reject untrusted authority strings.
4. Validate current Skill/Action lifecycle association and existing open Action/lease/settling conflicts; a proposed ControlFrame cannot override current S49's single-Action rule.
5. If invalid: DENY without issue. If temporarily unavailable/UNKNOWN: DEFER or fail closed, preserving original unresolved evidence and never inventing success.
6. At the existing issuer only, reserve and issue admitted effects via established S49/S14/S15/S16; supervise separately to OUTCOME/TIMEOUT/UNKNOWN, then release resources on actual clear/settling evidence.

This is a **contract algorithm sketch**, not an executable API.

### Extra negative tests (A-21–A-30)

| ID | Negative control | Required behavior |
| --- | --- | --- |
| A-21 | L2 slot constructs same textual Intent ID as S49 | No physical authority |
| A-22 | Old slot generation or another World session | No new issuance |
| A-23 | New Plan with unchanged live Intent | Future method changes without silent Intent replacement |
| A-24 | Two live candidates with existing single-owner S49 | Second deferred; no forged composite owner |
| A-25 | S15 clear / S16 OUTCOME yet post-clear motion continues | Physical resource not declared quiescent |
| A-26 | One channel issued, another failed/unknown | No frame-wide success; per-effect provenance |
| A-27 | Logical L2 cancellation but backend still busy | New output fenced; resources not falsely released |
| A-28 | Emergency L0 conflicts with in-flight pulse/held control | Fence future issue; explicit stop/clear evidence |
| A-29 | Fabricated authority or independently constructed same-ID owner | Reject before Action admission |
| A-30 | Expired control lease, capability map or unsettled input | No conflicting new issue |

### Owner handoff and acceptance

- **A-D0 DESIGN:** review R1–R5 and A-01–A-30 against actual S49 owner, executable Intent/Skill/Action contracts and DEV evidence; mark A DESIGN_ACCEPTED only after S owner agreement. Physical concurrency need **not** be implemented to accept an architectural contract.
- **A-I0 OFFLINE:** validate owner/source/generation rejection and Plan/suspension semantics without a World or new physical Action.
- **A-I1 SERIAL PRODUCT:** attach multiple cognitive Goal/Intent candidates to the unchanged single-owner S49 sequential adapter; report accepted/deferred candidates and next-epoch outcomes.
- **A-I2 FUTURE:** review multi-live body-directed owner representation and per-channel primitive mapping; verify offline frames before any opt-in DEV World; never infer atomic same-tick operation.

**Safety stop:** when live owner/currentness or quiescence cannot be established, stay on the existing sequential S49 path. Contract A does not approve Memory/Learning updates, energy debits, real-world grants or qualification claims.

---

## 14. Owner-identity admission API review — same-ID collision and issuance boundary (2026-11-06)

> **HISTORICAL API DESIGN EXPLORATION — SUPERSEDED IN OWNERSHIP MODEL BY §15 / S #537 OWNER REVIEW REQUIRED / NO EXECUTABLE CHANGE.** The multiple-independent-owner model explored here is *not* the selected v0.5 target. Same-ID tests remain valuable as cross-Self or forged-object negative controls. This section reconciles §13 with executable `src/relay_self/{intent,skill,action,action_supervision}.py` on the current `main`. It neither claims that S49 has a multi-Intent owner registry nor certifies real physical concurrency.

### 14.1 Code-derived gap that must not be papered over

Observed API facts (read from the current owner code, not inferred from a future implementation):

1. `IntentCommitment.current_intent` derives a fresh immutable `CurrentIntent` from owner-local events. Its `intent_id` uniqueness is **only within one owner lifetime**; there is currently no owner-instance identifier or global generation token in the public value.
2. `SkillExecution.start(..., intent_commitment=owner)` requires an actual current intent and stores **only the resulting textual `intent_id`**. The returned immutable Skill has `execution_id`, `skill_id`, `intent_id` and its own snapshot lineage; it does **not** carry an immutable reference to the originating Intent owner.
3. `ActionLifecycle.propose(..., skill_execution=skill, intent_commitment=owner)` rejects non-current/non-STARTED Skill snapshots, requires a current Intent and checks `skill.intent_id == owner.current_intent.intent_id`. It does **not** establish the object identity of the owner used at Skill start.
4. `ActionLifecycle.authorize(... authority: str)` records authority input but does not authenticate the external principal/grant. `ActionSupervisor.issue` retains a single Action lifecycle under `action_id` but is **not** the issuer's cross-owner permission registry.
5. These lifecycle libraries are not in themselves a secure physical dispatcher. The existing S49/adapter context remains responsible for trustworthy owner binding, scoped physical grants, source/currentness, resource exclusion and real native effects.

**Concrete collision:** independent owner A and owner B may both legally commit an `intent_id="eat"` in their separate lifetimes. `SkillExecution.start(owner=A)` followed by `ActionLifecycle.propose(skill_from_A, owner=B)` can satisfy the present *text equality* check if the Skill is current and STARTED. It is therefore unsafe to treat the current low-level proposal seam as a cross-owner provenance proof. The initial S49 single-owner path avoids needing to validate arbitrary owners, but a future multi-owner path **must introduce a trusted binding check before calling these APIs or strengthen their supported owner seam under S review**.

### 14.2 A-S49-1: proposed typed adapter boundary (illustrative, **not** current Python symbols)

```python
# Conceptual shapes, NOT imports or executable API.
@dataclass(frozen=True)
class ProposedEffect:
    source_ref: NativeObservationRef       # world/session/native generation
    producer_task_ref: TaskGeneration | None
    plan_ref: PlanGeneration | None
    intent_hint: str | None                 # advisory; never a capability
    required_capability: BodyCapability
    command: PrimitiveRequest              # channel, target, bounded duration
    requested_deadline: Deadline

# S49-private, non-serializable, never constructed by a model/slot:
@dataclass(frozen=True)
class LiveOwnerBinding:
    s49_runtime_identity: RuntimeIdentity
    world_session: WorldSession
    physical_body: BodyIdentity
    owner_handle: PrivateOwnerHandle        # resolves to the exact trusted Python owner
    owner_event_revision: int               # local history revision, NOT global truth
    current_intent_id: str
    grant_scope: PhysicalGrantScope         # independently checked at S49 admission
    source_generation: SourceGeneration

def s49_admit_effect(
    proposal: ProposedEffect,
    *,
    context: S49RuntimeContext,              # authentic in-process owner, not model input
) -> AdmissionResult:                       # ADMIT / DEFER / DENY
    ...
```

Required validation (performed **inside** the existing S49 runtime, not by a free-standing cognitive caller):

- Resolve owner from the S49 **trusted private allow-list / local owner context**. In current single-owner mode this is the exact already-known `IntentCommitment` Python object; no public registration API is needed. A future bounded multi-owner table, if needed, belongs *inside the same S runtime*, with registration only from its trusted owner setup path. Reject user/model-created owner objects even if their fields are identical.
- Check owner **object identity / privately held handle**, current active Intent, owner-local event revision, correct actor/world/session and current physical grant. `id(owner)` or a copied string is not a durable capability; a process restart invalidates every private handle. Derive event revision from the actual owner state (for example current event count); do not trust an unverified caller-supplied integer.
- Validate the proposal's source and Plan/slot generations against live currentness and reconcile body capability with the **authoritative** WorldBody/adapter view, not SelfBody belief. Binding to a slot is optional; a legitimate urgent L0 may run without creating a persistent cognitive slot.
- The admission response retains the **same verified owner instance** through Skill start, Action proposal, and scoped authorization. The S context keeps transient per-Skill/Action causal association sufficient to reject a later same-text-ID substitution. This is a local correlation function, **not** a second issuer or independent durable semantics owner.
- If a link cannot be verified, reject/defer the new effect. Neither `ActionLifecycle.propose` success nor a matching `authority` string elevates an invalid proposal.

**Implementation choice:** first implement an S49-local `assert_bound_owner(skill, trusted_owner, source)` or equivalent guard at the adapter seam, **before** modifying immutable Skill/Action contracts. If that guard cannot retain provenance safely across legitimately deferred execution, S owner must explicitly decide whether to extend `SkillExecution` with an immutable owner-generation binding and update `ActionLifecycle.propose` correspondingly. This is a tested alternative, not permission to add a global Intent registry or untrusted caller-selected owner ID.

### 14.3 A-S49-2: admission lifecycle and TOCTOU fence

```text
cognitive proposal (advisory)
  -> resolve owner in S49 local trusted context
  -> validate actual current Intent + owner revision + session
  -> source/capability/Plan/lease/grant/deadline preflight
  -> within S49's one serialized admission boundary:
        recheck all mutable owner/source/grant preconditions
        SkillExecution.start(actual_live_owner)
        ActionLifecycle.propose(actual_live_skill, same_owner)
        ActionLifecycle.authorize(real S49-scoped authority)
        ActionSupervisor.issue(current authorized lifecycle)
        native dispatch + source-bound follow-up (original S14/S15/S16)
  -> independent terminal Action evidence + input clear + settling
```

`AUTHORIZE` and `ISSUE` must not be split by an unguarded asynchronous gap in the current implementation. **Important gap:** today's `ActionLifecycle` supports `PROPOSED -> DENIED`, but after `AUTHORIZED` it only supports `ISSUED`; there is no general `AUTHORIZED -> CANCELLED` transition. A pre-issue source/grant loss cannot be falsely recorded as `OUTCOME`, `TIMEOUT`, or `UNKNOWN` (those require `ISSUED`). For current serial S49, preflight and final recheck should occur before authorization, and the owner must preserve any incomplete authorized attempt as an unresolved/explicitly rejected admission record rather than invent a terminal physical result. **If a future async/partial issuance path requires cancellation of an authorized-but-unissued command, S review must define that lifecycle extension separately** with independent tests.

`ActionSupervisor` supervises issued primitives; a terminal Action receipt is not proof of input-clear or settled movement. Logical task suspension/release can fence future admissions without mutating already-issued Action history.

### 14.4 A-S49-3: future multi-Intent / ControlFrame mapping

A bounded `ControlFrame` is an **issuer-local correlation envelope** for proposed compatible channel requests. It is not a super-Intent, not itself a durable physical owner and not a substitute for the existing primitive lifecycle.

```text
Frame F:
  locomotion effect M -> verified owner A, Skill M, Action M, source SM
  attack effect H     -> verified owner B, Skill H, Action H, source SH
  orientation effect O-> verified owner B (or independently authorized C)
  frame lease / conflict map / per-effect outcome and native order
```

Each emitted primitive carries exactly one **primary legitimate** `SkillExecution` and `ActionLifecycle` association under today's one-parent primitive schema; **supporting Goals/Intents** can be cross-referenced for cognitive explanation, never forged as a composite primary physical parent. When several Intents jointly propose an inseparable physical effect, S must explicitly arbitrate one primary authorized execution association or define a future reviewed multi-parent API; it cannot concatenate textual Intent IDs.

Pre-dispatch frame validation is all-or-nothing for its **planned** effect set. After the first native output, actual dispatch is not assumed atomic: record per-effect `NOT_SENT / SENT / ACKED / OUTCOME / UNKNOWN` distinctions and physical clear/settling separately. A failed later channel cannot erase already-sent commands. Do not replay uncertain pulses. Actual shared effects (e.g. damage while moving) may be causally linked to multiple proposals but must not be counted twice as independent physical successes.

### 14.5 A-31–A-40 executable regression plan (future S owner, not yet run)

| ID | Situation | Required behavior |
| --- | --- | --- |
| A-31 | Two `IntentCommitment` objects A/B both `intent_id="eat"`; Skill starts from A, proposal attempts binding to B | Low-level equality gap reproduced in a *controlled offline negative setup*; S49 adapter rejects cross-owner association before physical issue |
| A-32 | A's `reconsider(CONTINUE)` advances owner events while Intent ID remains equal | Old binding rejected until a fresh S49-owned bind/recheck |
| A-33 | B presents copied owner handle, `id(owner)` or authority string | Not admitted; only S49's privately held in-process owner identity is trusted |
| A-34 | Different `world_session`, actor or expired grant with otherwise identical fields | No issue, old evidence preserved |
| A-35 | Plan revision changes route while live Intent stays current | No hidden Intent release/recommit; stale prior Plan cannot issue |
| A-36 | Grant/source expires after validation but before authorization | Final recheck denies/defer without creating AUTHORIZED/ISSUED Action |
| A-37 | Source expires after AUTHORIZE but before ISSUE | Explicitly unresolved boundary; never invent terminal physical evidence; extension required if this path is permitted |
| A-38 | One frame proposed with MOVE and ATTACK from different legitimate owners while current S49 supports one open Action | No concurrent issue; defer incompatible/future effects and retain provenance |
| A-39 | Partially native-dispatched frame then failure/UNKNOWN | Preserve sent child effects, no blanket success/cancel/replay |
| A-40 | Owner process restart, stale slot completion or expired held-control lease | Invalid previous handles and no new physical Action until fresh admission |

**Owner acceptance criteria:** S #537 checks the exact mismatch with its concrete adapter, chooses the minimal private owner-binding implementation (or justifies a stronger Skill/Action seam), confirms existing command/clear/settling behavior, and approves A-31–A-40. Only then mark the **Contract A API design** `DESIGN_ACCEPTED`; actual offline code and real World claims are separate milestones. S review cannot be replaced by this documentation commit.

---

## 15. One Self, one Intent ownership scope, multiple live Intents (user-selected, 2026-11-06)

> **USER-ADOPTED DESIGN DIRECTION / DETAILS S #537 OWNER REVIEW REQUIRED / NOT IMPLEMENTED.** This is a correction to §13–14's proposed *multiple independent physical Intent owners inside one Self*. It does not retroactively alter current main, real World grants or the tested S49 serial path. Where §1, §13, or §14 speaks of several independent body-directed Intent owners **within the same Self**, read those passages as an earlier design alternative, not the preferred architecture.

### 15.1 Terminology and ownership invariant

**At the conceptual level, the owner of the Self's Intent commitments is that Self instance.** In this sentence "Self" means the *identity/scope of one continuously operating agent*, not a newly invented central reasoning controller, database for all memories, or a second Action issuer. MySelf/SelfWorld/SelfBody may propose Goals or knowledge; they do not individually own physical commitment authority.

A single Self may hold many independently current, deferred or reconsidering Intent records. Their lifecycles are **per Intent**; ownership scope is **one Self**. Thus:

```text
Self A (one logical Intent ownership scope)
    Intent[EVADE]       CURRENT / ACTIVE candidate
    Intent[EAT]         CURRENT / DEFERRED physically
    Intent[ATTACK]      CURRENT / competing candidate
    Intent[REST]        CURRENT / pending condition
        |
        |  bounded, source-qualified proposals / arbitration
        v
    one existing S49 physical Action issuer
        |
    original Skill -> Action -> WorldBody -> sourced outcomes

Self B (separate ownership scope) -- cannot authorize Self A's body
```

Here `Intent[EAT]` is an example label; a particular commitment has its own **unique runtime identity**, and several commitments of the *same type* may exist only if the Self's commitment rules permit them. A retained Intent does not consume a cognitive slot or imply a concurrently active physical Action.

This preserves the established v0.5 principle that **Self is a process, not a centralized independent controller**. The S-owned executable subsystem implements the *Self-scoped Intent lifecycle*; it is not ontologically a second Self.

### 15.2 Proposed minimal executable representation

**Target contract (not yet executable):** one Self-scoped Intent-management boundary with `0..N` live Intent records, each with its own objective, event/provenance history, state, local revision and reconsideration request/decision. It must prevent silent replacement of any record. Use a bounded collection inside the existing S runtime, **not** one independent globally authoritative Owner per Goal, slot or Intent.

Grand Null migration:
- First preserve existing `IntentCommitment`, which implements **one Current Intent per object** and must not be falsely described as already multi-Intent. A Self-local facade/collection can *reuse* multiple existing lifecycle objects as internal record mechanisms while exposing **one Self-bound authority scope**. Distinguish an internal lifecycle object from an autonomous semantic/physical Owner.
- The alternative is extending the existing Intent owner itself to hold a keyed collection and per-Intent transitions; choose it only if the wrapper approach adds non-reconstructible state or problematic lifecycle coupling. Do not rewrite a mature single-current API just to improve names.
- No global registry, per-slot Intent owner, per-Goal owner or extra physical dispatcher. Cross-epoch durability and restart reconstruction require their own B/owner contract; no implicit persistence claim here.

Candidate API vocabulary (conceptual, not Python imports):

```text
SelfIntentScope(self_instance, world_session, physical_body):
  commit(intent_key, objective, provenance) -> intent_revision
  request_reconsideration(intent_key, trigger, provenance)
  reconsider(intent_key, CONTINUE | RELEASE, provenance)
  close(intent_key, COMPLETED | FAILED | INVALIDATED, provenance)
  current(intent_key) -> SelfBoundIntentSnapshot | None
  current_all() -> bounded snapshots (for arbitration only)
  validate_for_execution(intent_key, expected_revision, source, grant)
       -> trusted, S49-private binding | DEFER | DENY
```

The scope is associated with **one Self**. `current_all()` does not authorize physical Actions. Each new Action requires S49 source/capability/currentness/resource/permission checks and still binds through the existing Skill/Action owner interface for the selected primary Intent. The existing S49 one-current-intent serial adapter remains an explicit compatibility stage.

### 15.3 Identity and same-ID collision after this choice

- **Within one Self:** allocate unique commitment instance IDs in its Intent scope and reject duplicates/reuse for that scope's declared lifetime. Intent *kind* (`EAT`, `ATTACK`) and *instance ID* are separate. There is no need to rely on random UUID collision probabilities for correctness if uniqueness is checked.
- **Between different Self instances or Worlds:** the same textual Intent ID must never establish cross-Self physical authority. S49 validates `self_instance / body / session`, trusted local Intent scope membership, record revision and actual scoped grant. Identical text is not a capability.
- **Within a single Self during migration:** internal `IntentCommitment` objects may be used for implementation convenience, but a caller cannot directly substitute a fabricated object of the same `intent_id` into `SkillExecution.start` / `ActionLifecycle.propose` and obtain an authorized S49 Action. The trusted Self-scoped facade selects the real internal record.
- Consequently old §14's "multiple independent Owner A/B *inside the same Self*" is **not an ordinary runtime assumption**. Retain its same-ID test as an **adversarial substitution test**, and test two independent Self scopes separately.

### 15.4 Intent vs slot vs physical execution

A Self may keep `EAT` and `ATTACK` Intent commitments current while `ATTACK` is selected for execution. `EAT` is *deferred for physical effects*, not necessarily released or suspended as a committed objective. If `ATTACK` resolves and food is still relevant, the same EAT commitment can be considered without inventing a new owner.

A slot is time-limited **cognitive compute capacity** for analyzing those commitments. It is neither the owner of Intent identity nor a permission to issue Actions. Intent scope and slot lifecycle are orthogonal.

**Physical action authority remains S49's**, with original S14/S15/S16/Supervisor handling. No Self API, memory update, Plan revision or L2 recommendation independently grants a native Action. Multi-channel ControlFrame remains future opt-in under the same issuer.

### 15.5 Owner-review tests updated to this direction

| ID | Scenario | Required result |
| --- | --- | --- |
| A-41 | One Self retains EAT + ATTACK while only one physical Action is active | Both commitments remain identifiable; original S49 single-Action issuance unchanged |
| A-42 | EAT deferred during ATTACK, then re-evaluated at a new source epoch | Retained EAT may resume after genuine revalidation; no hidden recommit |
| A-43 | Same `intent_key`/instance ID committed twice in one Self scope | Duplicate rejected before any physical binding |
| A-44 | Two Self scopes use identical textual Intent ID | Cannot cross-bind World/body/grant or issue for the other Self |
| A-45 | Forged internal `IntentCommitment` object with copied ID inside one Self | S49 rejects unless bound to trusted record in its Self scope |
| A-46 | Independent Goal/Plan/slot task ends while Self Intent is current | Intent unaffected unless explicit legitimate reconsideration/closure |
| A-47 | Current serial adapter receives multiple simultaneously current Intent candidates | Select/defer via same Self scope; no fabricated multi-Action capability |
| A-48 | Self/session restart while an internal record pointer or grant was retained | Old pointer/authority invalid; no implicit resurrection of active physical issue |

**Owner-review decision still required:** select the smallest S-owned Self-scoped lifecycle representation and its trust boundary; keep existing executable contracts unchanged until focused offline negative tests pass. This user-selected conceptual ownership decision **does not mark all Contract A API details DESIGN_ACCEPTED**.

---

## 16. Intent signal dynamics and outcome feedback (user-proposed refinement, 2026-11-06)

> **DESIGN PROPOSAL CONSISTENT WITH USER DIRECTION / S #537 OWNER REVIEW REQUIRED / NOT IMPLEMENTED.** A single Self's concurrent Intents may each have an independently changing **signal strength** and lifecycle. World/WorldBody effects supply externally owned physical consequences; their source-qualified observation can change which Intent is most relevant next. This is a closed-loop scheduling hypothesis, not a claim that the physics guarantees safe arbitration or that any convergence or learning has been demonstrated.

### 16.1 Three different notions: commitment, activation, physical eligibility

Do **not** collapse the following into a single priority number or state enum:

1. **Commitment lifecycle (per Intent):** whether this Self is still committed to the objective. Reuse the executable `IntentCommitment` semantics initially: `COMMITTED`, explicit `RECONSIDERATION_REQUESTED` then `CONTINUE / RELEASE`, and terminal `COMPLETED / FAILED / INVALIDATED`. A newly committed instance must not silently replace an older one. This layer is Self-scoped as in §15.
2. **Signal/activation (per Intent, time-varying):** how strongly currently observed or predicted conditions call for attention/action *given this Self's context*. The initial product can expose a bounded, documented, source-qualified `strength`, accompanied by `confidence/UNKNOWN`, urgency/deadline and triggering observations. The value is **not** necessarily constant during one commitment and is **not itself a physical permission**.
3. **Execution eligibility and scheduling:** whether the Intent is physically runnable *now*, temporarily deferred/blocked, or associated with an already executing Skill/Action. It is a source- and resource-dependent **derived view**, not automatic release/recommit of the Intent. `EAT` may stay committed at high strength while `ATTACK` temporarily occupies an incompatible input channel.

A high activation signal cannot override viability constraints, actual WorldBody capability, authorized grant, current source, incompatible control channels, protected L0 response, or required clear/settling. Unknown signal values must not be silently converted to zero or maximum.

### 16.2 Minimal signal snapshot (conceptual API, no new semantic owner)

```text
SelfIntentView {
  self_instance, intent_instance_id, intent_kind, objective,
  commitment_revision, commitment_state,  # owned by existing S lifecycle
  activation: {
    strength: bounded score | UNKNOWN,
    confidence: bounded estimate | UNKNOWN,
    evidence_refs: [...], observed_source_generation,
    computed_at, valid_until,
    urgency_or_deadline: optional source-qualified data
  },
  execution_view: {
    runnable | deferred | blocked | in_flight | unknown,
    blocker_reason, next_revalidate_source,
    skill_or_action_refs: [...]
  }
}
```

This is an **illustrative read model**. An epoch-local activation view can be derived from SelfWorld/SelfBody/MySelf evidence and does not justify a new permanent signal owner, global store or runtime central controller. Only the original S owner updates the commitment lifecycle; only S49 admits physical commands. The activation `strength` is relative to the chosen model and context; no universal inter-Intent calibration is asserted. Do not label a scalar as measured bodily pressure if it is inferred from degraded motor output or a WorldBody-private state.

### 16.3 Runtime regulation without a prewritten universal priority order

1. **Observe:** collect current source-qualified World, body and Self model readings (including stale/missing/UNKNOWN), plus previous issued Action receipts and *separate* observed effects.
2. **Update activation:** estimate Intent-specific need/salience, urgency, prediction error and confidence. A threat can strengthen `EVADE/ATTACK`; hunger strengthens `EAT`; impaired motor output can strengthen `REST`. Signals can coexist and need not sum to 1.
3. **Filter admissibility:** check hard safety/viability limits, legitimate physical S49 grant, real body capabilities, freshness, actor/session, channel conflict and in-flight/settling. If `EAT` is blocked by ongoing `ATTACK`, defer **its execution** without erasing the EAT commitment or forcing its signal to zero.
4. **Arbitrate bounded eligible requests:** urgency, activation, deadline, age of deferral, expected value/uncertainty and locally justified hysteresis can inform selection, sequencing or compatible composition; do not hard-code that the largest `strength` always wins. Use protected emergency L0 when needed and preserve WAIT/DEFER/ABSTAIN.
5. **Issue only through S49:** selected request does not yet imply `Action` authorization or WorldBody effect; one issuer performs the original grant/skill/action validation.
6. **Update from outcomes:** the next epoch sees independently observed result, uncertainty, body constraints and resource cost; revise activation, eligibility and Plan. A real EAT success can lower hunger-related pressure; a failed attack, unchanged danger or missing evidence may leave threat pressure high. Only explicit justified commitment events complete, invalidate or release an Intent.

A lower signal **does not itself mean a completed Intent**; an ACTION OUTCOME **does not itself mean success of the Goal**. By contrast, a credible terminal Goal outcome may justify closing the commitment under its actual owner. No L2/L1/L0 parameter learning, Memory/Habit write or value-gradient update is approved by this regulation design; those are Contract C responsibilities.

### 16.4 Example: one Self with ATTACK and EAT

```text
Epoch N: observed threat and hunger
  EAT    COMMITTED, signal substantial, physically DEFERRED (hand/attack conflict)
  ATTACK COMMITTED, signal urgent, physically ELIGIBLE
  -> S49 admits authorized ATTACK; record call / hit / damage / death separately

Epoch N+1: verified threat gone (if actually observed)
  ATTACK -> only if justified: COMPLETED, or signal decreases while retained
  EAT    -> remains same committed instance; eligibility recalculated
  -> S49 may authorize EAT, not infer it from a previous attack receipt

Epoch N+2: if food consumption and hunger change are actually observed
  EAT signal may fall; complete only when objective-specific conditions met
  REST or EXPLORE can become eligible according to fresh body/world evidence
```

This is *feedback-driven competition*, not a deterministic promise that WorldBody automatically resolves controller conflicts. Conflicting simultaneous commands on one actuator must still be rejected/sequenced by S49 **before** WorldBody dispatch; the World cannot be asked to repair a missing grant, erase an irreversible attack pulse, or retroactively solve contradictory controls. Equally, coupled feedback can oscillate or fail to converge if observations are delayed, resources depleted or goals incompatible.

### 16.5 Stability and limits

- Avoid winner flip-flop: use bounded hysteresis, minimum justified hold or cooldown **only when safe**; never delay urgent L0 or preserve an invalid commitment merely because its signal was strong.
- Avoid starvation: record age, reason and outcome of deferral, then reconsider or escalate when admissible. Do not automatically grant execution solely because an Intent waited.
- Avoid positive feedback based on self-reported success: distinguish requested Action, S15/ACK, S16 physical effect and Goal-level criteria; source and uncertainty remain visible.
- Keep physical rules outside Self. World/WorldBody owns hunger/fatigue/recovery/damage, and Self changes its estimates and behavioral choice, never the World transition coefficients.
- Dynamic signal evaluation and short-term arbitration belong to **Contract A**. Learning the signal-update function, outcome preferences, retention or crystallization belongs to **Contract C**; projecting the signal through Persistent Cognition and three models belongs to **Contract B**.

### 16.6 Additional design negative controls (A-49–A-58)

| ID | Input | Expected behavior |
| --- | --- | --- |
| A-49 | Strong EAT signal but attack occupies incompatible physical channel | EAT stays committed, execution deferred; no illegal EAT issue |
| A-50 | EAT strength decreases without food/hunger effect evidence | No automatic `COMPLETED` |
| A-51 | ATTACK call reports applied while target death unobserved | Goal not declared complete and threat signal not forcibly zeroed |
| A-52 | Missing/stale SelfBody activation input | Explicit UNKNOWN/DEFER; no fabricated zero pressure |
| A-53 | Weak urgent L0 score but hard safety guard requires action | Safety/admission boundary dominates ordinary score |
| A-54 | High activation with forged grant or stale source | No physical issue |
| A-55 | ATTACK/EAT alternate every epoch under noisy readings | Bounded hysteresis/deferral trace; no unsafe permanent latch |
| A-56 | Intent deferred for a long duration | Commitment preserved or legitimately reconsidered; no automatic Action grant |
| A-57 | Real WorldBody recovery or hunger improvement after valid action | Update signal from fresh evidence; never modify World rules |
| A-58 | Slot suspended or Plan revised while EAT remains committed | No silent Intent release, owner reassignment or physical cancellation |

**Acceptance path:** S #537 reviews signal read-model ownership and temporal eligibility, checks existing Intent/Skill/Action/state APIs, and tests a small serial offline ATTACK/EAT/REST progression plus stale/false-success controls. Values and hysteresis thresholds are test fixtures until calibrated, not World truth. Keep Contract A `DESIGN_PROPOSED / OWNER_REVIEW_REQUIRED`; no product/runtime learning or real World authority is implied.

**User clarification (2026-11-06):** S49 prevents known direct command contradictions and invalid physical authority; it is not required to eliminate every unforeseen bodily interference. A standing Self-owned HOMEOSTASIS regulatory commitment can maintain Need pressures without monopolizing Current Intent or Action authority. The focused [Contract A homeostasis and imperfect-control annex](intent-homeostasis-regulation-v0.5.md) defines the minimal semantics, source-bound feedback and offline A-59–A-68 checks. This refines, rather than removes, the current one-issuer/one-in-flight-Action S49 implementation boundary.
