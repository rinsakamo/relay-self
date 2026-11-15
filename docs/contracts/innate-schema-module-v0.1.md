# Cognitive Architecture v0.1 — Innate Schema Module Contract (02)

> Parent [#828](https://github.com/rinsakamo/relay-self/issues/828); child [#831](https://github.com/rinsakamo/relay-self/issues/831); prerequisite [#829](https://github.com/rinsakamo/relay-self/issues/829), [Common I/O Draft #830](https://github.com/rinsakamo/relay-self/pull/830).
> **DRAFT / DETERMINISTIC OFFLINE INTERFACE ONLY / NOT CONNECTED TO PRESENT, S49, WORLD OR LLM / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
> Integration baseline: `main@4348a614900c1d0828581a8eec2c523ba5ae237f` + unmerged `#830@ad2be305acc21b64a13afce33b5562e727c10121`. No changes to other lane history or evidence.

## 1. Scope, philosophy, reuse audit

An **Innate Schema** is a configurable cognitive **mechanism**, not built-in Minecraft knowledge. It can create Attention / Need / Affect / appraisal / Question / Goal *candidates*, use source-qualified Percepts and existing 3Self/Memory views, and supply bounded features to several execution profiles. It does **not** select a committed Goal/Intent, authenticate a native source, issue a Reference Action, authorize or acquire hardware, write retained Memory, or attest a World effect. A candidate is an *internal proposition*, not a native fact or an installed Skill.

Nine initial logical families (open IDs, not a hard-coded Python enum): **Perceptual, Homeostatic, Motivational, Affective, Exploratory, Causal, Learning, Social, Metacognitive**. Modules may be added without modifying the central registry representation. Not all nine are implemented.

Existing code reviewed:
- `relay_self.appraisal.AppraisalDisposition` and `project_entity_appraisal`: already separate a learned/seeded directional tendency from external entity truth. Reuse these exact values for Affective/Appraisal behavior; no parallel appraisal DB.
- `PersistentCognition`, `Memory`, `IdentitySpecification`: retained content and Provenance reside with their established owner. Switching a schema OFF does **not** delete earlier experiences, historical Log, identity or appraisal dispositions; it only fences new outputs from that Schema.
- `CommonEnvelope`, `ScopeRef`, `Provenance`, `FastCue` from #829/#830: reused for source/session/time refs and low-latency CPU path, not reimplemented. The old ActionLifecycle, ActionSupervisor and original S49 physical issuer retain authority.
- Prior Present/Attention are in other existing lanes or experiment code; schema activation does not introduce another Present owner.
- `SchemaSnapshot` is an **immutable configuration value held/published by an existing owner**. It is not a new service, scheduler, database, autonomously mutable registry, or authority token. The `with_schema_mode` helper returns a *proposal* for a newer revision.

## 2. Logical I/O and state/authority matrix

| Logical schema family | Input (minimal) | Output (candidate) | State / authority owner | Failure / Unknown / Staleness |
| --- | --- | --- | --- | --- |
| Perceptual | Source-qualified Percept, scope/coverage | Attention feature/cue candidate | Present/Attention and original Gateway; Schema only computes | Observation outside coverage is UNKNOWN, not absent |
| Homeostatic | SelfBody/Need readout, constraints/uncertainty | Regulatory Need / affective concern candidate | Body physics external; Self Need/Goal owner retains decisions | Unmeasured food/energy/fatigue remains UNKNOWN |
| Motivational | Current Need, Question/Goal context | Motivation or priority *candidate* | Present Self goal selection | Candidate does not commit/release an Intent |
| Affective / Appraisal | Percept + `AppraisalDisposition` | Source-qualified directional CurrentAppraisal | `PersistentCognition` retains dispositions | Bias is not enemy/ally truth or an Action directive |
| Exploratory | IDLE, LOW Need pressure, observed unknown subject, catalogued Reference Actions | Source-bound QUESTION_CANDIDATE | Present Self may accept/create a Question/Goal | UNKNOWN Need, BUSY, absent target/action, stale/foreign source => no proposal |
| Causal | Evidence, before/after, prior model | Hypothesis / comparison candidate | Existing Learning/Belief owner governs later revision | Model explanation not causally attested |
| Learning | Evidence-qualified episode, interpretation | MemoryRevision candidate | Existing #431 semantic owner | No write merely from a candidate |
| Social | Other-observed percept and bounded source-qualified view | Other/relationship inference candidate | SelfWorld and existing observation/Memory | Other's private Self/World/Intent not readable |
| Metacognitive | Cognition budget, task, interrupted/cancelled log | Allocation/Question review candidate | Resource scheduler owns compute; Self decides goals | L2 preemption record not evidence that danger caused contention |

These are **interface requirements**. Only config/eligibility and the generic Exploratory candidate have executable code in this child PR.

## 3. Minimum values (implemented in `innate_schema.py`)

| Type | Mandatory fields | Optional | Origin → consumer and lifetime |
| --- | --- | --- | --- |
| `SchemaModuleSpec` | schema_id, version, supported_modes, signal_kinds, dependencies, `Provenance` | Add capability/CPU/memory cost hints later only when measured | Design/config owner → eligibility evaluator; version must match registered module. Pointer provenance is not an authenticity proof |
| `SchemaDependency` | target schema_id, minimum_mode FAST/FULL | None | Module spec → dependency validator; unknown/self/cycle rejected even if OFF |
| `SchemaActivation` | module spec ref, selected mode OFF/FAST/FULL | None | Existing Self config owner → current snapshot; unsupported mode rejected |
| `SchemaSnapshot` | self_id, monotonically revised snapshot ID, activations | Empty module set allowed | Existing config owner → runtime; only authoritative current revision valid, not an old cached snapshot |
| `SchemaEligibility` | schema_id, requested mode, snapshot revision, allowed, reason | None | Pure checker → runtime; cannot authorize hardware, Goal or Action |
| `ExplorationOpportunity` | World-scoped `CommonEnvelope(kind=PRESENT_FRAME)`, source revision refs, target's observed `Provenance`, unknown subject ref, existing catalog provenance and reference Action refs, engagement and Need pressure | Empty action refs allowed but result is no candidate | Present / existing capability catalog → exploratory pure function; FOREIGN/STALE/UNKNOWN input does not qualify |
| `CognitiveSignal` | `CommonEnvelope(kind=COGNITIVE_SIGNAL)`, schema ID/version, registry revision, source revision refs, kind, exact FAST/FULL execution mode, epistemic status | `ExplorationQuestion` for question candidate | Schema evaluator → Present. Revalidate identity, source, registry version, mode, dependency on consumption; signal not an Action/Goal |
| `ExplorationQuestion` | unknown subject, *all available* catalogued Reference Action refs, inquiry `OBSERVE_UNKNOWN_EFFECT` | None | Exploratory schema → Present Question consideration; Self decides whether and which Action to try, and can decline |

`CognitiveSignal` intentionally **cannot claim OBSERVED**: the native Percept/Evidence source retains that role. Derived signals only carry INFERRED, HYPOTHETICAL or UNKNOWN. Concrete claim justification must still be checked by downstream existing owners.

## 4. Activation modes and dependencies

```text
SchemaModuleSpec (mechanism/version/dependency declarations)
      │
SchemaSnapshot(self_id, owner_revision, activations)
      │  pure eligibility
      ├── OFF  → zero *new* schema outputs; old Log/Memory unchanged
      ├── FAST → only declared bounded FAST output, no slow LLM/retained search
      └── FULL → permitted fuller view; FAST outputs only if FAST explicitly supported
```

Dependencies are declared by `SchemaDependency(schema_id, minimum_mode)`. Construction rejects missing IDs, duplicate IDs, self-reference (cycle), arbitrary cyclic graphs and unsupported modes. A dependency that becomes OFF or insufficient makes the dependent **ineligible**; its configured mode is **not silently mutated**. Changing a mode increments the **existing config owner's revision**; a previous output cannot be consumed after that revision change, even after OFF→ON.

`FULL` is an activation tier, not permission to run an expensive model. `FAST` is an eligibility label, not automatically a verified CPU rule. Deadline/currentness rules, GPU resource scheduling and physical Action arbitration remain in #829/#830 and existing owner APIs. A disabled optional schema cannot disable an independently validated emergency CPU-L0 installed rule, unless that specific rule declares that dependency through its actual L0 owner.

### Signal currentness contract
On consumption, the existing owner must supply **authoritative** current registry revision and Present source revision refs. The helper checks:
1. Self identity and (if World-scoped) exact World session;
2. Schema registered and version matches;
3. Same registry revision and source refs;
4. Explicit FAST/FULL mode of the produced signal equals the requested execution tier;
5. Dependencies and current activation remain eligible.
A stale snapshot supplied dishonestly as current cannot be authenticated by the pure helper alone. Integration must get these values from the actual owner, not from signal contents.

## 5. Exploratory Schema: voluntary Question, not gifted survival tactic

```text
Present(IDLE, LOW Need pressure)
    + source-qualified observation of a *present but not understood* subject
    + existing Reference Action catalog (capabilities, not known outcomes)
    + current FULL Exploratory schema / dependencies
        └─ QUESTION_CANDIDATE:
             subject: <opaque observed ref>
             candidate_action_refs: <all supplied capabilities>
             inquiry: OBSERVE_UNKNOWN_EFFECT
                  ↓
        Present Self may adopt/decline a Question/Goal
                  ↓
        Task/Profile/Action owner, if adopted and admitted
                  ↓
        real World readback → C1 experience → C2 hypothesis/revision candidate
```

No module names Minecraft items, assumes edible/hostile objects, suggests that any given action succeeds, or forcibly selects the first Reference Action. The signal contains the original observed target source and catalog source; catalog membership must be checked by the real capability owner on consumption. The source refers to a witnessed target with **unknown properties**, not an invented target. *Lack of knowledge* is not equivalent to an attested absence or an attested safe condition.

If `engagement` is BUSY or UNKNOWN, `NeedPressure` is URGENT or UNKNOWN, target observation is absent, no Action references are offered, any dependency is disabled, or source/session/revision is stale: no exploratory proposal. These are conservative candidate-generation defaults, **not a claim that curiosity cannot arise under uncertainty or danger in future learned behavior**.

## 6. Deterministic offline test matrix

| Case | Positive / negative expected |
| --- | --- |
| SC-01 Modes | FULL/FAST accepted only when advertised; OFF emits no new output; stale revision denied |
| SC-02 Dependency | Transitive active dependency required; OFF/insufficient dependent mode blocked |
| SC-03 Bad graph | Unknown, duplicate, cyclic/self dependencies rejected |
| SC-04 Existing Memory | OFF retains `PersistentCognition.Memory` and `AppraisalDisposition` unchanged |
| SC-05 Currentness | Signal source/session/self/version/config revision/FAST-FULL exactly matched |
| SC-06 Exploratory positive | Idle/low Need and observed unknown target → generic HYPOTHETICAL Question with all catalog Action refs |
| SC-07 Exploratory negatives | BUSY/UNKNOWN, urgent/unknown Need, no Action catalog, wrong target Provenance, stale native source, wrong Self |
| SC-08 Authority | Signal has no Action/Intent/World consequence; cannot be treated as OBSERVED |
| SC-09 Emergency | Existing native FastCue with installed CPU rule still uses original S49 action boundary, independent of optional Schema state |
| SC-10 Schema OFF→ON | Prior signal remains stale even if mode returns to FULL, retaining historical Log/Memory |

Passing these does **not** show actual emergent curiosity, independent goal formation, an operational registry in production, native response latency, or learned success. Real L0 performance/physical execution, L1/L2 backend, resource preemption and C1/C2 outcomes remain unverified in this contract.

## 7. Open integration tasks and next dependencies

- **#828/03 3Self/Present/Memory:** establish actual Present-owned IDLE and Need signals, observed-target unknown claims, revised current source refs and Self-side adoption of Question/Goal.
- **#828/04 Task/Profile:** convert eligible Schema outputs to a source- and version-bound CognitiveTask without silently selecting the Goal.
- **#828/07 Action/Gateway:** bound catalogued reference actions to actual native capability/authorization; schema activation never installs or issues a physical L0 action.
- **#828/05 Scheduler:** FAST/FULL activation is not a hardware grant and does not override L1-preempts-L2.
- **#828/06 Learning:** owner-governed acquisition of revised understanding, signal pattern/cue reuse and later reversible L1/L0 crystallization.
- **Registry publish/restart:** current revision assigned by existing owner. A restored old snapshot does not automatically confer fresh World admission; world/session source must be re-established.
- **Fairness and evaluation:** explore naturally when appropriate, without hardcoded schedule, reward or Minecraft answer. Offline stimulus demonstration cannot be called autonomous development.

**Verdict:** a small, typed and independently testable schema *contract seam*, intentionally not a second cognition/physical runtime.
