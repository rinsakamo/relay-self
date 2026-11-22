# Stage24e DEV — Need/Goal not a motor permit; Body and World return Outcome

Parent [Stage24 #911](https://github.com/rinsakamo/relay-self/issues/911), child [Stage24e #942](https://github.com/rinsakamo/relay-self/issues/942), stacked on Stage24d Draft [#939](https://github.com/rinsakamo/relay-self/pull/939).

## Architecture correction

The previous Stage24a/24c `_eligible_exploration` logic gated exploratory MOVE options on health ≥16, food ≥18, known positive oxygen, World time present, absence of nearby Entities, complete entity coverage, and no current Intent. That incorrectly treated bodily sensation/environmental information as permission to intend or attempt an Action.

**Stage24e removes the *physiological/environmental* permission**. Explore is a standing innate Schema Need, producing `EXPLORE_WORLD` as a Goal and prebound relative `MOVE` options when the **existing typed PhysicalCapability** actually exposes a compatible skill+target type. Body hunger, oxygen, health, fatigue, nearby entities, time and sensor uncertainty never mask that Goal. Nor do they silently authorize an action: model only chooses a frozen number and parameters. The original technical contracts stay mandatory: typed current native source/session, valid bound target and capability, ActionPort ownership, Intent/Skill/Action linkage, WAL, duplicate issuance and native/Paper Outcome reconciliation. A physically blocked/rejected/no-motion MOVE remains an experiment result for Self to learn from, not a prior Schema veto; **no physical-world Outcome is claimed by this offline change**.

The previously named `exploration_eligible` data field is now `exploration_need_active`, since it is not an eligibility test. The Stage24c gate audit is retained *strictly for comparing historical forensic observations*, with an explicit deprecation notice. It is never consulted by candidate generation or by revalidating a selected MOVE. Frozen model-choice records now declare `cpu_exploration_need_active` and `stage24c_gate_historical_indicators_only`; they still record the historical audit for comparison. The original Stage24b/Stage24c evidence remains immutable.

## Oxygen is an independent **SelfBody Need → Goal**

`WorldPercept.oxygen_reserve` carries a source-qualified native SelfBody oxygen sample when observed. Values are numeric, finite, nonnegative; `None` means not observed and **does not imply 0, high oxygen, or a MOVE veto**. The previous Stage24d owned-source/freshness witness is unchanged and still ensures no foreign, stale or missing oxygen sample becomes a number.

The innate pattern registry now includes `OXYGEN_LOW` → `RESTORE_OXYGEN`, with no fabricated Skill/Target. Initial DEV thresholds are body Need *signal thresholds*, not permission limits:
- reserve >10 or UNKNOWN: no `RESTORE_OXYGEN` Goal inferred
- reserve in (3,10]: `RESTORE_OXYGEN` ACTIVE, unresolved if no bound Skill
- reserve in [0,3]: `RESTORE_OXYGEN` URGENT, unresolved; `OXYGEN_LOW` FAST cue

These are temporary innate Needs; they do not claim that Minecraft's native raw air_supply unit is 0..20 or that synthetic 300 was real air supply. A learned appropriate Skill+Target can eventually resolve a Goal. L1 already contains numbered `ESCALATE_L2` for unresolved Goals, and the request calls attention to urgency without forcing a choice. L2 proposed SchemaPattern remains the same typed validator. No new physical ActionPort, `RESTORE_OXYGEN` action, automatic retreat, or unlearned Skill is created.

`isInWater`, head fluid and surrounding blocks remain **SelfWorld** observations. Their value is to choose how to reach a Goal, not to replace the Body's oxygen reserve.

## Outcome-first examples

- Low hunger, oxygen UNKNOWN: EXPLORE_WORLD MOVE candidate remains. HUNGER_RELIEF may be unresolved and L1 may escalate instead.
- Known oxygen 0: EXPLORE_WORLD remains with four relative MOVE choices; RESTORE_OXYGEN is a separate urgent unresolved Goal. L1 decides, not a hard-coded exception.
- Zombie nearby: DEFEND_SELF Need (if supported) and EXPLORE_WORLD coexist; no automatic global exploration mask.
- Body attempts MOVE but is stuck / physically exhausted / blocked: WorldBody motor and Paper readbacks, original physical ActionPort and canonical WAL should classify the **actual** result. This patch neither fabricates a no-motion OUTCOME nor returns success for an unexecuted Action.
- Inference epoch advances or Body values change: the selected frozen Skill+Target revalidation checks same native session, new native probe, current capability and owner, not a biological threshold. A different session, replayed probe, missing Skill, wrong target or occupied Intent can still cause technical refusal.

## Observed failure as first-class Action Outcome

The original Stage23/24 MOVE issue path previously rejected selected Actions at two physiological checks (`health<=0` and `oxygen_level==0`) before native START, and the fsynced canonical journal required `NATIVE_MOVE_SETTLED` displacement ≥0.1m even after valid START/STOP/settling evidence. Those policies would prevent Self from experiencing *attempted but physically ineffective movement*.

Stage24e removes the two biological checks from `issue_selected_move_dev` and from the original journal's MOVE reservation/closure. With the **same** trusted source, bound capability, owned native child Action IDs, applied START/STOP acknowledgments, distinct probes, and 8+8 Paper-tick stop-settling proof, the existing original WAL now persists one of two terminal, independently restorable statuses:

- `NATIVE_MOVE_SETTLED`: ≥0.1m and ≤8m **net** displacement, still NOT Goal/Skill success or Paper causal proof.
- `NATIVE_MOVE_NO_NET_DISPLACEMENT`: ≥0m and <0.1m **net** displacement; observed attempt without meaningful net displacement, **not** a claim the character never moved during the pulse nor an inferred physical cause (stuck, tired, collision, etc.).

These are outcomes with different evidence meaning, not success/failure values secretly assigned by Schema. Neither outcome grants a future Action or removes a Need; Self can evaluate and learn the result separately. A missing/ambiguous ACK, source, STOP, or settling proof **does not** become a no-motion result and stays in `PREPARED_UNRESOLVED` for reconciliation.

The present native MOVE executor retains a required observable World tick in the current source for 8+8 STOP verification. This is an **evidence integrity precondition**, not physiological permission or a claim that unknown World time prevents the character from moving. Removing this requirement requires a different independently proven tick witness. This DEV branch does not fake such a clock.

The new regression harness simulates an ACKed motor command whose position remains identical, verifies the canonical `NATIVE_MOVE_NO_NET_DISPLACEMENT` remains terminal after WAL restore, and separately verifies the original issuer does not reject a simulated healthy-but-low-health/oxygen-zero Self. There is no real World test of no-net displacement in this branch.

## Stage24c comparison record is historic, not rerun under new CPU policy

At exact HEAD `c40aea2e2f35de1d374edff98d608c51a8e0fa00`, the earlier actual Gemma synthetic comparison had A oxygen null → no MOVE, Jev UNRESOLVED; B synthetic oxygen 300 → MOVE options, model chose MOVE forward. That frozen evidence **does not change**.

The Stage24e stacked source uses a new CPU policy. If the old diagnostic generator is invoked at a new SHA, **both** A and B have exploration MOVE candidates and carry explicit `schema=STAGE24E_SYNTHETIC_JEV_CONTROL` / `historic_stage24c_outcome_reproduced=false` receipts. Never claim it reproduces the previous experiment. A new model call requires a separately authorized opt-in and generates new original evidence; **none is performed by this offline implementation**.

## Validation

New regression tests assert:
- health 0/low, hunger low, oxygen 0 or UNKNOWN, time UNKNOWN, nearby Zombie, truncated registry do not remove EXPLORE_WORLD;
- RESTORE_OXYGEN is independent and unresolved without an actual bound Skill; unknown oxygen does not fabricate low-oxygen Need;
- L1's preselected frozen MOVE remains READY after Body values change, **without issuing a native action**, while native session/Skill/owner checks still fail closed;
- historical Stage24c read-only gate can disagree with new standing Need (by design);
- previous Stage24b model → original physical issuer seam still requires the original owner/WAL and retains model-only no-authority evidence.

Use exact-head CI; Stage24b real physical MOVE is not attested and Stage25 remains QUAL_NO_GO. A later isolated real World test must observe the proposed physical Action, actual native/Paper readbacks, STOP, WAL and native Outcome, including genuine inability/no-motion when it occurs. Do **not** force a failure or fake an Outcome to prove this principle.
