# RelaySelf S49 × SelfBody × L8 × M — previous actual World to next actual World, source-withheld DEV

**Result:** `DEV_TWO_WORLD_SOURCE_HANDOFF_PASS /
PRIOR_ACTION_WITHHELD_FROM_L8_TRAINING /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## Tested physical code and provenance

- New World exact physical source/workflow HEAD:
  `e62b52ac49ee8da4fc4fb5e29791b2db362767bd`.
- Actual [GitHub Actions run #41174086368 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41174086368),
  [original evidence artifact #13031807923](https://github.com/rinsakamo/relay-self/actions/runs/41174086368/artifacts/13031807923).
- Earlier completed real World original source: [run #41172997142](https://github.com/rinsakamo/relay-self/actions/runs/41172997142),
  [archived originals #13031364823](https://github.com/rinsakamo/relay-self/actions/runs/41172997142/artifacts/13031364823).
- Prior native session: `539cf671-1f7a-4d74-9ca8-657db84de241`.
  Its W3 Node stdout SHA256:
  `fd4725d15875c179f9e639358b341379d18298d1451090f7a189613085d385c8`.
- New native session: `eb66128b-a3d2-4bc2-889f-429f0a7c93de`.
  GitHub-hosted disposable Mojang Minecraft 1.21.8 / Java21 / Node22 /
  Mineflayer4.39.0, not the user's local WSL2 World.
- User explicitly granted continued physical **DEV** trials for this integration
  lane. This run was a single marker-gated new disposable World; no
  automatic retry of physical Actions.

## Previous World is decoded, validated, but never goal-labelled

The original previous World artifact was downloaded **read-only** through
GitHub Actions. New `adapters/mineflayer/slm_prior_world_dev.py` calls the
existing original `audit_w3_sealed_stdout` to replay every original W3
Node-stdout byte through the original native decoder, checking the sealed
raw SHA256, session continuity, seq, shutdown ACK, EOF and process exit.
It also checks the previous S49 final report, 2 distinct original S16
`outcome/executed` Action IDs, source session, native probe sequence,
dispatch `set_control applied` / S15 `clear_controls applied`,
before/after evidence, no original claimed Goal and no learning.
Malformed or mixed source rejects **before starting Java/Node**.

Past original actions:
`s49-native-move-20` (probe 21),
`s49-native-move-47` (probe 48).

The result is intentionally
`WITHHELD_NO_INDEPENDENT_EXTERNAL_GOAL`:
`original_goal_labels=0`,
`l8_admissible_episodes=0`,
`s10_commit_permitted=false`,
`source_attested_independently=false`.
This original W3+S49 report **cannot** establish independent Goal attainment
or justify training in L8/L10. The prior original action context is kept as a
DEV audit row only, never passed as a fabricated `QualifiedEpisode`,
`ExternalGoalLabel`, `GoalSourceAdmission` or S10 habit grant.

## New World: original S49 + same-session L8 owner

| Original native L0 choice | event seq | original probe seq | result |
|---|---:|---:|---|
| WAIT | 8 | 9 | no Action |
| MOVE_AWAY | 20 | 21 | S16 OUTCOME, 0.8322911817508141m |
| MOVE_AWAY | 49 | 50 | S16 OUTCOME, 0.6269065734210613m |

The existing original `NormalWorldL0`, sole `NormalSessionActionExecutor`,
S14/S15/S16, native reader and cleanup were preserved. Original
Action IDs are `s49-native-move-20` and `s49-native-move-49`.
Two original Actions and two S16 OUTCOME; no extra Action issuer.

The DEV S49 owner now initializes **one** session-local
`PersistentCognition` at bind, instead of constructing a different
empty cognition object per probe. During after-Action/after-cleanup
passive evaluation, all three rows use the same Memory owner.
This is single-owner source topology only, **not evidence of retained
learning across separate Minecraft sessions**.

`--l8-empty-memory-shadow` explicitly sets L8 retention ON;
the past original Action summary is separately present
but **not** admitted as goal-labelled training. Result:
- S42/SelfBody/L8/M `RECORDED` **3/3**, errors **0**.
- `one_l8_memory_owner=true`, `l8_retention_enabled=true`.
- `no_admissible_l1_proposal` **3/3**, L1 candidates **0**.
- `l8_training_admissions=0`, S10/Habit/learning updates **0**.
- New native reads, extra cognition calls, extra Actions, M food/energy
  credits and real model calls **0**.
- M shadow tension `WAIT_MODEL_UNKNOWN`, then twice
  `MOVE_MODEL_UNKNOWN`. This is NOT physical M0/P1/gait accounting.

## New World original evidence and cleanup

New W3: `COMPLETE_NODE_STDOUT`, **36,508 bytes / 61 frames**,
seq **0–60**, EOF, clean shutdown, one shutdown ACK, no capture fault.
SHA256:
`7f5d69f72a2cbfde7751960eaef4a06c9434b2ec94fa57e50b6ce63604bd5e8c`.
Node exit **0**, Java server exit **0**.
Original cleanup steps:
`node_cleanup`, `node_reap`, `server_cleanup`, `server_reap`,
`collector_cleanup`.
GitHub runner is disposable; independent local PID/port tests were
not performed and are not claimed.

The workflow archived both the downloaded prior originals and new
original native frames and summary in artifact #13031807923.
Focused preflight **25 PASS**, Ruff and repository contracts PASS.
Earlier first preflight run #41173818628 failed only Ruff import order;
the exact final preflight [#41173921057 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41173921057)
was checked before launching the real World.

**Evidence limits:** This is decoded Node stdout, not independently
authenticated Minecraft TCP packets. Reusing past S16 receipts with a
different new session is **not proof of an independently witnessed
external Goal**, source precommitment or physical learned benefit.
The original S49 host's internal `QUALIFIED` text does not elevate
this integration into R qualification or science.

## Next actual learning gate

To make an actual next-epoch L1 experience-based policy change,
S/R/V must first supply separately authenticated original per-Action
external Goal receipts, from a different completed World, paired with
the original pre-Action source and S16 terminal. Only then use the
existing L10/L8 admission logic and compare retention ON/OFF with
the strongest cheap exact-cue baseline. Do not promote S16
`executed` or a measured move displacement into a Goal reward.

No main/protected Draft, historical artifacts or independent owner
branches are changed. New M/L8 cross-session readback is DEV-only and
does not change the original S49 sole Action issuer.
