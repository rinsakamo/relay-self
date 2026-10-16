# V8 M0.2 — R五条件資格完了後の候補入場ゲート（2026-10-17）

**Authority:** V #619、既存Draft #625、S #537/#545、R #575/#610、M #616、S50 #627。これはV8の**候補設計・オフラインの形状検査**に限定する。事前登録の最終承認、科学的検出力、実験開始許可ではない。既存V2–V7、原証拠、凍結済みV7 matched-path 0.005 block、消費済grantを変更しない。

## 入力と測定境界

Rは2026-10-17に BASE_ON（前回独立資格）＋残る4アーム（各1独立World・Java/Nodeセッション）の**5/5工学資格**を確認した。今回追加の4アームはS [実機 run 38922286471](https://github.com/rinsakamo/relay-self/actions/runs/38922286471)、R [独立再読査 38923706459](https://github.com/rinsakamo/relay-self/actions/runs/38923706459) に保存。R原報告: [独立資格](https://github.com/rinsakamo/relay-self/blob/infra/rsee-r6-s9-native-original-readback-20261012/docs/rsee-m02-v7-four-arm-physical-qualification-20261017.md)。一度限りの4件の資格grantはすべて**CONSUMED**、過去のBASE_ON grantもCONSUMED。Vは**Rの報告を受領**するが、今回のPythonコードはZIPを独立に取得・ハッシュ検証するR監査器ではない。

| 条件 | source-observed tick-chord距離下限 | 最初の200 tick BASAL入力 | WALK setter入力 |
| --- | ---: | ---: | ---: |
| SHAM_ON | 1.9389928412050272 | 0.2 | 0.019389928412050277 |
| BASAL_ZERO | 1.7231471919306607 | 0 | 0.01723147191930661 |
| WALK_ZERO | 1.9389928412050272 | 0.2 | 0 |
| BOTH_ZERO | 1.9389928412050272 | 0 | 0 |

4件間の最大差は**0.2158456492743665 block**。これは連続sub-tickの真の経路積分ではない。V7の旧0.005 block対応条件は依然**FAIL**であり、source-side exhaustion書込は食料・saturation・healthの下流差、適応利益、生態的fitnessを認証しない。BASE_ONは別runで認証済みだが、上表の**4条件の計算にBASE_ONを無理に混入しない**。V7科学試行0/20、V6科学試行0/48、G3/production NO_GO。

## 今回の実装

- `experiments/validation/v8_m02_admission_bridge.py`：8種の**候補**seed 62101–62108 × 5条件 = **40仮スロット**を生成。seed内の順序はSHA256に基づく決定的な**仮割付**であり、正式な盲検割付・ランダム化実験でも科学的grantでもない。すべて `NOT_RUN`、World UUID/原出典/SCIENCE grantを空に固定する。
- 同モジュールはRが独立に報告した4件の識別子・source write値・相異なるarchive/grantを**オフラインに形状照合**する。値を1つでも変えた場合は拒否。これは報告文字列の受領・照合であり、R原証拠の再認証でも5件目BASE_ONの再評価でもない。
- `tests/test_validation_v8_m02_admission_bridge.py`：欠損・重複スロット、seed入替、済grant流用、偽SHA・World識別子・SCIENCE昇格、改変R測定・原ZIP IDやgrant aliasを負対照で拒否。

CLI:
```sh
PYTHONPATH=src:tests:. python -m pytest -q tests/test_validation_v8_m02_admission_bridge.py
PYTHONPATH=src:tests:. python -m experiments.validation.v8_m02_admission_bridge
```

## 今後の必須順序（全て未達）

1. **S DEV feasibility**：同一seedだけでなく、chunk/regionと食料状態を含むWorld clone原本、物理native初期XYZ/yaw/pitch・server full tick一致、L0同一ポリシー、有限の食料機会、難易度・生態的測定時間を明示する。ランダム地形の障害物・no-progress・移動距離差は**結果**でありV7のように距離一致で結果を選別しない。
2. **R fresh source qualification**：今後の実験用に変わるJAR・config・native World・Action/OUTCOME・STOP・ホスト終了証拠について、別の実機原本を独立監査する。現行5/5工学資格は当該履歴ソースの範囲だけであり、P1 WAIT新JARや今後のV8 profileには自動的に継承しない。
3. **V最終前向き事前登録**：研究仮説を **World内の生存・食料獲得への代謝係数の因果影響**に限定し、主要評価量を1つ指定、残りを副次に固定。自然World seedごと5アーム割付、独立反復数・power/precisionの根拠、死亡とhost failureの区別、全試行保存、停止則、BASAL/WALKの交互作用、shamとの差、初期Worldのコンタミ対照を事前に決める。8×5=40は仮値であり検出力の根拠ではない。
4. **V SCIENCE**：上記を満たして初めて別の明示的許可・未使用grantを求める。Sの新runnerとRの原本監査が揃う前に試行を実行しない。DEV/QUALIFICATION試行をscience slotに充当しない。

認知的必要性・L1/L2の優位性はV8では測定しない。P1肉体疲労は独立：真正の物理WAIT tickのみ回復し、blocked MOVEはWAITではない。Lの認知疲労も別の試験・原出典を要する。Vは #628 の「異常行動→World/エネルギーのチートを優先監査」にも従い、仕様上のフリーランチと安価な機構の正当な効率差を混同しない。

**判定：`V8_CANDIDATE_ROSTER_ONLY_SCIENCE_NOT_ADMITTED`。実World実行0、新科学grant 0、科学試行0、production NO_GO。**
