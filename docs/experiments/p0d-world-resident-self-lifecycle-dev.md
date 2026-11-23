# P0-D #860 / Causal Recovery #851 — Stage 18 World residence, independent Self lifecycles (DEV)

Stacked on #885 (N-Self bounded full-roster synchronous checkpoint) → #880.
**Stage 18 is an alternative operation mode, not retroactive qualification or
a replacement for #885's all-N rollback contract.**

## Selected new policy

A Minecraft World is the physical authority, and each Self has its own durable
identity/cognition independent of whether a Mineflayer body is online. World
can progress with no Self at all. A Self's crash does not automatically stop
the World or unrelated currently ONLINE Self. The host distinguishes
OFFLINE → LOGIN_PENDING → ONLINE → LOGOUT_PENDING → OFFLINE and an
independent QUARANTINED path after uncertain termination.

**The World is not rolled back to accommodate a Self's old beliefs.** If A
remembers that a zombie was alive before logout but B killed it meanwhile,
A's memory remains historical and A must reobserve current World after login.
A different World ID/branch/tick has the same effect: retain identity and
retained cognition, invalidate native entity targets, Present projection,
physical Body state, current World assumptions and old Action authorizations.

World replacement or a same-world host restart is a fresh
(world_id, branch_id, host epoch, Paper session) binding. Numeric ticks are
NOT transferable between World histories or processes. Minecraft inventory,
playerdata, dimension-local body state and target IDs do not automatically
move from one World to another. No Action or Skill is replayed.

## Implemented, exact scope

- `world_resident_lifecycle_dev.py` is an in-memory typed, non-issuing
  membership and epoch contract. N may be zero. Every registered Self has an
  independent stable retained-cognition reference and a mutable presence.
  WORLD can accept Paper-source qualified ticks while all are offline, and
  while one Self is quarantined with others ONLINE. A Self failure does not
  mutate any peer's presence or issue automatic World rewind.
- `begin_login` generates a World/branch/Paper-epoch-scoped ticket.
  `complete_login` demands fresh session, same world epoch, request
  correlation, new native World tick not behind latest known Paper tick,
  clear original physical WAL, stale GPU/message fencing and actual
  source verification. This module itself never grants an Action. The
  previous stored cognition ref is carried only as historical context;
  fresh Present and Body must be reconstructed separately.
- `begin_logout` marks intent to leave, not proof that an Action stopped.
  `finish_logout` requires external *original issuer* proof: native child
  terminated, physical gate revoked, no in-flight Action, clear original
  WAL, retired GPU tasks, drained peer transport, durable cognition ref.
  A missing/false proof leaves that Self QUARANTINED, never silently OFFLINE.
  The other Self keep their statuses; whether real-world physical effects
  are contained still depends on connecting the original issuer.
- `begin_world_transition` rejects ONLINE, LOGIN_PENDING, LOGOUT_PENDING
  or QUARANTINED Self. `install_world` requires a new host epoch and
  different owned Paper session, old Paper terminated, World archive/source
  independently verified, old Action epoch fenced and no portable Body
  state import, historic replay or issue grant. On false evidence, World
  transitions to irreversible HOLD in this DEV owner.
- `world_only_owned_checkpoint_dev.py` explicitly controls the **same
  original OwnedPaperWorld**, only with zero ONLINE Self AND an independently
  supplied `WorldOnlyQuiescenceEvidence` from the original physical/GPU/peer
  owners. The explicit proof requires the exact Self roster, current World
  epoch, physically closed issuer, absent native sessions, no unresolved
  Action/WAL, retired GPU epochs and drained peer messages. An in-memory
  OFFLINE list alone can NEVER authorize World-only stop or World swap.
  No production receipt provider is connected yet; the test supplies
  visibly synthetic evidence. It obtains a real
  owned-process STOP/flush receipt, archives main + any known Paper sibling
  dimensions via the **existing** stopped-world archive SHA code, writes
  `WORLD_ONLY_COMMITTED.json` last, verifies manifest/hashes/zero Self
  snapshot count, restarts its owned Paper, and increments host epoch.
  This is a separate World-only manifest, NOT #885's typed World+all-Self
  generation; no `selves/` is written or silently reactivated. A failed
  flush, corrupted archive, failed restart or missing Self retirement
  never becomes an adoptable World-only generation.
- `verify_world_only_generation` reads and validates exact World-only
  World and companion source metadata and hashes. This is only archive
  integrity; actual Paper provenance is external.
- `owned_paper_world_switch_dev.py` now accepts two **different owned
  Paper server directories**. It requires every Self offline AND a
  separately supplied, source-qualified original issuer retirement receipt,
  a STOPPED candidate with a pre-existing World-only committed archive, an
  *externally pinned* SHA256 of that commit marker, exact source-vs-archive
  file inventory/digests for overworld and all Paper dimensions, and
  matching target World/branch identity. Source mismatches are rejected
  BEFORE the old Paper is disturbed. Once frozen, the old owned Paper
  is saved/stopped first, the candidate files rechecked, the new owned
  Paper launched, and a fresh native server tick read back. The new
  World branch+epoch is then installed without copying any Self Body
  data or replaying any Action. A failure after transition begins
  permanently HOLDS this World owner; it never guesses that the old
  World is still running. This is still an offline **fake-Paper** test,
  not actual qualified live Paper provenance.

## Relationship to old checkpoint and dynamic issuer

#885 remains usable for **deliberately global** all-N World + Self
point-in-time rollback, but its fixed-roster PhysicalIssueAdmission and
CognitionOwnerCohort do **not** support live per-Self deregistration,
resumption, source qualified GPU retirement or arbitrary Paper World
replacement. The new presence module deliberately **does not** splice
a new authority into them and **cannot** yet take over actual Mineflayer
session controls. Future physical issuer work must extend the *original*
owner with per-Self admission fences and a session/writer epoch, never
infer issue permission from the in-memory ONLINE flag. World-only file
archive and its no-actor guard are not distributed World/WAL atomicity.

A failed native issue with an unresolved physical effect cannot be
called a safe completed logout. A quarantined Self cannot log back in
or participate in World replacement until its original WAL/effects
are reconciled and positively fenced. The World may continue meanwhile
as the physical authority, and other online actors can see any
physically completed effect as a new event. Pending peer messages need
recipient-targeted causal analysis rather than a naive "no interaction"
assumption. The lifecycle model never asserts that such foreign
effects are impossible.

## Offline evidence

Python synthetic tests N=0/2/10/100:
- ticking and world-only owned OS child with **fake Paper console**, two
  stopped-file generations, no Self snapshot modified
- Nether/End hash coverage, corruption refusal, missing flush HOLD,
  and owned stopped-World A→B switch with pinned candidate, wrong pin,
  modified region, active/quarantined Self rejection, original issuer
  still open, unresolved physical WAL and stale World retirement epoch
- N=2/10/100 one quarantined Self while unrelated N-1 remain ONLINE;
  World source clock keeps advancing
- wrong world branch, stale/reused session, old request, stale clock,
  invalid retirement receipt, unavailable member, unsupported body
  portability and stale World epoch refusal

**No real Paper was started, no real players/LLM/GPU were run, and no
dynamic physical issuer is connected in this slice.** Do not classify
the synthetic World-only console as real Minecraft. Actual Paper
World swap, cross-World avatar migration, dynamic roster, selective
live GPU/transport cancellation, multi-Self World effect isolation
and recovery from unverified in-flight native Actions remain open.

DEV classification: `WORLD_RESIDENCE_LIFECYCLE_OFFLINE_DEV`;
`LIVE_PER_SELF_LOGOUT_NOT_ATTESTED / REAL_WORLD_ONLY_NOT_ATTESTED /
REAL_WORLD_SWAP_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN`.
