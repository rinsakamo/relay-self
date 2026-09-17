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

Skill selection may narrow Focus, Attention, Retrieval, admissible local actions, and parameter space without becoming the semantic owner of those mechanisms. Skill-local narrowing must remain penetrable by global viability, authority, reconsideration, and consequence evidence.

Parameter binding is likewise not a new owner by default. A simple Skill may require concrete values before execution begins, while a later closed-loop controller may bind or revise some values progressively. A prediction, retrieval result, or heuristic value used for binding does not become attested world state merely because the Skill consumes it.

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

Experience may make an expensive computation reusable through Memory, a learned policy, a Skill, a cached procedure, or another justified mechanism. Such amortization does not make the shortcut permanently authoritative: contradictory consequence evidence, changed applicability, novelty, or distribution shift should be able to invalidate the cheap path and trigger renewed processing where useful.

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
