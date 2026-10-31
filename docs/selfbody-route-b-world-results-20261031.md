# Issue #651 経路B 実World DEV結果 — 2026-10-31

**DEV_LIVE_NEXT_L0_NATIVE_EPOCH_REFERENCED_PASS**。
PR #650 HEAD `0f52d8d22814874baaa7d435ffc491abe3309d95` から隔離worktreeで実装。
実行コードHEADは `65246cd5e4cbc0905e736663120ca2b2be48951d`。
新規World **1回 / PASS 1 / FAIL 0 / PREWORLD_BLOCKED 0 / retry 0**。

| 実測項目 | 結果 |
| --- | --- |
| 元L0 decision / event→probe seq | WAIT 8→9、MOVE_AWAY 19→21、WAIT 55→56 |
| 各target ID / 距離 | 26 / 10m、28 / 2m、30 / 10m |
| 元S49 Action / S15 clear ACK / S16 OUTCOME | 1 / 1 / 1 |
| S16 before→after native seq | 22→30 |
| L22後の第2Goal probe | seq 42。旧validator用prefixはここで封印 |
| Paper WAIT / INPUT callback | 各8、連続World tick 252–259 |
| 前Actionの身体経験readonly参照 | 次native probe 56の既存live_probe内、1回 |
| 現在のBody / World Present | probe 56のみ。outcomeはnull |
| 報告入力OFFで変位を観測したtick | 252、253、254。全tick入力idleの証明ではない |
| full S7受信 / 送信原本 | 57 / 14行。旧prefixとのbyte一致PASS |
| Node client.write return | motion系33、player_input 0 |
| Paper INPUT_EVENT | 0。INPUT_TICKは8件すべてOFF |
| Node footer | TRACE_END、complete=true、lost=false |
| 終了・cleanup | Node/Java exit0、所有PID全消滅、World削除、port再bind PASS |

S16後に実Paper stdoutの改行終端byte prefix **146085 bytes**を取得。
SHA256 `2824928a88b9a354056d41f41f112b8637f9bc850447b3ba2d80f964ad1c3eb1`。
最終Paper原本との照合PASS。読み取り時点はあくまで
**PROVISIONAL_PAPER_ONLY**であり、完全Node原本の監査PASSは実際の終了後。
第3イベントは窓完成後のWorld zombie置換から発生し、元receiver→正式probe→元L0がWAITと判断した。
WAIT直接注入、人工probe、追加issuer、policy学習・閾値変更はない。

実session `15f04c47-1a80-4705-99e1-ebedb963e3a3`、
World `21c20dbf-0f44-4207-b557-b4a3e2764979`、
Action `s49-native-move-19`。
元typed SelfBody/S16の同一性は実行中のowner内でassertし、
独立監査では保存native sourceとdiagnosticの整合を確認した。
保存JSONからtyped ownerを再認証したとは主張しない。

Python3.12 FASTは **211 PASS / 1 SKIP**。
NodeがPATHに無かったためskipされた1件は、Node22のPATHを明示して
**1 PASS**を追加確認（合計212件を検証）。既存111件は別途全PASS。
Node22 focused 6 PASS、Ruff、compileall、repository contracts PASS。
追加source/lifecycle tests 9 PASSを含む。
終了後の独立原本監査PASS。負対照14件は全拒否：第3イベント欠損・偽物・早着・MOVE、
S16 UNKNOWN、別session/Action/World、逆順seq、WAIT欠損、INPUT欠損、
Paper SHA相違、二重参照、Node footer欠損。変造は隔離コピーのみ。

Java21 / Node22.22.2 / Python3.12.3 / Paper1.21.8 / Mineflayer4.39.0。
M0.2は **ACTIVE_METABOLISM_NOT_PASSIVE** の既存完全configを固定した。

- Paper JAR SHA256: `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`
- plugin JAR SHA256: `405657013fa315d76aab3730c6324b3583f9b30facf9233ef0b88fda9026585a`
- config SHA256: `2fd8f5bac2fea7fe857b1e7712a6979a2b76b78f626c374af7fbc7fee44e72d0`

新規外部原本root：`/home/rinsa/work/issue651-route-b-evidence-20261031/`。
[Git保存証拠](evidence/issue651-route-b-20261031/) /
[独立監査](evidence/issue651-route-b-20261031/run1/independent-original-readback.json) /
[負対照](evidence/issue651-route-b-20261031/negative-original-readback.json) /
[SHA256SUMS](evidence/issue651-route-b-20261031/SHA256SUMS)。
負対照変造入力の全コピーは外部rootの `negative-inputs/` に保持し、
Gitには再現script・結果・各入力SHAを保存する。
旧原本6708ファイルは全SHA一致、main HEAD不変。PR #650自体も更新しない。

**残課題・判定上限:** 次L0 epochでのreadonly参照は成立したが、経験によるpolicy変更や
学習成立は今回の対象外。effective clear tick、全tick入力idle、物理安定性、
時計同期はNOT_ATTESTED。**Goal UNDETERMINED、P1 WAIT=0、L10=0、S10/S11=0、
QUALIFICATION_NO_GO、SCIENCE_NOT_RUN**。Issue #632/#627全体の完了は主張しない。
