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

RelaySelf currently defines four deterministic CI jobs.

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
- the minimum Persistent Cognition restart slice, including validated `IdentitySpecification`, `Memory`, and exact-scope `AppraisalDisposition` values; separate source/integration provenance; explicit Identity/SOUL-seeded appraisal admission; exact-scope experience integration without implicit instance-to-class generalization; duplicate-memory / duplicate-appraisal rejection; versioned JSON save/load round-trip including bounded v1 -> empty-appraisal compatibility; and fail-closed handling of unsupported versions, unknown fields, missing files, and corrupt JSON.
- the minimal appraisal projection contract, including target-native class/instance facts remaining separate from Self-owned appraisal, directional non-emotion bias, exact-instance disposition precedence over a class prior for the same appraisal aspect, neutral behavior when no applicable disposition exists, and no `enemy` / `ally` / Action-authorization field or shortcut.
- the controlled Minecraft appraisal-prior integration path, including that an explicitly supplied Persistent Cognition harm-likelihood prior can narrow the same target-native entity observation toward FLEE even when scenario-local hazard names are empty, while exact-instance neutral experience can weaken that entity's Current Appraisal without rewriting the class prior for a novel entity.
- the minimal admitted decision-epoch coordinator, including Action Supervision before caller-owned decision work, deterministic no-cognition completion, exactly-once invocation of a supplied RelayEngine seam for an opaque unresolved request, explicit failure when cognition is requested without an engine, preservation of already-committed supervision outcomes across later cognition failure, and return of the next owner-local Action deadline without creating a clock owner.
- the RelayEngine cognition contract, including the unchanged bounded finite-choice path (finite unique choice admission, provenance-bearing transient context, BOUNDED -> optional explicit THINK, inadmissible-choice fail-closed behavior, no retries beyond the declared modes, content-free per-attempt work facts, and observational soft-wall-time comparison) plus the additive open path: provenance-bearing context with no finite choice/THINK surface, exactly one OPEN provider call, non-empty transient expression output with request identity/output provenance/elapsed work/provider facts, wrong provider result-family failure, and no hidden THINK retry. The request types also admit one optional canonical `IdentitySpecification` projection separately from dynamic context; projection determinism, source/provenance sensitivity, and invalid generic-datum rejection are tested directly.
- the target-local llama.cpp RelayEngine provider and qualification logic under mocked HTTP/provider evidence, including deterministic BOUNDED/THINK rendering with the existing finite-choice strict schemas, additive OPEN rendering without a finite choice/decision schema, reasoning_effort=none on all modes, preservation of provenance in model-facing JSON, one common leading generated-provider contract + canonical identity block across BOUNDED / THINK / OPEN before mode-specific material, identity remaining outside generated dynamic payload, explicit same-semantics identity carriage in Jev/System One state, `cache_prompt=false` remaining unchanged, empty/non-stop OPEN output and malformed bounded output remaining provider/protocol failures rather than cognitive uncertainty, transport/envelope failure remaining operational provider errors, preservation of provider-reported token usage/finish reason plus the applied max-output request bound when available, and the existing clean-checkout/runtime/expected-choice qualification guarantees for the bounded live path. Green CI does not prove token-prefix identity across Jev/chat templates or prompt/KV cache correctness.
- the read-only human activity-summary projection, including deterministic Mineflayer movement compaction, preservation of first/last movement provenance, retention of non-movement body/session/effect events, direct projection of existing Intent/Skill/Action histories without a new lifecycle owner, append-only Persistent Cognition Memory delta reporting with source/integration provenance, explicit distinction between unsupplied source surfaces and observed absence, and Markdown rendering that performs no source-state mutation.
- the controlled Minecraft MVP scenario harness under deterministic fake-session evidence, including scenario-local WAIT/EAT/FLEE admission from current Mineflayer facts, FLEE precedence over food maintenance when a configured hazard is present, finite RelayEngine destination selection only when multiple FLEE destinations require cognition, preservation of retained Memory as prior Memory rather than current World evidence, Mineflayer destination-heading yaw matching the target's own `bot.lookAt()` convention, supervised EAT and FLEE primitive Actions, primitive effect-result and FLEE-progress waits bounded by the existing time deadline rather than raw-message count, EAT success only after later food increase, FLEE success only after later progress toward the selected destination, and healthy WAIT with no Skill or Action creation.
- the controlled Minecraft explicit Memory/restart transaction, including the boundary that successful FLEE does not persist automatically, explicit Memory creation only from observed successful FLEE progress with separate source/integration provenance, reuse of the existing versioned Persistent Cognition save/load path, same-identity restart, later bounded cognition receiving reloaded Memory as prior experience alongside independently provenance-bearing fresh Mineflayer evidence, rejection of arbitrary free text as the controlled destination Memory payload, and read-only operator summary generation from underlying histories rather than summary-text persistence.
- the bounded #141 terminal-composition apparatus, including vanilla Hunger-effect resource setup rather than unsupported player-NBT mutation, fresh Mineflayer low-food verification before EAT admission, one overall deadline for required-observation waits even under high-frequency raw events, and fail-fast launcher ordering that prevents restart phase execution after first-phase failure.
- the adapter-local Mineflayer Python protocol surface, including exact-version startup validation, target-local session/sequence continuity, provenance references, strict survival observation/effect-result schemas, closed locomotion, heading, and food-effect encoding, bounded time/inventory/entity fact decoding, and rejection of injected appraisal labels or unsupported adapter fields.
- the concrete Mineflayer runtime-admission seam, including suppression of high-frequency ordinary move events from automatic high-level epochs, admission of bounded material body/session/survival observations including time, inventory, and entity fact changes, Action OUTCOME closure from target-native applied/rejected effect results before later decision work, canonical decision-epoch coordination, deterministic zero-model completion, and exactly-once use of a supplied cognition seam when caller-owned work remains unresolved.
- the target-local Mineflayer process-session seam, including one-child launch argument construction, mandatory startup attestation consumption, reuse of the strict stream decoder, explicit primitive-effect writes, explicit EOF failure, no hidden retry/relaunch, and bounded clean-shutdown behavior with termination fallback.
- the reusable Mineflayer live-qualification transaction logic under fake-session evidence, including canonical Current Intent / Skill / Action setup, supervised forward and stop Actions, rejection of a control acknowledgement without later horizontal movement, rejection of pre-ack or vertical-only displacement as movement evidence, rejection of target-native effect rejection, preservation of Skill/Intent state, and report emission only after the post-ack horizontal position-delta condition is satisfied.
- the canonical Mineflayer and llama.cpp live-qualification source-checkout launchers, including successful `--help` startup from an unrelated working directory with operator `PYTHONPATH` absent, proving that each launcher owns the repository `src/` import path and top-level adapter-module working directory without contacting the external runtime.

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
- automatic promotion of Action outcomes, consequence traces, model output, or loaded Memory into current World truth or newly accepted durable Memory;
- persistence/restart of active Current Intent, SkillExecution, Action lifecycle, supervision state, Present Projection, or external environment state merely because the minimal Persistent Cognition snapshot can restart;
- thread-safe or linearizable concurrent lifecycle mutation;
- that the Skill generated the Action payload or that a useful closed-loop Skill controller exists;
- that Action outcome should imply Skill success/failure/cancellation, or that Skill cancellation should cancel an issued/in-flight Action;
- that a deployed runtime driver eventually supplies future Action Supervision decision epochs;
- autonomous wall-clock scheduling or general Scheduler behavior;
- generic adapter-event admission/classification beyond the first Mineflayer-local policy, Present reprojection policy, Skill selection, or proof that any deployed external loop will call the admitted decision-epoch coordinator at the right times;
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
- actual localhost llama.cpp connectivity, a successful model/system qualification, or general model-backed RelayEngine quality merely because the bounded RelayEngine / mocked llama.cpp provider tests are green;
- that a human activity summary is Evidence, Belief, Memory, fresh World truth, or a complete cross-owner universal timeline merely because the reducer and renderer tests are green;
- that an observational soft cognition budget is a hard provider cancellation deadline, a World deadline, World time, subjective time, a learned optimal allocation, or evidence that shorter cognition caused a later successful consequence;
- live controlled-world EAT/FLEE quality, correct general threat appraisal, safe navigation, or end-to-end #141 qualification merely because the scenario-local fake-session harness is green;
- that every successful Skill should become Memory, that retained controlled-scenario Memory is current World truth, or that restart preserves active Intent/Skill/Action lifecycles merely because the explicit restart transaction is green;
- live Mineflayer/Minecraft connectivity or a successful external qualification merely because the survival protocol, admission, process-session, or qualification-transaction logic tests are green;
- package installation or minimum-supported Python/dependency floors.

The workflow pins the pytest tool version used by this gate. That pin is CI tooling, not a supported runtime dependency floor.

### `CI / lint`

Guarantee:

> The exact checked-out `src/`, `tests/`, `experiments/`, adapter-local Python, and `observability/` surfaces satisfy the configured Ruff mechanical checks.

The configured rule set is intentionally narrow: syntax/pycodestyle error classes, Pyflakes correctness checks, and import ordering.

A green result does **not** prove architectural correctness, type safety, runtime behavior, formatting uniformity outside the configured rules, or lint cleanliness of unrelated repository tooling.

The workflow pins the Ruff tool version used by this gate. That pin is CI tooling, not a supported runtime dependency floor.

### `CI / mineflayer-adapter`

Guarantee:

> The exact checked-out source head passes the first target-local Mineflayer adapter syntax and pure protocol tests under Node 22.

The job:

- checks JavaScript syntax for the adapter protocol and bridge entry point;
- verifies the package manifest pins Mineflayer 4.39.0 and declares Node >=22;
- runs pure Node protocol/runtime-hook tests for local connection arguments, bounded control/heading/food commands, body/time/inventory/nearby-entity snapshot projection, suppression of ordinary within-phase time progression from repeated time admission, appraisal-label exclusion, session/sequence envelope fields, deferred inventory-listener attachment after Mineflayer internal plugin injection, first-spawn observation deferral until Mineflayer has initialized health/food, explicit null representation for oxygen not yet reported by Mineflayer, and fail-closed rejection of malformed non-null oxygen values.

A green result does **not** prove:

- that the Mineflayer npm dependency can be installed in the target deployment;
- that a Minecraft server connection succeeds;
- that a control-state or heading acknowledgement means movement, destination arrival, or Skill success;
- correctness of Self-side threat appraisal, food choice, EAT/FLEE Skill success, reconnect, or authenticated-account support;
- live external qualification of the adapter; the reusable live-qualification harness must still be run against an actual Minecraft server and its result recorded as external evidence.

This job intentionally does not install Mineflayer or contact a Minecraft server; those are external qualification concerns for the concrete adapter.

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
