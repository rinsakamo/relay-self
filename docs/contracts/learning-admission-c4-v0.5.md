# Unified v0.5 — Contract C4: Governed learning admission, activation and rollback

> **Status: C4 CONCEPTUAL DIRECTION USER-ADOPTED (2026-11-06) / OWNER/API REVIEW AND IMPLEMENTATION PENDING.** Prepared 2026-11-06 after user adopted the C3 direction. Parent [#717](https://github.com/rinsakamo/relay-self/issues/717), [C1 Intent Experience](intent-experience-c1-v0.5.md), [C2 Understanding Revision](understanding-revision-c2-v0.5.md), [C3 Conditional Crystallization](conditional-crystallization-c3-v0.5.md), [A physical authority](intent-slots-action-authority-v0.5.md), [B provenance](persistent-cognition-three-models-v0.5.md).

## C4.0 Principal distinction — cognition, retention and execution

**User correction (2026-11-06): Self is free to learn and develop within its actual World/WorldBody and cognitive-resource constraints (time, GPU, CPU, memory, etc.).** There is no external cognitive-permission ladder controlling which knowledge, strategies, goals or competencies it may develop. A Self can autonomously form, revise, reject and reuse understanding and skills; as the embodiment grows, it may even autonomously crystallize suitable techniques into L0. The *implementation* must preserve authentic external World facts, resource limits and adapter integrity: gaining skill is not the same as acquiring an unprovided Minecraft API or rewriting World physics. Valid owner/revision checks are software consistency, **not a requirement for operator approval of each learning event**.

| Layer | Self can do | Boundary: physical truth and implementation consistency, not permission to think |
| --- | --- | --- |
| Interpret C1 / propose C2 (MySelf, SelfWorld, SelfBody, L1/L2) | Freely revise hypotheses, self-understanding, goals and prospective strategies with available cognition; track uncertainty | Inference cannot rewrite external World/WorldBody observations or masquerade as a confirmed external fact |
| Durable retention via existing owner APIs | Self autonomously saves and updates its own models, memories, preferences and habits where supported; preserve source and version lineage | An unavailable persistence API cannot be fabricated; don't corrupt other stores or label guesses as observed facts |
| Cognitive activation (Present / L1/Habit selector) | Freely select, test, retire or revise condition-matched skills; develop toward L0 if the implementation supports that safely | Never equate selection with native execution or claim that an unimplemented Skill installer is present |
| Physical execution (current A/S49, S14/S15/S16/WorldBody) | Execute any action that the actual embodied interface, physics and available resources make possible | Can't bypass real API/World constraints, forge source/grant or claim physical success without observed consequences |

Neither a single omnipotent 'learning orchestrator' nor three separate memory databases are required. The existing **owner APIs are the current implementation paths**, not authorities over Self's right to learn. Where an API does not exist, Self can still reason using provisional or transient understanding; a durable write is simply not yet technically implemented. The roadmap may extend these APIs so Self can autonomously revise and deploy more of its cognition while preserving external truth and data integrity.

## C4.1 Minimum bounded admission path

```text
C1 — one qualified attempted-Intent outcome (with before prediction/context)
  -> C2 — zero or more typed target-specific revision candidates
  -> validate evidence and exact owner/revision + permitted change scope
     -> ACCEPT / DEFER / REJECT / UNDETERMINED
        ACCEPT: governed write + owner revision/lineage + rollback reference
        DEFER/REJECT/UNKNOWN: preserve evidence + reason, NO hidden write
  -> C3 — condition-scoped shadow / eligible L1 retrieval and use
  -> next actual Intent attempt C1 -> independent observation and monitoring
  -> mismatch / new condition / invalid cue -> abstain, fallback or review
```

**Engineering checks should be proportional to the consequence and cost.** A fallible self-model estimate is cheap to revise; a low-latency physical routine needs dependable input, bounded execution and recovery when it fails. The Self may evaluate and adapt these autonomously. For existing owner-local updates validate revision/feedback/source and write once; do not insert mandatory L2, human approval, globally synchronized snapshots or independent scientific evaluation into ordinary DEV learning.

The minimal logical update request records: (1) experience/feedback ID, Self and source session, original World/Action/Intent consequence references; (2) target semantic owner/object ID and expected revision; (3) typed change and affected conditions/cues; (4) supporting/contradicting evidence and uncertainty; (5) authorized bounded rule or owner permission; (6) disposition plus recorded predecessor/new revision, provenance and rollback path. Replays, wrong owner, stale revision, forged permission, missing required native source and incompatible cues fail closed with a reason.

Preserve `NO_PREDICTION`, Action `UNKNOWN`, absent World outcome and uncertainty as distinct data. Learning can respond to failure; it cannot make a physical consequence certain merely by committing a preference update. One C1 experience may lead to zero or several independent target revisions, but each is separately admitted, without three automatic writes for the same physical observation.

## C4.2 State changes are not all the same

- **Evidence/experience retention:** original source-qualified C1 record and action/world receipt remain historical. Correcting a later interpretation does not mutate original observations.
- **Understanding revision:** SelfWorld, SelfBody and MySelf may autonomously reconsider model/applicability/competence and, when supported, self-goals or self-model revisions. Keep distinct record types for normative Identity Specification versus descriptive Self-Model; any existing immutable specification is an explicit current software boundary, **not a principle that Self is forbidden from autonomously developing its own values or self-understanding**. Do not infer that the current code already supports every type of revision.
- **L1 habit retention:** a selected rule/cue may be persisted by the actual Habit owner only when it has valid condition scope, source and lifecycle; using existing `HabitCue`, `HabitRule`, `HabitRepertoire` is a candidate integration strategy, not proof these are already linked to the full Self.
- **L1 invocation:** checking a Habit cue is a read/selection activity. It does not itself mean the result was updated or authorized to drive S49.
- **L0 crystallization:** a more consequential engineering change than L1 preference selection. It needs feasible cue guards, deadlines, World/WorldBody viability, resource budgets, counterexamples and fallback. **The design does not require human approval for each Self-discovered L0 skill**; the Self may eventually install/adapt L0 autonomously using a legitimate runtime integration path. **Bug-0 currently has no such demonstrated self-installation API**, so do not pretend it already does, or bypass S49 during implementation.

## C4.3 Rejection, suspension, rollback and recovery

**Retaining knowledge != enabling its current use.** A recent exception may trigger immediate **selection suppression / abstention** without modifying the retained model. Do not require a full learning rewrite before stopping an obviously inapplicable L1 habit; do require valid owner control for a durable disable/rollback decision.

- On missing critical cue, source staleness, incompatible World session, revision change, known contradiction or unverified risk, **do not invoke** the cached L1 rule. Use existing safe L0 or bounded new observation; propose L2 diagnosis only when time/compute permits.
- On a repeated mismatch or negative C1 Intent outcome, preserve counterexamples and request a **targeted governed change**: narrow applicability, suspend the candidate, revise the model, or restore a previously accepted version. No automatic erase of the original evidence.
- Rollback restores the previous **retained owner revision or active selection state**, not World history and not a past physical Action. Completed World effects cannot be undone by cognitive rollback.
- Keep an audit link from update to the C1 experience, before/after values/versions, decision reason, authorized actor/rule and later failing outcome. Late evidence may amend the **same C1 record** under its owning semantics without duplicating experiences or silently replaying a completed learning update.
- Do not re-enable an old habit merely because a 60-second cognitive checkpoint restored it; always re-evaluate actual current World/session/cues and target revision. B autosave is not learning admission.

## C4.4 Validation with proportional evidence gates

| Gate | Minimum engineering observation | Separate claim not made |
| --- | --- | --- |
| **Proposed** | Typed candidate, target, source and uncertainty preserved | Knowledge changed |
| **Retained** | Correct owner accepted an update under current revision and authorized rule | It improved the next decision |
| **Reused** | Subsequent independent Intent attempt actually consulted the retained candidate with valid cues | It improved World outcome |
| **Beneficial** | Relevant measured objective improved within declared cost/constraint comparison | Universal generalization or safe L0 promotion |
| **L0 in use** | A real bounded/validated runtime Skill integration path supports the Self's chosen routine under current World/interface limits | Proof of superiority or science qualification unless separately measured |

**Product-first, no over-gating:** a single-episode advantage over fixed L0 is *not* a required DEV progression condition, and cheap-equivalent remains a valid null. Developing the read-only replay/retention path should not wait for full V science. But do not promote source-unattested or unimplemented changes into claims of actual learned policy improvement. #619 QUAL/SCIENCE remains independent.

## C4.5 First Bug-0 implementation slice

1. Start from one source-qualified C1 attempted Intent Experience such as EVADE motion/ice or EAT with known/readback UNKNOWN outcomes. No separate event warehouse.
2. C2 computes *one bounded conditional understanding candidate* (source and target owner explicit), preferably initially in read-only/shadow. `NO_UPDATE` is an acceptable result.
3. Route through the **existing** specific Learning/Memory/Habit owner; only its current revision + authority can admit a retained change. Favor simple tags/typed cues to reuse the episode. Existing WB DEV `learning.py` demonstrates a revision/authority protected **scalar preference** update, not a generic approval of all proposed beliefs; `habit.py` provides read-only cue selection.
4. On next separate C1 Intent attempt, observe whether source-valid L1 selection used the update; compare with fixed cheap response and original physical outcome.
5. On cue mismatch or harmful outcome, suppress selection, preserve source, and revise or revert cognitive applicability; existing L0 implementation remains unchanged only while self-directed L0 installation is not implemented. A future implementation may autonomously adopt a revised L0 routine without an external permission hierarchy.

**Do not require:** heavy ML training, weight changes, always-on L2, automatic threshold-based promotion, a new independent persistent memory database, or per-checkpoint learning. More sophisticated safe rollout or shadow testing may be added only after the minimal loop works.

## C4.6 Design acceptance cases (C4-01–C4-14; NOT RUN)

| ID | Case | Required result |
| --- | --- | --- |
| C4-01 | Valid source-bound one-Intent experience and target-specific approved update with exact owner revision | One authorized owner transition and audit reference |
| C4-02 | L2 narration proposes a fact unsupported by external evidence | Candidate only or reject; no OBSERVED/Memory truth laundering |
| C4-03 | Target is another Self, wrong owner or changed revision | No commit or cross-write |
| C4-04 | Replayed same C1 feedback after successful commit | No duplicate transition or experience count inflation |
| C4-05 | Missing authority, fake token, unsupported rule | No durable write; preserve error/reason |
| C4-06 | One experience yields three different C2 candidates | Independent target checks; no automatic triple-write |
| C4-07 | A correct prediction yields no valid change target | NO_UPDATE valid and no fabricated Learning success |
| C4-08 | L1 candidate selected with valid cue but S49 source/grant invalid | No physical Action issued; cognitive candidate may remain |
| C4-09 | L1 habit has UNKNOWN critical cue or mismatched World session | Abstain/fallback; no guessed match |
| C4-10 | Failure after a retained L1 habit | Counterexample retained; scoped suppression/revision or owner rollback, not erasure of C1 |
| C4-11 | Prior snapshot restored after session change | Historical cognition only; no automatic reenabling action/habit eligibility |
| C4-12 | Frequent L1 success suggests an L0 routine but no bounded runtime integration exists | Candidate remains uninstalled; not because Self must obtain permission to learn |
| C4-13 | CHEAP baseline matches learning in same easy environment | Retention/reuse can be recorded, but no claimed unique advantage |
| C4-14 | Legitimate bounded low-risk learning update inside existing authority | Can autonomously commit without per-event human or full science gate |

| C4-15 | Self finds and revises a model from one valid Intent experience within its compute budget | No per-experience human approval required; version/provenance retained through actual storage API |
| C4-16 | Self discovers a viable low-latency routine with feasible cue, deadline and legitimate embodied execution path | Autonomous adoption can be architecturally allowed; cannot claim existing Bug-0 runtime supports it until implemented |

## C4.7 Handoff and status

C4 completes the **candidate conceptual boundary** for v0.5 A/B/C: one Self with multiple legitimate Intent commitments (A); source-bound three-view present/cognitive checkpoints (B); one experience per attempted Intent result (C1); scoped 0..n understanding candidates (C2); condition-limited reversible cognitive reuse (C3); governed owner-local admission and rollback (C4). Whether architecture design is formally closed is a separate user decision; owner-specific implementation/tests remain pending.

**C4 ARCHITECTURE_DESIGN_COMPLETE / IMPLEMENTATION_PENDING / NOT IMPLEMENTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.** No main change, Minecraft run, LLM call, Memory/Habit write or new Action privilege is claimed.

## C4.8 Clarification of freedom versus authority (user correction, 2026-11-06)

The earlier phrase **'learning does not automatically expand Self's authority'** was too broad and must **not** be read as a permanent architectural limit on autonomy or self-development. **The agent's effective abilities may absolutely increase through learning**, including changing its own understanding, selection policies, skills, resource allocation and eventual L0 crystallization. Its actual limits are the Minecraft World and WorldBody laws, available embodiment/interfaces, and host cognition resources such as time, GPU, CPU and memory. If the agent's implementation currently lacks a skill installer, this is an implementation gap to solve rather than a philosophical ban.

The narrowly valid part of the old phrase was only: a new idea or memory does not by itself grant an unprovided *external* primitive, falsify a native observation, alter authoritative World physics or bypass the current adapter's actual technical validity constraints. S49/source/grant checks are present-day actuation interface mechanics and source integrity, not an outside authority deciding what Self is permitted to learn, believe or try within its World. Formal DEV/QUAL/SCIENCE evidence rules concern **our claims about experiments**, not the Self's subjective permission to explore.

Treat 'approved learning' in the above text as **validated use of an actual versioned implementation API**, not a human governor supervising every learning step. Revise any conflicting owner-specific design before treating it as executable; do not claim existing protected code already supports autonomous L0 installation.
