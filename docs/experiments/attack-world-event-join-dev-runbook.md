# P0-B #855 — ATTACK WAL × independent World damage / death event (DEV)

Parent #851, existing physical ATTACK #843/#848/#849, semantic evaluation
#850, file checkpoint P0-A #853/#854.

The join is read-only. The original #856 real-run Paper recorder and
native probe witness were observation-only and did not include a ticket.
The new #857 ticket observer is still not a physical Action issuer.
Their existence alone is not real World evidence.

The Paper recorder in `experiments/p0b_paper_recorder` logs damage at MONITOR
and a separately sampled next-tick Health. A missing/dead entity yields
UNKNOWN, not calculated Health. Death linkage is UNKNOWN. World UUID is
server-derived; a branch identifier must be supplied separately by the
isolated-world operator. Before the existing ATTACK issuer, setting both
`RELAY_P0B_IDENTITY_WITNESS_PATH` and `RELAY_P0B_EXPECTED_IDENTITY_PATH`
requires the exact current probe's target and actor UUIDs to match the
independently recorded server identities. These paths must designate new
evidence files; neither establishes source authentication or a ticket.

## Provenance and grades

Existing physical ATTACK ends with a genuine Mineflayer
NATIVE_ATTACK_HURT_OBSERVED canonical WAL. That result has a native
Action ID, session, target runtime Entity ID, source-attributed hurt
and ACK, but does NOT independently establish server-side damage,
victim UUID, zombie death or the exact World cause.

New module: src/relay_self/attack_world_join_dev.py.
It joins four separately supplied evidence classes:

1. AttackWalEvidence, read only from an existing restored
   PhysicalActionJournal by attack_from_restored_wal. No WAL schema
   mutation, clearing, second physical owner or Action replay.
2. NativeIdentityWitness: both actor and target runtime Entity ID
   mapped to canonical UUIDs within the original native session.
   Never carry integer entity IDs across restarts.
3. ServerDamageEvent: server World/branch/tick, independently observed
   attacker and victim UUID, ENTITY_ATTACK cause, Health before/after,
   server event ID/source. Server Health delta alone is not sufficient
   if actor or cause is unknown.
4. Optional ServerAttackTicket: a one-use server ACK registered BEFORE
   native issue, binding world/branch/parent Action ID/native session,
   actor UUID and victim UUID to an unguessable nonce. The subsequent
   actual damage event must consume that nonce. **Current vanilla
   server and Mineflayer runner do not create these tickets.** Do not
   create such a ticket post-facto from a native result/World log.
   ServerDeathEvent must directly reference the matching damage-event
   ID and killer/target UUID, with Health reaching zero.

Offline verdicts:

| Status | Meaning |
|---|---|
| HOLD_UNKNOWN | Missing or conflicting native/WAL/server identity/effect |
| DEV_SERVER_DAMAGE_UNJOINED | Independent server hit matches UUID+actor; no Action ticket so not a claim about that particular L0 Action |
| DEV_ACTION_DAMAGE_CORRELATED | Source-compatible one-use server ticket and damage event, DEV only |
| DEV_ACTION_DEATH_CORRELATED | Same ticketed damage event is linked to a server death, DEV only |

Every verdict reports action_issue_authorized=false and
exact_causality_attested=false. Typed source references are *claims
from the supplied records*, not independently authenticated sources.
No outcome automatically upgrades #851 checkpoint atomicity.

## LocalCodex isolated real Minecraft 1.21.8 DEV plan

1. Read repo/Issues #851 #855 and PRs #848 #849 #850 #854 and actual
   issue_selected_attack_dev, PhysicalActionJournal, adapter and
   run_cognitive_minimal_world --help. Use isolated worktree and unique
   World, native Self session, WAL and evidence directory. No old WAL
   clearing or retry after PREPARED_UNRESOLVED.
2. Record the REAL server build, mode and difficulty, target Zombie UUID
   and Health, attacker Player UUID and a same-session Mineflayer
   runtime ID↔UUID mapping for both. The source of all facts matters.
3. If using vanilla, record scoped before/after server Health and native
   hit as separate evidence, but report Health-only / actor-cause
   NOT_ATTESTED if no server damage event hook exists. For a dedicated
   Paper 1.21.x DEV world, a small passive EntityDamageByEntityEvent
   observer can record server actor UUID, Zombie UUID, cause, tick,
   Health reduction and World+branch. Record plugin build and logs.
4. Execute ATTACK only via the existing selected L1 → L0 →
   PhysicalActionPort and canonical Self WAL. Preserve original
   PREPARED/terminal ACK/hurt evidence. No direct /kill or extra
   scripted damage to fabricate a success.
5. Without a pre-issued server-ACKed Action ticket, classify a matched
   server actor/target Health reduction as
   DEV_SERVER_DAMAGE_UNJOINED (still valuable DEV evidence).
   Do not infer a specific Action caused a hit just by nearby time.
6. For real Action-level correlation, implement a strictly
   observational one-shot *server* ticket registration on the
   existing physical path before native issue; bind unique nonce,
   World branch, selected Action ID, native session, actor UUID and
   target UUID. It must not trigger attacks or change the physical
   owner. The server records ACK before the Action and attaches/consumes
   nonce in an actual combat damage event. This bridge is NOT yet wired.
7. Zombie death is a separate claim: preserve an independent server
   death event explicitly linked to the damaging event, not just
   disappearing Entity or 0 Health readback. Multiple attempts
   must use separately granted physical Actions and WAL records.
8. Construct a JSON join input from independently preserved native,
   restored physical WAL and server event records. The auditor:
   
       python -m experiments.audit_attack_world_join_dev \
         --wal /ABS/unique-self-owned-wal.json \
         --join-record-json /ABS/join-record.json

   Never create synthetic ticket ACKs to achieve the positive status.
   The audit itself cannot authenticate producers; preserve raw files
   and SHA256SUMS and distinguish MOCK and WORLD sources.
9. Negative controls: other attacker, wrong victim UUID, runtime ID
   reused after restore, wrong native session, FALL damage, duplicate
   ticketed damage, stale/future server branch, WAL unresolved, death
   without explicit linked damage. Faults only on copies.

## JSON shape

Input JSON must contain exactly:
self_id, action_id, world_id, branch_id, native_identity,
server_attack_ticket, server_damage_events, server_death_events.

NativeIdentityWitness fields:
self_id, action_id, session_id, source_ref, probe_seq,
runtime_target_entity_id, runtime_actor_entity_id, target_uuid, actor_uuid.

ServerAttackTicket fields:
world_id, branch_id, action_id, native_session_id, nonce, actor_uuid,
target_uuid, registered_at_tick, server_ack_ref.

ServerDamageEvent fields:
world_id, branch_id, event_id, tick, victim_uuid, attacker_uuid,
damage_cause, health_before, health_after, server_source_ref, ticket_nonce.

ServerDeathEvent fields:
world_id, branch_id, event_id, tick, victim_uuid, killer_uuid,
causing_damage_event_id, server_source_ref.

native_identity and server_attack_ticket may be null. Both server event
lists may be empty. For a missing record use explicit unknown (no
fabricated values); the auditor will refuse or HOLD appropriately.

## Acceptance and nonclaims

- OFFLINE_ATTACK_WORLD_JOIN_DEV_PASS: all code/negative tests and exact
  HEAD CI green.
- REAL_SERVER_DAMAGE_OBSERVED_DEV_PASS: independent server event with
  UUID and Health delta actually collected.
- REAL_ACTION_DAMAGE_JOIN_DEV_PASS: ticket ACK was registered before
  issue and consumed by the server's real damage event.
- REAL_ACTION_ZOMBIE_DEATH_JOIN_DEV_PASS: also explicitly linked
  server death event.

A successful hit is NOT an automatic zombie kill; the current Minecraft
vanilla runtime is not a Paper server. Maintain QUAL_NO_GO /
SCIENCE_NOT_RUN, and separate this from multi-Self reconstruction.
Report exact HEAD/CI, provenance, event/source IDs, WAL digest, negative
cases, evidence SHA256, what is still NOT_ATTESTED and GitHub report
readback to #855 / #851 / PR.
