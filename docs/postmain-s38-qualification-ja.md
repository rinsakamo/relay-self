# RelaySelf S38 — actual forced Node loss and fail-closed source revalidation

## Authority and scope
- S37 frozen Draft PR #374 exact base `3f1298b4e485a7721af3b7fe1608a58d9f0fcce7`.
- S18–S37 frozen artifacts, RelayTheory R6 and Paper2 MAIN40 unchanged.
- S31-B was user-skipped and never independently reproduced.
- S38 adds new test-only controlled **SIGKILL of real Node/Mineflayer child**, not TCP packet-loss, server crash or autonomous host-process recovery.
- This plan is prospective: **only** `S38_REPORT.status=PASS` in exact-head real Minecraft CI plus full regressions grants terminal qualification.

## Scientific question
S37 could cleanly shut down a healthy Mineflayer process, discard its event queue and reopen a distinct session. S38 asks whether an *actual unexpected* Node process death can be detected and quarantined, so no previously admitted event or old World source can restart cognition, and whether a separately supervised successor can cognize **only on new source evidence**.

## Typed authority separation
```text
S37 normal ACTIVE session + actual Minecraft native event
  -> independently correlated World probe + cognition grant
  -> one bounded cognition (NO Action)
  -> test-only operating-system SIGKILL on actual Node child
  -> real MineflayerProcessEnded stdout EOF + negative process returncode
  -> S38 ForcedNodeLossFence observes fault
  -> QUARANTINED; S37 old session ended, queued work dropped
  -> old cognition ticket and attempts to run ACTIVE denied
  -> supervisor explicitly opens NEW distinct native Node session
  -> PROBATION (not ACTIVE; still denies old ticket and old decisions)
  -> independently created real new zombie event in SAME surviving game server
  -> native event + NEW correlated probe with exact UUID, newer seq, entity ID
  -> independent S35 cognition grant and S37/S36/S34 bounded cognition
  -> ACTIVE restored only after source checks; old ticket remains invalid
  -> NO Action/issue/physical movement; clean successor/Java teardown
```

## Dynamic physical experiment
- Mojang-verified real Minecraft Java1.21.8 server, Java21, loopback 127.0.0.1:25565, genuine Mineflayer4.39.0 + Node22; no S30 preload or fake bot.
- First real Node session receives one server-console-created zombie at about 2m. Native unsolicited `entitySpawn` and exact separate `observe(request_id)` yield `MOVE_AWAY/ADMITTED`, not an issued Action.
- **Deliberately send SIGKILL to the actual child PID through asyncio.subprocess.Process.kill()**. Record negative OS returncode, then read until genuine stdout EOF produces **`MineflayerProcessEnded`**. No test-only fake EOF counted.
- Fence retires the exact current UUID and rejects all old tickets. Even an attempted epoch call under QUARANTINED must raise.
- While Node is dead, experimenter removes original controlled zombie from still-alive game World. Spawn a new genuine Node process, new UUID, **PROBATION** until verified. Experimenter summons a separate new zombie, and real unsolicited event + correlated re-probe + separate grant/one-shot ticket are required for cognition.
- S37/S36/S34 exact native source lineage must pass. The successor's first valid epoch `MOVE_AWAY/ADMITTED` restores ACTIVE. Old ticket must remain rejected even after new-session revalidation.
- Both Node and Java teardown recorded, first Node exit **nonzero forced** and second Node+Java exit **0**.

## S38-only owner rules
`ForcedNodeLossFence` requires (a) current ACTIVE source, (b) actual typed `MineflayerProcessEnded`, (c) nonzero OS returncode to quarantine. It does not fabricate credentials, automatically reconnect, or import Action APIs. After fault no cognition may run via S38's public wrapper. Only a caller-opened successor under PROBATION can pass the genuine S37 event admission stack. The wrapped S37 scheduler uses an in-memory queue and EventCognitionLedger; both are dropped at fault retirement. No global replay protection, cryptographic attestation or signed world clock is claimed.

## Test partition
**Genuine physical CI** validates a forced OS SIGKILL on the real Node process, actual EOF evidence and a strict old-ticket denial, plus a new independently spawned Node and Minecraft-source event. This is a **supervised process-death scenario**; not unattended recovery or crash-resume.

**Deterministic negative tests** validate wrong/zero exit, fake error types, foreign active session, repeated fault, new session reuse, premature reentry, no event/probe under PROBATION, denied independent grant, active/current ticket post-proof and zero Action surface. Offline-only queue invalidation on fault is not falsely reported as a measured live queued-event burst.

## Hard nonclaims
- Game zombie stimulus and current intent, grant policy, semantic rules are explicitly experimenter-defined. No uncontrolled threat detection or novel goal formation.
- Valid risk4/rev1 comes from frozen S19 **synthetic but governed** FakeSession history, not S38 World action/learning.
- No autonomous reconnect scheduler, indefinite daemon, host Python process crash survival, TCP-only network partition recovery or world-server failover.
- No distributed/durable replay protection, no authenticated physical World source clock, no automatic Action4/Skill terminal or actual Minecraft movement.
- Arbitrarily expensive synchronous cognition is not CPU-preempted by these quota controls.

If exact-head CI passes, terminal classification:
`REAL_SIGKILL_FAIL_CLOSED_FRESH_SESSION_REVALIDATION_NO_ACTION_QUALIFIED`.
Keep PR Draft / unmerged.
