# RelaySelf L19 — World-ready original Goal window with bounded native interleaving

Date: 2026-10-31 JST. Parent L18 docs HEAD `29006332a6a8783bbb8f3a0b04f70b5648d0efca`.

## Problem and fix

The L16 S49 source collector receives exact Mineflayer bridge JSONL frames while the existing S49 executor issues one real Action and S16 clearance, then requests two post-Action Goal observations in sequence. Minecraft can emit unsolicited `observation(kind="entities",request_id=None)` frames **between** the two explicitly correlated probes. Previous L16 and L14 readers required the probes to have consecutive native `seq` values, incorrectly rejecting a legitimate single-Action source merely because of normal entity updates. This is different from requiring World tick adjacency (not supported here).

L19 updates the **read-only** S7 original verifiers (`adapters/mineflayer/l16_first_action_goal_originals.py` and `src/relay_self/l14_original_bridge_goal_window.py`) to accept up to 15 unsolicited, uncorrelated `entities` frames between the first and second exact Goal probes. Only one bounded S49 physical Action and its S15 cleanup ACK are still permitted. L16 requires the S7 prefix end immediately at the second terminal probe; L14 uses the actual **last** frame for that second probe, preserves original before/after/first Goal `seq`, checks source hashes and external preregistered Goal source, and reports actual second-probe `seq`.

**Explicitly forbidden within the Goal window**: a second effect/Action, any `entity_hurt` (could affect Goal outcome), `connection_end`, unknown native message, extra correlated/unrequested `probe`, loss of sequence continuity, source hash mismatch, excessively long span, or malformed duplicate-key JSON. The effect ACK scan still rejects other received Actions anywhere in the prefix. The source remains an observation of entity updates, not a proof that no unobserved World intervention occurred. All L13/L14/L17 flags for independent physical Goal authentication, TCP authority, nonintervention and qualified L10 learning stay **false**.

L19 does not change the original physical Action executor, Mineflayer World I/O, S49 host policy, existing Goal criterion or L18 terminal owner producer. It is narrowly preparing the already-written L16→L18 S49 physical source path for normal asynchronous World observations.

## Prospective explicit DEV run on user's own WSL2 Minecraft host

**No real Minecraft run has been issued by this GitHub-only development session**. The following is a runnable *example* for an operator-authorized disposable new World on the hardware that hosts Java 21 / Node 22 / Mineflayer 4.39.0. It has no automatic promotion, cannot consume previous qualifications or proofs, and does **not** authorize unattended physical execution without the operator choosing the Goal and the environment.

The experimenter must **predeclare** the target x/z before the run. Coordinates are not discoverable after the Action and retrospectively substituting target coordinates to force `REACHED` is not permitted. The arbitrary L16 operator plan is **not an independent external Goal criterion**, even when preregistered before World; an independently sourced external Goal owner/S16 action admission must still be collected.

```bash
cd ~/work/relay-self
git fetch origin
git switch integration/l19-native-goal-interleaving-world-readiness-20261031
export PYTHONPATH=src:tests:.
export S49_REAL_SERVER_CI=1
unset NODE_OPTIONS

# Set BOTH values prospectively for the physical World being selected.
: "${GOAL_X:?set pre-World target x}" "${GOAL_Z:?set pre-World target z}"
RUN_ROOT="$HOME/work/relay-self-dev/l19-first-action-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 -p "$RUN_ROOT"/capture
python -m adapters.mineflayer.s49_normal_session_real_ci \
  --report "$RUN_ROOT/s49-report.json" \
  --server-log "$RUN_ROOT/minecraft-server.log" \
  --l16-capture-root "$RUN_ROOT/capture" \
  --l16-goal-target-x "$GOAL_X" \
  --l16-goal-target-z "$GOAL_Z" \
  --l16-confirm L16-S49-FIRST-ACTION-ORIGINAL-DEV

# Source readback AFTER the physical process finished.
python -m adapters.mineflayer.l17_saved_original_goal_readback \
  --root "$RUN_ROOT/capture" \
  --s49-report "$RUN_ROOT/s49-report.json"
```

The original S49 physical qualification still expects three event decisions (WAIT, MOVE_AWAY, MOVE_AWAY) and **two** originally authorized motor Actions, all in one disposable Java World; the captured S7/L18 source prefix is limited to the **first** Action before the second. This is **not** a new single-Action-only World runner. The S49 code may fetch the original Mojang server JAR using its existing mechanism. Do not run against a valued persistent World.

Stop conditions: missing existing Java/Node/Python deps, missing explicit real World gate, unknown physical Goal coordinates, duplicate/missing source files, any uncertain/failed Action cleanup, or missing external independent Goal source; classify `DEV_ONLY`/`QUALIFICATION_NO_GO`, preserve originals and do not synthesize a negative or positive training pair. An observed `REACHED` only means operator-plan geometry matched two native probes.

## Tests and next step

`tests/test_l19_native_goal_interleaving.py` checks 1/2/8/15 pre-first + one between probes, crossed L16→L14→L17 source-shaped reach, strict rejection of unsafe events, excessive interleaving and broken native seq, and missing external Goal (0 learning). CI uses exact code/test HEAD with Python 3.12, Ruff, compileall and repo contracts.

Next: explicitly permitted physical S49 first-Action source (S7 + L18 + two Goal probes), then **separate independent pre-Action external Goal** original/source-owner admission and new distinct SelfWorld/SelfBody current epoch, followed by L10 shadow memory ON/OFF + cheap exact/singleton/global comparison. A source-shaped DEV result is never a causal demonstration or automatic S10/S11 Memory update.

## Exact-head DEV verification

**Successful code/test/workflow HEAD:** `96cdf645a475168c64a1aa626d5467f47cfd6d8a`; [GitHub Actions #41155368038 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41155368038). Python 3.12 focused **79 PASS / 0 FAIL / 0 SKIP**, Ruff PASS, compileall PASS, repository contracts PASS. The workflow exercises the new L19 read-only original interleaving tests plus L16, L17, and L18 original source suites, including rejection of effect/hurt/disconnect/extra-probe/missing seq, and the no-external-Goal learning boundary.

Initial source revision [#41155335952 FAIL](https://github.com/rinsakamo/relay-self/actions/runs/41155335952) stopped at a test import-order Ruff error and did not reach pytest; fixed before the successful exact code/test HEAD above. This note is documentation only, so its later HEAD is **not** asserted as a newly tested code revision.

**Limit:** synthetic source-shaped native messages only; this pass does not verify that Minecraft emitted these frames in an actual S49 World. No real S7/L18 original was collected on the user's physical WSL2 host by this session, no independent physical Goal owner, no qualified real L10 pair, and no S10/S11 writes.
