# Runtime Principles

This document records architectural principles for the future RelaySelf runtime.

These principles are normative design constraints derived from prior development and research. They are not claims that the current repository already implements the described behavior.

## 1. Viability is a constraint, not a utility term

Safety- or continuity-critical state should not compete with ordinary goals only by receiving a larger scalar reward.

Separate:

- **preferred range** — where regulation would like a variable to remain;
- **viability envelope** — the region inside which continued agency remains acceptable.

A deviation from the preferred range may create a Need without being an emergency. Crossing or predicting violation of the viability envelope should constrain admissible action.

If no fully safe action exists, the runtime must avoid deadlock and choose according to an explicit recovery or least-violation policy rather than pretending every candidate remains equally admissible.

## 2. Unify arbitration, not ontology

Needs, Questions, Goals, Commitments, relationship concerns, tasks, and opportunities are not the same kind of object.

They may emit a common transient representation for scheduling or arbitration, but their source semantics and lifecycles remain distinct.

```text
persistent / boundary source objects
  -> transient concern or tension projection
  -> arbitration
  -> Current Intent
```

Do not create one universal priority object merely because different concerns must eventually compete for action.

## 3. Intent is commitment, not a per-tick winner

Current Intent is the currently committed executable objective.

The runtime should not select a fresh winner every tick without cost. Intent should persist until completion, failure, invalidation, meaningful reconsideration, or justified preemption.

Reconsideration is itself a decision. Triggers may include:

- viability class change;
- invalidated intent precondition;
- important new evidence;
- new affordance;
- blocker change;
- skill stall or failure;
- deadline or slack collapse;
- material environment change.

These are trigger sources, not automatic reconsideration requests. A local Skill/path failure,
World mismatch, or newly available alternative should first remain under the same Current Intent
when local Skill/parameter recovery is still grounded and adequate. Admit an Intent-level
reconsideration request only when the grounded change materially challenges the commitment itself,
such as its validity, feasibility, priority, meaning, authority, or viability.

In particular:

```text
local execution-path failure
  != Current Intent failure

new affordance
  != automatic commitment break

World mismatch
  != automatic Intent replacement

admitted reconsideration request
  != later CONTINUE / RELEASE decision
```

The condition that justifies admission should preserve its provenance into the request. The later
reconsideration decision carries its own provenance and remains a separate transition. Prefer local
trigger logic at concrete existing responsibilities until materially different trigger sources
repeatedly demonstrate the same non-reducible shared contract; do not infer a global
`ReconsiderationDetector` or universal trigger score merely from this boundary.

Ordinary alternatives should not cause constant oscillation around near-equal scores.

## 4. Skills are closed-loop capabilities

A Skill is not merely a tool-call declaration.

A useful Skill contract may include:

- initiation conditions or preconditions;
- a temporally extended control policy;
- termination conditions;
- yield points;
- interruptibility class;
- expected duration or resource cost;
- success and failure evidence;
- side effects;
- required authority.

Primitive Action is the smaller world-effect command beneath a Skill.

Treat the Skill itself as the reusable capability/control definition, not as one execution instance. A future runtime should preserve the minimum semantic chain:

```text
Current Intent + Present + current capability information
  -> currently relevant/applicable Skill candidates
  -> selected Skill
  -> Skill-local cognitive narrowing / parameter binding as needed
  -> Skill execution instance
  -> primitive Action(s)
  -> Consequence
```

These stages are intentionally distinct:

```text
Skill candidate
  != selected Skill
  != started Skill execution
```

Candidate admission is a transient judgment that a Skill is worth considering now; it is not proof of success, external-state truth, or Action authorization. Selection chooses a Skill to structure the current local problem but does not itself start an execution or complete/replace Current Intent.

By default, candidate generation and selection are **decision-epoch computations**, not independently stateful owners. Their outputs are scoped to the Current Intent, Present, capability information, and evidence from which they were produced. If those inputs materially change before execution starts, recompute rather than silently treating the old selection as still current.

A bounded selection step must not require a winner. Its conceptual outcomes may include:

```text
START(skill, ...)
ESCALATE
DEFER / NO_SELECTION
```

`START` means enough structure exists to attempt the supported Skill execution start path. `ESCALATE` means bounded selection is insufficient and slower or more open-ended cognition is warranted. `DEFER / NO_SELECTION` preserves healthy inactivity or waiting when no Skill should start now. These are conceptual outcomes, not current executable value types, and none of them implies primitive Action authorization.

The current persistence boundary for a chosen execution path is the supported Skill execution start:

```text
transient candidate / selection
  -> SkillExecution STARTED
  -> execution-path lifecycle persistence
```

Do not introduce a second selected-Skill commitment lifecycle merely to carry a choice between Current Intent and SkillExecution. If pre-start work is small, keep it inside the current decision epoch. If it becomes temporally extended or requires external information, represent that work through existing cognition/agency concepts where they fit, or require concrete evidence before introducing another owner.

Once a SkillExecution has started, a later selector result cannot silently replace that active execution path. Switching paths requires explicit upstream policy and the existing Skill terminal/cancellation boundaries where applicable.

Skill selection may narrow Focus, Attention, Retrieval, admissible local actions, and parameter space without becoming the semantic owner of those mechanisms. Skill-local narrowing must remain penetrable by global viability, authority, reconsideration, and consequence evidence.

Parameter binding is likewise not a new owner by default. A simple Skill may require concrete values before execution begins, while a later closed-loop controller may bind or revise some values progressively. A prediction, retrieval result, or heuristic value used for binding does not become attested world state merely because the Skill consumes it.

Do not infer a repository-wide `SkillDefinition` schema or persistent Skill registry merely from these semantic responsibilities. The only cross-Skill representation already required by the current executable boundary is `skill_id`, which identifies the reusable Skill associated with one `SkillExecution`.

Applicability, cognitive narrowing, retrieval hints, parameter requirements, controller/execution binding, termination evidence, cost, or interruptibility may be necessary for a particular Skill without each becoming a mandatory generic field. For the first concrete strongly narrowing Skills, prefer local typed representations that expose only the information their actual consumers need.

Extract a shared cross-Skill field or interface only when materially different Skills repeatedly demonstrate the same non-reducible semantic responsibility at the same boundary. Shared syntax or implementation convenience alone is not evidence for a shared schema. For example, food choices, escape destinations, and conversational context may all be called "parameters" without requiring one universal parameter-schema language.

Keep the reusable Skill implementation distinct from the persistent `Capability Model`: the Capability Model is the Self's estimate of what it can do. It may later estimate availability, reliability, competence, expected cost, or other properties of a Skill without thereby becoming the owner of that Skill's implementation or definition.

The current executable `SkillExecution` contract owns the lifecycle of one started execution instance. It does not by itself prove that the Skill was a valid candidate, selected by a supported selector, correctly parameterized, or authorized to issue any primitive Action.

## 5. Action completion requires consequence evidence

Generated language or an issued command does not prove that an action occurred successfully.

The runtime should preserve a closure invariant such as:

```text
ActionIssued(a)
  -> eventually Outcome(a) | Timeout(a) | Unknown(a)
```

`Unknown` is preferable to inventing success when consequence evidence is unavailable.

Action Proposal, Authorization, Execution, and Consequence remain distinct stages.

### Cognition convergence does not establish World truth

A cognition path may settle enough to select a Skill or parameter without establishing that its
assumptions are true in the external World. Preserve:

```text
cognition convergence
  != World truth

expected consequence
  != observed consequence

observed mismatch
  != automatic Intent replacement
  != automatic training label
```

When a concrete Skill or Action path has a local expected-evidence condition, compare it with
provenance-bearing consequence evidence after execution. Keep that expectation local unless
materially different Skills repeatedly demonstrate a shared non-reducible contract.

Before execution starts, unresolved cognition should not be forced into an execution path merely
because a bounded computation ended. It may broaden, retrieve, inquire, escalate, or defer.

After execution, contradictory consequence evidence is an external correction signal. It should be
able to invalidate the applicability of the current narrow path, make stale Present views unusable,
and reopen or reproject cognition from the new evidence. Reopening cognition does not by itself
fail or replace the Current Intent; local Skill or parameter recovery remains valid where the
objective is still grounded and feasible.

Keep causal classes distinct where the evidence permits. For example:

```text
bad or stale estimate
  != World changed after the decision
  != controller / Skill execution failure
  != consequence unknown
```

A controller failure must not silently rewrite attested World state. A changed World must not
automatically become evidence that an earlier mapping was unreasonable. An unknown consequence must
remain unknown rather than being converted into success, failure, or training truth.

Validated success may justify cheaper future cognition through the existing reuse/crystallization
rules, but any such shortcut remains penetrable by contradictory consequence evidence, changed
applicability, novelty, viability pressure, or authority change.

Do not introduce merely for this recovery seam a global prediction owner, mismatch registry,
surprise scalar, universal Skill expectation schema, automatic failure-to-training conversion, or
automatic Intent replacement.

## 6. Facts, beliefs, appraisals, and presentation are different

A body or environment observation is not automatically a belief, and a belief is not automatically an appraisal or expression.

A useful separation is:

```text
Observation / Body Fact
  -> Evidence
  -> Belief or State Estimate
  -> Appraisal
  -> Affective / Present State
  -> Presentation or Action
```

A model statement such as "I am not tired" must not overwrite authoritative body observation merely because it was generated fluently.

## 7. Authoritative does not mean infallible

Authority describes who is allowed to write or attest a state field, not whether the source is cosmically correct.

Useful authority classes include:

- **Specification Authority** — policy, normative identity, viability rules, granted capability;
- **Attested State** — sensor reading, inventory, action outcome, environment observation;
- **Predictive Estimate** — learned or heuristic prediction such as route risk or likely skill success.

Attested state may still carry uncertainty, freshness, calibration error, or sensor faults. Predictive estimates do not gain specification authority merely by being learned.

> Learning may update estimates, not authority.

## 8. Present state should be derived where practical

Present Projection is a transient result of persistent cognition, boundary state, events, and time.

```text
Present_t = Project(PersistentCognition_t, BoundaryState_t, Events_t, Time_t)
```

Situation, Attention, current Appraisal, active Questions, transient tensions, and Current Intent should not automatically become durable cognition merely because they were active.

Trace the present when needed for debugging or evaluation, but prefer recomputation over unnecessary persistence.

## 9. Questions persist without monopolizing cognition

A Question is a persistent epistemic object. Its current activation is a present-state property.

A useful lifecycle may distinguish:

```text
candidate
  -> active
  -> blocked
  -> dormant
  -> active
  -> resolved
```

Other terminal or persistent states may include abandoned, superseded, or unknowable.

`blocked` should mean that no currently available capability, evidence source, or affordance can produce the next useful information-gathering step. Unresolved does not mean "think about this continuously."

Reactivation should be driven by meaningful change such as new evidence, a changed blocker, a new affordance, or an explicit event.

## 10. Healthy inactivity is valid behavior

Doing nothing for a period is not inherently a failure.

Wait, rest, sleep, recover, observe, reflect, conserve resources, wait for an opportunity, wait for another agent, and wait for a threat to pass may all be valid policies.

Evaluation should distinguish justified inactivity from pathological or unexplained idle behavior.

## 11. Runtime layers operate at different time scales and costs

Do not require language-model inference on every simulation or control tick.

Fast deterministic layers should handle regulation, event admission, viability checks, basic scheduling, skill control, and immediate safety response where practical.

Slower cognition should be invoked when interpretation, deliberation, novel planning, reappraisal, or persistent-state integration is actually needed.

When multiple available mechanisms can adequately serve the same current objective, selection should respect the current deadline, expected reliability or applicability, and relevant resource cost. Prefer a cheaper or faster mechanism when it meets the required result quality and constraints; escalate when cheaper control is no longer adequate and the remaining budget permits more expensive cognition.

This comparison need not collapse latency, compute, energy, uncertainty, risk, or information value into one universal scalar. A mechanism may be dominated in one situation and useful in another.

When cognition receives an explicit finite resource envelope, keep the **requested allocation** separate from the **observed cognitive work**. A caller may supply a soft wall-time allocation, token/output bounds, call-count limits, or permission to escalate, while execution records the wall time, calls, token usage, finish facts, and result actually observed. A soft wall-time allocation is an evaluation/control input, not a claim that provider execution was cancelled at that instant. Exceeding it does not silently relabel a resolved result as unresolved or make elapsed host time equal to World or subjective time.

The Self may later learn how much cognition to allocate from Present, Skill, capability estimates, viability pressure, and available World slack. Until such a learning mechanism is independently justified, recording cognition-work evidence must not create a new persistent owner, automatically update the Capability Model, or turn a successful consequence into proof that the preceding budget was causally optimal.

Experience may make an expensive computation reusable through Memory, a learned policy, a Skill, a cached procedure, or another justified mechanism. Such amortization does not make the shortcut permanently authoritative: contradictory consequence evidence, changed applicability, novelty, or distribution shift should be able to invalidate the cheap path and trigger renewed processing where useful.

A reusable cognition shortcut is qualified relative to the **cognition interface on which it was validated**, not merely to its semantic label, Skill identity, or retained input-key list. A material interface change that is observable to the mechanism may invalidate reuse even when the underlying task meaning appears unchanged. Depending on the local mechanism, such changes may include choice/control-id mapping, choice ordering, request or rendering shape, context-presence semantics, provider/model representation, or another demonstrated representation dependency. This is a local compatibility obligation, not a requirement for a repository-wide interface fingerprint or universal applicability schema.

Therefore prefer the conservative path:

```text
validated shortcut
  + materially compatible cognition interface
  -> shortcut may be used

compatibility unknown / materially changed
  -> do not assume shortcut validity
  -> broaden / reproject / use ordinary cognition
  -> requalify only when reuse value justifies it
```

Narrowing also must not change the meaning of missing information. In particular:

```text
omitted / not projected
  != known false
```

unless a local validated invariant explicitly establishes that reduction. If a shortcut cannot preserve uncertainty or distinguish omitted information from a decisive negative fact on its current interface, treat that as an applicability boundary rather than silently forcing a decision.

### Offline consolidation and compiled cognition remain derived

Offline consolidation may reorganize prior cognition into cheaper reusable mechanisms, but it does not create a new source of truth or semantic owner merely because computation moved out of the interactive path.

A minimal governed shape is:

```text
provenance-bearing consequence / trace
  -> eligible consolidation material
  -> derived candidate representation
  -> validation
  -> governed integration into an existing owner
     or a replaceable execution artifact
```

No arrow above is automatic. Preserve at least:

```text
Consequence / trace
  != durable Memory
  != training truth

derived training example
  != Evidence
  != authoritative fact

candidate reusable structure
  != accepted Skill / policy / procedure

compiled weights / adapter
  != Identity Specification
  != other Persistent Cognition

offline / sleep interval
  != learning authority
```

Persistent Cognition remains the source representation. It may influence current cognition through Present projection, Retrieval, or another existing governed path. Compiling repeated structure into a learned policy, cached procedure, model adapter, or other execution artifact does not transfer authority from the source cognition into that artifact. A product-specific label or projection of durable identity does not gain a second authority merely because it can also be compiled into model parameters.

Likewise, consequence or trace material does not become persistent merely because it is useful for learning. Retention and durable update remain governed by the existing Evidence, Memory, and Experience Integration boundaries. Candidate training material is a derived dataset: filtering, causal interpretation, deduplication or balancing, and held-out separation may all change what is eligible for training, and provenance back to the source material should remain available where practical. Generated self-claims, outcomes with unknown causal relation, and stale or retracted cognition must not become training truth merely because they appear in a local trace. Lower training loss alone is not evidence that a compiled artifact should be trusted or activated.

Sleep, rest, idle time, or another quiet interval may provide a useful scheduling condition for internal work by reallocating cognition away from external interaction. The scheduling condition does not own Memory, learning, consolidation, or weight mutation. The same internal work may run under another justified offline condition; biological sleep semantics are not required.

A candidate Skill, learned policy, cached procedure, or model-side adapter remains a candidate until the evidence appropriate to its claim validates it. Validation may be experiment-local and does not by itself justify a repository-wide registry or lifecycle owner. Activating a compiled artifact grants no new semantic authority: its output remains subject to the same authority, viability, provenance, and consequence boundaries as the uncompiled cognition path.

Crystallization must remain reversible. A compiled shortcut should be bypassable or replaceable when it is absent, stale, incompatible, contradicted, outside its demonstrated applicability, or followed by mismatching consequences:

```text
cheap compiled path
  -> mismatch / novelty / uncertainty / authority change
  -> bypass or disable shortcut
  -> broaden cognition / retrieve / inquire
  -> revalidate before reuse
```

The underlying Persistent Cognition must remain available when a compiled artifact is disabled or rejected. Deleting or replacing an execution artifact must not delete or redefine its source cognition.

Do not introduce merely for offline consolidation:

- a global `ConsolidationState`;
- a new semantic `Learning` owner;
- a permanent `SleepManager`;
- a repository-wide adapter registry;
- automatic persistence of generated interpretations;
- automatic failure-to-training or success-to-training conversion;
- automatic periodic fine-tuning;
- a generic Skill schema.

Extract a shared owner or lifecycle only when materially different concrete consumers repeatedly require the same non-reducible state, authority, or lifecycle.

Metacontrol itself consumes resources. Do not add an adaptive allocation mechanism when a fixed rule is sufficient, and do not hide unrestricted deliberation inside the mechanism that decides whether to deliberate.

These are cross-cutting runtime constraints, not a requirement for a new `CognitiveFrontier`, `ThinkingLevel`, brain-region layer, or other top-level owner.

Deliberate cognition is likewise a runtime mechanism rather than another architectural basis. When the current projection is insufficient, the runtime may retrieve already-owned cognition, perform bounded reasoning or simulation over available cognition, or pursue new information through existing capabilities.

**Retrieval** reactivates cognition already owned by Persistent Cognition and makes it available to current processing. Retrieval preserves the retrieved object's semantic type and provenance: recalling a Belief does not turn it into Evidence, and recalling a Memory does not make it authoritative external truth.

**Inquiry** is information-seeking behavior used to obtain information that is not already available as owned current or persistent cognition. The source may be a sensor, person, file, manual, database, API, source tree, Web source, or another external or not-yet-integrated information source. Physical locality is not the semantic boundary; cognition ownership and integration are.

Inquiry should reuse ordinary agency and authority paths when it requires action or external access:

```text
Active Question / present insufficiency
  -> Current Intent when investigation deserves commitment
  -> information-seeking Skill / Action
  -> source result / Observation
  -> provenance-bearing Evidence or candidate material
  -> Assessment / Belief / Present update
  -> optional governed Experience Integration
  -> Memory / other Persistent Cognition
```

Information acquisition does not grant authority by itself. A model-generated simulation remains a prediction or candidate assessment unless an authorized observation, source, or consequence path supplies stronger grounding. Likewise, a procedure named `verify` does not create truth merely by its name.

Choose among Retrieval, Inquiry sources, and other deliberate mechanisms using the same bounded selection rule above. Freshness, source reliability, expected information value, latency, monetary or compute cost, risk, and deadline may change the preferred path. Do not hard-code a universal ladder such as memory -> local file -> network, and do not create a universal `Knowledge` store merely because information can be accessed externally.

`Thinking Mode`, `Retrieval`, and `Inquiry` are therefore useful descriptive mechanism names, not new top-level semantic owners unless future implementation demonstrates independent state, authority, or lifecycle that cannot be reduced to current owners.

Prefer event-driven decision epochs over a single monolithic tick loop.

Keep the runtime distinctions explicit:

```text
raw/external event
  != admitted material change
  != decision epoch
  != cognition request
  != RelayEngine call
```

A decision epoch may only service an existing owner-local lifecycle or deadline and then return. A
material source change may require Present recomputation without requiring model inference; an
Action Supervision deadline may require deterministic lifecycle work without Skill reselection or
Intent reconsideration. Conversely, unresolved local uncertainty may justify a cognition request.
No event, deadline, or unresolved need may also mean no epoch at all.

Coordination does not transfer ownership: an Action deadline remains Action Supervision state, a
Current Intent remains owned by Intent Commitment, and a Skill execution remains its own lifecycle.
When several events are coalesced for efficiency, preserve enough causal provenance to reconstruct
which source change or deadline caused material work. Do not introduce a monolithic RuntimeDriver,
generic event bus, or mandatory model-call cadence merely to connect these decision epochs.

## 12. Time is explicit

The runtime should not rely on one ambiguous timestamp for all semantics.

Relevant time domains may include:

- runtime monotonic sequence or time;
- environment or world time;
- subjective or cognitive time;
- branch or epoch identity when rollback or alternate histories exist.

Rollback of the environment must not silently erase causal provenance in the runtime trace.

## 13. Causal trace is a first-class requirement

Trace should be designed with the runtime rather than added only after failures become difficult to explain.

Representative events may include:

```text
OBSERVATION_RECEIVED
NEED_ACTIVATED
QUESTION_REACTIVATED
RECONSIDERATION_TRIGGERED
INTENT_PROPOSED
INTENT_FILTERED
INTENT_SELECTED
SKILL_STARTED
ACTION_PROPOSED
ACTION_AUTHORIZED
ACTION_EXECUTED
CONSEQUENCE_OBSERVED
STATE_UPDATED
MEMORY_WRITTEN
SKILL_TERMINATED
ENVIRONMENT_ROLLBACK
```

Each event should carry enough provenance to reconstruct causal relationships and authority where practical.

Important rejected alternatives should be explainable, not only the selected winner.

## 14. Boundary adapters should stay small

Generic environment or body adapters should report observations, capabilities, and events rather than embed the whole cognitive policy.

For example, a Body Adapter should expose body facts and capabilities. It should not decide that a fact means "I should eat now." Regulation and arbitration belong above the observation boundary.

Simulation-specific state integration may live in a simulator or environment engine rather than being forced into a universal physical-body interface.

## 15. Environment truth remains external

RelaySelf may own observation, evidence, estimates, belief, appraisal, and action intent. It does not own external world truth merely because it has a model of that world.

Target-native class/type/instance facts remain observations even when Persistent Cognition carries
a matching appraisal disposition. Appraisal projection is a Self-side interpretation step:

```text
World / adapter fact
  -> Self-owned Appraisal Disposition lookup
  -> transient Current Appraisal
```

Neither a class prior nor a Current Appraisal is by itself Action authorization, and exact-instance
experience must not be silently generalized into class-wide World truth.

The boundary must remain valid across different environments, including simulators, virtual worlds, desktop systems, and physical devices.

## 16. Runtime mechanisms must remain subordinate to the basis

Viability guards, reconsideration controllers, skill schedulers, question managers, traces, and adapters are mechanisms that realize the architecture. They are not additional top-level ontological bases by default.

The order of reasoning is:

```text
Minimal Basis
  -> Architectural Principles
  -> Contracts
  -> Mechanisms
  -> Implementation
```

Do not promote a convenient mechanism into a new base concept unless its semantic contract genuinely requires a new architectural boundary.
