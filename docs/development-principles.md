# Development Principles

This document defines the default development discipline for RelaySelf.

The purpose is to preserve architectural meaning while keeping implementation work small, reviewable, and evidence-grounded. It carries forward lessons from earlier Relay development without inheriting historical module boundaries or process ceremony by default.

## Governing sequence

For semantic changes:

> **Meaning → Example → Test → Code → Docs / Authority → Audit**

Meaning comes first. Tests freeze the intended contract. Code realizes it. Current authority documents converge with the implementation. Final review checks the exact resulting change rather than the remembered intent.

This sequence is not required mechanically for every edit. Behavior-preserving refactors and docs-only changes should use the lightest verification that honestly proves their claim.

## 1. Classify the change before writing

### Semantic change

Use this class when behavior, meaning, authority, state ownership, lifecycle, validation, persistence, or an external contract changes.

Before implementation, establish:

- the intended meaning;
- one or more concrete examples or Given / When / Then cases;
- the affected architectural boundary or semantic owner;
- explicit non-goals;
- the evidence that will show the change is correct.

A new regression test should fail because the intended behavior is absent, not because the fixture, environment, or tooling is broken.

### Behavior-preserving change

Use this class for refactors, extractions, renames, relocation, simplification, and performance work intended to preserve semantics.

Do not manufacture a fake RED test. Establish the before/after contract through existing regressions or bounded characterization. If the work reveals an intentional semantic change, reclassify it.

### Docs-only change

Ground documentation changes in current architecture, implementation, and evidence. Do not describe deferred behavior in the present tense. Do not hand-edit generated or derived projections as if they were canonical authority.

## 2. One bounded responsibility per transaction

A change should own one bounded responsibility and name material non-goals.

A transaction may inspect wider context than it mutates. Discovery scope may be broad; mutation scope should remain narrow.

If completing the stated change requires unrelated semantic expansion, stop and split or redefine the work rather than silently absorbing it.

## 3. One concept, one current owner

A semantic concept should have one current canonical writer.

File boundaries, issue boundaries, package boundaries, or implementation convenience do not create independent semantic owners.

When ownership is ambiguous, resolve the ambiguity before introducing new state, fallback paths, or duplicate authority.

Owner-local authority should be introduced only when the semantic boundary is stable enough to justify it. Do not create a dense authority map merely to anticipate future components.

## 4. Converge on the canonical path

Fix the canonical path rather than creating a second internal path that exists because the first one is broken.

Avoid by default:

- temporary semantic bridges with no external-contract reason;
- dual-read or dual-write paths for superseded internal meaning;
- hidden fallbacks that silently change implementation;
- old-path aliases whose only purpose is internal compatibility;
- simultaneous old and new semantic authorities;
- runtime monkeypatching or module replacement required for production behavior;
- test-only architecture that materially differs from the production path it claims to verify.

Permanent adapters are valid at genuine external boundaries when they translate the current RelaySelf contract. An adapter must not become a second internal owner.

Do not extract a generic cross-target boundary protocol from one adapter's native lifecycle, identifiers, feedback, acknowledgement, or transport machinery. Keep those details target-local unless materially different adapters repeatedly demonstrate the same non-reducible RelaySelf-side semantic responsibility; shared syntax or implementation convenience alone is not evidence of a shared semantic contract.

Specification-grounded adapter probes may justify deferring such extraction, but they do not by themselves prove that a concrete adapter has an independently versionable, operable, or qualified product boundary.

## 5. Authority is part of the implementation

A behavior change is incomplete if code and tests are current but the owning authority document still describes an older contract.

Prefer local canonical facts over hand-maintained aggregates. Repository-wide maps and generated views should be derived when needed rather than manually synchronized by every transaction.

Historical notes, old issues, earlier comments, previous run results, and remembered SHAs are evidence. They do not replace fresh repository facts or current authority.

## 6. Preserve authority boundaries in code

Implementation must preserve the architectural distinctions defined elsewhere in this repository, including:

```text
Persistent != Present
Observation / Evidence != Belief
Proposal != Authorization != Execution != Consequence
Self != Environment
```

Model output is a proposal or interpretation unless an explicit authority path promotes it. Language generation does not by itself mutate world truth, body fact, durable cognition, or action completion.

## 7. Prefer explicit seams over hidden substitution

External systems, clocks, randomness, filesystems, providers, and devices should be isolated behind explicit seams where practical.

Tests may use fakes, mocks, or failure injection around such seams. Test instrumentation must not replace the semantic behavior under test with the expected answer or create an alternate production architecture.

## 8. Fresh-head review

Before merge, review the exact final head rather than an earlier checkout, summary, or remembered diff.

Ask:

1. Does the change express the intended meaning or preservation claim?
2. Did it add more semantics or machinery than required?
3. Does it create duplicate authority, hidden fallback, compatibility residue, or a second path around a broken canonical path?
4. Do docs and code agree about what is current versus deferred?
5. Are there materially equivalent supported paths that contradict the claimed invariant?
6. Does the cumulative diff still fit the bounded responsibility?

A material mismatch means the transaction is incomplete.

## 9. Exact-head verification

When automated checks exist, required verification must correspond to the exact head that was reviewed and merged.

A new push invalidates earlier exact-head review and exact-head CI claims. Local output and historical CI can be useful evidence, but they do not substitute for required current-head checks.

Merge should use expected-head protection where the platform allows it.

## 10. Evidence from external or physical execution

When work depends on a host, GPU, device, simulator, external service, or manual procedure whose outcome cannot be reconstructed from repository authority alone, preserve only the material lesson.

Distinguish:

```text
reusable procedure or invariant
  -> promote through the responsible owner or regression

immutable execution result
  -> preserve under the appropriate evidence boundary

volatile observation
  -> keep historical; do not copy into current authority
```

Exploratory rehearsal is not automatically qualification evidence. A successful trial may teach a procedure without proving the final claim.

## 11. Stop conditions

Stop and reconstruct the work when:

- semantic ownership is ambiguous or contested;
- a required dependency is not current or not yet available;
- fresh repository facts cannot be obtained;
- a bounded change would require material unrelated scope expansion;
- review finds an unresolved counterexample to the completion claim;
- required current-head verification fails or is unavailable;
- the proposed implementation requires duplicate authority or hidden fallback to appear correct.

## 12. Completion claim

Do not claim more than the evidence supports.

Every completion statement should be classifiable as one or more of:

- **implementation fact** — confirmed by the current repository implementation and appropriate verification;
- **simulation result** — produced by an identified simulation run and its recorded conditions;
- **hypothesis** — a design proposal, expected property, or unverified explanation.

The distinction is part of engineering correctness, not merely documentation style.
