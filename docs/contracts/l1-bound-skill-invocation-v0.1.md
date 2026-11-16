# RelaySelf v0.1 — Completed SkillInvocation at the L1 selection boundary

Status: **CPU-ONLY OFFLINE DEV CONTRACT; NOT A PHYSICAL ACTION GRANT**. Stack: #882 → #844, parent #843 / #829 / #828. The #860 checkpoint stack remains untouched.

## Responsibility split

1. **Innate/L2-accepted Schema** provides a Goal–Skill–Target pattern; Perception/Attention supplies a source-qualified concrete Target. An accepted, immutable `SkillParameterPreset` associated with that Pattern supplies all constraints, desired Budget, typed arguments and optional fallible expected cost.
2. **CPU Schema** (`cpu_schema_epoch` with both `skill_definitions` and an **owner-accepted** `parameter_presets` mapping) binds `SkillDefinition + Target + Preset` into one frozen `SkillInvocation` inside each `Option`. It does not infer a new Budget or generate a target. Missing definition or preset leaves the Goal unresolved and offers **no executable Option**. The ordinary legacy API is preserved when the new maps are not passed.
3. **L1 SystemOne** sees numbered completed Options, `ESCALATE_L2`, `DEFER`, and returns only a choice number. It cannot emit or modify Target, Budget, constraints, or arguments. Revalidation compares exact immutable Options against the current Schema frame, so a changed Preset, source or target invalidates the previous selection.
4. **L0** receives the previously selected `Option.invocation`. `compile_invoked_skill` and `FiniteSkillInterpreter.begin` reject postselection re-binding even if Goal, Skill ID and Target remain the same. In the new route a definition+capability does **not** authorize physical issuance: the previous parameterized `propose`/ActionPort HOLD is retained.
5. **L2** can propose improved Goal/Skill/Preset combinations in the same typed format; static validation and the **Self-owned, revision-checked acceptance/registration** must happen before the map supplied to Schema changes. The current implementation does not claim that full accept/revoke/publish owner is connected.

## Three different cost/limit concepts

| Value | Owner and meaning | Can L1 change it? |
| --- | --- | --- |
| `SkillCostEstimate` | Self's uncertain empirical prediction; can be mistaken | No |
| `SkillBudget` | Requested upper resource budget carried by the immutable Invocation | No |
| Physical capability, ActionPort grants, channel/STOP limits | WorldBody/execution-side external enforced limits | Never, even L2 cannot enlarge the grant by supplying new parameters |

A configured `SkillBudget(max_actions=64)` is not permission to issue 64 physical Actions. The existing L0 interpreter caps a compiled IR at four Actions, and native ActionPort/WAL admission remains independent. Likewise an L0 gait adjustment inside a permitted motor step does **not** change the Goal's arrival contract or Skill's Budget.

## Data contract

```text
registered SchemaPattern (Goal, Skill@version, TargetKind, pattern_id)
  + source-qualified Percept.Target
  + registered SkillDefinition@version
  + Self-accepted SkillParameterPreset(pattern_id, definition_ref, version,
        constraints, budget, arguments, expected_cost)
    ↓ cpu_schema_epoch(..., skill_definitions=..., parameter_presets=...)
SchemaFrame.Option(
  goal_id, skill_id/version, target_ref/kind, schema_id/pattern_id,
  arrival_contract, invocation=SkillInvocation(
      scope, definition_ref, goal_id, target,
      parameter_preset_ref, constraints, budget,
      arguments, expected_cost, provenance))
    ↓ assemble_l1_select / resolve_l1_choice
number-only Selection.option (= same immutable Option)
    ↓ compile_invoked_skill / L0 interpreter
nonissuing IR CHECK_TARGET → ACTION(PROPOSED/HOLD)
```

Hashes: `SkillParameterPreset.preset_ref` covers accepted preset identity, version, definition ABI, source, constraints, Budget, arguments and expectation; `SkillInvocation.invocation_ref` additionally binds Self/World, Goal, Target contract and source. The only authorized registry is the **trusted caller's** accepted map, not the model's unaccepted proposal. Existing legacy unparameterized callers remain supported until migrated; they are not evidence that full-Invocation selection has been enforced everywhere.

## Offline negative controls

- L1 receives one Option per fully bound candidate and returns a number, never a generated parameter.
- No preset / unavailable definition -> unresolved Goal and L2/DEFER choices, not a parameterless physical candidate.
- Different Preset version, Budget, constraints or expected cost -> different complete Invocation and stale L1 selection rejected.
- Changed Target/source or foreign definition/pattern -> stale or refused.
- At L0 compile and start, no replacement Budget, constraints, provenance or invocation may be substituted behind the L1 choice.
- Existing native MOVE/EAT/ATTACK issuer/WAL and original `PREPARED_UNRESOLVED` are unchanged.

## Outstanding integration gates

- Connect the owner-accepted Preset registry through the **actual** continuous CPU Schema/L1 runtime, including accepted L2 Goal+Skill+Preset registration/revision, persistence and checkpoint reconciliation. This CPU-only API requires explicit maps and currently keeps legacy callers untouched.
- Build the real one-parent parameterized ActionPort budget/constraint/admission join, empirical gait and arrival testing, and physical STOP/grant qualification. No physical parameterized issue from this contract.
- Measure complete-Option candidate growth and bound it in Schema before invoking SystemOne; no implicit L1 Budget tuning or separate Target picker.
- No real Gemma, Minecraft, Paper, QUAL, SCIENCE or multi-Self run is asserted by the offline unit tests.
