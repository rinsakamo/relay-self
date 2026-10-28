# RelaySelf S49 — L0観測フィードバック入力調整 DEV

2026-10-28. **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

## 開発方針

Minecraftの入力ラグ、PaperとNode物理tickの位相揺らぎ、Mineflayer入力受付時刻の差はWorld固有の環境条件として許容する。通常行動制御に「Node/Paper厳密同期tick一致」を必須としない。通常DEV同期traceを強制ONにしない（既存T1o trace既定OFF成果を維持）。

今回の最小実装は従来の本物の`NormalWorldL0`・`NormalSessionActionExecutor`・S14/S15/S16を維持し、S49の*1回目*の本物の`WorldConsequence`をL0側から読み出し、*2回目*の独立許可済みActionの入力保持時間だけを変更する。新しいAction issuer、packet reader、M0/P1投稿者は作らない。

- S49最初のAction：元の約0.60秒。独立S15 ACK → CLEAR ACK → S16 OUTCOME、実World XZ移動距離を得る。
- S49 2回目のL0選択・独立S14承認時に、前の閉じた本物S16から平均速度（移動距離/0.60秒）を計算する。これは物理tickの完全同期を仮定しない近似。
- DEVステップ目標1.0mに対して次の入力保持時間を`clamp(1.0m / observed_speed, 0.10s, 0.60s)`で決め、元S15の2回目のコマンドdurationだけ置換する。一般的な絶対座標ナビや行動方向選択とは別であり、本実装は「次の1ステップの量」の校正試験に限定。
- 2回目の危険源が1.5m未満の場合、L0逃走を優先して入力時間は短縮しない。取得済みS16の身元、元session、S14 grant、元Action open count、元のプローブが成立しない場合はfail-closed。
- 2回目の真のS16実移動量と希望ステップとの差を記録する。成功値を補完・捏造しない。過不足を記録するが、自動連続リトライ・障害物回避・個体学習・絶対目標到達は未実装。
- モデル事前値CARRY / WAIT_ASSUMEDは合成仮定のまま。P1回復の資格やL0物理能力の学術証明に昇格させない。

## コード

- `adapters/mineflayer/s49_l0_observed_step_dev.py`: S16検証・危険優先・bounded次ステップduration。
- `adapters/mineflayer/normal_action.py`: 同じ元S49 sole executorに限り2番目の発行済みDEV Actionのdurationを`dataclasses.replace`、次のS15へ渡す。新しい権限なし。
- `adapters/mineflayer/s49_normal_session_real_ci.py`: 同じL0 ownerの事前に閉じたS16に限定し、次の入力調整とS16結果をdev reportに記録。
- `adapters/mineflayer/s49_paper_forward_dash_dev.py`: CLI `--l0-observed-next-step-m-dev 1.0`、DEV opt-in環境変数。
- `adapters/mineflayer/s49_l0_observed_step_review_dev.py`: 4独立WorldのFIXED/FEEDBACK対照、S16 original typed evidence、Paper 7本連続ブースト・同じL0 Action所有者を照合。
- `tests/test_s49_l0_observed_step_dev.py`: 範囲上限/下限、危険時優先、偽S16拒否のFocused Python3.12。
- `.github/workflows/self-l0-s16-feedback-dev.yml`: Python3.12/Node22/Java21、紙Paper SHAの再読・4つの使い捨てWorld、original結果保存。

## 実機DEV事前登録

4 World: `FIXED_CARRY`, `FEEDBACK_CARRY`, `FEEDBACK_WAIT_ASSUMED`, `FIXED_WAIT_ASSUMED`。FIXEDは元の2回目0.60秒入力。FEEDBACKはS16観測から目標1.0mの次ステップdurationを決める。全Worldで同じPaper7 tick cap、同じ属性projection、元のL0とS16を保持。

一次指標は2回目のS16 XZ移動距離と`abs(actual−1.0m)`。判定は負の結果も保持し、World間の位相一致・乱数化・実P1回復を主張しない。1回目は別のゾンビ脅威から2回目に移るので、絶対位置までの到達保証は無く、次ステップの入力校正のみを比較する。

試験はR/SCIENCEでなくDEV disposable Worlds。main・Draft #545/#634を更新せず、QUALIFICATION_NO_GO。実機結果はcompleted exact SHA Actionsとsource artifactを読み戻して追記する。

## 実Minecraft DEV結果（2026-10-28 JST）— SOURCE_VERIFIED PASS

[GitHub Actions #40622805112](https://github.com/rinsakamo/relay-self/actions/runs/40622805112) `completed / SUCCESS`。実行固定HEAD `b537a3142badc239499e7073c75db5f6971d1f34`。事前Python3.12 focusedとRuff PASS、Node22 3 PASS、Java21 Paper pluginビルドPASS、Paper1.21.8 build60 SHA再検証PASS。4独立World（4独立session UUID / World UUID）を実行。元S49 sole owner各2 native S16 OUTCOME、FIRST Paper modifier正7連続tick、FIRST Paper gait13 tick、第二非ブースト入力を確認。追加Action issuer=0、reader=0。

| ケース | 入力制御 | 1回目実S16移動（m） | 2回目入力保持（s） | 2回目実S16移動（m） | 次ステップ1.0mへの絶対誤差（m） |
|---|---|---:|---:|---:|---:|
| CARRY | FIXED | 3.831942780067 | 0.600000 | 3.030157205469 | 2.030157205469 |
| CARRY | FEEDBACK | 4.123096636187 | 0.145521692297 | 0.559301003145 | 0.440698996855 |
| WAIT_ASSUMED | FIXED | 3.985247329119 | 0.600000 | 3.030157205469 | 2.030157205469 |
| WAIT_ASSUMED | FEEDBACK | 4.102717566258 | 0.146244529464 | 0.559301003145 | 0.440698996855 |

独立源監査結果 `S49_L0_S16_OBSERVED_NEXT_INPUT_FOUR_WORLD_DEV_ONLY` と `S49_L0_REAL_OBSERVED_S16_SECOND_INPUT_DEV_PASS`。両仮説で今回の次ステップ絶対誤差がFIXEDより **1.589458208613m小さい**。ただし実移動0.5593mはターゲット1.0mに**未到達**（0.4407m不足）。二つの仮定F値は実際のP1 WAIT回復ではなく、4つは独立World・異なるゾンビイベントを持つので厳密な因果・継続的目標到達を証明しない。

本結果は非同期Worldに対して厳密なtick一致や同期traceを必要とせず、元L0の次Actionが**前回の閉じたS16結果に従って入力を調整し、再度S16で実結果を観測した**というDEV成立を示す。FILE I/O差等を因果説明に使用しない。

Raw artifact: `s49-l0-s16-feedback-four-worlds-40622805112-1`、ID **12788680348**、ZIP SHA256 `231e82c124bcc0a4b2fb30a0bf0bac67f84309a05f455fb03d892ade60c139d8`。

次段階（本DEVでは未実装）：2回目の未到達量を受けて次ステップを再調整する連続L0制御、停止閾値・微移動WALK・障害物/逆進/危険割込み・過補正抑制。単純に0.6秒で移動量を割った平均速度はMinecraft加速・慣性を考慮していないため、精度向上には観測履歴または加減速モデルが必要。これらは別のDEV反証試験で検証する。

**DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。本番権限およびPaper/Node同期tick一致を主張しない。main、Draft PR #545/#634を更新しない。
