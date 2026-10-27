# T1n emit内部計測・実Minecraft DEV結果 — 2026-10-27

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

通常2Worldと固定軽度CPU負荷1Worldで各1,200連続会計行PASS。軽度負荷run-004のemit全体59.091475msのうち58.896873msを、既存`node_timing.jsonl`への同期`writeSync()`呼出し区間に局所化した。直後のPaper tickは旧challengeを再使用し、Node causal-age Aは110.324901msとなった。物理ディスク遅延、OS scheduling、GCの根本原因はUNKNOWN。

厳密な52〜58ms範囲のemit停止は0件。T1mの約52〜58msと同程度の約59ms停止を今回新たに観測した、という範囲の結論である。通常2Worldでは50ms以上のemit停止0件。T1m run-001の約267ms停止へ、この局所化結果を遡及適用しない。

## 実行主体と保護

開始branch `self/dev-t1n-emit-internal-timing-20261027`、local/remote HEAD `ac7ea83c9bd4a430d4519b71e3331d67c9f4bc88`一致。T1m基底`037d37325b5019ae9c28156ef8cacf6a1828a304`は祖先。隔離worktree `/home/rinsa/work/relay-self-t1n-20261027`を作成し、修正commit `3936390f`を全Worldの起動receiptへ記録した。最終HEAD/remote一致/cleanおよびIssue読み戻しは外部`delivery.json`に保存する。

Windows11 build10.0.26200.9711 / WSL2 Ubuntu24.04、Python3.12.3、Node22.22.2、Java21.0.12.1、Paper1.21.8、Mineflayer4.39.0。system Pythonにはpytestがなく初回コマンド失敗を保存し、以後既存Python3.12.3 venvを絶対パス指定した。

Java PluginソースはT1mから差分0。T1mでJava21ビルド済みの0.2.0-dev JAR（api-version1.21.8）をSHA256照合して再利用したため、今回の再ビルドは不要。bootstrapは既存T1h run-006のJAR/libraries/cache/versionsのみ読み取り、新規Worldを生成した。

Java Plugin SHA256 `7b24265e2a8087b12ff11351ef91d5db21250bce7fd1a220cfcd2e573cf69d81`。

Paper JAR SHA256 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`。

既存single native readerとT1e/S49/T2 ownerを維持。main・Draft #545/#634・S18 freeze・R/V原本・T1h〜T1m原本は変更していない。T1m封印1,711ファイルとsymlinkを開始/終了時に再読一致。

## 修正と検証

- T1n sidecarのopen失敗をnative起動失敗から分離し、従来emit経路を継続。write失敗も元native出力を失わず、欠落・不完全sidecarは後段診断FAILにする。無効なDEV opt-inは引き続き拒否する。
- T1n/T1mの後続記録でprevious-index重複、native評価完了時刻の不一致、complete/emit/diagnostic/next-issueの順序を検査。対応記録がない残余はUNKNOWN（n=0）とし、ゼロを補完しない。
- envelope→既存trace JSON→既存同期write→seq更新→stdout JSON→stdoutの順序とbytesを比較。session/seq/status/wireを維持し、stdoutは1回。通常opt-in OFFのemit本体は維持。
- 各区間分布、emit全体順の上位20件、session/seq/challenge/index/WorldTick/status/A/histogram/CPU/次issue/旧challenge再使用を保存。
- Python focused50 PASS、runner込み52 PASS、FAST637 PASS（T1hの既存27ファイル選択にT1i〜T1nを追加、全41ファイル）。Node22関連79 PASS。Ruff・構文・repository contracts PASS。FULL未実施。
- sidecar open/write失敗・欠落/重複・seq/challenge/status/session不一致・時計逆転・不正ACK解釈・backpressureを単体で検証。実run-002原本のコピー11負対照も期待どおり。欠落native ACK/transport terminal、source失効後の会計凍結は既存FASTのownerテストで検証。これらは新たな物理故障注入の主張ではない。
- 150ms/25ms/2,400challenge/2,300guard、T1f wire、source sequence、既存同期trace方式、M0/P1式を変更していない。

## 全World

|run|条件|元report|会計行|native/T1m/T1n結合|ADMITTED/STALE|実効TPS|cleanup|
|---|---|---|---:|---:|---:|---:|---|
|001|起動入力不備|FAIL|0|0 / 0 / 0|0 / 0|UNKNOWN|元cleanup=false保持|
|002|通常|PASS|1200|1202 / 1202 / 1202|1202 / 0|20.037820|正常|
|003|通常|PASS|1200|1202 / 1202 / 1202|1202 / 0|20.042018|正常|
|004|軽度CPU|PASS|1200|1202 / 1202 / 1202|1202 / 0|20.041574|正常|

run-001は外部runtimeのnode_modulesがsymlinkだったため、bridgeのphysical-root契約がadapter_started前に拒否（Node exit2）。Javaはexit0/PID不在/port再bind。Nodeの正確なPIDとnative terminalは未記録で、元reportのcleanup_complete=false/FAILを保持する。既存launchコードはstartup例外時に子終了をawaitするが、これを欠落したPID原本の代わりにしない。依存先を既存の物理runtime rootへ直し、別output/Worldのrun-002以降で再実行した。起動失敗は鮮度拒否ではなくNATIVE_UNVERIFIED。

正常3Worldは合計3,606 native Paper/3,600会計行、結合率100%。native全seq欠番0、source identity変更0、native観測窓のPaper index/server tick/WorldTick欠測0。各正常shutdownのPaper-only末尾1件はNode受信なしとして別記し、偽のjoinを作らない。未適用の上書きchallengeもT1m reducerが区別する。

run-002の初期にfocused再確認1.06秒を実施した通常ホスト活動を記録している。run-003はテスト並行なし。通常試験を完全idleホストとは主張しない。

負荷条件はrun-004開始前にload-plan.jsonで固定。所有するunpinned Python worker2本、各50ms busy/100ms周期、最大150秒、parent finallyでterminate/wait<=5秒。両worker exit0/PID不在。メモリ圧迫・TPS actuatorなし。T1m run-007と同じworkerソース/条件だが、別World/session/ホスト時刻なので因果的な非干渉比較ではない。

## 分布

時刻はNode同一単調時計/JVM同一単調時計の区間内のみ。以下はms、nearest-rank p95/p99、medianは中央2値平均。Dはchallenge受信→callback先頭、Eはcallback先頭→sendPluginMessage復帰。同じchallenge再使用時のDは古いchallengeからの経過も含む。histogramはpacket単位でなく監視窓の最大値。

|run|指標|n|min|median|p95|p99|max|
|---|---|---:|---:|---:|---:|---:|---:|
|002|Node A|1202|4.790266|49.817495|50.486779|51.800772|97.007942|
|002|JVM D|1202|0.229471|47.805229|48.389426|48.548466|48.879653|
|002|JVM E|1202|0.237840|0.416009|0.914067|1.298329|7.232733|
|002|event-loop窓最大|1202|0.000000|10.194943|10.665983|10.928127|96.468991|
|002|T1→T2 envelope|1202|0.001874|0.003592|0.006737|0.013546|0.238667|
|002|T2→T3 trace JSON|1202|0.008851|0.015446|0.029130|0.040752|0.124150|
|002|T3→T4 既存trace writeSync|1202|0.011165|0.022193|0.045227|0.072198|0.905455|
|002|T4→T5 stdout JSON|1202|0.002789|0.004548|0.012279|0.017970|0.109050|
|002|T5→T6 stdout.write|1202|0.022508|0.041802|0.078807|0.131793|0.217048|
|002|T1→T6 native作業|1202|0.060608|0.088688|0.162591|0.267052|0.977268|
|002|T0→T1 emit前|1202|0.010465|0.015102|0.029637|0.040958|0.323947|
|002|T6→T7 stdout後残余|1202|0.010582|0.020268|0.044458|0.093574|16.376683|
|002|T7→T8 次issue残余|1202|0.031322|0.042530|0.077555|0.108490|0.164234|
|002|T0→T8 次issueまで|1202|0.114961|0.170718|0.312440|0.531936|16.575588|
|002|T1→T7 emit全体|1202|0.071383|0.109779|0.218758|0.377631|16.486832|
|002|CPU user（T6まで）|1202|0.000000|0.086000|0.154000|0.266000|0.592000|
|002|CPU system（T6まで）|1202|0.000000|0.010000|0.074000|0.115000|0.432000|
|003|Node A|1202|6.049925|49.814639|50.460201|51.547931|99.905888|
|003|JVM D|1202|0.354757|47.772862|48.366780|48.532402|48.850643|
|003|JVM E|1202|0.233157|0.420000|0.876822|1.191673|10.669728|
|003|event-loop窓最大|1202|0.000000|10.338303|10.690559|10.838015|85.065727|
|003|T1→T2 envelope|1202|0.001482|0.003494|0.006393|0.014362|0.110291|
|003|T2→T3 trace JSON|1202|0.009748|0.015776|0.030788|0.052580|0.201423|
|003|T3→T4 既存trace writeSync|1202|0.012448|0.023778|0.048750|0.084740|1.151119|
|003|T4→T5 stdout JSON|1202|0.002741|0.004493|0.012158|0.019145|0.075414|
|003|T5→T6 stdout.write|1202|0.023926|0.041369|0.084785|0.123487|0.204498|
|003|T1→T6 native作業|1202|0.062635|0.090782|0.168218|0.269549|1.224170|
|003|T0→T1 emit前|1202|0.010616|0.015652|0.031147|0.043539|0.218473|
|003|T6→T7 stdout後残余|1202|0.011202|0.021201|0.045808|0.073536|0.165930|
|003|T7→T8 次issue残余|1202|0.029224|0.041652|0.076273|0.109320|0.166989|
|003|T0→T8 次issueまで|1202|0.122959|0.174023|0.303426|0.460388|1.307895|
|003|T1→T7 emit全体|1202|0.074473|0.112798|0.211606|0.322575|1.248751|
|003|CPU user（T6まで）|1202|0.000000|0.091000|0.163000|0.239000|0.426000|
|003|CPU system（T6まで）|1202|0.000000|0.000000|0.092000|0.148000|0.311000|
|004|Node A|1202|4.994120|49.829340|50.496194|52.561186|110.324901|
|004|JVM D|1202|0.333539|47.915522|48.492125|48.716388|97.990999|
|004|JVM E|1202|0.194179|0.388441|0.719599|1.044017|12.243676|
|004|event-loop窓最大|1202|0.000000|10.190847|10.625023|10.788863|74.055679|
|004|T1→T2 envelope|1202|0.002010|0.003431|0.005154|0.015867|0.132249|
|004|T2→T3 trace JSON|1202|0.009301|0.014857|0.023985|0.036645|0.079666|
|004|T3→T4 既存trace writeSync|1202|0.012466|0.022836|0.039862|0.073459|58.896873|
|004|T4→T5 stdout JSON|1202|0.003106|0.004651|0.007706|0.019353|0.040977|
|004|T5→T6 stdout.write|1202|0.020327|0.040254|0.056343|0.073020|0.113460|
|004|T1→T6 native作業|1202|0.059702|0.087576|0.126048|0.167127|59.013598|
|004|T0→T1 emit前|1202|0.009305|0.015716|0.025517|0.039413|0.227036|
|004|T6→T7 stdout後残余|1202|0.010611|0.017947|0.033750|0.047472|0.096653|
|004|T7→T8 次issue残余|1202|0.027664|0.039930|0.057396|0.078738|0.178048|
|004|T0→T8 次issueまで|1202|0.109864|0.165025|0.223835|0.294997|59.189213|
|004|T1→T7 emit全体|1202|0.070950|0.106664|0.154473|0.205289|59.091475|
|004|CPU user（T6まで）|1202|0.000000|0.088500|0.126000|0.160000|0.343000|
|004|CPU system（T6まで）|1202|0.000000|0.000000|0.070000|0.107000|0.175000|

実効TPSは最初の会計baseline→最後の会計snapshotのWorldTick差/JVM paper_ns差。次表はnative隣接source間隔ごとの実効TPS分布であり、catch-up短間隔で最大が高くても高TPS actuatorを意味しない。

|run|n|min|median|p95|p99|max|
|---|---:|---:|---:|---:|---:|---:|
|002|1201|19.657076|20.001998|20.093196|20.189235|258.081100|
|003|1201|19.655739|20.000614|20.080132|20.180197|219.192062|
|004|1201|19.015424|20.001573|20.077461|20.224690|259.070915|

## 外れ値と解釈

run-004: session `afb11e30-0533-4a4d-a429-313005795594`、native seq591、Paper index561、WorldTick1571、challenge `bb95f7679342be4e2d5f37e4b5cce461:561`、元status ADMITTED。T0→T1 0.014164、envelope0.003638、trace JSON0.013153、既存trace writeSync58.896873、stdout JSON0.040977、stdout.write0.058957、stdout後残余0.077877、次issue残余0.083574ms。評価完了→次issue59.189213ms。58.896873msはemit全体の約99.67%。

そのemitのCPU user/system0.198/0ms（process-wide、T6まで。T1→T6壁時計59.013598ms）。この差は呼出し区間でCPUを使い続けた証拠ではないが、CPU差分だけでdisk/GC/schedulerを識別できない。CPU計測はT1前の初回cpuUsage取得→T6直後までで、T6→T7診断残余は含まない。

次index562は旧challenge561を再使用しA110.324901ms。index563はchallenge563へ進みA39.036314ms。150msを超えず既存ADMITTEDのまま。全3Worldの旧challenge再使用は1/1/2件で、各Worldの最初のcatch-up1件と、run-004の当該停止後1件。上位20にはそれぞれ後続tick再使用の有無を保存。

当該snapshotのhistogram窓最大は10.158079ms。これは個別58.897ms停止を捉えた値ではない。reset/サンプリング窓の死角があり、histogramが小さいことを停止不在と解釈しない。T1mのhistogramをpacket遅延へ変換せず、異種時計の直接減算もしない。

run-002の最大emit16.486832msはT6→T7残余16.376683msに集中。既存trace write0.049909ms、stdout.write0.036945msで、こちらを既存trace停止と読み替えない。T6以前のCPU0.114/0msではこの残余の原因を論じられない。残余はT1n diagnostic JSON/write、CPU差分取得、return等を含む。run-003最大emit1.248751msは既存trace write1.151119ms。

各Worldのtop20原本照合付き一覧は外部run-NNN-top20.json、要約は同名JSONのworlds.*.emit_join.largest_emit_events。run-004-stall-context.jsonに前後6tickのnative/T1m原本を保存。stdout.write falseは全3Worldで0。falseの単体/コピー負対照はbackpressure1として記録するだけでPython受信ACKへ昇格しない。

## T1mとの比較

|系列|A median / p99 / max ms|評価完了→emit復帰 max ms|
|---|---|---:|
|T1m 005 通常|49.842624 / 51.834451 / 106.712237|1.165432|
|T1m 006 通常|49.846071 / 53.077773 / 103.721960|52.418903|
|T1m 007 軽度CPU|49.852148 / 52.162191 / 108.671337|57.706166|
|T1n 002 通常|49.817495 / 51.800772 / 97.007942|16.499377|
|T1n 003 通常|49.814639 / 51.547931 / 99.905888|1.263576|
|T1n 004 軽度CPU|49.829340 / 52.561186 / 110.324901|59.105639|

中央値の近さは非干渉の証明ではない。T1nの追加hrtime/cpuUsage/sidecar JSON/同期write自体にも観測コストがある。T1mの52.418903/57.706166msはT0→T7、今回59.091475msはT1→T7なので、境界差も維持する。過去T1mのemit内部区間は依然UNKNOWN。

## 会計・Action・cleanup

全正常Worldは会計行1,200、合計3,600。各World最終仮想E=10.680000000000945、基礎cost1.2＋L0認知cost0.12、移動cost/intake/食事credit0。全行既存cost和とexpenditure一致、P1 fatigue/recovery0、P1-qualified WAIT=false。M0/P1式未変更のため#626への重複報告なし。

各WorldでMOVE/EAT/STOP/Resume/Action effect/Motor effect/LLM/TPS actuator0。静止距離0やinput_idleをP1-qualified WAITへ読み替えない。正常3WorldはJava/Node exit0、shutdown_ackとconnection_end、記録PID不在、port再bind、Paper全dimensions保存をそれぞれ確認。高水準S49 STOP ACKは未発行・未検証。run-001の不完全native cleanup記録は前述どおり保持。最終独立scanでは本worktree bridge残存0、port再bind成功、負荷worker残存0。

## 原本保存

原本root `/home/rinsa/work/t1n-evidence-20261027`。全4新規Worldを保持。native.jsonl、paper.log、node_timing、t1m_node_timing、t1n_emit_timing、python_timing、report/source_hashes、t2_ticks/checkpoints、World全ファイル、起動argv/env/HEAD/diff/全source hash、JAR SHA、ホストログ、テストログ、外れ値を保存。起動前失敗run-001には存在しないnative/sidecar原本を捏造していない。

originals-manifest.json: **865ファイル再読一致**、SHA256 `075e8b16c8c278b91413e938501a83302429fcc561e1dc26b2e77b627ffbef99`。各正常Worldのsource_hashes全件と実ロードJARを別照合。manifest対象の原本/reportは以後変更しない。最終delivery/Issue readback/全証拠sealは外部rootに追加する。

T1m seal SHA256 `50be087171516a921e3c150f343fc97b11e551fc4edf8c6ed5214eb425f2d0e9`（1,711ファイルとsymlink、前後一致）。

## 確定事項と次段階

確定した処理区間は、今回run-004の既存同期trace writeSync呼出し58.896873ms。根本原因のdisk/GC/OS schedulingはUNKNOWN。stdout復帰はPython受信ACKではなく、JVM E終点もNode受信ACKではない。

次の最小変更候補は、既存同期trace writeSyncとT1n診断残余を対象に、同一Node時計でNode GCイベント・OS scheduler/対象fdの待機証拠を受動照合すること。まず約59msをI/O待機/スレッド非実行/GCに区別できる証拠を増やし、同期traceの非同期化等は別の測定根拠付き変更として判断する。histogramのreset死角も別の受動timer原本で検査する。

今回の資格判定はQUALIFICATION_NO_GO / SCIENCE_NOT_RUN。独立source認証、R/V、全subtick静止、P1-qualified WAIT、長時間自律性はNATIVE_UNVERIFIED。実source拒否は今回未観測であり、NATIVE_SOURCE_REFUSAL_OBSERVEDを今回Worldへ付けない。FULL/main mergeなし。

Issue #150（emit/source因果年齢）、#627（Physical Control時間境界）、#537（Self統合）、#616（会計連続性）へ報告し本文を読み戻す。最終URL/本文一致確認は外部issue-readback.json。
