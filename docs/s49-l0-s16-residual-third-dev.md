# RelaySelf S49 — L0 observed S16 residual third Action (DEV)

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## 設計目的

Minecraftの入力受付時間やNode/Paper tick位相は変動するWorldの性質であり、通常のL0入力に厳密同期を要求しない。既存の [S49 2 Action S16 feedback](https://github.com/rinsakamo/relay-self/blob/self/dev-l0-observed-motion-feedback-20261028/docs/s49-l0-observed-motion-feedback-dev.md) は、元0.60sの二度目入力を0.145sに調整し、実移動3.03m→0.5593m、目標次ステップ1.0mの誤差2.030m→0.4407mを示した。

今回はその**二度目のS16実結果**を用い、同じ元S49 L0 ownerが三度目のActionを独立認証・発行し、残り約0.44mの誤差をさらに補正できるか試す。

1. 最初のS49 native MOVE_FORWARD_SPRINT_DEVは従来0.60s。3イベントのゾンビ危険認知に対する通常L0判断・S14認証を維持する。
2. 第二の元S49 Actionは第一の終了済みS16の結果から入力時間を選択（既存保護経路）。
3. 第三の元S49 Actionは第二の終了済み**本物の**S16実移動と実発行入力時間から、相対目標1.0mとの差を計算。残差が0.15m以下（超過含む）なら`STOP_AVOID_OVERSHOOT`。危険源が1.5m未満なら`DANGER_L0_PRIORITY`。いずれも、すでにL0で三度目のMOVE要求が出ている場合には**新Actionを発行せずfail-closed**（本DEVではL0 WAITへの直接再選択は未実装）。
4. 残差が残り危険が差し迫っていない場合のみ、`clamp(residual/second_observed_speed, 0.10, 0.60)`秒を提案し、三度目の元のS15 Action入力のdurationだけ変更する。追加issuer=0、reader=0、P1/M0生体状態・学習権限変更=0。物理運動は**短いSPRINT入力**であり、本試験ではWALK速度への切替は未実装。
5. 第三S16の実移動量、第二と第三の実移動量の合計、誤差改善／悪化の両方を原本に記録。新Action別world段階のため、絶対位置目標や軌道/進行方向の正しさを意味しない。

## 新規・変更ファイル

- `adapters/mineflayer/s49_l0_observed_step_dev.py`: second S16 based residual policy
- `adapters/mineflayer/normal_action.py`: second/third limited input override, same executor
- `adapters/mineflayer/s49_normal_session_real_ci.py`: original L0 three native epochs, bounded third S16
- `adapters/mineflayer/s49_l0_residual_three_real_dev.py`: original Mojang 1.21.8 disposable World runner, isolated environment grants
- `tests/test_s49_l0_residual_third_dev.py`: overshoot STOP, danger priority, input clamp, invalid source
- `.github/workflows/self-l0-s16-three-action-dev.yml`: Python3.12, Ruff, Node22, Java21, native original Mojang World, always archive.

No modification to main, Draft PR #545/#634, qualification or science data. Tests must pass before World trial. No native physicsTick lockstep.

## 実Minecraft 一World / 元S49 3 Action DEV — PASS（2026-10-28）

[GitHub Actions #40627959223](https://github.com/rinsakamo/relay-self/actions/runs/40627959223) 実行固定HEAD `f87ccd1ce951d22533ce24d00c51859105e7bf54` **completed/SUCCESS**。Python3.12 focused / Ruff / Node22 static を実World前に PASS。Java21 official Mojang Minecraft 1.21.8（server SHA1 `6bce4ef400e4efaa63a13d5e6f6b500be969ef81`）、Mineflayer native session、Node/Server cleanup exit 0/0。追加issuer/reader/モデル呼出し0、紙Paper介在なし。

元L0判断（同一session）：
- event 8: zombie 10m -> WAIT（Actionなし）
- event 20: zombie 2m -> MOVE_AWAY -> native Action `s49-native-move-20` OUTCOME 3.030157164494362m、入力0.60s
- event 57: zombie 2m -> MOVE_AWAY -> `s49-native-move-57` OUTCOME 0.8149785454473797m、入力0.19800953133073582s（第一S16から入力調整）
- event 85: zombie 2m -> MOVE_AWAY -> `s49-native-move-85` OUTCOME 0.3243605275351431m、入力0.10s（第二S16から残差0.1850214545526203mを補正）

比較：元の二度目の次ステップ目標1.0mに対し二度目のみで `abs(0.814978545447−1)=0.185021454553m`、三度目まで累積 `0.814978545447+0.324360527535=1.139339072983m`、誤差 `0.139339072983m`。この一Worldでは絶対誤差 `0.04568238157m`改善。ただし三度目は行き過ぎ、メトリクスは複数Actionの**水平移動距離スカラーの合計**であって絶対座標への到達でも、方向一致でもない。

`S49_REPORT`の正規分類 `DEV_ONLY_S49_S16_RESIDUAL_THIRD_ORIGINAL_OWNER`。元のSingle S49 L0 owner、S14承認、S15 native typed ACK、3回のS16 OUTCOME、original Action supervisor closed、元Node/Server cleanupを確認。反射処理への学習/本番P1/M0/SCIENCE昇格なし。Node/Paper厳密tick同期なし。

**保持した失敗原本**: 最初の2 runは構文・テストパスにより実World前FAIL。run #40627688856 は最初の2つのS16を取得（3.0301571644943603m、0.8149785454473797m）したが、WORLDが三度目の判断に必要な4番目のゾンビイベントを送っていなかったため、元S49 max 95秒で BLOCKED / TimeoutError。後者を隠さず、隔離DEVでのみ4番目のWorld刺激を追加して再実行した。#40627959223 は単独で完全PASS。

次の課題: 微移動WALKへ遷移、慣性/加減速を考慮した下限0.1sの過補正低減、STOP時に**新しいL0 WAIT決定を実際に出す**（現状のSTOPは第三MOVE要求があるとfail-closedであり、正式な停止行動ではない）、絶対目標に対する座標誤差と障害物観測。現状は短いSPRINT入力でありWALK制御を実装・実証していない。

Raw artifact: `s49-l0-native-three-s16-40627959223-1`、GitHub artifact ID **12790760199**、ZIP SHA256 `da6c9a5d3d38ea1c9a5aa01380e132555692a0b267e2b762b66699567c1d29ad`。

**DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。main、Draft PR #545/#634は変更せず。
