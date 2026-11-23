# Q1g/Q1h — canonical Original MOVE_PLACE WAL shape and pre-S2 Git custody

Independent Q Lane / Issue #1088 / Draft PR #1089. This is
**CPU/offline, read-only** evidence analysis; NEVER an original Owner,
physical issuer, WAL writer, checkpoint writer or World qualification tool.

## Source and scope

Q1g's independent subset was checked against the actual
`src/relay_self/physical_action_journal.py` in the then-current I
integration branch at exact HEAD
`0e7a29565853dd8cf044bb81f5a19dace81dce64`
(original source blob `7bffab89740f0b90701cf0f12612a29c8b9cad86`).

That source writes a canonical UTF-8 JSON + LF envelope:
`{"body":{"schema":2,"self_id":"...","actions":[...]},"sha256":"..."}`.
The SHA is over canonical JSON encoding of **body**, not the whole file;
`PhysicalActionJournal.restore` checks this digest and row schema.

Previous Q1b/Q1f were *deliberately synthetic*, using flat
`{"schema":2,"self_id":"...","actions":[...]}`. They cannot be
relabelled a test of production journal format, even after all old
offline pytest pass.

Q1g implements **a separate conservative reader** at
`experiments/q_lane_original_move_place_wal_dev.py`, covering ONLY:

- Original schema v2, nonempty history of MOVE_PLACE rows, one Self and
  one unchanged Native session, and one newly appended S2 Action.
- Exact original required MOVE_PLACE row fields, optional WALK/SNEAK
  gait ACK extension and exact canonical envelope plus body hash.
- Sequential Native source_ref/seq; look, optional gait, start, STOP
  native ACK and STOP/settlement sequence; tick settling windows 8..200.
- Numeric finite 3D positions; readback displacement equals their
  Euclidean distance; original MOVE_PLACE terminal classification:
  NO_PROGRESS when <0.1m, OVERSHOOT beyond the optional budget, otherwise
  SETTLED. A terminal NO_PROGRESS/OVERSHOOT is **not Skill success**.
- S1 rows all SETTLED and exact same canonical action prefix in S2, with
  a distinct new S2 Intent, SkillExecution, Action and later native sequence.
  An external exact S1 raw file SHA256 must be supplied separately.
- Symlink/path traversal/changed-file protection is inherited from the
  Q original-source `_raw_file` reader.

Q1g is NOT an exact reproduction of every original
`PhysicalActionJournal._validate` branch. It rejects other legitimately
possible histories (EAT, ATTACK, relative MOVE, schema v1, multiple
S2 Actions, reJOIN, mixed session history) by design. It must never be
used as a generic proof that every version of original journal is valid.

## Q1h: bind actual canonical WAL to external anchor, checkpoint, Git

`experiments/q_lane_original_move_place_git_custody_dev.py` adds a
separate strict Q1h source join:

1. Read a separately pinned, raw S1 pre-S2 anchor (the Q1b anchor shape).
   Compare exact HEAD, World, original Owner, Self, Native session, S1
   Intent/Skill/Action, checkpoint generation, canonical S1 WAL hash and
   checkpoint hash against caller-provided separately established scope.
2. Validate both original canonical WAL files with Q1g, comparing the
   pinned historical S1 file bytes, full append-only MOVE_PLACE history
   and the exact S1 Intent + Skill recorded in the anchor.
3. Confirm the original checkpoint's **raw bytes** against anchor hash.
   The checkpoint's typed schema and generation restoration are NOT
   validated here.
4. Run Q1d's Git custody verifier for a separately specified Git root,
   pre-S2 committed raw anchor and later committed **actual canonical
   S2 WAL raw bytes**. The source and Git branch are not authoritative
   merely because their SHA values agree.
5. Re-read raw Original WAL, checkpoint and Git HEAD again, requiring
   identical results and rejecting source drift during inspection.

Outputs remain strictly:
`Q1G_CANONICAL_MOVE_PLACE_WAL_SHAPE_CPU_OFFLINE_DEV` and
`Q1H_ORIGINAL_MOVE_PLACE_GIT_WAL_COUPLED_CPU_OFFLINE_DEV`.

Both receipts ALWAYS return false for original Owner trust,
source-qualifying Native/Paper, prior independent witness authenticity,
actual event time, checkpoint generation semantics, real World, QUAL and
SCIENCE. A completely attacker-produced but internally consistent
"earlier" Git DAG and recomputed hashes can still pass local consistency.
The **pre-S2 witness must genuinely predate the physical dispatch and be
controlled outside the S2 writer's mutation scope**. Q cannot make such
a witness by recording a new Git commit.

## Reproduction (offline-only)

Q1g is called as a pure function:

    from experiments.q_lane_original_move_place_wal_dev import (
        audit_q1g_original_move_place_wal,
    )
    receipt = audit_q1g_original_move_place_wal(
        ORIGINAL_EVIDENCE_DIR,
        s1_wal_file="original-s1-wal.json",
        s2_wal_file="original-s2-wal.json",
        expected_s1_wal_sha256=EXTERNALLY_PINNED_PRIOR_S1_RAW_SHA256,
        expected_self_id=ORIGINAL_SELF,
        expected_native_session_id=ORIGINAL_NATIVE_SESSION,
        expected_s1_action_count=EXPECTED_S1_ROWS,
        expected_last_s1_action_id=ORIGINAL_S1_LAST_ACTION,
        expected_s2_action_id=ORIGINAL_S2_ACTION,
    )

Q1h is called via `audit_q1h_original_move_place_git_custody` with
the separate original archive path, Git repository clone, exact scoped
Owner/World/Session/Checkpoint identity, raw external S1 anchor bytes,
independently held anchor SHA256 and Git root/anchor/post commits. It
must not calculate or "trust" any pin from the S2 producer's own later
mutable WAL files.

Run focused tests:

    pytest -q tests/test_q_lane_original_move_place_wal_dev.py

They create only disposable local synthetic Git repos and pretend
WAL/checkpoint bytes. Adversarial cases cover forged body/envelope SHA,
changed original S1 records with locally recalculated hash, wrong Action
and Self, replayed source/ACK, STOP without settling, wrong 3D displacement,
forged terminal labels, missing/extra fields, false gait, SNEAK positive,
OVERSHOOT terminal, raw-file symlink, wrong checkpoint, different Git
S2 WAL, altered code Head/World/Owner/Native Session, forged S1
Intent/Skill even under a newly attacker-rebuilt self-consistent Git
history, and Git HEAD drift.

## The next real source gate

Before original S1→S2 can be qualified, I/B must supply **authentic,
independent, earlier S1 witness and original full Journal/Checkpoint,
Native stdin/stdout, Paper ACK/ticks, Owner-supervised Skill terminal and
issue admission leases**. For qualification, independently re-run the
actual product validators at the exact product code HEAD. Q tests neither
start nor authenticate llama.cpp/Gemma, Minecraft, or a World epoch.

**Q1g/Q1h CPU_OFFLINE_DEV only. I4a real S1→S2 HOLD.
QUAL_NO_GO / SCIENCE_NOT_RUN.**


## Q1k: Git parent graph replacement / graft defenses

Git `refs/replace/*` and `GIT_REPLACE_REF_BASE` can cause ordinary
`rev-list`, `ls-tree` and `cat-file` to return substituted object
contents while retaining the originally requested SHA in some displays.
An adversary can conceal an actual multi-parent merge behind a
single-parent replacement and make Q1d falsely accept a linear source
history. Q1k sets `GIT_NO_REPLACE_OBJECTS=1` on **every** Git read in
the custody verifier, including tree and object content inspection.
Legacy `.git/info/grafts` can independently rewrite parents, so any
nonempty or symlinked graft file causes HOLD. Empty regular graft files
are accepted. The Git path is discovered with
`git rev-parse --path-format=absolute --git-common-dir` + literal `info/grafts` to work
with ordinary repositories and linked worktrees.

Adversarial disposable Git tests cover merge laundering with
`git replace --graft`, a legacy parent graft, symlinked graft, and an
empty graft control. This closes a *local history interpretation*
failure mode, not the fundamental missing independent Original Owner
witness or real pre-S2 event chronology. An attacker who controls the
actual Git objects and the external pins can still manufacture an
internally consistent history.

**Q1k Git object custody hardening CPU_OFFLINE_DEV only;
Original independent source HOLD; QUAL_NO_GO; SCIENCE_NOT_RUN.**
