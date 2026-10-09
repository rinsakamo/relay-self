# RelaySelf S40 — Actual post-dispatch Node loss and S16 UNKNOWN

## Authority / status

Frozen S39 exact base: `80a8178ee9bd4c95c2f668247ba3e7c2f097895b`, Draft PR #376.
S39 had one complete exact-head five-job SUCCESS; the second full independent final-head run was not confirmed when S40 was branched. **S40 does not retroactively qualify S39.** Preserve frozen S18–S39, RelayTheory R6, Paper2 MAIN40 unchanged. S31-B WSL2 independent reproduction remains explicitly **SKIPPED**.

The static plan is `PENDING_CI`. Only real dynamic `S40_REPORT.status=PASS` on two independently confirmed successful five-job exact-final-HEAD CI runs permits scientific classification.

## Falsifiable question

Can real Node process loss **after** a genuine Minecraft `set_control` effect result `applied`, but **before** cleanup and final World observation, close a previously ISSUED Action as **UNKNOWN**, and forbid both old-source dispatch and speculative replacement?

An applied adapter receipt proves acceptance of control, **not** the terminal physical displacement. A failed transport/cleanup is not a known negative World outcome.

## Physical protocol

1. Spawn a Mojang-verified Java Edition 1.21.8 server and authentic unmodified Mineflayer 4.39.0 Node bridge. Experimenter creates zombie A.
2. Use S38/S39 path: native unsolicited entitySpawn A, correlated probe, explicit cognition grant, bounded MOVE_AWAY/ADMITTED cognition. Still no Action.
3. Intentionally SIGKILL actual first Node child; observe actual negative OS returncode + real `MineflayerProcessEnded` EOF, quarantine old source and deny old Action proposal.
4. Keep same Java server alive; remove A while Node is dead, supervise real new Node session, create independent zombie B, obtain new unsolicited event + correlated native probe + explicit cognition grant -> S38 ACTIVE. Old source still denied.
5. Independently grant S39 PROPOSE and ISSUE, create one actual ISSUED Action and consume exactly one S39 command release. No reissue authority.
6. Execute **unchanged S15** against actual Node. The *test-only transparent adapter wrapper* forwards real messages and waits for **actual typed applied effect receipt** for the precise Action ID. Immediately after observing that native receipt, OS-SIGKILL the actual **second** Node child. The wrapper must not forge a dispatch or an after observation.
7. S15's incomplete `WorldConsequence(FAILED)` must contain valid same-session before probe and native applied dispatch, **no cleanup receipt, no after probe, no measured displacement**, and a real `MineflayerProcessEnded` failure. This status reflects an interrupted evidence collection, not proof that movement physically failed.
8. Observe actual stdout EOF and second negative OS returncode, quarantine exact second session via S38. S40 checks process identity, current ISSUED supervisor snapshot, S15 command/binding identity, applied native effect, temporal order, exact missing completion evidence and genuine transport loss.
9. Invoke **existing S16** `interpret_world_consequence` and `record_interpreted_action_outcome` to transition one ISSUED Action to terminal `UNKNOWN`, with interpretation reason `adapter_failure_consequence_unknown`. No S16 OUTCOME, no auto-retry, no learning. Old S39 dispatch ticket cannot be reused.
10. The Java server exits0; both test Node children were intentionally OS-killed. **No claim** that the body did move, did not move, or moved a particular amount.

## Negative controls

Offline fixtures (no physical claim) require wrong status/session/returncode/Action/binding/effect, missing or rejected applied receipt, fabricated complete after/cleanup/movement, missing process-EOF error, non-quarantined source and duplicate UNKNOWN reconciliation to fail closed without creating another Action. An Action already terminal UNKNOWN must reject speculative later OUTCOME.

## Boundaries

- The experimenter's SIGKILL is a deliberate, supervised fault injection; not random network loss, Java-server crash, host Python crash, unattended recovery or real-world resilience.
- One caller-serial process, explicit grants and fixed cognition, no LLM autonomy or new goals. Retained rev1 is frozen S19 synthetic governed learning, **not newly learned from S40 Minecraft**.
- The S39 release gate is not a global unforgeable Action security perimeter. No distributed exactly-once semantics, durable transaction log, recovery from UNKNOWN, compensation Action, proof of physical nonexecution, or physical clock signing.
- S40 establishes one bounded fail-closed path. It does not establish that every possible process death timing is handled safely.

## Candidate qualified label

`REAL_INFLIGHT_NODE_SIGKILL_APPLIED_DISPATCH_UNKNOWN_NO_RETRY_QUALIFIED`

Keep S40 Draft / unmerged until exact-head 2x successful full CI and mandatory dynamic actual-world receipts are independently verified.
