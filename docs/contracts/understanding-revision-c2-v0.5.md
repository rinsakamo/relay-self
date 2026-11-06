# Unified v0.5 — Contract C2: Understanding-revision targets

> **Status: USER-ENDORSED CONCEPTUAL DIRECTION / DESIGN ONLY / IMPLEMENTATION PENDING.** This is a record of the 2026-11-06 discussion, not a tested or owner-approved update API. Parent [#717](https://github.com/rinsakamo/relay-self/issues/717), [C1 Intent Experience](intent-experience-c1-v0.5.md), [B three-model projection](persistent-cognition-three-models-v0.5.md), next [C3 crystallization](conditional-crystallization-c3-v0.5.md).

## C2.1 One source-qualified experience, zero or more proposed revisions

C1's one attempted-Intent experience may ground **zero or more distinguishable understanding-revision candidates** in MySelf, SelfWorld and SelfBody. This is **not** one experience = one write or one reason. Interpretations can disagree and remain UNKNOWN. No candidate can overwrite original physical evidence or normative Identity Specification.

| Revision target | Question | Example |
| --- | --- | --- |
| Predictive model | What is expected to occur? | Movement changes on a slippery floor |
| Applicability condition | Under which context is that model valid? | Old walk displacement rule applies to ordinary floor, not necessarily ice |
| Plan/selection tendency | Which feasible Plan or Intent response is preferred, given goals and costs? | Brake earlier on sliding floor, retreat before EAT under threat |
| Cognitive allocation | When is cheap L0/L1 enough, when should L2 inspect further? | Unknown surface or repeated mismatch -> limited L2 escalation |

Those changes are distinct from revising intrinsic goal values, altering normative identity, authorizing an Action or making WorldBody itself obey a new rule. A changed Plan forecast does not automatically change the value attached to that Goal.

## C2.2 Two stages: interpretation versus retained revision

1. **Tentative interpretation:** use Before/Prediction vs actual source-qualified After from the same C1 experience. Include target, proposed change, expected effects, model/owner revision, applicable cues, counterexamples, confidence/UNKNOWN, alternate hypotheses and source refs. A textual L2 explanation does not prove the proposed cause.
2. **Governed retained revision:** existing designated Memory/Belief/Learning/Capability/Habit semantic owner reviews the proposal, valid evidence, authority and revision before accepting a change. Rejection, abstention or no update is legitimate. The original C1 experience remains attributable and unmodified.
3. **Next independent opportunity:** verify whether the retained candidate was actually read and changed a prediction/decision; behavior change is not automatic success or scientifically established improvement.

For example, a slower-than-predicted EVADE movement on ice could suggest either a SelfWorld surface rule or a SelfBody performance limitation. Without contrastive observations, preserve both *as hypotheses* instead of declaring one causal truth. A subsequent ordinary-floor trial may discriminate them. **Prefer the smallest justified revision**, but allow L2 to propose a new model structure rather than only adjusting a scalar when existing applicability cannot explain the observations.

## C2.3 Minimum proposed revision association (logical shape, not new owner)

- Source: trusted C1 experience ID, intent attempt, before model revision and original action/WorldBody provenance.
- Target: one of the four typed revision kinds; model lens (MySelf, SelfWorld, SelfBody), actual existing semantic owner and current target revision if available.
- Proposal: *before -> after* candidate, scope/cues, evidence supporting and contradicting, uncertain parts, predictions for subsequent tests.
- Governance: requested authority, disposition (proposed, retained, declined, unverified), revision/rollback reference and who/what made the update.
- Reuse: downstream observation and selected behavior may refer back without turning predicted consequences into observations.

No global Memory database, automatic triple-write from the three views, unrestricted mutator or extra physical issuer is authorized by this document. Existing WB DEV `action_feedback.py` interprets particular S16 Action evidence; `learning.py` authorizes bounded owner-local updates. Neither presently proves the complete three-model C2 understanding-update loop.

## C2.4 Provisional checks (C2-01–C2-07, NOT RUN)

| ID | Input | Expected |
| --- | --- | --- |
| C2-01 | Prediction agrees with observed outcome | Legitimate zero-update choice |
| C2-02 | A single failure can be explained by both floor and fatigue | Preserve alternative hypotheses and UNKNOWN causes |
| C2-03 | Source missing, session mismatched or prediction made post-hoc | Reject qualified causal update; preserve raw evidence status |
| C2-04 | MySelf, SelfWorld and SelfBody all propose revisions from one Intent experience | Attributed proposals, no automatic multiple writes |
| C2-05 | Model is correct in ordinary conditions, fails on ice | Allow bounded applicability correction without erasing original rule |
| C2-06 | L2 suggests changing values/Identity or WorldBody physics from a mismatch | No such authority; owner-specific review required |
| C2-07 | Retained revision changes a later decision but not objective outcome | Report reuse/decision change, not proof of improvement |

**C3 handoff:** C2 produces retained or candidate condition-scoped understanding. C3 determines when it can be reused more cheaply, decrystallized or considered for a separate formal L0 gate. **C4** retains the authority/verification details. DEV, qualification and science are independent gates.
