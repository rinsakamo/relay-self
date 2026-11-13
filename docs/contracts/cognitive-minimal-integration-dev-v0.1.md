# Cognitive v0.1 — minimal CPU Schema → SystemOne → original Owner DEV

Parent #828 §27 (2026-11-13); children #829, #831, #841, #843.

**Status: initial offline-integrated DEV seam, not real Gemma or real World.**
This is stacked on #842's CPU contract code. It deliberately leaves the existing
single-`CurrentIntent` implementation in place and refuses a second new
physical proposal while that legacy owner is busy. It does not implement the
planned multi-Intent `IntentBook`.

## Implemented here

- `cognitive_minimal_dev.py`: bounded pure CPU pattern matching and source-bound
  WorldPercept. Typed `SchemaPattern` is identical for innate and accepted learned
  definitions. No LLM or memory retrieval occurs in Schema. Initially:
  Homeostatic HUNGRY → HUNGER_RELIEF/EAT/FOOD, Defensive ZOMBIE_NEAR
  → DEFEND_SELF/ATTACK/ZOMBIE, Body FATIGUE_HIGH → constraint sensation
  without a Goal. Both Goals may be simultaneously projected. The source
  Percept/targets must be provided by existing qualified perception gateway;
  the sample caller must **not** forge native readbacks.
- Finite `Goal × Skill@version × Target` options, up to eight concrete items.
  L1 context combines Schema CURRENT, live `IntentCommitment` state and up
  to three supplied RECENT 3Self summaries. Optional RETRIEVED memory is absent.
  L1 uses the existing `BoundedChoiceRequest`, strict finite IDs, explicit
  `ESCALATE_L2` and `DEFER`, `think_allowed=False`. The existing
  `LlamaCppRelayProvider` can run generated bounded or configured Jev.
- On response, compare just selected dependencies against freshly generated
  current SchemaFrame and known Skill version; **do not** require global epoch
  equality. Disappeared target, changed World session, unavailable Skill,
  or occupied legacy Intent owner block a new physical proposal.
- `prepare_existing_owner_action` uses existing `IntentCommitment.commit`,
  `SkillExecution.start` and `ActionLifecycle.propose`. Its return
  preserves the selected Target/World session and **stops at PROPOSED**. Native authorization, S49/ActionPort, Mineflayer
  submission, ACK, post-World observation and OUTCOME are not bypassed or
  simulated as successful.
- For unresolved Goals, `prepare_l2_pattern_request` constructs a single
  existing RelayEngine OPEN/SystemTwo request (no Schema model call).
  `parse_l2_pattern_proposal` admits only exact typed CPU SchemaPattern JSON,
  with no executable code, unknown predicates, extra fields or capability grant.
  This L2 seam is **offline-tested with a mock provider**, not live Gemma.
- A proposed learned Pattern is only published by a caller with affirmative
  Self acceptance, expected registry revision, supported CPU predicate, known
  schema and existing physical Skill capability. Publication yields a new
  immutable PatternRegistry snapshot; previous versions are preserved.

## DEV negative tests

`python -m pytest tests/test_cognitive_minimal_dev_v01.py -q`

D1 hunger + food → EAT L1 → existing Owner Action **PROPOSED**.
D2 simultaneous hunger + zombie → both Goals, defense eligible.
D3 hunger without a FOOD target → L2 escalation selectable, Need persists.
D4 in-flight target loss → reject/no Intent/Action.
D5 blocked L1 thread → independent CPU Schema/FAST epoch completes.
D6 Goal-less fatigue → L1 constraint sensation.
D7 bad/unauthorized L2 pattern → no install; valid accepted pattern → new snapshot.
D8 unrelated World update → selected still-valid dependency retained.
Additional invalid option, foreign session, unavailable Skill and busy legacy
single Intent owner controls.

These tests use synthetic input and provider decisions. D5 only proves a
threaded *possibility*, **not actual GPU contention or FAST latency**.
No physical Action is issued by these tests.

## Boundaries and next real measurements

1. **Read-only WorldBody integration:** translate actual S49/Mineflayer native
   hunger, inventory, visible zombie, fatigue and source-qualified
   `world_session_id/sequence` into `WorldPercept`. Do not infer item existence
   or native availability from L1 text. Preserve existing primary S49 Action
   issuer. Use a DEV-only opt-in bridge rather than modifying production owner.
2. **Real Gemma:** with local llama.cpp available and local user-approved grant,
   use `experiments/cognitive_minimal_l1_benchmark.py` to invoke the existing
   `LlamaCppRelayProvider` via explicit model/endpoint, warmups and repeated
   D1–D3 samples. Record exact model SHA/version, runtime, GPU, prompt tokens,
   p50/p95 provider latency and selection error rates. Do **not** declare
   0.2s achieved without measurements.
3. **Physical execution:** only after selected-Target revalidation at native
   ActionPort, use the original S49 authorized path to issue EAT/ATTACK;
   collect ActionLifecycle ISSUED and actual qualified WorldBody Outcome
   separately. Current `OwnerProposal` has no native ActionPort call.
4. **L2:** `ESCALATE_L2` is a preserved typed cognitive routing decision.
   An offline one-shot OPEN/SystemTwo request and strict response parser exist.
   Live Gemma invocation on this path, Self acceptance owner, persistent
   registry, richer CPU predicates and true GPU preemption/release are
   *not* yet wired; learned pattern proposal/validation is offline only.
5. **Multi-Intent:** #843 calls for an `IntentBook` with multiple active
   commitments and independent SkillRun owner checks. This branch intentionally
   uses original single slot to avoid a new physical issuer. Do not claim
   multiple simultaneous Intent/action support.

`DEV / QUAL / SCIENCE` remain distinct. The GitHub CI workers cannot access
the operator's local RTX 3060, WSL2, Gemma socket or private Minecraft world.
