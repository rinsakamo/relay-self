# #850 LocalCodex controlled real semantic evaluation — 3 independent trials

This runbook is a **handoff for local Minecraft/Gemma runtime**, not
evidence that such a run happened on this HEAD. GitHub CI cannot
instantiate the user's GPU, Mineflayer and Paper World.

## Boundaries

- Read #850/#849, this checked-out exact HEAD, `--help`, and #843 first.
  Use a separate worktree; record git SHA, CI and actual model/jar hashes.
- Reuse Minecraft 1.21.8, Mineflayer 4.39.0, Gemma 4 12B IT Q4_K_M
  and the controlled #847/#848/#849 physical World fixtures.
- Only owned processes and isolation World, server-side setup. Do not
  force L1 option 1, retarget the selected Skill or change the prompts
  to guarantee a desired result. Record what actual Gemma picked.
- Three independent Worlds, Self IDs and once-created physical WAL files.
  Check restore/require_clear before real-world startup and afterward.
  Never clear or replay an unresolved WAL after a possible native effect.
- Preserve unchanged single-reader native adapter, WAL-before-ISSUE and
  physical owner. Keep EAT/ATTACK capabilities untouched.
- The `--semantic-apply-dev` mode **does** transition the existing
  SkillExecution/IntentCommitment in this one-shot DEV session. It
  does **not** persist semantic owner events, publish memory or
  establish full autonomous goal management.
- Use distinct authority labels with explicit DEV acknowledgment:
  unverified labels are **not** authenticated physical grants.

## Commands — adjust actual existing local ports/paths/model only

The following examples assume the correct Python virtual environment
and already authorized/reachable llama.cpp and Minecraft World.
Use *fresh never-existing* WAL paths under pre-existing directories,
one per trial. Change placeholder `MODEL_ID`, paths and ports to your
actual local environment.

Common flags for all runs:

```text
--grant-real-world --grant-real-llm
--l0-skill-ir-dev
--semantic-eval-dev --semantic-apply-dev
--pre-l1-native-probe
--acknowledge-physical-dev-unverified-grants
--physical-propose-authority DEV_SEMANTIC_PROPOSE
--physical-issue-authority DEV_SEMANTIC_ISSUE
--model MODEL_ID
```

### 1. EAT, hunger Goal satisfied

Controlled source facts: Food around **6**, bread **1**, no nearby
entities; post-EAT Food expected around **11**. Configured CPU Schema
threshold **10**, so a successful EAT can end the HUNGER_RELIEF Goal.
Record actual observations, do not assert success on fixtures alone.

```bash
python -m experiments.run_cognitive_minimal_world \
  --grant-real-world --grant-real-llm --model MODEL_ID \
  --mc-port MC_PORT_EAT_10 --mc-username RelaySelfEat10 \
  --self-id semantic-eat-10 --intent-id intent-semantic-eat-10 \
  --physical-eat-dev --l0-skill-ir-dev \
  --semantic-eval-dev --semantic-apply-dev \
  --pre-l1-native-probe --edible-item bread --hunger-threshold 10 \
  --physical-journal-path /ABS/PATH/eat10/wal.json \
  --physical-create-journal \
  --acknowledge-physical-dev-unverified-grants \
  --physical-propose-authority DEV_SEMANTIC_PROPOSE \
  --physical-issue-authority DEV_SEMANTIC_ISSUE \
  --evidence-path /ABS/PATH/eat10/result.json
```

Expected only if exact native and Goal readback attest it:
one physical `NATIVE_EAT_OUTCOME`, L0
`PROPOSE_ACTION → AWAIT_ACTION → ADVANCED → TERMINAL_CANDIDATE`,
`semantic_assessment.skill_evidence=SUPPORTED`,
`goal_evidence=SATISFIED`,
`skill_final_state=succeeded`,
`intent_final_state=completed`.

### 2. EAT, local Skill succeeds while hunger Goal stays active

New World/Self/WAL; same food/bread conditions but Schema threshold **17**.

```bash
python -m experiments.run_cognitive_minimal_world \
  --grant-real-world --grant-real-llm --model MODEL_ID \
  --mc-port MC_PORT_EAT_17 --mc-username RelaySelfEat17 \
  --self-id semantic-eat-17 --intent-id intent-semantic-eat-17 \
  --physical-eat-dev --l0-skill-ir-dev \
  --semantic-eval-dev --semantic-apply-dev \
  --pre-l1-native-probe --edible-item bread --hunger-threshold 17 \
  --physical-journal-path /ABS/PATH/eat17/wal.json \
  --physical-create-journal \
  --acknowledge-physical-dev-unverified-grants \
  --physical-propose-authority DEV_SEMANTIC_PROPOSE \
  --physical-issue-authority DEV_SEMANTIC_ISSUE \
  --evidence-path /ABS/PATH/eat17/result.json
```

Expected if Food after consumption remains at/below 17:
Skill `succeeded`, Goal `ACTIVE`, Intent `committed`.
This explicitly proves Action completion != Goal achievement.

### 3. ATTACK, local hit succeeds while defensive Goal stays active

New controlled independent World/Self/WAL. Server-side single zombie
at 0.1..2.8 m, ideally nighttime + NoAI so it remains observable.
Stone sword server-provided. No other nearby entities.
Native source-attributed `entity_hurt` is mandatory and NULL
`source_entity_id` is not acceptable; do not relax the validator.

```bash
python -m experiments.run_cognitive_minimal_world \
  --grant-real-world --grant-real-llm --model MODEL_ID \
  --mc-port MC_PORT_ATTACK --mc-username RelaySelfAttack \
  --self-id semantic-attack --intent-id intent-semantic-attack \
  --physical-attack-dev --l0-skill-ir-dev \
  --semantic-eval-dev --semantic-apply-dev \
  --pre-l1-native-probe --hazard-name zombie --fight-max-distance 2.8 \
  --physical-journal-path /ABS/PATH/attack/wal.json \
  --physical-create-journal \
  --acknowledge-physical-dev-unverified-grants \
  --physical-propose-authority DEV_SEMANTIC_PROPOSE \
  --physical-issue-authority DEV_SEMANTIC_ISSUE \
  --evidence-path /ABS/PATH/attack/result.json
```

Expected if the zombie is still visible in the additional **fresh
post-Action Goal probe**: Skill `succeeded`,
`DEFEND_SELF=ACTIVE`, Intent `committed`. Disappearance/coverage
unknown means Goal `UNKNOWN`, **not** a proof of safety.
Paper Health reduction without native UUID/Entity ID/tick join
does not authorize `ATTACK_DAMAGE_PASS`.

## After each trial

- Preserve entire result JSON, final on-disk WAL, stdout/stderr, exact
  probe request ID and seq, selected L1 option, source, action parent,
  model/server SHA256, separately saved original Paper health evidence.
- Reopen the physical WAL as the same Self ID with
  `PhysicalActionJournal.restore(path, self_id=...)`, followed by
  `require_clear()`. If it fails: STOP, no auto retry.
- Verify a single physical parent, one supervised OUTCOME, the
  native capability consequence, and distinct later semantic probe;
  record Skill and Intent status separately.
- If read-only semantic probe fails after physical outcome, report
  physical success separately from `SEMANTIC_UNKNOWN`. Do not mark
  the already terminal physical Action UNKNOWN or repeat it.
- Calculate and verify per-trial SHA256SUMS, never merge evidence
  across different HEADs. Be explicit when raw Mineflayer/Paper
  event bytes or fsync syscalls were **not** independently captured.

## Conservative offline result-consistency gate

Only after obtaining the real individual JSON files, run:

```bash
python -m experiments.audit_cognitive_semantic_results \
  --eat-done /ABS/PATH/eat10/result.json \
  --eat-active /ABS/PATH/eat17/result.json \
  --attack-active /ABS/PATH/attack/result.json
```

This verifies **typed result identity and cross-trial separation only**:
the same selected Goal/Skill/Action, WAL terminal status, L0 trace,
later source-qualified probe, actual reported semantic owner updates,
and distinct Self/World/action/WAL. It cannot prove the JSON came from
an authentic World; it does not certify raw bytes, fsync, principal
authentication or independent Paper damage attribution.

Never label a trial real PASS only because the offline consistency gate
passes. The human-readable source evidence and runtime provenance
must also be reviewed independently.

## Reporting

Report exact HEAD, CI, three independent trials (including refusal/
UNKNOWN/absent Skill choice as applicable), raw evidence hashes, WAL
restore outcomes, L1 choice and latency, Skill/Goal/Intent verdicts,
and missing independent raw/Paper linkage to **PR #850 and Issue #843**.
Read both comments back. Do not create production QUAL claims.

- Valid conclusion when all three match independent live evidence:
  `REAL_SEMANTIC_EAT_DONE_PASS`,
  `REAL_SEMANTIC_EAT_ACTIVE_PASS`,
  `REAL_SEMANTIC_ATTACK_GOAL_ACTIVE_PASS`, and
  `REAL_SEMANTIC_EVALUATION_DEV_PASS`.
- If even one is absent, report actual partial evidence and use
  `REAL_SEMANTIC_EVALUATION_INCOMPLETE` rather than claim completion.
- Always `QUAL_NO_GO / SCIENCE_NOT_RUN`.
