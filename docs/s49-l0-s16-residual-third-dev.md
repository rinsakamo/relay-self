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
