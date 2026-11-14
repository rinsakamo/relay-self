# RelaySelf Cognitive Architecture v0.1 — Common I/O Contract

> **Issue #829** under frozen architecture [#828](https://github.com/rinsakamo/relay-self/issues/828).
> **Status: DRAFT IMPLEMENTATION CONTRACT / OFFLINE-ONLY / NOT WIRED TO S49 OR GPU BACKEND / NO QUALIFICATION / NO SCIENCE.**
> Baseline audit: `main@4348a614900c1d0828581a8eec2c523ba5ae237f`.
> The v0.5 design remains in [Draft #718](https://github.com/rinsakamo/relay-self/pull/718), not main.
> The read-only SelfBody/SelfWorld views remain in [Draft #634](https://github.com/rinsakamo/relay-self/pull/634), not main.
> This contract neither supersedes their owners nor upgrades earlier DEV evidence.

## 1. Reuse-first audit and owner boundaries

| Existing asset | Reused as | Gap / exclusion |
| --- | --- | --- |
| `relay_self.provenance.Provenance(source,reference)` | Evidence pointer in envelopes, traces, and actions | Not proof of source authority; identity, session, time, attestation still checked by original owner |
| `IntentCommitment`, `CurrentIntent` | Existing Intent lifecycle and stable intent reference | Existing main is single-current-Intent; multiple concurrent intents from Unified A are design-only |
| `SkillExecution`, `ActionLifecycle`, `ActionSupervisor` | Existing action proposal/authorization/issue/timeout/unknown lineage | Physical sole issuer S49 is on separate development branches; no new physical emitter |
| `BoundedChoice`, `BoundedChoiceRequest`, `ProviderDecision`, `RelayEngineResult` | L1 choice contract/provider result | Current bounded engine does not itself enforce world-epoch or cancellation fence |
| `OpenCognitionRequest`, `OpenCognitionResult` | L2 request/untrusted text | Does not attest interpretations, physical effect, backend stop or model output fencing |
| `coordinate_decision_epoch` | Existing coordination seam serving ActionSupervisor first | Not CPU Profile Selector, resource ownership or GPU scheduler |
| `PersistentCognition`, `Memory` | Existing retained cognition + source/integration provenance | No automatic Log→Structured conversion; separate retained-owner admission required |
| Present/Attention/WorldBody source, WB read-only views | Inbound source-qualified projections | Some on unmerged Drafts; consume by ref, do not invent a second World truth |
| Unified v0.5 A/B/C1–C4 | Frozen semantics for Intent attempt, episodic result and conditional learning | Documentation in Draft #718; not proof of working integrated runtime |

**Strict owner map:** external World/WorldBody owns physics; gateway/native receiver owns source attestations; S49 existing Action route owns physical issue/supervision; Self/Intent owner chooses goals and commitments; existing Memory/Learning/Habit owners govern revisions; CPU selector only picks computation; resource owner only admits/releases compute. A `Provenance` instance is an opaque pointer, never an authority token.

## 2. Block I/O Matrix v0.1

The columns `State owner` and `Authority` name *existing logical responsibilities*, not proposed new storage or processes. All producers must maintain provenance and typed clock domains. `UNKNOWN` is not zero/false/absent.

| Block | Input | Output | State / state owner | Authority | Failure, UNKNOWN, staleness |
| --- | --- | --- | --- | --- | --- |
| World / WorldBody (external) | Admitted physical command, world rules | Native observed state, command outcome/ACK | External WorldBody | Physical facts/physics only | Undelivered/unobserved effect=UNKNOWN, not success |
| Embodiment Gateway | Native source, session, seq; accepted ActionRef | EvidencePacket, action receipts / send status | Existing native receiver / physical issuer | Authenticate source/session/seq and transmit only via existing path | Disconnect, mismatch, duplicate, missing ACK=UNKNOWN or reject |
| Perception & Attention | EvidencePacket, attention budget | PerceptEvent, FastCue | Present projection/attention; no separate physical state | May select/transform received observations, not forge coverage | Out-of-coverage or truncated=UNKNOWN; mandatory Action audit cannot be filtered away |
| Innate Schema Registry | Percept, 3Self views, schema config/dependencies | CognitiveSignal, safe FAST rule candidates | Schema registry configuration (future contract) | Generates candidates only; not World facts or Action issue | OFF/dependency absent→no signal; FAST/FULL differences explicit |
| Log Memory | Percept, receipts, cognition trace, PreemptionEvent | Append receipt/log refs, time-series read | Existing Log/audit owner (integration pending) | Stores attributed occurrences, no world qualification promotion | Queue overflow / durable failure surfaced; L0 decision does not await query/flush |
| Structured Memory | Governed MemoryRevision, authorized retained Memory | Revisioned evidence/experience/knowledge refs | Existing Memory/Learning owner | Retained content and revision admission, not World truth | Missing, old or mismatched context must not become current evidence |
| Cognitive Core: MySelf | Percepts, Identity, Memory, current refs | Interpretation of capabilities/continuity | Read-only 3Self perspective on existing cognition | Owns no body physics/extra store | Lack of source→UNKNOWN |
| Cognitive Core: SelfWorld | Percepts, past World Memory, predictions | Interpretation of surroundings/causes | Read-only source-bounded view (#633) | Not omniscient World owner | Unobserved ≠ verified absent; prior sightings not current |
| Cognitive Core: SelfBody | Body percept, physical limits, past Body Memory | Interpretation of body capacity/needs | Read-only source-bounded view (#632) | Not true Body resource ledger | Physical cost unknown ≠ free |
| Present Self | Signals, Interpretations, goals, intent owner refs | PresentFrame, CognitiveTask | Existing Self/Intent owner | Selects Goal/Intent; no computation layer may replace Goal | Stale frame requires reprojection; no implicit release |
| CPU Profile Selector | CognitiveTask, resource capability, source-currentness | ProfileDecision L0/L1/L2/DEFER | Transient decision, no new owner | Choice of compute route only | No choices/known rule/expired→DEFER, not guessed Action |
| CPU Resource Scheduler | ProfileDecision, backend occupancy, cancellation/VRAM attestation | Compute grant, PreemptionEvent | Future compute lifecycle (not yet implemented) | Compute arbitration; L1 GPU prioritizes over L2 | Cancel≠stop≠release; unverified release→no L1 GPU admission |
| L0 CPU execution / Fast Path | Fresh FastCue, verified installed rule, CPU budget | CognitionResult or Action proposal | Existing CPU rule/physical Action owners | Rule execution only; all physical actions require S49 boundary | Deadline/stale/unknown guard→no unsafe proposal |
| L1 bounded cognition | Finite choices, bounded context, admitted compute | CognitionResult / abstain | Existing RelayEngine & provider | Finite choice within supplied alternatives | Backend failure/UNKNOWN→UNRESOLVED; no fabricated choice |
| L2 open cognition | Question, source-bound context, admitted compute | Hypothesis/plan proposal, CognitionResult | Existing RelayEngine & provider | Reasoning text only | Late/cancelled output invalid; no World/Memory/Action authority |
| Skill / Action Execution | Owner-admitted Intent + Skill, proposal, source qualified gate | ActionRef, native send receipts, Consequence / UNKNOWN | Existing Intent/Skill/Action lifecycle; S49 physical issuer | Sole physical admission, serialization, terminal outcome | Conflicting channels, no consent/ACK, old source→reject/UNKNOWN |
| Learning & Consolidation | ExperienceEpisode, interpretations, verified consequences | MemoryRevision proposal/owner decision | Existing Learning/Memory/Habit owners | May propose and govern retained revisions | No automatic promotion of LLM claim or duplicate episode |

**Fast path exception:** Gateway → source-bound FastCue → installed CPU L0 rule → **normal Action authorization and S49 supervisor** → WorldBody. It never needs a synchronous Log query, 3Self full interpretation, L2 inference, or completion of learning. Parallel L0 candidate computations do **not** imply parallel physical issuance.

## 3. Wire-value schema: common rules

- **Identity and scope:** `(self_id, world_session_id, event_id)` is the minimal namespace of a World-bound event. `event_id` by itself is not a global grant. Non-World cognition may have no world session, but cannot later be cast to fresh World evidence. Explicit self/session mismatches fail closed.
- **Version:** `schema_version=1` on common envelope; owner revision or source epoch/seq is *additional*. Session and revision must be pinned across task→decision→result. Schema version ≠ retained Memory revision.
- **Provenance:** reuse `Provenance(source,reference)` for pointers; an original native source ref and any causal refs remain separate. Strings alone do not attest permission or source authenticity.
- **Clocks:** `host_monotonic_ns` for local deadlines; `world_tick` for game progression; `wall_ms` for display; `UNKNOWN` with no numeric value. Never compare heterogeneous clocks or infer causal order from wall time. `occurred_at` vs `received_at` are distinct.
- **Epistemic status on each claim:** `OBSERVED`, `INFERRED`, `PREDICTED`, `REMEMBERED`, `HYPOTHETICAL`, `UNKNOWN`; `kind` is the event type, not the evidence quality. Producer marks each claim; consumer never upgrades it merely because the payload is structured.
- **Freshness:** explicit scope + source revision + currentness policy + deadline. Reboot invalidates runtime grants and freshness until original owners re-establish them. A missing native revision is not interchangeable with an arbitrary timestamp.
- **Backpressure:** mandatory Action receipt and reservation persistence remain owned by existing S49/supervisor. L0 perception/log fan-out may be asynchronous, but if a required pre-issue durable reservation fails, physical issue fails closed. No silent dropping of mandatory receipts.

## 4. Major I/O type inventory — required / optional / producer / lifetime

Every type is conceptually an Envelope-wrapped payload or a reference to an existing owner object. The minimum envelope carries `event_id, kind, scope.self_id, occurred_at(domain,value), provenance, schema_version`; `world_session_id` is mandatory for World events; `received_at, source_refs, cause_event_refs` are typed optional except where required below. The fields below are **payload-specific**, so this does not require one Python class per type.

| Type | Required payload fields | Optional fields | Producer → consumer / provenance, time, revision and invalidation |
| --- | --- | --- | --- |
| Envelope | Event ID, kind, scope, clock stamp, existing Provenance, schema v1 | Native source pointers, causal event refs, host received timestamp | All boundaries; owner attests scope. Reject unsupported version, foreign session, incompatible clock; reference alone confers no authority |
| EvidencePacket | source/native sequence ref, self/session, observation coverage, source kind, observed values or UNKNOWN | receive timestamp, truncation, readback depth | Native Gateway → Perception, Action audit. Native seq+session pinned; stale/coverage unknown never becomes verified absence |
| PerceptEvent | source EvidencePacket ref, scope, percept claim(s) with epistemic status, observed/received times | attention salience, feature refs | Perception → Log / 3Self / Present; source revision pinned; superseded observation is historical |
| FastCue | native source ref, world scope, received monotonic time, source revision ref, installed CPU rule ref, expiry monotonic ns | hazard severity, selected minimal features | Gateway/Perception → CPU L0; stale/expired/unknown rule/foreign session rejected before normal action gate |
| CognitiveSignal | signal kind, current evidence/interpretation refs, uncertainty/status, origin schema+version | Need/Question/Goal candidate, urgency | Innate Schema → Present/3Self; signal not Intent; OFF/dependency change or source loss invalidates active candidate |
| Interpretation | lens (MySelf/SelfWorld/SelfBody), input refs, claim/status, uncertainty | hypotheses, predictions, alternative interpretations | 3Self → Present/Learning; memory/prediction refs versioned, NEVER World physical truth |
| PresentFrame | self/session or nonworld scope, frame/epoch ref, active Attention/Need/Question/Goal/Intent refs | active 3Self revision refs, budgets | Present Self → Task / Profile executor; transient snapshot, version invalid on new owner epoch |
| CognitiveTask | task ref, scope, requirement, source revision refs, host monotonic deadline, generation | question/intent ref, finite choices only for SELECT_FINITE, context/budget refs | Present/Schema/Skill → CPU Selector; task creation cannot change Goal; stale/expired or inadequate choices→DEFER |
| ProfileDecision | task ref, generation, L0/L1/L2/DEFER, reason, source revisions, admission status | estimated compute cost, backend/slot ref | CPU Selector → Resource Scheduler/Executor; no implicit GPU admission; task/revision change invalidates |
| CognitionResult | task ref, generation, scope, profile, status, provenance, source revisions | choice ID, hypothesis, plan/proposal, backend call facts | L0/L1/L2 → Present/Intent/Skill; reject stale, cancelled, unknown option, foreign scope; text is not physical Action |
| IntentRef | Owner-scoped intent identity/instance + lifecycle revision | Goal/parent commitment refs, attempt ID | Existing Intent owner → Action/Learning; terminal/reconsidered or wrong owner rev invalid |
| ActionRef | Existing ActionLifecycle ID+revision, linked Skill/Intent, physical issuer scope | native ACK / source seq / command target | Existing S49/Action owner ↔ Gateway; issued != observed. Terminal Action does not prove Intent achieved |
| Consequence | exact original Action/Intent refs, verified native observations or UNKNOWN, source/time/coverage | comparison against prediction, confounders | Gateway / existing S16/feedback → Log/Learning; no post-hoc LLM narration as verified outcome |
| ExperienceEpisode | scoped intent attempt ref, before snapshot/prediction or NO_PREDICTION, Action/Consequence refs, assessed result/status | multiple Action refs, model comparison, correction/amendment ref | C1 assembly → Learning; one assessed **attempted** Intent→one episode, revisions amend same ID; passive events are Log not fake Action episodes |
| MemoryRevision | target existing semantic owner + prior revision, proposal kind, evidence/episode refs, applicability, epistemic status, disposition | competing hypotheses, rollback, later reuse results | Learning → existing structured Memory owner; proposed ≠ accepted, old base revision rejected, independent later proof required |
| PreemptionEvent | L2 task/generation, requesting L1 task, phase, source/host monotonic time | backend stop/VRAM release verification refs, retained Question/Goal refs, failure reason | CPU resource owner → Log, L1 gating, Learning; output fenced on cancel request. No STOP/RELEASE unless independently attested |

**No new owner is implied by a type name.** In code, `common_io.py` implements a small subset as pure Value Objects and functions, reusing existing `Provenance` and `BoundedChoice`. The rest is an owner-facing logical contract pending real interface review.

## 5. Minimal routing and GPU preemption invariants

```text
Task(FAST_REACTION, fresh source, installed CPU rule, time remaining) -> L0
Task(SELECT_FINITE, >=2 distinct choices, L1 backend available)    -> L1/PENDING
Task(OPEN_REASONING, L2 backend available)                          -> L2/PENDING
Foreign scope, stale revision, past deadline, unavailable backend   -> DEFER
```

`PENDING` means the route has been picked; it is **not a compute grant**, physical Action grant, or guaranteed response time. The caller must recheck all source revisions, deadlines and active generation **when receiving** results, before any effect. A retained Goal survives task cancellation; selector never substitutes it.

```text
L2 RUNNING
  -> CANCEL_REQUESTED     [old generation immediately ineligible for results]
  -> OUTPUT_FENCED        [output routing fence acknowledged]
  -> BACKEND_STOPPED      [trusted backend stop attestation required]
  -> RESOURCE_RELEASED    [trusted resource/VRAM release observation required]
  -> L1_ADMITTED          [new grant from existing resource owner required]
```

Failure to verify stop or release is a **real no-admission** case. Do not infer release from HTTP cancellation, timeout, a missing response, or output fencing. The implemented `PreemptionTrace.append` checks phase order and verification-ref *presence*, not actual GPU operations or authenticity; it never calls the backend. A trusted owner must supply source-attested proof at integration. L2 partial output is discarded as proposal text. `PreemptionEvent` is a Log item for a later conditional cognitive-resource hypothesis, *not* evidence that danger caused GPU contention.

## 6. Offline scenario trace and negative controls

| Scenario | Producer → interface → consumer | Positive contract check | Negative controls / forbidden claim |
| --- | --- | --- | --- |
| 1. Zombie emergency L0 | native damage/nearby EvidencePacket → FastCue → installed CPU rule → original Intent/Skill/Action Lifecycle | Source+session+deadline qualified, original authorization precedes issue, later outcome separate | Expired cue, wrong session/revision, absent rule, proposal bypass→reject. Offline synthetic trigger ≠ real 205ms reflex qualification |
| 2. Known-food L1 | retained Memory ref/condition → PresentFrame → finite CognitiveTask → L1 choice → Action owner | BoundedChoice reused; selected ID in advertised options; resulting Action governed by original owner | Stale Memory or mismatched current source, unknown choice, no food evidence→UNRESOLVED/DEFER; selection≠eaten |
| 3. Self-initiated L2 exploration | Exploratory schema signal → Self-owned Question/Goal → task → L2 hypothesis → proposed Reference Action → observed Consequence → C1/C2 | No existing Minecraft answer seeded; interpretation and memory revision remain proposals until qualified | New proposal not issued, no observation, post-hoc prediction, wrong source→no learning claim. Contract trace ≠ autonomous exploration demonstrated |
| 4. L1 interrupts L2 | L2 task RUNNING → L1 demand → output fence → backend stop → GPU release → L1 admission → Log | Late L2 result denied after cancel; sequence and reason preserved | Cancel requested but stop not confirmed, VRAM not released, out-of-order state, stale L2 result, missing Log → no claimed admission/success |

IO-01..IO-10 from #829 remain the wider acceptance suite. Offline tests in this branch exercise core invariants only; performance, logging durability/backpressure, true perception/3Self and actual GPU release require owner-specific follow-up.

## 7. Decisions / unresolved owner-specific questions

1. **Source epoch binding:** Which existing native session/seq + S49 Action receipt must be the canonical `source_revision_ref` in integrated product? Do not substitute monotonic time for native revision.
2. **Physical path:** Which existing S49 admission entrypoint consumes an accepted `FastCue` after the action owner establishes grant/intent/skill? No second emitter; L0 may bypass slow cognition but not authorization.
3. **GPU backend:** Which llama.cpp/Jev backend API proves generation fenced, backend stopped, VRAM/slot released? `PreemptionTrace` alone is insufficient.
4. **Log durability:** Native pre-issue reservation and post-issue mandatory audit must remain fail-closed; decide an asynchronous L0 event log overflow policy separately from this routing helper.
5. **L1 conditional applicability:** Link selected retained Memory/Habit revision and its validity predicates to the task epoch; a choice is not itself evidence of learned food acquisition.
6. **Schema lifecycle:** Schema ID/version, FAST/FULL dependencies and OFF invalidation need the next child Schema Contract; do not change existing retained beliefs when a Schema is disabled.
7. **C1/C2 handoff:** Semantic owner specifies idempotent Intent-attempt episode key and revision/readback gates, preserving unknown, passive events and multiple Actions.
8. **Integration base:** This branch is rooted on unmodified `main`, because #718/#634 are separate Drafts. Integration must review actual product-owner branch contracts before wiring.

**Scope and verdict:** Design contract + deterministic offline helpers, not production source attestation, real CPU latency certification, GPU scheduling, self-learning, Minecraft World run, qualification or scientific results.
