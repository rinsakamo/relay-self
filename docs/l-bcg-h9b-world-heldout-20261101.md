# L-BCG H9b — 事前固定8 World・FIT4→EVAL4 DEV代理運動予測

2026-11-01。Learning owner #431 / Draft PR #656 / S49 #537。

## 目的と既知の上限

H9a実Worldは元native S42 enemy 2.0m/3.5mの条件識別に成功。
2 WorldではL0はどちらもMOVE_AWAYで、reported-input-OFF中の
Paper sampled displacementは0.0670917m/0.0642466m。
H9aの**事前固定raw SHA一致pair**はserver.properties
生成日時コメント差のためREJECTED。以後もH9a原判定はREJECTED。
事後timestamp解析のPASSは旧判定を変更していない。

H9bは**新規独立8 World**だけで、「同じS42値を使い、
過去のDEV運動量代理指標から将来の代理指標を予測する」
試験の工学的成立可否を評価する。正式L1学習・記憶・Action提案ではない。

重要：この予測の結果指標は
`DEV_REPORTED_INPUT_OFF_SAMPLED_DISPLACEMENT_M` であり、
Paper input effective clearの物理認証でもGoal達成でもない。
条件付き予測の外部一般化と、運動制御の改善を証明しない。

## 実験の事前固定（World開始前に確定）

- branch: `dev/l-bcg-conditional-motion-shadow-20261101`
- protocol schema: `L_BCG_H9B_DEV_S42_WORLD_HOLDOUT_V1`
- World数: 8（**新規**, H5/H8/H9aのWorldは不使用）
- 2.0m A群4 World、3.5m B群4 World。
- 先にDEV fit各群2 World、後からDEV eval各群2 World。
  「DEV fit/eval」はデータ分割名であり、
  **有資格formal train/heldout Worldを意味しない**。
- 必須実行順：
  `A-F1 → B-F1 → B-F2 → A-F2 → B-E1 → A-E1 → A-E2 → B-E2`。
- CHEAP閾値は**3.0m未満**、元L0の4m閾値・sole S49 Executor不変更。
- 各World元S49 Action最大1、追加native probe0、追加BCG Action0、
  model/provider calls0、Learning/S10/S11/Memory更新0、retry0。
  0 Actionや途中FAILは試験成立と扱わず原本保存、無断再試行不可。
- native sourceの実測A 2.0±0.15m、B 3.5±0.15m、
  L0 `WAIT → MOVE_AWAY → WAIT`は元S49原本から独立照合。
- World/session/Paper UUID/report原本SHAとpre-Action sourceは
  8 World**全部異なる**。同じ実行HEAD、Paper jar、plugin jar、
  plugin config raw SHAを要求。

### H9b固有の事前宣言された設定等価性

H9aの旧raw SHAゲートは変更しない。

H9bでは**World1起動前に別基準**として次を固定する：

1. `server.properties` raw bytesはWorldごとにそのまま保存し、
   `original-sha256.json`と`runtime-assets-sha256.json`
   の各raw SHAと毎World厳密照合。
2. A/B間でそれらのraw SHAが同一ならbyte一致とする。
3. raw SHAが異なる場合は**生成日時の2行目だけ**
   `#Sun Nov 01 HH:MM:SS JST 2026`等の厳密形式で相違を許す。
   1行目・3行目以降は改行、コメント、空白、順序、重複、
   escapeを含め**全バイト一致**させる。
4. `minecraft.jar`、Paper plugin jar、
   `RelayMetabolismDev/config.yml`はraw SHA完全一致。
5. 条件差異はWorld内の近距離ゾンビの**召喚距離だけ**。
   preAction S42 native実測が予定水準に達していることを監査。

これはH9aの過去のpair REJECTEDを事後PASSにする口実ではない。
保存済みH9aをH9b fit/evalに混ぜることは禁止。

## フリーズ境界（結果を見る前に行う）

まずCI成功／runtime SHAとWorld占有状況確認。
executable exact HEADを固定後、World開始前に以下を実行：

```bash
PYTHONPATH=src:tests:. python tools/l_bcg_h9b_make_plan.py \
  --executor-head "<40桁のH9b実行コードHEAD>" \
  --output "/home/rinsa/work/l-bcg-h9b-evidence-20261101/protocol.json"
sha256sum "/home/rinsa/work/l-bcg-h9b-evidence-20261101/protocol.json"
```

出力はexclusive保存。後からplanを書き換えず、
全Worldの`predeclared.json` と
`WORLD_ATTEMPT_STARTED.json` からそのraw SHAへ参照させる。

1 Worldごとの前宣言は旧`L_BCG_H9A_ARM_PREREG_V1`の全必要項目
に加え、追加の`h9b`キー：

```json
{
  "slot_id": "A-F1",
  "role": "dev_fit",
  "plan_sha256": "<protocol.json raw SHA256>",
  "frozen_model_sha256": null
}
```

eval Worldではroleを`dev_eval`として
`frozen_model_sha256`に保存済み係数原本のSHAを指定。
`WORLD_ATTEMPT_STARTED.json`へ
`h9b_slot_id`/`h9b_plan_sha256`/
`h9b_prereg_sha256`/`h9b_frozen_model_sha256`を、
**実際のWorld開始前**に保存する。既存launcher markerの
`max_worlds=1,retry=0,launcher_entered_utc`を保存し、
Worldの実行順も独立して確認する。

先に`A-F1,B-F1,B-F2,A-F2` を各1回実行し、
全WorldでH8独立監査＋H9a native/副作用/source監査を完了させる。
次のfreeze CLIは**4件のDEV fit代理変位だけ**を読む：

```bash
PYTHONPATH=src:tests:. python tools/l_bcg_h9b_dev_holdout.py \
  /home/rinsa/work/l-bcg-h9b-evidence-20261101/protocol.json \
  /home/rinsa/work/l-bcg-h9b-evidence-20261101/worlds \
  --freeze \
  --output /home/rinsa/work/l-bcg-h9b-evidence-20261101/frozen-model.json
sha256sum /home/rinsa/work/l-bcg-h9b-evidence-20261101/frozen-model.json
```

保存後、**係数、CHEAP閾値、損失関数を変更不可**。
`B-E1,A-E1,A-E2,B-E2`の4 Worldは開始前に
そのモデルSHAをpredeclared+markerへ結合する。

8 Worldが成立した場合だけ：

```bash
PYTHONPATH=src:tests:. python tools/l_bcg_h9b_dev_holdout.py \
  /home/rinsa/work/l-bcg-h9b-evidence-20261101/protocol.json \
  /home/rinsa/work/l-bcg-h9b-evidence-20261101/worlds \
  --evaluate \
  --frozen-original /home/rinsa/work/l-bcg-h9b-evidence-20261101/frozen-model.json \
  --output /home/rinsa/work/l-bcg-h9b-evidence-20261101/eval-result.json
```

## 比較対象（同一元S42情報と代理変位）

**FIT4のみから予測係数を作り、EVAL4でMAE比較**：

- CHEAP global mean：条件無視、FIT4平均変位。
- CHEAP threshold3m：FIT4の元S42<3m群と>=3m群の平均変位。
- DEV L1 proxy candidate：FIT各群の`(S42距離平均,代理変位平均)`
  2点を結ぶ一次関数（線形補間／外挿）。
  **条件付き数値予測**であって型付きL1や学習済みAction提案ではない。

二水準の距離だけなら「線形L1候補」は
「閾値CHEAP群平均」と多くの場合で**同値**。
この設計は、条件を使っただけで知性や経験学習の優位性を
捏造しないため意図的に厳しくしてある。

比較器は固定MAEを計算し、
`EQUIVALENT_WITHIN_1E-9_M`、
`DEV_CANDIDATE_LOWER_MAE_NO_CAUSAL_CLAIM`、
`CHEAP_THRESHOLD_LOWER_MAE`を出す。
結果にかかわらず、元L0を変更せず
`learned_l1_attention=DEFER_UNKNOWN`、formal training0。

## スコープ・資格

このGitHub作業は**H9b新World0**。実WorldはLocalCodexで
継続grant [#431](https://github.com/rinsakamo/relay-self/issues/431#issuecomment-6552384315)
の下、各World別宣言・原本監査・cleanup・通常push／Issue読戻しを伴って行う。
複数Worldを1回の実Worldと数えない。予告なし再試行や、H9a失敗原本の
差し替えは禁止。

認証済みGoal、P1/M0/gait/obstacle、World source revision、
物理effective clearは引き続き不明。
**QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**、
`GOAL_UNDETERMINED / EFFECTIVE_CLEAR_NOT_ATTESTED /
QUALIFIED_TRAINING_WORLDS=0`を維持。

最終分類（準備段階）：
`H9B_OFFLINE_WORLD_HELDOUT_PROTOCOL_PREPARED /
DEV_WORLD_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。
