# Unified v0.5 — Contract A / Standing HOMEOSTASIS and imperfect bodily control

> **Status: A-H ARCHITECTURE_DESIGN_COMPLETE / 2026-11-07 DESIGN FROZEN / S #537 OWNER API REVIEW + IMPLEMENTATION PENDING.**
> [v0.5 freeze handoff](../unified-v0.5-design-freeze-20261107.md) adopts the conceptual HOMEOSTASIS/incomplete-control distinction; no executor changes or offline test claims follow.
> User direction, 2026-11-06. Companion to [Contract A](intent-slots-action-authority-v0.5.md) §§15–16 and [Unified v0.5](../unified-architecture-v0.5.md). No new physical issuer, grant, independent owner, real World authorization, Memory write or learning permission.

## A-H1. One Self, ongoing regulation, multiple episodic Intents

**Logical owner is the Self**. HOMEOSTASIS is the Self's **standing regulatory commitment** to stay within viable bodily operating ranges. It is permanently *available* while adopted, not permanently *executing*. It is not a wildcard physical Current Intent and does not occupy a slot or action channel merely by existing.

The repository's [ontology](../ontology.md) already distinguishes Homeostasis (regulation), Need (pressure from a deviation), Viability Constraint (hard boundary), Goal/Commitment (what persists) and Current Intent (committed action-level objective). Preserve those distinctions:

- **Standing HOMEOSTASIS**: conceptually a durable Self-scoped Goal/Commitment; long-term retention/lifecycle storage is a future Contract B decision. Do not claim it has been implemented by today's single-current `IntentCommitment`.
- **Need signals**: hunger, bodily fatigue/performance degradation, health/danger, available capacity. Each is source-qualified, time-dependent, uncertain and may be UNKNOWN. They do not need to sum to 1. Hidden WorldBody physical coefficients remain inaccessible to Self.
- **Episodic Intents**: EAT, REST, EVADE, ATTACK or MOVE are independent action-level commitments, with own IDs, reconsideration and completion evidence. They can stay committed but physically deferred while another Action executes.
- **Viability**: a verified hard limitation is not just a low numerical preference; emergency L0, real body constraints and S49 grants remain enforceable.

No automatic duplicate EAT or REST is created simply because a signal remains high. If one episode is retained, update its activation and eligibility rather than recommitting it every epoch.

## A-H2. Minimal read model (design vocabulary, not current API)

```text
HomeostasisView {
  self_instance_id, standing_commitment_ref,
  source: {world_session, native_seq, observed_at, valid_until},
  needs: [
    {kind, pressure: bounded_score | UNKNOWN,
     confidence: bounded_score | UNKNOWN, evidence_refs}
  ],
  viability: {known_hard_constraints, unknowns},
  next_review_trigger
}

EpisodicIntentView {
  self_instance_id, intent_instance_id, kind, objective,
  commitment_revision, commitment_state,
  activation: bounded_score | UNKNOWN,
  execution: ELIGIBLE | DEFERRED | IN_FLIGHT | BLOCKED | UNKNOWN,
  blocker_reason, last_observation_ref, current_plan_ref
}
```

These are *derived views*, not new owners, body truth, permission tokens or database schemas. The initial S owner may compute them from existing SelfBody/SelfWorld/MySelf/Need/Goal/Intent material. An independent storage or scheduler owner needs a Grand Null justification.

Standing commitment lifecycle: **ESTABLISHED → RETAINED** while the Self continues, with explicit **RECONSIDER / INVALIDATE / TERMINATE** when independently justified. These are conceptual states for the standing Goal/Commitment, **not new executable `IntentCommitment` enum values**. Episodic Intents retain the existing `COMMIT / REQUEST_RECONSIDERATION / CONTINUE or RELEASE / COMPLETED or FAILED or INVALIDATED` meaning.

A quiet healthy epoch is a valid state: HOMEOSTASIS remains retained, all actions may be deferred, no compulsory L2 invocation.

## A-H3. S49's minimum conflict contract — no perfect motor control

**Hard admission boundary**: the sole S49 issuer must validate its real grants, current source/session/actor, supported command channels, active leases/clear, and reject or sequence **known direct contradictions on the same exclusive control**. Current S49's single in-flight primitive policy remains unchanged until independently approved multi-channel work exists.

**Intentionally imperfect region**: legal bounded actions can still produce unforeseen bodily interference, nonoptimal sequencing or unwanted effects. Do **not** require S49 to prove all future movements interference-free or predict every physical result. For example, an authorized future move+attack combination may unexpectedly shift aim or range. Native WorldBody effects—not a fictional arbitration success—become feedback for next-epoch activation and Plan.

The following distinction is strict:

| Case | Handling |
| --- | --- |
| Simultaneous FORWARD and BACKWARD on one exclusive movement channel | Resolve, defer or reject **before issue** |
| Model-supplied authority string, expired source or unsafe conflicting uncleared control | Reject/fence; cannot be justified by strong HOMEOSTASIS pressure |
| Authorized bounded MOVE and ATTACK interact unexpectedly in a future supported ControlFrame | Permit the unpredicted physical effect, record it accurately and reconsider later; do **not** claim perfect coordination |
| ATTACK issued but no verified hit/death; EAT called but hunger not observed to improve | Retain actual uncertain/failed effect; do **not** close the Goal automatically |
| Loss of fresh body evidence or surprising movement during post-clear settling | Maintain UNKNOWN and required original S15/S16 safety boundaries; not proof of quiescence |

Unexpected interference is **not** a grant bypass, an invitation to run unsupported physical channels, or a guarantee of convergence. Current serial operation can already produce bodily prediction error and legitimate experience.

## A-H4. Feedback cycle

1. **Observe** current native WorldBody effects and provenance (hunger, health, displacement, attack, damage, input clear, fatigue-related bodily performance); preserve missing/UNKNOWN.
2. **Evaluate** HOMEOSTASIS' relevant Needs and signals in SelfBody/Current Appraisal. Body estimates are fallible; do not edit WorldBody physics.
3. **Activate or retain** relevant EAT/REST/EVADE episodes. A high-pressure but unavailable episode stays committed and DEFERRED. HOMEOSTASIS does not grant Action authority.
4. **Admit** a feasible, authorized physical request through existing S49. Only direct hard conflicts and original safety invariants must be prevented; allow bounded unknown interference.
5. **Read actual effects** independently of Action issuance and OUTCOME state. Re-evaluate pressure and Plan; record adverse interaction and possible failure. A drop in pressure alone does not establish episode success.
6. **Learn only when separately authorized** under Contract C. A single feedback update of a signal is runtime regulation, not automatic Memory/L1/L0 crystallization.

Stability is an empirical question: feedback may oscillate, stall or worsen viability. Preserve retries, resource budget, observed failure and UNKNOWN, and do not invent a convergence claim. Bounded hysteresis and a minimum dwell time can be policy candidates, but cannot override genuine emergency L0.

## A-H5. Initial Bug-0 design scenario

```text
World epoch 1: hunger pressure rises, enemy appears
  HOMEOSTASIS retained.
  EAT commitment retained, strong signal, DEFERRED because of danger/hand use.
  DEFEND/EVADE eligible, bounded S49 command issued.

World epoch 2: attack/movement has an unexpected bodily result
  Observe native target health/range/body effect or UNKNOWN.
  HOMEOSTASIS pressure recalculated; keep genuine failure evidence.
  No forced convergence, no duplicate Intent, no second issuer.

World epoch 3: if enemy threat actually subsides
  EAT becomes physically eligible from the SAME retained commitment.
  Authorize actual EAT only through S49 and a fresh food/body source.

World epoch 4: if hunger actually improves
  EAT can complete when its goal-specific criteria hold.
  HOMEOSTASIS remains retained with lower hunger pressure.
```

REST is similarly a conditional episode. Silence, Action absence, WAIT label or eight idle ticks alone do not prove P1 recovery; use the existing qualified WorldBody/fatigue source and keep M basal costs distinct.

## A-H6. Offline acceptance and negative controls

| ID | Offline scenario | Expected result |
| --- | --- | --- |
| A-59 | One Self has standing HOMEOSTASIS and active EAT/DEFEND | One Self ownership scope, distinct episode commitments and one S49 issuer |
| A-60 | Healthy epoch, low pressure | HOMEOSTASIS retained, no forced action or L2 slot |
| A-61 | Hunger rises without food in inventory | EAT may remain strong but physically deferred; no invented item |
| A-62 | Both FORWARD and BACKWARD proposed on one exclusive channel | S49 rejects/sequences direct contradiction |
| A-63 | Authorized MOVE with unexpected physical displacement | Consequence recorded, not declared arbitration failure or guaranteed success |
| A-64 | ATTACK is issued but target death unverified | No automatic DEFEND completion or threat pressure reset |
| A-65 | EAT outcome receipt without observed hunger change | No automatic hunger recovery or EAT goal success |
| A-66 | Source expired, authority fake, or physical input not cleared | Strong signals do not override S49 hard boundary |
| A-67 | Noisy threat/need observations alternate | Bounded re-evaluation; no fictitious guaranteed convergence |
| A-68 | Standing commitment and episode survive cognitive slot suspension | No silent release; no assertion GPU/physical Action stopped |

**Delivery sequence:** (1) S #537 checks the ontology distinction and minimum command conflict list; (2) implement minimal Self-scoped read-only views using existing owner APIs and focused offline tests; (3) connect a *serial* Bug-0 EAT/DEFEND/REST feedback cycle to real S49 source/outcome; (4) study unintended interference only via a separately approved, bounded physical DEV path. Qualifying and science claims remain separate. Contract A status: **DESIGN_PROPOSED / OWNER_REVIEW_REQUIRED**.
