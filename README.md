# RelaySelf

Persistent cognition, present projection, and embodied control runtime for Relay.

RelaySelf is the self-side architecture of the Relay family. It separates what persists, what matters now, and what connects the self to an environment.

## Minimal basis

RelaySelf is organized around five architectural bases:

1. **Persistent Cognition** — cognitive state that persists across moments and sessions.
2. **Present Projection** — the currently active projection produced from persistent cognition and the current situation.
3. **Embodied Boundary** — the causal coupling surface through which the Self receives environment/body observations, regulates and interprets its embodied state, and hands authorized effect commands to external execution.
4. **Environment** — world state and dynamics outside the self, including any authoritative external body/world state and physical or simulated execution owned by the environment implementation.
5. **Authority / Provenance** — the rules and evidence that determine what may be believed, changed, authorized, or persisted.

The Environment is external to RelaySelf and connects through explicit contracts. Authority / Provenance is cross-cutting rather than a peer runtime subsystem.

RelaySelf may maintain a self-model, working self, capability model, body/resource estimate, belief, and appraisal about its embodiment. Those Self-side representations are not authoritative external body or world truth merely because they describe the Self's body or situation.

## Core invariants

- Persistent state is not present state.
- Observation and evidence are not belief.
- Self-side body/resource representation is not authoritative external body truth.
- Proposal, authorization, issuance/external execution, and consequence are distinct.
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
- [`docs/contracts/action-lifecycle.md`](docs/contracts/action-lifecycle.md) — executable Action Lifecycle / Authority Boundary transition contract, including grounded proposal admission and same-root snapshot-lineage linearity.
- [`docs/contracts/action-supervision.md`](docs/contracts/action-supervision.md) — deterministic in-flight Action Supervision contract for explicit decision epochs.
- [`docs/contracts/intent-commitment.md`](docs/contracts/intent-commitment.md) — executable Current Intent commitment and explicit reconsideration contract.
- [`docs/contracts/skill-execution.md`](docs/contracts/skill-execution.md) — executable lifecycle for one Skill execution instance associated with a Current Intent, including same-root snapshot-lineage linearity.
- [`docs/migration-from-relaylm.md`](docs/migration-from-relaylm.md) — conceptual migration map from the former RelayLM architecture.
- [`.ai/README.md`](.ai/README.md) — authority and read-order guidance for AI-assisted development.

## Status

RelaySelf is in early executable bootstrap. The current Python bootstrap implements Action Lifecycle, deterministic Action Supervision, Current Intent commitment with explicit reconsideration requests and decisions, and an independent Skill Execution lifecycle with explicit success, failure, and cancellation terminal classes.

The bootstrap now also includes a deliberately small durable Persistent Cognition slice: one `IdentitySpecification` plus explicitly retained `Memory` values can be written to and restored from a versioned local JSON snapshot. Each retained Memory preserves separate source provenance and integration provenance, so loading a prior Memory does not convert it into fresh World attestation. Snapshot replacement is local/same-filesystem and fail-closed for malformed or unsupported schema data; this is not a general Memory database, migration framework, or active-lifecycle restart mechanism.

The bootstrap also exposes a minimal admitted decision-epoch coordinator. It services due `ActionSupervisor` deadlines first, then runs caller-owned deterministic/reprojection work, and invokes a supplied RelayEngine seam exactly once only when that work returns an unresolved cognition request. The coordinator does not classify raw events, own Present/Intent/Skill state, define a model request schema, own a clock, retry cognition, or constitute a deployed autonomous runtime driver.

The first executable `RelayEngine` seam is now a transient finite-choice mechanism rather than a model owner. It receives a bounded request with finite admissible choices and provenance-bearing model-facing context, asks a replaceable provider once in `BOUNDED` mode, and makes at most one explicit `THINK` escalation when the bounded result is unresolved or outside the admissible choice set. The result remains transient cognition: it does not authorize Actions, mutate Current Intent or Skill state, establish World truth, or persist model output. A target-local llama.cpp adapter now realizes this provider seam through the local OpenAI-compatible chat-completions endpoint, with deterministic parsing and no hidden retry/fallback. A live model/system-quality qualification command is included, but the repository does not yet contain a recorded successful run for the current main.

The repository now also contains the first concrete Mineflayer adapter slice for the Minecraft MVP: a Node >=22 / Mineflayer 4.39.0 target-local JSONL bridge for offline/local connections, bounded control and food primitive effects, and provenance-bearing spawn/body/movement/death/respawn observations. Its Python decoder fails closed on version, session, sequence, and schema mismatches. This code is not yet a live-qualified supported environment adapter and does not imply movement success, Skill success, pathfinding, eating, threat classification, or Minecraft World truth. Adapter-local admission now routes known primitive effect results and selected material body/session observations into the canonical decision-epoch coordinator while leaving ordinary high-frequency `move` updates outside high-level cognition by default. A Mineflayer `applied` or `rejected` effect result closes the primitive Action as a known `OUTCOME`; it still does not determine Skill success/failure. An adapter-local asynchronous process session can now launch one Node bridge, consume its startup attestation, exchange the same JSONL protocol, detect EOF explicitly, and shut it down without reconnect/retry semantics. Live Minecraft connectivity remains unqualified. The target-local survival snapshot now also carries server time when available, inventory item facts, and bounded nearby entity facts without threat/appraisal labels; primitive food realization is split into explicit equip-item and consume-held Actions. A reusable live-qualification harness now exercises the canonical supervised Action-to-Mineflayer path and requires both an applied forward-control result and observed position change before reporting success; the repository still does not contain a recorded successful live Minecraft qualification result.

A read-only operator observability slice now deterministically reduces bounded Mineflayer/lifecycle histories into a compact Markdown activity summary. High-frequency `move` observations are collapsed into provenance-bearing movement spans, while existing Intent, Skill, Action, non-movement Mineflayer events, and optional before/after Persistent Cognition Memory deltas remain inspectable. The summary is presentation only and does not write cognition or create a trace owner.

An experiment-local controlled Minecraft vertical harness now composes current Mineflayer evidence, Current Intent, SkillExecution, Action Supervision, and RelayEngine into bounded WAIT/EAT/FLEE paths without adding a generic RuntimeDriver. EAT requires later observed food increase before Skill success; FLEE requires later observed progress toward the selected destination and always clears movement control through a separately supervised Action. The harness is deterministic/fake-session evidence only and is not yet the terminal live #141 run or restart/Memory integration.

The supported Skill start seam derives its immutable `intent_id` association from the actual Current Intent owned by `IntentCommitment` instead of accepting an arbitrary caller-supplied intent identity. Snapshots derived from one supported Skill start root now share owner-local ephemeral lineage currentness: a successful transition makes predecessor snapshots stale, so an old `STARTED` snapshot cannot create another terminal branch or later seed a supported Action proposal.

The supported Action proposal seam requires the **current** snapshot of a `SkillExecution` in `STARTED` state plus the `IntentCommitment` owner, requires that the Skill's associated intent matches the actual Current Intent, and derives immutable `skill_execution_id` and `intent_id` associations rather than accepting those identities as caller text. Action lifecycle snapshots derived from one proposal root are likewise lineage-linear: after one successful transition, predecessor snapshots remain inspectable but cannot be advanced into alternate authorization, denial, issuance, or closure branches.

These guarantees are intentionally lineage-local. RelaySelf still does not have a repository-wide registry that proves global uniqueness or selects one globally latest root when independently created Skill or Action roots reuse the same textual identity. It also does not claim durable lineage retention across restart/serialization or concurrent/thread-safe lifecycle mutation.

The bootstrap does not yet declare a supported package-distribution boundary, minimum Python version, dependency floor, autonomous runtime driver, general scheduler, environment adapter, arbitration engine, reconsideration-trigger detector, closed-loop Skill controller, global latest-Skill-execution registry, external body/execution runtime, or general authority-policy engine. In particular, Action Supervision does not prove that a deployed clock or event loop will eventually deliver future decision epochs; Intent Commitment does not decide which runtime changes should request reconsideration or which candidate intent should win; and Skill Execution does not validate Skill capability existence or preconditions, generate primitive Actions, automatically cancel when its associated Current Intent later changes, or make local cancellation proof that a physical/controller process or child Action has stopped.

Hypotheses, simulation results, and implementation facts must remain distinguishable.

## License

Apache License 2.0.
