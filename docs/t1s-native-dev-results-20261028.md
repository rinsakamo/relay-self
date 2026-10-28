# T1s P1再校正候補・実Minecraft DEV（2026-10-28）

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN — PASS**

branch `self/dev-p1-physiology-calibration-20261028`、開始HEAD `426f494f77b9bcfb0b4fc8ef3b5862a40f283655`。実行sourceは同HEAD＋launch receiptのdiff。最終commitはGit履歴で特定できる。

## 検証と最小修正

Python 3.12.3 focused **140 PASS**、既存継承FAST **756 PASS / 46ファイル**、Ruff、488 Pythonファイル構文、repository contracts PASS。FULLとNode/Java再ビルドなし。

初回focusedはT1pの既存hazard negative testが1 FAIL。プロファイル未指定時にも新keywordを渡すAPI不整合を、旧呼出し維持で修正。hazard拒否の期待値は維持。Ruff初回2件は候補部分のimport順序のみ修正。初回ログは外部原本rootに保存。指数式・負荷・センサ・Action認可・freshness gateは変更していない。

旧P1 SHA `d23f1f595095adb1da0b3ce74a72803b85b68359dc94d2ee8b03fcd2078f68b0` は元T1rモジュールと一致。
新P1 SHA `cd71b4180b6439e8fd0f1365505150c81ae6ad37f9e0153ea85698f33a263f40`。

[新旧比較](p1-physiology-comparison-dev-20261028.md) と対応JSONを参照。4 block/s WALK 1/5/10分は旧1/1/1、新0.024/0.12/0.24。初期1.0のWAIT 1 tick/1秒/10秒/40秒/80秒は新0.998750781/0.975309912/0.778800783/0.367879441/0.135335283、旧0.9/0/0/0/0。

## 実Worldと監査

新規使い捨てWorld **1、PASS 1 / FAIL 0**。World UUID `228231b2-0ddc-475b-b4ae-1ba988a67424`、session `38e5978f-60e1-447f-b028-e3f188eb7e67`。既存T1r Paper/Plugin、bootstrap 121ファイル、Node依存136 manifestをSHA照合して再使用。World本体は継承せず新規生成。Node22.22.2 / Java21.0.12.1 / Paper1.21.8-60 / Mineflayer4.39.0。

元S49 **MOVE 2 / OUTCOME 2 / clear ACK 2**、effect 4個すべて一意、追加Motor・Action/effect重複0。実行経路は既存T1e単一native reader→T1p→S49、既存TickAccounting/P1を注入で再使用。同期Node trace OFF・sidecarなし、LLM 0、food credit 0、TPS actuator 0。

Paper source **81/81 ADMITTED**、source違反0。課金前baseline tick1033から会計tick **1034–1094、61連続tick**、欠損補間0。初回ADMITTEDは非課金。最大因果年齢 **92.925939 ms**、receive→評価完了最大0.726706 ms（25ms budget内）。因果年齢は片道遅延やroot causeを意味しない。

OUTCOME距離合計1.2538131468421227 block、静止後位置変位合計1.7143394396728937 block、**疲労課金元のPaper累積実測motion差分合計 1.682105896573586 block**。要求距離・想定速度を疲労課金に使わない。

M0: 12 − basal0.061 − cognition0.0061 − movement0.003364211793147172 = **11.92953578820689**。WAITでもbasal0.04を計上、食料入金0。

P1: 初期0 + 実測蓄積 **0.0001682105896573586** − 回復 **6.139620787906228e-06** = 最終 **0.0001620709688694524**。各epochの実WAIT_DEVは20 tick、計40 tick。第1 MOVE後の疲労8.249361767371389e-05は20 WAIT tick後8.045684299624882e-05、第2 MOVE後0.0001661738149798935は20 WAIT tick後0.00016207096886945236。各回 `exp(-20/800)` と一致。WAIT 1 tickで全回復しない。非WAIT回復0。

外部 `audit.py` は保存済みnative/commands/paper/t2/report/python timing/Worldをread-only監査し、元P1.advanceを使わずPaper実測距離と直接exp式で全tickを再計算。WAITの2端点・clear/terminal順序・入力/位置/脅威・同一control generation、profile/session/source連続、M0収支、2 OUTCOMEとclearを照合。実行source SHA、T1q/T1r原本全ファイルの不変も確認。独立source認証やR資格の監査ではない。

Java PID 842135・Node PID 842233はともにexit0・消滅、World保存、port25565の独立再bind PASS。transport closure、clear ACK、Paper保存/停止、PID消滅はそれぞれ確認した。高レベルSTOP ACKは本caseの証明対象外。

## 原本・保護・限界

原本 `/home/rinsa/evidence/t1s-20261028/T1S-001/t1s_calibrated_body_loop/`。World完全本体、native.jsonl、commands.jsonl、paper.log、t2_ticks.json、report.json、python_timing.jsonlを保持。
外部manifest `/home/rinsa/evidence/t1s-20261028/originals-manifest.json`、**205ファイル全SHA読み戻し一致**。
manifest SHA256 `4fa490f2963d1bfa018c4bb07d71f680873a8b89c7fc3dc715e88ff8c9997613`。
起動argv/env・実行source hashes/diffは `T1S-001-launch.json`。検証/比較/監査スクリプトとログも同rootに保持。

main、Draft #545/#634/#626のHEAD、S18凍結blobを開始時と終了時に照合する。旧T1q/T1rの成功原本を変更しない。R/Vレーンへの書込みなし。Draft #626はコメント報告のみ。

物理判定は**短時間WALKと回復時系列を改善した工学的候補／人体生理妥当性未確定**。長時間WALKの定常性、移動中回復、速度・地形・負荷別モデル、RUN/JOG/DASH（DASH約20秒制約を含む）は別途校正。実機は短距離MOVEのみで、1/5/10分WALKと40/80秒回復はオフライン比較。T1sは元T1p経路であり、SelfBody感覚/L0フィードバックの実機統合は今回未実施。旧T1q/T1rとセンサ量子化は回帰維持し、REST/READY再現のための負荷増幅は行わない。
