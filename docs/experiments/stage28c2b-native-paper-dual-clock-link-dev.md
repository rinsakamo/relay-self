# Stage28c-2b — independent native World-day time / Paper process tick (offline DEV)

Stack on Stage28c2b clock contract Draft #982, which is stacked on partial
observation-only recovery Draft #981. Parent Issue #966. No real Paper/native
trial has yet occurred here; **REAL_REJOIN_HOLD remains**.

## Finding from actual repository source

The original `verify_native_spawn_probe` in
`src/relay_self/owned_native_rejoin_cohort_dev.py` computes native
`observed_world_tick = snapshot.time.day * 24000 + snapshot.time.time_of_day`.
This is Minecraft **World day time**.

Paper `TickWitness.java` obtains `Bukkit.getCurrentTick()`. This is the
**current Paper process/server tick**, independent of the native World day
time. The resident-witness plugin separately creates a second
`ResidentPresenceWitness.java` boot ID. Both Paper plugins use
`Bukkit.getCurrentTick()` in the *same owned Popen* and can be compared
within that boot, but **neither Paper clock can be numerically compared
to the native World-day time**. The source checkpoint W221 is historical
and also MUST NOT be compared to the restarted process clock.

### Code/contract changes

1. `WorldResidentLifecycle(..., independent_native_world_clock=True)`:
   opt-in for fresh owned Paper boots `epoch >= 1` only. Keep the native
   observation as a separate original receipt, and store only the current
   Paper process tick in the lifecycle's `last_observed_world`. Do not
   numerically compare native World day tick to Paper tick. Default legacy
   lifecycle behavior remains unchanged for existing callers.
2. Original `OwnedResidentPhysicalBridge` accepts opt-in
   `forbidden_native_sessions=frozenset(all_historical_sessions)`.
   Refuse a recycled historical native session immediately after spawn,
   before sensor probe and original physical-issuer admission. Do not
   rely only on the most recent per-Self session.
3. `link_recovered_a_b_native_paper_body` validates after the original
   bridge's A/B login:
   - the same original recovered owner and resident work, original physical
     admission in observation-only mode, independent native PID/session IDs
     and guarded native probe refs;
   - the same owned new Paper Popen, original `PaperTickReceipt` and a
     fresh nonce ACK from its stdout; a separate owned resident
     JOIN/PRESENT/MOVE stream parsed by the existing strict parser;
   - one distinct player UUID for each Self; each must have a JOIN and
     subsequent presence before the new Paper post-login ACK;
   - **Paper tick comparisons are confined to Paper sources**; native
     world-day tick is carried without conversion or comparison.
   This does not call L1 or issue any Action.
4. `Stage28NativePaperBodyLink` is required for the separate
   `stage28_require_fresh_l1_eligibility` function. The gate checks A/B
   roster, exact original native probe refs, both distinct Paper witness
   boot IDs, current owned Paper session, physical denial, history fencing
   and new Paper local ordering. Merely creating this Python dataclass is
   NOT a substitute for the actual owner/Paper verifier.
5. All tests are synthetic contract checks. Stage28a source and Stage28c1
   restored real generation remain unchanged and read-only.

### Existing real source pins (do not mutate)

- World UUID `f9221410-b99e-417d-98f4-e98938586472`,
  fork `fork-3883122c-6edb-4017-bd82-00fc4324aded`,
  typed generation `g-000000000000`.
- Original W221, A C210, B C39; COMMITTED SHA256
  `d1425c49a5ef0ff03486931427907aeed6eccf568494efd8177ed96d3ce3f4ee`.
- Correct Stage28c1 29-file evidence manifest SHA256:
  `28d1a7548f98ab74d5e7359462e4a1f7baf5c43f80e4a9fbd4a2c74065e915c1`.

## Remaining before a real trial

- An owned execution runner must launch the validated executable fork copy
  with pinned Paper/Plugin, independent nonce tick + resident source;
  construct only recovered original A/B owners, not default fresh identities;
  install original PhysicalIssueAdmission observation-only final-stdin guard.
- The original historical-native session set must be independently derived
  from Stage28b raw evidence and manifest, including first A session,
  subsequent A rejoin and B; a manually supplied list is not proof of
  completeness. Bind this list before constructing the bridge.
- Source-linking A/B fresh probes to Paper player identities requires actual
  native child + Paper stdout and controlled independent audit. No
  `Stage28NativePaperBodyLink` may be constructed by fabricating a
  timestamp or matching unrelated process ticks.
- Bounded cleanup, real WAL persistence and post-run SHA256/mutable fork
  audit, original archives untouched; one real World trial ONLY after
  these preconditions are implemented and tested.
- No L1/Gemma, MOVE, ATTACK, EAT, REST, peer send or 60-second autosave
  is authorized or attested by this work.

Classification (when CI passes):
`STAGE28C2B_NATIVE_PAPER_DUAL_CLOCK_OFFLINE_PASS /
REAL_REJOIN_HOLD / FRESH_L1_NOT_RUN / 60S_AUTOSAVE_NOT_ATTESTED /
QUAL_NO_GO / SCIENCE_NOT_RUN`.
