# Q1d/Q1e — bounded Git source births and coupled S1/S2 custody (DEV)

Q Lane #1088, Draft PR #1089. This is **read-only** inspection on the
independent Q branch, not a source producer, checkpoint author, GPU owner,
Original Owner replacement, authentication service or physical ActionPort.

## Why Q1d was necessary

Earlier Q1c looked for the S1 anchor at the selected pre-S2 commit, and
required the final post-S2 commit to newly contain S2 evidence. It rejected
anchor edits after the pre-S2 commit. But two independent histories could
previously satisfy that check despite an incompatible time ordering:

1. Root -> S2 committed -> S2 deleted -> S1 anchor committed -> S2 committed
   again. Checking only root and selected pre-S2 commit missed the
   **transient S2 evidence before S1**.
2. S1 anchor committed -> S2 committed -> S2 deleted -> final S2 committed.
   Checking only the immediate parent of the final commit missed the
   **earlier S2 appearance**.
3. Root -> actual S1 anchor committed -> later commit relabeled as the
   selected pre-S2 anchor. Its original birth was earlier than claimed.

Q1d now validates a **strict, first-parent, single-parent bounded linear
chain** both from the trusted Git root through the designated anchor-birth
commit, and from the anchor to S2 commit (up to 128 steps per span). It
requires that the anchor first occurs at the selected pre-S2 commit and
S2 evidence first occurs at the selected final S2 commit; neither path
may be present at any preceding intermediate commit. It also rejects
post-commit HEAD drift before returning a positive receipt.

The named commits must be exact 40-hex IDs. The operator supplies the
Git root and file-content pins; Q cannot attest how these were obtained.
Checking this property **does not** prove an S1 World event was actually
completed before a later real S2 World event. Git ancestry is a code/data
retention order, not physical causality.

## Why Q1e was necessary

Two individually successful, standalone checks can refer to **different
files or different runs**. A Git anchor check may pass for one internally
consistent Git archive while the S1/S2 WAL checker passes for another.
Treating their independently produced receipts as an end-to-end audit
would allow an evidence substitution without an exact byte-level join.

The new experiments/q_lane_coupled_custody_dev.py instead operates on
untrusted **raw evidence and claims**, not caller-injected PASS receipts:

- Run the Q1b S1 historical WAL/checkpoint verifier against supplied
  pre-S2 anchor bytes and an expected external SHA256.
- Run Q1d Git DAG custody against the **same S1 anchor SHA256** and the
  **actual SHA256 of the original S2 WAL just read by Q1b**, not another
  caller-chosen S2 hash.
- Read the original S1/S2 WAL/checkpoint again and compare both Q1b
  readbacks exactly. Then repeat the Git custody check, comparing both
  Git readbacks exactly. This rejects observed mutations of the source
  or Git HEAD between the two domain reads.
- Require exact source-claim and Git-claim fields; unknown or externally
  supplied prior verifier receipts are rejected.

A successful receipt is
Q1E_GIT_S1_ANCHOR_S2_WAL_COUPLED_CPU_OFFLINE_DEV. It declares only
that a *locally inspectable* S1 anchor + checkpoint/WAL and S2 WAL share
the same bytes as the selected committed Git objects, under the given
unverified root/pins. It does **not** grant any original Runtime authority.

All positive receipts explicitly say false for external Git-root origin,
anchor producer provenance, true pre-S2 World capture time, original
Owner/Native/Paper, real World, QUAL and SCIENCE.

## Reproduction interface

The verifier is a Python function, not a new executable World runner:

    from experiments.q_lane_coupled_custody_dev import (
        verify_coupled_s1_s2_custody,
    )

    result = verify_coupled_s1_s2_custody(
        evidence_dir=ORIGINAL_READ_ONLY_EVIDENCE_DIR,
        git_repo_root=SEPARATE_GIT_ARCHIVE_CLONE,
        anchor_bytes=EARLIER_ORIGINAL_ANCHOR_BYTES,
        source_claims={
            "expected_pre_s2_anchor_sha256": EARLIER_PINNED_SHA,
            "s1_wal_path": "s1-wal.json",
            "s1_checkpoint_path": "s1-checkpoint.json",
            "s2_wal_path": "s2-wal.json",
            "expected_s2_action_id": S2_ACTION_ID,
            "expected_head": ACTUAL_ORIGINAL_CODE_HEAD,
            "expected_world_uuid": ORIGINAL_WORLD_UUID,
            "expected_owner_id": ORIGINAL_OWNER_ID,
            "expected_self_id": ORIGINAL_SELF_ID,
            "expected_native_session_id": ORIGINAL_NATIVE_SESSION_ID,
            "expected_checkpoint_generation": ORIGINAL_GENERATION,
        },
        git_claims={
            "trusted_root_sha": EARLIER_GIT_ROOT_COMMIT,
            "pre_s2_anchor_commit": EARLIER_GIT_ANCHOR_COMMIT,
            "post_s2_evidence_commit": LATER_GIT_S2_WAL_COMMIT,
            "anchor_path": "proof/s1-anchor.json",
            "s2_path": "proof/s2-wal.json",
        },
    )

**Important:** these uppercase names are deliberately not supplied by Q.
They require real independent Original Owner evidence and separately held
trust expectations. Do not invent fixture identities or backdate a Git
commit to simulate an earlier S1 run.

## Source families and exact verification

- tests/test_q_lane_git_anchor_custody_dev.py covers anchor introduced
  too early, transient deleted/reintroduced S2 before/after anchor,
  a merge in the trusted-root-to-anchor path, bounded overlong histories,
  and HEAD drift.
- tests/test_q_lane_s1_boundary_audit_dev.py covers a valid coupled
  synthetic fixture, foreign anchor, different-but-valid Git S2 bytes,
  changed local S2 WAL after Git commit, wrong Original Owner/Self/native
  session/generation, unknown claimed pass receipts, missing checkpoints,
  and changes to either domain during the two-step inspection.

These are **synthetic, CPU/offline** fixtures only. Q's simplified original
WAL fixture is intentionally not the full production PhysicalActionJournal
schema. Production adoption must use the existing I/B/Stage28 historical
journal, checkpoint, Owner Native/Paper and process verifiers, and an
independent, genuinely pre-S2, externally controlled witness.

## Scope and outstanding owner work

**I/B** still need an authentic, pre-S2, generation-bound WAL/checkpoint
witness; actual S1 terminal and S2 dispatch must be observed on one
Original Owner source and verified with original Paper/Native histories.
Git commits cannot substitute for that witness or imply World time order.

**Q** continues an independent read-only audit, with an inability to
inspect private WSL originals in GitHub Actions. It may accept a limited
CPU_OFFLINE_DEV consistency classification but **must not upgrade**
to INDEPENDENT_ORIGINAL_SOURCE_AUDITED_DEV, REAL_WORLD_DEV, QUAL or SCIENCE
without their own original evidence. Current overall state remains
**I4A_S1_S2_REAL_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN**.
