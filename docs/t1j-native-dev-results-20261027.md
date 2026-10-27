# T1j 明示再認可・World再観測・安全なAction再開 — 2026-10-27

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
実Minecraftの正常系列は2 World、2 PASS / 0 FAIL。故障組合せはoffline検証であり、
実Worldでの故障検証は **NATIVE_UNVERIFIED**。

対象branch `self/dev-t1j-explicit-resume-20261027`。
開始local/remote `d54c0d2c390cdb9f2cd5ab2d633dc97dc1a8a499`、
T1i `0c77688ade3e028aead023d1454375e9dda5a4f5` の祖先関係を確認。
mainのclean treeを保ち、`/home/rinsa/work/relay-self-t1j-20261027` に隔離worktreeを作成。
実装修正commit `56cbae622fd0bb7c2b54df2827a30fd2eb93278f`。
試行subject.jsonは開始HEADとその時点のsource diffを保持する。run-002の実装はこのcommitと同じ。

証拠root: `/home/rinsa/work/t1j-integration-evidence-20261027`。
数値・session/World ID・STOP ACK・再観測・会計は
[測定JSON](t1j-native-dev-results-20261027.json) に記録した。

## 検証と修正

Python 3.12.3（既存 `/home/rinsa/relay-self-s60b1-venv/bin/python`）:
指定focusedは初回70件通過。補強後の指定6ファイルは77 PASS、
最終は追加実行故障テストを含め **93 PASS**。
FASTはT1hの27ファイル選択にT1i/T1jを追加し、最終 **553 PASS**。
選択リストは外部rootの `fast-selection.txt`、結果は `focused-final-003.log` と
`python-fast-final-003.log`。FULLは実行していない。
Node v22.22.2 `node --test adapters/mineflayer/*.test.mjs`: **68 PASS**。
Java/Javac 21.0.12.1、Maven 3.9.11のPlugin build: **BUILD SUCCESS**。
Ruff関連ファイル、repository contracts、git diff --checkも通過。

実装確認で次を補強した。安全条件・150ms上限・M0/P1式は変更していない。

- 再観測Paperのbootを凍結前bootに結合。nativeの位置とhealthもPaperに照合。
- 負のcausal age拒否。native probe欠落を明示拒否。
- 過去reportのAction/effect IDを収集し、新MOVEとclear IDの衝突を拒否。
- 旧ledgerの全行・最終energy/fatigue・既存credit IDを新区間と別に保存。

テストの期待値をPASS目的で変更した箇所はない。native probe fixtureには、
新しい位置・health整合条件のため実インターフェースに存在する値を追加した。
Java初回はシステムがJREのみでrelease 21未対応compilerを選択し失敗、
2回目は指定javac不在で失敗。両ログを保持し、既存の完全なJDK21資産
`/home/rinsa/work/s50-p1-flat-native-evidence-20261017/jdk21/runtime` で成功。
実World・Python/Nodeの失敗試行はない。

## 同一World/session内の実系列

両Worldで MOVE×2 OUTCOME → cooked_beef EAT OUTCOME → 第3MOVE中STOP →
元S49のclear ACK → Paper 8静止transitionの限定DEV STOP ACK → 別のCLI明示再認可 →
Paper→native→Paper → 新Action `t1j-T1J-R1-move` → OUTCOME → clear・後続静止が成立。
真正EATはfood 18→20、cooked_beef 3→2、consume送信1回、credit 1回。
第3MOVEは意図したSTOPによりFAILED / Supervisor UNKNOWNとなる。
旧STOP ownerはlatchedのまま、新ownerのみを使用。native reader・Motor writer・
Supervisor・Executorは既存経路を維持した。

| 試行 | 凍結WorldTick | Paper→native→Paper source seq | Paper WorldTick | 新基準 | 会計未観測tick | 新MOVE実距離 | 新会計tick |
|---|---:|---|---|---:|---:|---:|---|
| run-001 | 1374 | 459→460→461 | 1393→1394 | 1394 | 19 | 0.626906573m | 1395–1412: 18 |
| run-002 | 1372 | 461→462→463 | 1390→1391 | 1391 | 18 | 0.832291182m | 1392–1409: 18 |

run-001 Paper server tick 395→396、causal age上界50.569430 / 49.075597ms。
run-002は392→393、49.464761 / 50.030575ms。
native probeにPaper WorldTickを捏造していない。上界は同じNode時計に基づき、
Python・Node・JVM時計の直接減算をしていない。

Action/effect ID重複0、permit再利用0、旧ACK流用0。
各Worldのset_controlは計4回、再開MOVEは1回のみ。追加ActionもEAT再発行もない。
ACKだけで成功扱いせずnative位置差・Supervisor OUTCOME・後続静止を確認した。

## 会計とclaim ceiling

旧ledgerはfailed/frozenのまま保持され、全行と最終値がSTOP時の値に一致。
run-001の最後に確認した仮想energy=15.621275321043846、fatigue=0.0052093432652756365。
run-002はenergy=15.620175321043847、fatigue=0.0052093432652756365。
credit ID `t2-native-meal` を保持し、新区間の追加intake=0。
停止中の会計未観測tickは `新基準−旧最終tick−1`。
STOP中のraw観測が存在しても旧会計consumerは無効であり、後からtickを補完していない。

新区間は新基準より後の連続した18 tickのみを会計し、旧ledgerに追記していない。
基準へのcarryでenergy/fatigueを回復させず、欠測基礎代謝・距離・WAIT回復・UNKNOWN EAT
の遡及入金は0。Minecraftの物理代謝は継続しており、停止期間の実コストはUNKNOWN。
新区間のWAIT_DEV回復は観測された後続tickに限り、P1 qualified WAITではない。

## 負対照とcleanup

offline統合故障注入12件: 再開MOVEのACK欠落・旧Action ACK・MOVE中断線はUNKNOWN、
set_control1回・clear1回・再試行0。再認可なし、STOP ACKなし、native欠落、stale、
food不一致、control未解除、危険、別session、未知EAT pendingはAction/Motor発行0。
純粋gateテストで使用済みpermit、重複再認可、旧STOP ID、Action/clear effect ID衝突、
World/Player/boot・入力・位置不一致、source順序、150ms境界も拒否。
会計テストは欠測・新区間再利用を拒否。これらをNATIVE VERIFIEDとは呼ばない。

Java/Node cleanup **2/2**。各試行でshutdown_ack、connection_end、exit 0、
PID消滅、port 25565再bindを個別確認。transport閉鎖を高位STOP ACKと混同しない。
各新規Worldのserver/とnative/commands/Paper/Python/Nodeログ、report、会計JSON、
source_hashesを保持し、両試行の記録済みSHA256を読み戻して一致確認した。
既存Worldは起動せず、bootstrapのcache/libraries/versionsだけをコピーした。
main・Draft #545/#634・S18 freeze・R/V原本は変更していない。

使用資産: Paperは既存T1h run-006/t1h_input_residual/server/paper.jar、
bootstrapは同server（World本体はコピーしない）。Pluginはこのworktreeでビルドしたもの。
生成物は終了後、外部rootのgenerated-build-and-cacheへ退避した。

次段階は、今回offlineで拒否した故障組合せの必要範囲を新規DEV Worldで独立検証し、
長時間のsource連続性と再開後の会計を評価すること。
R/V資格、full-tick静止、native source独立認証、実身体の停止期間コスト復元、
高TPS、継続的自律行動・モデル認知・科学的有効性は未成立。FULL/main mergeは未実施。
