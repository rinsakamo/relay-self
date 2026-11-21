# #858 P0-C — Forked World + Self A/B historical cut + fresh Present DEV

**Status: offline contract, not real Minecraft restore or concurrent
autonomous multi-Self execution.** This is a read-only bridge across
P0-A #853/#854, P0-B #855/#856/#857, and the strict #851
causal_recovery assessor. Does NOT call the strict assessor with
fabricated atomic_capture_attested=true or event coverage.

## Why the existing strict assessor cannot be naively reused

Restoring W100/W110 through P0-A generates a **new fork branch**.
P0-B ATTACK and paper event remain in the original source branch,
not the new fork. Thus an ordinary same-branch comparison would
reject a valid inherited historical effect or pretend that an Action
has physically occurred again. Different clocks (conceptual
C98/C105, level.dat Time/DayTime, Paper server tick and Mineflayer
seq) must not be compared as a single monotonic tick.

This DEV bridge uses an explicit scoped SourceWorldCutWitness:
world_id/source_branch_id/checkpoint_id, targeted Zombie UUID,
alive state at capture (may be UNKNOWN), event IDs INCLUDED in the
source cut, and independent source ref. The cut witness is an external
assertion based on actual local observations; it does **not** prove
full event coverage or global World/WAL atomicity. No cryptographic
authenticity is required for DEV. Missing event membership -> HOLD.

## Files and prelaunch/postlaunch phases

- src/relay_self/forked_recovery_dev.py
  - joined_action_effect_dev REEVALUATES typed P0-B native/WAL,
    preissued server ticket, Paper damage and linked death. Without
    a real ticket-correlated effect it cannot assert a source Action.
  - DerivedCognitiveCut: existing SelfCheckpoint with independent
    provenance tag SIMULATED / OBSERVATION_DERIVED. Exclusive
    separate-file save/load (no persistent cognition mutation).
  - prepare_forked_recovery_dev: before Minecraft launch calls
    verify_world_checkpoint and verify_restored_world on the
    original archive and P0-A fork directory. Checks source branch,
    target state vs included event, self claims, WAL, source effect
    and cross-Self message causal cut. It returns a candidate,
    HOLD or REJECT and NEVER grants physical issue.
  - reproject_present_from_fresh_world_dev: after launch consumes
    fresh *new fork branch*, *new native session*, target UUID,
    state and source. Prior Self beliefs stay retained, including
    Self A's post-W100 memory of killing Z1. A new target-state
    **Present candidate** is produced; the actual Present/Schema/Intent
    owners are NOT modified or restored. Missing or uncertain
    Zombie state remains UNKNOWN.
- experiments/audit_forked_recovery_dev.py: two-phase offline CLI.
  The prelaunch file integrity gate MUST run BEFORE starting the
  restored Minecraft server, since live files may change afterward.
  Store the prelaunch result separately, then pass a fresh postlaunch
  WorldBody record after the new server starts. No native IO.

### Inputs

1. A real P0-A stopped server World archive containing manifest.json,
   SHA256SUMS, world/ and a **new never-existing** restored World,
   plus its world.restore.json fork receipt.
2. source-cut.json exactly matching SourceWorldCutWitness fields:
   world_id, source_branch_id, checkpoint_id, target_uuid,
   target_alive_at_capture, included_effect_event_ids (array) and
   source_ref. For W110 with P0-B lethal event e.g. ["death-2"];
   for W100 captured before that event: []. DO NOT infer membership
   solely from level.dat Time or from an event ID label.
3. Two independently stored DerivedCognitiveCut JSONs, one for
   Self A (cognitive cut after Action, retained death belief, linked
   ActionClaim), one Self B (earlier alive belief, no claimed attack).
   Mark B SIMULATED unless a *genuine separately observed* Self B
   supplied its own source. Synthetic cognition is allowed for a
   DEV model, but may NOT be presented as concurrent real 2-Self.
4. An actual original Self A PhysicalActionJournal WAL file, never
   modified by this audit. A PREPARED_UNRESOLVED entry is HOLD,
   never cleared or reissued.
5. The original P0-B join JSON with exact fields self_id, action_id,
   world_id, branch_id, native_identity, server_attack_ticket,
   server_damage_events and server_death_events, with actual ticket,
   Paper logs and native sources preserved separately. Typed
   effects must match actor Self A, zombie UUID and WAL.
6. After running new fork server, fresh-worldbody.json has keys
   world_id, new_branch_id, native_session_id, target_uuid,
   observed_target_alive (true / false / null), source_ref and
   runtime_target_entity_id (new ID or null). The source must
   justify negative target existence/death; a bounded non-sighting
   of a zombie is UNKNOWN/null, not automatically false.

### CLI

Example; W100 and W110 use **different fresh fork paths,
independent prelaunch plans and fresh session observations**:

    python -m experiments.audit_forked_recovery_dev prelaunch \
      --archive /ABS/W100 \
      --restored-world /ABS/FORK_W100/world \
      --source-cut-json /ABS/cut-w100.json \
      --self-cut /ABS/Self-A-C105.json \
      --self-cut /ABS/Self-B-C98.json \
      --wal /ABS/original-Self-A-physical-wal.json \
      --ticket-world-join-json /ABS/source-attack-join.json \
      --output /ABS/new-w100-prelaunch.json

    # Start ONLY this forked Minecraft server after prelaunch succeeds;
    # record new session / fresh WorldBody UUID evidence.

    python -m experiments.audit_forked_recovery_dev postlaunch \
      --prelaunch-plan /ABS/new-w100-prelaunch.json \
      --fresh-worldbody-json /ABS/new-w100-fresh.json \
      --output /ABS/new-w100-present-candidate.json

Run the same separately for W110 using W110's own stopped source
archive, new branch, source-cut event list and new native session.

## Expected two-branch DEV outcomes

| Case | Historical source cut | Self A retained memory | Self B retained memory | New fork Present candidate |
|---|---|---|---|---|
| W110 | Death event included | Killed Z1 (C105) | Earlier Z1 alive (C98) | Z1 dead, if fresh evidence supports it |
| W100 | Death event excluded | Killed Z1 (after W100) | Earlier Z1 alive | Z1 alive, if fresh evidence supports it |

On W100, the retained historical Action A1 is explicitly marked
post-cut and belongs to **another history**. No automatic
physical ATTACK reissue, no deletion of the memory, no fake transfer
of original Paper event into the new branch.

Both cases start as NEEDS_FRESH_WORLD_BODY. A qualified fresh
observation may yield a *target-state only* DEV Present candidate.
This is not the full Present owner/Schema/Intent reassessment.
If source branch/cut mismatches, reject; if WAL unresolved,
target UNKNOWN or events incomplete, hold or keep reobserving
without physical issue. All results physical_action_issue_authorized
false and self_owner_restored false.

## Existing evidence cannot simply be spliced

P0-A real World checkpoint tests (#854) and P0-B real Paper ATTACK/death
trials (#857) were performed in **different actual Minecraft Worlds**.
Their World UUIDs and branch histories do not identify one causal
trajectory. Do not assemble W100 from the former and W110 from the latter.
Collect a NEW W100 -> ATTACK ticket / death -> W110 on one actual
source World/branch before any claim of real forked causal replay.
The offline tests below use simulated World files and synthetic ticket
events, not the prior real-world evidence as if it were shared.

## LocalCodex controlled real Paper 1.21.8 sequence

1. Read repo/#851/#858 and PRs #854/#857 plus this branch exact
   HEAD and CI. Use isolated worktrees and NEW evidence directory.
2. New Paper World, normal difficulty. Capture W100
   **after stopping server cleanly**, with Zombie UUID alive and
   its Player/inventory readbacks. Document actual Paper World
   UUID, source branch and separate game-time/event identities.
   Store file manifest and event membership evidence.
3. Resume the source World with existing native L1/L0
   PhysicalActionPort and NEW Self-owned WAL, perform one
   ticket-correlated ATTACK with a *known low positive Health*
   Zombie, verify Paper death event damage link. Preserve raw
   Paper, ACK, native seq, WAL, full source refs. STOP source
   World, capture W110 with death event included.
4. Independently derive and save Self A late cognition (Action
   claim/retained death) and Self B early cognition (retained alive).
   Only claim real independent B if it actually ran. Otherwise
   tag B SIMULATED and keep physical evidence provenance separate.
5. Restore W110 to a NEW isolated fork, verify entire file
   equality BEFORE Minecraft launches. Run prelaunch audit,
   then start fork and collect new native session WorldBody
   with exact Target UUID/Entity status. UNKNOWN if absence
   unverified; do not assert death from missing nearby entity.
   Run postlaunch.
6. Restore W100 into ANOTHER new fork and repeat prelaunch
   and postlaunch. Confirm fresh target alive despite retained
   A-death belief. Never send the old ATTACK or re-use stale
   native Entity ID, even if integer happens to match.
7. Negative: swap branches, WALs, missing/foreign ticket,
   duplicate Action event, unknown target, missing B message
   send, restored-target state mismatch, PREPARED_UNRESOLVED.
   Use only copied evidence/disposable NEW Worlds.
8. Preserve all original SHA256 and actual source/HEAD/CI,
   report separate classifications and real vs synthetic
   status to PR/Issue and read back posts.

## Success levels

- OFFLINE_FORKED_RECOVERY_DEV_PASS: exact HEAD CI and tests.
- REAL_WORLD_W100_W110_CAPTURE_RESTORE_DEV_PASS: **both** actual
  World checkpoints captured and separately restored with
  full file integrity and requested physical readbacks.
- REAL_FORK_CAUSAL_CUT_DEV_PASS: real source ticket/WAL event and
  both independently sourced World cut memberships correspond
  to the physical state, not guessed clocks.
- REAL_SELF_A_B_CHECKPOINT_DEV_PASS: two independently
  recorded *real* Self cognitive streams, not a synthetic B.
- FRESH_TARGET_PRESENT_DEV_PASS: separate fresh fork sessions
  observe the target and scoped target Present projection.
  Actual Schema/Intent owner reactivation remains NOT_ATTESTED.

This explicitly avoids demanding a separate PREPARED intermediate
snapshot for normal DEV success; it remains a distinct durability
question. No QUAL or SCIENCE claim follows. QUAL_NO_GO /
SCIENCE_NOT_RUN.
