# T1f / S49継続 / T2 — 実Minecraft DEV結果（2026-10-26）

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

実機試験HEADは `ba880ea1900a3c56b23224983f55d9c132bf91e0`、ブランチは
`self/dev-t1f-s49-t2-20261026`。開始点は指定T1e HEAD
`85a2aa48e46f113315bcf89c3599b29e3b441908`。
その後の変更は結果報告、報告用集計のT1f形式対応、終了時の会計cutoffのみ。
観測admission・Action・疲労・エネルギー計算は実機試験時と同一。
PR #545 / #634 / main、T1e原本、保護Worldは変更していない。

## 結果

| 段階 | 実World結果 |
| --- | --- |
| T1f観測のみ（run-002） | 59tick ADMITTED、上限年齢最大91.206770ms、Node処理最大0.704701ms |
| S49継続（run-003） | 正常MOVE 2epoch → 3回目をLOW_HEALTHで中断 → clear後の静止 → 次観測から新規Action抑止 |
| T2延長（run-005） | 正常MOVE 20epoch → 真正EAT・一度だけの入金 → 21回目のMOVEをLOW_HEALTHで中断 → 次観測から新規Action抑止 |

全て新規の隔離Paper 1.21.8 World、Mineflayer 4.39.0、loopback、目標20TPS。
既存T1eの5ケースを再実施していない。起動資材のライブラリだけを再利用した。

T1fは同じ接続のchallenge以後にPaperが採取した身体・入力・近傍敵を読む。
Node受信・評価開始・完了、既確認tick、session challenge / plugin boot / World /
Playerを分離。キャッシュはL0入力に使わない。run-005ではキャッシュとの不一致を
7frameで観測したが、Paper由来の判定を使用した。

run-005のloop消費範囲は**694frame全てADMITTED**。
観測年齢の保守的な上限は最大**127.610112ms**、Node受信→評価完了は最大
**0.702773ms**。DEV設定は年齢上限<150ms、Node処理<25ms。
これは受信間隔による推定ではなく、Node challenge送信からの因果上限である。
**正確なPaper→Node片道遅延はUNKNOWN**。50ms以内のPaper tick期限達成や、
評価時点の最新実World状態との一致までは保証しない。

元journal全体ではPaper送信696 / Node snapshot695。終了tailの1frameはloop会計に
入れず、最後のserver tick707はNode snapshotなし。どちらも成功tickに補完しない。
旧T1e reducerはsnapshotをcache shadowとして数えられないため、後続の報告修正で
T1f形式を区別した。元run報告は書換えず、JSONに独立した再集計を保存した。

## S49 / 中断 / ACK / 残留移動

run-005の正常20 MOVEの原probe変位は各 **0.626906573421061–0.626906573421064m**。
Action IDをepochごとに分離し、既存S51 issuer、ActionSupervisor、S49 executor、
S16 clearを使用。21 set_control / 21 clear_controlsで、重複送信なし。

最後のLOW_HEALTHはPaper自身のHP観測から判定。
**Node L0評価完了→clear適用は0.757703ms**（同一Node時計）。
Interrupted primitiveはFAILED、supervisorはUNKNOWN終端のまま保存し、成功OUTCOMEに
変更しない。正常20回は実変位を伴うEXECUTED / OUTCOME。

各移動後は元Action終端とclear ACKを待ち、boundary probeで旧epochを排出し、
clear後に送られたchallengeに結び付くPaper入力idle・位置不変を8連続区間確認。
その前の慣性・残留移動は保存し、次Actionの開始条件やWAITに混ぜない。
前epochの危険・効果メッセージは現在ActionのACKとして結合しない。
Nodeのdispatch直前admission再確認はPython滞留にも対応する。

**clear_controls ACKと高位STOP ACKは別**。このfixtureは高位STOPを発行しておらず、
STOP ACK成立を主張しない。ACK欠落→次Action禁止とclear再送禁止は既存T1eと
今回の負対照で検証し、既存ACK欠落実機試験を不必要に再実施していない。

## T2実tick会計

run-005の会計はWorld full time **1031–1703、連続673tick = 33.65基準World秒**。
先頭のanchor観測は経過tickとして課金しない。TPSの掛け直しはない。

| M0仮想E台帳 | 値 |
| --- | ---: |
| 初期E | 12.0 |
| 基礎代謝 | 0.673 |
| 移動追加消費 | 0.035147251867782885 |
| L0認知bridge消費 | 0.0673 |
| 真正摂食入金 | 4.0（1回） |
| 最終E | 15.224552748132643 |

移動量はPaperの既存累積packet-motion差分を一度だけ計上する。
認知消費は1評価につき.0001という明示的な未校正bridge単位であり、GPU/CPU jouleや
Minecraft exhaustionの測定値ではない。L1/L2/model呼出しは0。
Paper M0.2の物理basal/motionカウンタは別欄で保持し、Eに二重加算しない。

食事は配布したcooked_beefを既存S51 EATで消費し、**在庫3→2、空腹度18→20**を
真正な前後probeで確認。B0EnergyLedgerの既存receipt検証でAction IDを一度だけ消費し、
後続の実tickに4.0を入金した。その後のPaper観測が次のMOVE判断へ渡された。
自律採食・ゾンビからの食料取得の証明ではない。

P1は既存#626モデルを変更せず採用。実移動による蓄積 **0.7029450373556577**、
WAIT_DEVでの回復 **0.7029450373556577**、最終疲労0。
430tickが、Action終端→clear→後続Paper観測→Body台帳→WAIT_DEV判定に結び付いた。
移動指示中、blocked MOVE、解除境界、残留移動中は回復0。
WAIT中もbasalとL0消費を継続した。

**P1-qualified WAITは未成立**。bounded callback/input証拠によるDEV接続であり、
R全tick資格・独立source認証を代行しない。通常時の非WAIT継続回復や
WALK/JOG/RUN/DASH別率は現行P1に存在せず、今回も新しい疲労式を作っていない。

## 検証と保持した失敗

- Python **3.12.3 FAST: 418 PASS**。T0–T1eと近接owner、S51、B0、既存P1、T1f/T2。
  最後の報告修正は別途 **2 PASS**。FULLは実施していない。
- Node **22.22.2: 68 PASS**。新規16件と既存52件、bridge構文PASS。
- Java runtime/compiler **21.0.12.1**: 既存Maven plugin **BUILD SUCCESS**。
- Ruff変更ファイル、repository contracts、git diff whitespace check: PASS。
- 負対照: 古いtick再送、重複、欠損、逆順、World/Player/boot/session challenge違い、
  値欠落、近傍coverage欠損、Node queue/評価期限超過、受信前の滞留、旧キャッシュ不一致、
  dispatch時の観測失効、ACK欠落、blocked MOVE回復拒否、実tick会計の2/20/200 TPS不変性。
  wire障害はoffline負対照であり、物理TCPでdrop/reorderしたという主張はしない。

新規DEV World起動は**5回**、受入PASSはrun-002/003/005、FAIL原本はrun-001/004。

1. run-001: 起動catch-up時、challengeを1tickで使い切る実装が次tickをUNDETERMINEDに
   してsessionを停止。16件の有限challenge履歴と、各tickの因果上限保持へ修正。
2. run-004: 300tickの食事待ち窓で実foodは18まで低下したが、条件<18に届かず停止。
   観測がなかったという意味ではない。条件を<19へ修正しrun-005で真正摂食を確認。

初回CLIには既存test helperへのPYTHONPATH不足、初回選択には存在しないテスト名も
あり、各失敗ログを保持して修正。これらはWorld起動数やPASSに算入しない。
全5 WorldでJava/Node exit0、両PID消失、25565 rebindを確認。

## 原本・未解決・次段階

原本: `/home/rinsa/work/t1f-integration-evidence-20261026/run-001/` ～ `run-005/`。
測定値・原ファイルSHA256・失敗・cleanupは
[t1f-native-dev-results-20261026.json](t1f-native-dev-results-20261026.json)。
実装条件と実行方法は [t1f-s49-t2-dev.md](t1f-s49-t2-dev.md)。

成立したのは20TPS設定、単一Self、33.65基準World秒、22回の移動/抑止判断と
1回の摂食という**bounded DEV閉ループ**。長期連続運用、一般的な探索・採食、
EAT中危険のphysical preemption、正確な片道遅延、Paperの各tick内期限保証、
通常時回復/gait別率、R資格、科学試験は未成立。

次はこのentrypointの上で、停止/通信断を含むより長いDEV運転と、P1 ownerでの
通常回復・gait仕様の整合を行う。高TPS Motor・TPS actuatorは引き続き無効。
