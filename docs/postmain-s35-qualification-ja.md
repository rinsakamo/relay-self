# RelaySelf S35 — unsolicited real World entity event to explicit cognition request

## Frozen authority
S34 Draft PR #371 HEAD `a5fbec611caf86231e95932adf8e7fdf3a6ef099`. S18–S34 frozen source and receipts, R6, Paper2 MAIN40 unchanged. S31-B skipped as user-directed.

## Scientific advance
S34 explicitly called `observe(request_id)` before cognition. S35 instead uses **unchanged production bridge** `bot.on('entitySpawn')` to emit an **unsolicited** `MineflayerObservation(kind='entities')` *before the caller sends any observe command*. This may offer a cognitive **candidate**, never automatic Action authority.

A privileged local Minecraft Java 1.21.8 server console summons one zombie about 2m away; real Mineflayer 4.39.0 produces an unsolicited event. A pure event selector requires: exact native observation type, entities kind with **no request_id**, unique zombie, complete 16m entity registry, matching 3D geometry, distance under 4m, and original session/seq/provenance.

A separate explicit correlated `observe('s35-native-event-probe:001')` checks current identity and distance, same Node session and seq strictly newer than event. The **caller then independently grants** a matching `EventCognitionTriggerGrant` (the grant itself never comes from the event), and `EventCognitionLedger` enforces one-shot local admission. Denied grants, replay, session mismatch, stale probe, changed entity and missing target cannot request cognition.

Only the explicitly **admitted ticket** is passed through existing frozen S34 `_native_epoch_two` (ATT/BLF/CNC/PRD/PLAN/ROUTE/ADMISSION). A caller-owned retained risk4/rev1 snapshot is reconstructed from the frozen **S19 deterministic FakeSession history with a valid governed learning commit record**; the S19 predecessor is **synthetic, not Minecraft**. No S35 learning is performed. Expected bounded result: MOVE_AWAY plan and ADMITTED execution candidate, with **zero Action proposal, authorization, issue, effect commands, observed physical movement, learning or autonomous reentry**.

## Authority distinctions
```text
unsolicited source event -> candidate (no scheduling)
candidate + independent correlated probe + caller trigger grant -> one-shot ticket
ticket + caller-explicit cognition -> native-source ATT/BLF/CNC/PRD/PLAN/ROUTE/ADMISSION
ADMITTED plan != proposed Action != authorized Action != ISSUED Action
```

The new typed module `src/relay_self/native_event_cognition.py` intentionally has **no code paths to S15, ActionSupervisor.issue, or Mineflayer effects**. The CI runner checks `ActionSupervisor` has no issued/open Action and no modeled Action owner. A seed-retained value is NOT physically learned in S35 and no RelayEngine/LLM is invoked; the executed cognition is the existing deterministic chain.

## Dynamic qualification
Actual CI job starts official Mojang-verified Minecraft Java 1.21.8 + Mineflayer 4.39.0, waits for spontaneous entitySpawn, then requests separate probe, checks distinct trigger grant/denial/replay, runs explicit cognition and cleanly shuts down Node and Java. Report emitted as `S35_REPORT` and always uploaded with server log.

PASS only if actual unsolicited event observed before probe, exact separate proof and grant admitted exactly once, deterministic cognitive result under native input, zero Action issuance and full clean teardown. Inability to provision official server/Mineflayer = BLOCKED. Absent unsolicited event, false native state, grant bypass, unwanted Action or wrong cognition = FAIL. Neither static tests nor prospective plan by themselves establish live qualification.

## Hard limitations
This is a **controlled** local game, the zombie is placed by server console; no environmental novelty discovery claim. Trigger grant and main loop remain **explicit caller decisions**, so event creation does not equate to an autonomous cognitive scheduler. The event is an untrusted in-process Mineflayer software snapshot, not signed source attestation. Local ledger is not global/durable/concurrent exactly-once. Native session+seq does not authenticate real-world time. Plan/action selection uses frozen rules and a historically qualified yet synthetic S19 rev1 preference; there is **no actual RelayEngine invocation**, Action4, Skill terminal, learning or independent WSL2 reproduction. S35 is not S34 replacement or Theory result revision.

Terminal classification if exact-head CI PASS:
`REAL_ENTITY_EVENT_EXPLICIT_COGNITION_TRIGGER_NO_ACTION_QUALIFIED`.
PR remains Draft / unmerged.
