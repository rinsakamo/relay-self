# RelaySelf v0.5 — Contract A: Cognitive Intent Slots / Physical Action Authority

> **Status: DETAILED DESIGN CANDIDATE / OWNER REVIEW REQUIRED / NOT EXECUTABLE.**
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

**Still to resolve before DESIGN_ACCEPTED:** (a) model/registry for **multiple independently live body-directed IntentCommitment owners** and validation across S49 without widening permission; (b) can the frame be a transient `ExecutionBinding`/existing adapter structure instead of another owner; (c) exact per-Intent/per-Action vs frame causal mapping; (d) body-specific control/lease and native timing evidence; (e) safe quiescence/abort for partially dispatched frames. There is **no mandatory single global physical Intent**. This section does not mark A accepted. This section does not mark A accepted.

### 12.7 Multiple-Intent examples and guarded compatibility

- Intent `move_to_cover` can remain current while Intent `jump_obstacle` requests a time-limited jump; both may produce **one compatible ControlFrame** through one issuer if source/physics/dependency checks succeed. Neither must be renamed or fused into a global Intent.
- Intent `attack_threat` can also remain current while locomotion and jump are active; the attack pulse requires its own current authority, target/range/aim/cooldown checks. The composite frame records **which source Intent justified each channel**; shared causal outcomes may be linked to several but are not double-counted as independent successes.
- Intent `eat_food` can stay committed but **temporarily unrunnable** while hand-use conflicts with `attack_threat`. It can be deferred/suspended without treating its Goal as invalid or forcibly changing the other Intent.
- An emergency L0 Intent/viability guard can override specific competing **channels**, not necessarily revoke all other Intents. Actual cancellation/clear evidence and in-flight outcomes remain independently necessary.

**Architectural correction:** the global invariant is **single authoritative body-issuer per controlled WorldBody**, together with bounded concurrent Intent owners and channel-level arbitration. In general, `Intent count != cognitive slot count != concurrently issued control count != issuer count`. The existing S49 implementation is a narrower serial special case and does not establish a global one-Intent invariant.
