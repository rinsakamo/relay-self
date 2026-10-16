# V7 / #619 — M0.2 Paper 生理コストの分解可能性（prospective / NOT_RUN）

**Authority:** V #619, M #616, S #537, R #575. 既存 V Draft PR #625 にのみ追加。
既存 V2〜V6・V6 48セッション・M0仮想エネルギー台帳・凍結済み証拠を編集しない。

## 出発点と区別

2026-10-15 の**1回限りの R 工学資格**:
[GitHub Actions #38730925452](https://github.com/rinsakamo/relay-self/actions/runs/38730925452)
`M02_RSEE_PAPER_CANDIDATE_ENGINEERING_QUALIFIED`。
公式 Paper 1.21.8 build 60 / Java 21、BASAL 候補 0.001 exhaustion/実World tick、WALK 候補 0.01 exhaustion/実移動ブロック、S50 MOVE、S51 EAT、初期 `level.dat` 原本、native STOP、PID・ポートを実証した。
**これは機構の工学的成立であり、係数の生態学的妥当性、介入の因果効果、学習・知能の利益を実証していない。**
原証拠 [#11970775361](https://github.com/rinsakamo/relay-self/actions/runs/38730925452/artifacts/11970775361)、2027-01-13まで。
この証拠の再ラベルや S/R の既消費許可再利用は禁止。

## V7 が扱う問い

代謝の **BASAL tick課金** と **WALK 経路課金** は、同一World tick数・同一の物理移動経路下で、ログ原証拠から互いに独立して識別できるか。

*これは「係数が適切か」ではなく、「係数の寄与を識別できる測定系か」の問い。*
特にデフォルト値で200 tickの基礎代謝は0.2 exhaustion、1.28 blockの歩行は約0.0128 exhaustion。**歩行信号は基礎代謝より小さい**。加算後の残存 exhaustion や空腹ゲージだけでは、閾値とsaturation消費で両者を分離できない。

主要評価量は Paper のオリジナル原ログに現れる *課金分解*:
- BASAL：実際の Paper World tickごとの増分と各累積計数
- WALK：非teleport `PlayerMoveEvent` による実経路（cmではなく1 block = 1 m）と請求量
- WALK native event：別の移動距離計として扱わず、元イベント分の置換0を確認

`requested_max_step_blocks=1` は行動の**目安**であり、actual packet path=1.0の保証ではない。

## 前向き介入（5条件 × 4独立開始）

| 条件 | BASAL倍率 | WALK倍率 | 役割 |
|---|---:|---:|---|
| BASE_ON | 1 | 1 | 基準 |
| SHAM_ON | 1 | 1 | 同じ設定手順を経た無操作対照 |
| BASAL_ZERO | 0 | 1 | 基礎代謝のみノックダウン |
| WALK_ZERO | 1 | 0 | 歩行課金のみノックダウン |
| BOTH_ZERO | 0 | 0 | 交互作用／残余課金の検査 |

**全条件の標準値は固定**（BASAL 0.001/tick、WALK 0.01/block）、追加値0、`enabled=true`。
変更してよいのは当該二倍率のみ。残り14種の理由・行動実装・COGNITION OFFは不変。
設定変更版の SHA256 が既資格プロフィールと変わるため、**#38730925452 の工学資格が変更条件へ自動伝播することはない**。SのDEVで検証後、独立Rが条件別World/設定/プロセス原証拠を審査する。

指定World seedは61021〜61024。各seedの5条件は独立World 5開始・同じ初期条件、200実World tick、移動 nominal 1ブロック・actual path 0.5〜2 blockと条件間差0.005 block以内、初期food20／saturation5。食料の投入、空腹エフェクト、被ダメージは測定期は禁止。
**4 seed × 5条件 = 20 sessionは実行可能性の下限で、統計的検出力の根拠ではない。**

## 対照と判定

世界時刻は**サーバーWorld tick**で測る。ホスト秒、M0台帳tick、Minecraft nativeの空腹値は代用しない。
片方の課金をOFFにしても、違う物理歩行経路や違うWorld tick数になったら**比較不能**として全試行を保存し、都合のいい再試行・選別をしない。

各seedに対して必ず次を分けて報告する:
1. `BASE_ON - SHAM_ON`：課金差0が期待される偽介入対照
2. `BASE_ON - BASAL_ZERO`：独立したBASAL課金の寄与
3. `BASE_ON - WALK_ZERO`：独立したWALK課金の寄与
4. `BASE_ON - BASAL_ZERO - WALK_ZERO + BOTH_ZERO`：加法性・交互作用の診断

原ログの累積課金・同一World tick・経路を独立照合できて**初めて**因果的な機構評価候補。
SがレシートでPASSと書くだけ、SHA文字列だけ、端数が変わった空腹ゲージだけではVは認定しない。
異なる移動量の場合は比率補正だけで再成功としない。失敗、死亡、timeout、欠損も全20スロットの予定と結果を保存する。

主判定は**物理課金機構の識別性**に限定。飢餓からの生存率、習慣、L1/L2学習利益、理想的代謝係数、進化的fitness、production は扱わない。
生態係数校正にはさらにWorldの長期生存・餌機会・移動量・飢餓と回復・安価な行動政策との比較が必要で、その設計はV7とは別。Vの既存 V6 48科学試行は0/48を維持。

## 実装と実行ゲート

新規 `experiments/validation/v7_m02_physics_manifest.json` は上記候補・対照・上限・既資格R証拠を凍結する**新しい**事前登録。
`v7_m02_physics.py` は20本の**合成記録だけ**を受理し、BASAL/WALK/shamと交互作用の数学的整合・負対照・実Worldへの不正昇格を検査する。
`tests/test_validation_v7_m02_physics.py` で異なるseed・欠損アーム・偽World時刻・再使用nonce・native二重課金・不正SCIENCE宣言を拒否する。

```sh
PYTHONPATH=src:tests:. python -m pytest -q tests/test_validation_v7_m02_physics.py
PYTHONPATH=src:tests:. python -m experiments.validation.v7_m02_physics
```

このコードは**M/S/R実装を編集しない、JAR/World/Node/GPU/LLMを起動しない**。
現状：`S_PAIRED_PAPER_RUNNER_NOT_IMPLEMENTED`、`R_ARM_PREQUALIFICATION_NOT_RUN`、`V7_SCIENCE_0_20`、`ECOLOGICAL_CALIBRATION_NO_GO`、`PRODUCTION_NO_GO`。
**SCIENCEの20物理試行を始めるには、S/R各条件の原証拠資格と、新規で明示的なSCIENCE開始許可を別途要する。**

## 失敗時と今後の分岐

基礎代謝と歩行を出力・原ログで区別できなければ、**測定器を改善するDEV**に戻る。成功しても候補係数0.001/0.01は「良い」値にはならない。
V8以降で、エネルギー消費の差がWorld環境・食料・移動・生存に与える実利益を、無操作や安価な政策との比較で検証する。認知機構への帰属はさらに別の対照が必要。


## 2026-10-16 追補 — 実移動距離あたりのWALK課金と条件間比較の分離

**この追補は凍結済みV7事前登録・既存20 SCIENCEスロットを遡及変更しない。** 2026-10-16のseed61021／5つの独立DEV Worldと、Rによる固定原証拠5/5の独立レビューに対し、測定上の異なる2つの問いを分離する。

1. **WALK課金実装の整合性（個別試行）**：実ネイティブ移動イベントから測った正の水平経路長 `d_actual` と独立に抽出したWALK課金 `C_WALK` から `r=C_WALK/d_actual` を計算。追加値0の設定について、WALK倍率1では0.01 exhaustion/block、倍率0では0を期待する。**条件間の経路距離が等しい必要はない**。経路長が0・不明・欠損、課金の出典がない、他理由との混合・二重課金がある場合は係数を測定できない。原証拠ごとの実測値と設定整合性を報告するだけで、物理的係数の生態妥当性や独立qualificationは認定しない。
2. **凍結済みV7の5条件対応比較**：もとの事前登録は同一seed/World時間および各条件間の実経路差0.005ブロック以下を要求。履歴5 DEV試行の経路差0.24380101042250235は不適合のまま保存し、`BASE_ON–SHAM_ON` 等の総消費量差から介入因果効果を推定しない。比率が一致したことを、過去の対応比較を再入場させる理由にしない。

Vの `v7_m02_seed61021_dev.py` はR独立レビュー済み原観測値から各条件の `observed_walk_exhaustion_per_block` を併記するが、原本を再認証する別実行器ではない。`walk_rate_source_accounting=CONSISTENT_R_REVIEWED_DEV_ONLY` と、`paired_paths_eligible=false` / `causal_comparisons_allowed=false` を同時に記録する。Rの工学資格、BASAL直接write課金、正確な200 tick実験区間は別の未達ゲート。

ランダム地形の障害物・移動不能・迂回・歩行距離差は将来の生態・行動研究では実際のWorld結果であり、単純に不合格として消すべきではない。そちらを扱う場合は、**試行開始前**に自然World・初期座標/姿勢/地形・食料・World時間・打ち切り規則・複数seedの対照と評価法を定めて新規登録する。障害物の存在を今回の経路差の原因と断定しない。

V7 SCIENCE=0/20、V6 SCIENCE=0/48。基礎代謝BASALはsource-side書き込み量と累積値が未計測、changed profile工学資格NOT_RUN、G3/production NO_GOのまま。
