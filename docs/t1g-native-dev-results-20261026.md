# T1g / S49 / T2 実Minecraft DEV結果（2026-10-26）

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

ブランチ `self/dev-t1g-stop-disconnect-20261026`。指定開始HEAD
`636fb2dbd7a5786a6083858db7293d9426136a7f` はリモートと一致し、指定基底
`488fcd3576bb4f4f147dc37434bf71b51f0b02e4` の子孫。
修正版の実機試験HEADは `eb15d33a`（run-004、subject.jsonに完全SHA）。
main、Draft #545/#634、過去DEV原本、R/V資格原本は変更していない。
FULL・R/V実行・許可消費・モデル呼出し・TPS actuator・高TPS Motorは行っていない。

## 実装修正と検証

- next_tickのsource lossをsessionにも不可逆にラッチし、後続のADMITTEDを取り出して
  継続できないようにした。会計ownerがない観測モードにも適用。
- 既存の単一native readerで、実行中のconnection_end / adapter_error /
  command_error / shutdown_ack / EOF・読取異常もT2失効へ接続。
  次のset_controlも失効を拒否。既存issuer / S49 / S16 cleanup所有権を維持。
- 例外終了時も最終E・FatigueState・有効tick範囲を保存。未決Actionを完了扱いせず、
  cleanupで得た実exit値を保持。PID/starttimeを新規試行で記録。
- 既存のDEV CLIにPaper console kick、ACK consumer欠落・遅延・前epoch再提示を追加。
  kickは実TCP切断。ACK faultは**consumerへの注入**で、ネットワークpacket改変ではない。
  全原wire bytesを保持し、再提示は新しいMotor effectを作らない。

Python **3.12.3 FAST 440 PASS**、focused **45 PASS**。
Node **22.22.2 68 PASS**、bridge構文PASS。
Java runtime / javac **21.0.12.1**、Maven **BUILD SUCCESS**。
変更ファイルRuff・repository contracts・diff whitespace PASS。FULLは未実施。

## 32 MOVE / EAT / 危険中断

主結果はrun-004/t2_loop、単一新規World
`8481a74a-93e5-41ac-95cd-4cc9bb020aa0`、session
`61292add-37cf-4cc5-b75c-2bb9bb0e5b70`。Paper 1.21.8、Mineflayer 4.39.0、20TPS設定。

- 正常MOVE **32回** → 真正EAT **1回** → 33回目のMOVEをPaper LOW_HEALTHで中断 →
  後続観測からWAIT_NO_ACTION。正常MOVEのprobe変位は各 **0.626907–0.832291m**。
- **33 set_control / 33 clear_controls**、Action ID・clear ID二重送信なし。
  正常MOVEはEXECUTED/OUTCOME、危険中断はFAILED／supervisor UNKNOWNのまま。
- 消費範囲 **907/907 ADMITTED**。STALE/MISSING/LATE/UNDETERMINED各0。
  上限観測年齢最大 **85.255626ms**、Node受信→評価完了最大 **0.712491ms**。
  年齢<150ms・Node処理<25msという既存上限を維持。
  正確な片道遅延・各50ms Paper tick内期限保証はUNKNOWN。
- L0評価完了→Node clear適用 **0.857629ms**（同一Node時計）。
- clear ACK後の最初のPaper snapshot→静止確認までに観測した残留変位は
  **0–0.240460m**。これは解除瞬間からの総移動量ではない。
  各epochで残留を保持し、既存のpost-clear challenge・idle入力・位置不変の
  **8連続区間**を満たしてから次Actionへ進んだ。
- 正常owner shutdownでshutdown_ack→connection_end、Java/Node exit0、PID消失、
  25565 rebindを確認。高位STOPは**未発行**、高位STOP ACK・shutdown後のPaper身体静止は
  **未確認**。epoch間の静止確認と最終shutdown後の停止証拠を混同しない。

32 MOVEは初回run-001でも成立（887会計tick、907 ADMITTED）。修正版をrun-004で回帰。
前epoch clear ACKを2epoch目のdispatch ACKより前に再提示したrun-004/t2_old_effectも
32 MOVE→真正EAT→危険中断→抑止を完了。古いACKは現Actionに結合されず、二重effectなし。
同一IDを二度実発行して重複効果を作る試験は行っていない。

## 実World負対照（FAIL原本を維持）

| 原本 | 注入／観測 | 有効会計tick | 結果 |
| --- | --- | ---: | --- |
| run-002/t2_disconnect_move | set_control適用後kick | 1 | connection_end、FAILED/UNKNOWN、clear ACKなし、新規Actionなし |
| run-003/t2_disconnect_move | 同上 | 1 | adapter_error ECONNRESET→connection_end、同じくfail closed |
| run-003/t2_disconnect_boundary | 正常Action終端・clear ACK後、次Action前kick | 5 | connection_end、前ActionだけOUTCOME、新規Actionなし |
| run-002/t2_disconnect_wait | 最初の観測WAIT_DEVでkick | 13 | connection_end、以後会計なし |
| run-003/t2_disconnect_wait | 同上 | 12 | connection_end、以後会計なし |
| run-002/t2_lost_ack | 原clear ACKをconsumerで欠落 | 14 | clear ACK未確認、次Action・clear再送なし、WAIT回復0 |
| run-002/t2_delayed_ack | 原clear ACKをconsumerで0.7秒遅延 | 4 | ACK期限切れ、次Action・clear再送なし、WAIT回復0 |

上記は各 **1 set_control / 1 clear_controls試行**。断線後に再接続／原Action再発行なし。
断線5 WorldはJava exit0、Node exit3、両PID消失・port rebind成立。
ただし正常shutdown ACKはなく、`cleanup_complete=false`を維持。
MOVE断線のclearは送信試行のみで適用ACKなし。境界/WAIT断線の直前clearはACK済みだが、
それを高位STOP ACKや断線後身体停止に流用しない。
ACK負対照2 Worldは正常bridge終了しexit0だが、Action結果はFAILのまま。

WAIT断線では注入要求後も終端受信までに届いた実snapshotのみ保持した。
WAIT_DEVは各2tick、その回復総量0.032997447069485555、最終Fatigue0。
これは終端以後の回復ではない。全断線で終端検知時tick数と最終台帳tick数が一致し、
全台帳source_seqは終端seqより前。欠落tickやshutdown tailを0/WAITとして補完していない。
P1-qualified WAITは全ケースfalse。

## M0/P1会計・仕様整合

主結果はWorld full time **1032–1918、連続887tick = 44.35基準World秒**。
初回snapshotはanchorで課金せず、TPS掛け直しなし。

| 項目 | T1f既存20 MOVE | T1g主結果32 MOVE |
| --- | ---: | ---: |
| 有効WorldTick | 673 | 887 |
| M0基礎代謝 | 0.673 | 0.887 |
| 実motion追加消費 | 0.035147251868 | 0.057012814737 |
| L0 bridge消費 | 0.0673 | 0.0887 |
| 真正EAT入金 | 4.0 / 1回 | 4.0 / 1回 |
| 最終E（初期12） | 15.224552748133 | 14.967287185264 |
| P1疲労蓄積 | 0.702945037356 | 1.140256294732 |
| WAIT_DEV回復 | 0.702945037356 | 1.140256294732 |
| WAIT_DEV tick | 430 | 521 |

Eは `12 + 4 - basal - motion - cognition` と原台帳から独立に整合。
追加214tickのbasal/L0と実motion差分で説明できる。symbolic EとPaper exhaustionは
別台帳であり、CPU/GPU joule測定でもない。真正EATは既存receiptによる在庫減・food増を確認し
Action IDを1回だけ入金。全11 Worldのtick連続性・E整合・ID非重複を原本から再検査した。

#626現行bodyと#620仕様意図を読み直した。#626の既存P1ソースSHA256
`2f7ae969fcb4676558c30a06483d219353b8ca9214b61756db202b6821461c5a`を維持。
現行は**WAIT時回復、MOVE実距離あたり蓄積**。非WAIT通常回復、WALK/JOG/RUN/DASH別率は
未実装であり、同じ距離で速度だけを変えた疲労差は表現しない。REST専用Actionは不要。
M0のEとP1疲労は独立。異常時は最後の有効FatigueStateを保存して失効し、reset・仮想回復・
別sessionへの引継ぎをしていない。新しい疲労式は導入していない。

## 保持した失敗・原本・限界

新規 **11 World：3 PASS / 8 FAIL原本**。FAILは意図した負対照7件と、
run-002/t2_disconnect_boundaryの注入前鮮度拒否1件。
後者は起動時causal age上限190.604msが150msを超過してsessionがラッチし、Action0・会計0。
上限を緩めず原本を残し、run-003で目的の断線を実注入した。
初期Maven不在・既定compilerのrelease21不対応ログも保持し、既存の絶対Maven/JDK21を
明示してビルド成功。テストを弱めた修正はない。

原本：`/home/rinsa/work/t1g-integration-evidence-20261026/run-001/` ～ `run-004/`。
各caseのsubject、native/commands/python/node journal、Paper log、t2_ticks、report、
source_hashesを保持。既存Worldは起動せずcache/libraries/versionsだけ再利用した。
新規Worldは停止・オフライン保存し、削除しない。
機械集計は [JSON](t1g-native-dev-results-20261026.json)。

成立範囲は20TPS設定・単一Self・44.35基準World秒のbounded DEV。
高位S49 STOP発行/ACK、断線後の独立Paper静止証拠、長時間常用、EAT中断、R全tick WAIT、
速度別疲労・高TPS Motor・TPS actuator・科学的価値は未検証。
次段階は既存ownerの高位STOP経路と独立した停止後World観測の接続、およびさらに長い
DEV運転。P1通常回復/gait拡張はowner設計・影響範囲を先に確定する。
