# D14 R10 — Vanilla stone sword as one initial Self equipment item

Status: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
One R10 LocalCodex/WSL natural Minecraft World is **NOT_RUN** by this PR.
No permission to replay prior R9 World or reuse previous Action IDs.

## Repo, sources and exact HEAD

Read the repo, PR #815 (if issued), parent Draft PR #814, #813, #812,
Bug-0 Issue #742, Unified #717, Learning #431, and current CI before
doing anything with Minecraft. Confirm a **40-character exact R10 HEAD**
with its SUCCESS offline workflow; never infer it from a parent commit
or this guide. Read the source and latest CI before starting.

R9 World `6bab7906-fb2d-4808-8ad4-56d06d18a9d6`: 257 Paper ticks
SELF_DIED, original S49 same-zombie native ATTACK 7/7 native ACK applied
and S16 OUTCOME, entity_hurt 4, 0 Paper managed Zombie deaths,
0 natural loot/EAT, 0 C1, no Action unresolved, no MOVE. This is NOT
proof of Paper damage, kill or prolonged survival.

R10 is **not** natural weapon acquisition or crafting. It explicitly
gives one real, vanilla `STONE_SWORD` to Self's main hand **once before
the first natural zombie spawns**, via the existing Paper dev respawn
plugin, in a disposable natural Survival World. It never modifies
zombie AI/Health, Self Health/Hunger, damage coefficients, natural loot
RNG, spawn horizon or 600-Paper-tick respawn. It is not an automatic
ATTACK, native operator action, Self-side control or added S49 authority.

The plugin denies equipment when the first Self's inventory is not
pristine. With R10 disabled it is identical to prior R9 natural mode.

## Guarded physical behavior

The existing original S49 `NormalSessionActionExecutor`, same Intent
and original non-motion pre-ISSUE physical fence remain the **sole**
ATTACK issuer. R9's same-session stable native zombie admission
and WAIT-for-reach behavior stay unchanged. MOVE after prior motion
remains blocked for subsequent ATTACK/EAT until Paper-effective
STOP is independently established.

For every Paper `EntityDamageByEntityEvent` to the **managed** zombie
from actual Self, or from that zombie to Self, the observer records
world/player/entity UUID, Paper tick, cause, Self's genuine main-hand
item, before-Health and Paper `finalDamage`. A separate Paper
main-thread callback attempts next-tick after-Health readback. Death
and killer are still certified through the pre-existing real
`RSELF_RESPAWN_DEATH` source, not inferred from native ACK or a
missing entity. No Paper source pretends to contain an S49 Action ID.

The independent active-S49 audit rejects missing/duplicate/wrong
operator equipment and requires it to appear before Paper's initial
managed zombie. `r10_paper_combat_readout.json` strictly parses
the Paper original damage source, including same-world/player/victim
and after-health pairs. Incomplete next-tick observations remain
incomplete; no default damage, kill, loot or learning is inferred.

## One new World, only after separate operator permission

**Do not start any new World automatically upon CI success.**
The operator must grant one fresh World for this HEAD; keep the
prior R9 and all earlier evidence frozen. Use a clean detached WSL
worktree at an exact R10 SHA, with no symlinks or untracked deps
inside the repo. Use Java21, Node22/Mineflayer4.39, pinned Paper1.21.8,
Python 3.12 virtual environment, and new rebuilt R10 respawn JAR
at the exact normal filename. Never reuse the old R9 JAR hash!

Rebuild plugin:
```bash
mvn -B -ntp -f adapters/mineflayer/zombie_respawn_dev/pom.xml package
```

Copy the compiled, exact `relay-zombie-respawn-dev-0.1.0-dev.jar` to
a path outside the clean repo. Record its SHA256 and pass that SHA in
`D14_R3_RESPAWN_SHA256`; validate the jar contents and provenance.
Also pin the existing Paper SHA/size. Run focused R10/R9/R7/R6/D14
Python tests, Ruff, repository contracts and original Java tests before
any actual World.

Use all the existing R3/R4/R5/R6/R7/R9 grant/environment names
**exactly as in the source and parent handoff**. Add the sole new
independent grant:
```bash
export D14_R10_INITIAL_STONE_SWORD_ONEWORLD_ONLY=1
```
The R10 preflight also requires
`D14_R9_COMBAT_FIRST_ONEWORLD_ONLY=1`,
`D14_R7_NATIVE_EVIDENCE_ONEWORLD_ONLY=1`,
`D14_R6_NATURAL_MOTION_ONEWORLD_ONLY=1` and
`D7_PASSIVE_CONTROLS_WORLD_ONLY=1`.
No R10 grant means no new initial equipment.

With explicit one World permission and all source hash/port/clean-tree
guards passing, use a **new unused** directory outside repo:
```bash
python -B -m tools.bug0_d14_local_oneworld \
  --repo "$PWD" --expect-head "$EXPECTED_HEAD" \
  --evidence-dir "$EVIDENCE" \
  --paper-jar "$D14_R3_PAPER_JAR" \
  --plugin-jar "$D14_R3_RESPAWN_JAR" \
  --max-wall-seconds 3600
```
Never automatically retry a timed-out or failed source. No staging,
no weakened/NoAI zombie, no artificial Hunger, no forced loot,
no attack commands, no manual zombie TP, no plugin equipment refresh.

## Audit and what constitutes success

Read fresh independent original logs, not prior copies:

- Exact one `RSELF_R10_INITIAL_STONE_SWORD` prior to first initial spawn
- Original S49 ATTACK Action IDs/PROPOSE+ISSUE, durable fence and S16
- W3 raw native ACK/hurt and native decision sword inventory slot
- Paper `RSELF_R10_ZOMBIE_DAMAGE` from a managed zombie and
  `RSELF_R10_DAMAGE_AFTER` if the next Paper tick arrives
- Actual Paper Health decrease and native/Paper target IDs where
  independently matchable; action-specific causality remains UNKNOWN
  without strict explicit evidence
- Genuine `RSELF_RESPAWN_DEATH` and killer, actual natural drop,
  pickup, native inventory, and original S49→S51 verified EAT if
  hunger<14, the food really exists and normal EAT admission succeeds
- World UUID/session, Paper tick horizon and SELF_DIED vs disconnect
- 14+ original/derivative hash rows, W3+S50 forensics, original
  independent audit and R10 separate Paper source readout
- Node/Java exit 0, port 25565 free, no leaked PID

The count of `RSELF_RESPAWN_DEATH` is not a fabricated drop count;
zero rotten flesh must remain possible. Client S50 quiet ticks are not
Paper-effective STOP; do not unlock post-MOVE EAT or ATTACK.

If independent audit fails, retain its FAIL and **all** source bytes;
any later copy-source audit is separate. Historical R9 original remains
immutable. Report exact result in Japanese to #815, #814, #813,
#812, Bug-0 #742 and Unified #717; C1 #431 only with clear
NO_LEARNING status. No merge to main.

After completing the permitted single World, **no second World without
a distinct operator approval**, including on failure.
