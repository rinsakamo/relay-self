# Unified v0.5 — Contract C4: Governed learning admission, activation and rollback

> **Status: C4 DESIGN PROPOSAL / USER REVIEW OPEN / NOT IMPLEMENTED.** Prepared 2026-11-06 after user adopted the C3 direction. Parent [#717](https://github.com/rinsakamo/relay-self/issues/717), [C1 Intent Experience](intent-experience-c1-v0.5.md), [C2 Understanding Revision](understanding-revision-c2-v0.5.md), [C3 Conditional Crystallization](conditional-crystallization-c3-v0.5.md), [A physical authority](intent-slots-action-authority-v0.5.md), [B provenance](persistent-cognition-three-models-v0.5.md).

## C4.0 Principal distinction — cognition, retention and execution

**A Self should be able to learn autonomously within legitimate owner-local update authority, without conferring new physical authority on its models.** Owner-approved update rules may execute autonomously; each learning event does **not** require manual human consent. Model narrative alone is never such authority.

| Layer | May do | Must not do without a separately qualified owner |
| --- | --- | --- |
| Interpret C1 / propose C2 (MySelf, SelfWorld, SelfBody, L1/L2) | Evaluate discrepancies, formulate tentative hypotheses and candidate target revisions, compare against prior understanding | Rewrite World/WorldBody truth, normative Identity Specification, durable owner state or S49 source/grant |
| Governed retention (Memory/Belief/Learning/Capability/Habit owner's API) | Validate admissible evidence and update the precise existing target revision under an authorized rule; record provenance and reversibility | Write other owners' records, turn any hypothesis into a confirmed observation, create universal memory writer |
| Cognitive activation (Present / L1/Habit selector) | Use a retained, source-matching candidate within its allowed cues and revision; abstain/fallback on unknown or mismatch | Promote an L1 candidate to executable L0 or physical Action grant |
| Physical admission (existing A/S49, S14/S15/S16/WorldBody) | Execute only a valid present Intent/Skill/Action with current source, control channel, grant and eventual native outcome | Treat learning, experience count, L2 or habit selection as authorization or proof of physical success |

Neither a single omnipotent 'learning orchestrator' nor three separate memory databases are required. C4 routes updates to **existing actual semantic owner APIs**; an ontology label alone is insufficient to claim that the corresponding durable owner has been implemented. Where owner/authority is absent, the candidate remains provisional/read-only.

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

**Admission checks should be proportional to the requested authority.** A bounded self-model estimate or candidate forecast is cheaper to review than changing a motor reflex. For routine authorized owner-local scalar updates, validate target/revision/feedback/source and write once; do not insert mandatory L2, human approval, an expensive globally synchronized snapshot or an independent scientific evaluation into every DEV experience.

The minimal logical update request records: (1) experience/feedback ID, Self and source session, original World/Action/Intent consequence references; (2) target semantic owner/object ID and expected revision; (3) typed change and affected conditions/cues; (4) supporting/contradicting evidence and uncertainty; (5) authorized bounded rule or owner permission; (6) disposition plus recorded predecessor/new revision, provenance and rollback path. Replays, wrong owner, stale revision, forged permission, missing required native source and incompatible cues fail closed with a reason.

Preserve `NO_PREDICTION`, Action `UNKNOWN`, absent World outcome and uncertainty as distinct data. Learning can respond to failure; it cannot make a physical consequence certain merely by committing a preference update. One C1 experience may lead to zero or several independent target revisions, but each is separately admitted, without three automatic writes for the same physical observation.

## C4.2 State changes are not all the same

- **Evidence/experience retention:** original source-qualified C1 record and action/world receipt remain historical. Correcting a later interpretation does not mutate original observations.
- **Understanding revision:** SelfWorld, SelfBody or MySelf can receive *separately authorized* candidate model/applicability/competence changes. Normative Identity Specification and intrinsic Goal values retain their separate owner restrictions.
- **L1 habit retention:** a selected rule/cue may be persisted by the actual Habit owner only when it has valid condition scope, source and lifecycle; using existing `HabitCue`, `HabitRule`, `HabitRepertoire` is a candidate integration strategy, not proof these are already linked to the full Self.
- **L1 invocation:** checking a Habit cue is a read/selection activity. It does not itself mean the result was updated or authorized to drive S49.
- **L0 promotion:** always separate from L1 admission; requires bounded formal cue guard, safety/viability and deadline checks, counterexamples, owner review, reversible rollout and existing physical admission. **No automatic L0 executable reflex installation in v0.5 Bug-0.**

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
| **L0 accepted** | Owner-reviewed bounded execution guard and real-time safety/admission regression | Qualification/science proof unless separately run |

**Product-first, no over-gating:** a single-episode advantage over fixed L0 is *not* a required DEV progression condition, and cheap-equivalent remains a valid null. Developing the read-only replay/retention path should not wait for full V science. But do not promote source-unattested or unimplemented changes into claims of actual learned policy improvement. #619 QUAL/SCIENCE remains independent.

## C4.5 First Bug-0 implementation slice

1. Start from one source-qualified C1 attempted Intent Experience such as EVADE motion/ice or EAT with known/readback UNKNOWN outcomes. No separate event warehouse.
2. C2 computes *one bounded conditional understanding candidate* (source and target owner explicit), preferably initially in read-only/shadow. `NO_UPDATE` is an acceptable result.
3. Route through the **existing** specific Learning/Memory/Habit owner; only its current revision + authority can admit a retained change. Favor simple tags/typed cues to reuse the episode. Existing WB DEV `learning.py` demonstrates a revision/authority protected **scalar preference** update, not a generic approval of all proposed beliefs; `habit.py` provides read-only cue selection.
4. On next separate C1 Intent attempt, observe whether source-valid L1 selection used the update; compare with fixed cheap response and original physical outcome.
5. On cue mismatch or harmful outcome, suppress selection, preserve source, and request bounded C2 revision or owner rollback. L0 unchanged unless later independently accepted.

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
| C4-12 | Frequent L1 success suggests L0 rule but formal safety/deadline gate absent | L0_PROMOTION_PROPOSED only, never active L0 |
| C4-13 | CHEAP baseline matches learning in same easy environment | Retention/reuse can be recorded, but no claimed unique advantage |
| C4-14 | Legitimate bounded low-risk learning update inside existing authority | Can autonomously commit without per-event human or full science gate |

## C4.7 Handoff and status

C4 completes the **candidate conceptual boundary** for v0.5 A/B/C: one Self with multiple legitimate Intent commitments (A); source-bound three-view present/cognitive checkpoints (B); one experience per attempted Intent result (C1); scoped 0..n understanding candidates (C2); condition-limited reversible cognitive reuse (C3); governed owner-local admission and rollback (C4). Whether architecture design is formally closed is a separate user decision; owner-specific implementation/tests remain pending.

**DEV_ONLY / C4 DESIGN_PROPOSAL USER_REVIEW_OPEN / NOT IMPLEMENTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.** No main change, Minecraft run, LLM call, Memory/Habit write or new Action privilege is claimed.
