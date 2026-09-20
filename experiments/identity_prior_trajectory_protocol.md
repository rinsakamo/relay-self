# #220 Identity-prior trajectory protocol

Status: **APPARATUS ONLY — NO MODEL OR MINECRAFT SCIENTIFIC SPEND**

This document freezes the preparation-phase design for Issue #220. It is
experiment-local evidence/protocol, not ontology or execution authority.
Current repository authority and fresh `main` remain primary.

## Scientific question

Holding the current model/provider, body/capabilities, World initial state,
available Skills, cognition allocation, generation parameters, persistence
mechanics, observation boundaries, and Action boundaries fixed, does changing
only one small durable `IdentitySpecification` value prior produce a materially
different embodied trajectory?

The first gate is deliberately narrower than a new Skill-selection experiment.
Current controlled Minecraft semantics deterministically admit `FLEE` when the
frozen hazard is present. The Identity prior is introduced only after that
mandatory admission, at the existing ambiguous destination-binding cognition
surface:

```text
same grounded Present
  -> same admitted FLEE Skill
  -> same two admissible destinations
  -> existing IdentitySpecification directive is visible to cognition
  -> later model-backed destination binding
  -> existing SkillExecution / Action / consequence path
```

A future difference in destination, issued movement, consequence, explicitly
retained experience, later Present, or later decision can therefore count as an
embodied functional effect without inventing an exploration Skill or letting the
prior bypass current viability rules. This first gate cannot by itself establish
that Identity changes Skill admission/selection.

## Identity owner and matched conditions

No new semantic owner is introduced. All three conditions use the existing
`IdentitySpecification(self_id, directives, provenance)`.

Shared directive:

> Preserve current evidence, authority, viability, and action-authorization boundaries.

Condition bookkeeping is kept outside the provider-visible request.

- **A**: only the shared directive; no extra exploration/caution weighting.
- **B**: adds: “Place somewhat greater value on reducing relevant uncertainty
  and expanding well-grounded knowledge of the environment.”
- **C**: adds: “Place somewhat greater value on preserving known-safe options
  and avoiding poorly understood risk.”

The Identity provenance is identical across conditions:
`experiment.identity-specification / identity-specification:initial`.

The strings `neutral`, `explorer`, `cautious`, `expected_choice`, and
`preferred_destination` are forbidden from the provider-visible surface.
Condition ids are report bookkeeping and are not rendered into cognition.

## Frozen candidate World

The preparation fixture is a deterministic Mineflayer observation only; it
does not launch Minecraft.

Common initial facts:

- health 20;
- food 20;
- oxygen 20;
- position (0, 64, 0);
- one nearby zombie at distance 4;
- no retained Memory.

The common controlled scenario exposes two equal-distance FLEE destinations.

`route-17`:

- ten blocks north;
- corridor and waypoint currently visible;
- no exposed resource block visible along the corridor.

`route-42`:

- ten blocks south;
- terrain beyond a bend is outside current observation;
- an exposed coal ore block is visible before the bend.

These are factual descriptions, not labels such as safe/explore/cautious or an
expected answer. Both remain admissible destination choices under the
experiment-local FLEE surface.

## Deterministic preparation invariants

The deterministic test surface must prove all of the following before any
scientific invocation:

1. A/B/C share the exact same `self_id`, Identity provenance, and common
   directive.
2. Only the declared additional value prior differs.
3. Actual llama.cpp user payloads contain no condition labels or expected answer.
4. All conditions reuse the same World observation/scenario object.
5. Available Skills are the same: `WAIT / EAT / FLEE`.
6. Cognition request instruction, request id, intent id, focus, choices,
   THINK permission, and soft budget are identical.
7. Primitive Action capabilities are identical.
8. Identity is only a cognition datum; it has no Action authorization field or
   direct Action path.
9. Removing the Identity datum makes all provider-visible requests identical,
   so the prior cannot rewrite World evidence.
10. Building requests leaves Persistent Cognition Memory empty.
11. Current mandatory hazard handling admits FLEE before the Identity prior is
    consulted.
12. Preparation output stores `condition_id` beside, not inside, the
    provider-visible request.

The dry-run is:

```bash
python experiments/identity_prior_trajectory.py
```

It emits a versioned preparation report and must report:

```json
{
  "scientific_result": null,
  "scientific_spend": {
    "model_calls": 0,
    "minecraft_sessions": 0
  }
}
```

## Report schema

Each condition record keeps the following fields separate:

- `condition_id` — evidence bookkeeping only;
- exact `identity_specification`;
- `provider_visible_request_sha256`;
- exact `provider_visible_request`;
- `present_facts`;
- `available_skills`;
- deterministic pre-cognition `selected_skill`;
- declared `cognition_path`;
- `provider_calls`;
- `input_tokens`, `output_tokens`, `latency_ns`;
- `bound_destination`;
- `issued_actions`;
- `world_consequences`;
- `durable_memory`;
- `later_present`;
- `later_decision`;
- `interpretation_class`.

Preparation leaves all scientific outcome fields empty/null. It does not invent
an A/B/C result.

## Future matched-spend protocol

Physical/model spend remains blocked while #201 is open or until its final
shared-`RelayEngine` diff has been reviewed against this apparatus.

The planned matched protocol is frozen before results:

- three matched blocks;
- three repetitions per condition;
- condition order:
  1. A -> B -> C
  2. B -> C -> A
  3. C -> A -> B
- no repetition count changes after observing outcomes;
- use the currently qualified llama.cpp/GGUF identity unless fresh post-#201
  review requires a deterministic compatibility repair:
  - llama.cpp revision `e2d2c0d6a`;
  - build `10874`;
  - GGUF SHA256
    `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`;
- preserve current adapter generation semantics:
  - temperature `0`;
  - `reasoning_effort=none`;
  - `cache_prompt=false`;
  - BOUNDED max output 48 tokens;
  - THINK max output 256 tokens;
- do not add a provider seed field that the qualified adapter does not
  currently send; any backend variation is observed rather than silently
  controlled through a new request semantic;
- reset every condition to the exact same declared World fixture before its
  first scientific invocation;
- reset Persistent Cognition to the condition's declared
  `IdentitySpecification` with zero Memory;
- retain an experience only through the existing explicit governed Memory
  integration seam after grounded success;
- one scientific invocation runs one condition from reset through first
  cognition/decision, grounded Action consequence, any predeclared explicit
  Memory integration, and one later decision;
- preserve operational/protocol failures as failures;
- no hidden retry, replay, alternate runtime, alternate condition, or same-run
  fixture tuning.

The live World-reset implementation must be bound to the then-current
#141-derived Minecraft apparatus after #201 review. This preparation document
does not authorize or perform that live transaction.

## Interpretation

The future report must use one of the Issue #220 classes without preference:

- **A — embodied prior effect**: cognition/parameter binding changes and reaches
  Action/consequence/later trajectory;
- **B — transient cognition-only effect**: cognition changes but embodied
  behavior does not;
- **C — presentation-only effect**: only language/presentation changes;
- **D — overconstrained / policy leakage**: the prior or fixture encoded the
  answer;
- **E — no discriminating effect**: matched conditions remain behaviorally
  indistinguishable.

A favorable class must not be engineered by changing the fixture after the
matched transaction starts.

## #201 concurrency gate

Before any model-backed or Minecraft-backed A/B/C transaction:

1. reacquire fresh `main`;
2. confirm #201 is terminally complete or explicitly terminated;
3. inspect the exact #201 merged diff and current `RelayEngine` /
   provider-visible request semantics;
4. compare those semantics with
   `experiments/identity_prior_trajectory.py`;
5. classify the review as `NO MATERIAL CONFLICT` or `MATERIAL CONFLICT`;
6. if material, make only the bounded deterministic compatibility repair and
   rerun deterministic CI before spend;
7. only then authorize the matched physical/model transaction.

No model or Minecraft scientific result is claimed by this apparatus PR.


## Post-#201 execution binding

The post-#201 materiality review recorded on Issue #220 classified the current
shared-core change as `NO MATERIAL CONFLICT`. The matched scientific
transaction may therefore proceed only through the canonical transaction
apparatus added after that review.

The execution apparatus adds no new semantic owner and does not change the
predeclared A/B/C priors, block ordering, repetitions, provider generation
semantics, or interpretation classes.

### Live-to-frozen World binding

The first provider-visible decision request remains the exact frozen local-frame
fixture prepared before spend. Live Minecraft is used to validate and realize
that fixture, rather than injecting per-run session identifiers or raw
provenance references into model-visible context.

For every scientific condition invocation:

1. one live Mineflayer session is started;
2. the player is restored to a shared anchor position/orientation;
3. health and food are restored, inventory/effects are cleared, server time is
   reset, and prior controlled zombies are removed;
4. one persistent `NoAI` zombie is summoned about four blocks away, keeping
   the ambiguity non-terminal and preventing combat damage from becoming an
   uncontrolled treatment;
5. fresh Mineflayer evidence must confirm the matched reset before a provider
   call is permitted;
6. the frozen local-frame request is sent through the existing
   `RelayEngine`;
7. the resolved route id, if any, is mapped to the corresponding live
   north/south destination and executed through the existing supervised FLEE
   Action path;
8. only observed successful progress may be explicitly integrated as Memory;
9. the Memory is save/load round-tripped through existing Persistent Cognition;
10. the grounded consequence is projected into the same local coordinate frame
    for the predeclared later decision.

An additional anchor-acquisition Mineflayer session occurs before the nine
condition invocations. It makes **zero provider calls**, establishes only the
shared live coordinate origin, is recorded separately, and is not assigned to
A/B/C. It is part of physical transaction setup and must be counted separately
from the nine matched condition sessions.

### Provider-visible blinding

The live transaction deliberately does not expose condition bookkeeping,
Mineflayer session ids, entity ids, raw run-specific request ids, or
expected-result labels to the first model decision. The local-frame request
preserves the predeclared semantic World content while raw live evidence and
its original provenance remain in the evidence report.

The later request may differ through two causal descendants of the first
embodied result:

- the grounded live position/consequence projected relative to the shared
  anchor;
- the explicitly retained Memory of the first successful FLEE destination.

Those later differences are intended trajectory evidence, not treatment
leakage.

### Qualification and stopping rule

The canonical launcher must fail before scientific spend unless all of the
following remain true on the exact execution subject:

- tracked checkout is clean;
- local HEAD equals current remote `main`;
- open PRs targeting `main` are zero;
- ruleset 23442682 remains active;
- #141 is closed;
- #201 is closed / completed;
- #220 remains open;
- #220 contains the post-#201 `NO MATERIAL CONFLICT` review;
- the pinned Minecraft, Mineflayer, Java, llama.cpp, and GGUF identities pass
  the existing #141 mechanical runtime preflight.

The canonical transaction is one-shot. Any operational, protocol, reset, or
grounding failure stops at the first concrete failure and preserves all prior
evidence. There is no hidden retry, replay, condition substitution, or same-run
fixture tuning.

The transaction report counts the anchor session, matched condition sessions,
and actual provider calls separately.
