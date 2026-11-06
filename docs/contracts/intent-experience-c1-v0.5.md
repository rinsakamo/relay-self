# Unified v0.5 — Contract C1: Intent-outcome experience and understanding pair

> **Status: C1 CONCEPTUAL DIRECTION USER-ADOPTED / DETAIL OWNER REVIEW REQUIRED / NOT IMPLEMENTED.**
> Parent [#717](https://github.com/rinsakamo/relay-self/issues/717); Unified architecture [v0.5](../unified-architecture-v0.5.md); Contract A [Intent and Action](intent-slots-action-authority-v0.5.md); Contract B [three perspectives](persistent-cognition-three-models-v0.5.md).
> User decision 2026-11-06: **one actually attempted Intent whose result is assessed produces one experience**. Experience does **not** tick every control epoch, occur on every primitive Action, or depend on the 60-second cognition autosave.

## C1.1. One executed Intent attempt, one experience

A **C1 Intent Experience** is a bounded evidence-linked episode associated with **one specific attempted/implemented Intent instance**, its pre-action understanding and the best qualified assessment of its actual result.

```text
Retained episodic Intent (A; unique scoped identity)
  -> pre-execution model/cue/prediction reference (or NO_PREDICTION)
  -> actual execution attempt / skill with zero, one or several primitive Actions
  -> original S49/S15/S16 Action and WorldBody observations in sequence
  -> assessed Intent-level outcome (success / failure / partial / unknown)
  -> ONE experience record for that Intent attempt
  -> separately governed interpretation / hypothesis / memory or model update
  -> later independent opportunity tests whether understanding is reused
```

**Boundary:** an Intent can span several decisions, replans, S49 Actions, WAIT intervals and model consultations and still yield **one** Intent Experience. Each Action has its own distinct evidence and S16 status, but cannot automatically mint another completed Intent Experience. A native Action's `OUTCOME` is not a verified Intent goal achievement.

One instance's `COMPLETED`, `FAILED`, `INVALIDATED` or explicit `RELEASE` commitment transition and its **World-observed Intent result** must be recorded as separate dimensions. Existing [Current Intent Commitment](intent-commitment.md) terminal transitions are caller decisions; they do **not** themselves attest success or physical consequences. `RELEASE/INVALIDATED` following a real attempt may close the episode as aborted/failed/unknown; a non-attempted candidate or deferred Intent is **not** a physical experience.

**Implementation detail left to owner review:** mapping repeated physical attempts/retries under one persistent Intent to a well-defined episode identity. Default: one C1 experience per completed bounded **attempt** under an Intent; a genuinely new attempt after explicit closure/recommit is distinct, but ordinary Skill replans/primitive retries *within* that attempt do not create duplicate experiences. Do not reuse text-only `intent_id` across Self instances as a globally unique evidence key.

## C1.2. Timing — event/result driven, not a sampling clock

The experience is **finalized once the Intent's attempt has a qualified terminal assessment** (including a known failure or explicit UNKNOWN after an unresolved boundary). Qualification means separating the verified external readback from inferred achievement. It does not demand a success result: failure, loss, partial effect or outcome UNKNOWN are legitimate data.

- Capture the *before-understanding* (model/version, predicted outcome/conditions/confidence, or NO_PREDICTION) **before** seeing the relevant actual result; otherwise it is post-hoc explanation, not a prior prediction.
- During the attempt, continue collecting original action/source evidence without committing a completed experience each time a native Action closes. A useful provisional in-progress trace is allowed, **not counted as a second experience**.
- On attempted Intent terminal assessment, link the original native source sequence, World session, Intent/Skill/Action identities, observed consequence and uncertainties. If observation is still unavailable, record `UNKNOWN` without inventing success or indefinite blocking; later evidence can be linked as an **amendment to the same experience** under owner-controlled revision, not a duplicate experience.
- The record can be read immediately by later cognition, but durable Memory/Learning/Habit integration requires the existing proper authority. **Experience created != understanding changed != improvement proven.**
- No experience is forced merely by a new Present Projection, a new 60-second B checkpoint, slot scheduling, an observation-only tick, or a model-generated explanation.
- Environmental observations with no attempted Intent (e.g., sudden unsolicited attack) can still be historical Evidence and might motivate an Intent. C1 does not prohibit them or falsely label them as a completed executed-Intent experience.

**Time:** elapsed time and causal ordering should use their own attested source. One experience can span longer than the B autosave cadence; a checkpoint does not terminate the Intent or magically qualify its result.

## C1.3. Minimum logical experience fields (not a new storage API)

| Part | Logical content | Guard |
| --- | --- | --- |
| Identity | `self_id`, trusted `intent_instance_ref`, attempt/episode identity, Goal/standing-commitment refs where applicable | Prevent another Self/Intent's results from being reused |
| Before | Pre-execution SelfWorld/SelfBody/MySelf source refs, model revision, condition/uncertainty, prediction **or NO_PREDICTION** | Prediction time/order precedes consequence |
| Execution | Intent/Skill/Action refs, actual attempt phase, original S49/S15/S16 receipts, input clear/settling when relevant | Proposal/issue/Action OUTCOME each distinct from Goal result |
| After | Qualified native observations, elapsed interval, partial effects, failed/unavailable/unknown result, confounders | No invented WorldBody physical truth |
| Comparison | Prior model's testable expectation versus observed data; error/noncomparable/unknown | Do not label a narrative as causal fact |
| Interpretation | Candidate explanation or model applicability condition, source and uncertainty | No automatic Memory, Learning or Habit write |
| Reuse link | Future independent Intent attempt and resulting decision/outcome association, if any | No automatic generalization/advantage claim |

The first representation should be a **read-only association over existing owner-local receipts/episode Memory** where possible. Do **not** introduce a new universal event store, duplicate action lifecycle, alternative Memory owner or independent source of World truth without a demonstrated gap (Grand Null).

## C1.4. Bug-0 examples

| Intent attempt | Internal evidence | One resulting experience |
| --- | --- | --- |
| **EAT** | equip food, issue consume, source-qualified subsequent food/inventory observation | One EAT experience: verified eaten/failed/partial/UNKNOWN. `consume` issued is not proof food was consumed. |
| **EVADE** | choose direction, one or several MOVE Actions, post-clear movement and threat observations | One EVADE experience assessing **escape objective**, not one experience per MOVE. |
| **ATTACK** | orient/move, native attack command, later hit/damage/target-state evidence | One ATTACK experience; issued attack != landed hit != target dead. |
| **REST** | deliberate guarded inactivity, verified elapsed World ticks and measured recovery or no recovery | One REST experience if a real rest attempt was undertaken, even when **zero physical Action** was issued; WAIT alone != recovery. |
| **Standing HOMEOSTASIS** | persistent regulation may activate EAT/REST/EVADE episodically | No endless per-tick experiences for the standing commitment itself; each actually attempted episodic Intent may have one. |

## C1.5. Offline design negative/positive checks (C1-01–C1-10; NOT RUN)

| ID | Condition | Expected |
| --- | --- | --- |
| C1-01 | One EAT attempt has EQUIP + CONSUME + later native food change | One Intent Experience and multiple distinct Action/source refs |
| C1-02 | An EVADE attempt spans two MOVE Actions and an intermediate replan | One experience, preserving both MOVE consequences |
| C1-03 | Action is issued and S16 says OUTCOME, but goal readback unavailable | Intent result UNKNOWN; no fabricated success |
| C1-04 | ATTACK command is applied, but target remains alive or death unread | No automatic ATTACK completion/kill claim |
| C1-05 | Committed EAT remains deferred and never actually executes | Zero physical Intent Experiences; retained commitment remains |
| C1-06 | Valid REST involves intentional idle without primitive Action | One REST experience if qualified physical readback/attempt assessment exists; no WAIT-equals-recovery inference |
| C1-07 | A prediction is written after the observed outcome | Mark POST_HOC, cannot use as pre-registered prediction-error evidence |
| C1-08 | Replayed duplicate S16 event or repeated terminal assessment | Still one bounded Intent Experience, no double-counting |
| C1-09 | Same text Intent ID used in another Self/session or old World epoch | Do not cross-attribute observations, grants, predictions or experiences |
| C1-10 | A later qualified observation changes an initially UNKNOWN outcome | Amend/version the same experience, with original uncertainty and chronology intact |

## C1.6. Handoff to C2 and owners

**C1 decides the unit and timing of experienced evidence.** C2 decides *which understanding* may be revised (world model, body model, applicability, plan choice, cognition allocation); C3 addresses conditional reuse/crystallization; C4 retains real Memory/Learning authorization and independent outcome/qualification checks.

Reference code in audited WB DEV branch: `src/relay_self/action_outcome.py` provides S16 ActionOutcomeInterpretation; `src/relay_self/action_feedback.py` interprets exact Action/S16 evidence into bounded *proposed* feedback; `src/relay_self/learning.py` has revision-checked, authorized updates. These APIs **do not themselves implement one-experience-per-Intent aggregation**. Contract A's one-Self multi-Intent model and S49 sole physical issuer remain intact. Existing issue owners #537 (Action/Intent), #431 (Learning/Habit), #632/#633 (Body/World), and #619 (independent qualification/science) remain distinct.

**Classification:** DESIGN ONLY / USER-ADOPTED C1 UNIT / INTENT-LEVEL OUTCOME AGGREGATOR NOT IMPLEMENTED / B AND A PHYSICAL GATES UNCHANGED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
