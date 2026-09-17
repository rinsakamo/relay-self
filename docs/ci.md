# CI Verification Contract

This document defines what RelaySelf continuous-integration results mean.

> **CI verifies declared contracts. CI does not invent semantics.**

Executable workflow YAML implements checks. This document owns the meaning of a green result. Repository-host rules decide whether a check is required before merge. These are separate facts.

## Verification subject

Every CI result belongs to the exact source head or artifact that was tested.

> **Green is not transferable.**

A result from an older commit, another branch, another artifact, or another environment is evidence about that subject only. When merge policy requires exact-head verification, a new push invalidates the earlier exact-head claim.

## Three distinct CI facts

Never collapse these into one statement:

```text
CI definition    a workflow/job exists and defines executable verification
CI result        a particular run produced a result for a particular subject
CI enforcement   the repository host currently requires that result before merge
```

Source files can prove the first. Workflow-run evidence can prove the second. The third is a live GitHub repository setting and must be checked as such.

## Current source-defined deterministic jobs

RelaySelf currently defines three deterministic CI jobs.

### `CI / repository-contracts`

Guarantee:

> The exact checked-out source head satisfies the repository's current structural documentation and bootstrap-file contract.

The check currently verifies that:

- required authority, governance, executable-contract, and bootstrap files exist;
- local Markdown links resolve to repository paths;
- tracked text surfaces do not contain unresolved merge-conflict markers.

It does **not** prove runtime semantics merely because the corresponding files exist.

### `CI / pytest`

Guarantee:

> The exact checked-out source head passes the current deterministic Python unit and executable-contract test suite under the CI Python runtime.

The current suite includes direct verification of:

- the Action Lifecycle transition contract, including grounded proposal admission from the **current** snapshot of a `STARTED` `SkillExecution` and the actual Current Intent, derivation and retention of immutable Skill-execution / intent association, rejection of stale or terminal Skill snapshots, absent Current Intent, and intent mismatch, preservation of pending-reconsideration semantics, authorization-before-issuance, terminal closure classes, timeout boundary behavior, monotonic Action event time, same-root stale Action snapshot rejection, and invalid-transition failure;
- the Action Supervision contract, including supervised issuance retention, preservation of the Action lifecycle's immutable causal association, next-deadline discovery, explicit decision-epoch timeout processing, monotonic supervisor time, identity handling, terminal ordering, and fail-closed multi-action epoch behavior;
- the Current Intent Commitment contract, including single-active-intent retention, rejection of silent replacement, explicit reconsideration request-before-decision ordering, separate trigger/decision provenance, continue/release decisions, terminal release, identity handling, monotonic time, and fail-closed invalid operations;
- the Skill Execution contract, including immutable execution/skill/intent association, derivation of `intent_id` from the actual Current Intent at the supported start seam, rejection of start when no Current Intent exists, preservation of Current Intent state/history during association validation, explicit success/failure/cancellation terminal classes, cancellation distinct from Skill failure, monotonic Skill event time, provenance/reason validation, same-root stale snapshot rejection, no automatic later-Intent-release-to-Skill-cancellation mutation, and the boundary that Skill terminal state does not automatically release or reconsider Current Intent;
- the bounded lifecycle-linearity regressions, including that a successful Skill or Action transition advances only its same-root lineage after the next snapshot validates, predecessor snapshots cannot create sibling branches, a stale `STARTED` Skill snapshot cannot seed a supported Action proposal, failed transition validation does not consume the current snapshot, and independently created roots with the same textual identity are deliberately not claimed to be globally canonicalized.

The Skill-to-Action proposal tests establish the supported proposal-admission relation:

```text
ActionLifecycle PROPOSED
  -> supplied SkillExecution was current in its supported lineage
  -> supplied SkillExecution was STARTED at proposal admission
  -> supplied Skill intent matched the actual Current Intent at proposal admission
```

They also verify that proposal validation does not mutate Skill event history or Intent Commitment history.

The lifecycle-linearity tests establish only **same-root ephemeral currentness**. They do not turn the private lineage revision into a global runtime registry.

A green result does **not** prove:

- that a repository-wide Skill owner or registry establishes global uniqueness or selects the globally latest execution root for a textual `execution_id` across independently created roots;
- that a repository-wide Action owner establishes global uniqueness or selects one globally canonical proposal root for a textual `action_id` across independently created roots;
- durable lifecycle-lineage retention across serialization, process restart, or distributed execution;
- thread-safe or linearizable concurrent lifecycle mutation;
- that the Skill generated the Action payload or that a useful closed-loop Skill controller exists;
- that Action outcome should imply Skill success/failure/cancellation, or that Skill cancellation should cancel an issued/in-flight Action;
- that a deployed runtime driver eventually supplies future Action Supervision decision epochs;
- autonomous wall-clock scheduling or general Scheduler behavior;
- that an intent candidate was correctly generated, ranked, or selected merely because commitment transitions are legal;
- that a reconsideration trigger was correctly detected, sufficiently important, or admitted by a valid runtime policy merely because a request was recorded;
- that a reconsideration trigger policy detects every meaningful runtime change;
- that a Skill capability was correctly selected, exists in a validated capability library, satisfies initiation preconditions, or implements a useful closed-loop controller merely because its execution lifecycle is valid;
- that a Skill remaining active means its associated Current Intent is still current after start, or that later Current Intent release automatically terminates the Skill;
- that `SkillState.CANCELLED` proves a physical/controller process or issued/in-flight child Action was actually stopped, or that cancellation was safe under an interruptibility policy;
- that Skill success proves primitive Action success or external-world success;
- that Skill failure should always trigger Current Intent reconsideration;
- that an external authority identity is legitimate merely because it was recorded;
- model quality, simulation behavior, environment correctness, or physical execution;
- package installation or minimum-supported Python/dependency floors.

The workflow pins the pytest tool version used by this gate. That pin is CI tooling, not a supported runtime dependency floor.

### `CI / lint`

Guarantee:

> The exact checked-out `src/` and `tests/` Python surface satisfies the configured Ruff mechanical checks.

The configured rule set is intentionally narrow: syntax/pycodestyle error classes, Pyflakes correctness checks, and import ordering.

A green result does **not** prove architectural correctness, type safety, runtime behavior, formatting uniformity outside the configured rules, or lint cleanliness of unrelated repository tooling.

The workflow pins the Ruff tool version used by this gate. That pin is CI tooling, not a supported runtime dependency floor.

## Live merge enforcement

Workflow existence does not prove that a job is required by the repository host.

Required status checks must be inspected in the live GitHub ruleset before a merge claim relies on enforcement. This document intentionally does not turn volatile repository-host configuration into a source-file assertion.

## Invariant-gate decision

The current executable invariants are verified inside `CI / pytest` rather than by a separate `CI / invariants` job.

At the current repository scale, a separate invariants job would execute the same deterministic test surface and would not own a distinct guarantee. Revisit that decision only when a stable invariant surface has a materially different execution contract from ordinary pytest coverage.

## Deterministic CI versus evaluation

Required merge CI should cover properties deterministic enough to function as repository gates.

Actual-model quality, probabilistic agent behavior, latency distributions, simulation outcomes, and physical-environment observations belong to their evaluation or evidence owners unless an explicit transaction proves they are suitable deterministic gates.

> **CI proves deterministic repository contracts. Evaluation measures empirical behavior.**

See [`evaluation.md`](evaluation.md).

## Workflow implementation rules

A workflow implementing a merge guarantee should:

- bind verification to the intended exact source or artifact;
- fail closed when the verification subject cannot be established;
- use least-privilege repository permissions;
- pin executable third-party Actions to reviewed full commit SHAs;
- keep each job responsibility narrow enough that failure has an interpretable meaning;
- avoid hidden network or environment assumptions where a local deterministic check is sufficient;
- use explicit timeouts;
- use cancellation or concurrency rules so stale runs do not create merge ambiguity.

## One named gate, one named guarantee

Do not add a gate merely because another project uses it.

Before adding a required CI job, answer:

1. What concrete failure class does it prevent?
2. What exact subject does green describe?
3. What execution environment does it rely on?
4. Why is the property suitable for deterministic merge enforcement?
5. Which existing guarantee does it complement rather than duplicate?
6. What operational cost and false-positive surface does it add?
7. Which canonical owner defines the rule it verifies?

If two jobs claim the same guarantee, consolidate them or distinguish their contracts.

## CI changes are contract changes

Changing what a named CI job proves is a semantic contract change even if its job name remains unchanged.

A material CI change should converge:

```text
intended guarantee
  -> executable workflow/check
  -> deterministic checker or regression where practical
  -> this CI contract
  -> live required-check configuration when enforcement changes
```

Changing only workflow commands without updating the guarantee is incomplete. Updating only this document without implementing the stated check is also incomplete.

## Review questions

Before considering a CI change complete, a reviewer should be able to answer:

1. What does green prove?
2. What does it explicitly not prove?
3. What exact source or artifact was tested?
4. Is the result for the exact head under review?
5. Is the check merely defined, actually green, and live-required where intended?
6. Does it duplicate another guarantee?
7. Are empirical observations kept out of deterministic CI claims?

The objective is not more gates. The objective is a small set of trustworthy guarantees with stable meaning.
