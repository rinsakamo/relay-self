# RelaySelf Stage23b — original native MOVE raw-source audit and truthful report flags

Issue #904; Stage23a original real Paper result under [Draft PR #905](https://github.com/rinsakamo/relay-self/pull/905), Stage23b fix stacked as [Draft PR #908](https://github.com/rinsakamo/relay-self/pull/908).

## Preserve original once-only World evidence

The real Paper 1.21.8 + 2-native + B MOVE DEV trial was run **once**, exact prior HEAD \`9ed67ffac3e931d734bc713b63f189ab5bbcd004\`, new independent localhost World \`77438472-258e-4087-8ab9-9fd8ac3f7a66\`. The original log readback showed A QUIT at Paper tick108, B MOVE tick195/200 (about 1.507m), A new native JOIN tick241, native start ACK seq60, stop ACK seq68, original WAL \`NATIVE_MOVE_SETTLED\`, source tick206/226/246, no unresolved Action; full World-only generation with fresh Paper process restart verified. Its original file SHA256, operator result and 58-file manifest were preserved unchanged and reported in PR #905 comment #6906877502. It qualified **source-correlated B physical MOVE, not independent server-side Action-specific causation**.

**Two original evidence defects are permanent historical limits:**
1. The original result JSON top-level \`real_b_physical_action=false\` incorrectly contradicted nested \`b_actual_physical_action=true\` and the original terminal WAL.
2. The original real trial did **not** save the source-native JSONL bytes containing actual START/STOP ACKs and every intermediate native settling probe, only source-derived terminal summaries; full independent raw replay can **never** be asserted retroactively for that World.

Stage23b changes future code and future source qualification. It **must not overwrite, reclassify, rewrite or rebuild** any 9ed67ff real World output. The original bounded Stage23a result remains DEV correlated PASS and raw independent source replay remains NOT_ATTESTED.

## Stage23b changes

The original \`MineflayerProcessSession\` can now install an **exclusive one-time** \`start_raw_source_audit(path)\` on the already-owned B Node process after original login, **before** B's two native Action probes. Every *actual original stdout* JSONL line received on that exact process is fsynced as its original bytes before decoding; malformed/foreign source is also retained before the parser refuses it. The output is an owned-process stdout **suffix** (it does not include the initial \`adapter_started\` line from login). \`finish_raw_source_audit()\` freezes the file; double installation/freeze refuses. This transcript is source-owned, but **does not cryptographically authenticate the Node bridge**.

\`ResidentMoveDevReceipt.all_stop_probes\` now retains every native STOP observation the original \`_settled\` logic consumed, including interim drift. \`readback_owned_move_native_source\` independently decodes the complete source transcript, rejects missing/truncated/duplicated/foreign ACKs and probes, requires contiguous native seq, the original current probe and session, and recomputes native 8+8 tick settling with <=0.06m 3D drift across **all** samples. It compares source coordinates/ACK seq/ticks/Action ID/World session with the restored *original* source-validated WAL \`NATIVE_MOVE_SETTLED\`, original receipt and digest. It writes and rereads a separate exclusive raw-source readback sidecar. Any error is HOLD, not a synthesized source PASS.

The new real-only evidence paths under the fresh runner's 0700 evidence folder are:

- \`B-original-move-native-source.jsonl\`: exact owned Node stdout line bytes during the original B MOVE; its SHA256 is recorded.
- \`B-original-move-native-readback.json\`: independent raw replay proof with original source path+SHA, original B native session, original Action, WAL digest, START and STOP native ACKs, **every** STOP probe's seq/request ID/World tick/3D position, and explicit no-autonomous-selection/no-Paper-causal-ticket flags.
- \`resident-presence-result.json\`: root flags now derived from the only successfully qualified nested trial. On a selected MOVE before successful qualification, \`real_b_physical_action=null\` means UNKNOWN/HOLD, never false. After original WAL terminal + independent Paper B MOVE + raw source verifier all succeed, root and \`steps[0].b_actual_physical_action\` are both \`true\`; if any mismatches, the run stays HOLD. Presence-only runs remain \`false\`. The report rereads readback sidecar and source files, confirming SHA and Self/native/Action/WAL identity, instead of trusting a filename.

The original MOVE+STOP native final-stdin lease, canonical fsynced PREPARED/terminal WAL, original ActionSupervisor and optional World-only path are unchanged. This Stage23b is a **source-capture/audit fix**, not a new native action or new agent policy.

## Offline and real qualification

Offline tests include: exact byte-for-byte MineflayerProcessSession stdout capture and exclusive freeze; original MOVE/WAL fixture raw stream positive replay; missing final probe, false child Action, wrong session, duplicated ACK, tampered settled coordinates, truncated JSONL, raw source SHA tamper, nested/root result contradiction, omitted source sidecar, presence-only no-MOVE. These are synthetic fixtures, not proof of recovery of prior missing real bytes.

For further real source qualification, LocalCodex must first read the repo, #904, #905, #908 and this runbook; verify exact new HEAD CI 5/5; use the user's existing explicit Minecraft EULA and real World DEV approval without reasking; pin new Paper 1.21.8 build60 and Java21/Node22/Mineflayer4.39.0; start one **new isolated disposable localhost World**. Run the existing opt-in \`--b-selected-move-dev --b-pulse-seconds 0.35 --world-only\` on that fresh World. Verify:
- first A source-specific logout; B original current native process/PID; A fresh new login; Paper B independent MOVE while A OFFLINE, *not just PRESENT*;
- original WAL PREPARED/ACK/OUTCOME, final WAL clear, native stdout ACK seq IDs and every native stop probe coordinate restored and **recomputed from the archived original bytes**;
- exact source-file SHA256, independent readback sidecar and consistent report root+nested fields; immutable A first cognition, A-first/A-final/B-final logout receipts and verified World-only generation archive;
- one trial, no automatic action reissue on ambiguous STOP or unresolved WAL, no retroactive edits to the former real World files.

**Stage23b Offline PASS != NEW REAL RAW EVIDENCE PASS**. Do not declare independently reverified real raw ACK/stop until a **new real** B MOVE run captures the original bytes. Paper event correlation still cannot prove exact Action-ID specific causal attribution. L1 spontaneous MOVE/Skill success, forced GPU preemption, atomic World+Self checkpoint and QUAL/SCIENCE remain NOT_ATTESTED.
