# C Lane C1 longitudinal checkpoint continuity — Stage28 typed A/B (DEV)

**Scope:** read-only source qualification and adversarial offline test. Original Stage28 #988 and C integration #1007 unchanged; this Draft stacks on #1007, not on Stage27 #990. No real World, GPU, LLM inference or physical Action was run.

## Added boundary

`verify_c1_across_stage28_typed_epoch` returns an immutable `C1TypedContinuityWitness` only if:
- source is the **same original COMMITTED, fully typed World+A/B cut** checked with `verify_typed_generation`, matching the original Stage28 plan's World ID, generation, fork, SHA256 and both Self IDs. World-only cuts cannot pass.
- original archived `selves/{self_id}/cognition.json` is byte-identical to the newly restored **original Owner**'s `cognition.json`; in-memory `PersistentCognition` must also match. A C1 `Memory` must already have been adopted in the source cut; the function never inserts it.
- a source-qualified Stage28 `Stage28FreshL1Eligibility` covers the new World/Paper/native epoch for both original A/B with old Action/Skill/L1 replay and physical issuance disabled; original Owner's own adopted *fresh* Mineflayer probe must be from the newly admitted session and exact native lineage.
- Stage28 old/new process clock domains are **never compared numerically**. History in a Memory is not a fresh WorldBody fact.

The returned witness explicitly flags `real_historical_world_action_attested=False` and `physical_action_issue_authorized=False`. Both the eligibility receipt and the C1 historical content are inputs subject to upstream original-issuer verification; their dataclass shape alone is not proof.

## Actual typed-generation integration test (synthetic source)

1. Construct the original Stage28 retired A/B test owners and WAL. In the test **only**, attach the existing `CognitionOwnerCohort` and have original A explicitly accept a synthetic C1 native `Memory` candidate. Write it using the existing `save_persistent_cognition`. B remains unchanged. Simulate retirement via the test fixture.
2. Use the real Stage28 `capture_retired_resident_typed_world` to create one immutable World+A/B COMMITTED cut (three synthetic World dimension directories), not separate unpaired World and Self generations.
3. Use the real `prepare_stage28c1_inert_restore` + `create_execution_copy` verification. Stage28's own synthetic new native/Paper dual-clock helper is pointed at **this** exact execution copy (rather than creating another fake source). The new two-Self Paper/native link and Stage28 `stage28_require_fresh_l1_eligibility` must succeed. Original A Owner adopts a new-session probe.
4. Read back retained C1 across the exact cut with the new verifier. Compare read-only C3 contexts with the same current cues and immutable L1 choices, masking the C1 memory vs reading retained C1. Conditional C2 revision remains deliberately **synthetic**, and no actual Gemma selection occurs.
5. Adversarial cases: foreign Self/world/native session, wrong source boot, unqualified new L1 epoch, wrong Memory ID, stale probe, tampered archived/restored cognition, and World-only checkpoint.

## Distinctions and next step

This verifies durability *through a real original typed checkpoint implementation in a synthetic World fixture*, not the existence of a real original Stage27 C1 event. A separate Stage27 #1003 exact-original-issuer synthetic test validated one 3-Action child => C1 Memory proposal. Their source World/Paper/session IDs are not joined into one verified live trial.

**Still needed for real DEV:**
- operator's actual Stage27 sealed WAL/native probes and terminal child Skill owner evaluation;
- same World UUID and physically quiescent full A/B Stage28 COMMITTED generation, with independent Paper presence and native rejoin;
- independent genuine C2 revision acceptance when C3 reuse is claimed;
- actual new-epoch bounded Gemma A/B number selection, not merely changed context.

**Classification:** DEV_ORIGINAL_TYPED_CHECKPOINT_SYNTHETIC_ONLY / REAL_WORLD_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN.
