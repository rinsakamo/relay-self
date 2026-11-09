# D14 R9 — Attack-first natural Self, LocalCodex/WSL2 handoff

Classification: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
This is opt-in combat prioritization, NOT Paper-effective STOP, proof of
zombie damage, or proof of a complete natural food cycle.

## Read repo first

- GitHub repo `rinsakamo/relay-self`.
- Parent R8 audit-fidelity Draft PR #813, original parent HEAD
  `39c3853a22a2da424e5e7aa2b844c42f022dd65f`.
- R7 source evidence Draft PR #812 and [CI](https://github.com/rinsakamo/relay-self/actions/runs/42549644025).
- Parent R7 World `c7769356-9e0b-497f-8b86-bad9b912b6b1`:
  311 Paper ticks, Zombie-caused SELF_DIED, one original S49
  MOVE S16 OUTCOME (1.074469m), W3/S50 source readback, physical STOP
  still UNATTESTED, no attack/eat, original independent audit FAIL.
- Verify the **latest full exact R9 HEAD** with the corresponding **successful
  R9 offline CI**. Do not infer HEAD from this document.

## Behavior

The original `S49BasicPriorityL0` still produces a read-only DEFER
`preferred=MOVE_AWAY, fallback=ATTACK` on a nearby zombie.

With explicit R9 opt-in, the one existing `NaturalLifeLoop`:

1. Obtains the same two fresh Mineflayer native probes.
2. Checks both probes for the exact same one zombie, distance 0.1–2.8m,
   untruncated coverage, healthy Self, target displacement <=0.25m and
   body displacement <=0.05m.
3. If **both** probes satisfy original ATTACK admission and no prior MOVE has
   left settling unqualified, calls the **original S49**
   `require_attack_authorizations` and original `execute_attack` with
   the existing fsynced `OriginalS49NonMotionFence`, **before** considering
   any MOVE.
4. If a single zombie is close but the pair is not yet attack-admissible
   (including at 2.8–4m), R9 conservatively WAITs while the real zombie
   approaches. It does **not** issue R6 MOVE and thereby trap follow-up
   ATTACK/EAT behind the still-unproven Paper-effective STOP.
5. Without the R9 grant, original R6 native `entities` + S14 MOVE
   admission remains completely unchanged.
6. If original S49 rejects ATTACK, records a DEFER, not a granted Action.
7. No reissue after UNKNOWN; no new Action issuer or Self clone.

EAT already routes through original S49 to original S51 when Self naturally
has observed food <14, real native inventory food, zero nearby entities, and two
fresh stationary native probes. That **requires no prior MOVE**.
The original STOP fence still forbids EAT or ATTACK after MOVE until
independent physical STOP qualification. Existing S49/S51 food provenance
and verified outcomes are unchanged.

## Preflight

Use a new detached clean worktree at the successful exact R9 HEAD,
without touching previous World outputs or open original fences. In WSL2
verify Paper 1.21.8 exact hash and size, Java 21 plugin, Node 22,
Mineflayer 4.39, Python environment, no prior port 25565 owner, all R9
regressions plus R7/R6, Ruff, repository contracts and original Java tests.

Explicit operator grant for **one** natural World must include all R3/R4/R5/R6
grants and these separate opts:

```bash
export D14_R7_NATIVE_EVIDENCE_ONEWORLD_ONLY=1
export D7_PASSIVE_CONTROLS_WORLD_ONLY=1
export D14_R9_COMBAT_FIRST_ONEWORLD_ONLY=1
```

Do not bypass any of the other existing R3/R4/R5/R6 grants; consult the
parent R7 handoff for them. Keep natural World and actual zombie health/AI,
natural hunger and real rotten flesh drops, and 600-tick post-death zombie
respawn. No NoAI, lowHealth, Hunger, teleport, food staging, forced item
drops or manually triggered native Action.

Use the existing one-shot runner, with a **new unused** evidence directory
outside the repository and complete validated env:

```bash
python -B -m tools.bug0_d14_local_oneworld \
  --repo "$PWD" --expect-head "$EXPECTED_HEAD" \
  --evidence-dir "$EVIDENCE" \
  --paper-jar "$D14_R3_PAPER_JAR" \
  --plugin-jar "$D14_R3_RESPAWN_JAR" \
  --max-wall-seconds 3600
```

**One World and no automatic retry.** Do not execute World in GitHub Actions.

## Evidence

Preserve original `report.json`, Paper log, `d14_natural_events.jsonl`,
both physical pre-ISSUE fences, W3 raw stdout + seal, same-client S50
readback, standalone read-only source forensics, full `SHA256SUMS.txt`
and any failed independent audit. `#813` fixes the historical Paper
console carriage-return parsing; this does not make a prior original FAIL
into a PASS. Use the original R9 pinned HEAD for the new runner.

For each admitted ATTACK, report exact original S49 native pair seq,
target native entity ID, Action ID, S16 terminal, ATTACK native ACK,
observed entityHurt, and any independently captured Paper death/damage.
**ACK or S16 OUTCOME is not zombie damage or kill proof.**

For EAT, require original S51/S49 EAT outcome and actual food/inventory
deltas; no success if there was no hunger or no genuinely acquired food.

If R9 attacks with zero MOVE, the R7 forensic reader must not mislabel
same-session W3/S50 as foreign simply because the MOVE fence is empty.

After the trial, inspect prior historical World manifests unchanged and
verify Node/Java exit codes, cleanup, port release and separate audit
manifests. Report to R9 Draft PR, #813, #812, Bug-0 #742, Unified #717,
Learning #431. Keep qualification NO_GO and SCIENCE NOT_RUN.

## Next physically meaningful steps

Once ATTACK is observed from original S49, measure damage/hurt/death and
whether natural zombie flesh can actually be collected without staged loot.
For MOVE-before-ATTACK/EAT cases, wire existing passive D7 Paper main-thread
position/velocity/inputs to the same-world S50 clear sequence; **do not**
treat client quiet ticks as proof that the Paper-effective original STOP
happened. Continue to block post-MOVE EAT and ATTACK until that boundary
is independently established.
