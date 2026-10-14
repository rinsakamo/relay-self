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
