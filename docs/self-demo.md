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


### Mineflayerの実依存解決を起動前に確認（2026-10-11実機失敗への修正）

2026-10-11のSelf所有llama.cpp＋Minecraft単発実機試験は**FAILED**
（実Action・L0観測・L2 chat POSTは0）。使い捨てWorldと
llama-serverは起動したが、独立worktreeの`node_modules`を
外部ディレクトリへのsymlinkにしたため、`bridge.mjs`がロードする
Mineflayerの内側から`minecraft-protocol`を解決できずに終了した。
元の失敗原本・SHA256はIssue #537に保存。再試行ではない。

**今後の新しい実行**では、独立worktreeの`adapters/mineflayer`内に
lockfileどおりの物理的な`node_modules`をインストールする。
既存外部node_modulesのsymlinkを流用しない。実行前に、既存Worldや
既存推論サービスに触れず、次の**非接続**チェックを行う：

```bash
# 自分が所有する新規・独立worktree内だけで行う
npm ci --omit=dev --no-audit --no-fund --prefix adapters/mineflayer
test -d adapters/mineflayer/node_modules
test ! -L adapters/mineflayer/node_modules
node -e '
const {createRequire}=require("node:module");
const {resolve}=require("node:path");
const fromBridge=createRequire(resolve("adapters/mineflayer/bridge.mjs"));
const mineflayer=fromBridge("mineflayer");
const version=fromBridge("mineflayer/package.json").version;
const internal=createRequire(fromBridge.resolve("mineflayer"));
const protocol=internal("minecraft-protocol");
if(version!=="4.39.0" || typeof mineflayer.createBot!=="function" || !protocol)
  process.exit(1);
console.log("bridge Mineflayer and transitive minecraft-protocol import OK");
'
```

Self所有起動ラッパー`self_owned_llama.py`自身も、これと同等の
**実`bridge.mjs`基準・内部依存までのimport検査**を、GGUFのSHA256
計算、llama-server起動、Minecraft起動の**すべてより前**に実施し、
依存配置が不十分なら`BLOCKED`として0モデル／0Worldで終了する。
自動`npm ci`、既存symlinkの削除、実行試験のリトライは行わない。

この修正のCIは非接続モックの物理ディレクトリ、欠損依存、
誤バージョン、node_modules symlinkの負例を評価する。
CI成功はあくまで起動前検査の資格化であり、
**2026-10-11 FAILED試験をPASSへ書き換えない**。


## Lane C C15 → Self の読み取り専用接続（2026-10-11）

[Lane C #522 / Draft #525](https://github.com/rinsakamo/relay-self/pull/525)
で凍結された `goal_witness.py` と `ac_c_c15_manifest.json` を
**原文／凍結ハッシュを維持して**既存Self製品Draftへ取り込む。
C15の元のCIテストも継承する。C16 #531の実機Runner自体は
取り込まず、独立した承認・資格化のままとする。

Selfの現在のS49 Action OUTCOMEでは、制御開始前probe、
set_control ACK、clear_controls ACK、終了後probeは保存しているが、
**C15の要求する終了後の独立した2回目probeと、元の連続した
adapter JSONL streamは保存していない**。したがって、
**既存のSelf 1.0 / Self 1.1物理レポートからC15の
GOAL_REGION_OBSERVEDを後付けしてはいけない**。
Goal/Alternative領域も現行のSelf実行では事前指定していない。

追加した `self_spatial_review.py` は、**別途取得済みの本来の
Mineflayer JSONL全文**、既存のS49 native_report、明示的な
3D領域仕様が揃った場合だけ、厳密なC15 `EndpointReducer`を
**読み取り専用**で起動できる。4枚のAction前後・dispatch・cleanupを
S49のデコード済み原本に対してsession/action/seq/snapshot/ACKまで照合し、
C15の元の時系列検査と2回のpoststop probe判定に委ねる。
元のシーケンス番号を詰め直したり、2回目probeを合成したりしない。

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
mkdir spatial-readonly-evidence
python -m adapters.mineflayer.self_spatial_review \
  --native-report /path/to/original/native_report.json \
  --source-transcript /path/to/original/adapter-source.jsonl \
  --regions /path/to/predeclared-regions.json \
  --action-index 0 \
  --output-dir spatial-readonly-evidence
```

`--regions` は `{"goal":{"low":[x,y,z],"high":[x,y,z]},
"alternative":{"low":[x,y,z],"high":[x,y,z]}}`。
これは現行S49に存在しない **事前宣言された課題の目的領域**として
扱う必要がある。目標を観測後に合わせ込んでも因果成功証拠にならない。
処理の結果は `spatial_review.json` に保存し、デフォルトで
既存証拠を上書きしない。

結果が `GOAL_REGION_OBSERVED` でも、その分類は**空間的終点の観測のみ**。
Minecraftサーバーとの独立認証、Actionが原因で目標達成したこと、
負報酬ラベル、S17 LearningFeedback、S10/11学習権限、
またL2からのAction許可を付与しない。
既存S49にC15要件を追加する新しい物理測定は**NOT_RUN**。
この読み取り専用の接続は、SelfとLane Cのソースコード上の
最初の合流であり、実Worldでの因果学習合流ではない。

## Self の認知タイムライン（RelayUI向け・読み取り専用）

既存の S49 レポートを**もう一度Minecraftを起動せず**に読み、
各エポックの World 観測 → L0 選択 → S16 Action 結果を一画面で表示します。
実際に所有する任意の過去のレシートについて、元のファイルを変更しません。

```bash
PYTHONPATH="$PWD/src:$PWD/tests:$PWD" python -m adapters.mineflayer.self_timeline \
  --native-report ./self-demo-receipts/native_report.json
```

同じコマンドに `--memory ./self-demo-receipts/observed_memory.json` と、
`--live-l2 ./self-demo-receipts/live_l2.jsonl` （存在する場合）、
`--format jsonl` を追加すると、RelayUI等で消費できる安定した
`relay-self.product.cognition-timeline.v1` 行指向イベントが標準出力へ流れます。
ターミナルで直接見る場合はデフォルトの短いテキスト表示を使います。

**境界:** このビューアは Action を発行せず、L2 を起動せず、
Memory・学習・Habitを書き換えません。過去の S49 レポートに保存されていない
原本や因果的なゴール成功を生成しません。L2 のテキストは非信頼の参考情報であり、
WorldとL2の物理的時間重複の独立証明とは表示しません。
既存レポートや Memory と矛盾するソースは `UNDETERMINED` として拒否します。


### オフラインHTMLビュー（RelayUIに接続する前の軽量プレビュー）

テキスト/JSONLと**同じ読み取り専用タイムライン**を、Webサーバー無しで
ブラウザで開ける静的な `timeline.html` にできます。

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
python -m adapters.mineflayer.self_timeline \
  --native-report ./self-demo-receipts/native_report.json \
  --format html --output ./timeline.html
```

`--live-l2` と `--memory` も従来同様に指定できます（レシートがある場合のみ）。
HTMLにはWorld観測・L0判断・S16 OUTCOME・任意のL2要約・Memoryの
source-bound結果が表示されます。**JavaScript、外部CDN、通信、画像取得は無く、
実行も学習も一切行いません。** モデル文章はHTMLエスケープします。
`--output` はまだ存在しない `.html` パスであることが必須で、原本・既存
HTMLは上書きできません。ブラウザ画面は既存のS49記録の表示であり、
現在進行中のMinecraftをライブ監視したり、Goal成功を認定するものではありません。


## B0 optional rotten-flesh eating check (2026-10-13)

The low-cost existing S46 EatCursor now allows `rotten_flesh` as a
**last-choice** fallback. The existing S51 source-correlated actual eater
still requires native equip→consume applied receipts, Minecraft food-meter
increase and inventory count decrease. A rotten-flesh meal can cause the
Hunger effect; its nutritional **net benefit is not yet attested**, and
the M Lane research metabolic ledger has **not** been credited.

The existing S51 **operator-staged** disposable World runner can be invoked
with `--food-item rotten_flesh` after separately approved, fresh R/S
physical authorization, using the SAME optional preflight/cleanup protocol
as its default bread case:

```bash
S51_REAL_SERVER_CI=1 PYTHONPATH="$PWD/src:$PWD/tests:$PWD" \
  python -m adapters.mineflayer.s51_eat_real_ci \
  --food-item rotten_flesh \
  --report ./fresh-rotten-eat-report.json \
  --server-log ./fresh-rotten-server.log
```

**Do not run this without fresh approval.** Uses operator `/give` of
corrupt flesh plus an explicit hunger staging effect; that is not a
zombie-kill drop, autonomous SEEK, real M0 energy debit/credit or a
completed bacterium-like survival loop. In this optional mode the
report is classified `B0_ROTTEN_FLESH_OPERATOR_STAGED_NATIVE_EAT_ONLY`
and explicitly marks `zombie_drop_observed=false` and
`m_energy_credited=false`. Existing bread-mode default classification,
old evidence and issued-action logic are unchanged. Real World-source
authentication and exactly-once physical M credit remain the next gate.

## B0 opt-in physical ground-item foraging (still NOT_RUN)

The existing `s51_eat_real_ci` operator runner now accepts
`--food-source ground --food-item rotten_flesh`. In ONE
owned disposable World, it summons precisely one `rotten_flesh`
ground item near the original observed body (not a zombie kill),
selects a visible `item` entity using the original complete
native source, and admits up to eight **distinct, authorized S50
SEEK** actions toward that location. An observed item entity
disappearance plus `rotten_flesh` inventory increase is required;
then the existing S51 issued EAT independently checks both inventory
decrease and hunger-meter increase.

It does **not** establish the exact item's metadata identity,
causal pickup or zombie origin; these require improved original
bridge evidence. No autonomous hunting, M ledger credit, Hunger
effect accounting, full L0 survival, L2 or scientific selection claim.

After **fresh, explicit** R/S World authorization, example only:

```bash
S51_REAL_SERVER_CI=1 PYTHONPATH="$PWD/src:$PWD/tests:$PWD" \
  python -m adapters.mineflayer.s51_eat_real_ci \
  --food-item rotten_flesh --food-source ground \
  --report ./fresh-ground-b0.json \
  --server-log ./fresh-ground-b0-server.log
```

Never use this command on a persistent/personal World, and never
run it under an already consumed one-shot grant. CI is offline
only; new physical runtime remains unqualified. The existing
`--food-source inventory` default preserves previous S51 modes.


## B0 M0 bridge (2026-10-13; engineering candidate, WORLD_NOT_RUN)

The existing S51 `--food-item rotten_flesh` and optional
`--food-source ground` paths now feed only verified, terminal S51
EAT outcomes to an S-owned session ledger, then make one fresh,
non-issuing L0 native-World decision. No item pickup/UNKNOWN/replay
credits energy; each decision WAIT costs basal, each closed S50 SEEK
costs MOVE, and starvation is irreversible. Energy is an experimental
M0 value, **not** Minecraft hunger, physical joules or a reward.
L0 EAT/SEEK/WAIT reactions are designed, not spontaneously evolved.

`experiments/metabolism_viability.py` reuses the EXACT unchanged M0
source blob `4ecabd2811377a05925fb85cb32070dcd2d6bb0e`
from M #617 at `4bdc9daf0444e55908cff321111bae9a2927942c`.
This is one-file source reuse on the S product Draft, **not** a
merge or cherry-pick of M's Draft, and future M edits need manual
reconciliation. Decision ticks do not continuously measure wall
time, including subprocess wait time. The current S51 disposable
server script has NOT yet been placed behind the RSEE-qualified
preflight/evidence owner #575. R/S/V and a fresh one-shot local
authorization remain mandatory before any Minecraft/Node/Java run.

Synthetic offline tests and CI do not demonstrate physical B0 success,
zombie drops, native item metadata, no-food World starvation,
learning, evolution or a V scientific result.


## B0 — qualified RSEE dependency reuse and local admission (offline code only)

B0 rotten-flesh modes now **require** an explicit RSEE checkout at immutable
[#588](https://github.com/rinsakamo/relay-self/pull/588)
`34820f6bf391c77f325d7c29d3b779a33e3ca835`. The S runner
reuses the ORIGINAL owner `golden_admission.verify_qualified_world`
(#583 qualified initial stopped World), `node_runtime.verify_node_runtime`
(#586 real npm installation) and the ORIGINAL R-owned `bridge.mjs`
with byte-pinned RSEE source. It does not merge R's Draft into S.
It checks the original World, copies it into a **disposable** server
directory, then calls RSEE on the copy again before Java. No Mojang
download, new seed, generated World or home World substitution in B0 mode.

CLI flags on existing S51 module (no new launcher):
`--food-item rotten_flesh --food-source inventory` for first
operator-given food; later choose `--food-source ground` for the
operator-staged single local item. Additionally require
`--rsee-checkout PATH --rsee-jar PATH --rsee-snapshot PATH
--rsee-manifest PATH --rsee-initial-evidence PATH
--rsee-node-runtime-root PATH --rsee-eula-accepted
--confirm B0-RSEE-I-OWN-ONE-DISPOSABLE-WORLD`.

These flags are **NOT an authorization**: require a fresh explicit one-shot
user physical grant plus independent R and V admission before even attempting
a real local run. The existing `S51_REAL_SERVER_CI=1` gate and empty
`NODE_OPTIONS` are also required. This B0 branch is non-LLM and never
starts llama.cpp/GPU. Current GitHub checkout has neither the local
qualified stopped World, nor operator machine access; physical trials
are `NOT_RUN`. Zero retry/fallback on missing verification.

The source RSEE module must be a physically present separate exact HEAD;
Git checkout HEAD and nine source blobs are independently checked.
New S code does **not** claim independent original-world qualification.
RSEE controls World/env identity; S controls Action and body ledger;
V controls the scientific result. Source object grants remain separate.


### No-food real-World negative control (NOT_RUN)

The SAME S51 operator runner now accepts
`--food-item rotten_flesh --food-source none` with the identical
pinned RSEE inputs, fresh per-run physical authorization and isolated
World. The runner provisions no food and repeatedly obtains fresh
native observations. Every WAIT is non-issuing yet debits M0 basal
energy; exactly one irreversible terminal is expected. It checks
absent inventory and absent observed ground-item entities with
non-truncated coverage before each step. The 64-decision cap is a
bound, not a retry, and a missing terminal or inconsistent source
fails. This test does **not** demonstrate food acquisition, learning,
or physically real energy; it tests the research ledger's starvation
consequence in a real World source stream. No Minecraft run has
been authorized or executed here.

 
### One-command read-only B0 RSEE check (no physical grant consumed)

Before proposing a real Minecraft run, use **the existing S51 entry point**
with `--preflight-only`, `--food-item rotten_flesh`, and the six complete
`--rsee-*` path values plus explicit `--rsee-eula-accepted`. For example,
with the already qualified RSEE host assets and separately checked #588
worktree (`$RSEE_CHECKOUT`):

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
python -m adapters.mineflayer.s51_eat_real_ci \
  --preflight-only --food-item rotten_flesh \
  --report ./b0-preflight.json --server-log ./b0-not-started.log \
  --rsee-checkout "$RSEE_CHECKOUT" \
  --rsee-jar "$BASE/minecraft-1.21.8.jar" \
  --rsee-snapshot "$BASE/bootstrap-approved-20261011-once/snapshot" \
  --rsee-manifest "$BASE/bootstrap-approved-20261011-once/snapshot_manifest.json" \
  --rsee-initial-evidence "$BASE/bootstrap-approved-20261011-once/initial_native_observation.json" \
  --rsee-node-runtime-root "$BASE/npm-mineflayer-4.39.0" \
  --rsee-eula-accepted
```

This mode calls original #588 RSEE owner validators read-only, preserves
the result in the normal S51 report, **never** opens a Node/Java/Minecraft
session and never consumes an experimental physical grant. A qualified
offline result still cannot authorize starting the actual World. Source
checkout, operator-owned artifacts and Python dependencies must exist
on the local host. A dry-run synthetic CI result is not a host attestation.

### B0 one-shot original evidence (2026-10-13)

RSEE physical S51 runs reserve `<report stem>.native.jsonl` and
`<report stem>.commands.jsonl` with exclusive creation before Java. The
native stream tees exact bridge stdout bytes, including unread terminal
frames after process exit; existing decoder and transport exceptions are
preserved. Command lines record attempted sends, not applied effects.
No new launcher, RSEE bridge change or Action authority is introduced.

The report retains the issued Action ID and terminal even on executor
failure, verified eating outcome before M0 credit, body state immediately
before credit, credit count, intake/cost/tick and the next native probe.
Node cleanup errors or nonzero exit prevent PASS. Java-start attempt and
observed physical start are separate: the original helper creates its log
only after spawning Java. Cleanup exit does not by itself prove STOP ACK;
inspect the preserved native bytes and independently check owned PIDs and
port release. A staged-food loop is engineering evidence only, SCIENCE_NO_GO.


### B0 no-food next trial — proof ceiling and terminal non-reentry

The no-food mode is *not* the completed one-shot `inventory` trial.
It remains **NOT_RUN / NEW_EXPLICIT_GRANT_REQUIRED**. It uses the
unchanged M0 `MetabolismConfig(initial_energy=12, basal_cost=0.5)`:
if there is no verified food and only nonissued WAIT steps, the
experiment ledger reaches exactly one terminal on decision-tick 24.
Each decision is taken from one NEW correlated Mineflayer World probe,
with inventory empty, no visible ground-item entity, complete nearby
coverage, no food credit and cost 0.5. This does not prove 24 elapsed
Minecraft ticks, Minecraft hunger damage or in-World HP death.

After that terminal, a **new 25th correlated probe** must be obtained.
The same body must reject both a further L0 decision and an M0 WAIT
advance without mutating its terminal state. A reporter string is NOT
sufficient: code actually exercises both negative admission checks,
retains the postterminal probe seq and refuses any unproven denial.
Unknown item/coverage or replay causes FAIL, not a starvation PASS.
One live World run requires **one new, explicit, mode-specific grant**.
Existing B0 inventory authorization was already consumed.


### B0 ground one-shot — fresh user grant, L0-grounded SEEK

As of 2026-10-13, the previous `inventory` and `none` World grants
were each consumed by their separate successful single-session trials.
A *new explicit* grant for one `--food-source ground` World trial was
received. **The grant has not been consumed by these source edits or CI.**

Ground mode first uses the operator World Hunger effect only to
establish a genuine *native-measured* food deficit while the World is
still item-free. Each correlated hunger observation gives one designed
L0 WAIT; only preceding WAIT decisions incur M0 basal charges.
After hunger falls below 14, the Hunger effect is cleared and the
operator summons exactly one local ground-item fixture. The fresh
native observation must independently lead the existing cheap L0
to `SEEK` the unique observed item, otherwise physical movement is
rejected BEFORE issuing the next Action. Subsequent proposed SEEK
movements also require fresh L0 SEEK agreement. S50-issued movement,
pickup-disappearance plus inventory-rise consistency, S51 issued EAT
and verified native food/inventory change, one M0 credit and next
fresh L0 are separate evidence boundaries.

The external summon is NOT endogenous food creation. The entity's
item-stack metadata and playerCollect event are not authenticated by
the current native protocol. A consistent inventory-rise + item
disappearance is **not** direct causal proof of that exact item being
picked up or of a zombie drop. The L0 here is a deliberately coded
cheap behavior, not learned/evolved foraging, and does not establish
autonomous exploration of unknown resources. Human operator fixture,
physical tests, and V causal comparison remain separate.

**No additional Java/Node/World/LLM/GPU invocation has occurred as
a result of this implementation commit.** Local WSL2 LocalCodex must
verify exact updated PR HEAD and successful CI, source binding and
read-only RSEE preflight, and then use the new mode-specific grant
for **exactly one** real trial with fresh output paths and no retry.


### B0 controlled two-epoch World trial — new one-shot grant, NOT_RUN

The user authorized **one new bounded multi-epoch physical World run**
after three individually consumed one-shot B0 trials. The existing S51
runner gains an opt-in `--food-item rotten_flesh --food-source ground2`
profile on the same RSEE #588 stopped snapshot. There is **one** Java
start, one owned Mineflayer session, two separate sequential
**operator-summoned single-item** ground fixtures, and at most the
existing 8 issued SEEK moves per fixture. The local World never
auto-creates food as an autonomous resource.

Per epoch: after source-qualified native appetite (food <14), the
operator clears the hunger *effect*, summons one item, and requires
fresh L0 SEEK before S50 issued moves. Item disappearance plus inventory
increase is consistent pickup evidence only. A later **unique EAT Action
ID** per epoch uses the original S51 equip/consume native effects, terminal
OUTCOME, source-verified single consumed item and a single M0 +4 food
credit (with basal cost), followed by the next fresh L0 decision. Native
request/action IDs are namespaced across the epochs; no second issue of
an uncertain Action is permitted. The second epoch reuses the SAME
ledger and session, never resetting energy or the meal/credit tally.
The terminal must have `credit_count=2`, `meals=2`, positive energy
and nonterminal body; first-epoch evidence is retained in the report
even if the second fails. Original stdout/command JSONL remain retained.

World hunger/food is **not** M0 simulated energy. The operator's hunger
effect is a controlled environment intervention, not discovered
scarcity or a calibrated physiological process. Two meals in one
session do not show positive net long-term viability or evolution.
The L0 energy sensor is observed but **does not currently drive the
EAT/SEEK/WAIT policy**; merely toggling sensor gain would be
non-discriminating, so do not claim a sensor-driven behavioral response
or run extra sensor-off World trials under this grant.

Physical execution must wait for final exact-HEAD CI success and the
original RSEE read-only `--preflight-only`, use NEW exclusive evidence
paths, and consume the fresh **single World start** authorization only
on Java start. No retry/fallback. Any additional controls need
separate prospective V #619 experimental authority and user grants.


### B0 interoception → L0 choice (opt-in, OFFLINE ONLY, 2026-10-14)

**Why:** Previous physical `ground2` qualifies only a designed
native-food/item L0. The M0 `observe_energy` reading was logged but
did not causally affect `WAIT/SEEK`. The new strictly opt-in
`--b0-forage-policy sensor_gate` inserts a *designed* low-cost
decision gate for a uniquely observed ground item when native Food
already indicates hunger (the existing `EatCursor` NO_FOOD case).
The threshold is explicitly fixed at **M0 sensor reading <= 8.0**.
This is neither learned motive, evolutionary fitness, emergent value,
nor proof that 8.0 is the appropriate survival policy. M0 physical
ledger, costs, intake, event attribution and terminal behavior are
unchanged.

**Intervention definition:** with `--food-source ground2` only,
`--b0-sensor on` uses unchanged `Interoception(gain=1, bias=0,
quantum=1)`; `--b0-sensor masked` uses `gain=0, bias=12,
quantum=1`, so it always reports **12** regardless of true M0 energy.
The original M0 evaluator still advances identically. This is an
explicit *high constant readout* lesion, not physically absent
sensor, and its choice of fixed bias is a potential intervention
confound for V to review. All other existing S51 modes continue to
use `native_only/on` defaults; the existing B0 native ground and
two-epoch physical evidence remain unaffected. `native_only` is a
cheap deterministic comparator. `on` with the same policy is a
sham; no matched independent World trial is yet authorized.

**Matched synthetic counterfactual:** using the same typed
Mineflayer-shaped hungry native item observation and identical M0
energy **E=7 / tick10** after 10 WAIT costs:
- `sensor_gate/on`: observed 7, L0 SEEK
- `sensor_gate/sham`: observed 7, L0 SEEK
- `sensor_gate/masked`: observed constant 12, L0 WAIT
- `native_only/on`: L0 SEEK.

At **E=12**, `sensor_gate/on` and `sensor_gate/masked` WAIT
while `native_only/on` SEEK. Inventory EAT, true terminal safety,
source validity, Action authority and M0 cost are not lesioned.
These are deliberately *coded policy outputs*, not empirical
survival, value learning or a V causal advantage.

`--b0-forage-policy sensor_gate --b0-sensor on|masked` is accepted
only under the already opt-in `ground2` CLI. Argument validation
is before any World start. The new switches do not authorize World
launch, test repetition or retroactive reclassification. Prior
ground2 one-shot grant is consumed; **new live comparisons require
separate explicit user grants, a V #619 preregistered reference,
sham/cheap controls and RSEE preflight for each run.** If the
`native_only` cheap policy does as well, scientific incremental
value remains NULL/NO-GO.


### B0 nonforcing ground sensor contrast — offline runner ready, no real grant

The strictly opt-in S51 `--food-source ground2observe` mode
records L0 WAIT while one operator-staged ground item remains source-visible.
Each nonissued WAIT charges the authentic unchanged M0 experimental
basal cost, requests a new correlated World probe, and may end
in `M0_TERMINAL_NO_PICKUP`. A live but unproductive 24-decision bound
ends as `HORIZON_CENSORED_NO_PICKUP`, NOT as death. If L0 later chooses
SEEK, the existing independently issued S50 moves/S51 EAT and
one-credit-per-EAT receipt chain is reused. The same session and body
continue to a second food epoch when a first meal is actually observed.
A complete two-epoch episode returns `TWO_GROUND_MEALS_COMPLETED`.
Disappeared/ambiguous item, missing source, unknown Action or invalid
effect is engineering INVALID, not a physiological behavioral outcome.

This is a source/decision-tick-limited observation path, not elapsed
Minecraft time or an ecosystem with autonomous food generation. It does
not establish native collect event identity, zombie provenance, genuine
homeostatic learning, survival advantage, or a V scientific contrast.
The hard-coded `sensor_gate` threshold and constant bias12 OFF mask
are explicit manipulated-policy confounds; a sham and cheap native-only
reference need separate paired freeze conditions. The existing RSEE/S51
physical runner can parse the mode, but **no ground2observe physical
launch is authorized or has run**. Earlier ground2 grant is consumed.
Use only read-only preflight/offline tests until new user permission and
V #619 prospective comparison protocol.


### S-owned V2 prospective fixed-horizon single-fixture study (OFFLINE ONLY)

S #545 adds an explicit opt-in `--food-source groundv2 --b0-v2-arm
SENSOR_ON|SHAM_ON|SENSOR_MASKED|CHEAP_NATIVE`. It does not alter any
historical `ground/ground2/ground2observe` default or frozen evidence.
It uses the existing S51/RSEE physical owner (never a second launcher),
but **NO real World startup is authorized**. Per original V #625 frozen
manifest, its prospective S study mode sets a **GLOBAL M0 16-tick
horizon** inclusive of all pre-item hunger WAITs, **8 total issued
MOVE max**, and a **single precommitted operator fixture after the
11th M0 decision tick**. No learned motor/value/utility emerges.

The single item is offered in all four arms at the same *declared
simulated M0 tick boundary*, not as a function of how quickly a
previous meal was consumed. If actual World hunger is not below
native food14 **exactly at M0 tick11**, source admission FAILS
rather than rescheduling or claiming a matched stimulus. This
is not a verified match of elapsed **Minecraft World ticks**;
record native/host timings and compare independently in R/V.
No automatic item creation occurs before the controlled fixture.

L0 WAIT in sight of source-qualified single item is nonissued
but charges genuine M0 basal 0.5; it can be horizon-censored rather
than forced SEEK, and no true M0 terminal should be claimed at E4.
SEEK uses S50 issued MOVE under the same global horizon and existing
S51 verified EAT, with true food receipt +4 (basal charged). After
a verified meal the runner continues actual independent native WAIT
observations to tick16, not a fake no-op or Action. The report
retains true final M0 E, action counts, source provenance, item
identity UNKNOWN, food receipt, and explicit
`world_time_matched=NOT_INDEPENDENTLY_ATTESTED`.

This fixes S's major *local source* 24-opportunity/per-epoch MOVE
budget mismatch for a **new** study mode. It does not by itself
satisfy V independent frozen Golden World clone, matched
exogenous host/World tick schedule across 4 arms and seeds,
R original-byte/Goal admission, or V scientific evidence.
If the cheap policy achieves the same food outcome as ON,
incremental value is unproven. Note: under a 16-M0-tick
horizon with initial E12 and a single opportunity at tick11,
**all four arms can remain M0-terminal-free**; early SEEK
differences can be relegated to secondary EAT/energy outcomes
without promoting the primary. Every arm/start needs a fresh
explicit one-shot user grant, so this mode is **NOT_RUN**.


### R/V V2 World-time native source bracket — extra review evidence, not source admission

Only the opt-in S `groundv2` study passes an initially empty
`source_time_bracket` to the existing ground runner. Before operator
`/summon`, preserve the original **correlated item-free probe**
session/seq/request_id and existing Mineflayer
`snapshot.time={time_of_day,day,is_day}`. After the fresh native
single-item discovery probe, preserve the matching post-visible
session/seq/request_id, native time, item entity ID and M0 ticks.
Missing native time in either observation FAILS CLOSED in this
prospective mode. These fields reside in the physical original
report and should be independently compared with the raw stdout
and command-stream originals by R/V; they do **not** replace raw
bytes, prove an original Minecraft TCP-level packet, directly
attest the server console command time or pin equal elapsed
World time across arms. One asynchronous `/summon` can occur
anywhere between the two observations; its **exact server tick
is still UNKNOWN**. Explicit labels prevent promotion:
`fixture_command_ack=NOT_NATIVE_ATTESTED`,
`world_command_effect_timing=BRACKET_ONLY_NOT_EXACT`,
`minecraft_world_elapsed_tick_parity=NOT_QUALIFIED`.

Old product modes and RSEE/Node/Myneflayer protocol retain
their existing source and action semantics; only the V2
experimental opt-in argument is passed. Four independently
matched freezes, equivalent native World timing, no hidden
concurrent issuer, R original-byte review and V prereg admission
remain outstanding. No World authorization and no live V2 trial.

### V6 B0/L0 typed native WAIT source (OFFLINE ONLY)

V #619 paired-World pre-admission, Draft #625 exact head
`f1a747891e9620e4ab7c86f46f6c8b28e31e5f30`, specifies four
independent World-start groups x LOW/HIGH initial M0 E12/E20 x six
arms = 48 *unexecuted* slots, not grants. Food13, single item at
2.5m, 11 charged M0 WAIT steps, horizon16 and maximum eight issued MOVE.
Matched elapsed Minecraft-native World ticks at the item opportunity
within each paired start are R/V admission requirements; they are not
interchangeable with M0 decision tick or wall time.

S `adapters/mineflayer/b0_v6_source.py` provides
`new_v6_m0_l0_owner`, `source_only_v6_first_choice`, and the
`review_v6_native_wait_to_first_choice` typed source-stream checker.
The latter requires eleven distinct ordered, non-replayed native-shaped
item-free Mineflayer probes in one session, with complete entity
coverage and no inventory food, then a new correlated Food13/one-item
2.5m probe. It performs eleven actual existing M0 WAIT basal charges
(0.5 per decision) and runs existing S L0 selection without issuing
Action or minting S51 EAT credit. LOW E6.5 chooses SEEK with ON; HIGH
E14.5 chooses WAIT; sham, mask, always-SEEK, always-WAIT and equal-info
cheap retain their pre-registered choices.

These tests operate on typed *synthetic-shaped* source observations,
NOT independently acquired original real World evidence. A sequence of
eleven source observations does not prove eleven Minecraft World ticks,
actual operator-spawn command time or cross-arm native-time parity.
Source results explicitly attest neither originals nor real S50/S51
Action, item acquisition, ecological benefit, authorization or V GO.
Always-WAIT maps to `B0EnergyLedger(forage_policy="no_ground_seek")`
only in the offline comparator: the existing S51 physical CLI still
rejects that policy and has no V6 study mode. Equal-info threshold
parity is expected and allowed for bacteria B0, not evidence for
advanced learned cognition. Existing groundv2 and all prior frozen
modes, RSEE Golden, main and historical B0 evidence are unchanged.

Next only after independent native World-clock and Golden source
qualification: build a separately opt-in physical six-arm S51/RSEE
controller under S ownership, implement genuine native WAIT/Action
and verified EAT/cost receipts, then request one fresh permission
per intended live World session. Do not create a new launcher or
treat a 48-slot planning grid as permission to execute. Historical
R #575 B0 58-file/50-index review is complete REVIEW_ONLY; no rerun.
State: S_V6_SOURCE_STREAM_ONLY / WORLD_TRIALS_0 / G3_NO_GO.


## Candidate V6 native World age source (2026-10-14, NOT_ADMITTED)

The opt-in `RELAYSELF_V6_NATIVE_CLOCK_V1=1` binds the 1.21.8
Mineflayer bridge to original clientbound `update_time` packet callbacks.
It records server world age (raw i64, decimal string), separate raw daytime
and host monotonic ns, with the original bridge session/seq. No interpolation
occurs between server packet updates. The feature is disabled by default;
the existing S51 physical B0 runner **rejects the env flag** until a new
R-authenticated binary/runtime source and external per-session grant exist.
The changed bridge itself is NOT the frozen #588 RSEE bridge byte identity.

The raw packet is NOT a timestamp for the server-console `/summon` effect,
S50 movement, S51 EAT or any actual food acquisition. The server sends
updates sparsely and display time can jump. Eleven M0 ticks cannot substitute
for 11 Minecraft World ticks. R must independently qualify server-owned
effect receipts, exact packet bytes/source producer+SHA, initial Golden
live World and clock parity before V may admit the frozen V6 paired trial.
No V6 World or science/production outcome is asserted.

### V6 prospective server-atomic food/World-age witness (SOURCE ONLY)

An additional S-only pure contract lives in
`adapters/mineflayer/v6_atomic_fixture.py`. It returns the *bytes* of a
proposed Minecraft Java 1.21.8 (data pack format 81) `pack.mcmeta`,
`data/relayself_v6/function/install.mcfunction`, and
`data/relayself_v6/function/atomic_food.mcfunction`. It does not
install a datapack, create a clone, start a server, issue a World Action,
call `/summon`, modify frozen Golden #588 or use prior permissions.

The prospective operator commands, **NOT authorized by this document**,
would be `function relayself_v6:install` before trial and
`execute at RelaySelf run function relayself_v6:atomic_food` when an
independently qualified R/V experiment requests a first food item.
The updated **V2 candidate source** uses a persistent `#attempt` scoreboard.
The install function initializes missing scores with `add ... 0` rather
than resetting them. Each call increments `#attempt`; only count 1 is
allowed to clear receipt fields, read `time query gametime` into
`#before`, `summon minecraft:item` with one rotten flesh at ~2.5/~0.2/~,
and read game time into `#after`. A second call increments to 2 but cannot
repeat the summon or overwrite the first receipts. R must read all four
scores `#attempt/#before/#after/#ok` from independent *original*
server stdout/command and native entity receipts. Only attempt=1,
before=after and success=1 can become an *atomic same-server-tick
candidate*.

**Not a production protocol yet.** Minecraft datapack parsing, function
loading, server execution/success output, 32-bit scoreboard overflow
bounds, and exact effects have NOT been tested against the pinned Java
binary. The claimed values can be fabricated if not extracted from
independently verified ORIGINAL server logs. Repeated invocations of the proposed command are **blocked from
resummoning** by the attempt guard, and the surviving attempt count
invalidates the source claim. Privileged manual score resets or direct
unqualified commands are not prevented by code alone; these still require
R original server command logs and independent one-use verification. The generator returns an
explicit `S_V6_ATOMIC_FOOD_SOURCE_DESIGN_ONLY` and its source-only
claim parser returns only `S_V6_ATOMIC_SERVER_SCORE_CLAIM_REVIEW_ONLY`,
never R approval or scientific GO. The S51 physical CLI does not call
or install these functions.

**World-start accounting:** first compare the untouched 26-file Golden
to the stopped disposable clone *before* any added instrumentation;
record instrumented clone modifications separately and require R/V
approval of a new profile rather than pretending the changed clone
still matches frozen Golden bytes. Preserve M0 decision tick 11
separately from server game-time receipt and client `update_time` age
samples. Host wall time and display day/time-of-day are never World
age substitutes. V6 4 starts x 2 energy regimes x 6 arms = 48 slots
still unexecuted and NOT authorized. Actual end-energy primary
and original S50/S51 causal outcome admission remain V/R-owned.


### V6 atomic candidate V2 — revision authority

Only the S source candidate was revised; V #619's registered 48 slots,
16-M0-tick endpoint and equal native elapsed tick requirement are unchanged.
The exact SHA of the revised mcfunction is intentionally different from
V1; R must pin/review the new Git blob and verify real server semantics
before allowing it anywhere near an authorized clone. NO local Minecraft,
Java, Node or World execution occurred in this source revision.


### V6 separate trial-start server timestamp SOURCE V1 (2026-10-14)

`adapters/mineflayer/v6_start_marker.py` is a new, **separate**
in-memory 1.21.8 datapack generator; it does **not** rewrite the
independently pinned `v6_atomic_fixture.py` V2 food bytes. A per-session
32-hex trial nonce and one frozen `WORLD_START_A..D` slot are baked
into the start function's server `say` line. These are correlation
labels, **not** authenticators or physical permission.

The new source would install after the V2 food pack creates the shared
scoreboard objective `rs_v6_tick`, then only `add 0` missing
`#start_attempt` and `#start_gametime` scores. One call to
`function relayself_v6_start:start_trial` increments
`#start_attempt`; only count 1 can record
`time query gametime` into `#start_gametime` and emit the exact
slot/nonce marker. Count 2+ cannot overwrite the start receipt.
The function **never** summons food, changes World time or issues S50.
The operator would prospectively bind the marker issuance to the
first *genuine* same-session native L0 probe; it is not assumed that
the probe and marker occur in the same World tick. Future R original
command/packet evidence must establish order and source.

The S-only claim readers admit **no physical evidence**: a typed
first observation plus declared score and matching source SHA can
produce a `REVIEW_ONLY` start claim; a separately supplied V2 food
claim permits arithmetic `claimed_T_food - claimed_T_start`. This
is NOT the V-frozen cross-arm elapsed World tick parity result,
not an authenticated command execution and not `M0 tick11`.
R must independently pin BOTH producer Git blobs and the **newly
versioned six-file, two-pack staged-clone delta**, actual server
parsing/load, genuine command readback, caller source provenance,
one-use execution and start/food original timestamps. Neither pack
may modify original stopped Golden #588 World files. If the server
clock exceeds int32 scoreboard bounds or has any reset/overflow,
the study is invalid rather than silently unwrapping timestamps.
Physical S51 `groundv6` remains BLOCKED pre-Java.


### Prospective S original three-stream recorder (2026-10-14, NOT LIVE)

`adapters/mineflayer/v6_original_capture.py` adds a passive,
exclusive-create original-file capture adapter for future S51 use:
`server_stdout_original.log` from raw server stdout *before* UTF-8
decoding; `native_bridge_original.jsonl` from original Node stdout
*before* Python protocol decoding; and
`issuer_commands_original.jsonl` describing the S51 owner's
twelve predeclared, strictly ordered actual write **attempts** and
a distinct NONISSUED first L0 probe. It records native sequence numbers,
session/probe correlation, host monotonic ordering, original file bytes
and SHA256, and leaves incomplete captures in place on failure.
It is **passive** and cannot invoke the original S51 issuer, start a
World, install functions, summon food, mint M0 energy or grant V6.

`record_issuer_attempt` is an *issuer-side journal claim*, never a
server receipt. Because the two setup attempts precede the first L0
probe, their journal rows are buffered, then assigned the subsequently
observed first-probe correlation and written once. This provenance
annotation is retrospective, not an independently timed original
server acceptance. The produced SHA256 digest is captured *after*
bytes are written and is not an independently precommitted SHA.

**R protocol mismatch:** the Mineflayer producer emits a native
`observation(kind=spawn)` before it can produce the first
`observation(kind=probe)`. The current R synthetic envelope assumes
the first native observation is already the probe. It must be updated
to select the first *correlated item-free probe* while preserving earlier
spawn/other native originals, rather than altering/omitting real bytes.
The capture adapter is not yet wired into an admitted physical
`groundv6` S51 launch. Until R/V have reviewed the emitter and
server/clone/authenticity conditions, the S51 hard pre-Java STOP and
48 NOT_ADMITTED World slots remain unchanged.


**Pre-start server log capture:** the same passive recorder now accepts
`session=None` at exclusive original path creation before Java startup,
writes raw server stdout from the first byte, and binds its session
identifier **exactly once** from the first native
`adapter_started` frame with a 1.21.8/4.39.0 source-shaped header.
All issuer command attempts are blocked until binding. Such binding is
local provenance continuity, **not** independently authenticated server
origin. No real start has been authorized/executed by this adapter.

## DEV / QUALIFICATION / SCIENCE (2026-10-14)

通常開発は既存CLIの明示的DEV入口で反復する。各回、新しい絶対パスを指定する。
親ディレクトリだけ事前作成し、runの保存先自体は作成しない。

```bash
PYTHONPATH="$PWD/src:$PWD/tests:$PWD" python -m adapters.mineflayer.self_demo \
  --mode DEV --run-disposable --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD \
  --output-dir /absolute/development-root/new-run
```

既存S49 hostがMojang 1.21.8をダウンロードし、使い捨てWorld内でEULAを受諾、
Java/Nodeを起動する。Goldenや既存Worldは入力にしない。固定loopback port 25565
競合時は起動前拒否する。既存Action認可・STOP/cleanupはS49に委譲する。
新規Worldはrun内のowned-worldsに作成され、元hostのcleanupで削除される。
seedはserver生成で未attest。native reportとserver log、DEV receiptを保存する。

修正後は別保存先で再実行できる。`--retry-of PRIOR_DEV_RUN_ID`で履歴を記録する。
失敗receiptは保存し、既存保存先の再利用・symlink経路は拒否する。
World、証拠index、grant、DEV receipt、Git checkoutを祖先に持つ保存先も拒否する。
DEV receiptは常にDEV_ONLY。元S49診断reportのPASS/QUALIFIED表示は元ownerの
限定診断であり、DEV資格・科学入場の根拠にはしない。DEVはM0 credit、L2、
V6資格runner、V科学runnerを呼ばない。no flagsは従来どおりDRY_RUN。
QUALIFICATIONは別のR gateと新規preflightを要求し、消費済grantを再利用しない。
SCIENCEはV事前登録と独立評価に従う。既存科学NO_GO・凍結証拠を変更しない。

### B0 ground/EAT/M0 DEV（既存S51 owner、資格・科学には非昇格）

同じ **既存** `self_demo` CLIで、S51の真正腐肉取得・摂食・M0 ledger・次のL0観測をDEVとして反復できる。上の`native`（S49の3判断・2 Action）とは別の明示的シナリオで、共通Golden #588を使うRSEE資格化とは異なる。新規launcherは設けない。

```bash
PYTHONPATH="$PWD/src:$PWD/tests:$PWD" python -m adapters.mineflayer.self_demo \
  --mode DEV --dev-scenario b0-ground --run-disposable \
  --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD \
  --output-dir /absolute/development-root/fresh-b0-run
```

前提は既存S49/S51と同じローカルJava21・Node22+・Mineflayer4.39.0、外部ダウンロード/EULA、ポート25565の独占、空の出力先。各回は新run ID、新しい一時Worldを利用し、改修後は別のrootと`--retry-of`で履歴をつなぐ。DEVのEATにはoperatorがWorldで配布する腐肉を使い、ゾンビ自然ドロップ・内発的空腹価値・自律的獲得を証明しない。WorldはS51の既存ownerで開始/停止し、失敗なら原ログと失敗理由を残す。

`native_report.json`（既存S51 owner report）にアイテム取得のsource contrast、真正EAT Action/food delta、M0 ledger入金と次のfresh L0判断を記録する。`dev_receipt.json`には`dev_b0_*`という**DEV限定**の投影結果を残し、`SHA256SUMS`でrunの原始証拠を封印する。生じた`m_energy_credited`はM0実験上のledger eventでありMinecraft本体エネルギーではない。DEV receiptの`m_energy_credited`（資格済み認定）はfalseのまま、`engineering_qualified/science_success/g3_go`もfalse。STOP ACKと実World真正性は別途Rの独立監査なしには認定しない。

資格確認に必要なGolden/R readback、消費済みV6 grant、事前登録済みV #619の科学48試行は**このDEVコマンドから起動できない**。コード/CI上の受入は実World成功の代替ではない。

### B0 DEV原証拠の読み戻し（2026-10-15）

HEAD `291417539497f42269af9a15512cea320f375310` の新規DEV run
`ed76bb71518a4bebbe5639e768c74a79` は同一session
`0e177abe-88e3-498e-afc5-d850e789dc60` でループを閉じた。
空腹food 13 → L0 SEEK → MOVE OUTCOME 2件 → item消失と腐肉在庫0→1
→ 正式EAT OUTCOME 1件（food 13→17、在庫1→0）→
M0入金1件（energy 5.0→8.5、intake 4.0、cost 0.5）→ fresh seq145 L0 WAIT。
Java/Node exit 0、owned World削除と25565再bindを読み戻した。
これはoperator配置食料のDEV_ONLYで、自然ドロップや独立pickup因果認証ではない。

原証拠はホスト上の
`/home/rinsa/work/relay-self-b0-development-20261015/attempt-01` に保存。
同ディレクトリで `sha256sum -c SHA256SUMS` を実施する。
index自体のSHA256は
`d5446025952d9f4b34619a11a43c2d34cfb1cf5ce87b5e5ae40b262df88b30df`。
原DEV receiptにはS49用カウンタ流用によるdecisions/native_actions=0が残る。
原本は修復せず、source report/native JSONLから17判断・3 OUTCOMEを読み戻した。
本改修では今後のB0 receiptのみS51 trace由来の件数とsource scopeを投影する。
この投影修正後にWorldを再実行した証拠はない。

native seq146 `shutdown_ack` とseq147 `connection_end` は保存されているが、
独立STOP ACK証明を与えない。今後のDEV receiptは `stop_ack=UNATTESTED`
とscopeを記録する。成功ループ確認後は追加World試験を開始しない。
R資格PASS・V科学成功への昇格なし、V6科学48試行0、G3/production NO_GO。


## B1 initial local adaptation — DEV only

B1 uses the existing S51 disposable World owner (no new launcher), carrying a
single session and M0 body across two sequential operator-staged ground food
opportunities. In the first epoch it requests one stone wall between player and
item via the owned Minecraft console. This is **not** native proof that the
setblock effect was applied. Only a genuine supervised S50 MOVE with native
`BLOCKED` consequence can create a source-bounded L1 observational candidate.
The subsequent same-session source observation is used to propose a bounded
lateral waypoint through the existing S15/S16 issuer and S50 effect reporter.
The alternative may fail; there is no forced success, invented terrain result,
S10 learning authority, S11 Habit, or scientific claim. Both native S51 EATs and
exactly-once M0 credits must still close for full two-epoch DEV completion.

```bash
PYTHONPATH="$PWD/src:$PWD/tests:$PWD" python -m adapters.mineflayer.self_demo \
  --mode DEV --dev-scenario b1-local-adaptation --b1-retention on \
  --run-disposable --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD \
  --output-dir /absolute/existing-parent/new-b1-dev-run
```

For a *separate* cheap fixed-turn witness use `--b1-retention off`, always
with another **fresh** run root. OFF uses a fixed +Z after a native BLOCKED
Action and retains no Memory; ON stores one source-scoped observation using
existing Persistent Cognition and proposes -Z. A difference in these
**unmatched DEV runs is not a causal learning advantage**. Review the S51
`native_report.json`, `b1_observational_memory.json` (ON only if blocked),
original native/command JSONL, `dev_receipt.json` and `SHA256SUMS`.
If the local Java/Node/Minecraft runtime is unavailable: real World `NOT_RUN`.
Prior RSEE Golden/consumed V6 grants and V science 48 slots remain untouched.
