# RelaySelf S Lane S6 — explicitly controlled native-target S49 integration trial

Product owner #537. S6 is stacked **only** on S5 Draft #601 exact
`9086d092bb619f3c5b1fdd00df7e9f72dfdd8749`.
S4 #599, S3 #598, S2 #597, parent #592/#590, original #583/#588,
shared RSEE 1.0, main, other lanes (R/L/V/A/B/C), and #544 are frozen,
unchanged, unmerged. R4 #602 is a separate sibling; do not cherry-pick it.

## Why the experimental regime must be different

The actual S4 authorized World trial saw 181 driver frames (`move=180`,
`time=1`), zero `entities`, probe, L0/L1, Action or Outcome.
#583's **pinned** stopped World has `doMobSpawning=false` by design.
Repeated natural-spawn trials in that World are poorly discriminating.
The earlier S31A source-qualification trial intentionally used server
`execute at RelaySelf run summon minecraft:zombie ~2 ~ ~
{NoAI:1b,Silent:1b,PersistenceRequired:1b}` to present a controlled target.

S6 is a different **intervention** experiment: not natural encounter or
Minecraft survival, not evidence of S49 goal success, and not a demonstration
that Self can select a goal or learn a skill autonomously. The NoAI target is
stationary and cannot test hostile attack response. A server command written
to stdin is **NOT** proof the command actually executed; an original
Mineflayer `entities` frame is necessary to admit a target into original
S49; even that cannot independently tie the entity to the intended server
command without a native command receipt / identity link.

## S6 design

- Reuses the *same original* pinned #583 stopped World, venv, external
  Mineflayer, Java/Node and S49 owner. No new launcher/runtime or World.
  Controlled input affects **only** the disposable copy; original frozen
  World/JAR/manifest/EULA operator receipt must remain byte-identical.
- Adds a separate `self_s6_controlled_trial` CLI (default dry-run), requiring
  fresh exact user approval / #537 issue-comment reference, an explicit
  S6-only confirmation, standing independently verified EULA assent, and the
  original S1 fresh external output directory. A reference string or CLI flag
  does not establish permission: the real operator must manually read back
  the new user instruction and comment first. **No new physical permission
  is supplied by this Draft or a generic '進めて'.**
- Checks exact #583 World/JAR/manifest/initial receipt and saved NBT
  `doMobSpawning=false` before launch. No alternative asset, existing
  process or symlinked dependency accepted. Bounds remain max 180 s driver,
  500 outer frames, 12 decision events, 3 physical Action requests.
- After the original Mineflayer spawn, existing `BoundedSessionDriver`
  writes the original `session_started` and awaits **one** optional
  bounded foreground callback, **before** its single native receive loop.
  This writes fsync `controlled_target_submission_intent`, submits the
  exactly S31A-listed fixed command to the already-owned Minecraft server
  stdin, then fsyncs `controlled_target_stdin_drained_unconfirmed`
  **only if** stdin drain completes. Even drain success is not execution ACK.
  On uncertain submission, fail closed; no retry/replay, replacement or
  second server lifetime. Original Action issuer cannot be reached from this
  callback.
- S4's `native_observation_audit` separately logs original outer
  observation kinds/zombie counts/registry bounds. Original
  `NaturalS49ObservationSource` and independent S49 correlated probe,
  `NormalWorldL0`, independently scoped Action PROPOSE/ISSUE,
  original typed S16 terminal/OUTCOME, and S3 read-only observed Memory
  are otherwise unchanged. Only an actually source-qualified zombie
  can lead to S49 admission and an Action. L2/GPU/LLM never launch.
- Original derived JSONL/S3 Memory/cleanup are preserved. R4 #602's
  requirement for independently saved **raw original native/protocol bytes**
  and R1 envelope is **NOT** solved by these derived records, and is not
  inferred or backfilled from S3 hashes. A future explicit original
  producer may be needed before V-admissible science claims.

## Default, side-effect-free CI

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m adapters.mineflayer.self_s6_controlled_trial
"$BASE/venv/bin/python" -m pytest -q \
  tests/test_self_s6_controlled.py tests/test_self_s5_world_opportunity.py \
  tests/test_self_s4_observation.py tests/test_self_s3_experience.py \
  tests/test_self_s2_integration.py tests/test_self_s1_runtime.py \
  tests/test_self_continuous_host.py
"$BASE/venv/bin/python" -m pytest -q
```

The GitHub CI runner is ephemeral and has no operator RSEE World. Synthetic
fixture tests exercise grant denial, exact command identity, native source,
stdin uncertainty without retry, preservation of S49 independent Action,
and no effect from the default CLI. None is a physical trial.

## Future physical operator path — NOT AUTHORIZED BY THIS CHANGE

Only after the user grants a **new, single explicit** controlled intervention
session at the then-current exact HEAD, the operator verifies that approval
on #537, reads back standing Minecraft EULA assent, proves Java/Node/JAR/
World/manifest ownership and unchanged snapshot, and selects a new empty
evidence directory, may the original bounded controlled CLI be invoked:

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
OUT=/home/rinsa/work/NEW-S6-EXCLUSIVE-EVIDENCE-DIR
# Create $OUT as a new empty, absolute, non-symlink path once.
"$BASE/venv/bin/python" -m adapters.mineflayer.self_s6_controlled_trial \
  --run-disposable --confirm SELF-S6-CONTROLLED-TARGET-ONE-SESSION \
  --standing-eula-confirmed \
  --authorization-reference 'https://github.com/rinsakamo/relay-self/issues/537#issuecomment-NEW_GRANT_ID' \
  --output-dir "$OUT" --max-events 12 --max-actions 3 \
  --max-frames 500 --max-seconds 180
```

The `NEW_GRANT_ID` placeholder is NOT a valid argument until a fresh
positive physical permission exists and was read back. Never reuse an
earlier consent (#588, S2 or S4). No automatic POST/GPU. A failed or
zero-target trial consumes its single attempt and must not be rerun.
Check and SHA256-index original logs/events/S3 Memory/cleanup, owned
PIDs/listener, disposable deletion and original source hashes; report to
#537 and this Draft, read back, and stop. A successful S16 movement
OUTCOME is not evidence that the dummy fought back, Self escaped an
attacking enemy, achieved a task goal, learned or acquired a Habit.

## Ceiling

`S6_OFFLINE_CONTROLLED_INTERVENTION_CONTRACT_QUALIFIED /`
`CONTROLLED_TARGET_PHYSICAL_NOT_RUN / NATURAL_WORLD_UNQUALIFIED /`
`NO_PRODUCTION_GO`.

Do not promote #544 scientific G3 or Self 1.0 product acceptance.
