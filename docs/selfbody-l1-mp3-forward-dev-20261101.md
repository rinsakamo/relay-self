# L1-MP3 — readonly S50接続 / WORLD_GRANT_REQUIRED

2026-11-01。基点 PR #655 `9395da907db9f9371ee86b2cea339f2a9ec77235`。
隔離worktree `/home/rinsa/work/relay-self-l1-mp3-20261101`、branch `dev/l1-mp3-forward-20261101`。

## 権限確認の結果

GitHub #537本文、全コメント、#653仕様・最新コメント、Draft #655とローカルHEADを確認。
#537 [6539621176](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6539621176) の継続grantは **S49 × SelfBody × L8 × M統合レーン**に限定。
#653 [6545500226](https://github.com/rinsakamo/relay-self/issues/653#issuecomment-6545500226) は本S50予測レーンへの同一視を明示禁止。
以前の#654 bounded World grantは実行済み。今回に適用する未消費grantは確認できず、ユーザー指示に従い **WORLD_GRANT_REQUIRED / 実World 0回 / Java・Node起動0**。

## 実装と接続境界

`score_live_dev(ticket, training, original_S50LivePaperWindow)` を明示的なarchival→live provisional接続として追加。
MP2の `freeze_for_target(..., capture_mode="PROSPECTIVE_LOCAL_ORDER_NOT_EXTERNALLY_ATTESTED")` と元checksum・対象session/World/Action/subject照合を再利用。
既存MP1 `evaluate_heldout` / MP2 `score_frozen` の異種source拒否を維持し、数値計算だけ共用。
元archival入力をliveと再標識しない。typed objectは真正性の証明でなく、元S50 source ownerの窓生成が必要。

係数 c はtrainingの7隣接対だけで固定。新World x[t] を得たときの予測式は **c*x[t]**。
窓全体を受け取るこのAPI単独では、各予測がx[t+1]観測より前だったとは証明しない。
本段階は**接続契約をオフライン検証**したもので、live hostへの自動接続や前向き運動予測の実World完了ではない。
予測器・比較器は同じ7対でzero/last/training-mean/same-information cheap linearを採点し、cheapと厳密同値のため `CHEAP_EQUIVALENT`。微小差による優位判定を持たない。

S16 OUTCOME・cleanup・観測前固定の証明は独立フィールドでfalse。`LiveDevScore` はMP2更新の入力型ではなく、実OUTCOME未確認の次World用更新を拒否。
L0 policy・S49 issuer・S16・S50 source owner・SelfBody・native reader・元hostは変更0。追加probe/Action/model call、L10/S10/S11更新は0。

## 今回の数値と未実施項目

- 過去World由来固定係数: **0.20331885786720635**。予測値: `0.20331885786720635 * x[t]`（新Worldのx[t]は未観測）。
- 新World/session/Action: 未発行・未binding。固定時刻、Paper原本、S16 OUTCOME、実測値、MAE/RMSE、cleanup: **N/A / NEW_WORLD_NOT_RUN**。
- cheap比較: synthetic typed接続試験で同情報linearと厳密同値。新World比較は未実施。
- 次World用モデル更新: **未更新**。既存MP2の過去2World replay値 slope `0.2033188578672077` / mean `0.0021544437112471304m` は今回の新World更新値ではない。
- 既存archival replayの再現値は従来どおりlinear MAE `0.000723384425636194m` / RMSE `0.0013722649368450835m`。新World結果へ転用しない。

## 検証・残課題

Python3.12 focused FAST（MP1/MP2/MP3 + shadow/route B/live epoch/source）、Ruff、compileall、repository contractsを実行し、既存#655 CIにもMP3を追加。
テストの新session/WorldとS50 typed windowは**synthetic fixture**。実World証拠は0。

適用grant取得後、元hostのAction/World識別確定後かつS50 marker前にticketを原本保存するreadonly hookが必要。
加えてx[t]→予測値の固定→x[t+1]の順序を元callback側で記録し、終了後に元Paper/Node/S16/cleanupを照合してから候補更新する。
別レーンgrantの流用、事後生成ticketで前向き成功を主張すること、元の失敗原本の修正は禁止。

**DEV_OFFLINE_HANDOFF_CONTRACT_ONLY / WORLD_GRANT_REQUIRED / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
