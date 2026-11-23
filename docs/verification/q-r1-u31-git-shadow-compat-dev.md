# Q independent R1 Git-source compatibility audit — U31 baseline

**Audit role:** separate Q code lineage from R1. Read-only Git object + Python AST negative-control checker. This verifier **does not** read, write or launch the original U31 World, LLM, Owner, Native, Paper, WAL or persistent Memory. All original WSL source remains under `/home/rinsa/evidence/i-u31/` (not mounted in this GitHub CI environment). `QUAL_NO_GO / SCIENCE_NOT_RUN` always.

## Pinned identities

- Original I U31 [#1124](https://github.com/rinsakamo/relay-self/pull/1124): `d3034026a8eea3d2d4927527f5bc0d6ad0455457`.
- R1 Shadow [#1129](https://github.com/rinsakamo/relay-self/pull/1129): `c4917e21a496107638b98f8b98c49bc60aa6d9aa`.
- Independent Q [#1089](https://github.com/rinsakamo/relay-self/pull/1089): `450734c54e1432ec70a8206952779b5ad82796d8`. Q branch itself is **not** rebased onto R1.
- Original Q6/Q7/Q8/Q11 WSL audit of U31 remains the historical separately grounded DEV evidence only. No Q-R1 original source byte reinspection has occurred here.

## Check

Use `python -m experiments.q_lane_r1_u31_git_static_compat_dev --repo-root /path/to/relay-self` **only in a Git checkout/worktree with the exact I U31 and R1 Git objects locally available** (fetch if needed, without checking out or altering the originals). This CLI traverses immutable objects by externally specified Git hashes, even if the checkout's current HEAD is Q or another branch. No object fetching or branch switch is performed by the program.

- Reuse existing Q parent-graph guard (`GIT_NO_REPLACE_OBJECTS=1`, refusal of Git grafts), and require a finite **single-parent** ancestry from the U31 I commit to R1.
- Every intermediate R1 commit must preserve **every preexisting U31 tracked file's mode/blob**. Transient modification+restore of Original Owner, Native, I4a, Runtime, GPU, WAL or original U31 tests is a failure.
- Only three new regular `100644` files may ever appear: R1 read-only module, R1 hostile tests, R1 responsibility map. Missing, extra, executable or symlinked additions fail closed.
- Inspect the new R1 module AST for explicit original read-only sources, known R1 entrypoints and frozen non-grant result fields. Forbid obvious physical/GPU/issuer imports or calls, direct Owner object writes, and uncontrolled state mutation. This **is a heuristic syntax-level negative control**, not a complete proof that the original Owner state or external systems cannot change.
- Reject symlinked/grafted/merged Git history, extra paths, identity mismatch, missing refs, and intermediate tampering in offline synthetic regression tests.

Output `Q_R1_U31_GIT_STATIC_COMPAT_CPU_OFFLINE_DEV` means **only Git-source non-regression with a limited AST scan**. Every result explicitly states: original real WSL evidence not read, producer custody not authenticated, no new Real World R1 attestation, no R2 migration.

## Independent Q verification needed for complete R1

A separately authorized LocalCodex/Q worktree with `/home/rinsa/evidence/i-u31/` must independently review unchanged original U31 source: Paper/Native raw log custody, original issuer ticket + Owner commit, S1 WAL terminal + rearm, S2 fresh L1 issuance, actual ACK/STOP/settlement and canonical WAL final 2 settled rows. Q has historical U31 PASS; R1's three added files do not replace or revise those originals. The live R1 Shadow is opt-in only and not installed in the original motor loop; source-static compatibility **cannot certify real-world R1 Shadow execution or reJOIN**.

Because the checker can only prove what the local Git objects contain, an attacker-controlled Git directory or caller-supplied commit hashes do not establish an authenticated producer. Confirm checkout provenance outside this tool.

**Explicit status:** `Q_R1_GIT_STATIC_CPU_OFFLINE` may become PASS after its CI and the pinned SHA audit; `Q_R1_REAL_ORIGINAL_SOURCE_REINSPECTION_PENDING / R2_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN` remain.


## Dedicated pinned-object GitHub Actions transaction (Q-only)

The standalone `.github/workflows/q-r1-pinned-git-objects.yml` job checks out the
exact Q audit PR head, fetches **only the immutable original I U31 and R1
branch refs** into separate audit-only Git refs, then asserts both Git refs
resolve to the explicit 40-character expected SHA before calling the Q
read-only inspector. The extra fetch writes only runner-local Git objects,
**never World, LLM, native, source evidence or actual R1 runtime state**.
It checks that the tracked checkout remains clean and records a clear
`Q_R1_ACTUAL_PINNED_GIT_OBJECTS_CPU_STATIC_PASS` marker only after audit.
If the I/R branches move, the pinned commit check fails closed.

This distinct job must succeed for an *actual* target-Git-object Q audit
claim; the earlier Q pytest synthetic fixtures alone are not sufficient.
Its positive result still cannot authenticate the WSL original producer or
supply permission to switch R2 or run another World.

## Independent Q runtime semantic probes (separate worktree)

The dedicated pinned-object Actions workflow also creates a disposable
**exact R1 commit worktree** under runner temporary storage. It runs Q-owned
`experiments/q_lane_r1_original_owner_runtime_probe_dev.py` against the
real R1 module and the *original* I/B synthetic Owner fixtures via the
read-only comparison API, without adding any test file to the R1 branch.

Independent Q assertions include A/B owner state+canonical file no-mutation,
Source/Schema signal coherence, Memory as remembered digest only, foreign
Self/Paper/retired Owner rejection, non-adopted model output exclusion,
and **cached MATCH revocation** if old Present's Need, Attention,
frame revision or registry revision differs after the initial comparison.

No actual WSL U31 original evidence or real inference/movement is available
to the runner. A successful Q runtime run means synthetic Original Owner
API compatibility on the pinned R1 code only; it is not a real World
post-S2 Shadow proof or R2 authorization.

## Q runtime adversarial discovery and repair handoff

Q pinned-R1 dynamic probes at earlier R1 SHA
`fd2c6862fcb1a7e71211a96d89c287ab3c689677`
independently reproduced **4 failures / 8 passes**: cached R1 MATCH
stayed live after modifying legacy Present's Need refs, Attention refs,
frame revision and registry revision (with original Native/Paper unchanged).
R1 implemented the bounded fail-closed fix in its own read-only
`r1_shadow_is_live` revalidator and added matching R1 regression tests.
Q preserves its own independent test file and pins the exact updated R1
`c4917e21a496107638b98f8b98c49bc60aa6d9aa`.

The Q probe must independently assert all four cases become stale on
that updated R1 code, while the complete R1 Owner/Physical/WAL suite and
Q's own Git/static auditor both stay green. A synthetic negative case does
not substitute for original U31 World/Gemma provenance.
