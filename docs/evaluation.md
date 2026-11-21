# Evaluation

This document defines how RelaySelf claims should be evaluated and reported.

RelaySelf separates architectural invariants, simulation behavior, model quality, and physical or external qualification. These layers answer different questions and must not be collapsed into one score.

## Evidence classes

Every evaluation claim should identify its evidence class.

### 1. Deterministic invariant evidence

Used for properties that should hold independently of language-model quality or scenario luck.

Examples include:

- persistent and present state remain distinct;
- observation or evidence does not become belief without an authorized transition;
- action proposal is not action authorization;
- an issued action closes as an outcome, timeout, or unknown result;
- external truth is not committed by generated language alone;
- invalid authority transitions fail closed.

These properties should be tested directly and machine-readably where practical.

### 2. Simulation evidence

Used for dynamic behavior that emerges over time from state, scheduling, arbitration, skills, environment dynamics, and uncertainty.

Simulation results are evidence only for the recorded configuration, seeds, environment, model or policy versions, and evaluation horizon.

A simulation plan is not a simulation result. Do not report invented run counts, success rates, safety rates, or other measurements.

### 3. Model or system quality evidence

Used for properties that depend materially on model capability, interpretation quality, language behavior, or end-to-end cognitive usefulness.

This layer should remain separate from deterministic runtime correctness. A fluent model does not prove authority safety; a correct runtime invariant does not prove useful cognition.

### 4. External or physical qualification evidence

Used when a claim depends on real devices, host conditions, GPUs, network services, robotics stacks, or other external execution state.

Qualification must identify the actual condition being proven. Exploratory rehearsal may discover how to run a procedure, but it must not be retroactively treated as citable qualification evidence.

## No composite score by default

RelaySelf should not hide independent failure modes behind a weighted aggregate score by default.

Report metrics by architectural boundary and failure class. A system that is excellent on average but violates an authority or viability invariant is not equivalent to one that preserves the invariant.

## Evaluation dimensions

The exact metrics may evolve, but evaluation should preserve at least the following dimensions when relevant.

### Authority and grounding

- unauthorized state mutation;
- evidence-to-belief promotion errors;
- presentation or model output incorrectly treated as fact;
- stale, superseded, or wrong-provenance evidence use;
- specification, attested state, and predictive estimate confusion.

### Viability and regulation

- viability-boundary violations;
- time or exposure spent near critical boundaries;
- unsafe continuation when recovery was available;
- deadlock caused by over-restrictive gating;
- unnecessary maintenance that prevents useful behavior.

### Intention and arbitration

- excessive intent switching or oscillation;
- failure to reconsider after meaningful invalidation;
- unnecessary reconsideration cost;
- missed urgent preemption;
- unsafe interruption of non-interruptible work;
- domination by one concern class such as a question or relationship concern.

### Question handling

- futile retries while blocked;
- failure to reactivate after blocker change or new evidence;
- unresolved-question monopolization;
- premature resolution without sufficient evidence;
- failure to distinguish dormant, blocked, resolved, abandoned, superseded, and unknowable states when those states are implemented.

### Skill and action execution

- precondition violations;
- repeated skill failure without adaptation or escalation;
- missing action closure;
- disagreement between claimed and observed consequence;
- missed or invalid yield points;
- capability-model errors that cause impossible action selection.

### Inactivity and waiting

Raw inactivity is not a failure metric.

Distinguish justified wait, rest, observation, recovery, and opportunity-waiting from pathological or unexplained idling. Prefer a metric such as unjustified inactivity over idle ratio alone.

### Cognition cost

When model inference is part of the system, record cognition calls, latency, resource use, and avoidable deliberation. Calling cognition is itself a runtime decision and should be evaluated as such.

For a claim that a Skill, routing rule, cached procedure, learned policy, or other crystallized mechanism **narrows cognition**, use an outcome-preserving matched comparison where practical:

```text
less-structured baseline cognition path
vs
narrowed / crystallized path
```

A narrowing claim is supported only when the structured path preserves the task-specific useful outcome and required architectural invariants while materially reducing one or more relevant cognition costs without hiding unacceptable regressions elsewhere.

Do not reduce cognition cost to one repository-wide scalar by default. Report relevant dimensions separately, such as:

- context or input tokens;
- generated or output tokens;
- number of model calls;
- latency;
- retrieval calls or candidate-set size;
- Inquiry / external lookup calls;
- compute or accelerator time;
- memory or energy proxy where relevant;
- escalation frequency and the cost of successful escalation.

Outcome quality should likewise remain explicit: task/decision correctness or utility, consequence quality, invalid-output or failure rate, calibration where relevant, behavior under novelty/distribution shift, and successful escalation when the bounded path is insufficient.

Lower cost does not compensate for an authority or viability regression. Likewise, a Skill should not receive credit for compression merely because it was given less factual information than the baseline and therefore solved an easier problem.

Keep **cognitive narrowing** distinct from **experience-dependent crystallization**:

```text
cognitive narrowing
  = reusable structure / routing makes the current problem smaller

crystallization
  = prior computation or experience produces reusable structure
    that makes future cognition cheaper
```

A pretrained Skill or fixed routing rule can demonstrate narrowing without demonstrating individual experience-dependent crystallization. Conversely, a crystallization claim needs evidence about how the reusable structure was obtained, not only that the final fast path is cheap.

A bounded path that handles common cases cheaply and escalates uncertain, novel, or contradictory cases to more expensive cognition may still be high quality. Report escalation behavior rather than counting every escalation as automatic failure.

## Distributional reporting

For stochastic simulations, do not report only a mean.

Where sample size justifies it, report distributional behavior such as median, tail percentiles, worst observed seed, failure count, and relevant confidence or uncertainty. Preserve the raw conditions needed to reproduce notable failures.

A single severe counterexample may matter more than a small improvement in an average metric when the violated property is architectural or safety-critical.

## Counterexample-first review

Evaluation should actively search for cases that falsify the claimed invariant or design benefit.

Useful stress categories include:

- resource conflict;
- sudden internal-state change;
- unavailable resources;
- false or stale predictive estimates;
- blocked information goals;
- deadline pressure;
- changing affordances;
- action interruption;
- world rollback or branch change;
- distribution shift;
- missing safe action;
- external intervention.

The purpose is not to prove perfection but to expose where the current contract stops holding.

## Ablation discipline

When claiming that a mechanism improves behavior, compare against a version in which that mechanism is absent or replaced by a simpler alternative when practical.

Examples may include removing:

- viability gating;
- prediction or allostatic lookahead;
- hysteresis;
- intent commitment;
- reconsideration control;
- blocker signatures;
- bounded aging;
- interruptible skill semantics.

Do not attribute an observed improvement to a mechanism merely because the mechanism was present in a successful run.

## Evaluation stages

A practical sequence is:

```text
small deterministic / unit checks
  -> short debug simulations
  -> configuration or mechanism comparisons
  -> longer stochastic runs
  -> adversarial and distribution-shift cases
  -> external or physical qualification when applicable
```

Do not begin with a large world merely because it is the intended product environment. Small discrete environments are often better for finding semantic defects, causal ambiguity, oscillation, and authority violations.

## Trace requirements

A result is easier to trust when the system can explain its causal path.

Evaluation traces should preserve enough information to answer:

- what was observed;
- what was believed or appraised;
- what concerns or candidates were active;
- what was filtered and why;
- what intent was selected;
- what action was proposed and authorized;
- what consequence was observed;
- what durable state changed;
- which authority or model version supported each transition.

When practical, record why important alternatives were not selected, not only why the winner was selected.

## Reporting rule

Never blur these statements:

```text
Hypothesis:
  "This mechanism should reduce oscillation."

Simulation result:
  "Under recorded configuration X, run set Y observed fewer switches."

Implementation fact:
  "The current runtime enforces a minimum commitment interval under condition Z."
```

Only the evidence appropriate to each class may support the corresponding claim.
