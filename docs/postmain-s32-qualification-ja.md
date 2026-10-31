# RelaySelf S32 — supervised real Action3 / WorldConsequence / new observation / cognition

## Authority
- S31-A exact frozen HEAD `2f3af780508a51b66513043b4cfedf80d20ff1a0`, Draft PR #368.
- User elected to **skip S31-B WSL2 reproduction**. Do not claim it occurred.
- S18–S31-A frozen artifacts and RelayTheory R6 / Paper2 MAIN40 are unchanged.
- S32 is a **hybrid** real-world qualification: the S19–S23 *antecedent* history is a frozen deterministic test fixture; only **Action3 and subsequent observation** interact with a genuine Minecraft server.

## Scientific question
S31-A showed genuine Mineflayer 4.39.0 reading an actual controlled Minecraft Java Edition 1.21.8 zombie, but had **no** existing supervised Action3, S15 WorldConsequence, S16 outcome or S27-linked S24 epoch. S32 asks whether those existing typed contracts can be connected using **genuine physical movement and a subsequent separate actual observation** in the same native Mineflayer session.

```text
S19–S23 deterministic/seeded retained state and predecessor outcomes
      |
      v (explicit S23 Skill3, admission, binding, proposal, authorization, issue)
Real Minecraft Action3, existing S15 MOVE_BACKWARD physical primitive
      |
      v (real before+effect+cleanup+after native protocol messages)
S15 WorldConsequence3 EXECUTED, position delta >=5cm
      |
      v (existing S16 interpretation and exact ActionSupervisor closure)
Action3 terminal OUTCOME
      |
      v (server console summons real NoAI zombie at about 2m)
Separate correlated Mineflayer World probe with exact ID, session, seq
      |
      v (S27 exact Action3/World/session lineage and geometric validation)
PostFailureWorldEvidence from actual controlled Minecraft observation
      |
      v (explicit caller-invoked fixed S24 cognition)
WAIT / ADMITTED, retained risk_weight=4/rev1
```

**No second physical Action** after S24; this is an observation-and-decision boundary only.

## Exact environment
CI uses the frozen S31-A official Mojang server downloader and clean teardown:
- Mojang official Minecraft Java Edition **1.21.8**, verified size and SHA-1,
  Java21, loopback `127.0.0.1:25565`.
- Mineflayer package **4.39.0** installed from frozen npm lockfile.
- Actual `adapters/mineflayer/bridge.mjs`, `MineflayerProcessSession`.
- `NODE_OPTIONS` and all S30 test-only module substitution forbidden.
- No external Minecraft server; temporary local server is destroyed after qualification.

## Seeded history boundary (important)
The CI-only runner imports *frozen S23 test fixture helpers* via explicit
`PYTHONPATH=src:tests`: `_prepare_recovery`, `_propose`, `_issue`.
These instantiate the separately governed Skill3, admission, Action3 mapping
and issued supervisor owner using S19/S20/S21/S22 **synthetic prior outcomes**.
No claim that earlier Action1/2, retained learning rev1 or Skill3 formation
actually arose in this Minecraft world.

The production code still owns every S32-relevant transition:
`build_mineflayer_command` → `execute_mineflayer_command` →
`interpret_world_consequence` → `record_interpreted_action_outcome` →
`project_source_native_threat` → `run_explicit_postfailure_epoch`.

The frozen logical `at_ns` sequence (issue 49, closure 60, observed 65,
inspect 67, cognition 70) is an **explicit verification clock**.
These values do not represent timestamp attestation from the real Minecraft
server. Native Mineflayer provenance binds session/seq and actual message data.

## PASS conditions
1. Genuine server and Mineflayer spawn; distinct exact session identity.
2. S23 explicit S12/S13/S14/S15 authority chain produces Action3 ISSUED,
   mapped to the bounded S15 `MOVE_BACKWARD`.
3. Real Mineflayer command goes through physical dispatch+cleanup; observed
   position delta >=5cm and structured WorldConsequence3 = EXECUTED, same
   session and exact Action/binding/provenance.
4. Existing S16 outcome interpreter closes exact supervised Action3 as OUTCOME,
   no outstanding issued Actions.
5. Controlled NoAI zombie is summoned **after** action closure; explicit
   correlated probe returns entity ID, position, distance and same-session seq
   strictly newer than the S15 post-action probe.
6. Existing S27 projector *accepts that actual new protocol observation* with
   exact zombie ID, bounded coverage, geometry, caller time and Action3 lineage.
7. Existing S24 explicitly runs bounded ATT→BLF→CNC→PRD→PLAN→ROUTE→ADMISSION.
   With approx 2m, risk weight 4/rev1 it selects WAIT / ADMITTED, without Action4.
8. Node bridge and Java server cleanly exit 0; CI report is uploaded.

Any physical movement below threshold, wrong outcome provenance, stale seq,
misidentified entity or S27/S24 denial is FAIL, not an inferred success.
Infrastructure unavailable => BLOCKED, never PASS.

## Dynamic and static authority
`docs/postmain-s32-plan-receipt.json` is prospective and deliberately
`PENDING_CI`. The **dynamic** `S32_REPORT` stdout /
`s32-report.json` CI artifact and exact run status determine qualification.
Offline tests cover false Action provenance, stale seq, wrong session,
nonexecuted consequence, expired caller clock and no Action4.

## Limitations
- Hybrid history, not a genuine Action1→Action2→Action3 physical lineage.
- Source is a **controlled local game world** under server-console authority,
  not real-world physical truth or cryptographic trust.
- Caller provides target ID from real probe and logical nanosecond timestamps;
  the World transport itself has no authenticated sensor clock.
- Movement threshold 5cm is a bounded S15 primitive; no generalized
  locomotion/safety guarantee.
- S24 policy is fixed and deterministic, not LLM cognition or trained strategy.
- No autonomous scheduling, actual WAIT timer, Action4 authorization/issue,
  Skill3 completion, new retained learning, or LocalCodex S31-B reproduction.
- Paper2 MAIN40 result remains frozen.

## Classification
**`HYBRID_SEEDED_ANCESTRY_REAL_ACTION3_S15_S16_S27_S24_QUALIFIED`** only if exact HEAD's S32 real-server CI and full regressions PASS. Otherwise report BLOCKED/FAIL.
PR stays Draft / unmerged.
