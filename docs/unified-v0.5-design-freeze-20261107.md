# RelaySelf Unified v0.5 — Design Freeze / Implementation Handoff

> **Decision: ARCHITECTURE_DESIGN_COMPLETE (2026-11-07 JST) / IMPLEMENTATION_PENDING.**
> User explicitly requested closure of the v0.5 design. This is **conceptual and architectural closure**, not proof of integrated execution, a main merge, full owner/API review, real-World qualification or scientific benefit.
> Design ledger: [#717](https://github.com/rinsakamo/relay-self/issues/717); docs-only [Draft PR #718](https://github.com/rinsakamo/relay-self/pull/718). The design baseline and original evidence remain unchanged. This freeze governs interpretation of historical OPEN/DRAFT labels in earlier sections of the v0.5 documents; those labels describe their time of authorship or **owner/API implementation gates**, not an unapproved conceptual design.

## 1. Frozen architecture and boundaries

1. **Self is a continuing adaptive process**, not a newly authorized central controller, universal truth store or omnipotent Memory writer. MySelf (self/commitments/abilities), SelfWorld (subjective environment/others), and SelfBody (subjective bodily condition) are fallible interpretive models. Present is a current projection, not all durable cognition.
2. **World/WorldBody owns physical truth and physical law.** Cognitive interpretations, observations, proposed actions, actual S49 issuance, S15 clear, S16 terminal outcomes, and Goal/Intent success are separate evidence stages. Self cannot infer authoritative changes from an LLM answer or imagined consequence.
3. **Self holds distinct Goals, Needs, Questions and multiple Intent commitments.** Intent != Goal != Plan != Slot != Skill != physical Action. Slots are finite cognitive execution resources, not owners. A standing HOMEOSTASIS Goal/Commitment may remain retained while episodic EAT/REST/EVADE/ATTACK/MOVE Intents become eligible, blocked, deferred, executed or reassessed. A Plan switch or slot shutdown is not an implicit Intent release.
4. **Existing original S49 stays the sole physical Action issuer** with original source/currentness, bounded grants, channel/resource-conflict checks, clear/settling and one-in-flight primitive behavior. Multi-Intent / multi-channel ControlFrame is a future implementation direction; design does not confer a new issuer or runtime capacity. Valid commands may still have unexpected physical consequences and require feedback rather than a promise of perfect motor control.
5. **L0/L1/L2 are adaptive functional modes**, not mandatory complexity tiers. Familiar conditions can favor cheap fixed L0. In unfamiliar/OOD/mismatch conditions, Self may revise models and applicability, conserve resources, abstain, investigate with L1/L2, or re-escalate. Self is free to learn, improve skills and eventually self-install viable L0 skills within *actual* physical, embodied API, temporal, CPU/GPU/VRAM/memory constraints. There is **no per-experience human permission hierarchy for cognition**. Current missing APIs and source/revision validity checks are technical constraints, not a philosophical ban on development.
6. **Persistent Cognition and three lenses** reuse existing semantic owners/read models. The normative Identity Specification, inferred MySelf, World evidence, SelfWorld belief, WorldBody state and SelfBody estimate stay distinct. Historical memory and checkpoints cannot impersonate new native observations.
7. **C1:** one *actually attempted*, bounded Intent attempt and assessed result produces **one Intent experience**, even if it contains several primitive Actions or a qualified action-free REST interval. A commitment terminal state is not proof of Goal success. An unattempted/deferred Intent produces no physical experience. UNKNOWN/failure are legitimate; revisions to an experience are versioned, not silently counted twice.
8. **C2:** one C1 experience can generate zero or more typed, conflicting, uncertain proposed understanding changes (prediction, applicability condition, Plan/Intent selection, cognitive allocation), with before-model/prediction bound before outcome. Proposals are not automatic external facts or owner writes.
9. **C3/C4:** retain/reuse versioned, cue-scoped understanding and habits through the actual existing owner APIs; preserve original evidence. Habit use and physical admission are separate. Unknown cue, mismatch, stale source or failed results allow abstention, suspension, rollback and L1/L2 reinvestigation. Self may develop its own policies; R/QUAL and V/SCIENCE assess *our evidence claims*, not Self's permission to learn.

## 2. Snapshot and execution timing (separate clocks)

- **B default cognitive autosave = configurable best-effort 60 seconds** for *currently reachable* source-qualified SelfWorld/SelfBody representations, per-view source times and UNKNOWN. It is not a command clock, sensory-refresh clock or S49 source freshness grant. A restored checkpoint is **historical context** until a fresh session/native observation qualifies.
- **C1 experience boundary = assessed attempted-Intent result**, not each tick, each Action, each S16, or each autosave.
- **Physical WorldBody / native tick / S49 lifecycle** keeps independent timestamps and authentic before/after evidence. Paper's **600 server ticks after an actual managed zombie death** is an external DEV World-side respawn rule (nominal 30 s at 20 TPS), not guaranteed 30 s of wall time.

## 3. Owner handoff and acceptance gates

| Implementation owner | Frozen obligation / initial seam | Completion evidence belongs to |
| --- | --- | --- |
| **S #537** | Self-scoped Intent identity/lifecycle and technical currentness; serial original S49 single-issuer adapter; source, action, outcome and resource/clear checks; no shadow authority | S owner source-bound offline tests + original in-World actions |
| **WB #632 / #633, cross-boundary #636** | Finite MySelf/SelfWorld/SelfBody readouts and per-field provenance/UNKNOWN; current Present; best-effort 60 s checkpoint and historical-only restart recovery | WB/owner tests and qualified observation records |
| **L #431 / #426** | C1 attempted-Intent grouping and dedup; C2 typed revisions and conflicting hypotheses; C3 conditional retention/reuse; C4 version-checked autonomous write/activate/suspend/rollback using real owners | Learning/Habit owner and later independent next-Intent reuse |
| **M #616** | World-owned physical fatigue/food/health and real resource costs; SelfBody interprets signals, never edits hidden physical coefficients | M/WorldBody evidence |
| **Bug-0 #742** | Existing MOVE/STOP, EVADE, ATTACK, COLLECT_LOOT/PICKUP, EAT, REST, WAIT/OBSERVE in the same Self and original S49, with authentic death/drop/pickup/eat and World-owned 600-tick respawn | Same-World multi-Intent DEV loop; **not yet unlimited survival** |
| **R / V #619** | Independently qualify source and scientific claims separately from engineering development | QUALIFICATION / SCIENCE, not design closure |

No extra central semantic owner, Action issuer, new Minecraft primitive or broad merged branch is created by this document. Use existing owner implementations first (Grand Null), retain negative-control requirements in A/B/C and follow on owner-specific API reviews. In particular test wrong Self/session/epoch, stale and truncated sources, duplicate/replayed Intent outcomes, guessed World truth, unsigned/unsettled physical effects, and recovery of old grants.

### Initial integrated Bug-0 example (design target, not an achieved continuous-world claim)

Observed enemy → retain/select EVADE or ATTACK Intent → genuinely bounded S49 Action and independent observed effect → actual death/drop → use safe physical MOVE for collection (natural World pickup, not an invented PICKUP command) → fresh inventory/food evidence → EAT when eligible → REST/WAIT with real WorldBody signals → encounter respawned enemy via fresh native observation → assess each attempted Intent, retain C1 experiences, optionally reuse C2/C3 learning. Failure, no loot, Hunger, insufficient energy, death and UNKNOWN remain valid outcomes. B snapshots can occur independently without granting action or generating experiences.

## 4. Design acceptance / explicit non-goals

**v0.5 DESIGN DONE** means: (i) A/B/C1–C4 conceptual decisions accepted, (ii) source/owner and autonomy distinctions fixed, (iii) implementation entry points and negative tests documented, and (iv) Bug-0 first competence scope and evaluation claims bounded. No additional philosophical design choice is necessary before owner-specific engineering.

**Not implied:** individual code APIs agreed or merged, passing every proposed offline negative test, one unified executable Self, multiple simultaneous native actions, automatic L0 installer, longitudinal learning improvement, indefinite survival, real-World qualification, or scientific causal superiority. Advanced D (high-fidelity joint World/Body counterfactual simulator) and E (long-term self-training and competence optimization) remain deferred, without forbidding their future development.

**Change policy:** #717 may close as a *design issue*. Implementation gaps, runtime refinements and acceptance failures stay in their existing owner issues. Any material change to a frozen principle should be explicit, versioned and traceable rather than silently rewriting this baseline. Design PR #718 remains a docs-only review artifact until independently merged.

## 5. Contract index

- [Unified conceptual architecture](unified-architecture-v0.5.md)
- [A: Intent / Action](contracts/intent-slots-action-authority-v0.5.md) and [HOMEOSTASIS](contracts/intent-homeostasis-regulation-v0.5.md)
- [B: persistent cognition and three models](contracts/persistent-cognition-three-models-v0.5.md)
- [C1: Intent experience](contracts/intent-experience-c1-v0.5.md), [C2: understanding revisions](contracts/understanding-revision-c2-v0.5.md), [C3: crystallization](contracts/conditional-crystallization-c3-v0.5.md), [C4: autonomy and adoption](contracts/learning-admission-c4-v0.5.md)
- [Bug-0 initial embodied scope](contracts/bug0-minimal-embodied-self-v0.5.md) and [legacy implementation gap audit](unification-gap-audit-v0.5.md)
