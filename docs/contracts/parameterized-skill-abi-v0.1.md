# Cognitive v0.1 — Parameterized Skill ABI (CPU-only DEV)

Parent: #828. I/O #829. Initial/L2 Skill and Physical ActionPort #843.
Source branch: [PR #882](https://github.com/rinsakamo/relay-self/pull/882).

## Problem and decision

The earlier initial Skill compiler maps `MOVE@1` to
`EXPLORE_WORLD / DESTINATION` and `EAT@1` to
`HUNGER_RELIEF / FOOD`. These are **existing initial Schema-to-physical
issuer mappings**, not an intrinsic definition of the MOVE or EAT ability.
If inherited by every generated Skill, they would prevent L2 from
assembling a call such as MOVE toward an entity-relative attack envelope,
then ATTACK, without pretending that attack is the exploratory Goal.

**Decision**: minimal innate abilities, expressive *typed* invocation ABI,
finite CPU execution, and absolutely no implicit physical privileges.

## Separate three layers

1. `SkillDefinition` (**what the capability accepts**): immutable
   `(skill_id, version, origin, parameter schema, provenance,
   optional physical capability reference)`. **No Goal or Target instance.**
   The shared mandatory ABI for an innate or a learned Skill is:
   `target: TARGET`, `constraints: CONSTRAINTS`, `budget: BUDGET`.
   Learned Skills may declare up to nine additional, named typed arguments.
   `initial_skill_definitions()` describes MOVE, EAT, ATTACK and
   unimplemented REST. A Skill's physical capability reference is **a
   name**, not an observed affordance or an Action grant.
2. `SkillInvocation` (**why/where/how strictly now**): binds the specific
   Self/World session scope, Skill definition revision, the selected
   `goal_id`, `SkillTarget(ref, kind, optional TargetContract)`,
   `SkillConstraints`, `SkillBudget`, named typed extra arguments and
   provenance. Its SHA256 `invocation_ref` changes when any of these
   dependencies change; the digest does not attest the source.
3. `PhysicalSkillIR` + existing `FiniteSkillInterpreter` (**finite
   steps owned by Self**): existing IR still contains the same simple
   `CHECK_TARGET → ACTION` sequence. The optional immutable
   `ir.invocation` is checked against the actual L1 `Selection` at
   `begin()` and its `invocation_ref` is stored on the CPU cursor.
   Owner, registered Skill version, target readback, action correlation,
   WAL and actual external motor authority remain independently required.

The original `compile_initial_skill(Option, PhysicalCapability)` path
remains **unchanged** in meaning, including Goal/Target matching with the
existing initial physical issuer. New
`compile_invoked_skill(selection, definition, target, constraints, budget,
provenance, capability, arguments=())` can compile the *same two-step IR*
for a different Goal/Target Kind, but cannot authorize/issue the Action.
The actual existing EAT/ATTACK/MOVE native issuers still reject unsupported
Goals, target classes, stale TargetContracts and unqualified STOP conditions.

## Data-only examples

```text
SkillDefinition MOVE@1
    parameters = target, constraints, budget
    bound Goal = NONE

SkillInvocation A
    Skill = MOVE@1, Goal = EXPLORE_WORLD
    target = PLACE(source-qualified destination)
    constraints = {avoid_danger: true}
    budget = (max_actions=1, max_duration_ms=3000)

SkillInvocation B
    Skill = MOVE@1, Goal = ATTACK_FROM_REACH
    target = ENTITY_RANGE(live zombie, LOS and facing conditions)
    constraints = {prefer_clear_route: true}
    budget = (max_actions=1, max_duration_ms=3000)

SkillInvocation C
    Skill = MOVE@1, Goal = COLLECT_ITEM
    target = PICKUP_ZONE(source-qualified Item)
    budget = (max_actions=1, max_duration_ms=3000)
```

All three use the **same SkillDefinition** and a separately bound
`SkillInvocation`. These are *representable* examples; B and C are not
physically mapped to a qualified motor controller yet.

Arguments are strictly tagged `TARGET`, `NUMBER`, `FLAG`, `SYMBOL`,
`REFERENCE`, or `POSITION`; the `CONSTRAINTS` and `BUDGET` types are
separate. No arbitrary JSON, Python, unbounded loops or nested expression
evaluator. Numeric values must be finite. Arguments and constraint names
are unique, and the definition's parameter schema rejects missing/foreign
arguments. The typed requested `SkillBudget` may describe a larger future
learned/composite Skill (up to 64 requested Actions, 1 hour, 100 km and
4,096 observations), but the current physical interpreter and native issuer
**still enforce their own stricter four-Action/one-parent limits**. Budget
fields are explicitly caller requested **ceilings**, never extra grants.
The future composite executor must split/reconcile parent/child budgets
without multiplying Action authority. Arbitrary
constraint names do not magically acquire a WorldBody enforcement
implementation. An unrecognized requirement is a reason to DEFER/HOLD
once the physical admission bridge is built.

## L2 generated Skill template is inert until accepted

`LearnedSkillProgram` holds up to four typed `SkillCallTemplate` references
to **registered innate definitions**, not native Action primitives.

```text
SkillDefinition APPROACH_AND_ATTACK@1 (LEARNED)
    target: TARGET             # enemy
    constraints: CONSTRAINTS
    budget: BUDGET
    approach_target: TARGET    # target envelope, not enemy XYZ

CALL MOVE@1(
    target = $approach_target,
    constraints = $constraints,
    budget = $budget,
)
# Reobserve/qualify MOVE + Target condition before continuing.
CALL ATTACK@1(
    target = $target,
    constraints = $constraints,
    budget = $budget,
)
```

`validate_calls()` is **data-only**: it checks each child exists,
the named argument map is total and type-correct, no unregistered child,
unknown param or recursive cycles. A child may itself be a **registered
learned Skill with an explicitly available program**; expansion is a finite
acyclic DAG (depth ≤8, expanded leaves ≤32), never a free recursive runtime.
This does not install a registered Skill, issue a child Action, create a
fresh target/LOS observation, allocate a physical motor lease, automatically
execute both calls, or promote a parent/child outcome to success. Both
calls must later be carried
through the normal bounded Intent/Skill/ActionPort, source refresh,
WAL and per-child causal evidence boundary. Budgets will have to be
**shared/split** by the future executor; simply forwarding a parent budget
is a typed placeholder, NOT permission to multiply its Action limit.

The learned Skill uses the same `SkillParameter` and `SkillInvocation`
representation as the innate one, but still requires Self acceptance and
registration. A draft generated by an LLM is not executable merely because
its argument types validate.

## Compatibility and boundaries

- Existing EAT and ATTACK native issuers, original MOVE legacy forward
  burst and 0.05m STOP gate, Paper P0M and Checkpoint #878 **unchanged**.
- Pre-existing `NATIVE_ISSUED_UNKNOWN` physical MOVE and
  `PREPARED_UNRESOLVED` WAL originals are untouched and are not
  requalified/replayed. No new Minecraft World, Mineflayer control or Gemma
  inference was run.
- The new ABI does not currently participate in every legacy CLI
  `compile_initial_skill` call. The parameterized `PhysicalSkillIR` can
  pass a read-only L0 CHECK_TARGET, but `FiniteSkillInterpreter.propose`
  explicitly rejects it before any physical Action proposal until the
  parameter-aware issuer/constraint/budget admission is implemented. A future opt-in caller must construct an
  explicit invocation from a *validated original* L1 `Option`, and the
  Action owner and native issuer must additionally bind and enforce the
  invocation source, target contract, all required constraints and total
  budget before any real physical Action.
- A composite program executor is **not** introduced here. Future work
  can extend the finite interpreter with bounded child calls, fresh
  observations, Goal evaluation and per-child WAL ownership while keeping
  this parameter ABI shared across innate/learned definitions.

## Test scope

`tests/test_skill_invocation_v0.py` exercises three Goals with the exact
same innate MOVE definition; changing precision/source/Goal/budget changes
the invocation hash without changing ability definition; type/schema
validation; learned candidate with MOVE→ATTACK parameter forwarding;
foreign Source/Scope/Target, missing/duplicate named arguments, invalid
numbers, wrong capabilities/versions, recursion/nesting, and execution
cursor equality checks. No synthetic result is called a physical success.

**Status**: `PARAMETERIZED_SKILL_ABI_OFFLINE_DEV_ONLY` /
`LEARNED_PROGRAM_DATA_ONLY` / `REAL_WORLD_NOT_RUN` /
`QUAL_NO_GO`.
