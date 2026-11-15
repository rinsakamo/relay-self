# P0-D #860 — Stage 16: cognitive/native/work-epoch rebind bridge

Stacked on Stage 15 #878 → Stage 14 #876 → Stage 13 #874. Restrictions:
**no inference, no peer transport, no real Paper claim, no autonomous
Actions, no QUAL/SCIENCE**.

## Concrete connection

The existing `CoordinatedCheckpointHost`, `CoordinatedAutosaveRuntime`,
`CognitionOwnerCohort`, `OwnedPaperWorld`, `OwnedNativeRejoinCohort` and
`PhysicalIssueAdmission` remain the canonical owners. Stage 16 adds a
narrow `OwnedCognitiveNativeBridge` and `InertScopedWorkEpoch` so those
interfaces can be composed for a read-only/no-inference A/B experiment.

1. Both native sessions and cognitive owners begin with the same current
   physical sessions and a fixed complete A/B roster.
2. After supervised full-cohort STOP, `CognitionOwnerCohort` calls
   `bridge.close`, closing the existing physical gate and then the scoped
   work/communication gate. Attempted GPU work or outgoing peer messages
   taint the epoch irreversibly; flipping a boolean cannot clean it.
   Existing cognitive owners freeze typed Intent/Skill/Memory/peer/WAL.
3. After the controlled Paper save/stop, COMMITTED and restart, the
   host awaits `bridge.prepare_native_rejoin`. Actual native bridge
   processes must be terminated/relaunched and provide new spawn plus
   request-correlated probe and actual World clock. The strict scoped
   registry verifies the old/new session before allowing cognition rebind.
4. `CognitionOwnerCohort.rebind` invokes `bridge.external_native_rejoin`.
   It rechecks the current actual native process and immutable receipt,
   and rotates **only the original physical issuer** with the held token.
5. `bridge.release` requires every A/B rebind AND both source-derived
   WorldBody probe clocks. It first rechecks both live session IDs,
   checks the clocks against the previous cognition owner, and invokes
   `CognitionOwnerCohort.observe_fenced_rejoin_world_tick` while the
   cognition and physical gates are **still closed**. Only then does
   the existing physical issuer release. No native physical issue lease
   can be admitted in a fresh session before its WorldBody clock.
6. A missing/ended/stale B session or regressed WorldBody clock HOLDs
   the *whole* physical cohort while retaining the already committed
   World+Self generation as inert evidence. A future 60-second pulse is
   eligible only after a successful whole-cohort rebind and release.

## Strict scope and nonclaims

`InertScopedWorkEpoch` proves no GPU task or transport message was
submitted **through this particular no-inference/no-peer owner**.
There is no L2 engine, no unbounded message transport, no external
GPU executor or arbitrary W3 action scheduler in this limited scope.
Attempting such work through the registry permanently taints the
epoch until operator intervention. It does *not* inventory unrelated
processes or cancel unregistered GPU work. Therefore the true
`ExternalRejoin` flags are scoped to an explicitly no-inference DEV
experiment only, and MUST NEVER qualify an actual running L1/L2 RelaySelf.

`NativePreparedRejoin.probe_world_tick` is derived from the new
Mineflayer process's request-ID-correlated sensor observation, not
from an arbitrary function parameter. The existing real cognition
owners and an owned OS subprocess that **imitates** Paper are used in
offline tests; the native stream is simulated in CI. This is not
real Minecraft nor validated GPU retirement.

The next real experiment still needs authentic pinned Paper 1.21.8
and plugin JARs, operator EULA assent, isolated localhost A/B sessions,
source-qualified real STOP and Paper ACK, and a genuinely separate
GPU/transport retirement source if model tasks are enabled.

Classification after green exact-head CI:
`COGNITIVE_NATIVE_WORK_BRIDGE_OFFLINE_DEV_PASS /
REAL_MULTI_SELF_AUTOSAVE_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN`.
