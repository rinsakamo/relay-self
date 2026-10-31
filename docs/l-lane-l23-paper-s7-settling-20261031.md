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

## Prospective real Paper gate implemented in L23 DEV (not physically executed)

S49 now accepts **all six** pinned operator-provided Paper asset flags
(`--l23-paper-server-jar`, `--l23-paper-server-sha256`,
`--l23-paper-plugin-jar`, `--l23-paper-plugin-sha256`,
`--l23-paper-config`, `--l23-paper-config-sha256`).
All 6 or none; preflight must have `--l22-settling-probes 6`, the
existing L16 fixed Goal and fresh absolute capture root. Original non-opt-in
Mojang S49 execution is unchanged. No model and no additional motor issuer.

This **borrows** the S-owned unmodified Paper 1.21.8 plugin JAR from the
reviewed S branch. Unlike a passive independent observer, enabling it
changes real hunger/exhaustion (**physical intervention**). Required
operator-owned config has `dev-enabled: true`,
`s50-tick-meter-dev: true`, `target-player: RelaySelf`,
`minecraft-version: 1.21.8`. The L lane does not modify the S owner's
plugin Java code or substitute another R-approved version. Exact active
config / plugin / server SHA256s must be recorded. A local operator must
inspect this metabolic intervention before running a new DEV World.

`stage_paper_assets` copies the SHA-matched Paper server JAR, plugin JAR
and active plugin config into a **fresh temporary World only**. S49's owned
loopback server starts with the existing minimal config. Before S49's
existing Action executor is called, it submits
`relaydevphase <action-id>-<session-id> PRE_FORWARD` to Paper's **console**
and requires its original server-side `M02_DEV_S50_PHASE` line. After the
genuine S15 clear/S16 OUTCOME it requires Paper's
`POST_CLEAR` line, then requests `relaydevwait` and requires
`S50_DEV_WAIT_BEGIN`. The S49 Action and two L22/L16 source probes
remain on the same original S7 reader and preserve raw receipts. Paper
collects eight consecutive World-tick callbacks. This is a
**recorded console bracket, not the server-effective held-input
clear World tick**. Paper cannot read Mineflayer's native
`getControlState()` for the complete server tick.

The original Java stdout log is audited **after owned server shutdown**.
The L23 readback now requires both PRE_FORWARD and POST_CLEAR, same Paper
World, ordered `world_full_time`, then WAIT_BEGIN and eight callbacks.
The native source is checked against the original S7/S16 receipt and Paper
end geometry is compared only as a candidate. The final report includes
`l23_paper.readback` or `PAPER_SOURCE_REJECTED`. On rejection the run is
FAIL, with available originals kept. No successful offline tests or future
DEV use promote `physical_stability_verified`, R qualification, Goal,
L10 learning, S10/S11, or P1 WAIT recovery.

### LocalCodex operator command (real World only on the user's WSL host)

The existing real L22 command supplies `--l16-capture-root` and fixed
L20 Goal source; **use new unique roots and new Goal preregistration**.
Append to that command:

```bash
--l22-settling-probes 6 \
--l23-paper-server-jar /ABS/PAPER-1.21.8.jar \
--l23-paper-server-sha256 <sha256-of-that-file> \
--l23-paper-plugin-jar /ABS/relay-metabolism-paper-dev.jar \
--l23-paper-plugin-sha256 <sha256-of-that-file> \
--l23-paper-config /ABS/l23-only-active-config.yml \
--l23-paper-config-sha256 <sha256-of-that-file>
```

`<sha256...>` placeholders here are not literal accepted values. Exact
file hashes must be calculated from real pre-existing/build-generated
assets; never borrow old hashes or synthesize a Paper jar. Maven compiler
and a Paper 1.21.8 server are not available to this GitHub-only ChatGPT
execution environment. Do not claim a real World ran here.

The Paper plugin's `relaydevphase` requirements are an additional
prerequisite; **without** target player, dev enabled + tick meter enabled,
or a logged PRE_FORWARD, the run must terminate before issuing motor.
If PRE_FORWARD succeeds but S15/S16 fails, preserve a partial source and
do not issue a POST_CLEAR or WAIT claim.

Suggested result:
`DEV_ONLY / PAPER_NATIVE_8_CALLBACKS_CANDIDATE /
PAPER_ACTIVE_METABOLISM_INTERVENTION / CLOCK_ALIGNMENT_NOT_ATTESTED /
STABILITY_UNPROVEN / GOAL_UNDETERMINED / L10_S10_S11_P1_0`.

## 2026-10-31 — Cross-lane reuse and preflight repair

The original S-owned Java `RelayMetabolismDev` source (Draft #545) also
requires `version: M0.2`, `calibration-status: candidate_uncalibrated`,
`standard-food: cooked_beef`, and the complete 16-key exhaustion/actions
roster (14 native reasons plus BASAL and COGNITION). Earlier L23 preflight
accepted a four-flag-only synthetic config that **cannot activate the
actual Paper plugin**. The L23 preflight now rejects missing/duplicate
required profile keys and incomplete/duplicate rosters **before Java**.
This is a bounded input-shape check, not a replacement for Paper's own
runtime YAML/rule validation; SHA pins still bind the actual supplied files.
S-owned original Java/config remain untouched. Active metabolism still
changes physical World exhaustion and must never be called passive.

L23 also verifies observed raw Paper line order:
`PRE_FORWARD → POST_CLEAR → WAIT_BEGIN → 8 × WAIT_TICK`, in addition
to the original per-line and numeric tick checks. A reordered console
log must be rejected even when its tick values and geometry appear valid.
This is **console-source chronology only**, not a cross-clock attestation
of effective S15 clear at a Paper World tick. G4/P1/L must not each invent
a separate physical input-idle source: S #627 owns that producer; L23
reads it. No P1 WAIT recovery, qualified Goal/learning, S10/S11 or V.

The next genuine test is ONE fresh L-lane disposable Paper DEV World using
preexisting actual SHA-pinned Paper server/plugin/config on the user's
LocalCodex WSL host. The current GitHub code-only environment does not
access those local assets. Retain raw S7/S16/Paper logs and failures,
check normal PID/port/World cleanup, and return `GOAL_UNDETERMINED`
unless independent Goal owner and effective World-tick evidence actually
exist. This revision adds no new physical run or qualification claim.

## Local WSL integration repair (2026-10-31)

First fresh Paper run at `c845f9fc6390dfdcc32f4acb10fd94db00b4bbac`
issued one S49 MOVE and closed S15/S16, but its original contains only
seven WAIT callbacks: L22's three quiet probes ended before callback eight,
and session shutdown removed the target player. L23 correctly rejected the
partial source. Preserve that FAIL; do not complete its log retrospectively.

The opt-in runner now waits up to five host seconds for the original
marker-bound `S50_DEV_WAIT_TICK index=8` before normal session shutdown.
This is source completion scheduling, not an independent physical clock,
Action, STOP owner, or idle attestation. The final original-byte reviewer
still requires all eight ordered consecutive World callbacks. Missing row
eight times out and fails; seven quiet rows cannot pass. Regression tests
cover the truncated source timeout and delayed eighth callback.

An authorized second fresh World uses the same pinned server/plugin/config
and Goal plan after FAST validation. Full results and original source
index are recorded in `docs/l23-paper-real-results-20261031.md`.
