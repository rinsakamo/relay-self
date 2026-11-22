# Q1i/Q1j — original typed OwnerCut / S1 Skill / Git source join (CPU offline)

Q Lane #1088, Draft PR #1089. Original Owner, I, B, I2, World, Native,
Paper, Gemma, physical ActionPort and GPU are NOT started or modified.

## Production source reference

Q inspected at I integration Git HEAD
`7597ed1f2897198402d99ae772643d4dc7e3f6d4`:

- `src/relay_self/self_owner_checkpoint_dev.py` (blob
  `e533d646308bb8572a14aa5a66db0dd7aa761d94`): typed
  `SelfOwnerCut`, exact envelope `{"payload": ...,"sha256": ...}`,
  canonical payload-json-plus-LF digest, generation/Self/World/native
  session, Intent events, Skill histories, peer receipts and registry.
- `src/relay_self/preset_registry_checkpoint.py`: pattern registry v2
  and original accepted Preset reference sha.
- `src/relay_self/intent.py` / `skill.py`: original state transition
  values.
- `src/relay_self/coordinated_checkpoint_dev.py`: a whole generation
  also requires a World snapshot, verified `COMMITTED.json`, all Selves
  and an independently qualified stopped/quiesced process boundary.
  A typed Owner file alone can NEVER attest those.

## Q1i: independently read actual typed OwnerCut bytes

`experiments/q_lane_typed_owner_cut_audit_dev.py` accepts only an earlier,
**independently supplied raw SHA256** and explicit `g-XXXXXXXXXXXX`,
Self, World, branch and old Native session claims.

- Reads with Q's path/component `O_NOFOLLOW` read-only file primitive.
  Detects malformed/duplicate JSON keys, noncanonical bytes and
  incorrectly recomputed SHA256 envelope.
- Checks exact owner payload schema v1/v2 fields and typed generation
  scope; validates bounded Intent lifecycle sequence and monotonic
  nanoseconds; checks Skill current-event snapshots start once, terminate
  once and reference an earlier Intent. A Skill cannot have a recorded
  event after its Intent is released.
- Checks bounded no-duplicate peer delivery receipts and pending
  Questions. For v1, validates pattern field shape/revision; for v2,
  verifies the registry's canonical `schema-registry:v2@` digest,
  matching Self and receipt shape. It does NOT reconstruct every
  `PatternRegistry`, `SkillParameterPreset` or target contract and
  does NOT call the product decoder.
- Reports `Q1I_TYPED_OWNER_CUT_SHAPE_AND_LINEAGE_CPU_OFFLINE_DEV`.
  It explicitly refuses to claim full product semantic decode, authentic
  producer, checkpoint source time, multi-Self generation, World, QUAL
  or SCIENCE.

This is a *conservative subset*: a legitimate product v2 accepted Preset,
an exotic multi-Intent trace or future schema may require expanded Q
logic, not weakening a gate to get a desired PASS.

## Q1j: bind typed OwnerCut to Q1h canonical S1 / Git history

`experiments/q_lane_typed_owner_move_place_join_dev.py` requires the
previous Q1h raw source scope (S1 external anchor, S1/S2 Original canonical
MOVE_PLACE WAL files, checkpoint bytes and Git source custody), plus
separately supplied checkpoint World ID and branch ID. It:

1. Runs Q1h on the RAW original files and inspected exact Git chain.
2. Runs Q1i on the SAME original checkpoint bytes, with the SHA256 that
   Q1h read from the original S1 anchor and the matching original Self
   and native-session scope.
3. Requires the actual `g-{generation:012d}` typed generation match the
   numeric generation claimed in that S1 anchor. This is an explicitly
   bounded *same-generation* scenario, not universal epoch mapping.
4. Joins the certified S1 WAL's exact Intent and SkillExecution IDs to the
   typed cut. In this narrow S1 terminal contract, the original S1 Skill
   must be FAILED/CANCELLED and its Intent must be COMPLETED. A saved
   pre-S2 checkpoint with another active Intent or an active Skill HOLDs;
   it cannot silently represent a later S2.
5. Runs both original raw source readers again and rejects changed WAL,
   checkpoint or Git HEAD/objects during the two-domain inspection.

Reports only `Q1J_TYPED_OWNER_CANONICAL_S1_S2_GIT_JOIN_CPU_OFFLINE_DEV`.
All return flags for producer authentication, real S1→S2 runtime ordering,
full Stage28/Owner restore, Native/Paper causal source, issuer authority,
real World, QUAL and SCIENCE are **false**.

**Critical distinction:** the original Owner's pre-S2 cut must truly be
written BEFORE S2 on a separately controlled original-qualified
source. Backdating a Git commit, rewriting a new anchor and its expected
hash, or recreating a typed OwnerCut later cannot provide that temporal
fact. A wholly fabricated but self-consistent Git archive and WAL remains
outside Q's trusted-source qualification. **Do not promote a Q1j PASS
to I4A_REAL_WORLD_DEV_PASS.**

## Tests and follow-up ownership

`tests/test_q_lane_typed_owner_cut_audit_dev.py` covers v1/v2 envelopes,
tampered outer and inner digest, forged IDs/generation/World/session,
duplicate Intent/Skill, invalid lifecycle transitions, peer/question
replay and malicious but self-consistent SHA repinning.

`tests/test_q_lane_typed_owner_move_place_join_dev.py` covers two
positive synthetic canonical original-format instances and hostile
original checkpoint vs S1 WAL lineage, terminal Skill/Intent, falsely
active S2, exact Git and changed-source readbacks.

The fixtures contain **no actual Minecraft, original Owner or observed
native session data**. They demonstrate that Q's narrow consistency
checker is deterministic, adversarially fail-closed for tested defects
and read-only.

**I/B responsibilities**: independent authentic prior S1 receipt;
typed `load_self_owner_cut` semantic reconstruction and actual
coordinated generation/World `verify_typed_generation`; original Native
stdin/stdout and Paper correlated source, stopped/settled physiology,
trusted Original Owner process identity and authorized physical issuer.
Q cannot create this evidence or transform SHA equality into proof of
execution. Physical pending actions cannot be silently cleared or retried.

**Q1i/Q1j CPU_OFFLINE_DEV consistency only.
ORIGINAL_SOURCE_HOLD / I4A_REAL_S1_S2_HOLD.
QUAL_NO_GO / SCIENCE_NOT_RUN.**
