# Q1b — S1 external preanchor and destructive-tree audit (DEV)

Issue #1088 / I #1061 / architecture #828. This documentation belongs only to
Q; it does not grant a World, Memory, GPU or Physical authority.

## Observed destructive tree on I integration

GitHub commit [87d0e68e](https://github.com/rinsakamo/relay-self/commit/87d0e68e55b6978a02fc82e3826fb9320f736c05)
(parent 959264a22b670db96709af46cb532bea746acc9d) removed **156,846**
lines and added 54. Its tree 79f905ce3cde141b1d7feac39f48c6ecfdfb22e2
contained only 7 entries, corresponding to 3 PRE_WORLD files: a report,
a runner and a test. Original WAL, Owner and CI files were gone. Q reported
a strict HOLD to #1076, #1061, #1088 and #828 without changing I files.

Follow-on recovery [ca2be4b5](https://github.com/rinsakamo/relay-self/commit/ca2be4b500436dc25646d3f5511f5f6d7cd1b983)
restored 156,845 lines, now showing 626 tree entries including original
WAL and CI files. That is presence only, **not** a current CI or real-World
certification; fetch current I HEAD/CI before reusing this status.

## Q tree guard (independent, read-only)

Run experiments/q_lane_tree_integrity_dev.py against an exact local I branch
checkout, with an intact earlier parent as the trusted comparison baseline:

    python -m experiments.q_lane_tree_integrity_dev \
        --repo-root /path/to/relay-self \
        --base-sha <intact-prior-40hex> \
        --expected-head <current-branch-40hex>

The checker only reads Git commit trees. It refuses missing historical tracked
files, protected owner/WAL/issuer/CI paths converted to symlinks, a wrong
HEAD and a foreign unrelated base. It never checks out files, stages a write,
moves a branch ref, starts a model or launches Minecraft. For this additive
PRE_WORLD slice all historical deletions are unexpected. Future intentional
deletions need separately reviewed exception policy, not a weakened default.

Classification Q_TREE_PRESERVATION_CPU_OFFLINE_DEV_PASS is strictly a
code-tree preservation result, NOT source origin or physical qualification.
Repaired HEAD does not erase its destructive historical commit.

## Q pre-S2 S1 WAL/checkpoint anchor readback

experiments/q_lane_s1_boundary_audit_dev.py requires separately supplied
pre-S2 anchor bytes plus an **independently retained expected SHA**. It checks
both S1 original WAL and checkpoint raw hashes, scoped exact code HEAD,
Owner/Self/World/Native session/checkpoint generation, the original S1
Intent/Skill/Action/terminal status, exact historical Action-row prefix in
a later S2 WAL, and at least one new distinct S2 Action. It rejects foreign
identity, duplicate/old Action IDs, missing checkpoint, changed/rehashed
S1 rows, malformed/duplicate JSON fields, symlinks, unresolved PREPARED and
a missing S2 continuation.

Example, provided the anchor truly was retained before S2:

    python -m experiments.q_lane_s1_boundary_audit_dev \
        --evidence-dir /path/to/frozen-original-evidence \
        --external-anchor /separately-controlled/pre-s2-anchor.json \
        --pre-s2-anchor-sha256 <digest-retained-before-s2> \
        --s1-wal s1/wal.json \
        --s1-checkpoint s1/checkpoint.json \
        --s2-wal s2/wal.json \
        --s2-action-id <new-s2-action-id> \
        --head <actual-code-head> \
        --world-uuid <original-world-uuid> \
        --owner-id <original-owner-id> \
        --self-id A \
        --native-session-id <original-session> \
        --checkpoint-generation <generation>

The code never generates a supposedly trusted pre-S2 anchor from later
evidence. The test fixtures use simplified synthetic JSON, not the original
PhysicalActionJournal or Stage28 checkpoint serializer. Original
Stage28/WAL/source auditors remain mandatory and are not duplicated here.

A provided digest is only a comparison value. Git tree hashes do not prove
who captured an S1 anchor or whether it predates S2. An attacker controlling
both anchor bytes and expected digest can still create a consistent forged
source; Q tests this explicitly. The result
Q1B_PINNED_S1_S2_WAL_PREFIX_CPU_OFFLINE_DEV therefore always sets:
trusted_external_anchor_origin_verified=false,
pre_s2_temporal_order_verified=false,
original_owner_semantics_verified=false,
original_stage28_checkpoint_restored=false,
real_world_attested=false, qual_go=false and science_run=false.

## HOLD and ownership

B/I must separately deliver a trustworthy earlier generation-bound S1
checkpoint/WAL receipt controlled outside mutable S2 output. I must preserve
its full Git tree, exact-head CI and eventually original source-qualified
real S2 issuer. Q can inspect independent frozen original Paper/Native,
WAL, original Owner/Stage28 and model records only when actually available;
synthetic fixtures and local self-calculated hashes do not qualify.

Q1b is CPU_OFFLINE_DEV for consistency checks only. Original S1/S2
authentication, World, real Gemma, QUAL and SCIENCE stay HOLD/NO_GO/NOT_RUN.
