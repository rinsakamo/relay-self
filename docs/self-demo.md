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
