# AI Development Authority

This directory defines repository-level guidance for AI-assisted development.

## Read order

Before making architectural or behavioral changes, read:

1. `README.md`
2. `docs/ontology.md`
3. `docs/architecture.md`
4. `docs/runtime-principles.md`
5. `docs/development-principles.md`
6. `docs/evaluation.md`
7. `docs/ci.md`
8. `docs/issues.md`
9. `docs/migration-from-relaylm.md`

Migration notes explain origin and continuity, but current ontology, architecture, runtime, development, evaluation, CI, and Issue-governance documents take precedence.

Load narrower contracts and owner-local authority when they are introduced and relevant to the change. Do not create speculative authority files merely to anticipate future components.

## Authority rules

- Do not treat model output as authority by itself.
- Keep observation/evidence, belief, appraisal, and presentation separate.
- Keep persistent cognition separate from present projection.
- Keep proposal, authorization, execution, and consequence separate.
- Keep self state separate from environment state.
- Prefer one authoritative document for each architectural statement; avoid manually maintained duplicate projections.
- Fix the canonical path rather than introducing a second internal path around a defect.
- Treat historical issues, comments, run results, and earlier SHAs as evidence, not fresh authority.
- Treat Issues as planning and remaining-work ledgers rather than semantic authority.
- Treat a green CI result as evidence only for the exact subject and guarantee it actually tested.

## Evidence discipline

Always distinguish:

1. **Hypothesis** — a design proposal or unverified explanation.
2. **Simulation result** — an outcome actually produced by a recorded simulation under identified conditions.
3. **Implementation fact** — behavior confirmed by the current repository implementation and appropriate verification.

Do not invent empirical results, measurements, completed experiments, or implementation status.

A normative design document does not by itself prove that the runtime implements the design.

## Change discipline

For semantic changes, follow the repository development sequence:

> **Meaning → Example → Test → Code → Docs / Authority → Audit**

Architectural changes should preserve provenance: explain which authority document changes, what boundary moves, and whether the change affects ontology, runtime principle, contract, mechanism, implementation, or product surface.

Keep each transaction bounded. Resolve semantic ownership before adding duplicate state or fallback paths. Review and verify the exact final head before merge when repository tooling supports it.

When an Issue owns the remaining-work question, reconcile that Issue after terminal completion. A merged PR does not automatically prove the Issue is complete.

## Evaluation discipline

Do not collapse deterministic invariants, simulation behavior, model quality, and physical/external qualification into one undifferentiated claim.

Use `docs/evaluation.md` to determine what evidence is appropriate for a claim. A successful exploratory run may teach a procedure without proving the final qualification claim.

Use `docs/ci.md` to determine what a green CI result does and does not prove. CI definition, CI result, and live repository enforcement are separate facts.
