# T1p 通常Bodyループ実Minecraft DEV結果 — 2026-10-28

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
新規使い捨てWorld **1実行、1 PASS / 0 FAIL**。L0 → 元S51/S49 Action →
S16 clear ACK → Paper静止観測 → WAIT_DEV → 次L0の2サイクルが成立した。

## 基底・変更・検証

branch `self/dev-t1p-l0-body-loop-20261028`。fetch時のlocal新規branch／remoteは
`c214d629cad958063dd7cda05a80173222ff0b95`で一致。
T1o `ef1cd01a36e8ca9e9621e470ce64e3cde9db60b8`が祖先。
隔離worktree `/home/rinsa/work/relay-self-t1p-20261028`を使用。
実行runtimeはこのc214d629の既存実装と同一で、runtimeコード修正は不要だった。
実行時差分は下記test fixtureと仕様注記のみ。実行HEAD・全tracked source hash・差分は
`T1P-001-launch.json`。最終commitはGit履歴および外部`delivery.json`で固定する。

- `tests/test_t1p_body_runtime_dev.py`: frameとowner.previousの同一fixture参照を独立コピーへ修正。
  初回focused **78 PASS / 1 FAIL**原本を保存。seq改変が両方に伝播したfixtureの欠陥であり、
  判定期待値を緩めず修正後 **79 PASS**。
- `docs/t1p-unforced-body-loop-dev.md`: exact仮想E／疲労はホスト発行制限であること、
  SelfBody内受容観測の成立を主張しないこと、認知costは象徴的tick allowanceであることを明記。
- 本Markdownと同名JSON: 実機実測・環境・SHA256・未成立条件。

Python **3.12.3**、focused79、継承FAST42ファイル＋T1pの**43ファイル692 PASS**。
Ruff、480 PythonファイルのAST構文、repository contracts PASS。
最初のsystem python3.12はpytest未導入で起動不可だったため既存
`/home/rinsa/relay-self-s60b1-venv/bin/python`を使用。依存の追加導入なし。
Bridge変更なし、追加Nodeテストなし。Javaソース差分なし、JAR再ビルドなし。
FULL Regression、R/V資格実行、SCIENCE、PR作成、main mergeは実施していない。

## 実機と再現入力

WSL2 Ubuntu、Node **22.22.2**、Mineflayer **4.39.0**、Java **21.0.12.1**、
Paper **1.21.8-60-main@29c8822**。バージョンは今回の実資産から再取得。
物理Node runtime `/home/rinsa/work/t1e-integration-evidence-20261026/node-runtime`と
そのnode_modulesは実directory。136依存manifestとbootstrap121ファイルのSHA256を保存。
Paper/PluginはT1o記録と再照合した同一JAR。

| 資産 | SHA256 |
| --- | --- |
| Paper | `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e` |
| Plugin | `7b24265e2a8087b12ff11351ef91d5db21250bce7fd1a220cfcd2e573cf69d81` |

絶対パス・argv・PATH/JAVA_HOME/runtime環境・依存hashは外部`assets.json`、
`launch-config.json`、`T1P-001-launch.json`に保存。
`--cases t1p_body_loop --loop-moves 2 --node-trace off --confirm T1E-DISPOSABLE-DEV-ONLY`。
T1h bootstrapからcache/libraries/versionsのみコピーし、World本体は新規生成。
人工LOW_HEALTH・食料配布・STOP注入はいずれも0。

## L0・Action・World時間

run **T1P-001**、session `846852fd-2908-439b-85db-5e618562b07b`、
World `ca23688f-3360-4d1b-a1ad-5ab207efb31c`。
Paper80フレーム全ADMITTED、source seq／WorldTick／identity連続、違反0。
基準tick1032の次から**1033–1092の60連続tick（3 reference World秒）**を会計。
causal-age上限実測max **88.687888ms <150ms**、receive→evaluation完了max
**0.688382ms <25ms**。2400 challenge境界を変更せず使用。
Paper同一時計による会計区間のeffective TPS **20.001650**、設定20TPS、TPS actuator0。
性能改善の因果比較や追加タイミング原因調査は行っていない。

| epoch | L0 source tick/seq | Motor ACK / clear ACK seq | OUTCOME距離 blocks | Paper静止tick | WAIT後tick |
| --- | --- | --- | --- | --- | --- |
| 0 | 1032 / 27 | 29 / 38 | 0.6269065734210613 | 1050 | 1062 |
| 1 | 1062 / 73 | 75 / 84 | 0.6269065734210615 | 1080 | 1092 |

Motor送信2・clear送信2、Action ID2・effect ID4すべて一意、重複0、異種effect0。
両Actionはdispatch/clear applied、元Supervisor終端OUTCOME。
各clear後の残留運動を保持し、後続8連続Paper input/pose idle遷移を確認。
その後それぞれ12実tickを観測してから次L0判断／終了。
元T1e単一native reader、既存S51 issuer→S49 executor→S16経路を維持し、
新しいreader／issuer／Motor writerを導入していない。source拒否・危険・UNKNOWNでは
新Actionを止める既存focused負対照を通過。

OUTCOME距離計 **1.2538131468421227 blocks**、Paper開始→静止の変位計
**1.7143394396728937 blocks**、Plugin motion-event counter増分計
**1.6821058965735858 blocks**は異なる観測量として保存。
M0/P1は既存契約どおり最後のevent-counter増分を使用し、変位差分を補填・再課金しない。

## M0／P1

| 会計量 | 実測値 |
| --- | --- |
| 仮想M0 Energy初期 | 12.0 |
| basal消費 | 0.0600000000000000 |
| 認知allowance消費 | 0.0060000000000000 |
| 移動消費 | 0.003364211793147172 |
| 消費合計 | 0.06936421179314718 |
| 最終Energy | 11.93063578820689 |
| 食事credit / intake / meals | 0 / 0 / 0 |
| WAIT_DEV | 40 ticks、うちbasal消費0.04 |
| P1初期→累積蓄積→累積回復→最終 | 0 → 0.06728423586294344 → 0.06728423586294344 → 0 |

epoch別P1 peak／蓄積／回復は0.032997447069485555と0.03428678879345788、
各WAIT後0。回復はpost-terminal/clear、causal challenge、input idle、位置・motion counter不変、
非脅威の実ADMITTED連続tickだけで発生。blocked MOVEや単なるAction不在の回復0。
**WAIT_DEVはP1-qualified WAITではない**。#626疲労モデル式は無変更。

仮想M0は象徴的DEV単位でありMinecraft満腹度／exhaustionやjoulesではない。
Paper物理exhaustion増分はbasal **0.060000000000000046**、motion
**0.016821058965735856**として別保存。LLM呼出し0。
exact E/P1はホスト安全guardだけに使用。この試験は有限・可謬なSelfBody内受容知覚の統合を
実証していない。象徴的認知allowanceも実policy呼出し回数やCPU消費と同一視しない。

## Trace・cleanup・原本

`node_trace_enabled=false`、同期`node_timing.jsonl`不在、原nativeによるOFF audit PASS。
Java PID822891／Node PID823004ともexit0・消滅、port25565再bindを終了後に独立再確認。
`shutdown_ack`と`connection_end`を原nativeから確認し、World保存終端もPaper logで確認。
これは正常transport shutdownであり、**高水準STOP ACK成立を意味しない**。

原本root `/home/rinsa/work/t1p-evidence-20261028`。
全World、native/commands/python_timing/Paper log、report、t2 ticks、launch/assetsを
**206ファイルSHA256再読一致**。`originals-manifest.json` SHA256:
`cf971472f23a7676cd750f17ccc333b073f758bfce6a5a4b40e411a966c4c40e`。

| 原本 | SHA256 |
| --- | --- |
| native.jsonl | `56082b2b0c4f327f75adfe2299b770a45aaeb84d0f91bc4f176c5a3d5fb88642` |
| commands.jsonl | `23e9ecd0714a9176cab62a0101887fdc897574f897b54ff95c20949dd1b6fe4d` |
| report.json | `e1f1533b8fb0d71951341aa0fcf13ca64144a14544b3cfef55dc2e43bd387891` |
| t2_ticks.json | `471ff1f218cd5e85af2bbbe98dcad552098a52d1195eb8e9895f8af7ac39baf0` |

原本はローカル保管、GitにはMarkdown/JSON実測要約を収録。
初回focused FAILも保持。独立read-only原本監査22項目すべてPASS。
Issue #537/#627/#150/#616へ結果報告し、exact本文とURLを外部`issue-readback.json`に保存する。
main、Draft #545/#634、S18保護原本、R/Vレーンは変更対象外。

## 未成立・次の開発

正常な限定Body DEVループのみ成立。SelfBodyの有限・可謬な内受容観測を既存viewに接続し、
次の判断がその観測を利用する製品開発が残る。独立source認証、P1-qualified WAIT、
高水準STOP ACK、摂食・自律採食・長期viability、認知/学習の科学的効果は未成立／今回対象外。
T1o trace OFFの維持は確認したが、性能改善の因果的証明は主張しない。
