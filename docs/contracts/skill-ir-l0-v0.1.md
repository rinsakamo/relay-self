# Cognitive v0.1 — finite Skill IR → CPU L0 → Physical ActionPort (offline DEV)

Parent: [#843](https://github.com/rinsakamo/relay-self/issues/843);
base: [#844](https://github.com/rinsakamo/relay-self/pull/844), HEAD
`b7e043ff4897051e53635b327c8f928feef70ef7`.

**Scope:** a minimal generic, nonissuing Skill interpreter. It does **not**
replace/modify #844's REAL_EAT_PASS physical issuer, enable ATTACK/MOVE/REST
native issue, or qualify any new World run. No automatically installed L2 Skill.
Classification: **OFFLINE DEV / NO NEW WORLD / QUAL_NO_GO / SCIENCE_NOT_RUN**.

## Separation of responsibilities

```text
L2 proposal (hypothetical typed Skill data)
       ↓ explicit Self acceptance (future owner/registry)
compile_skill_ir ── trusted WorldBody capability/predicate registry
       ↓ bounded DAG, no code/native verbs invented
start_l0_skill (already committed Intent and started SkillExecution)
       ↓ CPU step_l0_skill (target fixed throughout attempt)
CHECK → observed predicate from trusted adapter → branch / YIELD_OBSERVATION
ACTION → existing PhysicalActionPort.PROPOSED (no ISSUE)
       ↓ single external Physical owner (not implemented here)
          grant → pre-ISSUE WAL → native effects/ACK → consequence → durable close
       ↓ qualified terminal from external physical owner + ActionSupervisor
         OUTCOME → next IR node
         DENIED → failure path (reserved; supervisor currently tracks issued only)
         UNKNOWN/TIMEOUT → STOP_UNKNOWN, no new Action
SUCCEED/FAIL → Skill outcome candidate, not automatic Skill/Intent mutation
```

## Concrete v0.1 API

- `SkillIRStep`: typed `CHECK`, `ACTION`, `SUCCEED`, `FAIL`.
  CHECK uses an opaque *trusted* predicate ref and explicit true/false edges;
  UNKNOWN/unavailable evidence yields without interpreting absence as false.
  ACTION names an existing versioned `PhysicalCapability`, body channel
  and outcome/refusal edges. No direct `equip_item` scripts or arbitrary Python.
- `SkillIR`: version, Goal, Target kind, immutable node list, entry,
  model/source provenance, `max_steps <= 32`, `max_actions <= 10`.
  In the first cut, graph **must be acyclic** (no loops, recursion, nesting,
  parallel actions, or hidden retry). Compilation checks all references,
  reachability, every branch, worst-case bounds, and *external* Body capability
  and predicate catalogue. Compiling does not authorize installation.
- `L0SkillCursor`: immutable, revision-fenced selected target, active
  Intent/SkillExecution and current step. Attempting a stale cursor is refused.
  This is temporary DEV in-memory progress, **not** crash-safe persistence.
- `step_l0_skill`: CPU operation. A CHECK consumes a same-World native-qualified
  `QualifiedPredicate`. ACTION calls existing
  `propose_bound_physical_action`; it does **not** commit a new Intent,
  authorize or issue a native effect, construct a new physical issuer,
  operate the journal, or select a substitute Target. No second Action may be
  proposed while a first one has pending Outcome.
- `QualifiedActionOutcome`: a read-only *interface requirement* for a
  canonical trusted physical issuer. L0 requires an existing matching
  `ActionSupervisor.OUTCOME`, a source-correlated, later native readback,
  `consequence_attested` and `durable_closed` before advancing. These
  Boolean values/provenance can be forged by arbitrary Python callers;
  **the typed object alone is NOT a grant or independent attestation**.
  Production wiring must derive them from authenticated WorldBody and journal,
  not LLM text or this module.
- UNKNOWN/TIMEOUT stops the cursor, including if the physical result was
  ambiguous. There is no retry/replay and no self-granted Skill success.

## EAT compatibility

Existing #844 EAT@1 remains a **single parent physical capability**;
the native adapter implements `equip_item` + `consume_held` as two distinct
child effects with ACKs and food/inventory consequence. L0 may propose the
parent EAT capability but does **not** split these native operations and risk
reissuing a consumed bread. If a future Skill uses separate primitive Actions,
each must have an explicit durable boundary/partial-effect rule in the one
physical owner. L0 never owns or resets WAL.

The new generic L0 layer is intentionally **not wired into #844's live
`--physical-eat-dev` path**. Its exact original REAL_EAT_PASS evidence
and DEV-only authority limitation remain unchanged. There is no generic
ISSUE API yet.

## Remaining gates before real generalized Skill

1. Self-owned L2 Skill acceptance, versioned memory/registry and a strict
   JSON-to-IR parser with no implicit installation or privilege expansion.
2. Trusted versioned WorldBody capability/predicate lookup at each
   decision and independently verified observation provenance.
3. Trusted canonical issuer outcome adapter producing genuinely attested
   `QualifiedActionOutcome` (not caller-created flags), including WAL
   post-close evidence; persistent cursor/checkpoint and duplicate prevention.
4. Native ATTACK/MOVE/REST adapters, STOP/settling, global Body arbitration,
   owner principal authentication and actual-world negative tests.
5. Distinct SkillExecution result and Intent achievement evaluation;
   `SKILL_SUCCESS_CANDIDATE` is only a proposal for external assessment.

## Offline test intent

`tests/test_skill_ir_l0.py` exercises DAG compile bounds and capability
refusal, same-Target finite CHECK→ACTION→OUTCOME→SUCCESS candidate,
unknown observation yield, wrong World/session or Target, a pending Action,
stale cursor, missing physical receipt, nondurable/native-unattested
OUTCOME and supervisor UNKNOWN/TIMEOUT STOP. All native-looking inputs
are scripted Python objects, **not new Minecraft evidence**.
