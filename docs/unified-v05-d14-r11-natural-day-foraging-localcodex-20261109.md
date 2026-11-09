# RelaySelf D14 R11 — one natural Minecraft day and passive food-source observation

**Stage:** DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
**R11 real World:** NOT_RUN. Never claim food pickup, zombie kill, Self
survival or learning from an offline CI. Distinct from R10's real 10000
Paper-tick World.

## Repository truth first

Before running anything, read repo `rinsakamo/relay-self`, parent
Draft PR #815 (R10 stone sword), #814 (R9 ATTACK-first), #813 (R8),
#812 (R7), Bug-0 #742, Unified #717 and C1 #431. Read current exact
R11 branch HEAD and its **same HEAD** offline CI. Do not reuse parent
HEAD, old R10 JAR, previous World/Session/Action ID/evidence or attempt
to change main or another lane.

## 24,000 Paper ticks — exactly one full Minecraft day

New independent **opt-in**:
`D14_R11_NATURAL_DAY_ONEWORLD_ONLY=1`

A new temporary Paper 1.21.8 normal-survival World uses 24,000
consecutive Paper ticks measured from **actual first managed zombie
spawn**, not hardcoded sunset or daytime speedup. `doDaylightCycle`
is verified true, and Paper sources record `world_time` and
`world_full_time` at start, every 200 ticks and at end. The
independent audit requires clock progression through the whole day,
119 intermediate samples and exact 24,000 elapsed ticks. The start
clock time is not forced or normalized to sunrise; it is a complete
cycle at whatever starting time generated Minecraft supplied.

Daylight burns a normal zombie when exposed. The managed zombie is
**not NoAI**, not weakened, not sun-immune, not immortal or staged
to be in range of Self. One new managed zombie is created 600 real
Paper ticks after each real managed Zombie death, as in prior R10.
Time, mob drops, terrain and world physics remain natural. Self has
one real vanilla stone sword as **operator initial equipment**, not
crafted or learned; no other free food, artificial hunger or special
weapon.

Early Self death/disconnect is a true early terminal, **not** 24k
survival. If 24k passes with Self alive, report survival for this
specific natural-World experimental setup, not "combat supremacy".

## Source and action limits

Original S49 is sole physical Action issuer, with R9 stable native
same-session Zombie pair before any ATTACK. PREPARE, PROPOSE/ISSUE,
native ACK, S16 and physical fences stay unchanged. R11 expands
bounded L0 **read-only** decision budget from 1,024 to 4,096 for the
longer World; physical Action cap remains 32 and cannot be reset.
Rest/WAIT remain passive intent, not fake recovery. No new L2/C1
learning, no fabricated goal.

R11 also adds read-only sources:

- Paper managed Zombie death with `last_damage_cause`, killer UUID and
  genuine `rotten_flesh_drop_count` from `EntityDeathEvent.getDrops()`.
- Read-only Paper `ItemSpawnEvent`: rotten item UUID and stack amount.
  Parent death association is **time/location proximity only**,
  expressly NOT causal Item provenance.
- Read-only Paper `EntityPickupItemEvent` when real Self touches
  tracked item UUID. It is an event; **native inventory increase** is
  separately required for actual pickup proof.
- Native L0 probe records untyped nearby `item` entity IDs/distances
  and repeated native rotten inventory counts/deltas, scoped to the
  actual Minecraft session. Paper omniscient death/loot information
  is NOT injected into Self's L0 policy.
- R10 Paper Health before/final damage/next-tick Health and exact
  native S49 ACK remain separate. S49 Action→Paper damage cause is
  NOT independently certified.

**Current limitation:** R11 does not add an item-directed physical
MOVE. The current R6 original S49 MOVE route is for an admitted
zombie threat, not for moving to a distant item. The old D6
natural-drop→original-S49 MOVE/PICKUP experiments (#777-#779)
show a qualified path exists, but it cannot be pasted into R11
without preserving the same S49 owner and post-MOVE physical STOP
qualification. Natural passive pickup at actual reach is allowed
by Minecraft; distant intentional pickup remains **NOT_EXERCISED**
until a separate, audited implementation.

A native rotten inventory delta without the independent Paper
item-UUID chain is source-limited; do not call it proven natural
pickup. Food=17-20 is not natural EAT admission. Keep R10 food<14
and S51 grant, as well as original STOP fail-closed.

## Preflight before a new R11 World

Do not start a new World merely because offline CI succeeds. A
LocalCodex run requires a **fresh explicit one-World operator grant**,
and exact clean source HEAD with complete successful offline checks.

- Java21 **JDK** (`javac`, not JRE-only), Python3.12, Node22 and
  Mineflayer4.39; pin actual Paper 1.21.8 SHA256/size.
- Offline Python R11/R10/R9/R7/R6/D14 regressions, Ruff,
  repository contracts and Java assertion tests.
- Rebuild the R11 Paper plugin with:
  `mvn -B -ntp -f adapters/mineflayer/zombie_respawn_dev/pom.xml package`
- Copy the generated JAR outside clean repo. Validate exact filename
  `relay-zombie-respawn-dev-0.1.0-dev.jar` and its new SHA256
  `D14_R3_RESPAWN_SHA256`. Never reuse R10's old hash.
- Use a new clean detached worktree at the **R11 exact 40-hex HEAD**.
  Dependencies, symlinks, build artifacts and evidence stay outside
  clean worktree; no untracked files or dirty `git status`.
- Select an unused evidence directory outside repo, with parent
  already existing; port 25565 must be free.

R11 needs all prior existing grants R3/R4/R5/R6/R7/R9/R10/S50,
not just its own. Verify each spelling from the actual code before
configuring. Explicit new grant:
```bash
export D14_R11_NATURAL_DAY_ONEWORLD_ONLY=1
```

Only after separate real World permission and complete preflight,
run the **existing LocalCodex one-World** entry:

```bash
python -B -m tools.bug0_d14_local_oneworld \
  --repo "$PWD" \
  --expect-head "$EXPECTED_HEAD" \
  --evidence-dir "$EVIDENCE" \
  --paper-jar "$D14_R3_PAPER_JAR" \
  --plugin-jar "$D14_R3_RESPAWN_JAR" \
  --max-wall-seconds 3600
```

One new World maximum, with no auto-retry. Preserve originals even
on failure and distinguish pre-World rejection from a World run.

## Independent sources to preserve

`paper_original.log`, `d14_natural_events.jsonl`,
`report.json`, original S49 non-motion and motion fences,
`independent_audit.json`, `r10_paper_combat_readout.json`,
`r11_natural_day_foraging_readout.json` (or honest error),
R7 W3/S50 source, R7 source forensics and `SHA256SUMS.txt`.

R11 audit independently checks:
- continuous 24k Paper tick and fullTime clock, with real day-night;
- each managed Zombie death cause (FIRE, FIRE_TICK, melee, etc. as
  actually observed); killer UNKNOWN is not Self kill;
- death drop `rotten_flesh_drop_count` vs actual matching item UUID
  `PROXIMITY_AND_TICK_ONLY`, without converting drop count to pickup;
- actual Paper pickup event and native inventory changes, separately;
- native L0 item candidate sources without converting them into free
  movement authorization, and original owner/fence S16 history;
- Self terminal, Action/Intent count, cleanup Node/Java exit 0,
  physical port and PID release, exact all-original SHA256.

Report failure if source mismatches instead of patching historical
records. Any additional World after failure requires a *new* grant.

## What to implement next, only after the new World results

If the R11 World reaches 24k alive, progress **incrementally** by
concrete gaps and separate source-qualified PRs:

1. Genuine native dropped-item identity/provenance and a source-
   conditioned SelfWorld "food candidate" (no Paper omniscience).
2. Original-S49 *item-directed* MOVE, reusing the existing D6 owner
   and pre-ISSUE persistent motion fence. No second operator MOVE.
3. Independent main-thread Paper-effective STOP after input release;
   only then enable existing real S49→S51 EAT.
4. Physical REST/fatigue awareness, threat navigation, durable food
   goal and eventually genuine resource/tool acquisition.
5. C1 experiences from *real terminal Intent outcomes*, not mere
   survival, paper events or command ACK.

If Self dies or survives passively, diagnose that rather than
declaring survival skill. Do not automatically create independent
World runs or increase Action grants due to a successful pass.

For GitHub, post exact HEAD CI and truthful result to child PR, #815,
#814, Bug-0 #742, Unified #717 and C1 #431.
Classification always remains DEV_ONLY / QUALIFICATION_NO_GO /
SCIENCE_NOT_RUN unless separately qualified.
