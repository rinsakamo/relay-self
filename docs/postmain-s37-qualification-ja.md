# RelaySelf S37 — three real native incidents across two Mineflayer sessions

## Frozen baseline and authority
- S36 qualified and frozen Draft PR #373 HEAD
  `670c2ee3c473cd2eb3f971bc2040356dc5060e06`.
- S18–S36 frozen artifacts, RelayTheory R6, Paper2 MAIN40 unchanged.
- User explicitly skipped S31-B local WSL2 reproduction.
- The plan receipt is prospective `PENDING_CI`; real PASS requires exact-head
  CI and per-run `S37_REPORT` source-native trace.

## Scientific question
S36 shows *one* native Minecraft event automatically invokes one bounded
cognitive pass, no Action. S37 asks whether a supervised host loop can
handle **more than one genuine changed-world event**, then reconnect to the
same Minecraft World without accepting old cognition tickets.

New `BoundedNativeHostLoop` consumes a stream of real `MineflayerObservation`
frames. For each distinct real zombie entity in its current session, it calls
the unchanged S36 scheduler `on_native_event` automatically. The scheduler
performs separate real correlated observe, independently configured
cognition-only grant and exact S35 ticket admission; it calls frozen
deterministic S34 native cognition. No Action or Skill API is present.

### Real CI controlled sequence
1. Boot one official Mojang-verified Minecraft Java Edition 1.21.8 server,
   Java21, loopback-only; genuine Node22 / Mineflayer4.39.0 package.
2. Spawn first Mineflayer Node session and attach host generation 1.
3. Console summons zombie A ~2m from bot. Unsolicited real entitySpawn →
   native entities frame → automatic re-probe/grant/ATT/BLF/CNC/PRD/PLAN/
   ROUTE/ADMISSION; expect MOVE_AWAY / ADMITTED, zero Actions.
4. Console kills A and corroborates no nearby zombie by a separate explicit
   native probe. Console summons zombie B ~2m; host loops waiting for next
   real unsolicited entitySpawn. B must have a *different* Minecraft entity
   ID; second automatic cognition, still zero Action.
5. Explicitly supervised clean Node process shutdown. `end_session` removes
   process-local pending queue and event ledger. Same Minecraft Java server
   remains running. Start second genuine Node session with **different UUID**.
6. Host explicitly rejects a prior session's admitted cognition ticket.
   Clear old controlled zombie, console summons fresh zombie C, and host
   automatically cognizes third real unsolicited event with new session/seq.
7. Validate exactly **3 actual source events, 3 distinct entity IDs, 2 real
   Mineflayer sessions, 3 newly observed source probes**, full clean
   shutdown. S19 prior governed risk4/rev1 is frozen synthetic FakeSession,
   not live S37 learning; no physical Action or Action authority added.

### Bounded host limits
- at most 2 Mineflayer sessions (supervisor must explicitly begin/end).
- at most 2 successful cognitive epochs per session.
- at most 3 total cognitive epochs across host lifespan.
- at most 100 native frames read seeking each new event.
- each native receive uses a 30s timeout.
- unchanged S36 per-session queue max4, batch max1, probe timeout10s,
  freshness and caller-only independent grant policies.
- the host enforces process UUID continuity, exact target identity and
  separate new entity ID per incident; duplicates are not new incidents.
- prior session's pending work is discarded on explicit end_session; old
  tickets cannot be reintroduced on reconnect.

These are in-memory, serialized, locally owned bounds. **They do not
preempt arbitrary synchronous CPU work in the supplied deterministic
cognition callback.** Native seq is only meaningful inside its own session.

### Evidence partition
**Real World CI** requires three actual controlled native `entitySpawn`
incidents across two real Node process sessions and one persistent Java game
server. Each event must have strict event<probe seq, entity identity, exact
session, and create an automatic cognition with no Action owner.

**Offline negative tests** reject foreign/reused session, old tickets,
unexpected stream EOF/timeouts, entity replays, queue carryover and limits.
These tests must not be called independent physical reconnect tests.

### Important nonclaims
This is a bounded host run explicitly staged by a CI experimenter, *not*
a permanently running autonomous agent or crash-resilient daemon.
The reconnect is supervised **clean shutdown**, not unexpected TCP
disruption or loss-of-power restoration. The zombie sequence is created
and killed by privileged server commands; no unstructured wild World threat
discovery or goal synthesis. The current intent, independent grant callback
and previous rev1 memory are all fixed by the experiment. The World data
are genuine Mineflayer-native game observations, not cryptographic
independent physical truth. The scheduler still cannot propose, authorize,
issue or physically perform any Action. No new retained learning, LLM
reasoning, or Paper2 reinterpretation is claimed.

## Qualification
Infrastructure missing => BLOCKED. Wrong event/seq/session/correlation,
unqualified source, premature process end, failure to observe all three
genuine incidents, unwanted Action, or unclean teardown => FAIL.
Only dynamic exact-HEAD `S37_REPORT.status=PASS` plus full Push and PR
CI success authorizes terminal
`THREE_REAL_NATIVE_EVENTS_TWO_SESSIONS_BOUNDED_COGNITION_NO_ACTION_QUALIFIED`.
Keep PR Draft/unmerged.
