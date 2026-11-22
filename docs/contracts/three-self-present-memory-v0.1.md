# Cognitive Architecture v0.1 / 03 — 3Self / Present / Memory Contract

> Parent [#828](https://github.com/rinsakamo/relay-self/issues/828), child [#833](https://github.com/rinsakamo/relay-self/issues/833). Stack: [Common I/O #830](https://github.com/rinsakamo/relay-self/pull/830) → [Innate Schema #832](https://github.com/rinsakamo/relay-self/pull/832) → this draft PR.
>
> **DRAFT / OFFLINE READ-ONLY CONTRACT SEAM / UNWIRED OWNER INTEGRATION / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.** The structural baseline #828 stays frozen; no World/Gemma, native Action, GPU, learning or qualified science was run.

## 1. Reuse-first owner audit

| Existing asset and actual branch | What is reused / what is not claimed |
| --- | --- |
| `main:src/relay_self/persistent_cognition.py` | `IdentitySpecification`, `PersistentCognition(identity, memories, appraisal_dispositions)`, `Memory` and retained provenance. It is an intentionally narrow store: not a global Goal/Belief/3Self database |
| `main:src/relay_self/intent.py` | `IntentCommitment`, `CurrentIntent` with proper lifecycle. Current main allows one current Intent per owner instance. Unified multi-Intent is a design, not present main implementation |
| `main:src/relay_self/appraisal.py` | Current appraisal remains directional prior/assessment, not observed danger/ally truth |
| `PR #634@087fe095a87594505392262da1d341cf0c65b2b2:src/relay_self/self_world.py` | Existing immutable `SelfWorldView`, `WorldObservation`, bounded memory/belief/prediction readout and world coverage; **Draft on a separate base**, not current main or this stacked PR |
| Same #634: `self_body.py` and Mineflayer `present_projection.py` | Existing `SelfBodyView`, `BodyObservation`/Interoception/Prediction, typed `MinecraftPresent`; no second Body state owner invented |
| Same #634: `attention.py`, `belief.py`, `prediction.py`, `learning.py` | Existing source-bound Attention, prediction, bounded belief assessment, owner-checked retained update proposals; separate Draft, not assumed merged |
| `#718` Unified v0.5 B/C docs | Three asymmetric lenses, projected Present, Intent-attempt experience and Memory revision governance. Frozen design only |
| `#830` `ScopeRef`, `CommonEnvelope`, `PreemptionTrace` | Source/scope and L2 generation fencing, not a new action or compute authority |
| `#832` `SchemaSnapshot`, `CognitiveSignal` | Qualified candidate generation and activation revision, not Goal/Intent owner |

**Key principle:** 3Self are three active interpretive *views on one Self's source-qualified input*, not three independent models/LLMs, a new World truth, three persistent databases, or three autonomous Goal agents. This PR creates a small read-only contract for cross-owner composition; it **does not duplicate** #634's physical/world-specific read-only projection details. The production adapter later maps existing #634 views to the thin cross-boundary reference representation.

## 2. Logical 3Self / Present / Memory I/O and authority

| Block | Input | Output | Owner / authority | UNKNOWN, stale, failure |
| --- | --- | --- | --- | --- |
| Native Gateway / Percept | Qualified source/session/coverage/time | Observed native claims / FastCue | Existing native owner and S49 authority boundary | Out-of-scope/truncated/missing source -> UNKNOWN, never presumed absence |
| MySelf view | Identity, retained self-experience, current context | Self competence/continuity hypothesis, canonical identity reference | `PersistentCognition` owner retains identity; Self perspective only | Prior self-confidence text not evidence of competence; known identity ≠ inferred ability |
| SelfWorld view | Current bounded observations + remembered World + beliefs/predictions | Source-qualified World interpretation | External World truth remains external; #634 SelfWorld is read-only | Prior observation is REMEMBERED, inference ≠ OBSERVED, other-Self privacy |
| SelfBody view | WorldBody observations/interoception, previous body experience, prediction | Source-qualified Body interpretation | Actual Body resources belong to WorldBody; #634 SelfBody only projects | No observed food/health/fatigue means UNKNOWN, never 0/free/full |
| Present Self | Three lens views + eligible Schema signals + existing owner refs | `PresentFrame` for Attention/Need/Question/Goal/Intent | Existing Self/Intent owner; *not* Profile Selector or LLM | Wrong scope/revision rejects, no implicit commitment release |
| Question review | PresentFrame + one eligible QUESTION_CANDIDATE + explicit caller-owned decision | ADOPT/HOLD/DECLINE receipt | Existing Self owner must authorize and commit actual Question/Goal | Stale frame, wrong self, invalid signal or owner revision rejects; receipt never grants Action |
| Memory read | Selected IDs from existing `PersistentCognition` | `REMEMBERED` read reference + original integration/source provenance | Existing Memory owner | Old Memory cannot become current World evidence |
| Memory write / learning | Qualified intent episode + proposed understanding revision | Existing owner revision check and accepted/rejected write | Existing Learning/Memory/Habit owners (#431, Unified C) | Reading a signal, L2 explanation or Question receipt never persists or upgrades a belief |

## 3. Minimal interop values / epistemic status

The implementation `src/relay_self/three_self_present.py` adds these owner-neutral immutable values:

- `Lens`: `MYSELF`, `SELF_WORLD`, `SELF_BODY`. The three views share **one** `ScopeRef(self_id, world_session_id?)`, epoch, and source revisions. No owner state, inference engine, memory mutation or native read is created.
- `LensClaim`: `claim_key`, one lens and scope, `EpistemicStatus`, source `Provenance` refs, original source-revision refs and optional opaque `value_ref` / `coverage_ref`. No raw World/Body values or source authority tokens are synthesized. `OBSERVED` requires native-eligible world session, source ref and current revision, while `REMEMBERED/INFERRED/PREDICTED/HYPOTHETICAL` stay distinct. `UNKNOWN` cannot have a known value or current observed revision. Pointer strings alone do not attest an actual Native event.
- `LensView`: immutable bounded claims, duplicate/foreign/stale-observed rejection, `read()` defaults to **UNKNOWN** rather than false or verified absent. Empty SelfBody/SelfWorld views are still typed and usable.
- `ThreeSelfProjection`: one common scope/epoch/source with exactly three `LensView` objects and canonical Identity provenance.
- `project_three_self`: reads `PersistentCognition.identity.self_id`, optional owner-qualified claims and explicitly selected `Memory` IDs. It projects an existing Memory as `REMEMBERED` with **both original source and integration provenance**, never as a current native observation. Reuses the existing Memory without cloning its content to a new DB; caller must supply actual current sources and validate native origin. Supports 0 selected memories.
- `PresentFrame`: three-lens projection, frame revision, Schema registry revision, a tuple of qualified Schema `CognitiveSignal`, and **separate** active Attention/Need/Question/Goal/Intent refs as provided by existing owners. No arbitration policy, universal scalar winner, implicit Goal selection or parallel physical issuance.
- `project_present_frame`: checks 3Self Self/sources against the current registry and validates Schema candidate provenance/source/epoch/mode via #832 `signal_is_current`. A stale candidate cannot silently modify Present. It does not consume an Action grant.
- `QuestionDecisionReceipt` and `review_question_candidate`: explicit **Self-owner-supplied** ADOPT/HOLD/DECLINE for a specific live Question signal with current Self owner revision, Present frame revision, schema registry revision and source refs. ADOPT is a **decision receipt** only; the original Self/Question owner must separately commit/retain a Question/Goal. HOLD and DECLINE similarly do not erase previously retained Question or existing Intent. Actual semantic decision policy belongs to Self, not this helper.

### Epistemic invariants

| Status | Interpretation | Forbidden upgrade |
| --- | --- | --- |
| OBSERVED | Owner-qualified current native observation in exact Self/session/source epoch | Only concrete native evidence owner can attest authenticity; no unrestricted World omniscience |
| REMEMBERED | Governed past memory with source/integration refs | Not current WorldBody truth, even if an earlier observation was valid |
| INFERRED | Reasoned assessment/belief using known evidence | Not direct observation or verified action outcome |
| PREDICTED | Conditional projected result | Not current effect or verified physical state |
| HYPOTHETICAL | Proposed explanation, counterfactual, LLM idea, question | Not true merely because LLM expressed it confidently |
| UNKNOWN | Not currently established; may be missing, stale or out of coverage | Not equivalent to false, empty, safe, healthy or lack of opponent |

Time: source owner maintains native seq/World tick, host monotonic clock, observation/receipt times. Thin `LensClaim` stores **references**, not fake wall timestamps; currentness is checked by comparing authoritative source revision refs and scope. v0.1 simulation cannot attest native provenance authenticity or independently reconcile time domains.

## 4. Signal → Present → Self-owned Question review

```text
Gateway/native evidence + selected old Memory (read-only)
                  |
       MySelf / SelfWorld / SelfBody
         |     |            |
         +---- PresentFrame -+-- eligible Schema CognitiveSignal(s)
                    |
          Self owner considers candidate
             /        |          \
         ADOPT       HOLD       DECLINE
          |            |            |
   owner-side Question  no owner   no owner
   commitment (separate) change   change
          |
       CognitiveTask (#829)
          |
   Profile selection / resources / existing Action/S49
```

The exact state machine of **retained Question/Goal commitments** is not implemented by this slice. An ADOPT receipt has no normative ability to create a Goal in `PersistentCognition` or `IntentCommitment`. The UI/next contract must explicitly bind the real Self owner and its own revision. An `IntentCommitment` currently holds only one Current Intent and is deliberately not extended here to a new competing owner.

Multiple Schema signals can coexist; **max instantaneous signal strength is not an automatic Intent replacement**. #828 Nov-10 addendum defines temperament + current state + learned dispositions as a potential origin for signal strength/response traits, **without requiring a universal scalar formula**. This slice only preserves multiple candidate refs; strength, appraisal and tension can be added as an owner-qualified input in a later Present selection contract.

**#831 compatibility caution:** its `propose_exploratory_question` helper emits one generic Question in the restricted `IDLE + LOW Need + observed unknown target` positive example. Per #828's later addendum, this is **not a rule that exploration only exists when idle or observations are present**: unresolved questions, self-uncertainty and richer candidate generation remain valid future Schema work. The Present contract accepts any eligible, source-bound Schema signal independently of that generator's narrow predicates.

## 5. Goal and Question persistence despite task failure

A `PreemptionTrace(CANCEL_REQUESTED)` immediately fences late L2 output, but it is a **compute-task transition**, not an event terminating a Goal, Question or Intent. Present may reproject with the **same** active refs supplied by their owners while issuing a new CognitionTask generation after meaningful circumstances change. Pending Question can be dormant/blocked until resources permit. A separate owner lifecycle decision can terminate/refine a Goal, but neither cancellation nor old partial L2 text can silently do it.

**Learning pair:** L2's pretrained conceptual understanding generates **hypotheses**. Only a qualified real World/Action outcome can ground C1's single attempted-Intent Experience, potentially prompting C2's candidate understanding revision; the existing owner controls retained memory/learning writes. Never compare source-mismatched experiences or label an LLM claim `OBSERVED`. No model weight training is assumed.

## 6. Deterministic offline test plan and negative controls

| Case | Expected |
| --- | --- |
| PR-01 Empty 3Self | typed MySelf/SelfWorld/SelfBody available; absent fact=UNKNOWN |
| PR-02 Memory | selected `PersistentCognition.Memory` projected as REMEMBERED, never OBSERVED |
| PR-03 Cross-scope | other Self, session or stale native source fails; different Selves don't leak internal views |
| PR-04 Epistemic | native observed Body/World separated from HYPOTHETICAL text, missing original source rejected |
| PR-05 Present assembly | multiple Schema signals retained, no universal winner, active Goal/Intent refs untouched |
| PR-06 Signal admission | stale schema epoch/source/self/mode rejected; OFF→ON never revives old output |
| PR-07 Question decisions | explicit ADOPT/HOLD/DECLINE bound to Self owner revision; existing Intent/Memory not mutated |
| PR-08 Stale decision | foreign Self owner, stale Present/schema/source or missing signal rejected |
| PR-09 Cancellation | L2 CANCEL_REQUESTED fences output without removing owner-supplied Question/Goal/Intent refs |
| PR-10 Unknown/non-Intent | unobserved entity absence or body value not fabricated; no passive experience or MemoryRevision written |

Passing these tests shows **typed offline reference coherence** only. It does not implement active MySelf interpretation, full #634 composition, persistent Goal/Question registry, actual Schema signal strength personality, human-free real learning, live backend preemption, physical World or source-integrity qualification.

## 7. Integration backlog and next contracts

1. Bring in the *actual* #634 WB view APIs via owner review, mapping their original field/coverage/native source refs to read-only `LensClaim` without serializing speculative fields as OBSERVED. Do not merge #634 blindly into #832 branch.
2. Establish a canonical current owner revision for retained Question/Goal and genuine Self-side ADOPT/HOLD/DECLINE lifecycle, with no accidental single-current Intent replacement. If multiple simultaneous intents become real, take design from #718 Contract A only after product owner review.
3. Define simultaneous schema signal strength/cost/temperament/Need semantics and current prioritization with hysteresis, interrupt triggers and possibly no new Goal. This is #828/03 Present selection work, not hardware Profile Selector.
4. Define any source/clock/coverage Currentness checks against native owners; no caller-chosen strings as freshness proof, no reopened saved World's old grants.
5. Handoff to #828/04 `CognitiveTask`/Profile: same active Goal/Question, task generation change and compute budget must not mutate owners; #828/05 handles actual L2 interruption; #828/06 handles revisioned learning; #828/07 retains original S49 physical authority.
6. Continue exploring how Schema signals derive from temperament/state/learned dispositions, and how active questions can be internal (memory retrieval, L2 thought) as well as physical observation. #831's current generator is one narrow demo, not a normative global gate.

**Status:** Documentation + owner-neutral/offline typed reference contract, with tests. Integration with real Self/World/LLM, qualification and science remain distinct gates.
