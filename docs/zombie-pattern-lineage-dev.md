# AC-5: Time-compressed cognitive scaffolds vs acquired patterns (DEV)

**SOURCE_STAGED / PYTHON3_12_UNVERIFIED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Issues: #426 (AC-1/3/5/6), #537 (Self product loop), #633 (SelfWorld), #354 (S18). Base: Draft PR #634 HEAD 0ceb75bbc41066b63d84037271e2b69159fc86df. Parent isolated zombie-perception candidate: 52ed3666d8bda0743a81f2c6601ccffddc59dddd.

## Why this scaffold is deliberately not learning

In human cognitive development, L2 would discover which sensory cues and environmental contexts matter, then propose reusable conditional L1 habits, and possibly small low-latency L0 reflexes subject to a distinct strict gate. Currently the developer chooses cues and lanes for quick engineering validation. This **time-compresses the target behavior**, but does not reproduce or certify the development that would normally produce it.

Retain a permanent epistemic distinction:

- **DEVELOPER_SCAFFOLD**: hand-selected cue/lane/hypothetical response. A useful target or fixed baseline, not an acquired Self skill.
- **SYNTHETIC_PROPOSAL_EXAMPLE**: a strictly bounded simulated stand-in for a *possible* future L2 proposal. Its refs must be distinct synthetic-only tokens. It is **not the output of an executed L2**, and the refs do not attest actual learning/outcomes.
- **SELF_LEARNED / qualified L0**: **not expressible in this DEV source**. True adoption will require S17-grounded genuine Action/OUTCOME, existing authority-governed S10 retained update, independent holdout, and an observed *next-epoch behavior change*. L0 needs a separate reflex qualification path. Mere Habit selection or repeated matching does not meet either gate.

## Minimal engineering prototype

- experiments/zombie_pattern_lineage_dev.py creates only metadata-wrapped **existing** HabitRule with origin-specific Provenance. It reuses HabitRepertoire, HabitCue and select_habit (no new second habit engine).
- L0 scaffold example: zombie L0 contact status POSSIBLE_CONTACT -> candidate ref dev_only_dodge_l0. The underlying evidence remains proximity/closing, **not proven attack**, and no physical dodge is issued.
- L1 scaffold example: ARM_SWING_OBSERVED_SYNTHETIC -> candidate ref dev_only_dodge_l1. It is synthetic swing, **not physically attested wind-up**; Java zombie raised-arm pursuit is not attack timing proof.
- synthetic_proposal_example uses the same bounded cue/lane behavior, but with explicit **different origin**. Side-by-side comparison may tie in selected candidate: equal choice **does not mean the Self learned it**.
- select_zombie_pattern returns PatternSelectionReview where learned_from_world, authorized_for_action, admitted_to_l0 are explicitly immutable false. Even attempting dataclass.replace(..., admitted_to_l0=True) is rejected. Rule provenance cannot be relabeled from developer to synthetic and vice versa.
- No runtime Action issuance, S17/S10/Memory writes, L0 Reflex owner mutation, World startup, L2 provider call, model-generated skills, independent authority or new core semantic owner.

tests/test_zombie_pattern_lineage_dev.py includes wrong-origin, repeated/missing/fake evidence refs, forged lineage/source, cross-Self, distinct L0/L1 cue namespaces, UNKNOWN/no-match, side-by-side same-choice-not-learning, and direct authority-forgery negatives.

**Known limitation:** source refs and claim flags are a DEV-only bookkeeping convention, not cryptographic or external attestations. The read-only pattern selector consumes a typed DEV perception review; this is not an attested raw native producer. A synthetic proxy is not an actual extracted rule. No scientific learning effect or net cognitive benefit is claimed.

## Subsequent development gates

1. **Source gate:** obtain real, observable and temporally ordered zombie movement/melee cues; do not invent attack wind-up from raised arms. First validate Mineflayer 4.39.0 in isolated non-World mocks, then any live World use only under separate authorization.
2. **Fixed baseline:** use these hand-authored patterns to validate L0/L1 interface and measure known performance under held-out situations. Failures (including dodging into a cliff) remain genuine World outcomes; no omniscient L0 safety oracle.
3. **L2 acquisition gate:** permit L2 to *propose* a cue/lane/conditional response from observations and memories. Source-bound proposal cannot write directly to any live Habit, L0 or Action issuer. Its proposal time must precede held-out outcomes.
4. **Learning gate:** existing S17 learning feedback/authorized S10 update, proof of next-epoch different selection/Action, independent situations and reversals. Baseline vs L2-generated candidate vs learning OFF, costs held constant.
5. **L0 eligibility:** separately demonstrate bounded formal cue, latency, false positive/negative, conflict handling, issuer authorization and the existing S18 gate. Never directly compile an L2 proposal into L0.

**Adoption** remains another owner decision. Isolated tests: Python 3.12.3 on new zombie files and focused existing Habit/Learning/S49/S18 tests, Ruff, contracts; before/after protected82/historic770/old evidence. No CI, FULL, LLM, Minecraft, Action, OUTCOME, S10 update or science under this stage. Parent zombie-source branch and Draft PR #634 are not updated.
