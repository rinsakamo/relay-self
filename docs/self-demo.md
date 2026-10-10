# RelaySelf — まず動かす Self デモ

Issue [#537](https://github.com/rinsakamo/relay-self/issues/537) / parent #426.
This is one **product integration entrypoint**, not the start of C17/B22/I7/E9
micro-experiment series. Implementation starts from frozen S60-B1 #523
(contains the S49 real native World script) and does not edit existing
S49/S60/Action/S10/S11 authority, Paper2, RelayTheory or protected main.

## 0. What works (and what does not)

- **No flags:** one quick JSON message with `DRY_RUN`, no server, Node, Java,
  network, World, LLM or Action.
- **`--smoke`:** three synthetic decision epochs exercising the *original
  S11 Habit read* and an *original explicit S10 retained commit*.
  Trace: preconfigured safe WAIT → synthetic threat FLEE (not issued) →
  explicit synthetic S10 feedback risk_weight 3/rev0 → 4/rev1 →
  safe WAIT with revised owner. It **never** claims real World movement,
  autonomous learned Habit, signed Minecraft goal, or L2 ability.
- **`--run-disposable`:** one explicitly consented, existing **S49** native
  Minecraft/Mineflayer experiment, with 3 unattended World-triggered decisions
  **WAIT → MOVE_AWAY → MOVE_AWAY**, 2 independently admitted physical Actions
  closed to original S16 OUTCOME; source-correlated observations and
  action movement receipts written as straightforward JSONL.
  It downloads a Mojang 1.21.8 dedicated server into a temporary workspace,
  accepts EULA for this disposable local test, spawns non-AI zombie fixtures
  through server console and shuts down/removes its test World afterward.
  For the two source-checked native Action OUTCOME receipts, the product
  entrypoint also writes one **existing PersistentCognition** Memory snapshot
  (`observed_memory.json`) containing only observed movement and explicit
  `goal_success_attested=false`. No S10 preference change or S11 Habit grant.
  It is not a general game-playing agent or operator World. S49 itself
  supplies *synthetic earlier retained rev1*; **no new learning in live World**.
  This mode can run ONLY locally on an operator machine with the toolchain.
  GitHub CI does **not** run Minecraft.
- **Optional `--think`:** after a *successfully completed* real S49 test World,
  submit the validated World observation summary ONCE to an explicitly named,
  **already running** localhost OpenAI-compatible model using the inherited
  S60-A owner and S60-B1 loopback transport. Its L2 answer appears as an
  `l2_commentary` JSONL entry with `used_as_action=false`.
  This is **post-hoc read-only reflection**, not concurrent L0/L2 inference,
  a new game command, Skill/Action authorization or learned Habit. If the
  local model is unavailable, the World trace still survives with an
  `UNCONFIRMED` commentary. This CLI does not launch llama-server, verify
  the model's GGUF/binary hash, assert backend STOP ACK or measured VRAM release.

## 1. Running locally from the integration Draft checkout

This Draft is stacked on **S60-B1** ([#523](https://github.com/rinsakamo/relay-self/pull/523)),
NOT on main. Use the **integration branch checkout**, not the protected
main or individual Lane A/B/C branch, which do not contain all features.

Prerequisites: Python version supported by RelaySelf, working Node 22+,
`npm ci` in `adapters/mineflayer/` (pinned Mineflayer 4.39.0),
Java 21, JavaScript and Python adapter dependencies (see root README).
For the disposable real-Minecraft mode only, the host needs outbound
network access to the official Mojang server-download source and
a free loopback Minecraft port 25565. Ensure **no other Minecraft server**
is listening on 127.0.0.1:25565, and no personal World is in use.

Run from the repository root:

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
python -m adapters.mineflayer.self_demo
python -m adapters.mineflayer.self_demo --smoke
```

The smoke trace is line-delimited JSON:
`start, epoch, epoch, synthetic_feedback, epoch, summary`.
It uses real owner-local S10/S11 Python classes, but all episode
data are deliberately synthetic. No LLM, GPU or Mineflayer process.

For the **explicit disposable local live test only**, once you have
reviewed the existing S49 operator side effects:

```bash
npm ci --prefix adapters/mineflayer
mkdir -p ./self-demo-receipts
PYTHONPATH="$PWD/src:$PWD/tests:$PWD" python -m adapters.mineflayer.self_demo \
  --run-disposable \
  --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD \
  --output-dir ./self-demo-receipts
```

If you already own a locally running **single-slot** OpenAI-compatible
`llama-server` with a known local model alias and loopback port, add these
options to that SAME command to request one L2 reflection **after** the
Minecraft task ends:

```bash
  --think --model-alias YOUR_LOCAL_MODEL_ALIAS --model-port 12345
```

(The above line is a set of **additional flags**, not a separate shell
command. The model is not automatically started and its alias/port are
operator-provided; its true GGUF identity is not qualified by this demo.)
The L2 prompt contains only S49 native World distances, fixed L0 decisions
and observed movement; it explicitly states that objective success and
learned Habit have not been proven. Model output is untrusted text that is
visible in JSONL but cannot become an Action or LearningFeedback. Any
HTTP failure, invalid model response or timeout yields `UNCONFIRMED`;
no retry and no backend-idle or GPU-release assertion.

- The command deliberately does *not* start unless the exact consent token,
  prepared output folder, available `java`/`node`, no Node shims and
  no existing evidence-file collisions are verified. It operates
  **only** on a disposable server/World it launches, not your existing
  multiplayer or persistent World.
- Success creates `native_report.json` (unmodified original S49 summary),
  `minecraft_server.log`, `observed_memory.json` and `self_trace.jsonl`; the latter is also
  printed to stdout after the owned experiment. If S49 returns BLOCKED,
  UNKNOWN or FAIL, no fabricated PASS trace is emitted.
- Each JSONL row contains a `source_type`: `S49_REAL_MINEFLAYER_RECEIPT`
  for checked genuine S49 run and `SYNTHETIC_SMOKE_ONLY` for offline
  control. The live trace has 3 native observations and 3 L0 choices;
  two independent source-bound Action OUTCOME/physical movement records.
  Original owner-local PersistentCognition stores precisely two observational
  memories, while no LearningPreferenceState or HabitRepertoire is changed.
  **Action OUTCOME != Goal success != LearningFeedback != Habit learning**.
- The local Minecraft server uses port 25565 only during the disposable test.
  It is short-lived, and the report appears at the end. If you join it
  with the Minecraft client during the test, you may observe the scripted
  zombie-event experiment, **not freeform autonomous gameplay**.

### Stopping

Use **Ctrl+C** in the local operator terminal if necessary and check whether
the disposable Java and Node child processes actually terminated; the
preexisting S49 finally block owns cleanup. The generated receipt folder
remains for review; next run needs a new empty folder. Do **not**
delete or reset a persistent World to retry this test.

## 2. One causal trace, no fake authority

```text
Real source event -> real probe -> existing S49 L0 decision
  -> WAIT (non-Action)  OR
  -> independent existing Action grant, Skill/Action admission
  -> Mineflayer command -> post-Action World probe
  -> existing S16 OUTCOME/UNKNOWN -> single JSONL trace
```

S49's **in-World** model calls are exactly zero. The separately enabled L2
commentary comes AFTER the S49 World run and has no Action permission. The retained-origin field explicitly
reports the existing offline S19 controlled preference as
`S19_FROZEN_SYNTHETIC_GOVERNED_REV1`. A JSONL receipt is a durable
observer trace, **not** a replacement for persistent Memory, a privileged
World truth source, a new central scheduler or a governed S10/S11 commit.

One limitation remains conspicuous: the live S49 experiment stages known
zombie events and uses an existing L0 rule. No unknown quest, new Minecraft
Skill, L2-driven physical Action, experiential Habit compilation or
adaptive low-cost allocation has been established. That is the next
**product integration** step if this first playable loop works.

## 3. Evidence and acceptance

CI runs the product CLI dry and synthetic smoke, and tests the strict
transformer using **mock S49 report dictionaries**. None of those tests
is a Minecraft physical run. The actual World claim can only be based on a
separately executed S49 native report from the operator.
Reject malformed/incomplete/foreign/duplicated Action or probe summaries;
no guessed positive/negative z, no forged S17 approval or production Habit.

Do not merge this stacked PR without review of the S60-B1 and inherited
S49-S60 history. No modifications to #46/#415 frozen scientific runs,
#417 stop/cancellation physical qualification, RelayTheory or Paper2.
