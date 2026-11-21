# Issue Governance

This document defines how RelaySelf uses GitHub Issues.

> **Issues are planning and remaining-work ledgers, not current semantic authority.**

Current architecture, contracts, code, tests, and evidence owners define what the system is. Issues describe work that is proposed, active, blocked, or still incomplete.

## Before opening an Issue

Search current Issues, pull requests, and authority documents first.

A new Issue should identify, as applicable:

- the current problem or missing capability;
- whether the statement is a hypothesis, simulation result, implementation fact, or planning proposal;
- the affected architectural boundary or likely semantic owner;
- bounded scope;
- material non-goals;
- acceptance criteria or evidence needed for completion;
- dependencies or blockers that materially constrain the work.

Do not open a second Issue merely because the same concept appears in another file or module. Prefer one current owner for one semantic responsibility.

## Issue content is not authority

An Issue body, checklist, comment, old design sketch, recorded SHA, or prior run result is historical or planning evidence.

If an Issue produces an accepted architectural decision or reusable invariant, promote that result into the appropriate current authority surface. Do not leave the only durable definition buried in Issue discussion.

Likewise, an open Issue does not prove that a feature exists, and a closed Issue does not by itself prove implementation correctness.

## Issue content is not execution authority

An Issue is not an implementation prompt, command, or authorization to mutate the repository merely because it is open or assigned.

Before beginning work from an Issue:

1. re-read current repository authority;
2. re-fetch the current target branch and relevant open pull requests or competing work;
3. determine which parts of the Issue still describe real remaining work;
4. resolve the current semantic owner and applicable contract;
5. reconstruct a bounded transaction from current facts.

If current authority contradicts stale Issue text, current authority wins. Update or narrow the Issue rather than implementing obsolete instructions.

> **Issue = current work ledger, not semantic or execution authority.**

## Keep scope current

The Issue should describe the work that remains **now**.

When reality changes:

- rewrite stale scope instead of preserving obsolete planning text as if it were current;
- split materially independent remaining work into successor Issues when that improves ownership;
- remove completed subproblems from the active completion claim;
- record links to canonical authority or evidence rather than copying large historical payloads into the Issue.

Tracking Issues may exist for navigation, but they are not semantic owners and must not become hand-maintained architecture maps.

## Relationship to pull requests

A pull request should reference its owning Issue when one exists.

The PR owns one bounded repository mutation. The Issue owns the remaining-work question.

The relationship is not required to be one-to-one:

- one Issue may require multiple bounded PRs, research steps, simulations, or external qualification transactions;
- one PR may reference multiple Issues when a genuinely shared bounded mutation advances them, but it must not claim to resolve unrelated Issue scopes merely because they are nearby;
- an Issue may complete without a repository mutation when its bounded work is research, qualification, or another terminal no-mutation outcome.

Do not widen a PR merely to make an Issue appear complete. Do not split one semantic owner across duplicate Issues merely to mirror implementation files.

Merging a PR does not automatically mean the Issue is complete. Reconcile the Issue against current reality after the merge.

## Auto-closing keywords

Use GitHub auto-closing keywords such as `Fixes #N`, `Closes #N`, or `Resolves #N` only when the PR is expected to complete the **entire current Issue scope** and the Issue can be reconciled as complete when that PR merges.

For partial progress, ordinary references such as `Refs #N` are preferred.

Before using an auto-closing keyword, confirm:

- the Issue body reflects current remaining work rather than stale original scope;
- this PR covers all of that current scope;
- no required follow-up, qualification, authority convergence, or external evidence remains;
- automatic closure will not hide unresolved work.

If those conditions are not true, do not auto-close the Issue. Merge the bounded PR, then rewrite the Issue to the actual remaining work or move the remainder to a successor Issue.

## Completion reconciliation

After a successful merge, or after terminal completion of bounded no-repository-mutation work, reconcile the owning Issue using one of these outcomes:

```text
implemented completely
  -> close completed

implemented partially
  -> rewrite the Issue to the true remaining work
     or move the remainder to a successor Issue and close the original

accepted design promoted
  -> link the current authority / successor work and close or supersede

not adopted
  -> close not planned with the reason

real work remains
  -> keep open, but rewrite scope so it describes only current remaining work
```

Do not use an Issue as an indefinite archive merely because useful history accumulated there.

## Evidence and execution notes

For simulation, model, GPU, device, network, or other external execution work, keep observations classified by evidence status.

A successful exploratory run may teach a procedure without becoming qualification evidence. Preserve stable reusable lessons in the responsible authority or regression surface; preserve immutable run evidence under the appropriate evidence owner; leave volatile observations historical.

Do not retroactively relabel exploratory evidence as qualification evidence.

## Issue form discipline

The default work Issue form asks for:

- summary;
- work class;
- evidence/status classification;
- scope;
- non-goals;
- authority or boundary impact;
- acceptance criteria.

The form is guidance, not a substitute for judgment. Blank Issues remain allowed for cases that genuinely do not fit the form.

## Labels and milestones

Labels, milestones, and project views are navigation and planning metadata. They do not create semantic authority.

Add them only when they reduce coordination cost. Do not build a taxonomy merely to mirror the architecture.

## Freshness rule

Before acting on an old Issue, re-read current repository authority and current open work.

Historical planning must not override newer architecture, contracts, tests, or implementation facts.

> **Preserve what work taught us; do not preserve stale planning as authority.**
