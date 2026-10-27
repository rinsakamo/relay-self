# T1m 実Minecraft A区間内部計測 DEV — 2026-10-27

**DEV_ONLY / DEV_WORLD_OBSERVED / NATIVE_SOURCE_REFUSAL_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

専用branch `self/dev-t1m-causal-age-instrument-20261027`、開始local/remote HEAD `5ec15fbe4e5b199734b1f6791b0f88242e1a62a2`。基底T1l `59092920ff91678ed3589646857890619d9ec546` が祖先。主checkout main `32fe105fc12cbf54abd11bfba7c8a75d319939df` はcleanのまま不変。最終HEADはGit履歴および外部delivery.jsonに記録。

原本root `/home/rinsa/work/t1m-evidence-20261027`。全7試行は新しいWorld/session/output。bootstrapはT1lと同じT1h run-006 serverからlibraries/cache/versions/JARのみコピー。過去Worldは再起動しない。T1l封印794ファイルSHA256一致。main・Draft #545/#634・S18・R/V原本・既存T1h〜T1l原本は変更していない。

## 実装修正・テスト

Python3.12.3: 指定focused60 PASS、runnerを含む拡張62 PASS、FAST625 PASS。Node22.22.2: 関連全体72 PASS。Java21.0.12.1: BUILD SUCCESS。Ruff・repository contractsを確認。FULL・main mergeなし。初回focused57/Node18、途中FAST624/Node71のログも保持。

- 診断hook例外をsource admission例外から分離。欠損sidecarは診断FAILとし、真正source/cleanupの結果は別保存。閾値を緩めていない。
- JVM J1をscheduler callback先頭へ移動し、sidecarにboot/world/player/server_tickを付加。wire schema/seqは変更なし。J0はchallenge受信処理内、J2はsendPluginMessage復帰。J2は受信ACKではない。
- joinはindex/challenge、source identity、WorldTick/server tick、native session、元status/reason/age、各同一時計の順序と経過時間を検査。重複/欠損/余剰は検出。catch-upによるchallenge再使用、未適用のまま後続に上書きされたchallenge、正常shutdown中のPaper-only末尾を分ける。架空の対応は作らない。
- Node timing revision2は評価完了後のemit復帰、診断hook開始/復帰、次challenge発行を追加。新規reader/issuer/Action権限なし。
- 150ms上限・25ms評価budget・2400 challenge・2300 soak guard・M0/P1式・拒否後ラッチは不変。計測既定OFF、T1f無効時の単独有効化を拒否。

## 全Worldの結果

run-001は実Worldで鮮度拒否。FAIL原本/reportは不変。run-002/003は通常負荷、run-004は軽度CPU負荷で各1200 PASS。その後、run-001で見つかった評価後区間のrevision2計測を追加したため、最終比較はrun-005/006通常負荷とrun-007同じCPU負荷で行った。初期World中にread-only reducerも修正したため、launch時source hash/diffと、最終reducerによる別ファイルjoinを区別する。

|run|条件|結果|会計行|native Paper / 結合|ADMITTED / STALE|150ms超過|実効TPS|
|---|---|---|---:|---:|---:|---:|---:|
|run-001|通常|FAIL|349|356 / 356|351 / 5|5|20.168346|
|run-002|通常|PASS|1200|1202 / 1202|1202 / 0|0|20.034023|
|run-003|通常|PASS|1200|1202 / 1202|1202 / 0|0|20.052792|
|run-004|軽度CPU|PASS|1200|1202 / 1202|1202 / 0|0|20.036842|
|run-005|通常|PASS|1200|1202 / 1202|1202 / 0|0|20.047293|
|run-006|通常|PASS|1200|1202 / 1202|1202 / 0|0|20.043611|
|run-007|軽度CPU|PASS|1200|1202 / 1202|1202 / 0|0|20.034653|

TPSは最初の会計baselineから最後の会計snapshotまでの同一JVM paper_nsと実WorldTick差で計算。失敗run-001のTPSは拒否前349会計tickのみ。全native seq欠番0、Paper index/server tick/WorldTick欠測0、identity変更0。startup NONEは実観測0。全試行の診断最終再結合率100%。

## 最終3Worldの分布

単位ms。minimum / median / p95 / p99 / maximum。nearest-rank、medianは中央2値の平均。A/D/Eとevent loopはsnapshot単位。writeは全unique issue単位（末尾の次challengeを含む）。同じchallengeを参照する複数snapshotのDは同じJ0からの経過時間であり、独立のscheduler待ち時間とは限らない。

|run|指標|n|min|median|p95|p99|max|
|---|---|---:|---:|---:|---:|---:|---:|
|run-005|Node A N0→N2|1202|5.645353|49.783096|50.422935|51.766498|106.524513|
|run-005|Node write N0→N1|1203|0.094098|0.154163|0.271423|0.401677|0.722996|
|run-005|JVM D J0→J1|1202|0.228625|47.799099|48.408227|48.522300|48.778147|
|run-005|JVM E J1→J2|1202|0.241107|0.413026|0.924473|1.332538|10.234470|
|run-005|event-loop区間最大|1202|0.000000|10.403839|10.674175|10.977279|69.664767|
|run-005|評価完了→次issue|1202|0.106127|0.148786|0.280669|0.431846|1.215289|
|run-005|評価完了→emit復帰|1202|0.068899|0.098106|0.200157|0.286204|1.165432|
|run-005|診断hook全体|1202|0.032673|0.046007|0.091754|0.130703|0.254031|
|run-005|hook復帰→issue|1202|0.000645|0.001677|0.004196|0.016010|0.059327|
|run-006|Node A N0→N2|1202|4.731926|49.797897|50.922505|53.020170|103.683703|
|run-006|Node write N0→N1|1203|0.093655|0.151851|0.253228|0.365521|0.475353|
|run-006|JVM D J0→J1|1202|0.282994|47.713577|48.325493|48.506052|97.829808|
|run-006|JVM E J1→J2|1202|0.246082|0.435049|0.977110|1.397227|8.328968|
|run-006|event-loop区間最大|1202|0.000000|10.231807|10.682367|11.018239|83.820543|
|run-006|評価完了→次issue|1202|0.095494|0.151348|0.266154|0.455780|52.513781|
|run-006|評価完了→emit復帰|1202|0.062880|0.101149|0.190626|0.308897|52.418903|
|run-006|診断hook全体|1202|0.030152|0.045338|0.073791|0.095659|1.690435|
|run-006|hook復帰→issue|1202|0.000727|0.001917|0.003852|0.015102|0.077272|
|run-007|Node A N0→N2|1202|4.791497|49.802651|50.611473|52.111671|108.631185|
|run-007|Node write N0→N1|1203|0.076151|0.141342|0.202811|0.256572|0.515305|
|run-007|JVM D J0→J1|1202|0.228610|47.964613|48.568817|48.749044|98.110349|
|run-007|JVM E J1→J2|1202|0.208655|0.379757|0.795082|1.048481|6.466683|
|run-007|event-loop区間最大|1202|0.000000|10.412031|10.665983|10.821631|78.577663|
|run-007|評価完了→次issue|1202|0.094887|0.135981|0.187777|0.243856|57.787309|
|run-007|評価完了→emit復帰|1202|0.059079|0.090359|0.129611|0.177437|57.706166|
|run-007|診断hook全体|1202|0.028238|0.042457|0.061225|0.080621|0.125679|
|run-007|hook復帰→issue|1202|0.000710|0.001922|0.003201|0.008125|0.057505|

event-loopは10ms resolutionのhistogramをsnapshotごとにresetした区間最大値。0はstall不在を意味せず、timer samplingより先にpacket callbackが配送された場合などを検出できない。個別packet配送遅延の実測値ではない。write復帰もネットワーク送信完了ではない。

## 原因の切り分け

通常負荷ではDの中央値が約48ms、Eは約0.38〜0.58ms。20TPSの次callback待ちがA約50msの通常成分と整合する。ただしA−D−Eを通信遅延とは呼ばない。JVM/Node絶対時計の直接減算は一切していない。

run-001のindex351はA50.151808ms、D47.930238ms、E0.448100msでADMITTED。その評価完了からchallenge352発行までNode同一時計で約267ms空いた。その間JVM callbackは約50ms間隔で継続し、旧challenge351がindex352〜356でも使われた。受信は後からまとまった。Dは97.796037→297.852229ms、A319.586159→321.098167ms、Eは0.33〜0.53ms。Dの増大をPaper callback停止の原因証明にはできない。最初のSTALE後ADMITTEDは0、会計349行で凍結。

この評価後停止は旧A/B/Cだけでは分離できなかったため、Nodeのemit復帰・診断hook復帰を追加した。emit区間には既存node_timing.jsonl同期write・native出力処理とOS待機、hook区間にはsidecar writeとOS待機が含まれる。run-001当時は内訳を記録していないので、267msがstdout、sidecar、GC、OS schedulingのどれかはUNKNOWN。後続revision2の最大値や負荷比較から遡及して原因確定しない。

revision2のrun-006 index354ではpost-eval52.513781msのうちemit区間52.418903ms、診断hook0.090647ms。次index355で旧challenge354が再使用され、A103.683703ms、D97.829808ms。run-007 index840でもpost-eval57.787309msのうちemit区間57.706166ms、hook0.077939ms、次index841は旧challenge840でA108.631185ms、D98.110349ms。両方ADMITTEDのまま。これらの停止をemit呼出し前後の区間へ局所化できたが、emit内の既存node_timing.jsonl同期write・JSON生成・stdout write・GC・OS schedulingの内訳までは未分離。run-001の267msへ遡及適用しない。

JVM gc/safepoint受動ログはrun-002以降に追加。startupを含む最大値をJSONに記録。JVM uptimeログと個別packetの精密整列は未実装であり、GCを個別外れ値の原因とは断定しない。相関係数はJSONに参考保存するが、catch-upの再使用やstartup、少数外れ値の影響があるため因果証明ではない。

## 負荷条件と非干渉の限界

run-004/007はいずれも所有CPU worker2本、各100ms周期の50ms busy・残りsleep、affinity変更なし、メモリ圧迫なし、150秒の自己期限。Minecraft起動前に開始しcleanup後にSIGTERMで通常終了させる。load-receipt.jsonとworkerログに開始/終了/PID/CPU時間、毎秒host.jsonlにCPU・RAM割合・loadavg・メモリ状況を保存。負荷条件は実行前固定。workerは全exit0/PID不在。

- run-005: A中央値/p99/最大 49.783096/51.766498/106.524513ms、D最大 48.778147ms、E最大 10.234470ms、event-loop最大 69.664767ms、TPS 20.047293。
- run-006: A中央値/p99/最大 49.797897/53.020170/103.683703ms、D最大 97.829808ms、E最大 8.328968ms、event-loop最大 83.820543ms、TPS 20.043611。
- run-007: A中央値/p99/最大 49.802651/52.111671/108.631185ms、D最大 98.110349ms、E最大 6.466683ms、event-loop最大 78.577663ms、TPS 20.034653。

T1l非計測のage中央値49.898139msに対し、最終T1m age中央値は49.842624/49.846071/49.852149ms。大きな定常悪化の有無は比較できるが、別World/host時刻であり、負荷非干渉の証明ではない。同期ログwriteが外れ値を作る可能性は残る。最終CPU負荷run-007のA p99=52.111671msは通常run-006の53.020170msより小さく、今回の軽負荷で一貫した悪化は観測していない。CPU負荷1条件各1回から根本原因や一般的安定性を確定しない。

## 会計・Action・cleanup

正常6Worldは各1200行、M0 E=10.680000000000945、基礎cost1.2＋L0認知cost0.12、移動cost/intake/credit0。P1 fatigue/recovery0、WAIT資格なし。失敗run-001は349行、E=11.616100000000275、source/ledgerラッチ。各行の既存expenditure式とintake0を原本照合。baselineは会計0、200tick checkpointを保存。

全7WorldでMOVE/EAT/STOP/resume/Action effect/clear/LLM/TPS actuator0。Java/Node exit0、shutdown_ackとconnection_end、PID不在、port再bind、Paper stop/all-dimensions保存を別確認。shutdownは高水準STOP ACKの証明ではなく、STOP自体未発行。

## 原本SHA256・読み戻し

各runのnative.jsonl、paper.log、t1m_node_timing.jsonl、Node/Python timing、report、source_hashes、t2_ticks、World全ファイル、起動argv/env/source hash/diffを外部rootに保存。source_hashes全件一致、ロードされたPluginの実コピーSHAがreport/launchと一致。主要原本SHAは同名JSON、全Worldはrun-NNN-world-hashes.json、原本総索引はoriginals-manifest.json。最終Git/Issue読み戻しと封印はdelivery.json / seal-readback.json。

Paper JAR SHA256: `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`。

実ロードPlugin JAR SHA256: `7b24265e2a8087b12ff11351ef91d5db21250bce7fd1a220cfcd2e573cf69d81`。全Worldで同一の今回ビルド品。

原本総索引SHA256: `ae77898928360f38203c4eceac9277087a0b428a7a77e741d0bc8e3fe8731c07`（1492ファイル）。

## 未成立と次段階

R/V資格・全subtick静止・独立source認証・P1-qualified WAIT・長時間自律性・SCIENCEは未成立。これらはNATIVE_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。高TPS・資格World・main merge・FULLは実施していない。

次は同じ受動境界で評価後停止を再観測し、必要ならOS scheduler/Node GC/既存node_timing同期I/O・stdio・sidecar I/Oを同一時計の個別境界で補足する。event-loop histogramのreset順序による死角も別のtimer遅延原本で検証する。現時点で確認できたのは通常のcallback待ち成分、challenge再使用、評価後の停止区間であり、267ms停止の根本原因はUNKNOWN。
