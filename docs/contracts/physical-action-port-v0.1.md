# Physical ActionPort v0.1 — minimal cognitive/physical boundary (DEV)

Parent: [#828](https://github.com/rinsakamo/relay-self/issues/828),
[#829](https://github.com/rinsakamo/relay-self/issues/829),
[#843](https://github.com/rinsakamo/relay-self/issues/843).
Development branch: [Draft #844](https://github.com/rinsakamo/relay-self/pull/844).

**Status: OFFLINE DEV EAT ISSUER + FSYNC/CAS JOURNAL + ONE-SHOT CLI COMPOSITION TESTED / REAL PHYSICAL ACTION NOT RUN / OPERATOR AUTHENTICATION OPEN / QUAL_NO_GO / SCIENCE_NOT_RUN.**

## 2026-11-14 update — EAT physical DEV issuer and durable journal (OFFLINE ONLY)

The original nonissuing `PROPOSED` seam remains unchanged. Added
`src/relay_self/physical_action_journal.py` and
`experiments/cognitive_physical_eat_issue_dev.py` as a *separate
DEV-only candidate for one physical EAT parent Action*. This uses only
existing `ActionLifecycle`, `ActionSupervisor`, `IntentCommitment`,
`SkillExecution`, and the Mineflayer process-session/typed result
contracts; **no `NormalSessionActionExecutor`, old S49 L0, S51
`EatCursor` or autonomous priority policy is imported**.

The journal adapts #767's C1/S49 mechanism: regular non-symlink
preexisting directory, OS file lock, immutable SHA256-checked JSON
envelope, on-disk CAS, temp-file fsync + atomic rename + parent-directory
fsync. `create` will not reset an existing journal; `restore`
validates the exact owning Self. `prepare_eat` persists
`PREPARED_UNRESOLVED` scoped to Self/World session, Intent,
SkillExecution, Action ID, selected item, native request ID/seq/source
**before** supervisor ISSUE or any native IO. No automatic recovery,
repair, deletion or retry of an unresolved entry. A disk/CAS failure
blocks issuance. Full replay/tamper-resistance against a malicious
privileged host is **not** claimed by an unkeyed checksum.

The opt-in DEV `issue_selected_eat_dev` checks the already-selected
`EAT@1/inventory:<item>`, started Skill/committed Intent, two fresh
different correlated native probes, same food slot and stationary
viable WorldBody with no observed nearby entities, exact existing
Action proposal identity, no in-flight/supervised prior Action, plus
two separately scoped, caller-provided PROPOSE/ISSUE grant objects.
The grant objects are **not independently authenticated**, so an
explicit `grant_real_world=True` and
`acknowledge_dev_unverified_principal=True` are additionally
required even to invoke this non-CLI experimental entrypoint. No
operator grant can originate from mere Schema/LLM preference.

One supervised EAT **parent Action** uses two distinct native child
command IDs, `<action>-equip` and `<action>-consume`. The existing
Mineflayer bridge rejects reused child IDs. The resulting native ACKs
must match exact action/effect/World and be chronologically followed by
a newly correlated probe showing **food increase and selected item
quantity decrease**. Missing, foreign, rejected or interrupted IO is
`ActionState.UNKNOWN` plus persistent `PREPARED_UNRESOLVED`,
not an Action retry or successful food experience. A journal close
fsync/CAS failure after observed native success *also* leaves the
physical journal unresolved, even if in-memory ActionSupervisor holds
OUTCOME. This candidate is **one bounded EAT parent transaction**,
not yet a general Skill IR/primitive scheduler.

New `tests/test_cognitive_physical_eat_issue_dev.py` uses a scripted,
typed MineflayerProcessSession subclass. Positive: distinct equip/
consume and after probe, exact native food/slot consequence, fsynced
terminal close; negatives: no grants, altered target, stale session,
wrong Action identity, lost/rejected ACK, no nutritional readback,
journal disk failure before issue or after physical result, restart
STOP, foreign Self, CAS stale owner, tampered checksum, symlinks and
double-issue. These tests **do not run a Minecraft World** and do not
authenticate the grant principal.

The **existing runner remains read-only by default**. Only an explicit
`--physical-eat-dev` option enters the new EAT issuer. Its legacy
`--execute-native` path is NOT THIS new issuer and is mutually exclusive
within the CLI, but **external issuer processes must still be excluded**.
Do not enable two physical issuers on the same Self session, do not interpret
`PhysicalEatDevReceipt` as independent S49 QUAL, and do not run this
new issuer in a real World until one canonical runtime owner/CLI
switch with independent operator admission and negative restart
verification exists. A genuine Minecraft/Gemma Action/Outcome has
**NOT** yet been observed through this new journal.

## 2026-11-14 — one-shot EAT runner wiring (DEV, LIVE NOT YET RUN)

`experiments/cognitive_physical_eat_runner.py` now bridges the existing
real-native + Gemma `WorldStepReceipt` to the same Physical ActionPort
without selecting another Goal, Skill or food. A **new explicit**
`--physical-eat-dev` mode in
`experiments/run_cognitive_minimal_world.py` (mutually exclusive with
legacy `--execute-native` and shadow-only
`--s49-readonly-shadow`) performs:

1. Load a journal *before Mineflayer launch/Gemma inference*: restore an
   existing self-owned file, or explicitly `--physical-create-journal`
   **only for an absent file**. Pending `PREPARED_UNRESOLVED` means
   **STOP/UNKNOWN before connecting to the World**, not recreation.
   Use one journal file per Self across World sessions, and do not share
   with other CLI processes that bypass the new port.
2. Spawn, optional post-spawn test server setup, exact pre-L1 native
   probe, CPU Schema and real L1 number choice. Require a current
   **two-probe** read-only EAT witness; if absent, preserve
   `ESCALATE_L2/REJECTED` with **no** WAL reservation/Action.
   This reuses the prior read-only S49-*shaped* witness as
   observational evidence, not the original S49 decision owner.
3. Commit the selected Intent and start only the matching EAT Skill,
   create the existing `ActionLifecycle.PROPOSED` through the new
   Physical ActionPort, then the one EAT DEV issuer persists a
   fsynced `PREPARED_UNRESOLVED` reservation **before** issuing any
   Mineflayer command. Distinct native equip/consume ACKs and
   correlated nutrition/inventory effects seal the journal.
4. Save positive/failure JSON with exact model selection, native
   probe ID/seq, original Self/World/source, journal status/history,
   parent Action and child effect IDs, plus whether the observed
   outcome was attested. Even an in-memory OUTCOME with **failed WAL
   close** remains persistent STOP/UNKNOWN. The new issuer uses logical
   ActionLifecycle clocks; **do not report those as measured
   Intent-to-Action nanosecond latency**.
5. Exit and clean up *only processes owned by this test*. Nothing
   issues automatically without every required explicit DEV CLI flag.

Required flags include: `--grant-real-world --grant-real-llm`,
`--physical-eat-dev --physical-journal-path PATH`,
`--acknowledge-physical-dev-unverified-grants`,
`--physical-propose-authority LABEL_A` and
`--physical-issue-authority LABEL_B` (distinct, but **labels are not
independent authentication**); use `--physical-create-journal` only
when the path has never existed. `--pre-l1-native-probe` and the
optional `--pre-l1-wait-s 30` support an **isolated, explicitly
controlled** test World with server-side hunger and bread setup.
**Do not** pass `--execute-native`,
`--acknowledge-unfenced-dev`, or `--s49-readonly-shadow` with
`--physical-eat-dev`.

At this stage the default runner remains read-only. The experimental
old unfenced issuer code is still present for earlier regression
tests; this CLI refuses **simultaneous** old/new modes, but cannot
guarantee external processes are not invoking unrelated issuers.
LocalCodex/operator must verify exclusive ownership of the isolated
World and native bridge. Independent principal authentication, a
multi-process global ActionPort arbiter, and physical qualification
remain OPEN.

`tests/test_cognitive_minimal_world_cli.py` now composes a real-shaped
typed Mineflayer stream into L1 EAT, two probes, one new parent EAT,
persisted WAL-before-first-command, two child ACKs, post-EAT native
food/inventory readback, and success. Negative cases: no Target,
stale bread/slot, lost equip/consume/after-probe ACK, persisted
UNKNOWN blocking a fresh *process* **before World launch**, missing
journal refusing reset, and old/new physical flags rejected. All
are **scripted native/provider tests**, not live Minecraft results.

## Decision: S49 is a reference implementation, not a runtime block

The previous proposal to bring the complete original S49
`NormalSessionActionExecutor` into Cognitive v0.1 is withdrawn. Code
review of original [#767](https://github.com/rinsakamo/relay-self/pull/767)
HEAD `efb6d14dfe9f2194273c7e0e9398a4fc0ad69ffe` shows it includes
old goal/intent-epoch handling, `NormalWorldL0`, `NormalFoodL0`,
World-specific MOVE selection, Stage R/T rehearsal/learning paths,
physical admission, Action execution and durable journal integration.
Importing that whole runtime would duplicate the new Schema/L0/L1/
Intent/Skill responsibilities. This is an **architecture replacement**,
not a claim that S49's physical constraints may be relaxed.

The new split is:

```text
WorldBody facts -> CPU Schema / Need / Goal -> L0/L1/L2
                  -> Self-owned Intent -> Skill interpreter
                  -> selected primitive Action + exact Target binding
                  -> Physical ActionPort [no selection]
                       - current Intent/Skill/Target/World/Capability
                       - physical channel conflict, owner currentness
                       - pre-ISSUE durable ledger + native session fences
                       - exactly one physical issuer -> native ACK/Outcome
                  -> qualified observation -> experience/learning
```

S49's **decision maker / food priority / old L0** is not imported.
Retain or extract proven physical constraints from existing assets:
`ActionLifecycle`, `ActionSupervisor`, native request ID/source
correlation, the ATTACK/EAT native effect verification, and the
fsynced, CAS-protected, fail-closed non-motion journal in
`src/relay_self/s49_nonmotion_physical_fence.py` from #767. MOVE
quiescence/settling remains unresolved where physical behavior depends
on it. The physical boundary never chooses a substitute target/food or
installs a learned Skill.

## Implemented first cut: one real existing Action PROPOSED, no issuer

`src/relay_self/physical_action_port.py` contains:

- `PhysicalActionBinding`: exact Self/World scope, current Intent/Goal,
  started Skill and version, requested primitive capability and version,
  body channel, immutable selected Target, native seq/request ID/source,
  and proposed Action ID.
- `PhysicalCapability`: *referenced* existing WorldBody capability
  and channel availability, **not** an authorization or an invitation
  to invent a primitive. The Skill interpreter/body catalogue must
  establish that the primitive belongs to this Skill.
- `PhysicalReadback`: matching source-qualified native Target projection;
  gateway must independently authenticate the bytes/source. An
  arbitrarily constructed typed snapshot is not evidence of World truth.
- `propose_bound_physical_action()`: validates exact source/currentness,
  matching Skill/Intent/Goal, no pending reconsideration, supported
  capability, target presence and body viability, no supervised duplicate
  Action ID, and **global body exclusivity while any Action is issued**.
  Until channel arbitration is proven, the conservative global lock
  is intentional. Calls existing `ActionLifecycle.propose`, **never**
  `authorize`, `ActionSupervisor.issue`, Mineflayer, disk, or another
  Intent owner. Returns `PROPOSED_NOT_AUTHORIZED` and explicit
  `physical_authorized=False`, `physical_issued=False`,
  `preissue_persisted=False`.
- The PROPOSED lifecycle is a transient, in-memory candidate. It is
  *not* a durable reservation, capability grant or physical safety
  conclusion. There is no method to issue through this port yet.

`experiments/cognitive_physical_action_preflight.py` is a **DEV-only
compatibility adapter**. It reruns the existing #844 read-only two-probe
selected Goal/Skill/Target check (formerly named S49 shadow) and maps
the witness to the new generic Physical ActionPort **without importing
the old S49 runtime**. It requires an already-committed existing Intent
and an already-started matching SkillExecution; the adapter itself
commits neither. The caller must supply the selected trusted primitive
capability. It yields a normal `ActionLifecycle.PROPOSED` and no
Action issue. Later this compatibility adapter can be replaced with
the regular native/Skill interpreter bridge without changing the
core Physical ActionPort contract.

**EAT is not a single primitive**: its verified native workflow contains
at least `equip_item` and `consume_held` with separate receipts.
A proposed primitive `equip_item` is not an EAT outcome. The narrow
DEV issuer now treats `EAT@1` as one supervised parent Action enclosing
two distinct Mineflayer child effects; this is a specific Body adapter
mapping, not a general L0 Skill interpreter, target chooser or proof
of Minecraft success. The eventual general interpreter must preserve
these primitive-level distinctions and branch/UNKNOWN semantics.

## Requirements still OPEN before canonical live Physical ActionPort readiness

1. **Authoritative issuer / runtime ownership.** A **narrow EAT DEV issuer
   candidate exists** and checks native session, selected Target,
   Intent/Skill, explicit grants and a durable file, but is not attached
   to the canonical runner or a trustworthy operator/principal source.
   Select exactly one active physical owner and retire/disable the
   legacy `--execute-native --acknowledge-unfenced-dev` branch before
   enabling a new real-World issuance flow. Do not treat two caller-
   constructed grant objects as independent authenticated operators.
2. **Durable reservation before external side effects.** The new
   `PhysicalActionJournal` adapts #767's fsync/CAS approach for
   one EAT transaction; its offline tests prove ordering and fail-
   closed restore for scripted sources. It is **not** the original
   S49 journal transplanted verbatim, is not yet a universal primitive
   log, and needs canonical real-world ownership, crash/restart and
   multi-session migration validation. A prior
   `PREPARED_UNRESOLVED` remains **STOP/UNKNOWN**, never retry.
3. **Native consequence.** The scripted EAT candidate now requires
   exact applied equip/consume child receipts and later source-
   correlated food increase plus selected item count decrease;
   missing ACK, ambiguity or disconnect leaves persistent UNKNOWN.
   This has **not been measured on the real Minecraft server** through
   the new path. ATTACK/MOVE/REST ports and any cross-Action arbitration
   remain separate. `Action OUTCOME` is not automatically `Skill success`
   or learned benefit; ATTACK ACK is not proof of zombie death.
4. **Body channel arbiter and movement STOP.** Current v0.1 proposal
   blocks on *any* supervised issued Action. Channel-aware concurrent
   issue is future work. STOP input-clear ACK, settling, physical
   quiescence and near-target motion must be qualified by native
   WorldBody; two correlated requests need not be different World
   physics ticks. FAST L0 deadlines cannot silently bypass
   durability or owner consistency.
5. **Skill interpreter capability provenance.** The new Skill
   interpreter must bind each finite primitive Action to a real
   versioned WorldBody capability and retain same selected Target,
   rather than trusting LLM text or transplanting the old S51
   food-selection priority into CPU Schema. If a food changed,
   report REFUSE/RECONSIDER; never retarget.
6. **Real DEV / QUAL separately.** The core proposal is nonissuing.
   The new standalone DEV EAT issuer *can* send a native command if
   separately invoked with grants and session, but is **not** wired
   to the normal real-World runner and has not run live. First
   reconcile the exclusive owner/explicit grant entrypoint, then
   repeat the isolated Minecraft 1.21.8 controlled EAT with evidence
   and safe cleanup. Physical QUAL and SCIENCE remain separate.

## Offline contract probes

`tests/test_physical_action_port.py` verifies a valid already-owned
Intent/Skill/Target becomes one PROPOSED lifecycle while supervisor
history stays unchanged; negative checks include foreign Self/session,
wrong Goal/Skill, stale request/source/seq, changed Target, unavailable
capability, body refusal, pending Intent reconsideration, stale/
terminal Skill, already-issued Action, duplicate completed ID and
invalid time/data. `tests/test_cognitive_physical_action_preflight.py`
checks a generated CPU Schema/L1 synthetic EAT/ATTACK selection and
existing two-probe witness bridge to **PROPOSED only**, with changed
food/slot/session/ref negatives.

These fake-source tests are not new real Gemma/Minecraft results. The
last **real** controlled World observation belongs to #844's prior
read-only EAT handoff, where physical Action/Outcome counts were zero.
