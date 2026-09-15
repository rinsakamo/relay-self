# RelaySelf

Persistent cognition, present projection, and embodied control runtime for Relay.

RelaySelf is the self-side architecture of the Relay family. It separates what persists, what matters now, and what connects the self to an environment.

## Minimal basis

RelaySelf is organized around five architectural bases:

1. **Persistent Cognition** — cognitive state that persists across moments and sessions.
2. **Present Projection** — the currently active projection produced from persistent cognition and the current situation.
3. **Embodied Boundary** — perception, internal regulation, arbitration, skills, actions, and consequence processing.
4. **Environment** — world state and dynamics outside the self.
5. **Authority / Provenance** — the rules and evidence that determine what may be believed, changed, authorized, or persisted.

The Environment is external to RelaySelf and connects through explicit contracts. Authority / Provenance is cross-cutting rather than a peer runtime subsystem.

## Core invariants

- Persistent state is not present state.
- Observation and evidence are not belief.
- Proposal, authorization, execution, and consequence are distinct.
- Self and environment are distinct.
- Model output is not authority by itself.

## Architecture and engineering documents

- [`docs/ontology.md`](docs/ontology.md) — canonical general vocabulary.
- [`docs/architecture.md`](docs/architecture.md) — architectural boundaries and state flow.
- [`docs/runtime-principles.md`](docs/runtime-principles.md) — normative runtime and agency principles.
- [`docs/development-principles.md`](docs/development-principles.md) — change, authority, review, and convergence discipline.
- [`docs/evaluation.md`](docs/evaluation.md) — deterministic, simulation, model-quality, and qualification evidence discipline.
- [`docs/ci.md`](docs/ci.md) — meaning and scope of continuous-integration guarantees.
- [`docs/issues.md`](docs/issues.md) — Issue scope, freshness, and completion reconciliation rules.
- [`docs/contracts/action-lifecycle.md`](docs/contracts/action-lifecycle.md) — executable Action Lifecycle / Authority Boundary transition contract.
- [`docs/migration-from-relaylm.md`](docs/migration-from-relaylm.md) — conceptual migration map from the former RelayLM architecture.
- [`.ai/README.md`](.ai/README.md) — authority and read-order guidance for AI-assisted development.

## Status

RelaySelf is in early executable bootstrap. The Action Lifecycle / Authority Boundary is the first concrete executable contract; most broader runtime behavior remains architectural design rather than implementation fact.

The current Python bootstrap exists to implement and verify that bounded contract. It does not yet declare a supported package-distribution boundary, minimum Python version, dependency floor, complete scheduler, environment adapter, or general authority-policy engine.

Hypotheses, simulation results, and implementation facts must remain distinguishable.

## License

Apache License 2.0.
