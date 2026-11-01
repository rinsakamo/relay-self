# RelaySelf MP7 — packed-ice ground distribution shift DEV

2026-11-01。親 [Draft #659](https://github.com/rinsakamo/relay-self/pull/659) MP6実Minecraftでは、元S49 Action前にPaper Slowness IIを実際に付与し、WAIT8 tickを通してamplifier1の状態を観測したが、**元MOVEとWAIT変位系列はMP5原本と完全同値**。物理状態を設定しただけでは観測運動の分布差を証明できない。

## 実験仮説と事前固定判定

MP7ではPotionではなく、Worldの身体を支える**実際の床ブロック25個（5×5）をPACKED_ICEに置換**し、元S49 Actionの開始前に全ブロックをPaperで再読取りする。クライアントには通常のPaper block update経路で変更が伝わる設計だが、**ブロック変更をMineflayerが物理移動として反映するかはUNKNOWN**。

次の項目を**独立**に判定する。

1. 同一marker/subject/WorldのMP5予測係数 `c=0.20331885786720635` とticketが元PaperでARMされた後、元S49 Actionより前に `relaydevicefloor <marker> PACKED_ICE_5X5` がconsole-onlyで1回実行される。床は元から全25個solid・同一材質、packed iceでなく、読み込み済みchunkのみ。プレイヤーはonGround。条件不一致は**変更前に拒否**。変更後全25ブロック `PACKED_ICE` のsourceを `S50_DEV_ICE_FLOOR_APPLIED` に保存。
2. 元S50 WAIT/INPUT各8 tick、Paper-local `FIXED→後続SCORE` 7対、独立Paper sourceに `S50_DEV_ICE_FLOOR_TICK` 8件があり、足元が `PACKED_ICE` と実際に観測される。元S49 native MOVE 1件、S16 OUTCOME 1件、Java/Node exit0、World削除・port解放を元ownerが完了。モデル更新/L0変更/LLM呼出し/追加Self Actionは0。
3. **事前固定した移動差**：元MP5通常床 MOVE `0.6269065734210615m` と今回MOVEの絶対差が `>=0.06m` なら **OBSERVED_DISTINCT_NATIVE_MOTION**。その未達は **MOTION_SHIFT_NOT_ESTABLISHED**。過去Worldと異なるfloorであることだけで転移成功とはしない。
4. Paper原変位系列8点に対しL1/cheap linear・zero・last・train-mean baseline MAE/RMSEを同条件で計算。MP5固定係数モデルと**同情報cheap linearは式が同じで差を生じ得ない**。性能改善・汎化/学習を主張しない。

## 保護と権限

- 物理ブロックを変えるのは**実験者**のWorld介入であって、自律的なSelf Actionではない。地面を変えるため完全なreadonlyとも呼ばない。
- `s50-ice-floor-dev: false` default OFF。MP6 potion `s50-changed-body-condition-dev:false` / MP4 console RTT gate OFF / MP5 Paper-local ON。専用Java gateは先行ARM・元native Action未開始・25ブロック完結・再発行拒否でfail closed。
- 以前のMP3/MP4/MP5/MP6原本、main、元S49/S16/物理M ownerを変更せず、フリーズ済係数と既存host/Action/Metaを使用。
- 実験は継続grant下の独立1新規使い捨てWorld、同一World再試行0。実World開始後のFAILも承認1回を消費。CI/JDK21/Maven/Python3.12/Ruff/contracts/正式SHA/port preflightがPASSするまで起動しない。結果と失敗原本を保存。

**制限**：単一Worldは因果統計的推定でも正式SCIENCEでもない。8 WAIT callback前の予測固定はMP5で成立したが、tick内部物理積分前の証明ではない。Goal UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN、学習更新0を保持。
