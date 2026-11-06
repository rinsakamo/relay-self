# RelaySelf — Unified Cognitive Architecture v0.5

> **Status: v0.5 ARCHITECTURE_DESIGN_COMPLETE / DESIGN FROZEN (2026-11-07 JST) / IMPLEMENTATION_PENDING / NOT A QUALIFICATION CLAIM.**
> Closure record: [v0.5 Design Freeze / implementation handoff](unified-v0.5-design-freeze-20261107.md). A, B and C1–C4 are conceptually accepted; owner-specific executable API review, tests and integration remain separate.
>
> Tracking: [Unified Architecture v0.5 #717](https://github.com/rinsakamo/relay-self/issues/717). This document freezes agreed *conceptual invariants*, not the detailed execution contracts. The existing `main`, S/L/M/WB/G branches, evidence and physical/learning authority remain unchanged. Baseline inspected: `main@4348a614900c1d0828581a8eec2c523ba5ae237f`.

## 0. Purpose, scope, and boundaries

Unify the general RelaySelf ontology (Persistent Cognition, Present Projection, Embodied Boundary, Environment, Authority / Provenance) with the embodied Minecraft architecture (MySelf, SelfWorld, SelfBody, L0/L1/L2, World/WorldBody) **without changing which component owns truth, memory, action issuance, or learning authorization**.

```text
Persistent Cognition                         World / WorldBody
(existing governed durable objects)         (external source-of-record)
        |                                          |
        +----> MySelf                              +-- world evidence --+
        |       (self / goals / competence)                           |
        +----> SelfWorld <---------------------------------------------+
        |       (environment / others / causal estimates)
        :                                          |
        : approved body history                    +-- body evidence --> SelfBody
        + - - - - - - - - - - - - - - - - - - - - - > (interoception / limits)
                (secondary, source-qualified use)
                     MySelf      SelfWorld      SelfBody
                         \          |          /
                          v         v         v
                            Present Projection
                  (current appraisal / Need / Goal / Intent
                      signals, uncertainty, disagreements)
                                     |
             bounded L0 / L1 / L2 slots and Intent arbitration
                                     |
                     original S49 Skill/Action admission
                                     |
                World / WorldBody qualified actual outcomes
                                     |
             fresh observation and separately governed
                   experience-integration candidates
```

This is an **explanatory map**, not an assertion that the whole diagram exists as one connected program. No new `SelfController`, `SlotManager`, world-state source, universal Plan store, physical issuer or generic cognitive-value scalar is authorized by this baseline.

## 1. Self and the three observer-relative models

**Self** denotes the continued process of perception, regulation, deliberation, control, learning, and self-maintenance, not a separate central entity, globally controlling singleton, or semantic persistence owner. Its present activity is a projection, not the entirety of Self or durable cognition.

- **MySelf**: the individual's fallible, possibly durable understanding of identity, commitments, values, competence, history, relationships and continuity. MySelf is *not* the normative `Identity Specification`, and it does not own all Persistent Cognition.
- **SelfWorld**: a subjective, source-bounded and incomplete model of surroundings, events, affordances, causality, uncertainty, and other agents. **SelfOther** is the model of another agent within SelfWorld, including beliefs about that other's beliefs. Neither is authoritative World truth.
- **SelfBody**: the individual's fallible internal model of its body, bodily limits, motion dynamics, viability, performance and resource capacity. It is not WorldBody or a new motor/action authority.

These are **semantic perspectives/representations**, not necessarily three permanent processes, three databases, or three independent update owners. Their *main sources* are deliberately asymmetric: MySelf and SelfWorld consult Persistent Cognition heavily, while SelfBody chiefly consults source-qualified WorldBody/interoceptive data. SelfWorld also needs fresh World observations; SelfBody may consult approved bodily memories and Capability Models; MySelf can consult qualified consequences. They may actively interpret, predict and disagree, but currently audited WB view objects are read-only with respect to persistent state, Action issuance and external truth. Their judgments converge **as attributed contributions** in Present Projection, not automatically by majority vote. Durable or reconstructible representations and authority to revise them remain detailed Contract B decisions.

**Persistent Cognition** retains the established objects and their ownership: Identity Specification, Self-Model, Relationship/Other Models, Goal, Commitment, Question, Evidence, Assessment, Belief, Memory, dispositions, Capability Model, and governed Experience Integration. **Present Projection** remains the transient, source-aware current activation. `Goal != Current Intent`, `Evidence != Belief`, `Belief != Memory`, `Identity Specification != Self-Model`.

## 2. Goal formation, values, experience and time

Each of MySelf, SelfWorld, SelfBody can contribute Needs, Goals and Questions to **L0/L1/L2 functional scales**; several can coexist, be suspended, conflict, cooperate, depend on each other, or remain unresolved. Do not collapse Need, Goal, Question, persistent Commitment, Active Goal, Tension, Intent, Plan, Skill and Action into one type. Cross-cutting allostatic, enactive and homeostatic regulation can appear in any model/scale; the heuristic analogy of L2 anticipating future conditions, L1 interacting/adapting, and L0 regulating immediately is **not** a one-to-one scientific mapping.

**Value-conditioned temporal Goal composition** may:
- **compose** concurrent goals where available capabilities and real resources permit;
- **sequence/time-slice** goals that contend for a resource;
- **decompose** high-level aims into local subgoals;
- **defer/suspend** an unresolved aim without erasing it;
- **replan/escalate** when preconditions, evidence, urgency or capabilities change.

Examples with the same high-level goals (respond to a threat, recover hunger):
- Move away -> eat -> approach -> attack.
- Eliminate the threat -> verify safety -> eat.
Neither is a universal correct plan. Experience about enemy behavior, body capabilities, deadlines, uncertainty, and individually held value gradients can lead to different choices. Short-term movement away from a target may advance a long-term approach/attack objective. Goal contradiction, Action resource contention, and mere temporal incompatibility are distinct.

Keep **viability constraints** distinct from preferences and ordinary utility. A violation of a hard envelope is an admissibility problem, not merely a low preference score; an unavoidable violation requires explicit recovery/least-violation policy rather than pretending all options are safe. Updating the expected success of a Plan **does not automatically rewrite the values** used to choose between Plans. Normative Identity changes require their separate authority.

A **Plan** is a transient possible causal/temporal arrangement of steps and conditions. A **Skill** is a reusable closed-loop competence that may implement some or all of such an arrangement. One Plan can be revised under the same executing commitment; a new Plan is not automatically a new Intent. Defining a dedicated durable Plan owner is **not** in scope without an independent proven need.

## 3. L0 / L1 / L2: functionality and development

- **L0**: low-latency, bounded reactive control and validated routines; may implement multi-step closed-loop skill, not merely one tick.
- **L1**: contextual, experience-informed choices, adaptation, conditional prediction and reuse.
- **L2**: deliberation, counterfactuals, new explanation, experiments, structural/conditional model revision.

This is a distinction in **function and cognition expense**, not immutable runtime durations, rigid layers of authority, model counts, or an assumption that L2 is always better. Known easy tasks should often stay on cheap L0. Unknown, out-of-distribution, erroneous or insufficient models may escalate. Knowledge and temporal composition strategies may be conditionally crystallized L2 -> L1 -> L0, or learned within L1, and decrystallized/re-escalated on failure. No autonomous L0 installation is claimed to be **implemented today**; Self-directed L0 crystallization is **architecturally allowed** when executable within the actual World/body/host resources. Neither cognitive progress nor L2 output by itself proves physical success or science qualification.

## 4. Current Intent and cognition-execution slots

**A cognitive slot is a transient execution capacity instantiated/managed by the Self**, not another Self, autonomous value holder, permanent personality, physical Action issuer or new semantic owner. It may carry a **current commitment (Intent)**, a budget, layer/mode, provenance/evidence revision, temporal constraints and execution status. The distinctions are:

```text
Goal (desired state) != Plan (candidate temporal construction)
  != Intent (committed executable objective)
  != cognitive slot (capacity to pursue/process an Intent)
  != Skill execution (one concrete control path)
  != Action (primitive proposed effect)
```

Multiple Goals and dormant commitments can exist while **ACTIVE cognitive slots are bounded**. Slots may be PENDING, ACTIVE or SUSPENDED as a conceptual model, but adding these states to the existing `IntentCommitment` state machine is **not** yet approved. A suspended process/slot does not prove a physical action stopped. Resumption must re-check current source/version, preconditions, deadlines, authority and any in-flight Action; never replay an old grant or stale observation.

The initial implementation may use fixed conservative maxima per L0/L1/L2. The eventual active capacity is **not an intrinsic constant or a new level of personhood**: World/WorldBody, physical host CPU/GPU/VRAM, temporal deadlines, cognitive/body resources, synchronization overhead and physical action conflicts bound actual execution. Runtime enforcement is independent of the SelfBody/MySelf *estimate* of capacity. The Self may empirically discover failure, latency, resource contention and the required **concentration/attention allocation**; study costs, conditions and alternative causes rather than asserting one magic slot count. Preserve headroom and deterministic emergency L0, and distinguish logical L2 task cancellation, backend STOP, compute quiescence and freed GPU memory.

**Cognitive concurrency != Skill concurrency != physical Action concurrency.** Several slots can read/process source-qualified snapshots; only the existing authorized S49 execution boundary physically issues actions in present Minecraft development. S49 remains the sole issuer while future arbitration and resource locking are designed.

The existing repository contract has *one Current Intent per `IntentCommitment` owner*, but **the architecture does not limit the number of concurrently valid body-directed Execution Intents to one**. Multiple Goal-derived Intents may remain committed while sharing a WorldBody; the single S49 physical issuer admits/decodes only compatible and actually authorized control requests, with arbitration and leases **per resource channel**, not by arbitrarily merging all Intents. Current S49's single owner and serial MOVE-only behavior are an implementation boundary to be extended only through contract A's reviewed owner/currentness and multi-channel checks. Do not let an L2 advisory mint a grant or treat local Skill failure as automatic Intent failure; reconsideration request is separate from CONTINUE/RELEASE.

## 5. Reality, authority, time and learning

The authoritative **World/WorldBody** physical state, host compute constraints, and actual elapsed time are not owned by the Self's subjective estimates. SelfWorld/SelfBody have evidence limits, freshness, uncertainty and possible mismatch. Observed source-bound outcome may inform subsequent cognitive state; a prediction, LLM message or narrative cannot establish that an Action succeeded. An Action proposal, valid authority decision, issuance, external execution, and consequence are distinct stages.

Retain the existing boundaries: original S49 sole Action issuer and S14/S15/S16 execution/clear/outcome; `IntentCommitment`, `SkillExecution`, `ActionLifecycle` and `ActionSupervisor`; result source identities; staleness fences; control cleanup; model and Body budgets; regulated S10/S11 Memory/Habit updates. A status like `OUTCOME` alone does not assert world success; read the actual consequence.

Learning is **experience + interpretation + governed revision**:
- physically sourced outcome/uncertainty may update estimates of the environment (SelfWorld), body/compute capacity (SelfBody), or self-competence/strategic choice (MySelf);
- choose whether a measured miss calls for changing a forecast, a Plan-selection rule, a goal applicability condition or a value gradient; these are different causal claims;
- test retention, applicability boundaries, transfer, failures, OOD abstention, time/compute/body costs and subsequent real action changes;
- retained evidence, a candidate hypothesis, a shadow behavior difference, a learned rule and promoted L0 skill have **different acceptance gates**.

## 6. What v0.5 freezes — and does not freeze

**Frozen:** conceptual division, causal/authority boundaries, three-model perspectives, multi-goal temporal/value conditioning, cognition modes, transient resource-bounded slots, experience-based allocation and conditional crystallization; no universal best plan.

**Bug-0 initial implementation slice:** [Minimum Embodied Self / «流暢にしゃべるゾンビ»](contracts/bug0-minimal-embodied-self-v0.5.md) limits the first real-world target to MOVE/STOP, EVADE, EAT, ATTACK, REST and WAIT/OBSERVE, with narrow SelfWorld/SelfBody/MySelf views, serial physical admission and one attributable experience-based decision change. EAT/ATTACK/REST are **not** inferred to be implemented from this design. High-fidelity joint World simulation (D) and MySelf-driven autonomous training (E) are deliberately deferred. Contract A/B/C owner review remains open.

**Open detailed contracts (tracked in #717):**
- **A — Intent slots and Action admission/authorization — ARCHITECTURE_DESIGN_COMPLETE / IMPLEMENTATION_PENDING (2026-11-06):** [Contract A](contracts/intent-slots-action-authority-v0.5.md) defines Self-owned multiple Intent commitments, each signal/lifecycle, and one S49 physical issuer. The [standing HOMEOSTASIS / imperfect control design](contracts/intent-homeostasis-regulation-v0.5.md) adds ongoing regulation, episodic EAT/REST/EVADE Intents, minimal S49 hard-command checks, and tolerance for bounded unexpected physical effects. Owner API review, offline regression and real World remain separate pending gates; no feedback convergence asserted.
- **B — Persistent Cognition + three models — ARCHITECTURE_DESIGN_COMPLETE / IMPLEMENTATION_PENDING (2026-11-06):** [Contract B draft](contracts/persistent-cognition-three-models-v0.5.md) maps existing semantic persistence owners to read-only MySelf/SelfWorld/SelfBody views, source-qualified Present, SelfOther, standing HOMEOSTASIS, identity governance and controlled cross-model update routing. New stores and automatic Memory/learning grants are explicitly disallowed by default; owner/API review and tests remain open.
- **C — Experience, understanding and crystallization — ARCHITECTURE_DESIGN_COMPLETE / IMPLEMENTATION_PENDING (2026-11-06):** [C1](contracts/intent-experience-c1-v0.5.md) uses one qualified Intent-attempt outcome = one experience, not one per Action/autosave. [C2](contracts/understanding-revision-c2-v0.5.md) proposes zero-or-more source-qualified revisions to prediction, applicability, selection or cognitive allocation. [C3](contracts/conditional-crystallization-c3-v0.5.md) supports condition-scoped L1/Habit reuse, reversible fallback and separately gated nonautomatic L0 promotion. [C4](contracts/learning-admission-c4-v0.5.md) separates model interpretation, actual owner-local Memory/Learning/Habit write authority, condition-valid activation, S49 physical Action admission and owner-governed rollback. C4's corrected Self-autonomy principle has been accepted: Self is free to learn and develop within actual World/WorldBody, available embodiment and compute limits; software owner/source integrity is not a cognitive permission ladder. Full learning loop and autonomous L0 installation are not yet implemented, and no DEV qualification or scientific effect is inferred.

**Not implied:** a change to main, an implementation release, a new central runtime owner, multi-Action/physical concurrency, valid real-model inference, automatic learning authority, QUALIFICATION/SCIENCE claims, or cross-branch evidence stitching.

## 7. Canonical existing references

- [Architecture](architecture.md), [Ontology](ontology.md), [Runtime Principles](runtime-principles.md)
- [Intent Commitment](contracts/intent-commitment.md), [Skill Execution](contracts/skill-execution.md), [Action Lifecycle](contracts/action-lifecycle.md), [Action Supervision](contracts/action-supervision.md)
- [#537 S product integration](https://github.com/rinsakamo/relay-self/issues/537), [#636 cross-lane architecture](https://github.com/rinsakamo/relay-self/issues/636), [#632 SelfBody](https://github.com/rinsakamo/relay-self/issues/632), [#633 SelfWorld](https://github.com/rinsakamo/relay-self/issues/633)
- [#426 cognition development](https://github.com/rinsakamo/relay-self/issues/426), [#431 learning](https://github.com/rinsakamo/relay-self/issues/431), [#432 cognitive cost](https://github.com/rinsakamo/relay-self/issues/432), [#619 validation](https://github.com/rinsakamo/relay-self/issues/619)

*Baseline document is normative conceptual guidance; executable owner contracts and physical-source evidence retain their own status until explicitly and separately changed.*

## 8. Self freedom and the meaning of technical authority (user correction, 2026-11-06)

Within the genuine physical limits of World/WorldBody, available embodiment/interface capabilities and finite time/GPU/CPU/memory/other cognitive resources, **Self is free to explore, learn, revise its understanding and improve/replace its strategies and skills**. This includes eventual autonomous crystallization into L0, if the implementation supports such routine installation. No per-experience human permission gate is an invariant of Self's cognition. Existing S49 issuer checks, source/provenance ownership and revision controls protect current implementation correctness and the World boundary; they are not external censorship of learning. Some normative or Identity record types remain separately modeled and current code may lack their mutation APIs; whether and how Self revises itself is an implementation/ontology question, not a claim that Self fundamentally lacks that freedom. R/V DEV qualification is about developer evidence, not Self authorization to learn. See [C4 autonomy clarification](contracts/learning-admission-c4-v0.5.md).

## 9. Conceptual design disposition (2026-11-06)

**A / B / C = ARCHITECTURE_DESIGN_COMPLETE / IMPLEMENTATION_PENDING.** The user accepted the C4 freedom correction: there is no external per-learning human-permission hierarchy; Self may learn, explore, revise its models and eventually crystallize skills into L0 within actual World/WorldBody, embodiment and host compute constraints. The stage boundary is **design closure only**. Any concrete S49/WB/Learning/Habit owner API, physical control integrity, and real-world validation remain engineering tasks. SCIENCE remains NOT_RUN, QUALIFICATION remains NO_GO. Do not infer the design branch has merged to main.
