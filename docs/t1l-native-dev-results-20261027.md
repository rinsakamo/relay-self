# T1l 実Minecraft source・M0/P1連続性 DEV 結果 — 2026-10-27

**DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。150ms上限、25ms評価budget、2,400 challenge、M0/P1式は変更していない。

専用branch `self/dev-t1l-source-continuity-20261027`。開始HEAD `1cb5b982aaa52117c32abda667ec0a889d5b26a9`、T1k基底 `2efabc7b901189418ac99e3a0ce37661568ccd35` の祖先関係を確認。main checkoutは変更せず、新規worktree `/home/rinsa/work/relay-self-t1l-20261027` を使用した。最終commitはGit履歴および外部 `delivery.json` に記録する。

原本root: `/home/rinsa/work/t1l-evidence-20261027`。各runは独立の新World。bootstrapからcache/libraries/versions/JARのみコピーし、既存Worldを再起動・上書きしていない。

## Python・Node・Java

Python 3.12.3 (`/home/rinsa/relay-self-s60b1-venv/bin/python`)：指定focused **50 PASS**、runnerを含む拡張focused **52 PASS**、既存FAST選択37ファイル＋T1l 2ファイル **615 PASS**。初回focused 36 PASS、初回FAST 604 PASSも保持。テスト期待値の緩和なし。Node 22.22.2 **68 PASS**、Java 21.0.12.1 **BUILD SUCCESS**。FULL未実施。

## T1k原本の読み取り専用切り分け

A=received−challenge_sent、B=evaluation_start−received、C=evaluation_completed−evaluation_start。すべて同じNode単調時計。Aはchallenge往復・Paper callback・Node受信前待機の複合区間であり、片道通信遅延ではない。

|原本|n|age中央値/p95/p99/最大 ms|A最大 ms|B最大 ms|C最大 ms|
|---|---:|---|---:|---:|---:|
|run-004|417|49.903228/51.214777/60.615432/118.300402|118.263552|0.284027|0.250410|
|run-006|19|49.757450/199.451933/199.451933/199.451933|199.379200|0.442985|0.286261|
|run-009|364|49.930169/52.175673/490.659087/490.986310|490.971118|0.440983|0.264446|

各最大値は同一フレームとは限らない。A/B/Cそれぞれのn・min・median・p95・p99・max、challenge IDと前8/後8フレームは同梱JSONに保持（percentileはnearest rank、medianは中央2値平均）。

run-006初回拒否：seq 10 / index 6 / server tick 18 / WorldTick 1016、A=191.076364、B=0.066953、C=0.137482ms。challenge `baaac1b41595b89968e3a5043ab27855:6`。
run-009初回拒否：seq 421 / index 356 / server tick 368 / WorldTick 1366、A=488.270247、B=0.026227、C=0.054042ms。challenge `5dfb5545ca813d0bc1845c44bb869444:355`。どちらも `STALE / CAUSAL_AGE_UPPER_BOUND_EXCEEDED`。

run-006はADMITTED 5 / STALE 2 / UNDETERMINED 12、run-009は355 / 8 / 1。Node側は原本観測を続けたが、拒否後のADMITTEDは0。source latchを解除していない。run-004は417件すべてADMITTED。

**確定した切り分けはAへの集中まで。根本原因はUNKNOWN。** B/Cは小さく、Node評価の25ms超過では説明されない。Paper callback、通信、Node callback配送前、OS schedulingのどれかを原本だけで特定できない。T1k当時の同時実行プロセス・Windowsホスト負荷の原本は未取得。ファイル更新時刻を同時負荷の証拠にしない。

## 新規実World — 3試行

|試行|対象|結果|baseline→会計WorldTick|native全seq|Paper index|入金/effect|checkpoint逐次保存|
|---|---:|---|---|---|---|---|---|
|run-001|1200|PASS|1034 → 1035–2234|0–1289|1–1221|0 / 0|0|
|run-002|1200|PASS|1011 → 1012–2211|0–1266|1–1202|0 / 0|6|
|run-003|2000|PASS|1011 → 1012–3011|0–2107|1–2003|0 / 0|10|

run-001は旧起動待機後のbaselineで1,200行PASSした初回原本。最初のPaper snapshotではなくWorldTick 1034から会計を始め、checkpointはreport内のみだったため、最終仕様の証拠はrun-002/003を採用する。原本のPASSをFAILへ書き換えていない。

run-002/003はspawn直後から単一readerでbaselineを取り、baseline会計0。連続source seqの監査はPaperだけでなく、effect/observation/shutdownを含むnative journal全体を対象とした。native欠番・重複0、Paper index/server tick/WorldTick欠測0、session/boot/world/playerの変更0。Paper seq間には通常observationがinterleaveするため、Paperだけのseq差を欠測と判定しない。

|試行|全Paper n|age median/p95/p99/max ms|A/B/C最大 ms|Paper実測秒/TPS|source由来challenge消費/残余|
|---|---:|---|---|---|---|
|run-001|1221|49.894786/50.694849/52.714346/106.355669|106.228781/0.486351/0.418517|59.997567134/20.000811|1222 / 1178|
|run-002|1202|49.901600/51.252200/52.469644/96.767654|96.553756/0.412658/0.250092|59.860886760/20.046479|1203 / 1197|
|run-003|2003|49.898139/50.639469/51.473581/80.661213|80.541359/0.495189/0.314268|99.901208286/20.019778|2004 / 396|

全Paper nには会計完了後shutdown drainで受信したADMITTEDも含む。challenge消費数は「login時1回＋各受信snapshot後1回」を凍結ソースと原本件数から再構成した値であり、独立した送信timestamp計測ではない。echoされたchallenge IDの範囲は各runで`:1`～`:1221`、`:1202`、`:2003`。2,000tick試験の開始予算投影はbaseline index 1＋2,000＋次発行1＝2002、終了drain込み2004、cap残396、停止境界2300への残296。cap延長・session再生成・counter巻戻しなし。

TPSはbaselineと最終会計snapshotの同一JVM `paper_ns` 差から算出。Node受信側TPSもJSONに別記し、JVM/Node/Python時計を引き算しない。PaperがNode切断後に記録した終端tail tickはJSONに明記し、観測会計区間の欠測へ混入させない。

## session custody

- run-001: session `dfaeba63-7136-492b-9ae2-792b6a8777c9`、boot `4f58d07d-1208-48de-a3d0-0f038579facf`、world `313322b4-15f5-41db-a920-6dc41257876c`、player `dcae346d-e66f-331a-b459-a5a5370e9738`。
- run-002: session `bbe5e5e7-a3e8-4d6c-8237-18b46f1bf89b`、boot `c09a883d-378f-4029-9bee-d56265993c5b`、world `a5d65280-b90c-42fa-b8c6-a932f5f2daad`、player `dcae346d-e66f-331a-b459-a5a5370e9738`。
- run-003: session `5185312d-c8cc-4e13-b7fc-78c5fdcf5e77`、boot `f4cb35e2-b85e-4f72-a431-8988497bce76`、world `97f006eb-218d-451f-bf25-d67281e543b3`、player `dcae346d-e66f-331a-b459-a5a5370e9738`。

## M0/P1・物理境界

run-002：1,200行、M0最終E=10.680000000000945（初期12、基礎1.2＋L0認知0.12）。run-003：2,000行、E=9.800000000001575（基礎2.0＋L0認知0.2）。各行のexpenditureと既存計算を照合。L0 work unitは各tick 1、移動cost 0、食事credit 0、intake 0。P1 fatigueは両方0、recoveryも0。距離観測0の既存式による連続更新であり、回復証明ではない。

MOVE/EAT/STOP/Resume/Action effect/LLM/TPS actuatorすべて0。`MOVE_OR_UNDETERMINED`を維持し、全subtick静止・P1-qualified WAIT・Physical Control資格を認定しない。仮想会計とMinecraft物理代謝は別。M0/P1式、T2式、Node admissionとJava Pluginソースには変更なし。#626への重複報告なし。

## fail-closed・cleanup・原本

今回の新実Worldは3/3でage/source拒否なし（native FAIL原本0）。source失効時の主張は、T1k実原本の拒否/latchとT1l offline負例に限定する。4種非ADMITTED、欠測、拒否後更新、2,300境界、2,400への境界拡張拒否、偽ADMITTED、異種identity、native gap/duplicate/interleave、checkpoint後の欠測保持を検査。新Worldで失効注入したとは報告しない。

3/3でJava/Node exit 0、native shutdown_ack＋connection_end、PID不在、25565再bind。Paper logのStopping serverとAll dimensions are savedも独立に確認。transport ACKは高水準STOP ACKではない（STOP自体0）。

各runのnative.jsonl、paper.log、Node/Python timing、commands、report、source_hashes、Worldを保持。200tick checkpointはrun-002で6、run-003で10を逐次保存し、reportと一致。起動argv/env/コードhash/diffはrun-*-launch.json、WSL負荷はrun-*-host.jsonl。T1kの3原本は既存manifest全21ファイルのSHA256一致。新3原本は既存manifest全項目を再計算一致し、World全ファイルもrun-*-world-hashes.jsonへ保存・再読照合する。

実機失敗はなかった。補助スクリプトの初回PYTHONPATH不足とreducerのEnergyTransition.before誤参照は修正し、execution-notes.mdに残した。原本契約に合わせてreducerを直し、原本・モデル式・テスト期待値を変更していない。

## 次段階・未成立条件

観測できた1,200/2,000tickのsourceと仮想会計の連続性のみ成立。長時間自律性、動作中の安定性、全subtick静止、R/V、科学的成功は未成立。次段階はA区間内のNode event-loop/JVM callbackの最小DEV計測と再現性の検査。2,400を超える寿命は独立したversioned protocol/owner lifecycle課題とし、今回のcapを変えない。main merge、Draft #545/#634、S18 freeze、R/V World、T1h～T1k原本は変更しない。

GitHub報告先は #150 / #627 / #537 / #616。最終commit/pushと投稿本文のreadbackは外部delivery.json・issue-payloads.jsonに記録する。
