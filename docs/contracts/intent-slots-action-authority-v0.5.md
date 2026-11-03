# RelaySelf v0.5 — Contract A: Cognitive Intent Slots / Physical Action Authority

> **Status: DETAILED DESIGN CANDIDATE / OWNER REVIEW REQUIRED / NOT EXECUTABLE.**
>
> Parent [#717](https://github.com/rinsakamo/relay-self/issues/717); review on [Draft PR #718](https://github.com/rinsakamo/relay-self/pull/718). This refines [Unified Architecture v0.5](../unified-architecture-v0.5.md), not `main` executable contracts. `main@4348a614900c1d0828581a8eec2c523ba5ae237f` is the audited baseline.
>
> **Authority boundary is fixed:** existing S #537 / S49 is the only Minecraft physical Action issuer. No model, cognitive slot, Plan, WB view, scheduler or newly invented Intent owner gains Action / Learning / Body-energy debit authority. This document does not approve real World, LLM/GPU, R/QUAL or V/SCIENCE runs.

## 1. Problem and design result

We need multiple independent or interdependent cognitive activities (L0/L1/L2) to pursue Needs/Goals/Questions and temporally construct Plans, *while keeping exactly one lawful physical Action execution boundary*.

The smallest compatible design uses **two explicitly distinct commitment scopes**, without requiring a second physical issuer:

1. **Cognitive Intent (slot scope)**: one active task commitment associated with a transient cognitive execution slot, or no Intent if the slot is only monitoring/reflexing a source. It may deliberate or propose plans/skills/actions but cannot authorize or issue physical effects.
2. **Execution Intent (physical owner scope)**: the existing `IntentCommitment` held by the sole physical execution route. At most one current physical execution commitment is admitted there. It covers a sufficiently bounded, meaningful objective, potentially composed from several Goals. Physical Skills/Actions are *always* grounded in this actual owner, not an arbitrarily selected slot owner.

**Slot scope is not a new ontology type of Goal.** The words `Cognitive Intent` and `Execution Intent` describe **use scope**, not automatically new durable semantic owners or new constructors. This contract does **not** change `IntentCommitment.current_intent` implementation; further executable scoping requires explicit S owner changes/tests.

```text
Persistent Goal A   Persistent Goal B   Question C
        \              /                  |
         \            /                   v
          value-conditioned Plan(s)     cognitive-only inquiry
                |                           |
       active/suspended cognitive slots [L0/L1/L2]
                |
       source/provenance-bound candidates (NO authority)
                |
       S49 sole-issuer physical admission / arbitration
                |  physical intent and execution binding
       existing IntentCommitment (one Current Intent)
                |
       SkillExecution.start (actual physical intent)
                |
       ActionLifecycle.propose + explicit authorize / deny
                |
       ActionSupervisor.issue -> S49 executor -> S15/S16/World outcome
```

The diagram describes a proposed connection, **not** integrated implementation. In existing S49 tests `escape-threat` is the fixed physical Current Intent; no experimental multi-goal plan change is already verified.

## 2. Distinct objects and relationships

| Concept | Scope / lifetime | May cause a physical issue directly? |
| --- | --- | --- |
| Need / Goal / Question / persistent Commitment | Owner-specific durable or transient cognition; may outlive all slots | No |
| Plan candidate / temporal Goal graph | Source/revision-scoped reasoning product; not necessarily persisted | No |
| Cognitive slot | Self-created bounded runtime work capacity; not a personality or semantic owner | No |
| Slot-local task / Cognitive Intent | At most one currently committed task per slot when needed; can be paused, reconsidered or released independently | No |
| Physical Execution Intent | Current commitment owned by original physical `IntentCommitment`; at most one per physical executor in initial design | Not by itself |
| SkillExecution | One started, immutable physical Intent association and lifecycle | No |
| Action proposal | One primitive requested effect, source and causal scope | No |
| Authorize / issue | Existing legitimate S49/S14-S16 owner seam; independent policy gate and one issuer | Yes, only after admission |

Multiple Goal or Question objects can be simultaneously *relevant* while zero, one or several **cognitive** slots are ACTIVE. There is no requirement to keep one heavyweight slot occupied per Goal. A slot may perform multiple successive tasks, but may not silently replace its committed task without the appropriate release/reconsideration event. A cognitive Goal graph may be a DAG rather than a fixed L2 > L1 > L0 hierarchy; dependency edges need explicit provenance and cannot create an Action grant.

### No accidental identity equivalence

For later API exploration, candidate binding identities should be explicitly scoped by:
- `self_instance / physical_body / world_session`;
- `slot_instance` plus `slot_generation`, if derived from a slot;
- `cognitive_intent_id` (if any), `physical_intent_id` **from the live physical owner**, not text supplied by a model;
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

- A Plan revision changes **how** current Goals are pursued; it does not necessarily change **what is committed**. A local phase failure, new affordance, safer route or timing change may replace a Plan/Skill while keeping the same physical Execution Intent.
- A new proposed Plan must not expand an Intent beyond its admissible meaning, authority or viability scope. Broad objective strings like "survive" are **not wildcard Action permission**. Source-grounded action applicability and actual grant scope remain necessary.
- If the goal/commitment's meaning, feasibility, authority or viability is materially challenged, request **reconsideration** with its own triggering source. Only the separate `CONTINUE` / `RELEASE` decision changes the commitment, or a valid terminal success/failure/invalidation closes it.
- New cognitive slots may create prospective work while old physical Action is still executing; their outputs are advisory until admitted at a source-current physical boundary. Do not retroactively alter an already issued command.
- Goal-level incompatibility (protect X vs destroy X), resource conflict (two operations need same input), and time-sliceable order (eat then attack) are distinct. Re-evaluation can choose composition, sequencing, deferral or escalation, with possible zero-action WAIT.

Example (conceptual): **Execution Intent:** deal with a nearby threat while preserving ability to recover. **Plan P1:** move away -> verify distance -> eat -> approach -> attack. **Plan P2:** attack -> confirm threat ended -> eat. Both are candidate plans for overlapping Goals, not unconditional recipes. Each phase is guarded by actual observed preconditions/outcome and may yield, replan, fail or ask for a new physical Intent. Minecraft command capability for movement+eating or attack+eating must be **empirically verified**, not inferred from Plan composition.

## 5. One physical issuer and admission sequence

**Mandatory physical path** (conceptual layers; the actual existing owners still execute their established interfaces):

1. Read the **current** source-qualified observation and actual physical owner state; record relevant WorldBody resources, deadline and uncertainty. Missing or stale inputs fail closed or yield UNKNOWN.
2. Form candidate bounded Plan/Skill/Action and any support from cognitive slots. L2 recommendations, value gradients and apparent Goal urgency are **not** grants.
3. Only the **existing S49 owner/adapter** decides whether to admit a candidate for physical execution based on the **actual live** `IntentCommitment`, actor/skill capability and source/currentness. It may choose none (WAIT), defer, or use an already tested cheap L0 path.
4. **Physical execution binding:** derive physical Intent association from the actual owner and record which cognitive Goal/Plan, if any, justified the proposal. Check bounded semantics and admission scope, not merely identical strings. The current `SkillExecution.start(...)` and `ActionLifecycle.propose(...)` must continue to use the physical owner instance; never feed an independent slot owner as a direct bypass.
5. Before issuance, check the authorized principal and grant's real scope, current source/epoch, actor, body capability, action resource reservation, deadlines, and exclusivity. `ActionLifecycle.authorize()` remains the **recorded lifecycle transition** and does not authenticate a fabricated `authority` string by itself. Avoid second issuers or independent authorizers minted by cognition.
6. Original S49-issued command passes existing S14/S15/S16 / ActionSupervisor processes. Final OUTCOME/UNKNOWN/TIMEOUT **and** source-bound consequence are passed to the next cognitive epoch as evidence; physical motion settling and control-clear must not be inferred from `OUTCOME` alone.

A possible transient **PhysicalAdmissionRecord** is a *typed, bounded source-and-owner join*, **not** a second authorizing owner: it might record `world/session, physical_intent_id, slot/plan generation, skill/action identity, admitted capability/resource scope, original grant/authorization source and expiry`. Exact fields need a local S owner Grand Null and tests; if existing `ExecutionBinding` and S49 traces suffice, **do not create a new record type**.

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

**Initial safe policy:** permit **one physically active effect transaction at a time per controlled WorldBody** through the existing S49 issuer. Cognitive parallelism continues; physical command concurrency is **deferred**. This policy avoids promising that simultaneous movement, use-item, attack and camera operations are compatible on Minecraft 1.21.8 or on an eventual different body.

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
- S49 physical Execution Intent stays committed through phase changes if its originally admitted bounded objective and authority remain valid.
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
- Movement and combat slots both request exclusive body control; independent IDs and apparent authority do not permit two physical issuances.
- One S49 owner chooses compatible sequencing or none; the other candidate is deferred or denied. No unqualified second issuer or fabricated "parallel" success.

## 8. Contract invariants (for later executable owner review)

| ID | Required invariant | Proposed negative control |
| --- | --- | --- |
| A-01 | Slot is transient cognitive capacity, never physical Action authority | L2-only slot tries direct issue |
| A-02 | Slot and physical owner Intent identity/lifetime differ | same textual ID, foreign owner |
| A-03 | No silent replacement of committed Intent | alternative Plan causes hidden COMMIT |
| A-04 | Local Plan/Skill revision need not break Intent | phase/route change without RELEASE |
| A-05 | Goal/Plan candidate carries bounded provenance/currentness | stale world/native seq or replay |
| A-06 | One physical issuer and required valid grant | second issuer, fake authority string |
| A-07 | Physical `SkillExecution` and `ActionLifecycle` use actual current physical owner | cognitive slot owner passed as Action parent |
| A-08 | Body resource exclusivity until qualified release; initial one in-flight transaction | same-time move + attack, post-S16 settling |
| A-09 | Slot suspension is not automatically Skill/Action cancellation | suspended L2 returns stale output |
| A-10 | In-flight issue closes via real evidence/deadline/UNKNOWN | RELEASE during MOVE; no STOP ACK |
| A-11 | Runtime budget/actual deadlines bound concurrency; emergency L0 remains available | L2 task saturates GPU/CPU or exceeds deadline |
| A-12 | Physical outcome is separate from commit/Plan success and learning | OUTCOME without effect, untrusted WB view |
| A-13 | Reconsideration trigger and CONTINUE/RELEASE carry distinct provenance | new affordance silently replaces intent |
| A-14 | Source-matched WorldBody/capability required for proposed actuation | phantom USE_ITEM or stale body capability |

## 9. Staged implementation path (owner S #537, not authorized by this document)

**A0 — Offline, read-only boundary:** create/derive source-bound cognitive candidate traces from fixed L0/L1/L2 slots; show slot/task/Intent versus physical-Intent separation and stale rejection; **0 new Action**. Reuse present S49 and existing intent/action contracts.

**A1 — Local physical-admission proof, still one physical action at a time:** at original S49 owner, validate candidate-to-physical `ExecutionBinding` association, source/epoch/deadline and actual grant scope. Test mismatch/fake authority/replay, consecutive plans under one physical Intent. Keep original MOVE-only behavior and no automatic learning.

**A2 — Cognitive scheduling and guarded Plan revisions:** preserve transient tasks, suspended/resumed cognitive work and Plan revision under unchanged physical Intent; enforce resource budgets. Add source-bound tests for protected L0 amid slow L2 and post-outcome physical settling/clear. No body-command expansion is implied.

**A3 — Physical capability expansion (separate grants):** only after body-specific Action primitive, grant semantics, control clear, physics, and outcome tracing exist for eating/attack, test composed Goal sequences. *Simultaneous* physical operations are a separate feature/qualification, **not** an A0–A2 completion gate.

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
