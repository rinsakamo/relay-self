# Cognitive v0.1 → original S49 durable ATTACK/EAT fence: DEV compatibility audit

**Evidence type:** source/code review + fake native protocol tests only.
**Classification:** `DEV_BOUNDARY_AUDITED / S49_DURABLE_NOT_CONNECTED /
REAL_WORLD_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN`.

## Exact code lineage

- Cognitive integration: [Draft #844](https://github.com/rinsakamo/relay-self/pull/844),
  `experiments/cognitive_minimal_minecraft_dev.py`,
  `experiments/run_cognitive_minimal_world.py`.
- Original physical fence: [Draft #767](https://github.com/rinsakamo/relay-self/pull/767)
  audited at `efb6d14dfe9f2194273c7e0e9398a4fc0ad69ffe`,
  `src/relay_self/s49_nonmotion_physical_fence.py` and
  `docs/unified-v05-s49-attack-eat-durable-fence-dev.md`.
- Original S49 uses `NormalSessionActionExecutor`, original S49
  `ActionSupervisor`, native S15 and S16, and optional
  `OriginalS49NonMotionFence`. This physical fence contract still does **not** exist as a usable
  imported module in #844's current stacked base. The **read-only**
  correlated probe request ID protocol has now been ported from #767.
- Current main-based #844 physical action experiment calls the older
  `controlled_minecraft_vertical.execute_decision` and its own existing
  `ActionSupervisor` (one physical issuer per invocation). This **is not**
  the long-running original S49 Action owner and has no pre-ISSUE physical
  WAL.

## Original S49 contract that must survive any handoff

1. **Native source:** an exact correlated original native `probe`, with
   `session_id`, monotonically increasing `seq`, `request_id` and
   `Provenance("mineflayer", f"{session_id}:{seq}")`. Both selected L1 Target
   and actual S49 owner must use this original source; no synthesized request
   IDs and no assumption that reading "a newer snapshot" suffices.
2. **Owner:** original `NormalSessionActionExecutor` / original
   `ActionSupervisor`, independently scoped PROPOSE and ISSUE grants.
   `Goal × Skill × Target` is advisory selection input, never a new
   authority to issue. The existing original Intent and S15 physical
   transaction own the action; no parallel EAT/FIGHT issuer.
3. **Before any possible world effect:** after original source/grant checks,
   `OriginalS49NonMotionFence.prepare_attack()` or `prepare_eat()` must
   persist an exact `PREPARED_UNRESOLVED` row (original Self/session/Intent/
   Action/subject/probe seq/request/source). #767 uses file/directory fsync,
   atomic replace, file lock, SHA-256 and compare-and-swap. Only **after**
   durable prepare may the original S49 `ActionSupervisor.issue()` and
   adapter effect send occur. A failed prepare **must not** issue.
4. **Restart:** original Self must restore the existing journal and call
   `require_clear()` before the first new World/Action. Any unresolved
   journal row is STOP/UNKNOWN, never auto-retry or success. A different
   Self, stale writer, duplicate Action ID or corrupt journal must fail
   closed.
5. **Terminal:** the exact original terminal `ActionLifecycle` in original
   supervisor identity is required, with original Intent/Action/Probe.
   An ACK is not itself proof of physical effect. For ATTACK, #767 verifies
   applied `attack_entity` plus native after-probe, but structurally records
   `death_attested: false`. For EAT, #767 requires two correctly ordered
   child ACKs, native after-probe, food increase and inventory-item decrease;
   otherwise `PREPARED_UNRESOLVED` stays unresolved.
6. **No physical exactly-once inference:** multi-file C1 MOVE journals and
   the S49 non-motion journal are different ownership/atomic domains.
   Do not derive "no double effect" or combat kill attribution from
   a one-shot native request or a ledger row.

## Current #844 matrix

| Requirement | #844 current reality | Verdict |
|---|---|---|
| CPU Schema bounded Goal/Skill/Target and existing L1 selection | Implemented, offline-tested | DEV PASS |
| L1-selected Target revalidation after native probe | Implemented in bounded main-based runner | DEV PASS |
| Original S49 S15 correlated `probe.request_id` | Backported optional request ID through Python + Node + bridge; two additional independently correlated post-L1 probes now checked in optional read-only shadow | DEV PARTIAL; **not S49 issuance** |
| Read-only selected Target + two original-S49-shaped native probes | `--s49-readonly-shadow` tests steady EAT inventory slot/no nearby Entity and stable single Zombie ATTACK, returns typed non-authorizing witness | **OFFLINE DEV PASS**; no owner grant |
| Self/Intent identity and selected Goal/Skill closure | Witness carries original Self scope, caller-proposed Intent ID, current Schema revision, and verifies selected Goal; no original Intent commit | **OFFLINE DEV PASS**; uncommitted candidate |
| Original S49 `NormalSessionActionExecutor` ownership | Current physical path instead calls `controlled_minecraft_vertical`; shadow issues nothing | **BLOCKED** |
| Original durable `prepare_*()` before physical ISSUE | #767 not in current import/ownership path | **BLOCKED** |
| S49 terminal identity + verified native S16 closure | Existing main-based supervised Action Outcome only | **BLOCKED** |
| EAT item-count delta alongside food and ACKs | Additional separate #844 readback attestation; not S49 ledger seal | PARTIAL |
| Restart STOP on unresolved prepare | #844 has only best-effort in-process failure audit | **BLOCKED** |
| In-flight L1 does not stop CPU-only Schema evaluation | 48-tick read-only simulation, not live GPU preemption | DEV PASS (offline only) |

## Fail-closed interim DEV policy

#844's CLI defaults to no physical Action. L1 post-decision source
revalidation now sends a unique `observe(request_id)` and requires the
same `request_id` on the `probe` observation. Optional
`--s49-readonly-shadow` requests a second correlated native probe and
runs `assess_s49_readonly_handoff()` on the *same selected* Target. It
returns a typed, non-authorizing, non-issuing witness or a refusal. Two
separate probe request IDs are **not** proof of distinct physical World
ticks or STOP/settling. The shadow flag is incompatible with
`--execute-native`. Legacy uncorrelated probes
remain readable for other callers but cannot satisfy this check. `--execute-native` additionally
requires `--acknowledge-unfenced-dev` *and* explicit existing
`--grant-real-world --grant-real-llm`; the direct DEV function also has a
separate `acknowledge_unfenced_dev=True` guard. Missing any required gate
prevents Action. The flag **does not** install a physical fence; a granted
legacy run remains explicitly `UNFENCED_DEV_ONLY`, unsuitable for
exactly-once, S49 durability, QUAL or SCIENCE claims.

## S51 original food-policy divergence (OPEN, not an admission)

Original #767 `src/relay_self/eat_hunger.py` owns `EatCursor.choose` and a
source-controlled ordered `ALLOWED_FOODS` catalogue. By contrast, #844
constructs L1 food options from the `ControlledScenario.edible_item_names`
configured for the bounded main-based Action port. These are **not the same
source of authority**. For example, when both bread and apple are in inventory,
the pinned original S51 cursor prefers bread; a valid L1 selection of apple
must not be silently retargeted to bread. Likewise, a Scenario-declared food
absent from original S51 policy cannot be treated as original-S49 ready.

#844 now emits `S49ReadOnlyHandoff` with `self_id`, a
`proposed_intent_id`, current `schema_registry_revision` and native
Goal/Skill/Target/slot or entity ID. Its `original_s49_intent_committed`,
`original_s49_policy_verified`, `original_s49_authorized` and
`physical_action_issued` remain **false**, including on
`S49_SHADOW_READY`. The proposed Intent ID is metadata only; no new
Intent/Action Owner and no S49 grant is created.

**Unresolved before full original-S49 ISSUE:** original S51 must read and
accept the *exact* L1-selected food/slot using its native physical policy and
the current original probe; any mismatch must return RECONSIDER/REJECT,
**never choose a different food behind L1's back**. This must be implemented
with the original S51/S49 code when stacked lineage is reconciled, not by
hardcoding a second food hierarchy into Cognitive Schema.

## Suggested original-owner migration (not implemented in #844)

- First reconcile the stacked branches and adopt #767's existing tested
  original S49 fence and `NormalSessionActionExecutor` without copying it
  or introducing another physical Action issuer.
- Adapt L1 `Selection.option` to the original owner grants, carrying exact
  Target identity, original World session, Intent scope and native source
  reference. #844's read-only double-probe witness can be a proposed
  *candidate* for the original S49, but cannot substitute for **that
  original Owner's own admission**, complete steady-window and post-move
  checks, independently scoped PROPOSE/ISSUE grants, or original S15/S16
  transaction. Do not transfer this witness as authorization.
- Route EAT and ATTACK only through original S49. Run #767's restore,
  CAS/stale source, pre-ISSUE disk failure, missing ACK, wrong after-probe,
  duplicate action, crash/restart STOP and child receipt attestation tests.
  Include a negative that asserts one current L1 option cannot dispatch via
  both the main experimental issuer and S49.
- Only after exact original owner/manifest and grant-backed real World
  readbacks are observed should actual S49 EAT/ATTACK be reported as
  physically qualified DEV. QUAL and SCIENCE remain separate.

**Do not infer that #844 is S49-integrated from its passing main GitHub CI.**
