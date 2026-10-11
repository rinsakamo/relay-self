# S Lane S1 — physical S49 wiring (offline implementation only)

Owner: Issue #537. This is a single S Lane child of #590 exact HEAD
`c361aeb546bb437b99362f6bf381902a15a955da`.
Parent chain: #590 → #589 → #588 → original RSEE/World/S49 stack.
Neither the parent Drafts nor main/Lanes A/B/C are modified or merged.
Golden #588's three physical authorizations are consumed and its third-run
69-file SHA256 index `57f0f55079943f8a9c714f166213917ca625ab5e143c4102a927fa4de7195fb0`
remains immutable. S1 offline CI is not a physical qualification.

## What the runtime actually does

`adapters.mineflayer.self_s1_runtime` binds the existing
`BoundedSessionDriver` to one original `MineflayerProcessSession` on a
**new disposable copy** of the already verified RSEE 1.0 World, using:
`NaturalS49ObservationSource` (S49 `NativeObservationOnly` source rules,\nbut accepts authentic health/time/move observations), `_correlated_observe`,
`NormalWorldL0`, S49's independently operator-scoped L0/PROPOSE/ISSUE
authorizations, existing S14/S15 admission, and the original
`NormalSessionActionExecutor.execute`. No other Action issuer exists.

All reads of the actual Mineflayer process are **sequentially awaited in one
foreground coroutine**, never scheduled as competing readers:
native observation → exact request-ID correlated probe → source-conditioned
decision → authorized existing native S49 Action and before/dispatch/
clear/after receipt → next native observation. The S49 probe and S16 Action
functions themselves read intervening native frames, so the outer
`max_frames` budget is for **outer driver-delivered observations**, NOT an
attestation of every underlying decoded protocol frame. Observations skipped
internally are not reconstructed. The existing S49 filter deduplicates a
zombie entity ID; the same zombie repeating is not a new qualified epoch.

There is **NO** background entity spawner or fixed three-event staging, no
artificial World labels, no L1/L2 Action, no S10 learning grant, no S11
Habit, no S60 model call, and no independent World goal success. If no fresh
qualified native zombie observation appears, there may be zero decisions or
Actions, correctly. Disconnections, invalid probe/source, incomplete Action
closure and uncertain Action outcomes fail closed; no replay/retry.

Event source: new exclusive `session_events.jsonl`, flushed/fsync'd
before potentially irreversible Action callbacks. Events preserve typed
original native S49 Action evidence, source/session IDs and frame SHA256
when a verified OUTCOME is observed, distinguish requested/not-yet-issued
from actual outcome or UNKNOWN, and retain explicit no-learning/no-Habit/
no-goal-success labels. A separate `owned_cleanup.json` records the
post-stop Java/Node exits WITHOUT inferring a STOP ACK or GPU release.
Java/Node are shut down on foreground exit; the disposable World copy is
deleted only after process teardown. Existing model/GGUF are not started.

## Default: safe dry-run (no side effects)

Run in a clean descendant worktree at the S1 exact HEAD. Use the existing
central interpreter; do **not** run `pip install`, `npm install`,
`npm ci`, `ln -s`, or make a per-worktree venv:

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m adapters.mineflayer.self_s1_runtime
"$BASE/venv/bin/python" -m pytest -q \
  tests/test_self_s1_runtime.py tests/test_self_continuous_host.py
```

Dry-run prints `S1_DRY_RUN_NO_EFFECTS` and does not inspect/create a World,
open a socket, touch an Action, start Java/Node/GPU or make HTTP requests.
Tests run entirely on offline fixtures. Repository CI uses an isolated GitHub
runner with its own temporary dependencies; it does not mutate RSEE.

## Physical opt-in command — DOCUMENTED, NOT AUTHORIZED OR RUN

**A new explicit user authorization for one physical S1 run is necessary.**
The old #588 grant must NEVER be reused. Operator must also independently
verify standing Minecraft EULA assent for the exact unchanged server JAR,
Git exact HEAD, RSEE import closure, versions, ports, World snapshot,
source identity and an unused external output path. Do not run this command
until permission is granted. Operator holds the EULA proof; the CLI
confirmation flag cannot establish legal consent by itself.

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
# After specific new consent: choose one NEW empty, physical directory
OUT=/home/rinsa/work/self-s1-evidence-authorized-once
mkdir "$OUT"
"$BASE/venv/bin/python" -m adapters.mineflayer.self_s1_runtime \
  --run-disposable --confirm SELF-S1-ONE-DISPOSABLE-SESSION \
  --standing-eula-confirmed --output-dir "$OUT" \
  --max-events 12 --max-actions 3 --max-frames 500 --max-seconds 180
```

The executable insists on the exact shared root and Python environment,
verified external locked Mineflayer 4.39.0 npm root, checked #583 World
JAR/snapshot/manifest/initial-evidence identity, one fresh output directory,
no Node shim and explicit consent. It uses the RSEE World preparation owner;
it does not copy GGUF, install dependencies, launch llama-server or construct
new synthetic zombies. The operator should separately verify Node22/Java21
and local listener ownership before consuming any new authorization. An
existing foreign process on 25565 means STOP; do not kill or reuse it.

Signal interruption or owner cancellation is failure/UNKNOWN unless a
typed terminal already exists, not a replay instruction. A `stop()`,
`pause()` or `resume()` issued to the in-process `BoundedSessionDriver`
controls the foreground loop (but cannot retract a command already issued).
The CLI presently has Ctrl-C cancellation, not a RelayUI control socket.

## Qualification ceiling and next milestones

Expected terminal after offline source/CI checks:
**OFFLINE_INTEGRATION_QUALIFIED**, provided the exact-head checks pass.
Physical Minecraft S1, source/Action latency, natural threat availability,
retained native Memory, Java/Node terminal process proof, actual stop ACK,
end-to-end learning and goal success all remain **NOT_RUN / UNVERIFIED**.
`session_events.jsonl` is observational evidence, not an S10 preference
revision or a durable S11 Habit. S2 connects qualified L1/L2 choices; S3
connects governed S17 feedback/S10 reuse; S4 expands read-only RelayUI.
