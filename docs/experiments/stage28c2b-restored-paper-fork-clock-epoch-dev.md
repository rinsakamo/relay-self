# Stage28c-2b — restarted Paper **new boot epoch** contract (DEV / partial HOLD)

Parent #966; based on Stage28c2b observation-only partial Draft #981,
Stage28c2a #977, Stage28c1 #973 and Stage28b #969.
This is a **clock/provenance correction and contract tests** only.
No real Paper, Mineflayer, Gemma, Action or peer transmission is run here.

## Source provenance — immutable

- Stage28b original typed generation `g-000000000000`, World UUID
  `f9221410-b99e-417d-98f4-e98938586472`, source branch
  `p0d-real-resident-presence`. Saved physical World tick W221,
  A cognitive cut C210, B cut C39.
- Original COMMITTED SHA256:
  `d1425c49a5ef0ff03486931427907aeed6eccf568494efd8177ed96d3ce3f4ee`.
- Stage28b 285-file evidence manifest digest:
  `7a202d68f6d275a0031f9c7091e0e1e7f33c4976c4565461d425e040f87209f4`.
- Stage28c1 original inert fork receipt:
  `fork-3883122c-6edb-4017-bd82-00fc4324aded`.
- **Correct** Stage28c1 29-file evidence manifest digest (64 hex):
  `28d1a7548f98ab74d5e7359462e4a1f7baf5c43f80e4a9fbd4a2c74065e915c1`.
  An earlier user-facing prompt had 63 digits: do not use it.

## Clock model

The archived W221 is a tick in the **old Paper process**. It is not
the starting tick of the new Paper Popen. Never add W221 to new process
ticks, and do not reject a new legitimate process tick 3 merely for being
smaller than W221. Old A/B cognitive cut values C210/C39 are retained
as *history* and require a new WorldBody observation.

`Stage28InertRecovery` now retains a SHA256 of the verified original
typed COMMITTED marker, so an independent runner can compare against
the same source committed blob. `Stage28ForkPaperEpoch` declares
the source World/branch/generation, saved W tick, COMMITTED digest,
new fork branch, fresh owned Paper session/boot, owned process PID,
the **new-process** tick, authenticated tick-ref, and the supplied complete
historical native session rejection set.

`observe_new_fork_paper_epoch(ExecutionCopy, OwnedPaperWorld,
historical_native_sessions=...)` requires:
- Stage28c2b copy with exact original A/B owner state, restored World
  UUID and fork branch; observation-only issuer, full OFFLINE roster;
- the actual original `OwnedPaperWorld` instance whose server dir and
  world dir equal the source-verified executable copy;
- a **fresh** owned Paper session, live owned Popen/PID;
- real `PaperMainThreadTickReader` main-thread ACK bound to exactly
  that Paper session and its owned process log, with boot/nonce/hash
  witness and READY before ACK.

`stage28_require_fresh_l1_eligibility` now REQUIRES the boot witness,
and checks source COMMITTED digest, source vs fork identity, Paper
session, new epoch and boot, historical native sessions, and that A/B
WorldBody ticks belong to the **same new Paper clock** and are no earlier
than its boot witness. The source saved W221 is never used as a numeric
threshold. No L1 inference is performed by the validator; no
physical Action issue permission is granted.

### One Paper boot needs at least two tick reads

The original `PaperMainThreadTickReader` defaults to one read per Paper
session for legacy Stage24g / Stage28b source qualifications. Stage28c2b
requires a boot-local tick before native JOIN **and** another independently
nonce-qualified main-thread tick for `OwnedPaperWorld.stop_and_save()`.

Use explicit `allow_repeated_same_boot=True` only in the restored Paper
runner's reader. Under that opt-in, the reader requires **every read**
to have a fresh nonce/ACK/log correlation, the **same owned Paper session
and boot ID**, and a nonregressing tick. It rejects a different Paper
session reusing that boot, an unexpected new boot in the same session,
and a regressed tick. It is not an arbitrary tick override or global
clock offset. Existing legacy readers default to `False`; their one-shot
contract and tests remain unchanged.

The owner must stay observation-only; the second read is for save/stop
provenance, not Action admission.

### Source-capture and classification boundary

Passing a typed Python dataclass or offline synthetic test is not proof
that the Paper process ran. Only an actual pinned Paper + witness plugin
owns live tick ACK/log evidence; a real runner must also independently
tie both native probes to *this* Paper process and verify independent
Paper JOIN/PRESENT/QUIT. Any missing raw provenance is HOLD, not L1.

The original `NativeLoginEvidence` contains source claims; it is
not self-authenticating. The actual bridge must verify all historical
native sessions and the original native final-stdin guard, NOT claim
success based only on synthetic boolean flags.

### Required next task before any real one-shot

Implement a single owned executable Paper/native runner on a **new
isolated copy**, not the Stage28c1 original, with actual source-qualified
native probe, independently owned Paper presence, original A/B owner
adoption, bounded logout/cleanup and source + copy SHA256 audit.
Only then allow one LocalCodex real World DEV attempt.

Do not run Gemma or physical actions at Stage28c2b. A fresh real L1
numbered choice belongs to a later Stage28c2c experiment, with
independent idle GPU slot and source qualification.

Current result:
`STAGE28C2B_CLOCK_EPOCH_OFFLINE_CONTRACT_PASS /
REAL_RECOVERED_OWNER_PAPER_REJOIN_NOT_RUN / FRESH_WORLDBODY_NOT_RUN /
FRESH_L1_NOT_RUN / 60S_AUTOSAVE_NOT_ATTESTED / QUAL_NO_GO /
SCIENCE_NOT_RUN`.

This deliberately does not upgrade the earlier REAL_REJOIN_HOLD.
