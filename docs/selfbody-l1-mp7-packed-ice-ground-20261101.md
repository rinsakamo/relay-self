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


---

## MP7 actual Minecraft DEV 1 World — 物理変位系列の条件差成立

2026-11-01、[GitHub Actions実World #41274077794](https://github.com/rinsakamo/relay-self/actions/runs/41274077794) **SUCCESS**。実行HEAD `49ba1f5f1d2d0c255fc471542c9f7c062229641c`。新規World 1回、S49唯一native Action 1件、再試行0。Paper/Mineflayer pinned source、Python3.12 **81 PASS**、JDK21 ICE gate **15チェック PASS**、Ruff/contracts PASS、Maven `BUILD SUCCESS`、preflight/port PASS。

### 原Paperと元S49の物理readback

- `S50_DEV_ICE_FLOOR_APPLIED` **1件**、World tick251、対象World `ad49ff13-fa30-4577-ae27-33176601f48f`、身体 `dcae346d-e66f-331a-b459-a5a5370e9738`。元床 **GRASS_BLOCK** → **PACKED_ICE** 5×5の**25 blocks**。起点 (x7, floor y-61,z-2)。床を変更したのは実験者のWorld介入で、Self追加Actionではない。
- `S50_DEV_ICE_FLOOR_TICK` **8件**すべて足元 `PACKED_ICE` を原Paperから確認。元S50 `WAIT_TICK` と `INPUT_TICK`各8（World tick258–265）、Paper-local `LOCAL_FORECAST_FIXED`7件 / `SCORE`7件。元stdoutで `WAIT[t] < FIXED[t→t+1] < WAIT[t+1] < SCORE[t+1]` の**全7対**を独立検証。原stdout/server.log byte一致、SHA256 `6729c0c1eb8d55893a2d1487758969d3fc68c4b23a657eb956bc400a1edeb9d7`。
- MP5通常床の元S49 MOVE `0.6269065734210615m` vs MP7氷床の元MOVE `0.36725501102687663m`。差 **0.25965156239418485m** は事前固定した `0.06m` を超過。**observed distinct native motion** を認定。
- 原Paper S50 WAIT変位8件（m）：`[0.1381888451, 0.0580941902, 0.0, 0.0980111288, 0.0412035947, 0.0367453657, 0.0327695171, 0.0292238554]`。通常床MP5の `[0.0494921883, 0.0095436049, 0.0052108083, 0,0,0,0,0]` とは明確に異なる。氷床では3番目のサンプルが0、ほか7/8は非ゼロ。全tick連続滑走とは主張しない。
- 平均絶対誤差：既存過去World係数L1/cheap **0.0339034618559081m**、RMSE **0.04318067423116191m**、zero baseline MAE **0.042292521701713985m**、last MAE **0.04356960676556668m**、training mean MAE **0.04078696933358777m**。旧MP5通常床 L1 MAE **0.0006927084716710721m** より大幅に悪化した。ただし**同情報cheap linearと同値**、L1独自モデル優位は0。
- 元S49/S16/S50 owner DEV PASS、Node exit0・Java exit0・cleanup・port再bind PASS。S10/S11/L10更新、L0 policy変更、新規Self Action/実LLM calls 0。Goal UNDETERMINED / QUALIFICATION NO_GO / SCIENCE NOT_RUN。
- 元原本artifact `mp7-packed-ice-one-world-41274077794-1` をActionsに保存。[独立SHA付きreadback](evidence/issue653-mp7-ice-floor-20261101/run1/independent-physical-readback.json)。過去World原本とmainは不変。

### 分布差と因果効果の限界

今回**実際に異なるブロック条件および実測運動系列**が成立した。これによりMP6で不成立だった*条件が違うWorldでの予測を採点する*実験は成立したが、**予測モデルが未知条件を適切に一般化したことは未証明**。また、MP5とMP7は別のWorldで初期spawn位置や環境も異なるため、移動距離差0.25965mの全量を氷の摩擦だけに因果帰属しない。matched control / 複数seedは今後の実験。

**結論：** `MP7_DEV_OWNER_PASS / REAL_PACKED_ICE_WORLD_25_BLOCKS / OBSERVED_DISTINCT_NATIVE_MOTION / PAPER_LOCAL_PREQUENTIAL_7_7 / OLD_MODEL_MAE_DEGRADATION / SAME_INFORMATION_CHEAP_EQUIVALENT / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。
