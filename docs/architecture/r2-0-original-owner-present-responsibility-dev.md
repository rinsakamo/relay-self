# R2-0 — Original Owner / 3Self / Present / Memory responsibility refactor

**Scope:** DEV/CPU read-only refactoring only. The original U31 S1→Owner
redecision→S2 Native/Paper/Physical/WAL execution remains **unchanged**.
No product L1 input switch, new authority or state store. The R2 runtime
migration remains **HOLD**, regardless of a passing R2-0 refactor CI.

## Original evidence baseline

- [I U31 Draft #1124](https://github.com/rinsakamo/relay-self/pull/1124)
  exact `d3034026a8eea3d2d4927527f5bc0d6ad0455457`: actual one bounded
  Original B World, 2 real Gemma decisions, S1/S2 two settled WAL rows.
- [R1 Draft #1129](https://github.com/rinsakamo/relay-self/pull/1129)
  exact `06349c7a216b042511a90e05ad0196f4a7164378`: opt-in read-only
  Shadow, 3055 CPU tests full CI PASS.
- [Q Draft #1130](https://github.com/rinsakamo/relay-self/pull/1130)
  exact `f3ff4842ecb3e0907ddfa0bf22fdc9356e272302`: independent R1
  runtime 12/12, Git noninterference, independent WSL U31 readback handoff.
  Subsequent authorized LocalCodex Q run
  `Q_R1_U31_WSL_ORIGINAL_READBACK_DEV_PASS` checked all 265 original files
  before/after, Q6/Q7/Q8/Q11, and 669 original source paths across all 10
  R1 commits; results posted to Issues #1088 and #1117. This attests past
  U31 source custody; the R1 Shadow itself **did not run in real World**.

## Responsibility contract — a single Original B Owner

| Responsibility | Sole source of authority | R2-0 policy |
|---|---|---|
| Identity, persistent Memory, Questions, Skill and cognition writes | Existing `CheckpointedCognitiveOwner.retained`, `cognition.json` | No new store, no new writer |
| Session epoch, Schema registration, task ownership, quarantine, lock | `ResidentCognitiveWorkOwner` for **that same** original owner | No second Owner / lock / lifecycle |
| Native/Paper observation and STOP/ACK/WAL/physical issuer | Original I U31 runtime | No change to any existing issuer or runner |
| Legacy 3Self lens claims, original Native `OBSERVED` Body | `BD1bOwnerPresent` under resident read lock | A diagnostic input, never Schema CURRENT World truth |
| `CognitiveContext.current` | Original registered Schema, signals, owner epoch and original Native/Paper refs | Read-only source/Scope/Need/Attention comparison |
| `CognitiveContext.recent` | Only already original Owner-persisted OPEN issuer-adopt Questions | MYSELF/HYPOTHETICAL, never fabricated generation or Action |
| `CognitiveContext.retrieved` | Existing persistent Memory identities/digests | REMEMBERED, applicability UNKNOWN; no C3 adoption |
| Model, L1 prompts, scheduler, Intent and physical actuation | Existing unified I Original Owner path | No R2-0 call-site or product change |

## Concrete R2-0 code change

R1's `compare_original_owner_r1_shadow` (first read) and
`r1_shadow_is_live` (cached check) previously repeated nine equality
conditions in separate source locations. A prior independent Q runtime test
caught four missing conditions in the cached path. They now **share exactly
one pure, non-I/O** function:

`relay_self.r2_present_responsibility_boundary_dev.legacy_current_mismatch_codes`.

It compares existing `BD1bOwnerPresent` with
`CurrentSchemaFrame` for original source, Schema, Self/World scope,
Native/Paper revisions, Owner frame epoch, Schema registry revision, signals,
Need references and Attention references. The original stable R1 mismatch
codes and their order are preserved. Invalid objects cannot compare equal.

The helper **does not** read another source, call the original Owner, own a
lock, write Memory, create a second Present, switch L1, or grant GPU/Physical
admission. Existing R1 call sites still hold the original resident lock,
validate the persisted owner, re-read Native/Paper, check epoch 1, accepted
Questions, Memory digest and context freshness. It is **not** a refactor of
the canonical Present writer or an abstraction of a new runtime manager.

Original `src/relay_self/resident_cognitive_work_owner_dev.py`,
`three_self_present.py`, `r0_cognitive_context_dev.py`, U31 Native/Paper,
I4a, L1 and physical/WAL paths remain byte-identical to R1. The only
existing code changed on this R2-0 branch is the opt-in R1 Shadow read-only
comparator.

## Tests and qualification limits

New CPU tests assert A/B original Owner pointer identity, no original file,
turn, retention or Skill/Intent changes, all nine independent stale mismatch
conditions, and refusal of untyped objects. Existing R1 and full I U31 tests
are unchanged. Require exact HEAD CI for pytest/Ruff/contracts/Mineflayer/
Paper witness before classifying `R2_0_PURE_PRESENT_BOUNDARY_CPU_DEV_PASS`.

This stage is **only a responsibility-boundary refactor**. Do not extend
the Stage28 epoch-1 source to reJOIN Composite, promote subjective RECENT
to Native OBSERVED, invent new accepted Memory/Need, create Owner #2,
or use this helper as an L1/Physical authorization token.

**Status before independent Q review:** `R2_0_CPU_REVIEW_PENDING /
R2_1_HOLD / R2_2_HOLD / R2_3_HOLD /
QUAL_NO_GO / SCIENCE_NOT_RUN`. Existing Q R1 PASS applies to original
R1 SHA; it is not automatically a new Q R2-0 qualification.
