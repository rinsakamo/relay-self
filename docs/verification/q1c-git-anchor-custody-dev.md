# Q1c — pre-S2 Git blob custody is not runtime authentication

Q Lane Issue #1088 / Draft PR #1089. DEV read-only assessment.
Main-based Q never imports B/I owner, PhysicalActionPort, GPU or Memory runtime.

## Exact inspection contract

The new experiments/q_lane_git_anchor_custody_dev.py inspects a local
Git repository at an exact committed S2 HEAD. The operator supplies:

- a **separately verified** 40-hex earlier trust-root commit;
- a distinct pre-S2 *anchor* commit that descends from that root;
- a distinct post-S2 *evidence* commit descending linearly from the anchor;
- original anchor and new S2 evidence paths; independently held exact SHA256
  pins for each committed file.

The read-only checker uses git rev-parse, merge-base, ls-tree,
rev-list and cat-file; it does not checkout, commit, write a file, start
Minecraft, send Native commands or enter the original Owner. It verifies:

1. exact HEAD equals post-S2 commit; root -> anchor -> evidence are an
   ordered Git commit ancestry, not merely a commit's author date;
2. anchor and S2 files are absent at the supplied earlier root, S2 file
   is absent in the anchor commit and immediately preceding S2 commit;
3. anchor is a normal regular Git blob and remains **the exact same blob**
   across every linear intermediate commit through the S2 evidence commit;
   merges and reordered/nonlinear paths HOLD;
4. both file bytes match the independently supplied SHA256 pins, with
   bounded object size and symlink/submodule refusal.

Invocation, using only previously established real commit IDs and separate
pins (placeholder labels must be substituted, never auto-inferred):

    python -m experiments.q_lane_git_anchor_custody_dev \
      --repo-root /path/to/read-only-clone \
      --trusted-root-sha <earlier-trusted-40hex> \
      --pre-s2-anchor-commit <earlier-anchor-40hex> \
      --post-s2-evidence-commit <later-evidence-40hex> \
      --anchor-path proof/pre-s2-anchor.json \
      --s2-path proof/post-s2-evidence.json \
      --expected-anchor-sha256 <independent-earlier-64hex> \
      --expected-s2-sha256 <independent-later-64hex>

The strongest local category is
Q1C_GIT_DAG_PRE_S2_BLOB_CUSTODY_CPU_OFFLINE_DEV, and only states that
the **Git commit graph** has a consistent, unbroken blob chain.

## What is independently known, and what is NOT

Git object hashes bind committed bytes to an inspected DAG. They do not
provide an independent signer, operator identity, tamper-proof clock,
runtime-relevant Owner scope or evidence of when the *World events* occurred.
An attacker able to construct a full new history (and choose all three
commit IDs and SHA pins) can obtain a consistent result. Even a correctly
ordered anchor commit can be created after the true S2 action, or for a
fabricated action. The auditor MUST NOT call that real pre-S2 capture.

The receipt **always** returns false for:

- external_root_origin_authenticated
- anchor_producer_authenticated
- real_pre_s2_capture_time_verified
- owner_checkpoint_semantics_verified
- original_wal_validated
- real_world_attested / qual_go / science_run

The original Q1b verifier still needs the exact immutable S1 original WAL
and checkpoint bytes, matching the external S1 anchor and the later full
S2 WAL prefix. The original Stage28 typed generation and physical journal
auditors must independently inspect production schemas. These tools are
separate; neither one's synthetically valid fixture grants authenticity
or physical action authority to the other.

## Independent witness admission criteria for future real S1/S2

**Original B/I responsibilities, not Q-side runtime changes:**

1. At a genuinely source-qualified S1 terminal, the existing original Owner
   freezes a canonical S1 WAL and checkpoint generation and verifies
   original Native/Paper/STOP evidence; no PREPARED_UNRESOLVED promotion.
2. A separately controlled witness receives the unmodified WAL/checkpoint
   byte hashes, exact run HEAD, original Owner/Self/World/session,
   generation and S1 Action ID **before S2 can dispatch**. It records
   an independently retrievable custody time / monotonic order and prevents
   either the S2 producer or Q auditor from rewriting the old receipt.
3. The original issuer, not Q, proceeds with S2 only through existing
   PREPARED, ActionPort, STOP and Supervisor gates. The S2 evidence
   references the earlier receipt and retains the full append-only history.
4. Q retrieves the earlier witness independently and reads immutable
   original Native/Paper/WAL/checkpoint archives read-only. Q compares the
   original source against the witness, checks previous and current HEAD
   with the original code auditors, and only then considers a scoped
   independent source audit result. No self-written SHA is an authority.

If any earlier witness, genuine checkpoint, original World source or owner
identity cannot be obtained, classify **HOLD** rather than synthesizing
a stand-in. Actual witness provenance/trust must be evaluated separately;
a Git path or signature alone is insufficient.

## Tests and provenance

tests/test_q_lane_git_anchor_custody_dev.py uses disposable local Git
fixtures, not the private WSL original evidence. It covers altered
root/anchor/post/head and SHA, S2 in pre-anchor commit, S2 added too early,
intermediate anchor changed then restored, symlink source, wrong path,
nonlinear history and untrusted-but-self-consistent producer roots.
Read-only invariance is checked, including unchanged Git HEAD.

This is **CPU_OFFLINE_DEV** for a narrow version-control file-custody
property, not REAL_WORLD_DEV or INDEPENDENT_SOURCE_AUDITED_DEV.

Q1c remains PRE_WORLD / QUAL_NO_GO / SCIENCE_NOT_RUN for I4a S1->S2.
