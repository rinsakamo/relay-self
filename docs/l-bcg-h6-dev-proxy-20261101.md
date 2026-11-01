# L-BCG H6 — 実H5経験の DEV-only proxy 読戻し

2026-11-01。Draft PR #656、Learning owner Issue #431。H5実Minecraft原本を使用。
このreadback自体はWorld／Action／Model呼出しを一切行わない。

## 今回の実装

- `src/relay_self/l_bcg_dev_proxy.py`：H5原本 `s49-report.json`,
  `independent-audit.json`, 元S16, 元S7 **pre-next-L0 prefix**,
  元Paper `server.log` の**既存バイト列**を読むread-only分離器。
  監査manifest SHA256、S16 Action/seq、S7 pre/action/next、
  source session/Paper World ID、provisional S50 tickとhost L-BCG DEFERを照合。
  S7の元Action直前のfoodとS42 threat距離を採用し、
  **次epochのS42距離と別のsourceタイミング**に保持する。
- `DevProxyEpisode`：1World→1件だけ。入力OFF**報告**中Paper変位の
  単なるサンプル合計と、参照元のdigest・World/sessionを保持する。
  保存値が観測されたことと入力の実効clearは別。
  `physical_effective_clear_attested=False`、
  `physical_training_eligible=False`、
  `goal_attested=False`。
  `MotorOutcome`や`MotorSourceAdmission`を一切生成しない。
- `summarize_h6_provisional_worlds`：
  別World/sessionとsession-scope Actionを有界に照合し、安価な
  `latest`／`any`の**観測フラグ**を算出する。
  学習済みL1判断・Action候補ではなく、
  `learned_l1_attention=DEFER_UNKNOWN`、
  `admitted_training_worlds=0`を固定。
- `tools/l_bcg_h6_readback.py`：
  `PYTHONPATH=src:. python tools/l_bcg_h6_readback.py docs/evidence/l-bcg-h5-20261101`
  で読み出し専用のDEV proxy結果をJSON出力。
  ファイル書換え・追加native probe・Minecraft起動なし。

## H5から読み取れる数値の意味

H5の元Actionは`s49-native-move-20`、元S16 before/after seq
23/30、元L0の次native probeは56。Action**前**の元S42敵距離
2.0m、Minecraft food 20が原nativeから読める（Goalまでの距離やMエネルギーではない）。
Paper tick252–259 の8 samples中、`last_reported_input_active=false`
の最初の3 tickで観測変位あり（合計約0.0642466m）。
これは**reported-input-OFF中のsampled motion**であり、
`PHYSICAL_POST_CLEAR_VERIFIED`とは異なる。H5で有資格trainingは0。
World sample=1であり、8 tickを8 Worldにしない。

- source digestの整合性は外部TCPやPaper物理受理を証明しない。
- H5監査のGoalは`UNDETERMINED`、有効clear tickは`NOT_ATTESTED`。
- 暫定変位ラベルの真偽と、未来の行動改善は別問題。
  `cheap_any_world_motion` がSAMPLED_MOTIONでもL1の有用な行動は未証明。
- 前Actionの特徴と次のepochの特徴を混ぜて条件学習ラベルを作らない。
  H6の現在は全条件が揃っておらず、**条件付き学習候補そのものはDEFER**。

## H6 DEV後続計画と境界

既存S/R owner側でWorldごとの**事前固定された操作条件**（独立なGoal、
選択gait、P1/M owner状態、障害物条件）とAction前のnative観測の
同時刻sourceを明確化する。最初はownerの型・source確認だけ、
既存S49 Action issuerやL0 safetyには接続しない。
複数WorldのDEV proxyを先に収集してcheap比較は可能だが、
これだけで正式L-BCG学習器の`MotorOutcome`へ入れない。

formal trainingへの移行には、独立に認証された入力実効clearからの
post-clear物理区間、別原Goalの判定、source revisionと
訓練／heldout Worldの分離が必要。前段と正式学習の違いを常時表示する。

**H6 offline proxy extraction / H5 real World source reused /
H6 new real World 0 / Action 0 / qualified training 0 /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
