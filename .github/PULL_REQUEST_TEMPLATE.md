## Summary

Describe the bounded change and why it is needed.

## Scope

What responsibility does this PR own?

## Non-goals

What materially related work is intentionally outside this PR?

## Authority / boundary impact

List the current authority, contract, architectural boundary, or implementation surface affected by this change. If none, say so explicitly.

## Issue relationship

Refs #

Use `Fixes`, `Closes`, or `Resolves` only when this PR completes the entire current Issue scope and no required follow-up remains.

## Evidence status

Classify claims made by this PR as applicable:

- Hypothesis / design proposal:
- Simulation or empirical result:
- Implementation fact:
- Documentation / governance-only change:

Do not promote unverified design or historical evidence into implementation fact.

## Verification

Record the verification performed for the exact final PR head. Include commands, CI jobs, simulations, or external evidence only when they were actually run.

## Remaining work

State any known work intentionally left open. If none, say `None`.

## Review checklist

- [ ] The transaction was reconstructed from current authority and current `main`, not from stale Issue text alone.
- [ ] The PR is bounded to one coherent responsibility.
- [ ] Semantic ownership is not duplicated or bypassed by a second internal path.
- [ ] Authority / documentation was reconciled when semantics changed.
- [ ] Hypotheses, empirical results, and implementation facts remain distinguishable.
- [ ] Verification refers to the exact final PR head where exact-head evidence is required.
- [ ] Issue references use auto-closing keywords only when the entire current Issue scope is complete.
