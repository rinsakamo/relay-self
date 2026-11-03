# RelaySelf v0.5 — Legacy/New Unification Gap Audit

> **Status: DESIGN AUDIT / NO EXECUTABLE AUTHORITY.** Parent: [#717](https://github.com/rinsakamo/relay-self/issues/717). Companion: [unified-architecture-v0.5.md](unified-architecture-v0.5.md). Audited baseline `main@4348a614900c1d0828581a8eec2c523ba5ae237f` (2026-11-03); newer PRs are **not merged into main** and are not treated as one integrated Self.

## 1. Audit rubric

Each claim is tagged as:
- **BASE CONTRACT**: implemented or explicitly specified by existing `main` owner; no claim that every caller uses it.
- **DRAFT/DEV EVIDENCE**: separate proposed integration or disposable-world exercise, not canonical main or independent QUALIFICATION.
- **V0.5 DECISION**: user-agreed conceptual design, not executable.
- **OPEN**: a decision, transition, authority rule, implementation or outcome test still required.

The smallest existing semantic owner should continue to own each fact; do not add a central manager before demonstrating irreducible independent state/control (Grand Null). A contract changes only through reviewed owner-scoped implementation; documenting a future workflow does not grant it.

## 2. Legacy-to-v0.5 mapping and invariants

| Existing concept/source | v0.5 interpretation | Authority or necessary distinction | Status |
| --- | --- | --- | --- |
| Persistent Cognition | Durable state supporting MySelf / SelfWorld / SelfBody | Preserve Identity Specification, Self-Model, Belief, Memory, Goal, Question, Capability Model and their provenance | BASE CONTRACT + V0.5 DECISION |
| Present Projection / Working Self | Current Self-relative cognitive activation | Not Self in total; recomputable, not automatically durable | BASE CONTRACT |
| Self-Model | Durable, fallible self-assessment supporting MySelf | Not normative Identity Specification; MySelf does not own all memory | V0.5 DECISION |
| Other Model / Relationship Model | Part of observer-relative SelfOther in SelfWorld | Other's subjective beliefs are neither World truth nor Self's own commitments | V0.5 DECISION |
| SelfWorld view | Source-qualified current subjective world/context | Not physical World, memory owner, generic World simulator, or Action authority | DRAFT/DEV EVIDENCE |
| SelfBody view / Capability Model | Subjective physical/body/compute capacity estimate | Not WorldBody nor authoritative CPU/GPU availability; observed and predicted costs differ | DRAFT/DEV EVIDENCE |
| Embodied Boundary | Perception, interoception, Action proposal/authorization/issue/closure | Self estimates never override World/WorldBody observation/host runtime enforcement | BASE CONTRACT |
| Need / Goal / Question / Tension | Distinct pressure/desired state/inquiry/transient arbitration input | Do not collapse types or automatically promote any one to Action intent | BASE CONTRACT + V0.5 DECISION |
| Arbitration / Current Intent | Commitment to executable objective after selection | Existing owner: one current Intent per `IntentCommitment`; multi-slot scope **OPEN** | BASE CONTRACT + OPEN |
| Skill | Reusable temporally extended control capability | Skill execution instance is separate from Skill definition, Intent, Action | BASE CONTRACT |
| Action Lifecycle / Supervision | Primitive proposal, recorded authorization, issue, evidence-based closure | Authorization recording != proof the supplied authority is legitimate | BASE CONTRACT |
| L0/L1/L2 | Functional cognition modes, possible concurrent/reused operations | Not rigid clock intervals, automatic authority tiers or accuracy ranking | V0.5 DECISION |
| Goal temporal composition / Plan | Parallel, sequential, deferred, restructured fulfillment | Plan is not automatically a durable new semantic owner | V0.5 DECISION |
| Cognitive execution slot | Temporary Self-created capacity carrying active work/commitment | Not an agent or physical issuer; runtime capacities and slot-Intent contract **OPEN** | V0.5 DECISION + OPEN |
| Learning / crystallization | Evidence-based conditioned updates and tested amortization | Outcome != learning != improvement != authorized L0 promotion | BASE CONTRACT + OPEN |

## 3. Existing executable constraints (main)

### Intent owner
[`docs/contracts/intent-commitment.md`](contracts/intent-commitment.md) and `src/relay_self/intent.py`: one current commitment per owner. Commit cannot silently replace it. Reconsideration request records a *reason*, distinct from `CONTINUE` / `RELEASE`; successful completion, failure and invalidation terminate commitment. No general goal arbitration, source trigger-admission, scheduling, automatic preemption, or multi-slot Intent-to-owner mapping.

### Skill owner
[`docs/contracts/skill-execution.md`](contracts/skill-execution.md), `src/relay_self/skill.py`: a Skill execution starts with a *real current* intent, immutable association; ends SUCCEEDED/FAILED/CANCELLED. Its lifecycle does not itself select Skills, perform closed-loop control, retain child Actions, cancel in-flight Actions, or automatically cancel on an Intent change. A local Skill failure does not automatically fail the parent Intent.

### Primitive Action owner
[`docs/contracts/action-lifecycle.md`](contracts/action-lifecycle.md), `src/relay_self/action.py`: a proposal is admitted only from a current STARTED Skill matching the current Intent. Then `PROPOSED -> AUTHORIZED|DENIED`, `AUTHORIZED -> ISSUED`, `ISSUED -> OUTCOME|TIMEOUT|UNKNOWN`. Legal lineage transitions, association, provenance and deadlines are checked. This seam records an authority identifier/provenance but **does not independently establish that the real principal has authority** or that commands are physically compatible. `OUTCOME` closure is not an automatic claim of external success.

### Action supervision and runtime
[`docs/contracts/action-supervision.md`](contracts/action-supervision.md), `src/relay_self/action_supervision.py`: deterministic retained in-flight actions and explicit epoch/deadline processing, not an independent operating system clock or global concurrent Action scheduler. `src/relay_self/runtime_coordination.py` is a minimal coordinator, not a complete adaptive slot scheduler.

### Current S49 DEV path
The stacked S49 product branch and [#674](https://github.com/rinsakamo/relay-self/pull/674) provide original L0 `WAIT -> MOVE_AWAY -> MOVE_AWAY`, source-linked original MOVE/clear/S16 completion, and only the existing physical action issuer. Its particular `escape-threat` Intent and MOVE_BACKWARD are not generalized Goal composition or concurrent fight/eat control. S/WB/M/L Draft results in different Worlds cannot be added into a single combined physical PASS. [#537](https://github.com/rinsakamo/relay-self/issues/537) remains the sole product-integration owner. DEV_ONLY, SOURCE_UNATTESTED, QUALIFICATION_NO_GO, SCIENCE_NOT_RUN distinctions survive.

## 4. Detailed contract A — Cognitive slots, commitments, Action authority

**Goal:** allow multiple cognitive loops and temporal Goal construction while keeping physical authority singular and bounded.

### Must decide
1. **Identity/lifetime:** distinguish persistent Goal and Commitment, transient Plan, slot instance, slot-level Intent commitment, Skill instance, Action ID; define what survives interruption, reallocation and process restart. A stored unfinished Goal is not itself an ACTIVE slot.
2. **Currentness:** how `IntentCommitment` per-slot semantics relate to old one-owner `current_intent`; forbid arbitrary sibling owners passing only matching textual IDs to an Action admission gate. Define atomic routing across slot replacement/Intent release and staleness fences.
3. **Temporal dependencies:** phase completion, guarded transitions, parent/child/peer dependencies and one Intent containing multiple subgoals. Local Plan or Skill replacement must not always trigger Intent RELEASE.
4. **Interruption:** PENDING/ACTIVE/SUSPENDED conceptual states; distinguish slot yield from Intent reconsideration and Skill CANCELLED; in-flight actions remain supervised; no fictional control stop or reuse of original authority on resume.
5. **Admissibility vs genuine authority:** final physical authorization needs provenance/identity/scope/grant legitimacy, current WorldBody constraints, unique issuer, source-qualified preconditions, deadline and Action resource lock/conflict treatment; model output remains advisory until specifically admitted.
6. **Feasibility:** concurrent MOVE and USE, attack, camera and input combinations are version/body/API specific. A valid *Goal* composition does not prove simultaneous physical commands. Define sequencing/time slicing/deferral with bounded fairness and safe emergency priority.
7. **Compute resource admission:** initial fixed slot caps are conservative implementation knobs; later schedule using actual observed time/memory/compute/body costs, estimates, deadlines, UNKNOWN. Protect L0 deadlines; separate logical cancellation from actual backend STOP and GPU release.

### Minimum acceptance cases (offline first)
- two Goals lead to distinct but admissible Plans under changed context or value gradient, without a universal fixed winner;
- Plan A `retreat -> eat -> approach -> attack` vs B `attack -> verify -> eat`: phase evidence, changes without silent Intent break, failure/reconsideration/continuation;
- two L0 candidates request same action resource: only one authorized issuance unless body interface independently proves compatible combination;
- stale slot/source/revision, foreign Intent, duplicate execution, denied grant or L2-only suggestion cannot issue;
- releasing/suspending Intent during in-flight MOVE yields deterministic cancellation/closure or explicitly UNKNOWN, never a fake stop;
- L0 continues within deadline while L2 is slow, absent, cancelled or backend resources have not yet been proven free;
- no second World/physical issuer; source and original S16 event IDs remain independently auditable.

**Design result:** precise contracts and negative tests routed to existing owner #537; a new central `SlotScheduler` or admission owner needs a separate Grand Null and demonstrated irreducible state.

## 5. Detailed contract B — Persistence and three-model projections

**Goal:** prevent dual stores or authority drift when MySelf, SelfWorld and SelfBody learn from one experience.

### Must decide
- existing semantic objects and exact update owner for each fact: source Evidence vs inferred Belief vs durable Memory vs capability estimate vs regulated identity/value;
- ephemeral view vs reconstructible cached model vs new persisted representation; require evidence of irreducible durable state before a new owner;
- multi-model update from same outcome with separate assessments/provenance/uncertainty and conflict resolution;
- SelfOther beliefs about another vs that agent's own MySelf; disagreement is normal, not a World fact;
- missing data, aging, invalidation, replay and source mismatch; continuity across restarts.

### Minimum acceptance cases
- same movement failure can update a body-capability hypothesis and a world-surface hypothesis *without* declaring a single correct cause;
- derived view invalidated by newer world observation; remembered evidence remains with correct provenance;
- belief about an enemy's intention never reclassifies an externally observed species/type into an independently attested hostility fact;
- retained assessment cannot change normative Identity Specification or authorize Learning merely by being included in MySelf.

**Design result:** map to existing `docs/ontology.md` and #632/#633/#636; preserve explicit write ownership.

## 6. Detailed contract C — Experience learning and conditional crystallization

**Goal:** ground learned predictions, Plan selection, concentration capacity and possible Skill formation in real source-qualified outcomes.

### Must decide
- differentiate **predicted physical effect**, **observed consequence**, **plan success**, **selection reason**, **value gradient**, **policy revision**, **model applicability**, **learning authority** and **promotion**;
- evidence/temporal credit assignment for multi-step and simultaneous Goals, distinct World/body/host costs, confounders and UNKNOWN;
- experience-based model of runtime concurrency and required concentration without learning an unqualified fixed maximum; repeated failures can reflect changing environment/loads;
- holdout/shift/return-to-cheap and rollback/abstain gates; L2 diagnosis is not self-correction until revision and later tests succeed;
- learning from L0/L1 failures and upward escalation, not mandatory L2 origin; conditions for L1/Habit adoption and separately reviewed L0 promotion.

### Minimum acceptance cases
- increasing concurrent slots causes misses; reduced concurrency improves deadlines under matched conditions, while alternate bottleneck explanations are tracked;
- `attack first` succeeds once: update conditional forecast/selection evidence without automatically changing the agent's values;
- `retreat first` succeeds in different conditions: both retained as context-dependent candidates;
- model predicts wrong physical movement: detect mismatch, propose revised applicability, test across independent opportunities; unproven claims remain unknown;
- cheap L0 stays best in simple conditions; L2 overhead and compute/body cost are counted, not rewarded.

**Design result:** #431/#426 owners; V qualification #619 remains independent. No automatic S10 write or L0 execution grant.

## 7. Sequencing, acceptance and non-goals

1. **Conceptual v0.5 baseline**: accepted user decisions, this audit, one parent Issue, docs-only Draft PR. No claim of executable v0.5.
2. **Contract A** first, because it connects all later learning and persistence to a lawful physical execution path. Define use of current `IntentCommitment`, `SkillExecution`, `ActionLifecycle` and single S49 issuer without speculative second owners.
3. **Contract B**, mapping durable storage vs transient models and legitimate cross-model updates.
4. **Contract C**, grounded experience, safe candidate learning, retention, test and eventual crystallization.
5. Only after owner review: staged **offline negative tests -> DEV World/LLM opt-in where appropriate -> evidence audit -> separate R/QUAL and V/SCIENCE qualification**. One branch success is not another branch's World success.

This Draft **does not** update protected main, rewrite existing owner contracts, start Minecraft, use the GPU, assert actual learned cognitive superiority, or authorize new Action/learning/energy debits.

## 8. Existing reference index

- [Ontology](ontology.md), [Architecture](architecture.md), [Runtime Principles](runtime-principles.md)
- [Intent Commitment](contracts/intent-commitment.md), [Skill Execution](contracts/skill-execution.md), [Action Lifecycle](contracts/action-lifecycle.md), [Action Supervision](contracts/action-supervision.md)
- [v0.5 parent #717](https://github.com/rinsakamo/relay-self/issues/717), [S #537](https://github.com/rinsakamo/relay-self/issues/537), [cross-lane #636](https://github.com/rinsakamo/relay-self/issues/636), [L #431](https://github.com/rinsakamo/relay-self/issues/431), [AC #426](https://github.com/rinsakamo/relay-self/issues/426), [V #619](https://github.com/rinsakamo/relay-self/issues/619)

## 9. Detailed contract A — design proposal recorded (2026-11-03)

[Contract A: Cognitive Intent Slots / Physical Action Authority](contracts/intent-slots-action-authority-v0.5.md) now specifies the **candidate design**, not executable acceptance. It separates slot-scoped cognitive task commitment from the **single existing physical Execution Intent owner**; cognitive outputs must pass an S49-owner admission bridge before the original `SkillExecution`/`ActionLifecycle` path. It specifies guarded Plan revision, runtime capacity, suspension vs physical stop, resource exclusivity and post-S16 settling, source/authority fences, 14 negative-control invariants, and staged A0–A3 owner implementation.

**Status: A DESIGN_DRAFTED / OWNER REVIEW REQUIRED / OFFLINE IMPLEMENTATION NOT RUN.** Existing product owner S #537 must resolve the precise slot-local commitment representation, whether existing `ExecutionBinding` suffices without a new type, physical quiescence qualification and scoped generation identity. A is **not** marked `DESIGN_ACCEPTED` or implemented. B and C remain open.
