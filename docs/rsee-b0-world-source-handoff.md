# R Lane B0 — RSEE reuse, original-byte audit and nonissued WAIT handoff (2026-10-14)

Authority: R #575, S #537 / Draft #545, RSEE Golden #588, R6 review-only #610, V #619 / V2 #625. **This is an R-owned runbook/contract, not a new launcher, source attestation, live authorization, or V scientific admission.** The existing R6 S9 audit source and frozen S9 receipts remain unchanged.

## Frozen reference coordinates (do not silently promote)

- S historical B0 two-epoch **producing** HEAD: `2c2659010e79529f897da5c75b1974b3bd3bb57a`, session `b8b9918e-07dd-43ce-b923-b5fa282ac266`, S original operator report [#6156001226](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6156001226). Four issued S50 MOVE; two issued S51 EAT; two M0 meal credits, a single retained ledger and two next-L0 decisions are *operator reported*, not original bytes independently verified by this GitHub review.
- Current prospective S owner nonforcing HEAD: `6f95c34918fbe29fea56bc7284e94c4edce21aff`; #545 exact-head CI `38482920207` completed success. **No ground2observe physical run / no reusable permit.**
- Existing Golden RSEE #588 exact `34820f6bf391c77f325d7c29d3b779a33e3ca835`, Minecraft 1.21.8, Java21, Node22, Mineflayer4.39.0, shared RSEE Python. S's `b0_rsee.verify_b0_rsee` imports only the nine pinned original RSEE source blobs and checks 26-file stopped World snapshot, jar, manifest, initial evidence and Node runtime. Do not copy validators or bootstrap a second World.
- R6 #610 exact historical reviewer HEAD `b5ca2afc0e2cb8b419e7d2f18afc3e24f991ad4a` applies to **S9**, not to B0; its on-host S9 57/57 readback cannot be transferred to B0.

## R1: B0 original-byte reconciliation — independent host action needed

Reported frozen host root: `/home/rinsa/evidence/relay-self-b0-ground2-20261014-2c26590-once`. The GitHub reviewer cannot read files from this WSL2 path; until actual R-host readback, **B0_R_ORIGINAL_BYTES_NOT_READ**. Refuse to say R independently audited it on the basis of the S report alone.

Expected comparands **from S operator**, not R measurements:

| Original | Reported SHA256 |
| --- | --- |
| `physical.json` | `4c87c8815e170ea827713105c8ad2ea291cde622878e444c89dac6925e9b1d55` |
| `physical.native.jsonl` | `0c99ae8b7583c7709b751784802186243d383708c9589abf15b892c34a514e81` |
| `physical.commands.jsonl` | `29a00089a9dcb81cf77c3ab28a2dcfc3f4e5caa4017eaea852510ca00328e6f0` |
| `minecraft.log` | `b4814335fefa6f90dc4b789a2ff13267cbf87ffd39e6db4a3418b579ce9588d6` |
| `SHA256SUMS` | `322b693a0beb546270ebb617a1718d619ecbfa42e79a1dad022885f2ed181714` |

S reported 50 index entries and 172 contiguous native rows (seq 0..171), item entity2 then entity3, EAT OUTCOME native seq102 and 168; native shutdown_ack seq170 followed by connection_end seq171. These are audit targets, **not independently established facts**.

Existing read-only on-host action, using no Java/Node/World/GPU/LLM launch or model inference:

```bash
set -euo pipefail
EVIDENCE=/home/rinsa/evidence/relay-self-b0-ground2-20261014-2c26590-once
test -d "$EVIDENCE" && test ! -L "$EVIDENCE"
for name in physical.json physical.native.jsonl physical.commands.jsonl minecraft.log SHA256SUMS; do
  test -f "$EVIDENCE/$name" && test ! -L "$EVIDENCE/$name" || exit 2
done
( cd "$EVIDENCE" && sha256sum -c SHA256SUMS )
sha256sum "$EVIDENCE"/{physical.json,physical.native.jsonl,physical.commands.jsonl,minecraft.log,SHA256SUMS}
```

The host reviewer must independently inventory *all* original regular paths, canonical roots and symlinks, pre/post `size/SHA256` and existing index identity, verify 50/50 only if locally observed, and store its stdout/exit/report/index in a **new disjoint audit namespace**, never inside original frozen root. If original bytes cannot be read, a checksum differs, a stream is incomplete, or a root/path is ambiguous: **BLOCKED**, do not repair/synthesize/replay.

Check source-head/session/World snapshot/JAR/initial-state bindings against `physical.json` and RSEE preflight; parse original JSONL independently with duplicate-key rejection, all-session/contiguous seq and source correlation, and distinguish outbound command attempt vs inbound applied/terminal response. Read exact Action IDs and OUTCOME; correlate epoch1 ledger tick14 / meals1 / E8.5 and epoch2 tick21 / meals2 / E8.5 to *distinct* terminal S51 EAT receipts. Never credit a pickup alone, duplicates, UNKNOWN, or regenerated display trace. Check original shutdown request and **inbound shutdown_ack** separately from Java/Node exit, PID disappearance, port bind and deleted disposable clone.

Item disappearance + increased inventory is `PICKUP_SOURCE_CONSISTENT`, **not proven native collect-event causation**; the original producer lacked `playerCollect` / item metadata proof. Therefore independent byte review cannot upgrade this evidence ceiling.

## R2: nonforcing WAIT and M0 / World time contract

S current `b0_ground_runner.nonforcing_ground_decision` chooses WAIT or SEEK from a correlated native probe. For WAIT it charges the M0 **decision-tick** basal cost, records `issued_action:false`, and reobserves the World. It must **not** emit an S16 WAIT Action/OUTCOME.

For each nonissued interval require, prospectively in native originals and independently correlated manifest:

1. exact producing HEAD, single owner/session, pre/post native probe request IDs, decoded `session_id` and contiguous native seq; complete predecode inbound/outbound bridge bytes with SHA256, scope and completeness markers, not TCP-level claims;
2. native World tick before/after with a finite monotone delta **when actually available** (otherwise `WORLD_TICK_UNVERIFIED`), wall monotonic times where captured, M0 body tick before/after and energy debit as **separate clocks**; no assumption that one M0 decision equals one Minecraft tick/second;
3. source-verified observed same food item entity and exposure window, qualified nontruncated entity coverage, start/end inventory; explicitly attest the bridge-owner's *whole bounded interval* and all its attempts, with foreign clients/commands either excluded by qualified exclusivity or declared unknown. Silence in partial JSONL cannot prove global absence of action;
4. `WAIT_NONISSUANCE_OBSERVED` only for the qualified issuer scope, **not** `S16_OUTCOME`; `ISSUED_ACTION_WITH_TERMINAL` requires actual S50/S51 owner-authorized Action and receipt; `INVALID_SOURCE` for missing/stale/mismatched originals;
5. terminal distinctions: `M0_TERMINAL_NO_PICKUP` means research M0 energy irreversibly zero, **not** Minecraft HP death; `HORIZON_CENSORED_NO_PICKUP` means observed bounded expiry and nonterminal body; `TWO_GROUND_MEALS_COMPLETED` requires both independently received EAT terminal and distinct M0 credits. UNKNOWN, cleanup failure, truncated stream or unconfirmed stop remain distinct `INVALID`/unverified claims.

Current S limit is up to **24 item-opportunity decisions, up to 8 issued moves per epoch, 2 epochs**; hunger staging also consumes M0 ticks. V2 frozen protocol requires **16 M0 ticks global** and **8 moves total**, plus identical independently committed item schedule across the 4 arms. **This is S/V study admission incompatibility**, not a bug for R to fix in the launcher. No retrospective reinterpretation of S historical B0 and no unilateral V redesign.

## R3: one reusable existing-RSEE operator path (preflight only)

Use a clean detached checkout of exact S producer and a separately pinned #588 Golden checkout. Check source diff and exact CI; maintain a fresh *different* report namespace for each intended episode. The following command is **offline preflight only**; its `--report` and `--server-log` paths must not exist, and parent directory must already exist.

```bash
set -euo pipefail
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
test "$(git rev-parse HEAD)" = 6f95c34918fbe29fea56bc7284e94c4edce21aff
test -z "$(git status --porcelain --untracked-files=all)"
test -x "$BASE/venv/bin/python"
test -d "$RSEE_CHECKOUT" && test "$(git -C "$RSEE_CHECKOUT" rev-parse HEAD)" = 34820f6bf391c77f325d7c29d3b779a33e3ca835
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m adapters.mineflayer.s51_eat_real_ci \
  --preflight-only --food-item rotten_flesh --food-source ground2observe \
  --b0-forage-policy sensor_gate --b0-sensor on \
  --report "$PREFLIGHT_DIR/preflight.json" --server-log "$PREFLIGHT_DIR/server-not-started.log" \
  --rsee-checkout "$RSEE_CHECKOUT" \
  --rsee-jar "$BASE/minecraft-1.21.8.jar" \
  --rsee-snapshot "$BASE/bootstrap-approved-20261011-once/snapshot" \
  --rsee-manifest "$BASE/bootstrap-approved-20261011-once/snapshot_manifest.json" \
  --rsee-initial-evidence "$BASE/bootstrap-approved-20261011-once/initial_native_observation.json" \
  --rsee-node-runtime-root "$BASE/npm-mineflayer-4.39.0" \
  --rsee-eula-accepted
```

`RSEE_CHECKOUT` and `PREFLIGHT_DIR` must be operator-supplied **existing absolute locations**; this documentation does not create them. RSEE/S `--preflight-only` is not a physical grant, does not consume a grant, and cannot establish STOP or World-run success. After a future **separately authorized** S run, S owns original native and command JSONL, immutable fresh report paths, STOP and cleanup; R independently rechecks snapshot/clone identity, original bytes and SHA before handoff; V independently handles science. R should not add another Java/Node launcher or duplicate S's Action/energy code.

## Single S/V handoff & stop point

- **Ready for S engineering preflight:** existing Golden #588 World/Node checker, #545 original S51 entrypoint and disposable clone flow; exact-head S and R CI already available.
- **R evidence blocker:** original B0 ground2 WSL2 bytes not independently read in this GitHub review; source/body/STOP hashes remain operator-claimed until a separate local R readback. An original collect-event witness remains absent.
- **R prospective WAIT blocker:** qualifying complete captured issuer-scope native originals and World tick/wall/M0 timing for true nonissuance is not yet physically demonstrated.
- **S/V trial-design blocker:** S 24-per-epoch/8-per-epoch/2-epoch fixture does not implement V2 global 16-tick / 8-move paired, source-matched, exogenous opportunities; S must supply explicitly study-bounded mode or V must revise prospectively before seeing outcomes.
- **Permission blocker:** every prior B0 grant was consumed. No real S/V experiment until independent admission and fresh user one-shot permission **per run**.

Conclusions remain `B0_R_HOST_ORIGINALS_NOT_READ / R_WAIT_ORIGINAL_NOT_QUALIFIED / RSEE_REUSE_PATH_DOCUMENTED / V_LIVE_NOT_ADMITTED / SCIENCE_NO_GO`. This runbook itself neither certifies code CI nor changes the older R6 S9 result.


## R B0 bounded independent checker (added 2026-10-14)

The R-only implementation \`experiments/standard_env/b0_original_audit.py\` is a **read-only, existing-file checker** (not a second launcher, not a retrier). It pins S-operator-reported four original SHA256 digests and the existing 50-entry SHA index, checks the referenced files, source session/seq 0–171, inbound native STOP ACK versus connection-end and outbound shutdown *attempt*, and tests the *reported* two terminal EAT/credit correlations and original RSEE identity claim. It never turns reported source into independent S16 semantics, R1 envelope, complete native item pickup causal certification, or science.

From **clean detached R HEAD** with the preexisting shared Python, after separately inventorying the frozen original root:

\`\`\`bash
test "$(git rev-parse HEAD)" = <PIN_CURRENT_R_PR_610_HEAD> || exit 2
test -z "$(git status --porcelain --untracked-files=all)" || exit 2
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
EVIDENCE=/home/rinsa/evidence/relay-self-b0-ground2-20261014-2c26590-once
test -x "$BASE/venv/bin/python" && test -d "$EVIDENCE" || exit 2
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m experiments.standard_env.b0_original_audit
"$BASE/venv/bin/python" -m experiments.standard_env.b0_original_audit --root "$EVIDENCE"
\`\`\`

Replace \`<PIN_CURRENT_R_PR_610_HEAD>\` with the **then-current exact, CI-qualified R reviewer commit** before invoking: the runbook deliberately does not invent a future commit. First invocation returns \`RSEE_B0_READONLY_AUDIT_PLAN\` without reading evidence. Second invocation should return \`RSEE_B0_ORIGINAL_BYTES_AND_REPORTED_EPOCHS_REVIEW_ONLY\` only for exact readback; otherwise exit 2 \`RSEE_B0_ORIGINAL_READBACK_BLOCKED\`, STOP without repair or retries. This checker alone does **not** independently verify producer HEAD by inspecting S's on-host clean checkout, full host process history, native metadata collection causation, World time, STOP process/PID/bind or S16 semantics. Verify all such fields separately where physically possible, report unknown otherwise.

Independently compare path identities and full inventory **before and after** the read, storing only the new report, stdout, exit status and checksums in a fresh disjoint report directory. The old B0 root, S/R worktrees, shared Python and Golden RSEE assets are not output destinations. Never use the tool's exit0 as physical admission or a fresh Minecraft execution grant.


## S newest study-mode reconciliation (supersedes the earlier S/V mismatch statement)

At readback, S owner Draft #545 advanced to exact \`5ac03d4ff0197a2a1e55825da1aed1d6d71f24de\`, CI [#38489893708](https://github.com/rinsakamo/relay-self/actions/runs/38489893708) COMPLETED SUCCESS. This HEAD includes optional \`--food-source groundv2\` with the V arm names, **global 16 M0 decision ticks**, **global 8 issued MOVE cap**, and an operator-fixed item placement at **M0 tick11**. The older \`ground2observe\` (24 opportunities/two epochs) remains distinct, and the old V source-only mismatch remains correct *for that older mode*. Therefore the previous global budget mismatch is **partially resolved by S**; it must not be reported as an outstanding constraint mismatch for the new groundv2 mode.

**Still not resolved:** M0 tick11 is not an independently qualified equal Minecraft World tick/time across four arms, even though nominal external item placement is fixed in M0 time. Golden ability freeze, genuinely matched World-start/exogenous timing, complete capture and qualified nonissued WAIT original bytes, independent original Action/Goal semantics, R on-host admission and V live admission are still absent. R must not convert S's exact-head CI into temporal-world attestation. Every old one-shot permission is consumed. No V science experiment has run. This note updates only interpretation of the newer S source; it does not rewrite historical R6/S9 or B0 ground2 evidence.

## V6 R-side World-start and three-clock independent pre-admission (OFFLINE)

R #575 owns `experiments/standard_env/v6_world_timing.py`. This is an
independent, **read-only** World-start and clock review; it does not
change or replay the already completed historical B0 original-byte audit.
V #619 Draft #625 fixed V6 paired protocol at
`f1a747891e9620e4ab7c86f46f6c8b28e31e5f30` (CI success):
4 starts x LOW/HIGH E12/E20 x 6 controls = 48 *unexecuted*
individual session slots. This is not a grant.

Three DIFFERENT axes must be kept independent:

- M0 decision tick: 0 at initial fresh owner, then 11 **real M0 ledger**
  WAIT charges at basal0.5, before first Food13 item observation. This
  is a count of ledger transitions, not elapsed Minecraft or wall time.
- Host monotonic real time: store a single host-clock domain with
  monotonic_ns at each native observation. Difference between stamps
  is a host elapsed duration, affected by stalls and scheduler/bridge
  delays, not equivalent to Minecraft server ticks.
- Native Minecraft clock display: frozen RSEE #588 Mineflayer 4.39
  schema carries `snapshot.time={day,time_of_day,is_day}`.
  Day/time-of-day change with Minecraft `/time` commands and
  daylight-cycle rules. `day*24000+time_of_day` is a *display
  coordinate*, NEVER the independently monotone World-age/elapsed tick.
  Frozen RSEE bridge/protocol currently do **not emit** the
  independent `bot.time.age` or a certified server-side World tick.

New R reviewer has two separate entry points; invoke from a clean R
owner checkout. With no flags it produces
`RSEE_V6_WORLD_TIME_PRE_ADMISSION_PLAN` and reads no originals.
`--jar JAR --golden STOPPED_SNAPSHOT --manifest MANIFEST
--initial-evidence INITIAL --clone EXISTING_UNSTARTED_CLONE`
reads qualified #588 original Golden byte identity and independently
verifies every named stopped clone (26-file listing/content hashes
and NBT seed). It NEVER creates a clone, writes, starts Java or
attests subsequent runtime state. Any unavailable or changed bytes
fail closed, exit2, without repair/retry.

`--trace ABSOLUTE_EXISTING_JSON` reviews one **projection** of 13
ordered native-shaped rows (first observation, eleven no-item L0
WAIT probes at M0 ticks1..11, then Food13 item at M0 tick11).
`--paired ABSOLUTE_EXISTING_JSON` reviews all 12 arms in one World
start set. Projections must carry one session per arm, unique probe
IDs/sequences, host monotonic nanoseconds, separate M0 tick/energy,
native day/time-of-day fields and optional independent `world_age_tick`.
Missing, rewound, forged-looking or unmatched fields fail closed.
Duplicate JSON keys, symlink paths, oversized input and foreign
native source are rejected. **A self-consistent projection is not
independently original-byte authenticated**. Even a supplied
`world_age_tick` is only a claim until linked to R-verified full
native/raw originals and a source-qualified monotonic tick producer.

Cross-arm comparison checks equal elapsed World-age **only when**
every arm supplies a nonnegative tick source; it still returns
`RSEE_V6_PAIRED_CLOCK_REVIEW_ONLY_NOT_ADMITTED`, not physical GO.
Without the frozen bridge source for true age the R result MUST be
`world_age_sample_presence=INCOMPLETE`, not age inferred from day
or M0 count. The observed summon command's native pre/post bracket
provides only an interval of possible effect timing, not the exact
server command-effect tick or inter-World equality. To pass future
physical parity, S/R must separately qualify raw source-time
instrumentation and align actual World-start age and food-opportunity
age in *each* matched start; if impossible, request V prospective
amendment **before** any real outcome or experiment grant.

Do not conflate snapshot equality-at-rest, World reset parity,
host-time duration, native displayed time, native World age,
ledger M0 charges or causal S50/S51 Action/OUTCOME. The source
review cannot certify independent original SHA, native session
issuer completeness, field-level command timing, food acquisition
or V science. Retain `SCIENCE_G3_NO_GO`, `PRODUCTION_NO_GO` and
`NO_FRESH_WORLD_GRANT`. R source/tests remain a separate owner
from S implementation and V preregistration.

## V6 opt-in server-age packet: independent R source pin and ORIGINAL byte review

**R independent implementation:** `experiments.standard_env.v6_packet_provenance`.
Default invocation is no-file/no-launch plan. Pin S experimental producer
HEAD `67c03400a16d0170264e16884b8d82439e3a3194` to its exact
`bridge.mjs`, `v6_native_clock.mjs`, `python_protocol.py`, and
`package.json` Git blobs. The existing Golden #588 bridge is
**different** and cannot be silently used as the versioned producer.
Run offline with `--s-checkout ABSOLUTE_CLEAN_DETACHED_S_V6_CHECKOUT`
to verify exact Git HEAD and byte hashes. The R CI independent sibling
job checks out this exact S commit, never the mutable S branch tip.

S's opt-in `RELAYSELF_V6_NATIVE_CLOCK_V1=1` listens to Minecraft 1.21.8
clientbound `update_time` packets and preserves the packet `age`
(64-bit signed decimal string) separately from packet `time`
(display-time counter), `tickDayTime`, host monotonic ns, original
bridge session_id/seq and `command_effect_tick_attested=false`.
Samples are **sparse** and cannot be interpolated into item spawn tick.
The existing S51 live runner rejects opt-in until new R/S admission.

With independently precommitted expected SHA256 and native session,
an R host reviewer may call:

`python -m experiments.standard_env.v6_packet_provenance`
`--s-checkout ABSOLUTE_PINNED_S_CHECKOUT`
`--native-original ABSOLUTE_EXISTING_NATIVE_JSONL`
`--expected-sha256 EXPECTED_SHA256 --expected-session EXPECTED_SESSION`

This is a read-only original-byte review: canonical/non-symlinked source,
max16MiB bound, independent SHA256 comparand, duplicate JSON keys
fail-closed, one session, continuous seq0..end, Minecraft 1.21.8
adapter_started, each native_clock_packet exact source/keys and
canonical i64 fields, nondecreasing world-age & host clocks, no
fabricated exact effect flags, inbound STOP ACK before terminal
connection_end. Requires >=2 independent raw samples.
SHA and original sequence consistency **do not independently prove**
that a network packet came from the Minecraft server or that an
unrelated `/summon` command applied at a specific age.

Even a perfect result remains
`RSEE_V6_PACKET_BYTES_MATCH_REVIEW_ONLY`: true source-to-server-age
packet provenance requires independent binary/protocol and
runtime identity verification; **exact command-effect World age
and equal cross-arm food opportunity remain blocked**. No current
physical session has been run. Existing B0 58-file independent
historical readback is complete and MUST NOT be rerun for this.
Any future command-effect source must be prospective, separately
versioned, R-qualified, and reviewed by V #619 before requesting
one explicit user authorization for one real World session.

## V6 atomic food fixture: R source and stopped World-overlay checks

R #575 `experiments.standard_env.v6_atomic_admission` is read-only.
It pins exact S source HEAD `cf55c118135e2b11243a1a2d1c375998858f5894`
and blob `b7f0900b27a536c2efa30b6ce8f7a912c4d0378b` for
`adapters/mineflayer/v6_atomic_fixture.py`. Existing R CI checks out
this immutable S revision separately. The R module independently
constructs three expected Java 1.21.8 (format81) candidate datapack
files; it does not execute S code or install datapacks.

Plan only: `python -m experiments.standard_env.v6_atomic_admission`.
Source pin: same command plus `--s-checkout ABSOLUTE_CLEAN_DETACHED_S`.
At-rest World check requires that option plus `--jar ABSOLUTE_JAR`,
`--golden ABSOLUTE_STOPPED_GOLDEN`, `--manifest ABSOLUTE_MANIFEST`,
`--initial-evidence ABSOLUTE_INITIAL_EVIDENCE` and
`--staged-clone ABSOLUTE_EXISTING_CANDIDATE_CLONE`.

The checker verifies frozen #588 Golden's original manifests/bytes,
then rejects ANY deleted/modified original World file or any extra
candidate clone file except the three exact source bytes under
`datapacks/relayself_v6_atomic`. The instrumented clone is therefore
intentionally not byte-identical to Golden; match to Golden is a
pre-install original-file property, NOT proof of runtime clock parity.
No real WSL2 cloned World has been reviewed by this synthetic CI.

The prospective mcfunction records `/time query gametime` into a
scoreboard, summons one rotten-flesh item and records gametime again.
`review_score_claim` can reject mismatched, out-of-bounds or ambiguous
reported scores, a false summon success, replay claims and wrong M0
tick. It ALWAYS returns CLAIM_REVIEW_ONLY: no source-owned original
server stdout or loaded function is attested. The source has NO
single-use guard: subsequent invocation overwrites all three
scoreboard values. Independently proving exactly one invocation
remains an admission blocker; a source-only claim of one invocation
does not close it. The signed 32-bit scoreboard value also needs
an independently qualified age bound.

Before any future physical World grant, independently qualify
actual Minecraft 1.21.8 function parsing/loading, original server
console issuance/readback and command-effect age, exactly one
invocation, fresh live-World start and elapsed native tick parity,
and genuine S50/S51 action and M0 credits. All 48 preregistered
V6 sessions remain NOT_RUN. No Python synthetic PASS is scientific
GO. Original Golden, RSEE #588, S/V manifests, main and B0 original
58-file completed review are untouched.
