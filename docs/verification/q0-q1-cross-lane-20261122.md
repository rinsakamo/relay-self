
# Q0/Q1 — independent cross-lane verification (DEV)

Snapshot: 2026-11-22 JST. Q Issue #1088; parent #828; integration #1061.
Main basis for the standalone Q branch: **4348a614900c1d0828581a8eec2c523ba5ae237f**.
All listed PRs are unmerged experimental branches; their code is **not** in main.

## Q0 exact PR HEAD and CI

| Lane / PR | Inspected GitHub HEAD | CI / independent scope |
|---|---|---|
| A #1059 | 666a5dc4331cabe935d7555d9a36940c2330323b | [44744855418](https://github.com/rinsakamo/relay-self/actions/runs/44744855418) reported 5/5; real 5m World trial used older 7198be44. Q has not independently read trial originals |
| B #1050 | 31c6684c84d2d5245608938c56de7f3ffb5ab8d9 | [44922610433](https://github.com/rinsakamo/relay-self/actions/runs/44922610433) success; true Question ADOPT and durable owner boundary remain separate |
| B reJOIN #1079 | 9edb07f22f737f2f2eac79d885174a0654bff48 | [44922679876](https://github.com/rinsakamo/relay-self/actions/runs/44922679876) success; synthetic; new Composite Source Receipt HOLD |
| C #1060 | ec3922a9e6727a8a59cdfde3df1d308c128ba2f1 | [44870546165](https://github.com/rinsakamo/relay-self/actions/runs/44870546165) reported 5/5; real T1/T2 and C1 adoption HOLD |
| D #1043 | 0eb3dc88b5cfa6326b3666642c95077c178a35c6 | [44715118527](https://github.com/rinsakamo/relay-self/actions/runs/44715118527) success; inert handoff only |
| E #1053 | b3524a6a37b711747b07b962d29a762dfdaccc36 | [44858592593](https://github.com/rinsakamo/relay-self/actions/runs/44858592593) reported 5/5; real bounded Owner/Present link HOLD |
| I1 #1062 | a69f4304c2d7e4ec6807d83b0857a9672b0b49f2 | [44914269595](https://github.com/rinsakamo/relay-self/actions/runs/44914269595) success; I1 original independent World audit *reported*, not newly repeated by Q |
| I2 #1080 | 33c5a5d970bc2190b88230ba1009e1150e589900 | [44923222497](https://github.com/rinsakamo/relay-self/actions/runs/44923222497) verified five successful jobs; controlled CPU provider, not real Gemma |
| I4a #1067 | 72c1b09e1b6039f894b0d42f1db29a575239d44e | [44915987448](https://github.com/rinsakamo/relay-self/actions/runs/44915987448) success; synthetic S1/S2, real SkillRun HOLD |
| I1+C+I4a #1076 | 292622edb2de99aaa0d5c3095f4fcbb327fc6341 | [44924564231](https://github.com/rinsakamo/relay-self/actions/runs/44924564231): **lint FAIL (I001), pytest pending when first inspected**; preceding a710d653 [44923902340](https://github.com/rinsakamo/relay-self/actions/runs/44923902340) 5/5 PASS; PRE_WORLD_NO_GO remains |

A green CI is not original evidence, real World execution, autonomous closed-loop
qualification or independent source attestation. The private WSL original archives
have not been made available through this GitHub connection. Q records **HOLD**
for new independent source qualifications pending independently provided originals.

## Q0-A #1076: reproduced historic failures, then verified upstream fix

1. **No-motion uncertain MOVE: HOLD / contract versus fixture or safety defect.**
   The failing test is
   tests/test_p0d_resident_move_issuer_dev.py::test_original_move_uncertain_keeps_wal_and_blocks_a_retirement[no-motion].
   The fixture resets ScriptedNative.x to 1.0 after a valid set_control ACK;
   the source contract supports terminal NATIVE_MOVE_NO_NET_DISPLACEMENT after
   qualified STOP/settling. The test expects PhysicalMoveRefusal or
   PhysicalJournalError but neither occurs. Whether this is a fixture that
   confuses valid no-net terminal with unresolved motion, or a true unsafe
   terminal/WAL release, is **UNRESOLVED at historic 5aa94d39**, before the focused fix.
   Do NOT just delete the negative assertion or weaken an issuer fence.
   **Owner: I and A.** Fixed in new a710d653 with separate settled-no-net and wrong-STOP tests; independently test validated STOP,
   all settlement observations and WAL close vs actual ambiguous/failed STOP.
2. **Receipt timing API incompatibility: confirmed.**
   tests/test_stage24b_resident_real_l1_integration_dev.py::
   test_l1_selected_move_can_have_terminal_no_net_outcome_without_fake_success
   raised AttributeError at 5aa94d39: the caller experiments/stage24b_real_l1_move_dev.py
   accessed receipt.native_start_dispatch_monotonic_ns, absent from the then-current
   ResidentMoveDevReceipt in experiments/cognitive_physical_move_issue_dev.py.
   **Category: producer/consumer API incompatibility on old HEAD**, not a model failure.
   **Owner: I.** Resolved at a710d653: the sole original Native issuer records
   the actual monotonic dispatch time in the typed receipt; Stage24b validates
   its chronology. No synthetic caller-supplied clock value was substituted.

The previous 496 test failures, 14 collection errors and the 2,641 PASS / 2 FAIL
run are historical. **At HEAD a710d653, exact-HEAD CI 44923902340 succeeds
5/5**. Commit diff touches only the original MOVE issuer receipt, its
Stage24b reader and two test files; it adds real sender-side chronology and
separates no-net settled outcome from ambiguous STOP. No owner/physical WAL
fence relaxation was observed in this diff. It is still a code-stage success:
**zero integrated real World launches/Gemma POST, I4A_PRE_WORLD_NO_GO**.


### Next concurrent I head: 292622edb2de (checked 2026-11-22 01:28 JST)

A further one-commit move from a710d653 adds only a dedicated read-only
I1+C+I4a PRE_WORLD source-hash inventory, its negative tests and a runbook.
The new command always returns exit 2, never creates the World directory,
never issues a physical action or submits a model POST. It explicitly lists
missing authentic S1/S2 WAL, Native/Paper and GPU/Owner boundaries. This is
**not an executable real-World runner**.

[Exact-head CI 44924564231](https://github.com/rinsakamo/relay-self/actions/runs/44924564231)
has a **confirmed lint failure**: Ruff I001 unsorted imports in
tests/test_i_lane_i1_c_i4a_preworld_dev.py line 2. At this inspection moment
pytest was still running. **Classification: I-branch test/import fixture,
owner I.** Minimum fix is import ordering only; do not touch protected
WAL/source/Owner/physical conditions. All of this is separate from the
successful prior a710d653 CI. No new qualification PASS is inferred.

## Q0-A #1080 Source mismatch diagnosis

Historical **2,227 PASS / 25 FAIL** concentrated on BD1bSourceHold; this is
not the current verdict. Latest exact-head five-job CI passed. Original B
build_bd1b_owner_source still requires the actual Original Owner/resident lock,
exact A/B roster and distinct actor/native sessions, owned Paper PID/boot,
Paper ACK/complete-line prefix SHA, original current Native request/session and
seq, owner observed World epoch, source/retirement flags, and a requalified
presence timeline. A changed complete Paper line forces a new link; a partial
line cannot qualify as an ACK. Native and Paper clocks are not comparable.

Original shared L1 on #1080 additionally compares the exact attached
ResidentLlamaInferenceLane, ticket Self/request/work ref/epoch/session/backend,
original current Owner/Schema/revision, idle GPU slot and one-time result
consumption. Original no-PATTERN source may yield no exploration Goal.
Recomputed local request/source hashes are change detectors **not authenticators**.
**Classification: historical fixture/source mismatch not reproducible from
latest passing CI, but real Source and restored Schema still independent HOLD.**
Owners B (Source) / I2 (fixture and handoff); never relax BD1bSourceHold.

## Q0-B cross-lane compatibility matrix

| Shared file / contract | Dependencies | Conflict / risk | Minimal fix and owner | Q independent status |
|---|---|---|---|---|
| Mineflayer process_session, Native probe and SENSE revision | B/E/I1/I2 | duplicated source authority; old request/seq or stale passive SENSE | Keep original decoder and exact-current source/Scope; **B/I/E** | I1 source auditor exists on #1062; Q1 raw link checks only |
| Resident Owner, source, Present and Registry | B/D/E/I1/I2 | divergent branch signatures and alternative Owner bootstraps | Same original Owner + lock and rechecks, no new cognition owner; **B/I** | CPU tests pass, real restoration HOLD |
| Paper ACK/prefix and World clocks | B/I1/I2 | growing complete log versus frozen link; Paper vs Native time | Relink producer to complete original ACK and do not equate clocks; **B/I** | Q1 synthetic ACK negative; original audit not rerun |
| Physical ActionPort/STOP/Supervisor/WAL | A/C/I4a/I | no-net vs uncertain action/retirement ambiguity | Keep PREPARED quarantine and a single issuer; **I/A** | historic failure corrected in a710d653; real World HOLD |
| ResidentMoveDevReceipt | A/I | caller demands absent monotonic dispatch field | Owner-side actual timestamp or remove unsupported field; **I** | API fixed in a710d653, exact CI 5/5; real capture HOLD |
| C1/T1/T2/SkillRun original WAL | C/I4a/I | stale T1 evidence, incorrect source admission | Separate same-Intent vs new-task source, no success promotion; **C/I** | synthetic test only, durable S1 anchor HOLD |
| Exploration Question candidate versus ADOPT and ticket | B/D/I2 | fake target, duplicate ADOPT or reused GPU ticket | B-owned single transaction; no candidate adoption by Q; **B/D/I2** | #1080 offline, original readback HOLD |
| Checkpointed generation and historical S1 | B/I4a/I | recomputed action ID + SHA masquerades as original | Trustworthy independent prior Owner boundary/anchor; **B/I** | Q1 hash pin cannot authenticate both attacker-owned copies |

## Q1 limited independent evidence gate

The Q1 module also provides build_untrusted_file_inventory: it reads file bytes,
returns deterministic role/path/size/SHA metadata and writes nothing. That
inventory is **self-calculated and unauthenticated**; a modified WAL plus
recomputed inventory cannot pass independently held earlier pins.

The new experiments/q_lane_evidence_audit_dev.py checks external pins versus
captured original byte hashes (not merely self-declared SHA), exact HEAD /
Self / Owner / World / native session / checkpoint generation, original
Native observe request and ordered seq, complete Paper ACK versus nonce/tick,
a scoped MOVE WAL terminal, optional Question ADOPT/ticket records, missing,
swapped, truncated and symlink evidence. It is read-only.

Synthetic Question and ticket JSONL used by Q1 tests **are not** the original
B persistence or original resident GPU evidence schema. The original I1
independent audit, Stage28 checkpoint recovery auditor, B question verifier
and I4a full historical WAL auditor must still be run against their exact
branches and separately archived originals.

**Never label this gate cryptographic authentication.** Its result is only
Q1_EXTERNAL_PINS_AND_SOURCE_LINKS_CONSISTENT_DEV_ONLY, with explicit
external_pin_origin_authenticated=false, real_world_attested=false and
owner_checkpoint_semantics_attested=false. If the alleged external pins can
also be rewritten by an adversary, both copies can be forged. A secure
earlier source/Owner anchor remains required.

Q overall: **DEV_ONLY / latest #1076 CI PASS, HOLD on real integrated source evidence /
QUAL_NO_GO / SCIENCE_NOT_RUN.**


## Q1b continuation — exact verified incident / source gate (2026-11-22 JST)

The latest independently read I #1076 exact HEAD at this inspection is
ca2be4b500436dc25646d3f5511f5f6d7cd1b983. Its exact-head
[CI #44926065481](https://github.com/rinsakamo/relay-self/actions/runs/44926065481)
is **5/5 SUCCESS with pytest 2,654 PASS**. The additive PRE_WORLD scanner
is *not* an executing original real-World runner: S1/S2 real causality and
trusted checkpoint source continue to HOLD.

Q independently discovered catastrophic intermediate I commit 87d0e68e,
which dropped 598 of 601 tracked files (156,846 deleted lines). Recovery
commit ca2be4b5 has **601/601 historical paths restored**, no added/deleted
paths against prior intact 959264a2, and exactly three changed original
PRE_WORLD files. The Q JSON evidence for these exact Git trees is
[q1b-i-pr1076-destructive-head-audit.json](./q1b-i-pr1076-destructive-head-audit.json).
Do not erase the destructive commit or treat intermediate CI as success.

Q1b added two separate read-only auditors:

- experiments/q_lane_tree_integrity_dev.py: strict additive historical Git
  file preservation, exact HEAD/ancestor and protected-file mode check.
- experiments/q_lane_s1_boundary_audit_dev.py: separately provided pre-S2
  anchor SHA and exact historical S1 WAL+checkpoint bytes, plus S2 WAL append
  and unchanged S1 Action prefix. Fails on foreign owner/scope, replay,
  PREPARED, changed S1 history, missing artifacts and forged checksum.
  **No temporal/origin authentication is inferred from a caller-supplied
  digest**. Original Stage28 checkpoint decoder and physical WAL owner remain
  authoritative; full original evidence has not been read by Q.

Q1 original byte-reader was also hardened with O_NOFOLLOW on every path
component and directory-fd traversal against parent-symlink swap races.
The hostile tests include swapping a symlink ancestor after a precheck,
FIFO original evidence, duplicate JSON keys and synchronized WAL+anchor
tamper that demonstrates false authentication risk.

[Q exact-HEAD run #44926505232](https://github.com/rinsakamo/relay-self/actions/runs/44926505232)
at code HEAD 19851f42fe34d80f1a3f7bd770e032a9c2965cb4:
**4/4 SUCCESS, pytest 997 PASS**, lint, repository contracts and Mineflayer
adapter passed. Main's CI does not include a separate Paper witness job.
The new Q1b verification is **CPU_OFFLINE_DEV only**.

**Current Q verdict:**
- CODE/GIT TREE incident: resolved on I head ca2be4b5; no product bypass;
- Q1/Q1b tests: passed exact HEAD, no real World/Gemma startup;
- Trusted pre-S2 S1 anchor / authenticated owner continuity: **HOLD**;
- Real S1→S2 Paper/Native and independent I4a original source: **HOLD**;
- QUAL_NO_GO / SCIENCE_NOT_RUN.
