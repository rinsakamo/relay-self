# D14 Defense-F2 — one native zombie with known passive bystanders

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**
**New Minecraft World: NOT_RUN.** Branch is a child of #825
(`0e7c5cb32d7ef6fc30bada2c1d0a49678be3bf85`).
Parallel L2 Skill PRs #820–#824 are separate and not touched.

## Verified historical cause and limit

R12 original World `a7fec96a-7d56-493c-8b34-7620b736dbb8`,
Session `4e7c41f5-a293-4162-aa25-da9f7df42e3f`, Self died
after 243 Paper ticks. Paper recorded 9 managed-zombie hits,
while the original S49 Action count was zero.

#825's **read-only** sealed original W3 analysis:
- 18 paired decisions, R9/F1 candidates 0/0;
- **18/18** pairs had `nearby_entities` total count other than 1;
- six pairs also had UNKNOWN oxygen, ten had no recent Health-loss
  witness, two had zombie distance-out-of-range, one pair did not
  observe a zombie in both probes; these overlap.
- Native inventory and Paper attack UUID/entity-time alignment are
  **not** established. Health decrease in the presence of a zombie
  is NOT proof that the zombie caused it.
- Original W3 SHA256 is
  `a13f85fcb518cdbfa07388024fc15777ab28472671cf83f93c4e9236fc919a52`.
  W3 was complete and the original manifest 16/16 unchanged.

This means **R9/F1 mistakenly conflated one target zombie with one
entity of any species**. A sheep nearby is not a second Zombie, but
the presence of a sheep must not automatically authorize an Action.

## F2 improvement (opt-in only)

`adapters/mineflayer/s49_reactive_defense.py` adds the separate
`allow_known_bystanders=True` path. Frozen F1 still requires
exactly one total entity with its historical default.

F2 requires all of the following:

1. Exact same current native session, typed actual native probes,
   monotonic fresh seq and actual Health-loss witness within 64 seq.
2. Self alive, **known nonzero** oxygen at *both* pre/fresh probes.
   UNKNOWN/null and 0 still fail closed.
3. Complete non-truncated native entity coverage with exact matching
   candidate count. More candidates than max_entities is refused.
4. **Exactly one** visible zombie in each fresh probe with the same
   native ID. The native attack target is that exact zombie ID.
5. Any *other* entity must be a known passive Minecraft mob from the
   explicit, conservative allowlist: sheep, cow, pig, chicken, rabbit.
   Unknown species/type, another zombie, skeleton/creeper/other hostile
   or untrusted entity registry is refused.
6. Previous zombie distance 0.1–4m; current 0.1–2.8m. Target per-axis
   delta <=2m; Self per-axis delta <=0.9m.
7. No MOVE-post-settling ambiguity, unresolved S49 Action, unscoped
   grant, incorrect Intent, replayed Action ID or missing durable
   PREPARE/ISSUE authorization. Only **original S49** may issue.

F2 has a new typed witness source:
`NATIVE_HEALTH_DROP_SINGLE_ZOMBIE_KNOWN_BYSTANDERS_CAUSE_UNATTESTED`.

F2 **cannot** be reached solely by passing a candidate to an old
executor. The S49 owner must have been constructed with
`dev_reactive_bystanders_source=True`, and it checks the separate
`D14_F2_SINGLE_ZOMBIE_BYSTANDERS_ONEWORLD_ONLY=1` grant on each
admission. That requires F1 opt-in and all prior R11/R10/R9/R7/R6/S50
grants; the LocalCodex preflight rejects missing grants before
creating a World/evidence directory. Default F2 OFF, no physical
World grant is provided by this document.

## No artificial combat help

F2 does not remove sheep, change zombie AI/Health, decrease difficulty,
add free food, force attack, fabricate oxygen, preposition an enemy,
directly issue an Action, or bypass physical STOP. If there is a
second zombie, other hostile entity or unknown, physical Action is
still refused. With F2 enabled and real source, S49 may still
independently refuse. The F2 candidate itself is not an S16 Outcome
or a success in self-defense.

## Offline replay (next required source check)

Only LocalCodex with access to R12's original W3 evidence can measure
actual F2 candidate count:

```bash
export PYTHONPATH=src:tests:.
EVIDENCE=/home/rinsa/work/relay-self-evidence/d14-r12-natural-original-20261109-01
sha256sum "$EVIDENCE/w3-node-stdout.raw.jsonl"
python -B -m tools.bug0_d14_defense_f1_replay \
  --evidence-dir "$EVIDENCE" \
  --expected-session-id "4e7c41f5-a293-4162-aa25-da9f7df42e3f" \
  --expected-w3-sha256 "$ACTUAL_VERIFIED_W3_SHA" \
  --output "/home/rinsa/work/defense-f2-r12-source-only-20261109.json"
```

Fill `ACTUAL_VERIFIED_W3_SHA` with the real measured raw hash; if
the output path exists use another new filename. No original file,
manifest, report or fence may be rewritten.

The archived counterfactual now reports:

- `f2_single_zombie_with_known_bystanders_candidates`
- `f2_source_refusal_reasons`
- per-decision native F2 target ID, witness seq, raw Health loss,
  refusals, and whether the old F1 candidate existed

**R12 actual F2 count is NOT_YET_MEASURED**: do not convert the synthetic
sheep case or 18 total non-single-Entity pairs into a claim about
actual F2 opportunities. A candidate requires all other conditions.

## Next independent checks

Run exact HEAD CI: Python F2 rejection/positive/owner grant tests,
sealed W3 sheep+zombie replay, original F1/R12/R11/R10/R9 regression,
Ruff, repository contracts, Node 22 protocol and Java 21 assertions.
Document exact HEAD and CI URL.

After sealed R12 source replay, compare F2 candidate cycles to
the three original within-pair native Health drops and late oxygen
non-NULL observations. If F2 still yields 0, analyze actual refusal
causes; **do not weaken oxygen or target binding based on the desired
survival outcome**.

Only a fresh *separate explicit* operator grant can allow a new
one-World run. Any future run must have a new clean exact-HEAD worktree,
one new World, rebuilt hash-pinned JAR, new evidence path, no automatic
retry and full independent S49/Paper/W3 closure audit. The original
Self death remains true; learning/C1 not yet proven.
