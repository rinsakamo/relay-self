# #843 — ATTACK@1 through L0/Physical ActionPort, shared WAL (DEV)

Baseline: #847 HEAD `87d81cbf0fe9226641244a06bab0d6e7a972c161`,
`REAL_L0_EAT_PASS` in a controlled Minecraft/Gemma World. This new ATTACK
mode has **NOT** yet run in a real World.

## Reused owners and explicit opt-in

`run_cognitive_minimal_world.py --physical-attack-dev --l0-skill-ir-dev`
requires the same explicit real-World and real-LLM grants, **the same
Self-owned `--physical-journal-path`**, one-time create or exact restore,
two distinct caller-supplied unverified authority labels, and the opt-in
unauthenticated-principals acknowledgment as EAT. It additionally requires
`--pre-l1-native-probe --hazard-name zombie --fight-max-distance 2.8`
(or a stricter positive range). It cannot be combined with
`--physical-eat-dev`, `--execute-native` or
`--s49-readonly-shadow`. An unresolved journal is checked before World
launch/inference.

Actual numbered L1 selection of `ATTACK@1/entity:<id>` is not replaced or
re-targeted. Before Intent/Skill creation, the existing two-probe source
admission checks exactly one nontruncated same-session zombie with unchanged
entity ID and a stable body/target position, 0.1..2.8m range and positive
Health. CPU L0 interprets the minimal fixed **innate** ATTACK@1 Skill IR,
emits exactly one Action request, and uses the **same**
`propose_bound_physical_action` that EAT uses. No learned Skill is
accepted/registered here; no new Intent owner or physical scheduler.

## Shared WAL / native evidence

`PhysicalActionJournal` retains its v1 schema and exact EAT row validation.
A typed ATTACK row has its own extra target/hurt attribution fields.
The same `create/restore/require_clear`, on-disk CAS, OS lock, SHA256
envelope, tempfile fsync, atomic replace, directory fsync and restart STOP
protect both capabilities. `prepare_attack` persists
`PREPARED_UNRESOLVED` before ActionSupervisor.ISSUE or Mineflayer IO.

The existing `MineflayerProcessSession.send_attack_entity` performs
one `attack_entity` child command (`<parent>-attack`). Its applied ACK
alone does **not** demonstrate physical damage. The bounded DEV issuer
also requires the existing source-qualified `entity_hurt` native event:

- same session and exact selected entity ID;
- a nonnull `source_entity_id` equal to `actor_entity_id` (the
  Mineflayer bridge's currently operating Self entity ID);
- target != actor, monotonic seq after the pre-issue probe;
- one applied ACK and one uniquely attributed hurt, in either order;
- a later matching-request after-probe and existing ActionSupervisor OUTCOME.

Only these permit durable `NATIVE_ATTACK_HURT_OBSERVED` and L0
`ADVANCED → TERMINAL_CANDIDATE`. This is a **DEV native hurt event
attribution**, not a claim that Zombie Health decreased by any measured
amount, that the zombie died or that Paper independently attributed
damage. Mineflayer's optional `source_entity_id` may be null in a
real World. A missing/null/foreign source, lost ACK, readback disconnect,
or journal close failure retains `PREPARED_UNRESOLVED` and UNKNOWN/STOP.
No automatic attack retry or WAL reset, including across new Worlds.

The current grant dataclass keeps its original `PhysicalEatGrant` name
as a temporary DEV wrapper; its scoped validation is reused but there is
no authenticated operator authority or process-wide physical owner.

## Evidence/qualification

The CLI reports the selected Target, L1 choice, L0 instruction trace,
one Action parent, `attack_hurt_evidence` with native seq/source and
`independent_damage_attested=false`, one native ACK, WAL history and
a `skill_final_state=started` rather than declaring Skill/Intent success.
No semantic/learning success is recorded.

Offline tests use a scripted provider and typed Mineflayer session to
cover positive ACK+attributed hurt, before-first-native WAL reservation,
missing/moved/foreign target refusal, lost ACK/hurt, null/foreign source,
after-probe failure, restored unresolved STOP and conflicting modes.
#847 EAT test regressions remain required.

**Next real DEV gate:** audit actual target Entity ID mapping and optional
hurt source behavior under the real Minecraft 1.21.8/Mineflayer 4.39.0
server. If `source_entity_id` is null, STOP/UNKNOWN; never loosen
attribution just to obtain a PASS. A distinct Paper Health before/after
source/UUID/tick join is required for an independent measured damage claim.

**Classification:** OFFLINE_DEV_ONLY / REAL_L0_ATTACK_NOT_RUN /
QUAL_NO_GO / SCIENCE_NOT_RUN.
