# RelaySelf L1-MP6 — 異なる身体条件下の予測と原本比較（DEV-only）

2026-11-01。親 [Draft PR #658](https://github.com/rinsakamo/relay-self/pull/658) / 物理実行済みMP5 World原本（[run #41269170943](https://github.com/rinsakamo/relay-self/actions/runs/41269170943)）は凍結。MP5ではPaper main-thread内で `WAIT[t]→FIXED[t+1]→WAIT[t+1]→SCORE[t+1]` の7対が成立したが、同情報のcheap linearと数学的同値、過去Worldとほぼ同じ変位系列で、未知条件の転移は未検証。

## 実験目的と事前固定した判定

**問い：** 既存世界で固定された係数 `c=0.20331885786720635` は、独立の環境介入で身体速度を変えた新規Worldでも次tick位置変位を予測できるか。勝利条件は「異なる条件だった」と「因果順序が成立した」と「精度」の**独立**した判定。cheap linear超越は同式のため**理論上不可能**、L1固有の賢さ/学習更新は主張しない。

- **介入**：実験者がPaper pluginでS49元Action前に `SLOWNESS_II`（`PotionEffectType.SLOWNESS`、amplifier=1、duration=400 tick、Paper effect readback）を対象の身体へ一度だけ付与。これは**本物のMinecraft物理条件変更でありreadonlyではない**。一方でSelfからの追加Actionや新規issuer、S49/L0 policy変更、モデル再学習ではない。元S49がMOVEを実行。
- 初期モデルは前の独立Worldで得た同じ係数で、PRE_FORWARD直後にPaperでticket/source-bindし、効果介入はその次、S49 Actionの前にのみ受付。実行中のfit/refitなし。
- 元Paperが `S50_DEV_BODY_CONDITION_APPLIED` を一件発行し、元 `S50_DEV_BODY_CONDITION_TICK` の8件で同じ対象World/subject・効果active/amplifier1を観測したとき「異なる身体条件に曝した」と判定。Pre-action source順序を原本から監査。
- **事前固定した軌跡差閾値**：MP5旧Controlの同一元S49 action `movement_m=0.6269065734210615m` に対し、新規WorldのMOVE距離絶対差が `>=0.06m` であれば `OBSERVED_DISTINCT_NATIVE_MOTION`。それ未満は `NOT_ESTABLISHED_BY_NATIVE_MOVE_METRIC`。条件介入が効かなかった可能性や元World自然ばらつきは分けて残す。単一Worldの差をSlowness因果効果の統計的推定としない。
- 元Paper WAIT/INPUT各8件、Paper-local予測7件・採点7件の本物のcallback順序、元S49 S16 OUTCOME、Node/Java exit0、cleanup passを別々に監査。MAE/RMSEを0/last/train-meanと比較し、**同情報cheap linearは完全同値**と記録。旧Controlと新規Slowness条件は1対の例であり、これだけでは汎化改善/劣化の確率的結論を出せない。

## 実装と保護

- `S50BodyConditionGate.java`：World/subject/marker/効果モードの一回限りpreAction受理。未PRE_FORWARD・未MP5 arm・元Action開始後・事前効果・他効果・重複・異なるWorldを拒否。
- Paper本体 `s50-changed-body-condition-dev: false` default OFF、console-only `relaydevcondition marker SLOWNESS_II`。自動世界改造や追加Actionは行わない。効果付与/readbackを元Paper sourceへ記録し、WAIT中は効果サンプルを既存S50オブザーバから受動ログ化。効果付与自体は物理介入である。
- `self_body_s50_l1_body_condition.py`：SHA pinしたconfig/登録元Paper receiptを検証。`self_body_s50_world_dev.py` に `--l1-paper-body-challenge-dev` 明示opt-inを追加し、元モデルARMの後・元S49 native MOVEの前にeffectのsource readbackが正しく得られなければAction前でBLOCK。
- S49唯一Action issuer、S16、Paper M0.2排気会計、S50 8×2 source owner、既存MP5モデル/チケット所有、mainおよび過去の原本は変更しない。次回Worldは新規使い捨て／再試行0／実験レーン継続grantの別消費として報告。

## 資格境界

Slowness介入はアクチュエータ命令ではなく実験者の環境条件制御だが、物理条件を変えるため完全readonlyのMP5とは異なる。実Worldを見ずに自然条件の変化と断定しない。実験の差が通常World生成の自然ばらつきやtick jitterを含む可能性も残す。

**上限分類:** `MP6_CHANGED_BODY_DEV / PREVIOUS_MP5_CONTROL_RETAINED / FROZEN_CHEAP_EQUIVALENT / UNSEEN_CONDITION_TRANSFER_TEST / GOAL_UNDETERMINED / L10_S10_S11_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。
