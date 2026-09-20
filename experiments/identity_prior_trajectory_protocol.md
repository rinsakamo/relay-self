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
- food saturation 20 in the synthetic frozen preparation fixture;
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

These are experiment-authored semantic route descriptions, not labels such as
safe/explore/cautious or an expected answer. The current Mineflayer boundary
does not observe corridor geometry, bends, or coal blocks, and the live reset
does not construct those terrain facts. Both descriptions remain matched
provider-visible inputs and both route ids remain admissible under the
experiment-local FLEE surface, but they must not be reported as live Minecraft
terrain observations.

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
- preserve current adapter generation semantics for this experiment:
  - temperature `0`;
  - `reasoning_effort=none`;
  - `cache_prompt=false`;
  - BOUNDED max output 48 tokens;
  - THINK max output 256 tokens;
  - the optional Jev/System One BOUNDED endpoint added after apparatus
    preparation is **not configured by #220**; this transaction remains on the
    generated BOUNDED baseline unless a separately predeclared matched study
    changes that execution surface;
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

### Grounded two-phase World reset

Each fresh condition session first waits for its Mineflayer `spawn` observation
so the existing controlled-world command owner does not issue player-targeted
commands before the player is ready. It then performs exactly one reset sequence:

The controlled server itself disables natural monster, animal, and NPC
spawning and disables generated structures before the fresh flat World is
created. This keeps uncontrolled entities/structures from becoming an
order-dependent physical nuisance variable.

1. **Cleanup phase:** first freeze cleanup-side World generation/drop
   behavior with Minecraft 26.1's namespaced rules
   `minecraft:spawn_mobs=false`, `minecraft:mob_drops=false`, and
   `minecraft:entity_drops=false`. Then remove every non-player entity
   exactly once, clear effects/inventory and restore anchor/orientation. Each
   scientific invocation already uses a fresh opaque player identity, so the
   apparatus does not manufacture body state with restorative effects; instead
   the explicit reset probe must observe the fresh-player defaults
   `health=20`, `food=20`, and `food_saturation=5`. The overworld clock is
   first paused with `time of minecraft:overworld pause`, then set to the exact
   total tick `6000` while paused. The pause must precede the numeric set so the
   World Clock cannot advance between the exact set and a later pause command.
   Recurring time markers such as `noon` are not used because 26.1 advances
   them to their next occurrence. The drop rules are set before the kill so
   cleanup itself cannot create item/experience replacement entities from normal
   death/drop handling.
   After cleanup, issue two ordered server commands: first a
   conditional `DIRTY` marker that emits only if any non-player entity still
   exists, then an unconditional `BARRIER` marker. The transaction accepts
   server-side zero only when the post-offset server log reaches the BARRIER
   without containing DIRTY. This positively acknowledges command ordering while
   using the conditional marker only as fail evidence. After that server
   barrier, request an explicit target-local Mineflayer `observe` probe and
   require a current `probe` snapshot showing the common anchor/body state
   and no nearby entity within the adapter's fixed 16-block / 16-entity
   projection. The boundary rejects changed coverage bounds, so condition runs
   cannot silently narrow or widen the entity sensor scope. Reset qualification
   also requires the explicit
   Mineflayer probe to report `time_of_day=6000` and `day=0`, so command
   delivery alone cannot qualify the clock state.
2. **Fixture phase:** only after that two-source cleanup barrier is grounded,
   issue one summon command for
   exactly one static `NoAI`, persistent, silent, invulnerable zombie. Then
   issue a unique server-log marker after the summon command. Once that marker
   is observed after its captured log offset, request explicit Mineflayer
   probes until the bounded client projection shows exactly the one controlled
   zombie and no other nearby entity.

Ordinary Mineflayer `forcedMove` remains a valid target observation, but it is
not reset-qualification evidence. The reset no longer assumes that a specific
teleport must emit that event.

Fixed command settle intervals are execution aids only. Server-command delivery
itself is fail-closed and bounded: the FIFO is opened non-blocking, retryable
reader/backpressure errors are retried only until a fixed delivery deadline,
and each #220 reset command first verifies the owned Minecraft PID is still
alive. A dead server, missing FIFO reader, partial write, or delivery timeout
stops the transaction instead of blocking indefinitely. DIRTY/BARRIER markers
use the fresh Mineflayer session id and are matched only after a captured log
offset, so old log lines cannot satisfy a new barrier. Because the BARRIER
is unconditional, its absence is an acknowledgment failure rather than an
ambiguous statement about World state; a preceding DIRTY marker is explicit
server-side evidence that cleanup did not establish zero entities. Queued
ordinary Mineflayer events also cannot satisfy the client barrier: only
observations explicitly emitted in response to post-marker `observe` probes
qualify. Bounded repeated probes may
wait for client projection convergence, but the owner never repeats cleanup,
summon, a scientific condition, or a provider call.

A missing server marker, a DIRTY marker after the fixed drop-suppressed
cleanup, a post-marker probe that never reaches the declared cleanup state, or a
post-summon probe that never contains exactly the one controlled zombie is
`NOT QUALIFIED` and stops the invocation. The apparatus does not respond to
DIRTY by issuing another kill. Command evidence records gamerules, cleanup,
marker, and summon commands; the transaction report records the unique causal
markers and grounded probe snapshots.

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
semantic fixture prepared before spend. Live Minecraft validates only the
embodied reset/threat state that the current boundary can actually observe
(player state, controlled zombie presence/distance, and route movement
realization). It does **not** validate the experiment-authored corridor/bend/coal
route descriptions. Those descriptions remain fixed matched cognition inputs,
while the selected route id is realized as live north/south movement. This
avoids injecting per-run session identifiers or raw provenance references into
model-visible context without overstating terrain grounding.

For every scientific condition invocation:

1. one live Mineflayer session is started with a fresh opaque Minecraft player
   identity derived only from the predeclared absolute invocation ordinal, never
   from A/B/C or any semantic condition label;
2. that fresh player is restored to the shared anchor position/orientation;
3. the fresh player's health, food, and food saturation are observed at the
   matched defaults while inventory/effects are cleared, the exact server clock
   is fixed, and prior controlled entities are removed;
4. one persistent, silent, `NoAI`, invulnerable zombie is summoned about four
   blocks away, keeping the ambiguity non-terminal, preventing combat damage,
   and preventing daylight burn/death from becoming an uncontrolled
   time-dependent treatment;
5. fresh Mineflayer evidence must confirm the matched reset before a provider
   call is permitted;
6. the frozen local-frame request is sent through the existing
   `RelayEngine`;
7. the resolved route id, if any, is mapped to the corresponding live
   north/south destination and executed through the existing supervised FLEE
   Action path;
8. after forward progress is observed, controls are cleared and an explicit
   Mineflayer `probe` is required after the stop acknowledgment; only that
   post-stop probe may ground FLEE success and the terminal consequence;
9. only the post-stop grounded consequence may be explicitly integrated as
   Memory;
10. the Memory is save/load round-tripped through existing Persistent
    Cognition;
11. the grounded post-stop consequence is projected into the same local
    coordinate frame for the predeclared later decision.

An additional anchor-acquisition Mineflayer session occurs before the nine
condition invocations under its own distinct opaque Minecraft player identity.
It makes **zero provider calls**, establishes only the shared live coordinate
origin, is recorded separately, and is not assigned to A/B/C. Each of the nine
scientific invocations then uses a different player identity so server-side
player persistence cannot carry condition-to-condition state. These target
usernames remain evidence-only and are not projected into provider-visible
cognition. The anchor session is part of physical transaction setup and must be
counted separately from the nine matched condition sessions.

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

The durable Memory remains stored with its original live-world destination
coordinates and exact provenance. Only its transient provider projection is
converted into the same matched-local coordinate frame as the later Present and
route catalog. The model-visible wrapper preserves the source class and the
fixed integration provenance while replacing the run-specific Mineflayer
session/sequence reference with the constant semantic reference
`matched-first-grounded-consequence`. Exact durable provenance remains in the
evidence report and is not leaked into cognition as a treatment-irrelevant run
identifier.

Those later differences are intended trajectory evidence, not treatment
leakage.

### Claim boundary

A positive result on this apparatus supports only the bounded claim that an
Identity prior changed cognition and/or embodied route behavior **given the
fixed semantic route descriptions supplied by the experiment**, with the chosen
route realized through grounded Minecraft Action/consequence.

It does not by itself establish that RelaySelf perceived corridor visibility,
terrain beyond a bend, coal ore, or other block-level Minecraft facts. A claim
about Identity changing behavior from live terrain/resource perception requires
a later apparatus that constructs and observes those facts through the
environment boundary.

### Provider-free live apparatus smoke

Before an owner may publish a new
`QUALIFIED_FOR_NEW_TRANSACTION_SUBJECT` marker, the exact candidate HEAD/tree
must first pass the canonical provider-free smoke:

```bash
bash experiments/run_identity_prior_trajectory_apparatus_smoke.sh \
  --repo-root <fresh-exact-main-checkout> \
  --evidence-root <new-empty-evidence-root>
```

The smoke launches a fresh ephemeral Minecraft 26.1 server from the pinned
official `server.jar`, installs Mineflayer only from the tracked lock, and uses
two opaque non-scientific player identities: one anchor session and one reset
session. It does **not** start llama.cpp, load a GGUF, construct a provider, run
A/B/C, create Memory, or invoke the classifier.

PASS requires the real current reset implementation to reach, exactly once:

1. fresh anchor spawn;
2. server-side cleanup DIRTY/BARRIER proof;
3. explicit empty bounded Mineflayer probe with matched body/time state;
4. exactly one controlled zombie summon;
5. post-summon server barrier;
6. explicit exactly-one-zombie bounded Mineflayer probe;
7. no recognized Minecraft command-parser error in the reset log segment.

The smoke report records the local HEAD/tree and zero scientific/model spend.
A smoke result on a different HEAD/tree is stale. A failed smoke is apparatus
evidence only and must not be retried as though it were a scientific condition;
repair requires a new repository subject and a fresh smoke transaction.

### Qualification and stopping rule

The canonical launcher must fail before scientific spend unless all of the
following remain true on the exact execution subject:

- tracked checkout is clean;
- local HEAD equals current remote `main`;
- open PRs targeting `main` are zero;
- ruleset 23442682 remains active and still targets exactly the default
  branch with no bypass actor/current-user bypass, deletion and non-fast-forward
  protection, required linear history, squash-only pull requests, required
  review-thread resolution, and exactly the required status checks
  `repository-contracts`, `pytest`, and `lint`;
- #141 is closed;
- #201 is closed / completed;
- #220 remains open;
- the exact HEAD/tree has a fresh provider-free
  `APPARATUS_SMOKE_PASS` read-back from the canonical smoke above before the
  trusted owner publishes a new qualification marker;
- the **latest trusted-owner** machine-readable #220 execution
  qualification is `QUALIFIED_FOR_NEW_TRANSACTION_SUBJECT`; comments from
  other GitHub users or non-`OWNER` associations are not execution authority;
- that qualification contains exactly one `subject_head` and one
  `subject_tree` line and binds the exact current local/remote HEAD and tree;
- a later `NOT_REQUALIFIED`, missing marker, or stale subject binding fails
  closed even if an older `NO MATERIAL CONFLICT` comment exists;
- the adapter's tracked `package-lock.json` is part of the exact execution
  subject and pins the Mineflayer transitive dependency graph; the launcher
  requires that tracked lock, installs only with `npm ci`, verifies the lock
  was not changed by installation, and records both its hash/copy and the
  resolved dependency tree as evidence;
- the pinned Minecraft, Mineflayer, Java, llama.cpp, and GGUF identities pass
  the existing #141 mechanical runtime preflight; the fresh Minecraft server
  root is constructed from the pinned official `server.jar` plus generated
  experiment configuration only, and does not import mutable external
  `libraries/` or `versions/` runtime directories;
- after runtime preflight, the launcher reacquires this authority immediately
  before `--phase run`;
- the run phase receives the exact PID of the Minecraft server started by the
  canonical launcher and verifies that positive PID is still alive immediately
  before the scientific transaction begins.

The canonical transaction is one-shot. Any operational, protocol, reset, or
grounding failure stops at the first concrete failure and preserves all prior
evidence. There is no hidden retry, replay, condition substitution, or same-run
fixture tuning.

Scientific evidence is checkpointed after each completed cognition result,
before any subsequent grounded Action can fail. A terminal failure report
reconstructs conservative evidence-backed lower bounds for already-recorded
provider calls and Mineflayer sessions from those durable checkpoints/evidence
files. Both provider calls and session counts are explicitly labeled as lower
bounds: an external provider or child process can consume/start before a usable
result or recorded session file exists. Completed transactions continue to
report exact counts from the completed records.

The classifier accepts a resolved embodied outcome only when the recorded Skill
execution is explicitly `SUCCEEDED`; a non-null or malformed Skill-run payload
is not sufficient grounding evidence.

The completed transaction report counts the anchor session, matched condition
sessions, and actual provider calls separately.


### Pre-spend interpretation audit

Before the first scientific invocation, the automatic classifier is deliberately
conservative about repetition noise.

- class A requires a condition-linked behavioral difference that is stable
  within each condition across the three predeclared repetitions at at least
  one measured decision stage; an unresolved/no-Action outcome may differ from
  a grounded Action outcome, but it is never treated as a destination;
- class B is used only when cognition-path signatures differ reproducibly while
  both first and later behavioral outcomes are themselves stable and identical
  across conditions;
- initial and later cognition signatures are evaluated separately so a later
  cognition-only effect is not silently collapsed into the Grand Null;
- within-condition behavioral variability is retained as variability and does
  not become class A or B merely because two raw condition vectors differ;
- class E therefore means **no reproducible discriminating effect** on this
  bounded surface, not that every raw invocation must be byte-for-byte
  identical;
- class C is not directly observable on this bounded non-presentational FLEE
  gate and is reported as such rather than inferred from internal rationale
  text;
- class D is a pre-spend invalidation class for policy/label leakage. The
  canonical transaction fails closed before scientific execution if its
  deterministic anti-leakage requirements do not hold, rather than counting a
  leaked run as SOUL evidence.

The canonical launcher is syntax-checked by deterministic pytest using
`bash -n`.
