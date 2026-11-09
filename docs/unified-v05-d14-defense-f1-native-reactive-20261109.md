# RelaySelf D14 Defense-F1 — source-bound defensive reflex, offline only

**Status: DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
**New Minecraft World: NOT_RUN**. This is an independent child of R12 #819,
not a replacement for the parallel D14 R13–R15 skill branches #820–#822.
Do not merge main, rewrite earlier evidence, or authorize another World by
merely reading this design.

## Why

Actual R12 World `a7fec96a-7d56-493c-8b34-7620b736dbb8`,
native session `4e7c41f5-a293-4162-aa25-da9f7df42e3f`:
Self died at **243 Paper ticks**. Paper reported **nine zombie hits**
and native source showed Self Health from 20 to 0.333, then death,
but original S49 issued **zero** ATTACK/MOVE/EAT Actions. The
immutable W3 stdout had 354 continuous seq frames; six decisions
deferred due to UNKNOWN oxygen. Actual source-decision refusal
breakdown should be computed by replay, not guessed.

R9 requires the same native zombie within 2.8m across two fresh
probes and per-axis displacements <=0.25m for the target and <=0.05m
for Self. During actual close combat such stationary-pair thresholds
may not hold. This change adds a bounded alternative *only when*
the Self's own native Health has demonstrably fallen during a recent
probe. The cause of Health decrease is **NOT** independently attributed
to the nearby zombie.

## New pure evidence checks

`adapters/mineflayer/s49_reactive_defense.py`

1. The native source is a typed, actual `MineflayerObservation`,
   `kind=probe`, unique request IDs, one exact session.
2. A fresh previous/current pair with increasing seq (gap <=32);
   a current or last-cycle Health witness must be within 64 native
   seq, precede the current probe, and have Health strictly greater
   than current Health.
3. **Both** current probes must show Self alive, observed nonzero
   oxygen, complete nontruncated registry coverage and **exactly
   one same-ID zombie**.
4. Previous distance 0.1–4m; current distance 0.1–2.8m.
   Target displacement per axis <=2m, Self <=0.9m.
   These are explicit DEV bounds, not scientific evidence of safe
   combat or zombie-caused injury.
5. Candidate contains the exact immutable native witness/seq,
   target ID, actual Health loss and label
   `NATIVE_SELF_HEALTH_DROP_NEAR_SAME_ZOMBIE_CAUSE_UNATTESTED`.
   It is one bounded opportunity, **not** an Action permission.

The *original* `NormalSessionActionExecutor` now revalidates
this candidate inside `require_attack_authorizations` and then
again inside `execute_attack`. The ordinary R9 stationary-pair
route is unchanged without the explicit candidate. Existing two
stage PROPOSE/ISSUE, retained Intent/owner, Action budget,
persistent ATTACK PREPARE, native ACK, S16 OUTCOME and unresolved
post-MOVE STOP gate are not bypassed.

## Opt-in and fail-closed boundary

Default: **OFF**. New dedicated one-World opt-in name:

`D14_F1_REACTIVE_DEFENSE_ONEWORLD_ONLY=1`

It is **not** currently authorized for any new World. If explicitly
authorized in the future, it requires all existing R11/R10/R9/R7/R6/
S50 and R3/R4/R5 grants in a new, disposable exact-HEAD clean
worktree; the LocalCodex preflight refuses incomplete grants
*before* creating an evidence directory. No additional physical
issuer or automatically incremented Action allowance exists.

An UNKNOWN or zero oxygen reading in either fresh probe defers
all new physical Action attempts in R11, even if Self Health fell.
Self death, no recent damage, mismatched target, foreign/stale
probe, too many entities or large motion also defer.

## Reproduce counterfactual source-only diagnosis of R12

The original R12 evidence directory, if still available locally:

`/home/rinsa/work/relay-self-evidence/d14-r12-natural-original-20261109-01`

Run in an isolated Python environment with `PYTHONPATH=src:tests:.`.
First verify original immutable W3 receipt and SHA256:

```bash
EVIDENCE=/home/rinsa/work/relay-self-evidence/d14-r12-natural-original-20261109-01
sha256sum "$EVIDENCE/w3-node-stdout.raw.jsonl"
```

Write a derived **new file outside** that directory, not into any
preexisting manifest-backed original evidence:

```bash
PYTHONPATH=src:tests:. python -B -m tools.bug0_d14_defense_f1_replay \
  --evidence-dir "$EVIDENCE" \
  --expected-session-id "4e7c41f5-a293-4162-aa25-da9f7df42e3f" \
  --expected-w3-sha256 "<ACTUAL_64_HEX_FROM_SHA256SUM>" \
  --output "/home/rinsa/work/f1-r12-native-counterfactual-readout.json"
```

This refuses a missing/incomplete W3 receipt, a wrong session or
hash, untyped source, duplicate probe or output overwrite. It reports
the original **R9 stationary-pair candidates**, alternative F1
**native self-damage reactive candidates**, request IDs, seq and
explicit refusal reasons.

**Do not** interpret a shadow candidate as an Action that really
issued, damage caused by the zombie, independent Paper health
attribution, a verified survival Skill, a C1 experience or learning.
The old actual Action count stays 0; the old Self death stays real.

## Audit after a separately authorized future World

If a future F1 World is expressly authorized, the local runner's
independent readout `f1_native_reactive_source_only.json` (or an
error record) compares each genuinely closed original-S49 F1 Action's
source witness/probe seq against complete immutable W3. A mismatch
sets RC=2 rather than retroactively changing Paper, S49 action or
W3 source. No unknown source can authorize an Action.

Only actual receipt and Paper damage/terminal evidence may later
support separate qualification. Do not downgrade the existing STOP
constraint or give F1 a second physical ACTION owner. World never
starts without a new operator permission.

## Suggested next step

Run this exact HEAD's offline CI. Run the read-only replay against
the original R12 evidence to see if F1 would have had even one
source-qualified response opportunity **before Self's death**. If
zero, diagnose the real cause from native geometry/oxygen/coverages;
do not repeatedly force World executions or widen criteria based
only on desired outcomes.

Only after source diagnosis and explicit permission should any
new one-World real combat attempt be performed.
