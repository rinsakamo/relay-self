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

## Current merge baseline

RelaySelf currently has one deterministic repository gate:

### `CI / repository-contracts`

Guarantee:

> The exact checked-out source head satisfies the repository's current structural documentation contract.

The check currently verifies that:

- required authority and governance files exist;
- local Markdown links resolve to repository paths;
- tracked text surfaces do not contain unresolved merge-conflict markers.

It does **not** prove:

- that future runtime contracts are implemented;
- language-model quality;
- simulation performance;
- physical or external-system qualification;
- security, type-safety, packaging, or multi-platform compatibility unless separate gates are introduced for those guarantees.

The baseline should grow only when the repository contains a concrete deterministic contract worth enforcing.

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