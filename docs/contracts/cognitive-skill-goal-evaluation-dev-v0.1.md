# Cognitive v0.1 — independent Skill / Goal / Intent outcome evaluation (DEV)

## Scope and status

Child of #849 (real controlled `REAL_COMMON_EXECUTOR_PASS`) but **the
evaluation code has not run in a real World yet**. This change adds an
optional *post-physical*, read-only native Goal recheck and a separate
evaluation module. The tested EAT/ATTACK L1, L0, Physical ActionPort,
fenced native issuer and WAL code remain unchanged. Existing CLI behavior
is the default.

- `--semantic-eval-dev`: only with existing
  `--physical-eat-dev/--physical-attack-dev --l0-skill-ir-dev`.
  Obtain one *fresh, separately request-qualified* native observation
  after the Action's already-verified after-probe; evaluate local Skill
  evidence and broader selected Goal **without mutating owners**.
- `--semantic-apply-dev`: requires the above explicit evaluation flag.
  Re-derive and compare the assessment immediately before transitioning
  existing `SkillExecution.succeed` and, only if Goal evidence says
  SATISFIED, existing `IntentCommitment.complete`. No new owner, native
  effect, learned Skill publication or background retry.
- Results include selected Skill and Goal, source/session/probe seq,
  exact physical Action ID, local physical evidence, separate Goal
  verdict, Skill and Intent final states, and nonpublication flags.
  The evaluation is an **experience candidate** only; Structured Memory
  promotion / cross-epoch learning are not implemented.

## Distinctions

- **ActionSupervisor.OUTCOME**: the physical issuer's supervised
  completion with capability-specific native evidence, *not* a semantic
  Goal achievement.
- **L0 TERMINAL_CANDIDATE**: Interpreter reached its bounded terminal
  node, *not* a Skill/Intent transition.
- **Innate local Skill result**: EAT@1 has applied equip+consume ACKs
  and a verified positive Food / negative inventory delta; ATTACK@1
  has applied attack ACK and native source-attributed entity_hurt.
  The evaluator checks exact same-session after source, matching selected
  Target, existing terminal WAL row, Action owner, and **one extra fresh
  read-only evaluation probe**. If all are consistent, the innate
  Skill-local evaluation is SUPPORTED. This still is not an independent
  Paper damage-amount claim.
- **Goal HUNGER_RELIEF**: compare *fresh* observed Food to the
  explicitly configured CPU Schema hunger threshold. A Food increase
  below/equal threshold leaves Goal ACTIVE and Intent committed;
  Food above threshold means the local HUNGRY predicate is no longer
  active, allowing optional Intent completion.
- **Goal DEFEND_SELF**: a successful hit is NOT safety. A zombie still
  visible in the fresh native registry keeps Goal ACTIVE; truncated
  coverage or absence of a zombie is UNKNOWN (local disappearance does
  not independently establish safety), so this initial DEV evaluator
  cannot automatically complete a defense Intent.
- **UNKNOWN**: absent/stale evaluation readback, stale owner, mismatched
  Goal/Target, broken WAL identity or incomplete native evidence never
  becomes SUCCEEDED/COMPLETED. Failure of an optional *read-only*
  evaluation after a terminal physical OUTCOME does **not** relabel that
  physical Action UNKNOWN; no reissue occurs. Actual physical UNKNOWN
  remains protected by the existing permanent WAL STOP.
- **No automatic Skill failure** from missing positive proof; it is
  unknown evidence, not attested failure.
- Re-running `--semantic-apply-dev` on a stale SkillExecution
  snapshot is invalid, not idempotent automatic success.

## Qualification and follow-ups

Offline tests cover EAT below/above threshold, actual outcome versus
Goal, ATTACK with observed zombie / disappearance, source-stale
evaluation, explicit opt-ins, unchanged default EAT/ATTACK paths, and
no repeat native command. Extra provenances and evaluation readback are
reported distinctly.

Future steps: stable goal predicates and richer Goal satisfaction beyond
innate DEV patterns, independent Skill/Intent terminal evidence persisted
across restarts, owner concurrency, raw native/Paper UUID↔Entity ID↔tick
joins, and eventual memory publishing after explicit separate acceptance.

**Classification until real trials:
OFFLINE_SEMANTIC_EVALUATION_DEV / REAL_EVALUATION_WORLD_NOT_RUN /
QUAL_NO_GO / SCIENCE_NOT_RUN.**
