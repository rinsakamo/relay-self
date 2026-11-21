# P0-D Stage 22 — real Paper per-Self presence and causal limitations (DEV)

Stack: Stage22 → Draft #898 (shared Gemma slot) → #894 (original per-Self cognition) → #892 (original per-Self physical) → #889 (World-resident Self) → #885 (all-N coordinated checkpoint).

**New Stage22 is intentionally two-qualified stages, not an all-in-one PASS:**

1. **Paper B continuous presence** after A logs out, while A later rejoins on a NEW native session: can be independently witnessed by the Paper main-thread player JOIN, QUIT and sampled PRESENT event chain, original A physical/WAL/cognitive retirement and live B native probe. Real Paper 1.21.8 + actual Mineflayer bodies required for *live* success.
2. **B actual original physical Action outcome while A is OFFLINE:** NOT delivered by this slice. The original resident PhysicalIssueAdmission currently authorizes EAT/ATTACK and explicitly rejects MOVE/LOOK/CLEAR outside its supervised global STOP. Never bypass its final native stdin gate or claim that a Paper position delta caused a Self MOVE. To prove B's actual Action, use the original ActionPort+WAL-backed EAT/ATTACK with independent Paper actor outcome, or implement and qualify a resident MOVE+STOP+WAL owner as a separate reviewable change. This remains HOLD until such evidence exists.

## Independent Paper observer

Existing P0BRecorder now owns \`ResidentPresenceWitness\`: on the **Paper main thread** it logs a fresh per-Paper-boot UUID, JOIN, QUIT, and per-player PRESENT heartbeat every >=40 Bukkit ticks or MOVE after >=0.2m 3D displacement, sampling all online player UUIDs every 5 Paper ticks. Records include world UUID, stable actor UUID and username, Bukkit tick, x/y/z and source=PAPER_MAIN_THREAD. This Java observer cannot send a physical Action, fabricate a native Self receipt, or inspect a local LLM task.

\`parse_owned_paper_resident_trace\` is a pure read-only parser; it accepts **bytes read from the current exact \`OwnedPaperWorld.read_owned_log(server_session_id)\`** by its caller, requires one single boot marker, one World UUID, monotonically ordered Paper tick/line positions and schema-exact finite coordinates. A global latest.log or an unverified source is not authenticated by the parser. \`join_resident_paper_presence\` joins the original lifecycle's exact A normal logout (physical issuer revoked, zero active physical Action, canonical WAL clear, actual native terminated, work/peer fenced), A new native login probe and current World+Paper process, unchanged original B native session, and independent Paper A JOIN → A QUIT → B PRESENT/MOVE → A JOIN ordering. It refuses A's old session reused, foreign actor UUID, B reconnect, missing B presence, foreign World/boot/Paper session and forged clocks. **Paper Bukkit tick and native day/time-of-day are different clocks:** their numeric equality is neither required nor sufficient.

The auditor distinguishes \`DEV_B_PAPER_PRESENCE_AFTER_A_LOGOUT\` and \`DEV_B_PAPER_MOVED_AFTER_A_LOGOUT\`. Neither confers a B physical Action source ticket: \`native_action_caused_b_move=False\`, \`physical_wal_action_attested=False\`, and \`actual_paper_source_authenticated_by_parser=False\` remain explicit.

## Operator-approved real Paper harness (not run in GitHub CI)

\`experiments/p0d_real_resident_presence_dev.py\` reuses the existing Stage15 operator-approved **pinned Paper 1.21.8 build60 preflight**, plugin SHA pin, Java21/Node22/Mineflayer4.39.0, real Minecraft EULA flag, owned disposable new scratch World, localhost-only private Paper port, \`OwnedPaperWorld\` OS process, independent \`PaperMainThreadTickReader\`, actual \`MineflayerProcessSession.launch\` and original resident PhysicalIssueAdmission plus original \`CheckpointedCognitiveOwner\`, canonical WAL and \`ResidentCognitiveWorkOwner\`. It does **not** invoke the L1/L2 GPU model; the GPU source qualification for #898 remains separate.

The harness uses **two additional requirements** to prevent accidental real World execution: \`--eula-accepted\` and **\`--real-world-dev-grant\`**. Neither is inferred from prior GPU authorization. Absent either, it MUST HOLD without any Paper or player process launch. It never connects to an existing Paper port, never overwrites an existing World, never sends an L0 MOVE/EAT/ATTACK, never retries unresolved Action, never changes the global roster's checkpoint semantics.

Procedure: operator explicitly grants this real Paper/native DEV; create fresh World; log in A/B as independently owned native child processes using their original physical issuer and cognition owners; wait for independent Paper heartbeats; A clean logout verifies native process termination, original physical WAL and cognition; B retains same native process and supplies a fresh correlated real sensor probe; Paper main thread logs B PRESENT after A quit; A re-logs on a new session and is newly probed; join the current Paper process log to the original source receipts, then cleanly logout both. Optional \`--world-only\` executes the Stage18 original-issuer-qualified World-only STOP/save/restart with exact archive SHA after both Self retire; never include a Self snapshot in this World-only generation. A failure is HOLD and logs/PIDs remain for human inspection, not silently retried.

Example (substitute verified actual paths and SHA; only after operator has agreed to the EULA and granted real World):

\`\`\`bash
PYTHONPATH=src:. python3 experiments/p0d_real_resident_presence_dev.py \
  --paper-jar /absolute/verified/paper-1.21.8-build60.jar \
  --paper-sha256 8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e \
  --plugin-jar /absolute/verified/P0BRecorder-with-ResidentPresenceWitness.jar \
  --plugin-sha256 PLACEHOLDER_COMPUTE_ACTUAL_SHA256 \
  --scratch-parent /absolute/isolated/scratch \
  --eula-accepted --real-world-dev-grant --world-only
\`\`\`

Never infer the plugin SHA from this runbook; build/verify the exact Java21 plugin jar and supply its actual \`sha256sum\`. The full disposable World and immutable audit files stay on the user's local machine; do not upload personal World files without approval.

## Offline evidence and next qualification

Pure parser+join tests require source-backed A/B identities, exact original logout/native session, chronological Paper join/quit/move, B never quitting, correct world+boot and no post-hoc movement causality. Additional local-only runner tests refuse missing real World approval before filesystem changes and refuse bad native probe sources. Java plugin is compiled in the existing Paper plugin CI. No genuine Paper/Mineflayer was started by GitHub Actions.

**Real Stage22 positive qualification requires LocalCodex to use the current HEAD on a separate worktree and explicit user EULA/real-World grants.** Report exact HEAD, paper/plugin SHA256, Paper PID/boot, source logs, native A/B session IDs, cognition/WAL readback, Paper A QUIT/B PRESENT/A JOIN, source-correlated B native after-A probe and, if opted-in, World-only archive hashes. A Paper MOVE without canonical B physical WAL+original issuer and a causal server ticket MUST NOT be called a B actual original Action. If B only remains PRESENT, report precisely \`REAL_PAPER_RESIDENT_PRESENCE_DEV\`, not \`REAL_B_ACTION_PASS\`.

No forced GPU preemption, actual cross-Self communication, N=100 live World, or QUAL/SCIENCE claim follows from this stage.

Classification (pending real run): \`PAPER_RESIDENT_PRESENCE_OFFLINE_DEV_PASS / REAL_PAPER_RESIDENT_PRESENCE_NOT_ATTESTED / REAL_B_PHYSICAL_ACTION_NOT_ATTESTED / REAL_WORLD_ONLY_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN\`.
