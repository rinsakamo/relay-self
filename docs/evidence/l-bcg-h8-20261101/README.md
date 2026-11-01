# L-BCG H8 実Minecraft DEV原本（2026-11-01）

**DEV_H8_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
実行exact HEAD `a244f5b2ae92878b337297398f5ff3cb48afbdb5`。
branch `dev/l-bcg-conditional-motion-shadow-20261101`、Draft PR #656。

外部保存先 `/home/rinsa/work/l-bcg-h8-evidence-20261101`。
事前固定JSON、失敗したoffline検証ログ、World原本を保持する。
`predeclared-before-command-audit.json`はWorld開始前の旧宣言。
実行前にcommand監査を強化したcommitへ進め、`predeclared.json`で
executor HEADのみを更新した。旧宣言時にはWorld起動0回。

- 新規World **1**、元S49 Action **1**、S16 Outcome **1**、retry **0**。
- 追加L-BCG Action/native probe/model/Learning/S10/S11/Memory更新 **各0**。
- 元L0：`WAIT(event8→probe10) → MOVE_AWAY(20→21) → WAIT(56→57)`。
- Action `s49-native-move-20` / `MOVE_BACKWARD`、S15/S16 before23 / after30。
  元実測変位 **0.6269065734210608m**。方向は歩容値ではない。
- session `928fb68a-5582-485c-9f3d-2de7e80f7ac0`。
  Paper World UUID `5a7423d9-6c57-4eb0-a814-690faa54824f`。
- Action前の元native seq21 / request `s49-actual:928fb68a-5582-485c-9f3d-2de7e80f7ac0:event-20`。
  Body/Worldは同一Presentからの既存projection。
  position=(-9.5,-60,-3.5)、health20、food20、saturation5、敵距離2m。
- 元L0選択後、Executor実行前にexclusive作成した
  `run1/capture/h8_preaction_sources.json`へ、元行digest、prefix11228 bytesのSHA、
  session/request/seq、Body/World、8条件UNKNOWN、`DEFER_UNKNOWN`を記録。
  次epoch seq57、S16/Paper OutcomeからAction前の条件を逆算していない。
- 独立Goal owner receipt、gait receipt、P1/M0 correlated sensor receipt、
  voxel obstacle source、World revision、qualified post-clear trainingは未取得。
  L16 operator plan target(0,0)、tolerance0.49と水平幾何10.124228365658293mは
  operator計画だけであり独立Goalではない。
- P1 #626 exporterはcheckout未統合。M0 adapterは存在するがroute Bから
  owner sensor/native tick対応を渡していない。既存Paper M02 basal/exhaustion
  logをM0 energy ledgerやP1状態に流用しない。別lane mergeなし。
- preaction診断も次epochの既存L-BCG shadowも **DEFER_UNKNOWN**。
- Paper callbacks254–261、reported-input OFF motion254–256、合計約0.0642466m。
  **EFFECTIVE_CLEAR_NOT_ATTESTED / GOAL_UNDETERMINED / QUALIFIED_TRAINING_WORLDS=0**。
  8callbacksは8Worldではない。

## 監査とcleanup

`independent-audit.json`は別プロセスの元S7/S16/Paper/packet/L0/source/cleanup照合。
元L0は元観測に対する既存policyのread-only再評価で照合し、実Actionは再実行しない。
全S7送信commandを元S49の3判断probe、S15 before/after、元L22 settling5件、
元L16 goal確認2件、元移動/clear2命令と順序一致させ、追加read/effectを拒否した。
L-BCGが追加したprobe/Actionは0。既存S49のprobeを0件と主張しているのではない。
`host-preflight.json`は別のhost JSON自己整合性判定であり、独立原本監査とは別。
保存S7はNode bridge stdout JSONL、Paperは既存sole collectorのUTF-8 log。
独立Minecraft TCPや外部物理認証ではない。

Node68946 / Java68836 **exit0**。所有lshw子PIDも消滅。
World `/tmp/relay-self-s49-vxpezbn0` 削除、port25565再bind PASS。
元原本を変更せずH6/H7/H8 CLIは当該WorldのUUID/native seq/SHAを照合した。
H5原本の既定読戻しも維持。

## Offline検証の初回失敗

最初の広い回帰：540 PASS / 12 FAIL（通常PATHにNodeとjavacなし）。
Node22を指定した再検証：7 PASS / 5 FAIL（system Java21はJREのみ）。
既存isolated JDK21.0.12.1 compilerも明示した再検証：12 PASS / 0 FAIL。
コード不具合を隠す削除・SKIP・緩和なし。これらは不活性process fixtureであり
Minecraft Worldではない。初回の存在しないglob指定によるpytest exit4も記録。

## H9に向けた限定条件

最初の独立World比較候補は、既に元S42 ownerがAction前に提供できる
**native敵距離2.0m対3.5m**の1軸。両方とも元L0の4m閾値内に置き、
L0/Executorを変えず、既存server側stimulusの距離だけを次実験で事前固定する。
新しい値は必ず当該Worldの元probeから確認し、指定値を実測値とみなさない。
CHEAPは同一元distanceの連続値/事前固定3m flagを用い、sampled motionとの
観測比較だけを行う。距離はGoal/obstacleではなくnative DEV cueである。

各Worldにfresh宣言・UUIDを持たせ、DEV provisional training候補とheldoutを
World単位で分離する。full BCG条件、独立Goal、実効clearが不足する限り
正式trainingは0のまま。H9のWorldは今回起動していない。

## H8実行後の読戻し表示修正

H7比較出力に残っていた歴史的な`H5`というsource-ceiling名を
World共通の`DEV_ARCHIVED_PRE_ACTION_NATIVE_NOT_GOAL_OR_P1_M`へ変更。
CLI positional引数名も`evidence_root`へ統一した。判定条件や原本は変更せず、
初回readback JSONを保持し、`*-final-readback.json`へ再読戻しを保存した。
実行HEADと報告HEADは区別する。これによる追加Worldは0。

## 最終ローカル検証

World後focused **100 PASS**、広いS49/S16/S50等回帰 **553 PASS**。
その収集中に追加した実H8原本回帰を含むH8単体 **19 PASS**、
S16 Outcome回帰 **17 PASS**。重複する検証件数をWorld数や独立経験数へ加算しない。
Ruff / compileall / repository contracts / diff-check PASS。
実行HEADの関連CI全件SUCCESS（専用54 PASS、L-BCG full196 PASS）。
報告commitの最終CIはGitHubのexact HEAD付き報告で別途読戻す。
