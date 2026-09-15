# AI Development Authority

This directory defines repository-level guidance for AI-assisted development.

## Read order

Before making architectural changes, read:

1. `README.md`
2. `docs/ontology.md`
3. `docs/architecture.md`
4. `docs/migration-from-relaylm.md`

Migration notes explain origin and continuity, but current ontology and architecture documents take precedence.

## Authority rules

- Do not treat model output as authority by itself.
- Keep observation/evidence, belief, appraisal, and presentation separate.
- Keep persistent cognition separate from present projection.
- Keep proposal, authorization, execution, and consequence separate.
- Keep self state separate from environment state.
- Prefer one authoritative document for each architectural statement; avoid manually maintained duplicate projections.

## Evidence discipline

Always distinguish:

1. **Hypothesis** — a design proposal or unverified explanation.
2. **Simulation result** — an outcome actually produced by a recorded simulation.
3. **Implementation fact** — behavior confirmed by the current repository implementation.

Do not invent empirical results, measurements, or completed experiments.

## Change discipline

Architectural changes should preserve provenance: explain which authority document changes, what boundary moves, and whether the change affects ontology, runtime mechanism, or product surface.
