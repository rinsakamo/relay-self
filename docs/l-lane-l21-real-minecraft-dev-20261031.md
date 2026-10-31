# L21 実Minecraft GoalObserver統合DEV — 部分実測、正式受理FAIL

2026-10-31 JST。Issue [#426](https://github.com/rinsakamo/relay-self/issues/426)。

## 結果と実行境界

**分類: `DEV_PARTIAL_PHYSICAL_ORIGINALS_FORMAL_ADMISSION_FAILED`。DEV PASS、QUALIFICATION、SCIENCE、L1学習成功ではない。**

ユーザーが本セッションに許可した新規使い捨てWorld上限2回を使用し、追加Worldは起動していない。
開始ブランチ `integration/l21-separate-client-physical-goal-observer-20261031` のremote HEADは指定の
`160e42fe36d209135e39049594e6300fbc93fae7` と一致。mainの元HEAD
`32fe105fc12cbf54abd11bfba7c8a75d319939df` と既存worktreeを維持し、独立ブランチ
`dev/l21-real-goal-observer-20261031`、worktree `/home/rinsa/work/relay-self-l21-real-20261031` で実施した。
開始時のGitHub L21 PR検索結果は0件。既存保護ブランチへのpush/mergeはない。

| 試行 | 物理実行HEAD | 結果 |
|---|---|---|
| 1 | `597c0419d4bd0cfe7abd14591d9ca1d89bcb3c6a` | World起動、Observerログイン拒否、Self未接続、Action 0、runner exit 2 |
| 2 | `35d0a9869ea9929ffacb925a8c8ee50a10a89c38` | 両クライアント接続、MOVE 1、S15 clear、S16 OUTCOME、Observer 2観測。L16拒否、runner exit 1 |

上記HEADは各environment原本およびGitの実値を参照する。後続の終了・報告保全修正のコードHEADは
`d43a3ce9e11a0d48f05e1441e72aa4a6ea0f52f1`。この修正後の新規World実行は0回。

共有RSEEのPython 3.12.3とMineflayer 4.39.0を再利用した。Node v22.22.2、OpenJDK 21.0.12.1。
S49既存standalone経路で公式Mojang vanilla Java 1.21.8を検証取得し、新規flat Worldを生成した。
公式jar SHA1 `6bce4ef400e4efaa63a13d5e6f6b500be969ef81`、57,555,044 bytes。
共有の保存WorldやPaperプロセスは使用・変更していない。Gemma/外部LLM呼出し0、課金0。

## 実機で判明した問題と修正

1回目: `RelayGoalObserver` は17文字で、Minecraftログイン名の16文字制約に違反した。
サーバーは `Failed to decode packet 'serverbound/minecraft:hello'`、Observerは `socketClosed` を記録した。
役割名はRelayGoalObserverを維持し、実ログイン名を **`RelayGoalObservr` (16文字)** に修正した。
Node・Pythonの起動引数、原本検証、テストfixtureを同じ実名に揃えた。失敗原本は変更していない。

2回目: S16後、S7 seq32/34に `observation kind=move` が到着した。
既存L16はこの区間で相関済みGoal probe以外には `entities` だけを許容するため、
`unsafe or foreign event inside post-S16 Goal capture window` で拒否した。
S49はL16検証をObserver closeより先に実行していたため、Observerをfailure cleanupで終了し、
`closed` 原本行と正常終了ACKを得られなかった。
また `actual_native_actions` の追記がGoal監査後だったため、原本S16が存在しても元reportの配列は空のままである。
この不一致を後から原本reportへ補正していない。

後続修正は、実Action結果とL18 indexを監査前にreportへ保持し、2観測後のObserver closeをL16監査前へ移した。
stdin readlineも明示的にcloseする。診断用時刻は別JSONLへ記録し、S7の原本形式を変えない。
元Executor、L0選択、S15 clear、S16解釈、L16/L13/L14の受理条件は変更していない。
この修正の物理再検証は上限到達により未実施。模擬Botを使う実Nodeパイプlifecycle試験は終了まで成功した。

## Goal事前登録と実測順序

実座標を見る前にL20原本を作成し、両試行で固定した。
**target x=0.0 / z=0.0、tolerance=0.49m、stable delta=0.05m**。
同一オペレータによるDEV事前登録であり、独立Goal所有者、独立事前時刻証明はない。

2回目のMinecraftサーバーログに、別TCPポートで次のログインがある。

- Observer: `/127.0.0.1:55682`、entity ID **1**、spawn `(-8.5,-60,-3.5)`。
- RelaySelf: `/127.0.0.1:55694`、entity ID **2**、spawn `(1.5,-60,0.5)`。

Self session `bd9117de-85e5-4d76-afd8-c1da26ff34c2`。
最初の遠距離zombie probeはseq10で10m。近距離zombieのevent seq21 / probe seq22は2mで、
Action **`s49-native-move-21`** に進んだ。
S7 before seq23 → back ON receipt seq24 → clear receipt seq29 → after seq31。
両effectは `applied`、L18 originalは `source_status=executed`、`disposition=outcome`、
`reason_code=observed_execution`。afterまでの移動量は約 **0.7342911432m**。

その後の呼出順は Observer #1 → S7 Goal #1 seq33 → Observer #2 → S7 Goal #2 seq35。
Observerは自分の `bot.players.RelaySelf.entity.position` を読んでいる。
Observer JSONLのrequest IDは両方ともこのsession/Actionに一致する。

| 観測 | Observer (x,y,z), target ID=2 | S7 (x,y,z) | 水平差 |
|---|---|---|---|
| 1 | `(1.5,-60,-0.234375)` | `(1.5,-60,-0.2929231183274858)` | 0.0585481183m |
| 2 | `(1.5,-60,-0.234375)` | `(1.5,-60,-0.32493617673713887)` | 0.0905611767m |

Observer間隔は診断monotonic clockで **43.291803ms**。
wall記録は `1793422184356` / `1793422184399` ms。
S7のtime_of_dayは239 / 259だが、これを正確な観測tickや20tickの経過と解釈しない。
ObserverにMinecraft tick原本はなく、時刻・順序・サンプル位置は同時観測ではない。
clear後もSelf座標が変わっており、観測遅延、プロトコル更新・量子化、惰性移動を分離していない。
位置差だけでObserverバグや物理的因果を確定しない。

Observer自身が書いたGoalは `NOT_REACHED`。固定Goalからread-onlyで再計算したObserver/S7も双方
`NOT_REACHED`、S7二点の水平変位は約0.0320130584mで閾値内。
ただし **L16正式windowは不成立、L21正式reviewはclosed欠落で拒否**。
`goal_result` 原本5行を6行の正常完了原本へ補完・修復していない。
元S49の残り2回目のActionは実行されていない。S49 reportの空のAction配列を「物理Action 0」の根拠にしない。

Observerはコマンド語彙 `sample` / `shutdown` だけを持ち、明示的move/attack/look/chat権限はない。
ただし通常のMineflayerプレイヤーとして参加すること自体が介入である。
S7 entitiesにはObserverが約10.77mで見え、entity数・spawn・負荷・時刻にも影響しうる。
共有ホストが両クライアントを起動し、サンプル時刻を要求している。物理的非介入、独立所有者、TCPの独立認証は証明しない。

## 原本・再監査

外部原本保存先: `/home/rinsa/evidence/l21-real-20261031/`。
バイト一致のGit保存複製: [evidence/l21-real-20261031](evidence/l21-real-20261031/SHA256SUMS)。
32ファイルの[SHA256SUMS](evidence/l21-real-20261031/SHA256SUMS)は次のSHA256を持つ。

`474593f8b4553e3f0304008e981d3bcf9c5b9c0c4f508c34fcf6cebf53811b74`

| 原本 | SHA256 |
|---|---|
| L20 criterion | `e22f417216d4c4042a0a129334d218b1ab35caf0f0676230ae405e2196bb062a` |
| Run2 S7 received (36行) | `77a12b805d577482423d622392d7b0e5fe1aab0cd1f203d6a7085b580532c5e2` |
| Run2 S7 sent (8行) | `2795bd405f7479cd33669d41cb09d59158998e998058f9b63090843b0124b671` |
| Run2 L18 S16 | `9ca9b36599f1365e08b1f2c15137b8ce8c9dd2da6a5ac3e1282d7b48af2004f0` |
| Run2 L21 observer (5行、未正常close) | `38c378dc41066e519b33c37d48edfe359b0a2bd282da988b73cbaa539c241559` |

S49 report、Javaログ、L16 pre-World plan、S7 index、L18、L20、Observer原本・時刻sidecar、各実行HEAD・環境、
L17/L20失敗readbackと終了確認を保存した。S49の一時World自体は既存cleanupで破棄された。
L18 indexはrun2の監査例外でreportへ転記されていないため、欠落を明示し、後からowner indexを捏造しない。
SHAは保存されたバイトの同一性であり、独立認証ではない。

```bash
cd docs/evidence/l21-real-20261031
sha256sum -c SHA256SUMS
cd ../../..
ROOT="$(pwd)/docs/evidence/l21-real-20261031"
PYTHONPATH=src:tests:. python3 tools/l21_real_dev_diagnostic.py \
  --run-root "$ROOT/run2" \
  --criterion "$ROOT/preregistration/goal.jsonl" \
  --sha256 e22f417216d4c4042a0a129334d218b1ab35caf0f0676230ae405e2196bb062a
```

このCLIは原本を変更せず、新規World/Actionを発行しない。
S7 SHA・seq、Action/clear ID、S16のpre-probe SHA、L20条件、Observer request対応を検査し、
L16/L21の正式拒否と位置差・Goalの診断再計算を同時に出す。複製からの結果も元診断とバイト一致した。
既存L17/L20 CLIの正式readbackはともにexit 2で、report未sealによるBLOCKEDを保存した。

Javaは両試行ともexit 0、run2のSelf Nodeはexit 0。Observerはrun2失敗cleanupでkillされ、正常終了とは扱わない。
後続の別プロセス確認でJava/対象Node/25565 listenerが残っていない。独立STOP認証とは区別する。

## L Laneと次の候補

実S7 Previous World、Action、S16、別クライアント位置原本の材料は取得した。
SelfWorld/SelfBodyの独立lineage、L13独立per-Action Goal、L14事前session/action付き契約、
L17/L20正常結合、次の認知epochは成立していない。
**実L10学習ペア0、S10更新0、S11昇格0、L0蒸留0**。
この診断スクリプトは経験候補の不成立理由を示すだけで、学習器への登録経路ではない。

次の実装候補はS16後の物理的settlingを真正なsole-reader原本から扱う契約と、
Goal監査の失敗時にも観測原本を正常sealできる終了経路の実機再検証。
moveイベントを無条件で無視したり、未知を静止へ変換したり、許容値を緩めたりしない。
新規Worldは既存上限を消費済みのため、新しい実行許可を要する。

## 検証

Python 3.12 focused **185 PASS / 0 FAIL / 0 SKIP** (277.93秒)、Node 22 pure **4 PASS / 0 FAIL**。
185件に模擬BotでのNode pipe lifecycle 1 PASSを含む。
Ruff、Python/Node構文、repository contractsもPASS。
[validation記録](evidence/l21-real-20261031-validation/validation.json)とテストログを保存した。
CIはDEVブランチのpushでL21 focused workflowを実行する。実WorldはCIへ追加しない。
物理実行HEADと後続修正HEADの検証を混同しない。
