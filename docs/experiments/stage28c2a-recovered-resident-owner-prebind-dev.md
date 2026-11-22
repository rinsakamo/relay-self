# Stage28c2a — original typed A/B cognition into an OFFLINE resident owner (DEV)

Parent [#966](https://github.com/rinsakamo/relay-self/issues/966). Stack on Stage28c1 [#973](https://github.com/rinsakamo/relay-self/pull/973) and Stage28b [#969](https://github.com/rinsakamo/relay-self/pull/969). Stage24f HOLD and Stage27 PLACE remain unchanged.

## Exact real source provenance, not a substituted fixture

Stage28b original physical World saved in the typed committed generation:
- World UUID `f9221410-b99e-417d-98f4-e98938586472`; source branch `p0d-real-resident-presence`; generation `g-000000000000`.
- World stopped tick 221; A cognition cut 210; B cognition cut 39.
- Stage28b 285-file original evidence manifest SHA256 `7a202d68f6d275a0031f9c7091e0e1e7f33c4976c4565461d425e040f87209f4`.
- Original generation `COMMITTED.json` SHA256 `d1425c49a5ef0ff03486931427907aeed6eccf568494efd8177ed96d3ce3f4ee`.
- One Stage28c1 real inert file restore `/home/rinsa/stage28c1-restored-575198-20261118`, fork branch `fork-3883122c-6edb-4017-bd82-00fc4324aded`. Stage28c1 evidence manifest digest `28d1a7548f98ab74d5e7359462e4a1f7af5c43f80e4a9fbd4a2c74065e915c1`.
- Stage28b source A/B contain their **actual original identities**, zero Memories, zero Intent and Skill events, four innate Schema patterns per Self, zero learned patterns, peer deliveries and Questions, and clear canonical WALs. These are not evidence of experiential memory retention yet.
- The **actual generation directory** is under the local Stage28b evidence: `/home/rinsa/evidence/stage28b-1dcd48-20261118/`. Discover by immutable `COMMITTED.json` and manifest; do not guess or re-create its contents.

## Why 28c2 needs an intermediate owner boundary

Stage28c1 produces a verified, **inert** restored file tree, not a runtime
`CheckpointedCognitiveOwner`. Old original session IDs are historical
rejection tokens. Instantiating a new default Self with `initial_patterns()`
would silently lose the saved identity, learned patterns and Intent history.

New `prepare_recovered_a_b_resident_owners`:
1. Checks the exact committed typed source, source World UUID and branch,
   restored fork identity and all original A/B typed cut ticks via Stage28a.
2. Re-checks byte-for-byte SHA256 equality of **every restored Self**
   `cognition.json`, `owner-state.json` and `physical-wal.json` against
   the archived file. This explicitly closes the Self-file validation gap
   left by World-only file inventory checks in Stage28a.
3. Reconstructs each ORIGINAL `CheckpointedCognitiveOwner` from
   `StagedRecoveredCognition.retained` + `RehydratedSelfOwner.intent`,
   existing pattern registry, exact Skill history, peer and Question refs,
   canonical WAL and original native session record. This is a NEW Python
   object for the SAME preserved Self state, not a new default identity.
4. Attaches both owners to a single existing
   `ResidentCognitiveWorkOwner` and sets `fresh_native_observation_required`
   on both. The work owner starts strictly **OFFLINE**, refusing writes and
   stale work output. Never attach another `CognitionOwnerCohort`.
5. Creates an existing `PhysicalIssueAdmission` in resident mode with
   both old session IDs initially OFFLINE. This grants **no** physical
   Action, cannot issue a MOVE and is only the future native source-bound
   boundary. It does not invent a new Physical issuer implementation.
6. Returns a structured non-authorizing receipt and the owner handles
   for a later *actual* native bridge. No Paper, Mineflayer, GPU, peer,
   HTTP or physical Action is invoked.

**No historical Skill/Intent is auto-executed.** A surviving active Intent
in the journal remains historical state for a future *new* choice. A
nonempty Memory/Intent test checks actual restoration rather than default
Self creation.

## LocalCodex no-World preflight

After checking #966, #973, this branch's exact HEAD and all the source
hashes (including Stage28b original evidence, Stage28c1 fork files), run
using the actual checked Stage28b generation directory:

```bash
PYTHONPATH=src:. python3 -m experiments.stage28c2a_recovered_owner_preflight_dev \
  --generation "$EXACT_STAGE28B_TYPED_GENERATION" \
  --restored-directory /home/rinsa/stage28c1-restored-575198-20261118 \
  --expected-world-id f9221410-b99e-417d-98f4-e98938586472 \
  --expected-source-branch-id p0d-real-resident-presence \
  --expected-committed-sha256 d1425c49a5ef0ff03486931427907aeed6eccf568494efd8177ed96d3ce3f4ee \
  --expected-fork-branch-id fork-3883122c-6edb-4017-bd82-00fc4324aded
```

This is entirely read-only and should be independently re-run in a separate
process as a source inspection, without modifying either prior evidence
directory. Archive the output and all SHA256. The read-only tool does not
persist the constructed runtime objects across processes and does not
connect them to a real World.

## Strict scope / classification

- Source-verified off-line owner construction and canonical byte matching
  is NOT a real new Paper/native rejoin or physical invalidation of a GPU
  process. It does not prove the owner was revived in an actual Minecraft
  runtime or received WorldBody sensation.
- Stage28a's `stage28_require_fresh_l1_eligibility` requires fresh
  `WorldLifetime`, actual original `NativeLoginEvidence` for A+B and
  single-slot idle GPU source. Neither is constructed by this stage.
- Physical Action permission, L1 reevaluation eligibility, historical
  Action replay, previous L1 selection reuse are all false.

`STAGE28C2A_OFFLINE_ORIGINAL_OWNER_RECONSTRUCTION_PASS /
REAL_RECOVERED_OWNER_PAPER_REJOIN_NOT_RUN / FRESH_WORLDBODY_NOT_RUN /
FRESH_L1_NOT_RUN / 60S_AUTOSAVE_NOT_ATTESTED / QUAL_NO_GO /
SCIENCE_NOT_RUN`.

## Next Stage28c2b

Implement a separate **actual** runtime on a **new executable copy** of
the Stage28c1 fork, keeping that fork's original restored files immutable.
The existing `OwnedResidentPhysicalBridge` must use the reconstructed
A/B owner dictionary; original `ResidentCognitiveWorkOwner`; actual
`WorldResidentLifecycle` with the restored World UUID and fork branch;
the original `PhysicalIssueAdmission` and real independently owned Paper
session and new native Mineflayer A/B processes. Check source-qualified
fresh `NativeLoginEvidence` and Paper tick/probes. Never initialize
`initial_patterns()` to replace restored patterns and never substitute
the historical Stage24g World-only archive. Limit initial real trial to
actual A/B native JOIN, fresh Body perception and independent Paper
PRESENT evidence; new real Gemma L1 decision comes only after those
are source-proven and an independent idle single slot exists. No MOVE
should be forced.
