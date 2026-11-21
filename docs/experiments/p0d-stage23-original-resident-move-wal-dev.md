# Stage 23 (#904) — original resident MOVE / STOP / canonical WAL (DEV)

Stack: Draft #905 → #902 (real two-resident Paper presence) → #898 (real single-slot Gemma DEV) → #894 → #892 → #889. This is **not** full autonomous behavior, L2-created Skill qualification, or QUAL/SCIENCE. **The repository must be read before running.**

## Original physical owner, no S49 selection

\`PhysicalIssueAdmission(…,resident_mode=True,allow_resident_move=True)\` is an **explicit opt-in** on the original issuer. Global-N STOP and ordinary resident mode remain unchanged unless this flag is enabled. No second Action issuer, Skill selector or WAL writer is introduced. The MOVE parent must already be an original current \`PhysicalActionPort.propose_bound_physical_action\` proposal created from the same Self's selected Intent/Skill and two correlated native probes.

The first DEV primitive is a bounded relative-direction MOVE: \`MOVE@1\`, body channel \`locomotion\`, target kind \`RELATIVE\`, target ref \`relative:forward\` / \`relative:back\` / \`relative:left\` / \`relative:right\`, with a 0.15–0.75-second native pulse. It is **not** a general waypoint resolver or a target-positioning planner. Future generated Skills can use a common typed ActionPort, but target/tolerance policy must not be frozen to this relative pulse.

Original issuer sequence:

1. Already-selected original physical proposal + explicit operator World DEV grants; require fresh prior/current native request-correlated probes, current Intent/Skill, and no conflicting supervisor action.
2. Acquire Self-scoped original \`PhysicalIssueAdmission\` lease; ***fsync*** \`PhysicalActionJournal.prepare_move\` = canonical \`PREPARED_UNRESOLVED\` before **any** native motion IO or ActionSupervisor.ISSUED.
3. Bind exact native child IDs (\`<parent>-start\` \`set_control\`, \`<parent>-stop\` \`clear_controls\`) from the *restored fsynced* original WAL. Original final native stdin refuses wrong or repeated IDs, another Self/native session, wrong effect family or an unbound MOVE. Existing selected EAT/ATTACK wrappers and L1 runners now similarly bind their true child IDs from the canonical WAL; the generic test adapter lease is not a production skill authorization.
4. Send a **single bounded** native start pulse; await source-qualified \`set_control\` ACK; issue single STOP and require \`clear_controls\` ACK, then 8 Minecraft World clock ticks of settling and a subsequent 8-tick final interval with 3D drift <= 0.06m. STOP here is a motion neutralization threshold only, **not the target accuracy** for a waypoint/place/attack stand-off.
5. Original \`ActionSupervisor.OUTCOME\` + canonical \`PhysicalActionJournal.close_move\` = \`NATIVE_MOVE_SETTLED\`, only if current native, unique ACK IDs/sequences, four source-correlated probes and sufficient observed net 3D displacement all validate; re-open original WAL from disk to verify digest.
6. A Self quarantine closes new MOVE starts, but the **already-bound single STOP child** may pass once even after A's issuer is quarantined, to prevent infinite motion. Other Self remain ONLINE and may issue original Action leases. A failed/canceled/unknown MOVE remains \`PREPARED_UNRESOLVED\`, no auto-reissue, no falsely clean logout/World-only save. A STOP send attempt is not a verified STOP ACK, nor 8+8-tick physical settling.

The existing generic EAT/ATTACK lease tests can still use their declared literal root ID as a source fixture in resident mode; selected production EAT/ATTACK wrappers bind the **actual parent + exact child IDs** after WAL PREPARED. This does not claim all legacy direct native command call sites were audited for bypass.

## Offline negative controls

Test \`tests/test_p0d_resident_move_issuer_dev.py\` and the real runner adapter tests:
- N=2, 10, 100: original B physical lease stays live while A MOVE is quarantined; only A's exact STOP child remains authorized; original WAL and supervisor seal successful MOVE after source-qualified 8+8-tick stillness; A may retire only after original WAL clear
- forged/same-family child ID, replayed start/stop ID, family mismatch and pre-WAL MOVE write all refuse at **final native effect admission**
- malformed/absent STOP ACK or insufficient net displacement leaves original fsynced \`PREPARED_UNRESOLVED\`; one Self cannot retire, the other Self's original EAT still admits
- original canonical WAL restored across process state, wrong stable-tick timing rejected; all existing EAT/ATTACK and global STOP paths remain tested
- actual runner adapter wires the original \`CheckpointedCognitiveOwner\` facade \`commit_intent\` and \`start_skill\` with the same original physical ActionPort, action supervisor, issuer and WAL, without pretending L1 autonomously chose MOVE
- immutable first A logout cognition bytes, initial source receipt, final A/B individual receipt files and owned native PID↔session pairs retained as separately hashed DEV sources

All Offline tests are synthetic Mineflayer/physical World; the Java plugin's independent Paper witness remains passive.

## Operator-approved real two-Self Paper runner

The existing Stage22 operator-owned harness has one additional **opt-in** flag \`--b-selected-move-dev\`. It is independent of normal presence-only mode, uses the SAME original B cognitive owner, canonical WAL and \`PhysicalIssueAdmission.issue_move\`, and runs B's relative MOVE only **after A's original logout** and before A relogs. It also retains B's newly observed native probes, original start/STOP/settle ACK/probe history, WAL sha, Paper independently witnessed B movement, A's immutable first cognition and individual final receipts, and original native process PID↔session metadata. Optional World-only save/restart after both clean Self retirements remains supported.

In the RelaySelf project's LocalCodex prompts, the user has already explicitly approved Minecraft EULA and real-World DEV, so **do not repeat an approval question**. Supply the runner's explicit \`--eula-accepted --real-world-dev-grant\` flags as the existing user's grant, and use **one fresh, isolated localhost World**, pinned Paper/plugin jars and existing Java21/Node22/Mineflayer4.39.0. Do not start a new local server against already running endpoints; never import a previous World. Do not retry when any start/STOP/WAL is uncertain. No GPU/L1/L2 is required in this trial.

Example after exact-head CI and SHA preflight:

\`\`\`bash
PYTHONPATH=src:. python3 experiments/p0d_real_resident_presence_dev.py \
  --paper-jar /absolute/pinned/Paper-1.21.8-build60.jar \
  --paper-sha256 8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e \
  --plugin-jar /absolute/build/P0BRecorder.jar \
  --plugin-sha256 VERIFIED_ACTUAL_SHA256 \
  --scratch-parent /absolute/new-isolated-scratch \
  --eula-accepted --real-world-dev-grant \
  --b-selected-move-dev --b-pulse-seconds 0.35 --world-only
\`\`\`

**This trial's B MOVE is operator-selected for DEV**, then carried by the original Intent/Skill/ActionPort. A successful native MOVE under this harness does **not** prove L1 autonomously selected MOVE, L2 generated a Skill, target navigation succeeded, or the precise Paper movement had a fully independent Action-specific causation ticket. Require \`NATIVE_MOVE_SETTLED\` with original canonical WAL sha, matched native start/STOP ACKs and 8+8-tick stillness, and **Paper main-thread B MOVE after A QUIT** with the same Paper/World/player UUID while A relogs with fresh native session. Classify physical movement as source-correlated, not uniquely causally attributed, without an action-specific server ticket.

Before the World-only stop, write and read back the *first* A cognition snapshot; individually preserve each original A initial and A/B final logout receipt via exclusive fsynced writes; record actual owner-held native OS PID and source session, Paper boot and World UUID, original full Paper log and SHA256, WAL and complete 59+ file hash manifest as applicable. The earlier Stage22 run did not retain first A cognition and final receipts, and these must now remain separately inspectable.

## Classification gates

- Offline exact-head CI 5/5: \`RESIDENT_MOVE_ORIGINAL_WAL_OFFLINE_DEV_PASS\` (only for tests actually passing)
- Real B movement: \`REAL_B_ORIGINAL_NATIVE_MOVE_AND_PAPER_CORRELATED_DEV_PASS\` only with independent real Paper source, original WAL and native/STOP; leave \`REAL_B_AUTONOMOUS_SKILL_SELECTION_NOT_ATTESTED\` and \`PAPER_ACTION_SPECIFIC_CAUSAL_ATTRIBUTION_NOT_ATTESTED\`.
- World-only remains NOT_ATTESTED until the new run completes with original B MOVE WAL clean; do not infer atomic World+all-Self save or replay.
- GPU forced preemption, real peer delivery, QUAL and SCIENCE not established. Earlier real Gemma natural completion and Stage22 real resident World-only PASS remain separate historical DEV results.
