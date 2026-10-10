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

### Optional live L2 during Minecraft (L0 remains independent)

Use the **same existing operator-owned disposable World** and an already running
localhost one-slot OpenAI-compatible LLM, but pass `--live-think` instead of
`--think`:

```bash
mkdir -p ./self-demo-live-receipts
PYTHONPATH="$PWD/src:$PWD/tests:$PWD" python -m adapters.mineflayer.self_demo \\
  --run-disposable --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD \\
  --output-dir ./self-demo-live-receipts \\
  --live-think --model-alias YOUR_LOCAL_MODEL_ALIAS --model-port 12345
```

This starts ONE S60-B1 localhost L2 request on the first admissible genuine
source native zombie probe while the S49 native L0 loop continues.
S60-A owns the deadline, completion and World revision stale fences;
new World observations invalidate old L2 thoughts. `live_l2.jsonl`
captures exactly one bounded model-attempt receipt, source seq, whether
its commentary is still current, and model transport status. The main
`self_trace.jsonl` includes this sidecar if S49 closes successfully.

**The model does NOT choose/issue MOVE_BACKWARD or alter the S49 L0 policy.**
This is concurrent read-only observation, not L2-guided gameplay, not
an L1/Habit update, not an independently verified GGUF identity or
guaranteed observed inference/physical Action overlap. A timeout or
HTTP error never grants Minecraft Action authority; an L0 move never
depends on L2 completion. Without a real local model or authorized
test World the integration can only be tested with synthetic local HTTP.

The two options `--live-think` and `--think` are mutually exclusive:
the product cannot start two model attempts. The S49 internal
`real_model_calls=0` means *S49 itself* never calls a model;
the **separate product L2 attempt** is reported in the sidecar.
Old physical source reports remain untouched.

### Reflect on an existing Minecraft run without repeating it

If you already have the four receipts from a previous approved S49 run,
**do not replay the disposable World just to test the LLM**. Reuse only the
saved `native_report.json`; the source is marked operator-provided, NOT
cryptographically or physically re-attested by this read-only command.

With an already-running one-slot local `llama-server` at a known alias/port:

```bash
mkdir -p ./self-demo-reflection
PYTHONPATH="$PWD/src:$PWD/tests:$PWD" python -m adapters.mineflayer.self_demo \\
  --reflect-report /path/to/earlier/self-demo-receipts/native_report.json \\
  --think --model-alias YOUR_LOCAL_MODEL_ALIAS --model-port 12345 \\
  --output-dir ./self-demo-reflection
```

This reads a completed original S49 report, requires its explicit 3
source decisions and 2 closed Action outcomes, submits **one** observation
summary to the preexisting localhost S60-B1 provider, and writes only
`self-demo-reflection/l2_reflection.jsonl`. It never starts Java/Node or
Minecraft, performs no native Action, and does not overwrite or update the
original native report, source Memory or World. It remains read-only L2
reflection, **not L2 choosing the next game Action**. A missing/invalid model
gives `UNCONFIRMED` but preserves the reflection and no Action rights.

Use a fresh output folder each time. Do not treat an operator-provided JSON
report as independent cryptographic proof of a physical server.

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


## Action前後のネイティブ観測原本（今後の実行のみ）

2026-10-10の実機実行HEAD `be852fb64e1174507a72ae9a6d9de9e3321778cc` は
3回の判断と2回のAction OUTCOME・Memoryまで確認済みですが、
**Action前後のフレームを永続化していません**。その原本やSHA256は
変更せず、後から座標を推定・補完しません。

本改修以降の新しいS49実行では、既存の`WorldConsequence`から
次のデコード済みネイティブ型付き証拠を`native_report.json`の
`actual_native_actions[*].execution_evidence`に追加記録します。

- `before_observation` / `after_observation`: 元のsession、seq、kind、
  request ID、Health/Food/Inventory/Time、周辺entity coverage、各entityの
  座標を含む**デコード済みsnapshot全文**、およびMineflayer由来provenance
- `dispatch_receipt` / `cleanup_receipt`: 元のsession、seq、action ID、
  effect、result、error、provenance
- Action/binding/session ID、明示的な後退Action、movement、S16 terminal status。
  座標x,zから`hypot(Δx, Δz)`を**独立再計算**しS16値と照合。

これらは**デコード済みPythonオブジェクトの原本値**で、Node側から受信した
*生のJSON通信バイト*の保存ではありません。また、座標・World観測が真に
信頼できる物理的因果やgoal successを暗号学的に証明するわけではありません。

`self_trace.jsonl`にもデコード済み証拠全文とSHA256を保持し、
`observed_memory.json`にはAction観測Memoryとその証拠SHA256参照だけを
保存します。欠損・順序違反・session/action不一致・座標から再計算できない
移動量はfail-closedです。古い`native_report.json`には
`execution_evidence`が無いので`action_frames_complete=false`と明示し、
過去の実機実験を完全証拠と再分類しません。

**CIは実機を起動しません。** 新しい実機証拠はオペレーター承認付きの
別の使い捨てWorld実行で取得する必要があり、先行実機結果を上書き・
再実行することはありません。


## Selfが所有するローカル llama.cpp 起動（明示的実機実行のみ）

これまでの `--live-think` は**既に起動済みの**モデルを利用しました。
新しい `adapters.mineflayer.self_owned_llama` は、実行の都度、
**このコマンドが新しく起動した llama-server だけ**を所有して、
同じ `self_demo --run-disposable --live-think` に渡し、終了を管理します。
既存LM Studio、他のllama-server、他のNode/Javaは終了しません。

WSL2の既存RelaySelf checkoutから、実行前にバイナリ/モデルの正しい
絶対パスを指定し、**前もってGGUFのSHA256**を照合します。
予期しないサーバーの再利用を避けるため、新規の空きloopbackポート
（Minecraft 25565とは別）を使い、新しい空の証拠フォルダを準備します。

```bash
# 先に Java21 / Node22 / npm ci / 新規worktree / port空きを確認
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
GGUF="/absolute/path/to/your/model.gguf"
BIN="/absolute/path/to/your/llama.cpp/build/bin/llama-server"
SHA="$(sha256sum "$GGUF" | awk '{print $1}')"
mkdir ./self-owned-demo-receipts

python -m adapters.mineflayer.self_owned_llama \
  --run-disposable --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD \
  --output-dir ./self-owned-demo-receipts \
  --llama-server "$BIN" --gguf "$GGUF" --gguf-sha256 "$SHA" \
  --model-alias relay-self-local --model-port 12345 \
  --ctx-size 4352 --gpu-layers 60 \
  --ready-timeout 90 --model-timeout 12
```

- `--gpu-layers` の値はVRAMに応じてオペレーターが決めてください。0はCPUのみ。
- 起動時に`--host 127.0.0.1 --parallel 1`を強制し、
  `/health`と`/v1/models`のaliasをチェックします。
  **GGUFのディスクバイトSHA256照合は、GPUが実際に何を計算したか
  という独立した証明ではありません。**
- Minecraft側は既存S49だけがActionを発行し、L0はL2 HTTPを待たない。
  L2出力はread-only。停止した古いL2はActionやHabitsを更新できません。
- `owned_llama_server.log`、`owned_llama_receipt.json` を追加保存します。
  process PID、バイナリSHA256、GGUF照合結果、loopback readiness、
  Java/Nodeデモの返値、モデル子プロセス終了結果を追跡します。
  **物理STOP ACK、VRAM解放、GGUF実ロードの独立証明は付けません。**
- 自分が起動した新しいプロセスグループだけSIGTERM（必要ならSIGKILL）。
  他の推論サービス、Minecraft World、古いプロセスを停止しません。
- 空きポートのチェックはTOCTOU競合の余地を残すため、他者が同時に
  ポートを奪った場合は操作を中断して証拠を保全してください。
- 本モードのCIは実GGUF、GPU、Minecraftを立ち上げず、代替localhost
  モデルのプロセスで事前条件と終了処理だけを検証します。

**旧実機記録は不変。** この新モードの実World＋実GGUF同時実行は、
ユーザーのローカル実行結果が得られるまではNOT_RUNです。
