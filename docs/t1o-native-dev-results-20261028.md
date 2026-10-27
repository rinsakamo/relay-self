# T1o 同期trace通常OFF・実Minecraft DEV A/B結果 — 2026-10-28

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

新規使い捨てWorldをOFF/ON各1個、合計2個実行し、両方PASS。追加反復なし。通常DEVの既定値OFFを維持する。OFFでは実Node環境にtrace変数なし、`node_timing.jsonl`なし。未変更bridgeの`paperTraceFd=null`とwriteSync guardから、既存同期trace書込みが通常DEV経路から外れることを確認した。追加のper-call計測は導入していない。

## ソースと環境

branch `self/dev-t1o-trace-optin-ab-20261028`、開始local/remote HEAD `388da75d19c8d011491bc628996bfcf71979d2de`一致、T1n `9e5b98e5379cf89efb86dabe2383c94fd536993e`は祖先。隔離worktree `/home/rinsa/work/relay-self-t1o-20261028`。修正をcommitしたcleanなruntime HEAD `36d05b58`で両Worldを起動。最終HEAD/remote/cleanは外部`delivery.json`へ保存する。

Python3.12.3 venv `/home/rinsa/relay-self-s60b1-venv/bin/python`、Node22.22.2、Java21.0.12.1、Mineflayer4.39.0、実Paper1.21.8-60。物理runtime root `/home/rinsa/work/t1e-integration-evidence-20261026/node-runtime`の実directory依存を使用。T1hの既存bootstrapからJAR/cache/libraries/versionsのみコピーし、Worldは再利用していない。

Plugin SHA256 `7b24265e2a8087b12ff11351ef91d5db21250bce7fd1a220cfcd2e573cf69d81`。Paper SHA256 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`。Java Pluginソース差分0、既存Java21ビルド品を照合して使用、再ビルドなし。

## 比較

同一T1l source-only・通常ホスト負荷・各1200 ticks、追加CPU workerなし。計画した差はtrace設定のみ。World/session/identity/開始時刻は独立している。ageは元native内の同一Node時計による因果年齢上界A（片道遅延ではない）。

|指標|OFF run-001|ON run-002|
|---|---:|---:|
|結果|PASS|PASS|
|会計WorldTick|1200|1200|
|native Paper|1202|1202|
|ADMITTED / STALE|1202 / 0|1202 / 0|
|native seq欠番 / WorldTick欠測 / identity変更|0 / 0 / 0|0 / 0 / 0|
|age median ms|49.936729|49.888075|
|age p95 ms|50.729916|50.789936|
|age p99 ms|52.224219|52.634792|
|age max ms|83.152740|112.135503|
|150ms以上|0|0|
|実効TPS|20.037480|20.045221|
|同期traceファイル|不存在|存在・1202行完全一致|
|native.jsonl|存在|存在|
|M0最終エネルギー|10.680000000000945|10.680000000000945|
|P1 fatigue / recovery|0 / 0|0 / 0|
|Action / effect|0 / 0|0 / 0|
|cleanup|PASS|PASS|

各Worldのnativeは1,267行、seq連続、単一session/boot/world/player。native Paperのindex/server tick/WorldTickは全1202件連続。1200会計行はbaselineの次WorldTickから連続し、snapshotが余分に2件あるのはbaselineと末尾観測による。Paper-only shutdown末尾各1件（OFF server tick1218、ON1214）はNode受信なしとして記録し、欠測を補完・joinしていない。会計窓とnative観測窓の欠測は0。

ONはtraceとnativeの対応対象1202件すべてでsession/seq/type/payloadが完全一致。Node単調timestampの存在・形式・順序を確認。OFFは元nativeでsource/ADMITTED/age/Actionを集計し、legacy Node trace専用遅延は未計測・UNKNOWN。source欠落とは扱わない。実効TPSは会計baseline→最終snapshotのWorldTick差を同一JVM `paper_ns`差で除した値。異種時計を減算していない。

## 会計・cleanup・保護

両Worldとも基礎cost合計1.2、L0認知cost0.12、移動cost/intake/credit0。全行で既存M0 cost和とexpenditureが一致。P1全行fatigue0、recovery合計0。MOVE/EAT/STOP/Resume/Action effect/Motor effect/LLM/TPS actuatorはすべて0。commands原本はshutdownのみ。P1-qualified WAIT=false。

両Worldでshutdown_ack、connection_end、Node/Java exit0、記録PID不在、独立port再bind、Paper全dimensions保存を確認。高水準STOP ACKは発行・証明していない。main・Draft #545/#634・S18・R/V・過去Worldを変更しない。T1n seal990ファイルとsymlinkを前後再読一致、seal SHA256 `c0633460fe521a84a3340d313ee13beb3216afddf946cf6f9fddb8218fd7db9e`。

## 修正・検証

開始focused47 PASS。trace破損JSONがmeasure()を例外終了させ、診断FAILのreport保存を中断し得る不具合を修正。不一致traceも元nativeへ戻し、件数・元STALEを保持したまま独立auditでFAILにする。環境変数削除/絶対パス設定をhelper化してテスト。trace欠落/重複/seq/session/status/payload不一致/時計欠落・逆転・不正型/OFF残存/ON不在、元STALE非昇格を確認。

修正後Python3.12 focused82 PASS、FAST667 PASS（継承41ファイル＋T1o、計42ファイル）、Node22関連79 PASS、Ruff・AST構文・repository contracts PASS。合成原本コピー9負対照をファイル保存して全件期待どおり拒否。過去T1n run-002をmeasure(root,{})でread-only再解析し1202 ADMITTED一致。FULL/R/V資格実行/SCIENCE/main mergeなし。150ms/25ms/2400challenge/2300guard・wire・admission・latch・M0/P1式・Motor/STOPと単一reader所有権は不変。

World試行失敗は0。外部reducerの初回実行だけPYTHONPATHにrepo root不足でimport失敗し、ログを保存。外部解析に`.`を追加してread-only再実行した。World再実行や原本reportの書換えはしていない。

## 原本と結論

原本root `/home/rinsa/work/t1o-evidence-20261028`。native/commands/python_timing/paper.log、ON node_timing、report/source_hashes、t2_ticks/checkpoints、全Worldファイル、起動argv/env/HEAD/diff/source hashes/JAR SHA、実process cmdlineとenv、ホストログ、テスト/負対照/比較結果を保存。originals-manifest.json **416ファイル再読一致**、SHA256 `9aa1a4166b2563212df3a4c8e66477df9127cdf1aeb6ca448d58d0b615265d38`。最終delivery/Issue readback/全証拠sealを追加保存する。

確定事項はOFF時の既存同期trace書込み除外と、source・1200連続会計・M0/P1・cleanupの実World成立。各1Worldでは遅延分布改善や外れ値発生率を統計的に確証できない。今回のmax差をtraceの因果効果とはしない。T1nの59ms停止がすべて解消したとの主張なし。disk/GC/OS scheduling根本原因、片道遅延、OFFのtrace専用時計はUNKNOWN。独立source認証・P1-qualified WAIT・長期自律性は今回の成立範囲外。

次の最小開発項目は、通常DEVでOFF既定を維持し、タイミング診断時だけ明示ONを選ぶ運用の継続。新しい計測機構やGC/OS原因調査は今回追加しない。Issue #150/#627/#537/#616へ報告・読み戻し、モデル式未変更のため#626重複報告なし。
