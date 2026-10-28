# T1u 実Minecraft DEV結果 — 2026-10-28

**DEV_ONLY / DEV_WORLD_OBSERVED / NATIVE_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

**単一P1歩容会計の実World統合は未成立。** オフライン接続はPASS。新規4 Worldの内訳は、T1u接続FAIL 2、既存P1を使う観測専用PASS 2。後者をT1u成功へ昇格しない。

## ソースと変更

branch `self/dev-t1u-gait-t2-integration-20261028`、開始HEAD `fa61ca9fe1c84fd8886db8ed6e5cf7e124b67f4a`。T1s成功HEADは祖先。実行コードは各 `T1U-NNN-launch.json` のbaseline・diff・全source hashと、hash読戻し一致する `T1U-NNN-source/` に固定。最初の2件のsourceコピーは実行後にbaseline+保存diffから復元し、全ファイルの実行時SHA256へ一致を確認。後半2件は起動前にコピー・hash照合した。

既存 `p1_gait_dev.py` blob `d241978d0eba1843e3a6caed96c90e3c16e8dc39`、既存テストblob `4887ccc32b7e0aede95b0301d7778fe9a16f9c45` は変更なし。P1状態は `TickAccounting.fatigue` の1個。既定T1p/q/r/sは元advance、opt-inだけ既存advance_gait_dev。tau併用拒否、未会計anchor、tick連続性、未決済DASH拒否を維持。元M0・reader・issuer・Motor writerを増やしていない。

追加計測は既存Paper snapshotにdefault OFFの `gait_dev`（実sneak/sprint、速度base/value、modifier数）、既存Node callbackに `getControlState()` の読取り `applied_controls_dev`。厳密なoptional wire検証、実観測を使うbounded JOG/back・因果的WAIT provider、refusal記録と例外ラッチ、新規T1e DEV caseを追加した。

## 検証

Python 3.12.3: 初回focused **174 PASS**、最終focused **198 PASS**、FAST **814 PASS / 49 files**。Ruff・構文492 Python files・repository contracts PASS、Node snapshot 17 PASS、Java21 plugin build PASS。FULL / QUALIFICATION / SCIENCE未実行。system Pythonのpytest欠如、開発中indentation FAIL、監査器のpath/API不一致を含む初回ログを保存。負対照は緩和していない。

## 実World

|Run|用途|runner|MOVE / OUTCOME / UNKNOWN / clear ACK|会計tick|歩容観測|最大因果年齢 ms|
|---|---|---|---|---|---|---|
|T1U-001|T1u接続|FAIL|0 / 0 / 0 / 0|0|JOG 0, WAIT 0|106.559021|
|T1U-002|既存P1の観測専用|PASS|2 / 2 / 0 / 2|60|JOG 0, WAIT 40|96.647769|
|T1U-003|既存P1の観測専用|PASS|2 / 2 / 0 / 2|60|JOG 4, WAIT 40|85.808094|
|T1U-004|T1u接続|FAIL|1 / 0 / 1 / 1|0|JOG 0, WAIT 0|101.209607|

全native sourceはADMITTEDかつ各run内連続、session/World/player/boot一致。Action/effect重複0。各Worldにshutdown時Paper送信tailが1 tickあり、会計へ補間しなかった。全runでtrace OFF、LLM 0、食料credit 0、TPS actuator 0、追加Motor owner 0、追加P1状態0、追加DASH課金0。全4件でWorld全次元保存、Java/Node exit0・PID消滅、transport closure、port再bind、独立再bindを確認した。clear ACKとtransport closure、高レベルSTOP ACKを区別し、後者は証明していない。

001は初期静止tickの非因果WAITを拒否し、Action前停止。004はanchor後のMOVE開始境界で拒否し、S49が1 ActionをUNKNOWNとして閉じ、clear ACK 1を得て次Actionを止めた。両T1uのP1遷移0、蓄積0、内部回復0、最終F=0、M0=12。実行開始や正常cleanupをT1u会計成功へ読み替えない。

002ではPaper input bitmapが実移動中も0だったためJOG認定0。003で同一readerの実適用control読取りを追加し、Paper実移動・速度属性・両端点の因果MOVING generationと結合してJOG/back 4 tickを確認した。WorldTick/source seqは1033/36、1034/38、1063/82、1064/84。速度base/value≈0.10000000149、modifier0、sneak/sprint false、実controlはbackだけtrue。これはbounded DEV観測であり全tick R証明ではない。初期・開始・惰性・clear境界はUNDETERMINEDを維持。

003の台帳は**旧P1観測用**で、WorldTick 1031–1090の60 tick、WAIT_DEV 40。旧P1蓄積0.06728423586294344、回復0.06728423586294344、最終0。M0 basal .060 + cognition .006 + move .003364211793147172、最終E=11.93063578820689。これらはgaitモデルのnative遷移ではない。

## オフライン比較

同一初期F=0、capacity=1、既存advance_gait_devを使用。値は設計パラメータであり人体生理の確定値ではない。

|モード|1分 F|10分 F|60分 F|定常F|
|---|---:|---:|---:|---:|
|WALK|0.000000000|0.000000000|0.000000000|0.000000000|
|JOG|0.032422543|0.033333333|0.033333333|0.033333333|
|RUN|0.124299174|0.159999951|0.160000000|0.160000000|

|DASH定出力|上限到達/観測秒|最終F|追加M0要求|
|---|---:|---:|---:|
|25%|3600.00|0.736799507|180.000000|
|50%|59.85|1.000000000|5.985000|
|75%|30.20|1.000000000|4.530000|
|100%|20.00|1.000000000|4.000000|

25%は60分でも上限未到達（定常≈.7368）。100%定出力では20秒・M0追加要求4。内部回復も各tickで計算され、蓄積−回復＝正味疲労を確認。DASH後RUNは.16へ、WALK/WAITは0へ回復する。方向をside/backへ変えるとDASH stanceは保持して追加出力0・追加M0 0、上限4.32 m/s。詳細JSONに蓄積・内部回復・身体効率・DASH後各1/10/60分を保存した。

20秒は**定出力の数学的anchor**。既存motor fadeはF>.5で出力を下げるので、実機が常に全開で20秒に到達するという主張ではない。DASH追加値は要求であり既存M0への決済ではなく、native forward DASHは引き続き拒否する。速度別負荷を変更していない。

## 独立原本監査・保全

外部原本root: `/home/rinsa/work/t1u-evidence-20261028`。完全World、native/commands/paper/t2/report、実行source/profile hashとsourceコピーを保持。外部manifest `/home/rinsa/work/t1u-evidence-20261028/originals-manifest.json`、**802 files**、SHA256 `f9647c6698ca59f9023e0437b6d7dde3eca0cd55e9b511bb8e17439ac93c57d5`。全ファイル読戻し一致。

外部 `audit.py` は停止済み原本だけからidentity・admission・連続性・WAIT因果端点・台帳before/after・既存関数の再計算・M0収支・Action/clear/UNKNOWN・保存/cleanupを照合した。4 runとも個別に実行時source providerを使用。T1u native advance_gait_dev照合は **NOT_EXERCISED / 0 transitions**。未知tickを除去して架空の連続gait系列を作っていない。独立監査はsource認証やR資格を意味しない。T1q/T1r/T1s全原本manifestと全ファイル、S18はbefore/after一致。

## 未成立条件・次段階

初期静止・MOVE開始・残留区間を、sourceに基づき単一P1へ正当に計上する規則が未成立。WAITへ再ラベル、tick破棄・補間、anchor繰返し、無根拠回復や人工疲労では修復しなかった。これを解決後、改めて2 MOVE/OUTCOME/clearのT1u連続会計と既存advance_gait_devの独立native再計算が必要。WALK/RUN/DASH適用証拠と元M0へのDASH追加決済、SelfBody→L0フィードバックはその後。main・保護Draft HEAD・R/V ownerは変更しない。
