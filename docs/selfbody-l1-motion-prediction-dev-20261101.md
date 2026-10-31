# SelfBody / L1-MP1 — 二つの実World原本監査報告を用いた自己教師あり変位予測（#653）

2026-11-01。**DEV offline archival readback / no new World**。Spec: [Issue #653 L1-MP1 comment](https://github.com/rinsakamo/relay-self/issues/653#issuecomment-6545345807)。Parent PR #654 exact `731737e4a9d12574a9e03826f5e4bcf37ae4e880`。

## 重複・保護

L #426 / L2 PR #603（PRD outcome comparison）/ L6–L8 PR #638（next S epoch L1 shadow）、AC-B #431 / B23 #543 / B25 #552（経験・Habit・cheap parity）は既存の独立owner。ここでL10、PersistentCognition Memory、S10/S11、S49/L0、S16/S50原本コードは変更しない。#537 Sが今後の実World実行owner。Goal/source-true rewardとは無関係の**次のPaper変位の数値予測**だけを取り扱う。

## 固定した二World分割（回顧的）

| 用途 | 保存元 | session | World UUID | sampled 変位列（m） |
| --- | --- | --- | --- | --- |
| **Primary train** | #652 → Issue #651 run1 original-audit JSON | `15f04c47-1a80-4705-99e1-ebedb963e3a3` | `21c20dbf-0f44-4207-b557-b4a3e2764979` | `0.0494921883, 0.0095436049, 0.0052108083, 0,0,0,0,0` |
| **Primary heldout** | #654 → Issue #653 run1 original-audit JSON | `3da31d96-95bf-49db-ac5e-5fabe8f35b38` | `0dcf8a5d-b8da-4863-bc0d-641d0abc1260` | `0.0516839041, 0.0099662346, 0.0054415641, 0,0,0,0,0` |

各8件は **Paper callback sampled displacement**。完全な入力OFF期間でも、S15実効clearでも、身体安定の認証でもない。両Worldの構成は非常に近い。時間／位置／速度の世界間同一性を仮定しない。既存independent audit JSONは保持されたoriginal digestを記述するが、このツールがoriginal log bytesを再読・再認証したわけではない。

## 数値予測（実World source ownerへの読取り追加なし）

入力: trainの変位列 `x[0:8]`。最小二乗 `c = sum(x[t]*x[t+1])/sum(x[t]^2)`（t=0..6）。heldoutの各 `x[t]` から `x[t+1]` を予測し、次点の観測値は**採点時のみ**参照する。同Worldに固有な学習済み係数の保存や本番のL1 policy書込みは行わない。

**比較:** memory OFF `0`、`LAST_VALUE`、train側の `TRAIN_MEAN`、L1-labelled linear、**同一入力・同じ線形式のcheap linear**。後二者は厳密一致であるため、改善があっても`CHEAP_LINEAR_EQUIVALENT`。指標は7対のMAE/RMSE (m)。

### 予備再計算値（Primary; exact-head CIは別途実行）

| Arm | MAE (m) | RMSE (m) |
| --- | ---: | ---: |
| memory OFF / zero | 0.0022011141 | 0.0042917937 |
| LAST_VALUE | 0.0073834149 | 0.0159930664 |
| TRAIN_MEAN | 0.0031044455 | 0.0036855532 |
| L1-labelled 1-param linear | **0.0007233844** | **0.0013722649** |
| CHEAP_LINEAR (identical) | **0.0007233844** | **0.0013722649** |

fit `c≈0.2033188579`。逆方向（感度確認のみ）MAE `≈0.0006927085`、zero `≈0.0021077733`、cheap linear一致。**8 sampled tickのうち5が零で、World二つだけ。** 誤差改善の統計的・科学的強さを主張しない。単純な慣性減衰曲線に線形回帰したに過ぎない。

## 実行・検証

```bash
export PYTHONPATH=src:tests:.
python tools/selfbody_l1_motion_prediction_replay.py
python -m pytest -o addopts='' -q tests/test_self_body_s50_l1_motion_prediction.py
python tools/check_repository.py
```

- 既存audit JSONをsource-labelled replayへ変換する際、同一session/World混入・SHA形式・World tick連続・有限非負距離・8件・provisional・NOT_ATTESTED ceilingを検証。元JSONから独立のPaper/Node authenticationはできないので `ARCHIVAL_READBACK_REPLAY_NOT_REAUTHENTICATED` を明示する。
- 事前にtrainを固定し、heldout未来値をfittingに渡さない。負対照は偽Goal、偽L10/P1、偽final source、長さ・時刻・値・source/subject混入を拒否。
- 既存native試験の再実行、実World、資格/科学、S49/L0介入は今回なし。CIが成功しても物理実装成功とは呼ばない。

## 次に必要な実World DEV

#537の既存launcher/grantが新規試験まで含むことを**実行前に確認**する。新しい使い捨てWorldで、過去Worldで凍結した `MotionForecast` を元の受信済みnative/S50位置観測**より先に**read-only生成してdigestを保存し、その後の実際に到着したsampled WorldTickで誤差を採点。必要ならoff／cheap／linearを同じWorld観測上でpairedに比較。追加probe・Action issuer・L0 policy変更・S10更新禁止。元Java/Node/Paper original、clean shutdown・source監査、実行HEAD/grant、失敗原本を保存。

**完了分類の上限:** `DEV_OFFLINE_ARCHIVAL_TWO_WORLD_HELDOUT_REPLAY_ONLY / CHEAP_LINEAR_EQUIVALENT / GOAL_UNDETERMINED / NO_L10 / NO_S10_S11 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。未確認の次Worldの実測を捏造しない。
