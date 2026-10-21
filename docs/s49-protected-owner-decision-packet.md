# S49 protected originals — independent owner decision packet (2026-10-21)

**Status: REQUEST FOR SCOPED OWNER DECISIONS, NOT AN OWNER APPROVAL.**
**DEV_ONLY / PROTECTED_SOURCE_CHANGE_NO_GO / W4_LIVE_NO_GO /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

This decision packet is **documentation only** in an isolated non-CI-triggering
review branch. It does not modify any protected originals, expected source
hashes, frozen evidence, grants, PR #634, PR #545 or main.

## Fixed provenance

- Original cleanup-only isolation base:
  `c8edb2d42ab31934feda5f30024e68eeb016e100`.
- Instrumented WSL2 DEV test candidate:
  `b8a51ac369a31399349d5401cf802304f63e522c`,
  branch `self/product-self-one-command-s49nativeos-independent-115641Z-0bb0826a`.
- Its preceding uninstrumented Linux CI baseline is
  `a76e1a71e5ecfd4158ccd3918c42f05c03100804`.
- #392 original S49 source authority; #633 SelfWorld/W4 handoff;
  #634 W4 Draft; #545 S Draft; #354 S18 architecture freeze.
- [WSL2 DEV report](https://github.com/rinsakamo/relay-self/issues/392#issuecomment-6315693951),
  [W4 handoff](https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6315694336),
  [prior technical audit](https://github.com/rinsakamo/relay-self/issues/392#issuecomment-6315872612),
  [exact candidate CI](https://github.com/rinsakamo/relay-self/actions/runs/39595835232).
- The WSL2 observer/JUnit/W3/SHA256 original evidence is stored in the
  user's WSL2 evidence root. GitHub's source and CI logs were read here, but
  **the local original evidence bundle was not fetched or recomputed here**.
  The independent OS claims remain LocalCodex-reported DEV findings.

## Decision A: four protected originals (four SEPARATE explicit decisions)

All expected values below come from the unchanged 19-item
`tests/test_self_world_stage_w4_lease.py::PROTECTED_BLOBS` manifest.
GitHub's current candidate blob IDs were independently fetched at exact HEAD.
**15 of the 19 protected originals are unchanged.**

| Protected original | Existing frozen expected Git blob | Exact candidate blob | Why candidate needs owner approval |
| --- | --- | --- | --- |
| `adapters/mineflayer/process_session.py` | `6eec8f80621c581d47154f7c76e72303e00c04f0` | `cf5a979d9da38acbe670973c11d7186ade49dbfe` | Node spawn custody, cancellation-safe startup cleanup, W3 incomplete seal and `abort_startup()` for the same original Node process |
| `adapters/mineflayer/s31a_real_server_ci.py` | `7ee3e95af66e1b981f72509a3dd661d79ef95744` | `04a4b20278844528082f9f5c731350418ac3553c` | Java spawn custody, startup failure termination/reap and settlement of the *same* stdout collector; bounded unconfirmed on non-cooperative collector |
| `adapters/mineflayer/s34_native_world_cognition_ci.py` | `eaecb117ad26059d6d2abb2c12bca61b2dce1f01` | `66728a9667734f4b7164de23f244a938a756dbdc` | Node session ownership continues through `_await_spawn`; failed/cancelled native spawn invokes `abort_startup` before ownership transfer |
| `adapters/mineflayer/s49_normal_session_real_ci.py` | `fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258` | `c48e22980d19c79e68c381566fb0edc09b346f1e` | Six-line fail-closed propagation of `startup_cleanup_unconfirmed` to CANCEL/FAIL/BLOCKED reports on top of *already-unadopted* cleanup-only S49 blob `b0b96c798593f0621ac63076929cc4ab287812e7` |

The owner should compare the full before/after source, not just the blob table.
Candidate diff: `c8edb2d42ab31934feda5f30024e68eeb016e100...b8a51ac369a31399349d5401cf802304f63e522c`.
For S49, review the **two-stage** change: historical frozen S49 →
cleanup-only candidate → six-line startup diagnostic addition. A clean 6-line
comparison by itself does **not** approve the earlier cleanup-only amendment.

For each file, record an explicit `APPROVE_SCOPED`/`REJECT`/
`NEEDS_CHANGE`/`UNDETERMINED` disposition with: authorized source owner,
reviewer identity, date, before/after SHA, scope and exclusions, independently
inspected evidence references, reasons, and accepted remaining risk.
Do not describe the technical reviewer or automated test author as an
independent owner unless the real owner's authority and independence are
established. Silence or a generic technical PASS is not approval.

## Decision B: repository-contracts path authority (separate from A)

The existing `.github/workflows/self-demo.yml` scans **all changes since**
`B0_PARENT=4edac0b139d2d49b0169ffaad7c5892bed7fa2d1`, not only the
latest commit. Comparing its `case "$path" in` allowlist with the real
candidate diff identifies **three non-allowlisted paths**:

1. `adapters/mineflayer/s31a_real_server_ci.py` (protected non-S owner)
2. `docs/s49-native-os-custody-dev.md` (new DEV instruction)
3. `tests/test_s49_native_os_custody.py` (new native OS test)

The workflow currently fails first on S31A, masking the two later misses.
The existing allowlist *does* already include
`adapters/mineflayer/process_session.py`,
`adapters/mineflayer/s34_native_world_cognition_ci.py` and the S49 path;
**allowlisted does not mean protected-source-approved**.

An authorized repository/workflow owner must separately review a minimal
path-policy change. Do not add a wildcard, disable the job, cherry-pick a
suppressed result, move source just to evade the check, or confuse a path
allowlist with a source SHA exception. This packet deliberately does NOT edit
the workflow.

## Decision C: W4 frozen-original assertion (separate from A and B)

`tests/test_self_world_stage_w4_lease.py::
test_s18_and_original_default_routes_are_blob_identical` uses 19 immutable
expected blobs and currently rejects candidate S49 first. W4 lease 3.11/3.12,
W4 prehost and FAST pytest all fail that one test; repository-contracts
separately rejects S31A. CI `full-regression` is SKIPPED.

It would be incorrect to globally rebaseline or rewrite the 19 historic
`PROTECTED_BLOBS` hashes just to green CI. If an authorized owner approves
an exception for a specific protected file, design a *versioned scoped
exception receipt* or another owner-approved test contract that preserves the
original historical SHA and distinguishes existing frozen baseline from
candidate application. The original W4 source/test authority must approve
any guard migration as its **own** change. Until that is done, the candidate
cannot be called CI-eligible for integration.

## Positive DEV evidence and limits

- LocalCodex reports WSL2 Windows/Ubuntu, real Java/Node inert subprocesses,
  4/4 Native OS tests on each Python 3.11/3.12, PID+starttime/wait/reap,
  Java single collector settlement, W3 startup incomplete sealing and a
  SIGTERM-resistant Node kill/reap negative control.
- Existing instrumented focused suite: 97 PASS on 3.11 and 97 PASS on 3.12
  (per LocalCodex report). GitHub exact-HEAD two focused jobs, lint and
  Mineflayer adapter are SUCCESS; other five jobs are guard FAIL, 10 SKIPPED.
- LocalCodex's separate 3.12 all-test partition reports 3426 PASS/one
  immutable-source assertion FAIL, 0 SKIP/ERROR, with collected/JUnit union
  equality. This is a DEV report, not a successful full GitHub workflow.
- Negative controls cover double cancellation, stale/unconfirmed waiter,
  integer exit code without confirmed reap, inconsistent wait/returncode,
  unresponsive Java collector and lost startup exception metadata.
- W3 `INCOMPLETE_UNQUALIFIED` with zero bytes is **correct failed-startup
  evidence**, not proof of normal adapter_started, full stdout, STOP ACK or
  valid Minecraft physical OUTCOME.

The actual cancellation injection is **after OS child creation but before
Process handle handoff to the owner**, not an exhaustive proof of every
internal CPython spawn instruction boundary or host crash/OS user isolation.

## Unverified/remaining risk and separation

1. Normal *successful* real Minecraft Java readiness → genuine
   Mineflayer `adapter_started` → native spawn → sole owner handoff has not
   been qualified by the inert Java/Node cancellation fixtures.
2. Original W4's single receiver, single Action issuer, lease scopes and
   World grant must be checked on an exact eligible, independently reviewed
   state. This is **not** a live World execution permission.
3. A non-cooperative Python waiter or collector may remain pending after
   a fail-closed diagnostic. Such a state is unconfirmed, not a clean exit.
4. Local 1479-file source/evidence digest and `/proc` third-party OS
   observations have not been independently re-read by this GitHub-only
   reviewer; if required as stronger qualification evidence, obtain the
   authentic read-only bundle and verify the byte hashes and source lineage.

## Required sequence for a future eligible candidate

1. Independent authorized owner decisions for **each** of four sources (A).
2. Repository/workflow owner decision on the three unallowlisted paths (B).
3. W4/test authority decision on historical blob protection and explicit
   scoped exceptions (C), retaining the frozen 19-blob provenance.
4. Apply ONLY the explicitly approved changes in a **new isolated branch and
   exact HEAD**. Run complete Python 3.11/3.12 focused, Ruff/Node, W4
   lease/prehost, all-tests, original guards, and independently read CI logs.
   No prior native DEV receipt can prove this new HEAD by transference.
5. Only after an eligible reviewed candidate, separately decide whether
   new real World DEV/QUALIFICATION run is authorized. Reconfirm one
   receiver, one issuer, no grant replay and all evidence provenance.

Until A/B/C have affirmative, concrete receipts:
**PROTECTED_SOURCE_CHANGE_NO_GO / W4_LIVE_NO_GO /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
