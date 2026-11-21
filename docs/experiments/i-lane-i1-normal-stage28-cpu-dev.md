# I Lane I1 — normal Stage28 original A/B SENSE → Present → CPU runtime (DEV)

Owner: Issue #1061 / Draft PR #1062; architecture #828 §27; B+D #1047; E #1054. The I branch is B #1050-anchored; do not wholesale merge E or override B original checkpoint, oxygen ownership, bounded GPU, source audit, or Physical ActionPort.

## Exact supported flow

1. **Offline rebootstrap** — `prepare_i1_original_schema_bootstrap` inspects both original restored PatternRegistries BEFORE copying/starting a real World. `install_i1_original_schema_bootstrap` installs only per-Self transient `SchemaSnapshot` config on the copied offline B Owner. If the original Self has no exploration pattern (as in Stage28b), the snapshot has no exploratory module; CPU food/oxygen/defense patterns remain, but **no EXPLORE Need, Question, Goal or Skill is injected**. A saved eligible exploration pattern can activate the matching exploratory config; unknown, foreign, mutated or duplicate pattern mappings HOLD. Zero canonical memory/registry/WAL writes.
2. **Native / source** — the existing `OwnedResidentPhysicalBridge(enable_sense=True)` owns original login/spawn/probe, historical native-session denylist, independent Paper checks, patched owned-oxygen reader and physical issuer. The optional SENSE dispatcher shares that SINGLE original `MineflayerProcessSession` decoder; the original correlated login probe seeds initial read-only SENSE with no claim of a second observation. Later passive native events or explicitly correlated `refresh_i1_read_only_sense` observations change native revisions. The refresh goes through original stdin `observe` and original bounded JSONL receive, not a new sensor process, GPU task, physical effect or target grant. An in-flight refresh blocks World-only cut; original Owner fence invalidates its result.
3. **Present** — B qualifies its original current Native and Paper receipt and associates E's optional current SENSE under the original `ResidentCognitiveWorkOwner.lock`: composite refs `(native, paper, mineflayer:<session>:<seq>)`. E's facts keep Native provenance; missing collision AABB/chunks remain UNKNOWN, never route-clearance or proof that the World is empty.
4. **CPU** — `prepare_i1_cpu_schema_probe` consumes the same current SENSE revision as B Present, runs the existing bounded CPU `cpu_schema_epoch` and `assemble_l1_select`; with no verified action catalog it yields only ESCALATE_L2/DEFER and does not perform an LLM POST, commit a Goal/Intent, write Memory or issue Actions.
5. **Normal Stage28 optional runner** — `--i1-original-cpu-sense --execute-once` is a **deliberate DEV opt-in** to `experiments.stage28c2b_real_recovered_rejoin_dev`. After the original independent A/B JOIN/PRESENT→Paper Body link and old Body acceptance, it calls the same original Native observation reader twice per Self, obtains fresh independently qualified Paper tick/link receipts per cognitive epoch and stores source-bound **read-only CPU receipts** in the existing original trial report. No separate runner, scheduler or persistence owner. The mode refuses simultaneous `on_reconnected` (real L1/Gemma) attachment until explicitly reviewed.
6. **Classification** — original Stage28 default remains unchanged. With I1 enabled the report is `I1_ORIGINAL_CPU_SENSE_CAPTURED_INDEPENDENT_AUDIT_PENDING`, deliberately NOT the old Stage28 audited class. The existing Stage28 independent auditor must not be presented as an I1 source/CPU auditor. A new independent raw-audit qualification is a separate gate.

## Evidence states

- `I1_NORMAL_STAGE28_CPU_OFFLINE_DEV_PASS` requires exact-HEAD pytest/Ruff/repository-contracts/Mineflayer/Paper checks, including original restored registry no-EXPLORE rebootstrap, offline A/B separate registration, two independently versioned native observations per Self, original B Present/CPU path, stale Native/session/epoch / forged request rejection, read-only stdout decoder, Owner fence and zero persistence mutation.
- `I1_REAL_WORLD_HOLD` until one isolated actual Paper 1.21.8 execution, genuine native/Paper raw source captures and independent review of newly added `i1_cpu_epochs` and requests. **Do not promote from CI**. `i1_normal_continuous_native_observed` is only the runner's claim until independently audited. A seed or one single Body snapshot is NOT sufficient to prove ongoing updates.
- `L1/GEMMA_NOT_RUN`, `PHYSICAL_ACTION_NOT_ISSUED`, `C1_LEARNING_NOT_RUN`, `QUAL_NO_GO`, `SCIENCE_NOT_RUN`.

## I1 native dependencies: required **before** Paper startup

The single isolated real-World attempt at exact HEAD
`e1b779812271df9b29be5315af441439b1db226d` correctly remained
`I1_REAL_WORLD_HOLD`: the worktree's borrowed `node_modules` was a
**symlink**, which the Node `oxygen_owner_patch.mjs` inspector rejected
only after Paper was already running. Its SHA/capture report does not
attest any A/B Native login, CPU epoch, outbound command or successful
independent audit. Paper exited cleanly; do not relabel or overwrite
those original HOLD files.

New `require_i1_native_preflight` checks **all** worktree-local path
ancestors (`node_modules`, `mineflayer`, `lib`, `plugins`), the exact
version and regular files, then executes the **same original Node**
`oxygen_owner_patch.mjs --inspect-only` validator that gates the Native
bridge. It compares the reported original `entities.js` SHA256 with
the locally read file. It ALSO does one read-only Node `require('mineflayer')`
from that exact worktree, checks the resolved entry remains inside the
owned Mineflayer package and checks for the `createBot` API **without
calling it**. This catches absent or broken entrypoints and missing
transitive npm dependencies, which previously might have failed only
after Paper had started. The fixed `createBot` probe cannot create a
game bot, and no Native bridge, socket or Minecraft World is started.
It never installs dependencies, patches code or starts Paper/Native/Gemma;
any missing file, symlink, unowned oxygen patch, version discrepancy,
malformed Node result, digest mismatch, incomplete package import or
unexpected module API is **PRE_WORLD_HOLD**.

### Known Node 22 punycode warning: narrowly classified, never suppressed

A later real WSL/Node 22.22.2 I1 **pre-World** attempt at HEAD
`22f083865dad9d31c95325af4b67bd35ebc13a85` reported
`I1_NATIVE_DEPENDENCY_PRE_WORLD_HOLD` because `require('mineflayer')`
completed successfully yet emitted the Node runtime's native
`[DEP0040] DeprecationWarning` for `punycode` to **stderr**. That
execution created **zero** new Worlds, made **zero** Gemma/Physical
calls and did not run an independent auditor. No old HOLD receipt is
promoted by the following fix.

I1 now qualifies **only** the exact two-line Node 22
`(node:<PID>) [DEP0040] DeprecationWarning: The \`punycode\` module is deprecated...`
diagnostic including Node's standard `--trace-deprecation` hint
and its precise punctuation. A genuine empty stderr also qualifies;
nonzero exit, unexpected stdout, any *other* warning (including
additional or duplicated DEP0040), error stack, ANSI, extra log line,
alternate wording or oversized stderr **remains PRE_WORLD_HOLD**.
No `--no-warnings`, `NODE_NO_WARNINGS`, muted logger, patched
dependency or dependency version change is introduced.

The verdict retains the exact original Node warning text and SHA256 in
the I1 preflight receipt (`i1_native_preflight.node_module_stderr_raw`
and `node_module_stderr_sha256` in terminal real-run evidence). I1
inspect-only explicitly **reprints the original warning to stderr**
alongside its classification and digest, and stdout reports
`node_warning=DEP0040`. This is narrowly recognizing a known
runtime diagnostic rather than silently accepting arbitrary stderr.
Keep the console/terminal capture with the source evidence; only
a separate new isolated trial can change the real-World status.

The original worktree must contain **genuine regular files** installed
under `adapters/mineflayer/node_modules`; copying a symlink or setting
`NODE_PATH` does not qualify. An operator may install the exact
package-lock dependencies with `npm ci --prefix adapters/mineflayer`
and, only if the regular installed source is the exact unmodified
vulnerable version, explicitly apply the already reviewed Stage24d
backport with `node adapters/mineflayer/oxygen_owner_patch.mjs --apply`.
Neither action is automatic. Verify read-only first with:

```bash
node adapters/mineflayer/oxygen_owner_patch.mjs --inspect-only
python -m experiments.stage28c2b_real_recovered_rejoin_dev \
  --generation "$GENERATION" --restored "$RESTORED" \
  --stage28b-evidence "$STAGE28B_EVIDENCE" \
  --paper-jar "$PAPER_JAR" --plugin-jar "$PLUGIN_JAR" \
  --eula-accepted --i1-original-cpu-sense --inspect-only
```

The second command now explicitly accepts the I1 flag in inspect-only
mode; **it refuses** a World grant, execution/evidence directories or
any Paper/Native startup. It emits
`I1_NATIVE_DEPENDENCIES_PRE_WORLD_PASS` with the exact source SHA256
only if the worktree passes. The **direct Python runner** repeats the
same check before its first execution-copy creation; a successful
CLI-only check is never taken as authority after source changes.
Keep old Stage28 default mode unchanged. Even after this preflight
PASS, the previously failed real-World attempt stays HOLD; only a
separately initiated fresh isolation can generate a new trial result.

## Existing local DEV invocation (operator LocalCodex only)

Preserve the previously approved Minecraft EULA agreement and ongoing isolated real-World DEV consent. The runner intentionally still takes the explicit CLI flags; no new human approval prompt is necessary. Find and hash-verify the pinned **actual** Stage28b source, restored fork and Paper/plugin builds; never invent paths or hashes. With those established, invoke once:

```bash
python -m experiments.stage28c2b_real_recovered_rejoin_dev \
  --generation "$GENERATION" --restored "$RESTORED" \
  --stage28b-evidence "$STAGE28B_EVIDENCE" \
  --paper-jar "$PAPER_JAR" --plugin-jar "$PLUGIN_JAR" \
  --execution-dir "$NEW_ISOLATED_WORLD" --evidence-dir "$NEW_EVIDENCE_DIR" \
  --eula-accepted --real-world-dev-grant \
  --i1-original-cpu-sense --execute-once
```

The new execution and evidence paths must be absent/fresh. No autonomous retries. Inspect `stage28c2b-recovered-world-result.json`, original independent native raw JSONL, actual owned Paper log, original B source qualification for each readout, per-self revision advancement (2 each), Original Owner/Registry/retired WAL, cleanup and every HOLD receipt. If any source is unavailable, stop at PRE_WORLD_HOLD and report that clearly. This mode intentionally **does not start llama-server or make a model POST**; future I2/I3 integration must reuse the one original owned llama-server, not add a second GPU lane.

## Separate I1 independent audit (implemented; real World not yet run)

**Run only after** the original Stage28 opt-in runner has exited and written a
terminal `I1_ORIGINAL_CPU_SENSE_CAPTURED_INDEPENDENT_AUDIT_PENDING` report.
The original Stage28 audit command rejects this I1 classification by default.
Use the I1-specific verifier in a **fresh process**, with verified actual
paths rather than guessed/stale evidence:

```bash
python -m experiments.i_lane_i1_independent_cpu_audit_dev \
  --result "$NEW_EVIDENCE_DIR/stage28c2b-recovered-world-result.json" \
  --generation "$GENERATION" --restored "$RESTORED" \
  --stage28b-evidence "$STAGE28B_EVIDENCE" \
  --execution-dir "$NEW_ISOLATED_WORLD"
```

The verifier first reruns the established Stage28 owner/World lineage,
historical Native and Paper source, physical WAL and clean-retirement checks
with an explicit I1-only base classification (never the old Stage28 promoted
classification). It then independently re-parses the original Native JSONL:
the initial admission probe plus exactly **two new request-correlated probes**
per Self, with strictly increasing Native seq and unique request IDs.
Every admitted CPU epoch must match the actual Native request ID,
source provenance and composite source revision.

**New original stdin audit:** When I1 is enabled, the same original
`MineflayerProcessSession` journals the exact outbound JSONL *after*
`stdin.drain()`, independently of its existing raw stdout recorder. The
frozen `native-commands-Relay{A,B}-<native-session>.jsonl` files and their
SHA256 hashes (`raw_native_command_file_sha256` in the terminal report)
must contain **exactly 3 read-only `observe` commands per Self**: the
original `p0d-rejoin` admission request and the two distinct
`i1-original-sense` requests. The verifier checks exact ID and order
against all three original Native stdout probe messages. Extra effects,
forged or missing requests, absent transcript files, bad hashes, and
partially written transcripts are HOLD. Command journaling is an
independent original-owner stdin *process* witness, not proof that
Minecraft acted; original Native stdout and owned Paper ACKs are still
required. A failed `stdin.drain` is not journaled as successfully
delivered; a journal-write failure after drain is an unresolved attempt,
not a success.

### I1 Native read-only request correlation vs passive E SENSE

A later **real single-World** I1 DEV trial at old HEAD
`afd1106724e1b472efaf4626444612ab23a20b16` passed PRE_WORLD and
recorded the two distinct `i1-original-sense-...` stdin requests and
matching original Native stdout probe replies **per Self**, but the
Runner HOLDed on `read-only Native request correlation lost before CPU
adoption` without a terminal CPU ledger. This is **not** BD1bSourceHold,
and no BD1b failure-time Paper file should be expected for that attempt.
Actual row values were not preserved, so do not assert confirmed unique
cause or promote its partial raw stdout to a CPU assessment.

One concrete original-receive race is now addressed: normal passive
E SENSE updates `bridge._sense` on unsolicited `move/entities` messages,
which have **no request_id**, after an explicitly correlated read-only
Native `probe` reply was verified. The I1 loop previously consumed the
latest passive `current_sense` instead of the response to its own
`observe` request. New **I1-only** per-Self ephemeral
`_i1_correlated_sense` on the **same original resident bridge/lock**
retains exactly the reply verified through the original session
`_receive_matched`; passive SENSE continues normally and has not
changed. The separate readback
`current_i1_correlated_sense` independently checks the still-current
original Native/Paper/Owner scope and a short TTL, exact I1
32-hex request ID, probe kind, same session, source revision and
non-future Native seq. It is cleared on failed login, quarantine and
logout. It is not a separate owner, memory, World witness or physical
Action grant.

The normal original B Present → CoverageInquiry → I0 CPU → I1 CPU
read-only path receives an **explicit** correlated-I1 mode, checks
the *same* pinned request-response revision both before and after
projection, and compares each CPU row with the **exact verified
`SenseFrame` returned by that round's original Native refresh**
(A/B request ID, seq, provenance and revision all must match).
Merely starting with `i1-original-sense-` does **not** authorize
adoption. In no-refresh/normal E SENSE mode the previous passive
behavior is unchanged. CPU evidence is emitted only after the
original B/Paper, Native and Schema fences agree. A correlation HOLD
can retain a diagnostic-only mismatch record; it never creates a
completed CPU ledger or independent-audit eligibility.

Synthetic regression exercises two explicit matched A/B probes each
with a later higher-seq unsolicited passive event before CPU, plus
passive-only, expired, foreign session/scope/request, future seq and
Owner retirement negatives. All synthetic/offline results remain
distinct from the historical real World HOLD and any future
separate independent real-source audit.

### I1 BD1b Original Owner source readback (2026-11-21 follow-up)

A new isolated World at older HEAD `1a0581f9b95a1beacc85dceff384e5ab4e8e847d`
passed preflight but HOLDed during the first I1 Native refresh with
`BD1bSourceHold: original A/B native or Paper link mismatch`. The
initial Paper link's SHA256 exactly matched the owned stdout's 7,221-byte
completed ACK-line prefix, while BD1b's pre-existing Owner source path
`build_bd1b_owner_source()` rehashed the **entire currently read raw log**
and compared that to `link.paper_log_sha256`. The mismatch is a
well-supported potential cause; the original failing predicate and exact
live raw bytes were not captured, so do not claim confirmed exclusive
causation. The new World attempt, partial Native traces, and manifest
remain `I1_REAL_WORLD_HOLD` without any completed CPU epochs or
independent audit.

The follow-up fix keeps BD1b's **default exact full-raw SHA fence**.
Only an explicit `i1_complete_paper_prefix=True` on the original I1
readout/Present/coverage/Schema call chain makes BD1b re-read the same
**owned live Paper Popen** and derive the **last actual LF-terminated
prefix**, requiring the link's actual main-thread ACK marker to be
inside that completed source. The recomputed original SHA must equal
the independent producer's linked SHA; B does not trust a caller-supplied
digest or normalize prompt bytes. If a new complete line or ACK has
appeared, currentness changes and the old link **HOLDs** until new
producer linkage. Foreign session, swapped Self, stale Native, changed
actor/nonce or incomplete ACK also HOLD. No plugin/Paper stdout mutation,
new Owner, model, physical Action or auditor relaxation is permitted.

For a new I1 BD1b HOLD, the source reader now attaches the exact
**single owned-Paper read() byte string** and its original full-log /
completed-prefix SHA256 values to the escaping exception. Only the
**original Stage28 Runner** may freeze that attached read into the
exclusive new artifact
`i1-bd1b-failure-time-owned-paper-readback.log`, with SHA256, byte
count, original session, A/B link SHA and phase in the existing terminal
HOLD report. It does not reread the growing Paper log after the
failure or use this diagnostic to authorize cognition, Paper/PID trust,
an independent audit or a classification change. Failure to freeze
is explicitly reported as diagnostic uncertainty; no old result is
promoted by the frozen bytes. Ordinary B does not attach/freeze these
I1-only diagnostics.

Any future fresh isolated World run must retain the failed readback
and the remaining original sources if BD1b still HOLDs; do not
substitute a later post-STOP Paper log for failure-time evidence.
This fix is CPU/offline only until an entirely new actual trial passes
the unchanged independent I1 auditor. Historic failures cannot be
reclassified or rewritten.

### I1 original Paper console prompt / complete-line capture contract

The **first actual independent I1 audit** after a successful single isolated
Paper A/B trial at old HEAD `9c32cec3b311a044658c470d061f7aa0760875da`
correctly HOLDed: its two captured CPU `paper_log_sha256` values were
genuine byte prefixes of the immutable owned Paper stdout, **but included a
non-newline-terminated console prompt after a valid Paper ACK**. They were
not a complete line-boundary source and the independent auditor rejected
them. The old trial and its original evidence remain `I1_REAL_WORLD_HOLD`,
regardless of later software fixes; no retrospective promotion, artifact
rewriting, or re-audit-as-success.

I1's new **opt-in source projection** now makes its initial A/B Paper body
link and each subsequent read-only CPU epoch hash only the exact original
`read_owned_log()` byte prefix ending at its **last real LF byte**, and
requires that the newly requested Paper ACK marker be present *within that
complete prefix*. The source projection never inserts a newline, repairs
an ACK, changes an old byte, trusts a detached/global log, or consumes a
trailing partial line as evidence. If the requested ACK is only in the
partial tail, or there are no complete lines, capture HOLDs. Full raw
console output **including the trailing prompt** stays attached to the
original owned Paper stdout and is frozen as the pre-STOP source; the
independent auditor still recomputes original complete-line prefix SHA256
from its independently read frozen log. Default (non-I1) Stage28 behavior
is unchanged.

Adversarial offline tests emulate two real ACK-bound CPU epochs with
`> ` prompt bytes observed during the first read and still retained when
the second ACK arrives. They prove canonical source digests pass an
unchanged strict independent auditor while the old byte-prefix-in-prompt
SHA **still HOLDs**. This is CPU/offline evidence only, not an attestation
of the past real World or a license to repeat/relax an independent audit.

For each epoch, it recomputes SHA256 of a line-complete **prefix** of the
immutable pre-STOP owned Paper log, verifies the plugin-owned ACK bytes and
nonce/tick, and checks that the two same-original Paper actors were still
present. Paper and Native clocks are **never compared numerically**. Finally,
it reconstructs the original saved rev-0 PatternRegistry/Intent, replays the
CPU Schema from the actual Native Body, and checks Goal IDs, fixed bounded
ESCALATE_L2/DEFER choices, and the absence of invented exploration.
An altered ACK, a forged or duplicate request ID, a changed Native raw
observation, an invented Goal/Action, an absent second epoch, or a stale
Paper prefix is HOLD. The verifier does not send World commands, modify
source files or call a model.

**Only the external independent verdict**
`I1_ORIGINAL_A_B_NATIVE_PAPER_CPU_SOURCE_AUDITED_DEV` qualifies that new
DEV capture. GitHub CI proves the verifier's synthetic tests only; it is
**not** a real World result. The new audit is specific to the historically
pinned original Stage28b A/B Self (which has no saved exploration pattern).
Expanded PatternRegistry variants require a separate independently testable
audit contract. Never elevate this DEV result to QUAL/SCIENCE.

## Next work

- One isolated LocalCodex real Paper+Native DEV trial using the existing
  standing EULA and World DEV authorization, then the new independent audit;
  source mismatch must terminate PRE_WORLD_HOLD with **no automatic retry**
- Verify the original Paper output prefix/ACK and original Native response
  correlation against the real source; if stale, do not borrow a new World
  epoch or old decision to make it pass
- Beyond the two-sample observation-only DEV loop, build an original-owner
  autonomous CPU cadence and complete D Question ADOPT, A motor/bounded L1,
  C learning after terminal Intent and checkpoint integration separately
