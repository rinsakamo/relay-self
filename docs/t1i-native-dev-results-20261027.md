# T1i — 通常multi-epoch / EAT STOP 実Minecraft DEV結果（2026-10-27 JST）

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

専用branch `self/dev-t1i-self-stop-eat-20261026`。
開始remote HEAD `8a1b23aaa01b15cadc8f7f5f94d4bd05934139d8`、T1h
`2531ba0a08ac77aca79f4d939122784e8556f3e5` の祖先関係を確認。
source commit `485ac98fc77542bf7dc44bed61d94ab97c1031f4`。
主checkout `/home/rinsa/relay-self` はcleanなmain `32fe105fc12cbf54abd11bfba7c8a75d319939df`
のまま保持し、`/home/rinsa/work/relay-self-t1i-20261027` に隔離。
main、Draft #545/#634、S18 freeze、過去DEV・R/V原本の変更なし。merge/FULLなし。

## 検証と変更

Python 3.12.3 focused **78 PASS**、既存T1h FAST選択482件にT1i21件を足した
FAST **503 PASS**。Node v22.22.2 `node --test adapters/mineflayer/*.test.mjs`
**68 PASS**。Java/Javac 21.0.12.1、Maven3.9.11、Paper plugin **BUILD SUCCESS**。
Ruff・repository contracts確認。GitHub CI成功の主張ではなくローカル検証。

既存S49 Executor/Supervisorと単一native receiver、同じS49DevStopOwnerを維持。
EAT receiptのforeign sessionを即時拒否。STOPで既存DEV tick会計consumerを凍結し、
STOP時点のticks/energy/fatigue/creditsと終了時の完全一致を検査する。
原native/Paper streamは保持したまま、同じ受信所有者が12回・全体5秒以内の
read-only correlated probeを行う。新Motor issuer・reader・plugin・resume APIなし。
STOP後はUNKNOWN/ラッチを維持し、古いACKで再開しない。

## 全World履歴

**13 World：PASS 12 / FAIL 1**。
全試行 `--loop-moves 2`、毎回新規絶対outputと新World/session。

| 原本 | report | STOP境界 | 正常MOVE | UNKNOWN | consume | M0 credit | passive food |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| run-002/t1i_stop_eat | PASS | consume_wait | 2 | 1 | 1 | 0 | None → None |
| run-002/t1i_stop_loop | PASS | MOVE | 2 | 1 | 1 | 1 | None → None |
| run-003/t1i_stop_eat | PASS | consume_wait | 2 | 1 | 1 | 0 | 18.0 → 20.0 |
| run-003/t1i_stop_loop | PASS | MOVE | 2 | 1 | 1 | 1 | 18.0 → None |
| run-004/t1i_stop_eat | PASS | before_equip | 2 | 1 | 0 | 0 | 18.0 → 18.0 |
| run-005/t1i_stop_eat | PASS | after_equip | 2 | 1 | 0 | 0 | 18.0 → 18.0 |
| run-006/t1i_stop_eat | PASS | consume_send | 2 | 1 | 1 | 0 | 18.0 → 20.0 |
| run-007/t1i_stop_eat | FAIL | after_receipt | 0 | 0 | 0 | 0 | None → None |
| run-008/t1i_stop_eat | PASS | after_observe | 2 | 1 | 1 | 0 | 18.0 → 20.0 |
| run-009/t1i_stop_eat | PASS | consume_wait | 2 | 1 | 1 | 0 | 18.0 → 20.0 |
| run-010/t1i_stop_eat | PASS | after_receipt | 2 | 1 | 1 | 0 | 18.0 → 20.0 |
| run-011/t1i_stop_eat | PASS | consume_wait | 2 | 1 | 1 | 0 | 18.0 → 20.0 |
| run-011/t1i_stop_loop | PASS | MOVE | 2 | 1 | 1 | 1 | 18.0 → None |

`None`は欠測（NATIVE_UNVERIFIED）であり、0や食事未完了を意味しない。
run-002は初期実装の基準観測で、STOP会計凍結と追加受動観測の証拠を持たない。
修正版run-003以降のSTOP成立試行では会計凍結を確認。
run-007は開始時にPaper causal age **238.182849 ms**が既存150ms上限を超過し、
SESSION_LATCHEDでAction開始前に拒否。Action0・入金0・cleanup成功のFAIL原本を保持。
上限は変更せずrun-010の新Worldで同じafter_receipt境界を再試験。

## T1i-A 通常Selfループ

同じWorld/session内でPaper ADMITTED → 正常MOVE2 OUTCOME → 本物の空腹/Inventory
から既存EAT1 OUTCOME/入金1 → 後続Paper → 第3 MOVEを元SupervisorがISSUED →
同じSTOP ownerへ要求 → 元Executorのclear_controls1/対応ACK → 独立Paper marker →
後続8静止遷移 → 稼働中ownerの限定DEV STOP ACK。
中断MOVEはFAILED / Supervisor UNKNOWN。STOP後の次Actionは0。
clear ACKとshutdown ACKは別物で、STOP ACKは8連続callback静止の範囲のみ。
最終run-011：要求→clear ACK **18.083442ms**（同一Python単調時計）。
Paper静止窓はserver tick **382–389**、marker後の観測経路 **0.049492188301 block**。
marker前後の残留移動は原Paperログに保存し、窓前の移動を消去しない。
最終AのM0 move消費 **0.0036246789564109536**、真正EAT入金1。
STOP前のP1累積 **0.07249357912821906**／回復 **0.06728423586294344** は
DEV観測会計で、STOP後はどちらも増分0。これをP1-qualified WAITと呼ばない。

全履歴の正常MOVE **24**、正常EAT **3**、
中断/未確定Action UNKNOWN **12**、限定DEV STOP ACK **3**。
Action/effect IDはsession内一意、重複effect ID **0**。

## T1i-B 非冪等EATとSTOP

判定は **EAT_STOP_FAIL_CLOSED_DEV_PASS**。物理EAT中断成功ではない。
equip前後STOPではconsume0、food18のまま、Inventory3のまま。
consume送信後STOPではfood18→20、cooked_beef3→2、applied native consume receiptと
後続独立Paper由来food観測を確認。詳細のreceipt seq・session・後続foodはJSON参照。
receipt直後/後続観測中STOPも、既にWorldで進んだ食事を「食べていない」と読み替えない。
原ActionはUNKNOWNのまま、EatingOutcome生成0、M0入金0、P1-qualified WAIT0、
EAT高位STOP ACK0。consume再発行は全履歴 **0**。

送信中STOP、ACK欠落/遅延、old session/Action再提示、source lossとの競合、
STOP後の同Action再要求/新Action拒否、ACK後もラッチ維持はfocusedテストで確認。
実Worldの`consume_send`は送信直後のイベントループ境界であり、network backpressure中の
物理送信取消を実証しない。欠落/遅延/旧ACK/source-lossの組合せは今回offline注入で、
全組合せのnative実証は **NATIVE_UNVERIFIED**。T1h原本を新T1i試行へ数えない。

## M0/P1とcleanup

通常MOVEの測定距離コスト/観測tickのbasal・疲労は既存T2式を利用。
正常EAT入金は各A試行1、未確定EAT入金0。STOP後は会計を凍結し、欠落tickの補完、
架空WAIT回復、target TPS再乗算を行わない。式/profile/速度別疲労率は変更なし。
凍結Self ledgerはSTOP後のWorld代謝を表す完全な帳簿ではない。
Paper側の実basalは継続するので「STOP後の物理コスト0」とは主張しない。
新たな明示許可と再観測によるresumeは未実装で、無条件再開は禁止。

各試行Java/Node returncode、単一readerでdrainされたshutdown_ack/connection_end、
PID/starttimeと/proc消失、25565再bindをreportに保存。
全13試行でcleanup成功・PID回収・再bind **13/13**。Java0/Node0、個別JSONに記録。
STOP ACKはcleanup成功による代用ではない。

## 原本・再現

root `/home/rinsa/work/t1i-integration-evidence-20261027`。
各World `server/`、`native.jsonl`、`commands.jsonl`、`paper.log`、
`python_timing.jsonl`、`node_timing.jsonl`、`t2_ticks.json`、`report.json`、
`source_hashes.json`、run別`subject.json`にHEAD/diff/runner hashを保持。
全source_hashes読み戻し検査は測定JSONに記録。

実行例（outputは毎回存在しない新規絶対path）:

```bash
PATH=/home/rinsa/.nvm/versions/node/v22.22.2/bin:$PATH \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests \
/home/rinsa/relay-self-s60b1-venv/bin/python -m adapters.mineflayer.t1e_native_dev \
  --output /NEW/ABSOLUTE/PATH \
  --paper /home/rinsa/work/t1h-integration-evidence-20261026/run-006/t1h_input_residual/server/paper.jar \
  --plugin /home/rinsa/work/t1i-integration-evidence-20261027/generated-build-and-cache/adapters/mineflayer/m02_paper_dev/target/relay-metabolism-paper-dev-0.2.0-dev.jar \
  --bootstrap /home/rinsa/work/t1h-integration-evidence-20261026/run-006/t1h_input_residual/server \
  --confirm T1E-DISPOSABLE-DEV-ONLY --loop-moves 2 \
  --cases t1i_stop_loop t1i_stop_eat
```

bootstrapからcache/libraries/versionsのみコピーし、World原本を再起動しない。
plugin buildはJDK21を明示。システムPython pytest欠落、最初のPYTHONPATH不足、
Maven PATH不足とJRE-onlyのjavac不一致を修正したログも保持。最初のimport失敗はWorld試行に数えない。

## 未成立と次段階

R資格STOP、全tick/subtick完全無活動、P1-qualified WAIT、高TPS期限/高TPS Motor、
汎用resume、EAT物理取消、独立資格化、科学的効果は未成立。
次はSTOPで切れた観測/会計の明示再認可・再観測境界を設計し、必要なら既存native EATに
取消/完了照合のDEV seamを追加する。未知Actionの再送や食事再発行で解決しない。
