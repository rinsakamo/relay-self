# Stage28c-2c — original recovered A/B fresh L1 preflight (CPU/offline DEV)

Parent [#966](https://github.com/rinsakamo/relay-self/issues/966);
depends on Stage28c2b [#998](https://github.com/rinsakamo/relay-self/pull/998)
and real original A/B rejoin independent audit PASS at exact execution HEAD
`3469ce11a19a2ea15e635fcebfddaf3664e69878`.

**Do not use that consumed World again**. The previous result proves original
A/B adopted new native WorldBody then retired normally. It does NOT prove
the new transient Body was persisted for reuse, nor any fresh Gemma decision,
Action, online autosave or QUAL/SCIENCE finding.

## What this PR does

`src/relay_self/stage28c2c_fresh_recovered_l1_dev.py` creates a
`Stage28c2cFreshTurn` from the **actual original restored**
`CheckpointedCognitiveOwner` while both original A/B still have live
verified native session and their **exact** source-qualified
`current_worldbody_observation`.

- Requires `stage28_require_fresh_l1_eligibility(plan, world, A/B logins,
  Paper/body links, actual single idle-slot witness)`; its receipt is an
  eligibility check, **not** a model call or proof of actual Paper execution
  when constructed synthetically.
- Uses the owner's **retained** `pattern_registry` and original
  `IntentCommitment` with the existing `cpu_schema_epoch` and
  `assemble_l1_select`. **Never** calls
  `initial_patterns_with_relative_move()` to fabricate a new innate MOVE
  schema after restore.
- Builds Target candidates only from same-native source snapshots:
  bread in a known inventory slot, observed zombie entity IDs, or
  RELATIVE controls **only if the saved owner already has an EXPLORE pattern**.
  An available Skill requires an explicitly supplied source-validated
  `preset_by_skill`; a fabricated new Skill or absent Preset is HOLD.
- Native food/health/oxygen/coverage are model-facing current source facts.
  UNKNOWN oxygen is `None` and never a made-up positive oxygen reserve.
  An empty inventory/nearby scene is allowed: the existing CPU schema may
  produce zero physical candidates, followed by **ESCALATE_L2 / DEFER**.
  Neither fallback actually invokes L2 during this Stage28c2c milestone.
- Freezes numbered choices, original owner session/epoch, Paper session/boot,
  native probe request/seq, registry revision and current contexts under a
  SHA256. The request has a fresh unique ID and original Identity context.
  `think_allowed=False`. A stale candidate/request is rejected.
- `validate_fresh_original_l1_result` accepts a ticket only from the
  existing `ResidentLlamaInferenceLane` attached to that same original
  `OwnedResidentPhysicalBridge`, with fresh `CognitionMode.BOUNDED`,
  registered current Self/native/World epoch, same original adopted
  WorldBody and frozen candidates. Calls `lane.result(ticket)` rather than
  trusting a supplied choice. Normalizes the *already returned* model
  decision locally with `RelayEngine` (no second GPU POST).
  Readback returns a non-motor `Stage28c2cL1Result` only.
  `run_one_fresh_original_bounded_choice` performs the **single actual**
  `lane.submit`/`await_result`/source-check sequence when invoked by a real
  owner runner; no hidden THINK retry and no native issue on any choice.
- `OwnedResidentPhysicalBridge.attach_observation_only_bounded_l1` permits
  attaching the original single-slot GPU lane *after* source-linked A/B
  WorldBody adoption, and only when there are no Actions and
  `PhysicalIssueAdmission.observation_only` stays true. This keeps the
  existing `bridge.logout` and `world_only_quiescence` GPU fence/retirement
  checks on the same lane. No physical issue API or Intent/Skill writer is
  added.

## Original source pins

- World UUID: `f9221410-b99e-417d-98f4-e98938586472`.
- Restore fork: `fork-3883122c-6edb-4017-bd82-00fc4324aded`.
- Original Stage28b `COMMITTED.json` SHA256:
  `d1425c49a5ef0ff03486931427907aeed6eccf568494efd8177ed96d3ce3f4ee`.
- Stage28b evidence 285/285 manifest SHA256:
  `7a202d68f6d275a0031f9c7091e0e1e7f33c4976c4565461d425e040f87209f4`.
- Stage28c1 29/29 manifest SHA256:
  `28d1a7548f98ab74d5e7359462e4a1f7baf5c43f80e4a9fbd4a2c74065e915c1`.
- Consumed real A/B rejoin audit-PASS evidence 29/29 SHA256:
  `5a684637746ebf7e9b406d8dd7ab67601055e01b01430d96afbadd87dcaedb84`.
- Stage28b historical W221, new Paper `Bukkit.getCurrentTick()` and
  new native Minecraft full day time remain **separate clocks**.

## Qualification boundary and next work

This PR is intentionally **CPU/offline-only**. All tests use synthetic
Paper/native/model receipts; no real Paper, actual Gemma POST, physical
Action, Skill start, Intent commit, peer send, checkpoint or autosave.

To qualify a future **real Stage28c2c L1** trial, LocalCodex must build
a separate owned runner from the already verified Stage28c2b observation
runner with a **new** isolated execution copy, and:
1. Re-verify original typed A/B archive, old session denylist and fork copy.
2. Pin an **actual** Gemma GGUF/model alias, owned PID/GPU, local
   endpoint, one backend slot idle and exclusive backend ownership; NEVER
   infer the model's identity from a synthetically supplied receipt.
3. Start a new owned Paper session; obtain independent A/B JOIN/PRESENT,
   post-presence Paper main-thread nonce and request-bound native probes.
4. Adopt exact native WorldBody into original A/B owners; freeze new
   CPU-derived candidates from **saved Registry** using this module.
5. Attach the same actual GPU lane to the original bridge, submit at
   most a bounded numbered request per Self using existing
   `ResidentLlamaInferenceLane.submit / await_result / result`, and
   validate its original result with this module. No prompt-/model-selected
   Target parameter changes.
6. Never issue a physical Action or start a Skill/Intent from that number.
   L1 ESCALATE is a choice, **not a hidden L2 model call**.
7. If the model times out, backend uncertainty/HOLD persists until
   actual provider thread terminates and `/slots` is source-verified idle.
   `bridge.logout` must fence both Self/GPU work; save/stop Paper only on
   independently verified retirement, log raw request/response SHA256 and
   original owned PID/slot/probe sources.
8. A separate audit must reparse model POST original request/response,
   exact candidate hash, choice number, Self/native/epoch, body provenance,
   old-result rejection, owner A/B retirement and all Paper/native evidence.

**Current scope on PR creation:**
`STAGE28C2C_ORIGINAL_OWNER_FRESH_L1_CPU_PREFLIGHT_DEV_ONLY /
REAL_GEMMA_L1_NOT_RUN / PHYSICAL_ACTION_NOT_RUN /
60S_AUTOSAVE_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN`.

Do not reclassify the proven Stage28c2b real rejoin as L1 evidence.
