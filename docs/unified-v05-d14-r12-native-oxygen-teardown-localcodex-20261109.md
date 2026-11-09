# D14 R12 — 24,000-tick native oxygen sentinel & teardown correction

Status: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
R12 native oxygen/teardown changes are **offline-only; new real World
NOT_RUN**. This is the child of R12 S50 row-cap PR #818, itself based
on R11 #816 and R10 #815. Read the repo, Issue #742, Unified #717,
Learning #431, exact branch HEAD and exact HEAD CI before acting.

## Original R11 natural World remains unqualified

- Paper source World `3e1fbaf6-2859-46d6-80a5-5be688e00417`, native
  Session `9b0d9ce6-d23f-474c-9a7b-b96cb25ef23d`.
- Paper **24,000 ticks** and **119** 200-tick checkpoints:
  world_time 17→17; world_full_time 17→24,017;
  daylight_cycle=true.
- Paper `LIMIT` is not independent evidence that native Self lived a
  continuous 24,000 ticks. The original run's native readback broke
  early and launcher cleanup hung; formal report and independent audit
  were never generated. Do **not** retrospectively upgrade it.
- Initial R10 stone sword Paper source observed. Original S49 MOVE,
  ATTACK, EAT & physical S16 count 0. STOP not attested.
- 14 managed zombie deaths **all FIRE_TICK**, killer UNKNOWN.
  Paper death drops=14 rotten flesh, 8 Item Spawn events, pickup
  events=0. Item Spawn association remains proximity/tick only.
  Native inventory and Health/Food unobserved after early readback halt.
- Preserved partial originals and SHA256 checks; Node/Java/launcher
  PIDs reaped and port25565 freed after **manual interruption**.
  No R11 real-World retry or second World is authorized.

## R12 fixes in this child

1. **Native oxygen sentinel**: Node Mineflayer can emit
   `oxygen_level=-1`, whereas Python's previous snapshot decoder
   required nonnegative. The new Python decoder converts only the
   **exact native -1** into `oxygen_level=None`: unknown, **not** 0
   and not full air. Other negatives, boolean, NaN, malformed native
   frames remain rejected. The byte-exact original Node W3 stdout
   still contains `-1`, and independently replaying W3 does not
   change it. This is protocol interpretation, not a World event or
   a new Self capability.
2. **R11 fail-closed Action gate**: With unknown oxygen in either
   of the fresh probe pair, a genuine R11 Life decision is
   recorded with `r12_action_admission=DEFER_UNKNOWN_OXYGEN_NO_PHYSICAL_ISSUE`.
   L0 observation can continue across Paper's day; no original
   S49 MOVE/ATTACK/EAT is issued from unverified oxygen.
   An available World/body source must establish adequate breath
   before physical admission can be enabled. Other Action grants,
   limits and STOP restrictions remain unchanged.
3. **Bounded teardown**: When a raw-captured native shutdown fails
   (including decode faults), the same owned Node stdout reader is
   drained concurrently with a bounded terminate→kill→reap path.
   It does not add a second runtime receive consumer or Action issuer.
   Corrupt or incomplete W3 remains `INCOMPLETE_UNQUALIFIED`, and
   the original termination fault is not masked. Node shutdown
   timeout for one full R11 day is 30 s; Paper graceful teardown has
   a total watchdog and bounded terminal reap diagnostic. A failed
   receipt, unknown process exit or canceled collector never becomes
   success solely because a signal was sent.
4. Retains PR #818's opt-in bounded 48,000-line S50 readback only
   when R11 is enabled; older settings remain unchanged.
   This does **not** attest physical STOP or guarantee that an
   arbitrary future 24,000-tick capture will fit.

## Offline test and future one-World constraints

Offline workflow tests exact raw W3 -1 replay, -2 and malformed
rejection, abnormal Node shutdown, R11 no-Action gate, prior R11/
R10/R9/R7/R6/D14, Ruff, repository contracts, Node protocol, Java21
plugin build and Java assertion tests. Check that **the exact final
HEAD's CI is SUCCESS** before considering an actual World.

**Do not automatically start a new Minecraft World.** A new World
requires separate explicit operator consent, a new clean exact HEAD
worktree, Java21 JDK, rebuilt plugin JAR SHA256, pinned Paper,
completely new evidence directory and fresh one-World DEV grants.
Never reuse the old World/session/Action IDs or rewrite the original
R11 partial audit to make it PASS. Always seal manifest and report
false/unknown completion as such.

Next independent World should discriminate:

- Native live readbacks across the full day, including every
  `oxygen_level=-1` as **UNKNOWN** and all subsequent observations.
- Original S49 Action count, clear deny reasons and any genuine
  Paper/player combat, with strictly separate source attribution.
- Natural rotten flesh and Paper Item Spawn vs Self actual native
  item recognition and pickup. No fake guided pickup or distant
  item-directed MOVE without separately implemented original S49
  admission and physical STOP attestation.
- Paper `LIMIT`, native Self continuity, real Node/Java/PID/port
  closure, manifest, true independent audit and R10/R11 readouts.
- No learning authorization or C1 experience from Paper LIMIT
  alone; retain DEV_ONLY/NO_GO/NOT_RUN.

If this repair does not achieve continuous native observation,
continue **offline source diagnosis** and do not claim a qualified
24k autonomous survival. All new physical World grants remain separate.
