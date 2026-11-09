# R15b — merge proven R11 native fixes before any retained Skill real-World trial

**Branch** `dev/d14-r15b-native-fixes-skill-trial-20261109`, child of
R15 #822, with the source-compatible fixes from #818 / #819.
**DEV_ONLY / NO_WORLD_EXECUTED_IN_THIS_BRANCH / QUALIFICATION_NO_GO /
SCIENCE_NOT_RUN.**

## Repo/source qualification

Read R11 #816 and its actual two local World reports, R12 #817,
R13 #820, R14 #821, R15 #822, Bug-0 #742, Learning #431 and
the independently tested runtime fix #819. This is a **code
integration**, not a claim about the original R11 World's outcome.

The first R11 real World reached **Paper 24,000 ticks** but native
observation stopped and launcher cleanup needed intervention.
The #819 follow-up one-World test died after **243 ticks** with 0 S49
Actions; original/native teardown was completed. Both remain genuine,
immutable separate evidence, never retroactively upgraded.

## Integration changes

- Ported byte-for-byte from #818/#819: R11 S50 opt-in 48,000 row
  cap, decoded native oxygen `-1→None` in Python (W3 original bytes
  unchanged), bounded Node shutdown stdout drain + terminate/reap, and
  bounded Paper graceful shutdown/reap. Scope R11 only.
- Transposed #819's unknown-oxygen no-physical-Action gate to
  R15's child-modified `NaturalLifeLoop.step` before R15 optional
  Skill consideration. Unknown previous/current oxygen records a
  genuine native `LIFE_DECISION`, but no fresh Skill hint/physical
  Action is issued. R11 non-R15 remains source-compatible.
- R15 conditional guard also refuses to present any Action as
  available when either native breath reading is UNKNOWN/0.
- Ported #819's regression tests; added R15 missing-breath tests,
  consolidated R15b exact-SHA CI with Python tests, Ruff, repository
  contracts, Node22 protocol, Java21/Paper build/assertions.
- Does not add Action authority, reset action count, bypass post-MOVE
  effective STOP, or import LLM-generated arbitrary code.

## Dependency for actual first Skill-controlled Action

The already recorded qualified **early-death** R12/#819 World at
`/home/rinsa/work/relay-self-evidence/d14-r12-natural-original-20261109-01/`
is a candidate for *prior World A source*, subject to the fresh
`tools.bug0_d14_r12_l2_shadow` independent source audit. It is NOT
a 24k survival result, and no prior L2 candidate has been verified.
Do not create a new World until the prior source is independently
admitted, an optional **one-shot** actual Gemma/llama.cpp run on the
prior experience returns a validated non-null Skill, the raw response
and owner Catalog replay passes, and exact R15b CI passes. L2 is
allowed to abstain; no forced Skill or synthetic substitute.

A later R15b World B, if separately granted, uses the original R11
Paper/Node/plugin, original S49 issuer and R15 experimental Skill
hint cursor. It is **one World with zero automatic retries**. Do not
stage or weaken zombies, change food drops or player damage, fast
forward ticks, or bypass S49's original Action grants/fences.
Interpret actual S16 outcome, Paper damage/pickup, native inventory
and effective physical STOP separately.

If the prior R11 source does not pass, if L2 abstains, or if Python
focused/Node/Java/contracts/CI fails, **stop before World** and report
the blocker. Keep all original evidence unchanged, no fake completion.

For full commands read the R11
`docs/unified-v05-d14-r11-natural-day-foraging-localcodex-20261109.md`
and R15
`docs/unified-v05-d14-r15-retained-skill-original-s49-20261109.md`.

After an actual run, report exact HEAD/CI, repo SHA, model identity,
World/session UUID, native observation quality, original S49 actions,
Skill hint IDs vs original S49 Action IDs, S16 outcomes, R15
independent audit, Node/Java exit, port/PID cleanup, original SHA
manifest and honest classification. Later owner Memory/Habit and
L1 reuse still need a separate follow-up implementation.
