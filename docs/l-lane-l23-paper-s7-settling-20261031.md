# L23 — Paper eight-tick candidate × S7 read-only settling (2026-10-31)

Base source: L22 branch HEAD `451270faa1281889494f933a5eda33a71e88834f`.
L23 owner: [Issue #640](https://github.com/rinsakamo/relay-self/issues/640).
Paper implementation owner remains S [Draft #545](https://github.com/rinsakamo/relay-self/pull/545), #627.

## Why the gap matters

The **actual** L22 vanilla Minecraft run1 (2026-10-31) observed S15 clear
seq34, S16 after seq35, six native `move` events and 0.24046m displacement
after S16, followed by 6 settling probes (quiet streak 0/0/0/1/2/3).
L22 proved source-visible settling, not continuous World-tick inactivity.
Its last Goal geometry and separate observer agreed within ~0.000003m, but
the observations were not independently synchronized.

Paper plugin S50 branch has original `S50_DEV_WAIT_BEGIN` and eight
`S50_DEV_WAIT_TICK` callbacks with `World.getFullTime()`, cumulative motion/
combat/swing/tick-meter counts, server positions, sprint/sneak/swim. These
are per-tick callback samples, **not an entire tick packet/input census**.
They belong to S owner, are not present in the vanilla L22 run, and cannot
be backfilled into an archived original.

## Implemented offline L23 readback

`adapters/mineflayer/l23_paper_s7_settling.py` takes *both original bytes*:
the sealed existing S7 native received/sent plus index and S16 owner original,
and a bounded future Paper console log. It invokes unmodified L22 reviewer,
requires an operator marker `<action_id>-<session_id>` and explicit Paper
world label, exactly one BEGIN and eight consecutive World fullTime snapshots,
coherent position/from-position, monotonic activity counters, basal progression,
and three state flags. It compares Paper last pose to the **last native Goal
probe** as a geometry-only diagnostic; records both SHA-256 originals.

`PAPER_8_QUIET_SAMPLES_ONLY` means 8 callback samples were quiet;
`PAPER_SAMPLED_ACTIVITY` means the Paper source saw movement, combat,
sprint, sneak or swim. Both maintain:

- `clock_alignment=NOT_ATTESTED`.
- `paper_effective_input_clear_tick=NOT_ATTESTED`.
- `paper_full_tick_input_idle=false`.
- `world_session_independently_bound=false`.
- `physical_stability_verified=false`.
- `accepted_goal_status=UNDETERMINED`.
- L10/S10/S11/P1 WAIT 0. No Action, recovery, R or V authority.

The operator marker is an association hint, **not** a trusted action-to-tick
causal transfer. The Java S50 Paper console command only accepts marker IDs
up to 128 ASCII alphanumeric, dash and underscore; the prospective L23
`<action>-<session>` fits for the current known native Action IDs, but
must be checked at preflight. A numeric `time_of_day` match, or identical
positions, cannot establish source clock alignment.

## Negative controls

Test with authentic sealed L22 S7 originals and plainly **synthetic Paper
rows** (never treat that synthetic source as real). Reject missing/duplicate
ticks, mismatched World/marker, extra bad tokens, nonfinite positions,
unexplained position prefix drift, regressed counters, changed S7 receipt.
One simulated Paper tick with real motion remains `PAPER_SAMPLED_ACTIVITY`.

## Next real DEV boundary (standing user grant covers L Lane only)

The Github-only executor cannot launch the user's local Java/Node/Paper World.
Use LocalCodex on the WSL host to run a disposable independent Paper server
and native S49 together. First ensure S owner compatibility / owner separation;
copy or build a reviewed **unchanged** plugin at a verified SHA/JAR digest,
rather than committing to S owner code on this L branch. The existing
`s49_normal_session_real_ci.py` runs vanilla server; it is not a Paper
launch path by default. Add an opt-in DEV Paper launch stage as necessary,
without replacing S7's sole reader or altering original S49 authority.

Fresh evidence must record Java plugin digest, source S branch HEAD, World
identity, preregistered marker, S7+S16 sealed original, Paper console original,
Node/Java termination, SHA256SUMS and cleanup. Confirm Paper callbacks actually
cover the target player's S16 **post-clear** interval, not merely an
unrelated quiet later interval. A console marker alone cannot establish the
effective input-clear tick; source-owned anchor/event necessary. If no
cross-clock anchor exists, preserve the candidate and classify
`SOURCE_SHAPE_ONLY / CLOCK_ALIGNMENT_NOT_ATTESTED`. Do NOT promote L10 or P1.

Avoid modifying historical L22 originals or other owner branches. No
unattested physical stability or scientific assertions.

Classification: `DEV_ONLY / L23_OFFLINE_SOURCE_SHAPE /
REAL_PAPER_ORIGINAL_NEW_0 / STABILITY_UNPROVEN /
CLOCK_ALIGNMENT_NOT_ATTESTED / GOAL_UNDETERMINED /
L10_S10_S11_P1_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
