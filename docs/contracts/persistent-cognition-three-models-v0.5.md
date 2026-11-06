# Unified v0.5 — Contract B: Persistent Cognition and three Self-model projections

> **Status: B-D0 DESIGN_DRAFT / REVIEW OPEN / NOT IMPLEMENTED.** Parent [#717](https://github.com/rinsakamo/relay-self/issues/717), Draft PR [#718](https://github.com/rinsakamo/relay-self/pull/718). Started 2026-11-06 after the user closed **A architectural design** as ARCHITECTURE_DESIGN_COMPLETE / IMPLEMENTATION_PENDING. A's approved concepts remain frozen; owner/API/World/qualification are separate gates. This document does not create new memory writers, physical World facts, runtime controllers or learning authority.

## B0. Design question and Grand Null answer

**How can one Self keep its own history, goals and identity while MySelf / SelfWorld / SelfBody change with each observation, without creating three conflicting memories or confusing an estimate with truth?**

**Grand Null default: reuse existing semantic owners and read-only projection interfaces.**

- [Canonical ontology](../ontology.md): **Persistent Cognition** (Identity Specification, Self-Model, Other/Relationship Model, Goal, Commitment, Question, Evidence, Assessment, Belief, Memory, Appraisal Disposition, Capability Model) is a family of distinct semantic objects, **not** necessarily one implemented store. **Present Projection** (Working Self, Situation Model, Current Appraisal, Attention, Active Goal/Question, Tension, Current Intent) is the current, derived view.
- [Architecture](../architecture.md) and [runtime principles](../runtime-principles.md): `Present_t = Project(PersistentCognition_t, BoundaryState_t, Events_t, Time_t)`; normally recompute Present rather than persisting it as a second truth.
- Actual **`main:src/relay_self/persistent_cognition.py`** has a deliberately **narrow**, immutable `PersistentCognition(identity, memories, appraisal_dispositions)`, `IdentitySpecification`, governed `Memory`, schema v2 and save/load. It **does not currently persist every conceptual Goal, Belief, Capability Model or all of MySelf**. Their ontology is not evidence of an implemented shared database.
- The source-audited [WB development branch](https://github.com/rinsakamo/relay-self/tree/b9b2acf57ed55a87d3a58995c2e16a655aaf1024) has read-only `SelfWorldView` (`src/relay_self/self_world.py`), `SelfBodyView` (`src/relay_self/self_body.py`) and Mineflayer projection adapters. It is **not** proof that those branch changes are in main or already integrated with one real Self. Both are immutable one-epoch views, not persistent owners; do not re-create them under new classes or stores solely for v0.5.
- Contract A's standing HOMEOSTASIS is a **Self-owned long-lived regulatory Goal/Commitment**. Its **current Need pressure** is a Present projection inferred from body evidence. Persisting the standing commitment and recording individual EAT/REST execution Intent history are distinct; B does not fabricate an existing homeostasis database or change S49.

**Decision target:** one logical Self identity, existing individually governed durable semantic owners, three *observer-relative lenses* on current evidence, one derived Present/Working Self, and explicit provenance for each field. Not three LLM agents, three always-on autonomous worlds or three persistent data lakes.

**Source-routing refinement (user direction, 2026-11-06):** Persistent Cognition is a **primary** input for MySelf and SelfWorld; WorldBody-attested body information is the **primary** input for SelfBody; the independently interpreted three views then contribute to Present Projection. This is an *asymmetric default*, **not exclusive routing**: SelfWorld still needs current external World observations, SelfBody needs approved past bodily experience and capability estimates, and MySelf can consult present body/world consequences. See §B9.

## B1. Ownership mapping — what exists, what may be projected

| Concept / update | Semantic owner or state authority | MySelf / SelfWorld / SelfBody role | B permission |
| --- | --- | --- | --- |
| **Identity Specification / normative constraints** | Existing governed `PersistentCognition.identity` and specification authority | MySelf can read/use the canonical identity; its inferred Self-Model is **not** Identity Specification | Read-only projection; no normative update from experiences or LLM narration |
| **Self-Model / competence & Capability Model** | Existing conceptual Persistent Cognition objects; code owner is consumer-specific and must be audited before writes | MySelf reflects fallible self-understanding; SelfBody may display body/compute capability estimates | Transient estimates permitted; durable change requires existing governed owner/Contract C |
| **Relationship / Other Model** | Governed persistent Other/Relationship semantic objects where actually implemented | SelfWorld hosts **SelfOther**: what this Self predicts/infers of another agent | No writing to another Self's MySelf; no claim to see other's internal state |
| **Evidence / observations / Body interoception** | World/WorldBody / native adapter attests only its qualified fields; Self's Evidence semantics retain source refs | SelfWorld sees bounded exterior facts; SelfBody sees body/interoception; MySelf may refer to same evidence | Read/correlate with source; cannot assert outside coverage or invent physical consequence |
| **Belief / Assessment / Prediction** | Existing BLF/PRD/assessment owner when available; otherwise provisional read-only cognition | Each model may present differently scoped interpretations of **one** source | Label inference and uncertainty; projection is not an authorized belief write |
| **Memory / Appraisal Disposition** | Actual `PersistentCognition` and other explicitly governed Memory/Habit owners as audited | Views reference/retrieve approved retained material | Never persist merely because projected, remembered, selected or LLM-generated |
| **Goal / Question / standing HOMEOSTASIS** | Self-scoped persistent semantic commitment; existing owner or future owner-reviewed lifecycle where implementable | MySelf sees retained aims; SelfBody supplies Need evidence; SelfWorld supplies opportunities/threats | View / propose activation, not silent create/close of a durable commitment |
| **Current Need / Tension / Appraisal / working attention** | Present Projection, derived from relevant source objects and time | Source-specific activation can be present in all three lenses | Recompute each epoch; changes do not automatically mutate persistent values |
| **Execution Intent / Plan / Skill / Action** | Contract A Intent scope and existing S49-Skill/Action owners | Models contribute advisory proposals | No new physical authority or automatic learning privilege |

Different source objects may influence the same current concern but **do not become one ontological item**. Example: a hunger reading from WorldBody, SelfBody's inferred fatigue, a standing HOMEOSTASIS commitment and a current EAT Intent are four distinct facts/estimates/commitments. Their interrelations are source-bound links, not duplicate independent sources of truth.

## B2. Immutable three-model readout — first practical scope

**Initial Bug-0 v0.5 projection:** recompute narrow views for the same Self and current epoch using the existing WB/Present APIs where possible.

- **SelfWorld**: observer identity, World session, qualified `native_seq/request_id`, entity coverage radius/cap/truncation, nearby threats/food/obstacles/affordances, freshness, and explicitly tagged `OBSERVED / REMEMBERED / INFERRED / PREDICTED / HYPOTHETICAL / UNKNOWN`. A missing entity outside bounded coverage **is not proven absent**. Predictions or an Other Model are not hidden World facts.
- **SelfBody**: session and qualified body `native_seq/request_id`; position, food, health, saturation and supported sensed or readback facts; distinguish `OBSERVATION / INTEROCEPTION / BELIEF / HYPOTHESIS / PREDICTION / UNKNOWN`. Fatigue/energy may be independently P1/M-qualified or UNKNOWN. Input clear, S16 closure, physical settling and genuine recovery are separate claims.
- **MySelf**: **initially a derived projection, not a new persisted MySelf database or owner**. Minimum content: Self ID and canonical identity *reference*, retained Goal/Intent refs, current standing HOMEOSTASIS Needs, current questions, recent qualified outcomes and tentative ability/condition estimates with uncertainty. A model's eloquent self-description **does not edit Identity Specification**.

**Join contract:** views about one decision epoch must refer to the same `self_id` and compatible world/session/actor, and carry precise native observation refs when a field is World-bound. They may use different native sequences if explicitly ordered, coverage/age is bounded and the consumer records what was observed **when**. Never merge a new SelfBody with an old SelfWorld into a fictional synchronized snapshot. Missing join evidence gives `UNAVAILABLE / STALE / UNKNOWN`, not a fabricated `observed` value.

The WB implementation currently accepts `SelfBodyView.self_id` optionally for legacy compatibility but requires a validated identity for a genuine `SelfWorld` join; **the v0.5 join contract requires same legitimate Self identity**. Do not silently treat an absent optional value as matched.

## B3. Read and revision path: evidence does not equal persisted update

```text
Native World / WorldBody and host observations
  -> qualified source-bearing Evidence / Interoception
  -> immutable SelfWorld and SelfBody one-epoch views
  -> MySelf/Working Self, Need and Intent-signal Present projection
  -> guarded prediction, appraisal, comparison and proposed hypotheses
  -> (separate authorized owner path, only when applicable)
       Belief/Capability estimate revision OR governed Memory/Disposition integration
  -> rebuild next Present from approved owners + fresh source
```

**Do not** let the same observed consequence trigger three automatic writes by each model. Views may generate **candidate assessments with separate target and uncertainty**, but an existing semantic owner decides whether a state transition or persistence is valid. B defines provenance and update *routing*, not the learning/admission/persistence gates themselves; Contract C governs improvement, tested transfer and policy/value learning.

Each projected claim must preserve as relevant: `self_id`, source kind, `world_session`, `native_seq`, `request_id`, `observed_at` or attested ordering/age bound, source provenance, field coverage, `OBSERVED / INFERRED / REMEMBERED / PREDICTED / UNKNOWN`, and producer/read-model generation. When native time is not qualified, `observed_at` cannot be invented; source epoch/order is used with its limitation.

Original evidence may remain historically true as *an observation at that earlier time* after a newer World observation invalidates a Present projection. Historical evidence must not be rewritten as current World truth or deleted merely to make views agree.

## B4. Identity, SelfOther and boundaries

- **One Self is logical owner of Intent scope, not one universal memory owner.** Same-self continuity across World restarts requires separately justified persistent identity/commitment reconstruction and fresh source binding. `self_id` continuity does **not** license reuse of old `world_session`, Action grants, live Intent owner handles, source freshness or VRAM reservations.
- **MySelf is epistemic and fallible**: competence/fatigue estimates and its sense of identity are assessments. Normative `Identity Specification` is separate even if the same language model renders both in a conversational answer.
- **SelfOther is a representation of another agent**, situated within SelfWorld; the agent may act differently from the observer's prediction. Its beliefs/goals are neither observable private states nor authoritative facts. The same external agent can have inconsistent representations in different Self instances without either forcing an update to the other's model.
- **No contradictory write reconciliation by coercion:** when an observed body effect contradicts an old self-belief, preserve source and discrepancy, reproject the current view, and submit an appropriately scoped candidate revision to the actual belief/Capability owner. Do not overwrite the observation to agree with memory, treat belief as granted physical authority or overwrite normative identity.

## B5. Standing HOMEOSTASIS through the three lenses

The A-homeostasis annex defines the standing commitment and episodic EAT/REST/DEFEND Intent boundary. B specifies where the changing information appears:

```text
WorldBody source: genuine hunger/health, native movement, attack consequence
   -> SelfBody: subjective hunger/fatigue/performance and uncertainty
   -> SelfWorld: threat/food/opportunity/visibility and uncertainty
   -> MySelf: retained HOMEOSTASIS commitment + prior experiences + tentative capability
   -> Present: Need/Tension + eligible Goal/Intent signal readout
   -> A/S49: admitted action, if source/grant/channel allow
   -> next WorldBody readback -> new Present
```

Example: EAT remains committed but blocked when a zombie is near. SelfWorld may update its threat estimate while SelfBody's hunger estimate stays high. MySelf can retain that EAT remains a goal. None of these projections consumes food, proves that a zombie died, applies a WorldBody recovery coefficient or authorizes the next Action. A physical effect, its source and real value must be observed before reinterpreting the relevant pressures. Durable learning/changed preferences await Contract C.

## B6. Minimal read-model interface for owner review (illustrative, not actual Python symbols)

```text
project_present_for_self(
  identity_ref, approved_persistent_read_refs,
  qualified_world_view?, qualified_body_view?,
  latest_original_action_outcomes?, source_epoch
) -> {myself, selfworld, selfbody, present, evidence_refs, unknowns}
```

This is an **API boundary sketch**, not a requirement to implement a new `project_present_for_self` function. First see whether existing `compose_self_world_view`, `compose_self_body_view`, Present projections, cognition datum rendering and current owner readouts already provide the needed joined fields. If not, add the **smallest read-only association layer** that is demonstrably missing. It cannot write Memory, adjust Identity Specification, approve a grant or create physical Actions.

Expected ownership outcome: **no new persistent SelfWorld store, SelfBody store, MySelf store, generic provenance database or universal Self controller by default**. A source-qualified immutable join/correlation view is permissible if needed and if its fields cannot already be represented with existing owner data.

## B7. Design acceptance tests (B-01–B-14, NOT RUN)

| ID | Case | Contract result |
| --- | --- | --- |
| B-01 | One native event contributes to SelfWorld, SelfBody and MySelf | Three derived views may reference one genuine source; **zero automatic durable writes** |
| B-02 | New native observation contradicts cached Present | Reproject current view; old observation remains historical evidence, not current truth |
| B-03 | Native entity list truncated by coverage cap | Unlisted entity status UNKNOWN, never confirmed absent |
| B-04 | Enemy visibly attacks | Other's hidden intent/belief not promoted to OBSERVED/World fact |
| B-05 | Same `entity_ref` appears in two different Self observers | Separate SelfOther beliefs and observer scope; no cross-Self memory overwrite |
| B-06 | Session/body mismatch between World and Body view | No synthetic synchronized Present; reject or expose source discrepancy |
| B-07 | Source missing `observed_at_ns` | Do not fabricate wall/native time; maintain attested seq ordering |
| B-08 | LLM says Self is healthy despite qualified low health | Normative/observed health unchanged; inferred claim marked uncertain |
| B-09 | A good Action outcome but no actual approved Memory integration | No new Memory or disposition record |
| B-10 | MySelf projection includes identity directives, then a model changes its narrative | Persistent normative Identity Specification remains unchanged |
| B-11 | Old World session restart with same Self identity | Self identity may continue but old source/grant/slot/in-flight owner not revived |
| B-12 | HOMEOSTASIS pressure changes, EAT remains deferred | Readout and signal change without silent EAT commitment replacement or WorldBody write |
| B-13 | A prior learned body capability estimate conflicts with native effect | Preserve mismatch and candidate reassessment; do not alter native evidence |
| B-14 | SelfWorld/SelfBody/MysSelf projection references out-of-scope or unqualified WB draft code | Not claimed merged into main or accepted for physical admission |

## B8. Open review choices, staged delivery and classification

**B-D0 (this document):** decide three-lens *read* semantics, ownership mapping, identity boundaries and minimal cross-model provenance, while listing exact remaining decisions. Status **B_DESIGN_IN_PROGRESS**, not DESIGN_ACCEPTED.

**B-D1 owner review:** identify exact read API/current implementation paths at main and WB #669; determine (a) whether a MySelf projection can be assembled from current owner reads without a new class, (b) which owner can reconstruct standing HOMEOSTASIS/Goal state across a process restart, (c) source-freshness and same-epoch join requirements, and (d) whether any persistent object needs new schema/authority (Grand Null). These are still *open*.

**B-I0 offline (future):** run B-01–B-14 with fixtures using exact existing WB/Persistent Cognition and S owner contracts. A fake `self_id`, copied source ref or synthetic field must not be treated as authenticated source. Document actual tests and failures before claiming pass.

**B-I1 integration (future):** read-only binding of the narrow three-model Present to original S49/source-bound events, optional DEV World only under existing grant and owner oversight. No automatic Memory write or L0 policy promotion.

**Handoff to C:** C may propose governed updates from source-qualified experience, but B's projections do not decide *whether* cognition improved, warrant an update, or authorize Memory/Habit/Skill/weights changes.

**Hard guard:** main unchanged; S49 original physical issuer unchanged; prior WB/M/L branch achievements are not one integrated World run. `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN` remain distinct from a complete design document.

---

## B9. Asymmetric source routing and MAGI-style cognitive scopes (user-selected direction, 2026-11-06)

> **DESIGN DIRECTION / MODEL-AND-DATA-ROUTING ONLY / IMPLEMENTATION NOT CLAIMED.** This section clarifies what the three observer-relative models actually do. The Evangelion MAGI analogy is about **division of evaluative responsibility**, not three equal authoritative voters, three personalities, three autonomous LLMs or independent memory stores.

### B9.1 Primary upstream paths

\`\`\`text
 Governed Persistent Cognition                 External World / WorldBody
 (identity, goal, belief, memory,                 (physical state, entities,
  capability, relationship, ...)                  effects, time, resources)
               |                                        |
       +-------+-------+                       +--------+--------+
       v               v                       v                 v
    MySelf         SelfWorld <---qualified World observations   SelfBody
 (self-history,   (environment, other agents,              (body sensation,
  values, goals,   uncertainty, causal expectations)        dynamics, limits)
  competence)                                                ^
       ^             ^                                       |
       |             |          approved past body experience / capability
       +-------------+-------------------+----- from Persistent Cognition
                      qualified cross-view evidence
               \                 |                 /
                \                |                /
                 v               v               v
                     Present Projection
          (Working Self, current appraisal, attention,
           Needs/Tensions, active Goals, Intent signals)
                                |
                    existing Contract A / S49
                         physical admission
                                |
                  World/WorldBody actual effects
                     -> next source-qualified epoch
\`\`\`

**This is a flow of reading and deriving cognitive assessments, not a call graph, hardwired service topology or write-authority graph.** A stored prior observation can be in Persistent Cognition while new source-attested WorldBody data is transient. External data must pass the current owned boundary adapter; SelfBody does **not** bypass the S49 or WorldBody authority boundary to read private physics parameters.

| Model | Primary information source | The question it evaluates | Necessary secondary access |
| --- | --- | --- | --- |
| **MySelf** | Persistent Cognition: Identity Specification reference, Goal/Commitment, approved memory, Self-Model/Capability estimates | What do I aim for, what do I believe I can do, what is this event's meaning for my continuity and commitments? | Fresh body/world outcome via qualified views; actual identity directives remain governed, not writable by the viewpoint |
| **SelfWorld** | Persistent Cognition: prior evidence, world beliefs/Other Models, remembered causal regularities **plus fresh observed World** | What exists or may happen outside me, and what does this imply about other agents and opportunities? | Qualified SelfBody state as needed for egocentric distance and affordance estimation; no other Self's private state |
| **SelfBody** | External WorldBody/body-sensor/interoceptive observations and their time, provenance and reliability | What is my body doing/able to do, how strained or impaired does it seem, what may happen if I act? | Approved remembered bodily experience, Capability Model and predictive history; no private WorldBody state or coefficient edits |

**World versus WorldBody:** SelfWorld's live factual feed is the **World-side external observation**, including perceived entities and terrain. SelfBody's live factual feed is **WorldBody/body-side observation** (body readback, health/food, movement, sensory consequences), although a Mineflayer Present event can carry both. One external snapshot may lawfully contribute to multiple viewpoints **without assigning the full snapshot's authority to each inference**.

### B9.2 The three are active interpreters, not merely mirrored data columns

Each model can **interpret, forecast, notice discrepancies, judge uncertainty and propose a current appraisal or Need/Question/Goal candidate** within its remit. "Read-only view" means that such computation has **no unconditional right to mutate external truth, existing Persistent Cognition, another Self, S49's Action state or learned policies**. It does not mean the model is cognitively passive.

Example of one zombie encounter:

- SelfWorld: recent coverage suggests a zombie is approaching; remembered encounters inform a **prediction**, not an attested hostility mind state.
- SelfBody: observable health/hunger and qualified fatigue-like performance suggest the body is struggling; missing P1 source remains **UNKNOWN**.
- MySelf: retained HOMEOSTASIS and an EAT Goal weigh against a threat-related commitment, with remembered experience and uncertain competence.
- Present: **keeps all three attributed claims**, including divergence, and derives current appraisal/Need/Intent activations for Contract A. It need not use **majority voting** or force a consensus value.

The internal mismatch may itself trigger inquiry or optional bounded L2 deliberation, but cannot authorize a physical Action, store a Memory, revise Identity Specification or assert that a proposed explanation is true.

### B9.3 Present is an integrative projection, not a fourth owner

The actual conceptual order is:

1. **Retained source objects and evidence** remain at their genuine persistent or external owners, unchanged by rendering.
2. **Three specialized interpretations** read whatever source is valid for their remit; source role is **primary**, not exclusive.
3. **Present Projection** combines currently relevant conclusions, uncertainty, tension, attention and execution-Intent activity. It may expose conflicts rather than hide them.
4. **S49** admits any actual Action using Contract A's authenticated current Intent/source/grant/physical-channel checks.
5. **New effects** yield a new epoch of observations and new projections; only separate governed integration may update persistent beliefs, memory or learned competence (Contract C).

Present can be recomputed at the next epoch from approved sources and retained commitments. It is not a third/fourth Memory writer, an omniscient synchronizer, a solver guaranteeing convergence or a runtime Self singleton. A Self's continuity is not guaranteed by reusing stale snapshots after World/session restart.

### B9.4 New review controls (B-15–B-21; NOT RUN)

| ID | Case | Required result |
| --- | --- | --- |
| B-15 | Persistent Memory refers to a zombie previously observed, but current World coverage is incomplete | SelfWorld can remember or infer, but must not label enemy's current presence/absence OBSERVED without fresh evidence |
| B-16 | WorldBody reading shows low food, while MySelf recalls recent eating | SelfBody retains qualified current reading; MySelf and Present may disagree without overwriting observed food or Memory |
| B-17 | Old bodily capability evidence is useful for predicting a new movement | SelfBody may reference approved experience as a PREDICTION, not promote it to WorldBody-authoritative observation |
| B-18 | MySelf, SelfWorld and SelfBody output conflicting recommendations | Present preserves source/confidence per model; no synthetic majority vote or automatic S49 issue |
| B-19 | One Mineflayer Present carries both entity and body fields | Both specialized views may use their proper fields with separate origin/field qualification, without duplicating semantic owners |
| B-20 | A model emits a revised belief or new fact during interpretation | No durable mutation until its actual approved semantic owner applies a governed update |
| B-21 | SelfBody's native source session has advanced while SelfWorld refers to an older epoch | Record bounded, explicitly ordered disagreement or mark stale/unavailable; never invent synchronized observation |

**Review open:** exact existing S/WB/Present adapter join points, available MySelf inputs and per-field source age budgets still need owner approval. Neither this refinement nor an older WB-branch class is a new executable contract. Keep B \`DESIGN_IN_PROGRESS / OWNER_REVIEW_REQUIRED\`.

---

## B10. Cognitively reachable World and Body snapshots (user-selected 2026-11-06)

> DESIGN DIRECTION / NOT A NEW RUNTIME OWNER OR EXECUTABLE API. The relevant snapshot is **the world and body within the reach of SelfWorld and SelfBody cognition**, not the Minecraft server's full state.

### B10.1 Two distinct snapshots

**Qualified observation snapshot** means currently sampled, permitted World/WorldBody facts within actual observer coverage. Preserve world session, native sequence, request ID, observation origin, radius/cap/truncation where available, and known sampling age. Existing WB WorldObservation and BodyObservation already provide bounded source-qualified readouts.

**Cognitive snapshot** means the read-only state that SelfWorld or SelfBody can currently represent from those observations **and** earlier approved Memory, belief, prediction, hypothesis or interoceptive information. Each reading keeps its individual origin and age, not a single fictitious World time. Existing WB SelfWorldView and SelfBodyView are compatible initial mechanisms; they are not independent persistence owners.

World/server state may contain hidden entities, unobserved chunks or actual private body parameters. These are **not automatically exposed to Self**. A remembered entity may appear in SelfWorld, but is not currently OBSERVED. Fatigue not attested by an authorized body source remains WorldBody-UNKNOWN even if SelfBody predicts impairment.

### B10.2 Model-specific views flow into Present

World observation -> SelfWorld (current external surroundings + old world beliefs/Memory).
WorldBody / body interoception -> SelfBody (current physical sensing + body history/Capability).
Persistent Cognition -> MySelf (identity reference, continuing commitments, experience).
All three -> Present Projection (current source-qualified Need, appraisal, tension, Goal/Intent signals).

The three source epochs need **not** be identical. Join only compatible Self/session identities and explicitly ordered source readings, retaining per-field freshness, inference level, mismatches and UNKNOWN. A Present projection does not materialize an omniscient full-world or fully synchronized physical snapshot.

Cognitive reach is **epistemic rather than a literal single sensing-radius limit**: the Self may know of a distant place from memory while its current condition is unknown. Observed area, remembered area and predicted possible area remain different.

### B10.3 Implementation restraint

Reuse existing WB partial projections and original external source. Avoid a whole-server API, periodic giant world copy, new global world registry or new self-memory owner. External World saves/checkpoints may support DEV reproducibility, but they are not Self's sensory experience. Any requested new observation must use its already legitimate source/authorization path, not unrestricted World access.

### B10.4 Extra design negative controls (B-22 through B-26, NOT RUN)

| ID | Input | Required result |
| --- | --- | --- |
| B-22 | A zombie is remembered at a location outside current coverage | REMEMBERED / PREDICTED / UNKNOWN, never current OBSERVED |
| B-23 | Truncated entity sampling or capped coverage | No global absence/safety inference |
| B-24 | SelfBody estimates hidden fatigue with no qualified WorldBody fatigue | Estimated subjective condition only; physical truth UNKNOWN |
| B-25 | SelfWorld and SelfBody have ordered but different native sequence values | Explicit individual source ages; no fabricated synchronized World |
| B-26 | An operator has a complete offline World save invisible to Self | Not used as SelfWorld perception or SelfBody sensation |

**Decision:** B adopts partial, cognition-reachable, source-tagged snapshots. Current observed reality, remembered evidence, inference, predictions and UNKNOWN are not collapsed. No implementation, new authority or owner approval is implied.

---

## B11. Periodic autosave of cognitive snapshots (user-selected MVP direction, 2026-11-06)

> **B DESIGN DECISION / NOT IMPLEMENTED.** The initial snapshot mechanism is a **configurable fixed-interval autosave** of the *currently cognitively reachable* SelfWorld and SelfBody readouts. No full server World snapshot, special always-on event-sourced capture pipeline, or model inference on every tick is required.

### B11.1 Minimal behavior

1. On a configured interval (a tunable implementation setting, not a hard-coded law of cognition), serialize the **latest already-available** source-qualified SelfWorld and SelfBody cognitive views or their minimal read-only representations. If a view is unavailable, save its explicit UNKNOWN/UNAVAILABLE status; do not force a World read, Action or L2 call solely to fill the checkpoint.
2. Capture the same checkpoint's self identity, world/session, checkpoint time and per-view *original observation* native sequence/request, coverage/truncation, origin, age/freshness and evidence/approved-Memory references. Different model observation times are allowed and must **not** be rewritten to the autosave timestamp.
3. Use bounded local snapshot retention or rotation and simple atomic save/failure reporting. Save failures may retain the previous checkpoint; they must not block the real-time L0/S49 path or imply that no new World event occurred.
4. Present Projection is recomputed from current qualified inputs and the three cognitive views as needed. A saved snapshot is an **operational checkpoint/cache**, not new authoritative Evidence, an approved durable Memory, or a new Persistent Cognition writer.

**Important temporal separation:** autosave frequency does **not** define Action observation freshness. S49 may require a newer, differently timed native observation immediately before admission and must keep existing source/grant/clear/settling checks. A snapshot saved 1 second ago can still contain a 20-second-old entity reading; saving does not make that reading fresh.

### B11.2 Recovery and evidence

A checkpoint from a previous World session can be **read as historical cognitive context** if source identity and permission allow, but it cannot be restored as a present native observation, live action authorization, current body truth, or confirmed active physical Intent. After restart, fresh source-qualified body/world data is required to establish a new Present and physical eligibility. Independently governed standing Goal/Commitment persistence is still a separate responsibility.

For first implementation, favor the **smallest snapshot file and interval configuration that actually supports the DEV loop**; a more elaborate differential/event stream, auto-learning archival system, and universal persistence owner are explicitly deferred. Missing observation between saves is not filled in by interpolation except as separately labeled prediction.

### B11.3 Additional acceptance cases (B-27–B-31; NOT RUN)

| ID | Case | Required result |
| --- | --- | --- |
| B-27 | Autosave tick with no new native observation | Checkpoint retains original source seq/time/age; does not claim fresh World observation |
| B-28 | SelfWorld and SelfBody latest native samples are from different times | Save both with distinct source refs; no fabricated synchronized whole-World frame |
| B-29 | Snapshot file write fails | Explicit checkpoint error, previous valid snapshot preserved where feasible, no S49 authorization impact |
| B-30 | Restore checkpoint after World/session restart | Historical context only until new qualified observation; no old Action grant or live body state resurrection |
| B-31 | Stored snapshot references inferred enemy position or body fatigue | Origin remains INFERRED/PREDICTED/UNKNOWN, not converted to OBSERVED or physical WorldBody truth |

**Scope:** B decides *when/how to capture its available cognitive readouts*, not a new Memory lifecycle. The configurable interval and bounded retention defaults can be selected in owner-reviewed implementation tests; Contract B does not assert that this autosave mechanism currently exists.
