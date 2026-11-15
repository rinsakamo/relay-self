# P0-B #855 — Paper one-shot observation ticket + one-hit death DEV

Parent Issue #855/#851; stacked on PR #856. **OFFLINE DEV until actual
Paper/Mineflayer real World trial; do not claim a real damage/death join yet.**

## What changed

The existing experiments/p0b_paper_recorder Java 21 Paper 1.21.8 plugin
now creates its data-folder requests/, acks/, and handled/ directories.
Every tick it consumes a fresh UUID-named request file containing a
single DEV observational ticket with fields nonce, world_id,
branch_id, action_id (the existing parent L0 Action ID),
native_session_id, actor_uuid and target_uuid. Input must identify one
online Player and one Zombie in the same genuine Paper World UUID.
After validation the server records P0B_TICKET_ACK and writes a
separate ACK file (includes registered_at_tick and server_ack_ref).
The original request is moved to handled/ and retained.

Each ticket lives for at most 80 server ticks and is consumed only once
by a non-cancelled, matching ENTITY_ATTACK event. P0B_DAMAGE includes
actual attacker UUID, victim UUID, server tick, event ID and consumed
ticket_nonce (or NONE). P0B_TICKET_CONSUMED is logged separately.
P0B_AFTER records next-tick Health, not predicted Health.
P0B_DEATH records killer UUID, server-side Health and damage_link only
when the matching recorded damage and death had the same attacker,
target and tick. If the link cannot be established, write UNKNOWN;
do not infer kill from a vanished Zombie.

The observer DOES NOT issue ATTACK, select an Intent/Skill, mutate WAL
or grant physical permission. Branch labels are external DEV claims.

## Explicit opt-in on existing selected L1/L0 ATTACK runner

Set all variables for the isolated LocalCodex trial:

    RELAY_P0B_IDENTITY_WITNESS_PATH=/ABS/native-identity.jsonl
    RELAY_P0B_EXPECTED_IDENTITY_PATH=/ABS/server-expected-identity.json
    RELAY_P0B_TICKET_REQUEST_DIR=/ABS/paper/plugins/P0BRecorder/requests
    RELAY_P0B_TICKET_ACK_DIR=/ABS/paper/plugins/P0BRecorder/acks
    RELAY_P0B_TICKET_WORLD_ID=ACTUAL_PAPER_WORLD_UUID
    RELAY_P0B_TICKET_BRANCH_ID=EXTERNAL_DEV_BRANCH
    RELAY_P0B_TICKET_EVIDENCE_PATH=/ABS/unused/ticket-ack.json

The existing issue_attack_from_selected_l1_dev path requires
the UUID identity witness first. After proposing the real L0 Action
ID and before physical issue/WAL PREPARED, it creates an exclusive
nonce request, awaits an actual separate Paper ACK (3-second timeout),
and writes that ACK as new evidence. If missing/foreign, it fails
closed BEFORE native ATTACK. No retry after any unresolved
physical effect. Without the variables old non-ticket mode is
unchanged.

The raw server ACK and handled request, Paper log, original
Mineflayer stream and physical WAL MUST all be retained separately.
Do NOT fabricate a ticket after the attack. The existing
experiments/audit_attack_world_join_dev.py consumes the real
restored WAL and separately derived record JSON. A real ticket is
server-ACKed before issue and consumed in the actual server damage
record; mere matching clock times remain DEV_SERVER_DAMAGE_UNJOINED.

## LocalCodex controlled real World sequence

1. Read repo, Issue #855, PR #856, original physical
   ActionPort/WAL and this exact PR HEAD. Build the
   experiments/p0b_paper_recorder module with Java 21 and
   Maven. Use fresh isolated 1.21.8 Paper server, normal
   difficulty, one actor and a nearby Zombie. New Self,
   Intent, native session and WAL per trial. No old Worlds.
2. Trial A: start Zombie at Health 20. Read actor and Zombie
   UUID from independent Paper record and fresh Mineflayer
   Entity ID/UUID mapping. Execute ONE existing L1-selected
   WAL-owned ATTACK with server ticket opt-in. Verify ACK
   preceded attack, then exactly one P0B_TICKET_CONSUMED,
   native ACK+hurt, WAL terminal, P0B_DAMAGE and actual
   P0B_AFTER Health decrease. Feed original sources to
   the read-only audit. If they match, classify
   DEV_ACTION_DAMAGE_CORRELATED for this DEV trial only.
3. Trial B: use ANOTHER fresh World/Self/session/WAL.
   Set a single Zombie Health to a known *low positive*
   initial condition (for example 2.0) and independently
   read it back BEFORE the ATTACK. Execute one selected
   ATTACK through the same owner/WAL path with a NEW ticket.
   Observe actual Paper death, actual Health, victim/killer
   UUID and damage_link to the exact P0B_DAMAGE event ID.
   Only then evaluate DEV_ACTION_DEATH_CORRELATED.
   If Paper event ordering prevents an explicit link,
   mark death attribution NOT_ATTESTED, not guessed.
4. Failure cases: missing ticket ACK before ATTACK must
   leave no physical issue; wrong UUID, foreign native
   session, another actor, cancelled/FALL damage, duplicate
   consumptions and missing server death link must
   not become Action death claims. Inject faults only in
   copied evidence/fresh disposable Worlds.
5. Optionally restart World and native session; verify
   stale numeric Entity IDs cannot be reused without
   renewed UUID mapping. Never restart an old unresolved
   WAL to issue the same Action.
6. Preserve raw Paper log, request/ACK files, native source
   seq, canonical physical WAL digest, results, SHA256SUMS,
   plugin jar/build and exact code HEAD. Report to PR #856,
   Issue #855 and parent #851 with comment readback.

## Boundaries / success classification

OFFLINE_P0B_TICKET_DEV_PASS applies only if offline code/CI passes.
REAL_ACTION_DAMAGE_JOIN_DEV_PASS requires the actual server-ACKed
ticket to be consumed by an independent Paper event.
REAL_ACTION_ZOMBIE_DEATH_JOIN_DEV_PASS additionally needs a death
event linked to that exact damage event.
No multi-Self replay, distributed World/WAL atomicity,
production authorization, QUAL or SCIENCE claims follow.
QUAL_NO_GO / SCIENCE_NOT_RUN.
