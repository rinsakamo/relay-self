# W4 — 原 S49 owner への明示 opt-in 接続レビュー v0

**Authority:** SelfWorld #633 / Draft PR #634、S18 architecture freeze #354、S 統合 #537。  
**レビュー起点:** `3e08e226d48c58fbde24a7cbf06aa41206826240`。
**判定:** `W4_S49_OPTIN_REVIEW_CONDITIONAL_NO_GO`。
本書は設計審査だけであり、元 `qualify()` / `_new_session()` に接続しない。
実 World・physical Action・実 S16・実 S10 の許可も作らない。

## 1. 検証済みの足場と未成立の条件

起点HEAD exact CI run #39411893046 は必要7/7 `completed/SUCCESS`、full/physical jobsは
`SKIPPED`。LocalCodexの報告は、lease55 PASS（拒否50）、focused 3.11 99 PASS /
3.12 254 PASS、FAST996 PASS/0 SKIP、Node37 PASS、Ruff/contracts、S18 freeze7 PASS。
19 protected Git blob の before/after 一致、実World/Action/OUTCOME/S10各0。

`W4DevLeasedSession` は元 `MineflayerProcessSession` を継承し、同じ decoder と
`receive()` を経由する。operation epoch・一度きり coroutine 委譲・phase/actor/
in-flight排他・失効・S16正規型を通すオフライン工学PASSは資格化済み。
一方、実 `S49.qualify()` は依然として元 `s34._new_session()` が生成する
**base `MineflayerProcessSession`** を用い、直接
`stage_world()` と `host.run_session(NativeObservationOnly(session), ...)` を起動する。
W4 DEV lease はインポートも接続もされていない。

## 2. 元 owner 接続の変更が必要な3つの点

| 元の接続 | 現状 | W4 opt-inが要求すること | 初期判断 |
| --- | --- | --- | --- |
| S34 `_new_session()` | `MineflayerProcessSession.launch(...)`、通常 W4 orientation **OFF**、後続 `_await_spawn()` | 同じオリジナル owner task で `W4DevLeasedSession.launch(...,w4_native_orientation_dev=True)` と元 `_await_spawn()`。startup/leaseの境界を正しく束縛 | **default変更禁止**、独立DEV専用factoryで先行検証 |
| S49 `qualify()` | 元session準備後、`stage_world()`と`host.run_session()`を並行開始 | preworld native oriented probe → ledger一回移譲 → command計画 → collector確証 → hostへのowner lease委譲。Worldとhostが先に開始する経路なし | **元関数変更は別レビュー** |
| S49 `stage_world()` | 10m / 2m / 2m の旧脚本化されたWorld変更、`stdin.drain()`とsleep使用 | 同一source frameから yaw/XYZ による W4 2m前方 target、既存 `_command()` と collector tailの対応、postprobeとの順序確定 | **旧脚本をW4証拠に再ラベル禁止** |

これらは単なるサブクラス差替えや `asyncio.Lock` では実現できない。
特に `stage_world()` には旧 S49 三イベント/二Actionの結末が焼き込まれているため、
W4の条件付き marker を旧 scripted World実行に上書きして追加すると、歴史的
S49 と W4 の結果が混同される。別のW4 DEV-only実行モードを**明示選択**する必要がある。

## 3. 推奨接続形：二段階の opt-in

### Phase A — OFFLINE guarded composition（今回の次実装可能範囲）

元 protected files は不変更。新しいDEV専用 composition adapter が既存の
`W4DevLeasedSession`, `W4PrehostOwnerBridge`, `W4OwnerPreworldProbePort`,
`W4OwnerHandoffGate`, `W4CollectorCursor`, `W4WindowEvent`,
`NativeObservationOnly`, 元 `NormalWorldL0`, 元 `NormalSessionActionExecutor`
を**同じowner・sessionに対して**順序付けする。

外部公開入口は**実Worldに到達不能な fake transport/fixture専用**とする。
必須の正順：
`STARTUP/adapter_started/spawn → PREWORLD native probe → complete ledger
transfer → WORLD_WINDOW planned command/collector marker → HOST original
event loop → original S16 read-only fixture → QUIESCE → SHUTDOWN`。

一つの owner session が reader を所有し、`wait_for` child Taskや既存
S16 Action実行中は明示的な一回権限移譲を行う。不法な別task / 連続無許可read /
終了済epochからの復帰を拒否。成功したfake transportからのreceiptは
`SYNTHETIC_DEV_ONLY, live_owner_attested=false, physical_run_permitted=false`。

**注意**: `NativeObservationOnly` が受け取る事前受信frameは事後World刺激に再注入しない。
元host filterの`receive()`、元correlated reprobe、S16の`receive()`を、
許可scopeが途切れず本当に使っていることを試験で立証する。

### Phase B — 原 S49 owner の live opt-in変更提案（今回禁止）

Phase Aのexact HEAD CIが成功し、freeze/default非干渉、raw source、
外部信頼、grantの独立レビューが終了した**後**に初めて候補にする。

候補は元の`qualify()`にある無条件の
`_new_session() / stage_world() / host.run_session()`を変更するのではなく、
**新規W4専用明示DEV orchestrationを原ownerが選択する入口**を設けること。
既定の S49 CLI/ENV/R/V経路は同じバイト列・同じ3決定/2Actionとする。
`w4_native_orientation_dev`は pinned MC1.21.8 と明示的なDEV選択の組合せだけで有効。
server stdoutには既存 `_ready_server.collect()` の1 consumerしか置かない。
collectorのローカル marker文字列は独立した server tickの署名ではない。

新しい物理実行CLI、`--confirm`、旧grantの再利用、任意のserver commandの汎用発行、
原S49 Action issuerの複製、S10 grant発行、後付け効果判定の変更を許可しない。
**Phase B自体も物理実行の資格化や開始を意味しない**。

## 4. 再検証すべき Task / authority / World 境界

- CPython 3.11 の `asyncio.wait_for`子Taskと3.12の直接awaitは異なる
  実行経路として両方保持。元 `launch`, `_await_spawn`,
  `host.run_session`, `execution._receive_until`の既存関数本体を通す。
- `delegate()`で受信コルーチンを発行するownerとは別taskが、コピーした
  ContextVarで権限を得られないこと。タイムアウト後・キャンセル抵抗のある
  native readerが未完了なら新epochへ進ませない。
- `NormalSessionActionExecutor.execute()`の
  `isinstance(session,MineflayerProcessSession)`型ガードは不変。
  lease自身がAction grant、ActionSupervisor、Skill、S10 retained ownerを作らない。
- preworld probeのsource/timeが、配置やhostの観測より先行すること。
  `stdin.drain()`、sleep、marker自己申告を物理適用時刻/外部署名へ昇格しない。
- 原 `S49.stage_world()`は旧脚本のため、W4の新 target位置と
  必要な3イベント2Actionの両立は**未設計・未資格**。
  W4の単独target観測から旧S49資格をそのまま請求しない。
- Shutdownの排他leaseへの移譲はhost/action Task停止後のみ。
  Node raw stdout capture / STOP ACK / Java collector shutdown、
  途中失敗でWorld上の既存コマンド効果が残る可能性について別評価。
- 世界が先に進む場合は`EXPIRED_WORLD_ADVANCED`相当として停止し、
  古い事前姿勢で後発のゾンビを配置して成功と扱わない。

## 5. Freeze / protected owner影響判定

| 境界 | 判定 |
| --- | --- |
| S18 の凍結 manifest / tests / S1–S17 の cognitive owner / STOP | MUST REMAIN IDENTICAL |
| `NormalSessionActionExecutor` / `ActionSupervisor` / S16 / S17 / S10 | MUST REMAIN IDENTICAL |
| S49 `qualify()`, `stage_world()`, `reprobe()`, `_new_session()` | PHASE Aでは MUST REMAIN IDENTICAL、PHASE Bでは別レビュー |
| 新 W4 lease/composition adapter / synthetic receipt | PHASE A限定、認知やActionの第2 ownerではない |
| W3 HOLD×2 / Stage S `delta_m=0.100`、`min_motion_m=0.050` | MUST REMAIN IDENTICAL |
| R/V qualification/SCIENCE / W2外部 source/custody/issuer/global monotonic spend-once | NOT QUALIFIED、資格混同禁止 |

## 6. 必須の Phase A 退行・負対照

必要な試験:
1. 原 S49/Node/R/V default launch/env/argv byte-identical。
2. 原 owner選択の明示 opt-inなしでW4 moduleがimportもsession変更もしない。
3. 過去凍結証拠や旧token / grantは使用せず新fixtureIDで別試行。
4. 二重 native reader / 失効epoch / foreign task / cancelled child。
5. spawn以前・World以後の誤ったpreworld probe。
6. ledgerの欠落/重複、違うsource/session/seqの観測、preworld L0誤再投入。
7. collectorの欠落/二重、partial行・偽marker、command_hash不一致。
8. World処理前と後の同一entity ID/XYZ/姿勢及びsource関係、古い姿勢やWorld進行。
9. 元 host `NormalWorldL0` WAIT/MOVE処理とS16の独立issuer、Actionなし時のコマンド拒否。
10. shutdown/EOF/STOP ACK/Node/Java process quiescenceと失敗時BLOCKED。
11. S18 freeze regression + 19 protected blobの一致。
12. FAST/full対象の削除なし、Python 3.11/3.12 focused、Node37、Ruff/contracts、exact HEAD GitHub Actions。

`W4_S49_OPTIN_COMPOSITION_OFFLINE_PASS` は**原本コードと同じ処理を使うfake stream統合だけ**を意味する。
Phase Aの成功でも実`qualify()`のW4 leaseは依然として
`W4_S49_ORIGINAL_OWNER_LIVE_LEASE_UNDETERMINED`。

## 7. 最終判定と停止規則

**現状:** `W4_S49_DEV_LEASE_OFFLINE_ENGINEERING_PASS`（起点HEADで確認済）。
**本レビュー:** `W4_S49_OPTIN_REVIEW_CONDITIONAL_NO_GO`。
**継続:** `W4_S49_ORIGINAL_OWNER_LIVE_LEASE_UNDETERMINED`、
`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED`。

今作業は原ownerへの実接続・物理実行・新独立issuerの資格付与を行わない。
実OS級のexclusive custody、Minecraft TCP由来性、
Java server tick真正性、global spent-once、独立外部署名が不十分な間は
Minecraft Java/Nodeを起動せず、`QUALIFICATION/SCIENCE`へ昇格しない。


## 8. Phase B 接続前監査 — 原 S49 順序と Phase-A close-out（2026-10-20）

**現行原本照合:** `s49_normal_session_real_ci.qualify()` は先に
`_fetch_official_server → _ready_server → s34._new_session()` を行い、
同じ関数内で旧 `stage_world()` を起動しながら
`host.run_session(NativeObservationOnly(session),...)` を開始する。
`s34._new_session()` は通常の `MineflayerProcessSession.launch()` を呼び、
`_await_spawn()` まで行う。W4 lease はこの経路に接続していない。
この関数の元の3決定/2 Action の期待結果と W4 の向き依存2m配置は別の契約。

**判定:** 「引数だけで opt-in」「session subclass を直接入替」
「起動済み host に preworld probe を挿入」はいずれも **NO_GO**。
PREWORLD ledger より前にステージング・host reader・Action issuer が動く経路、
元の `stage_world()` と新しい W4 command window の同時実行、
元プローブを過去に遡ってpreworldと呼び替えることを禁止。

**Phase-A close-out の追加条件:** 合成 readback を生成しただけではなく、
元sessionの正常 `QUIESCE → SHUTDOWN → CLOSED` と Node exit 0、
元 lease の `OPEN(SHUTDOWN)` / `OPEN(CLOSED)`、発行済みreadの消滅と
decode/deliver数一致、BLOCKED/ABORT/DENYなしを最後に別関数で照合する。
`seal_w4_s49_optin_offline()` は外部の署名やログ原本とは無関係の
**local synthetic close-out** であり、同名のプロセスに対する OS 排他証明ではない。
途中 close-out receipt の再利用・汚染を拒否する負対照を増やす。
exact HEAD CIが確定するまでこの追加資格を PASS と呼ばない。

**Phase B の将来候補（実装・物理開始はこのレビューで許可しない）:**
1. 元 S49 標準CLI・環境・default session・3イベント2Action・stage_r分岐を
   完全不変更とし、既存 S owner内に **明示的かつ非既定の W4 DEV-only 分岐**を
   別途設計する。新しい独立的 Action/World owner は作らない。
2. 本物のWorldへアクセスできる入口を組み込む前に、W2実OS custody、
   external native source/tick、独立issuer、原本の取得前固定と
   global monotonic spend-onceが検証・認可されていることを別レビューで確認。
   未充足なら実装はoffline fake portで停止する。
3. 事前pose→ledger→W4 source-XYZ/yawで配置計画→単一Java collector
   marker→新規native event/probe→原L0/原S16→STOP ACK/Node・Java
   quiescence→最終receiptの順序を前向きに固定する。
   `drain()` やmarker文字列は物理適用時刻・server tick署名でない。
4. 原 S49 旧三イベントscripted試験と W4 単独ターゲット試験を分離し、
   旧3/2の成功をW4 1/1へ、あるいは逆に再ラベルしない。
   World外のfake stdoutが自動でpostworld frameを先読み供給する経路は不可。
5. 取消・reader Task競合・shutdown未完了・変化したWorld epochは
   fail-closedの新runとして証拠保持し、失敗したrunを補修して成功扱いしない。

**現時点の gate:** `W4_S49_ORIGINAL_OWNER_LIVE_LEASE_UNDETERMINED` /
`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` を維持。
今回の新規 World 起動、物理Action、実OUTCOME、S10 update、
QUALIFICATION/SCIENCE = すべて **0**。


## 9. Original S49 cleanup report の W4 読取ゲート（offline-only）

S49 原 `qualify()` は、World Action 3決定/2件の後に `PASS` を先に
記録し、`finally` でNode・Javaを閉じる。標準実行 (`raw_capture_root=None`) の
Node `shutdown()` が非0を返した場合や `node_cleanup_error` が発生した
場合でも、その事実が最終 `status` / `rc` に反映されない経路がある。
この実装のPASSを外側のW4入口が無条件に再利用することは禁止する。

今回追加の `audit_original_s49_cleanup_claim_offline(report=...)` は
**producer自身が記録した report の内容のみ**を検査する純関数。
少なくとも、`S49/CLOSED/PASS`、厳密な int 型 `node_exit=0` /
`server_exit=0`、cleanup error keyなし、同一sessionの
`w3_node_stdout_capture` が `COMPLETE_NODE_STDOUT`、
EOF true、shutdown ACK ちょうど1、Node exit 0、clean seal、
過剰なTCP/source/S10/science資格の主張なしを要求する。
いずれか欠損/不整合なら `W4PreworldBlocked`。
旧通常S49のreportはACKを別捕捉していないので、W4には**適格化しない**。

返るものは `UNTRUSTED_REPORT_CONTENT_ONLY` であり、
`raw_stdout_independently_replayed=false`、
`physical_run_permitted=false`。偽造されたJSONにも整合PASSし得るため、
**Node raw stdout原本と記録receiptの独立 replay（既存
`audit_w3_sealed_stdout`）は別の必須工程**。そのreplay自体も
OS外部保管、独立issuer、server tick署名の代替ではない。

同じ新moduleの
`review_w4_s49_phase_b_optin_offline(selected_mode,
explicit_opt_in,closed_composition,report,archive_root)` は、
`W4_S49_SYNTHETIC_OFFLINE_REVIEW` + 明示 true + 合成CLOSED seal
+ S49 cleanup claimの同一session一致だけを受け付ける、
**process-launch / session factory / World writer / issuerを一切受け取らない
レビュー入口**。返却の
`original_s49_qualify_wired=false` /
`live_original_owner_permitted=false` は常に不変。
標準S49、live W4、暗黙選択、foreign session、未終了、非0 exit、
勝手な物理資格主張は拒否する。

**この実装は原S49の最終statusを修正したわけではない**。
原status最終化の不備そのものは、保護19原本の別レビュー対象。
既定起動・既存stage_world・R/V、S16/S17/S10、
W3 HOLD×2やStage Sの10cm基準は不変更。

必要な判定を明確に分離する:

| 層 | 資格 |
| --- | --- |
| Phase A synthetic compose / close-out | exact HEAD CI成功ならOFFLINEのみ |
| S49 producer cleanup report | 不一致をrejectする内部整合読取のみ |
| W3 raw stdout independent replay | 別の原本照合が必要 |
| Original S49 live opt-in + W4 XYZ/yaw staging | 未実装・未資格 |
| 外部custody / TCP / Java tick / issuer / spend-once | NO_GO |
| 実World / S10 / R/V / SCIENCE | 実行も昇格も禁止 |


## 10. W3 raw stdout independent *local* replay join (offline only)

The Phase-B review now requires the existing `audit_w3_sealed_stdout(root)`
independently to decode the W3 raw JSONL file and reconcile it with the
stored W3 receipt, and then compare **the entire stored receipt** against
`S49.report["w3_node_stdout_capture"]`. The earlier report-only claim
remains available for diagnosing failures but can no longer satisfy the
explicit offline Phase-B review without the raw file. The caller passes
`report` and `archive_root`, **not** an asserted `replayed=true` dict.

This is independent *replay of local bytes*, **NOT independent source custody**.
An attacker who controls both original raw bytes and the report may rewrite
both: neither the fixture nor the replay proves Minecraft TCP authenticity,
external OS identity, physical ordering, World causation, trustworthy timestamps,
independent action authorization, or globally monotonic token spending.
A symlinked archive root, missing receipt, changed bytes, divergent SHA256,
frame count or session is rejected by the offline gate. The existing
`audit_w3_sealed_stdout` is reused unmodified; the original S49/Node/R/V
launch paths and 19 protected blobs remain byte-identical.

Only `W4_S49_CLEANUP_RAW_REPLAY_OFFLINE_V0` is produced; scope
`LOCAL_W3_RAW_REPLAY_NOT_EXTERNAL_CUSTODY` and all live/physical/S10/science
permissions remain **false**. The original S49 `finally` bug still requires
its own independent protected-owner review and prospective correction.
**Neither a local raw replay nor exact-HEAD CI success clears
`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED`.**


## 11. 原 S49 cleanup 最終化の独立修正レビュー候補（未配線）

`review_s49_cleanup_finalization_candidate(report, provisional_rc)` を
**W4側のオフライン純関数**として追加する。原 `s49_normal_session_real_ci.qualify`
（protected）を変更せず、同じ原status／終了記録を入力にし、修正後に
期待すべき `candidate_final_status` と `candidate_rc` を別々に返す。
これは過去reportの書き換え、元のS49ランナー実行、live接続ではない。

最小修正候補（**原S49に今回適用しない**）：

1. `finally` における session.shutdown の戻り値、node_cleanup_error、
   Java shutdownの戻り値／例外を保存してから、**レポート出力直前**に
   statusを最終化する。Action成功時点の `PASS` は暫定に過ぎない。
2. 以前のstatusがFAIL/BLOCKEDなら一切PASSへ昇格しない。暫定PASSであっても
   Node終了コードが0以外／欠損／bool偽装、`node_cleanup_error`キーあり、
   Java終了コードが0以外／欠損、`server_cleanup_error`キーありなら
   `final status=FAIL`, `rc=1` とする。
3. W3捕捉を明示したときはその自己申告がCOMPLETE、EOF、ACK 1、
   同一session、Node exit 0であることを要求する。未捕捉の標準S49に対して
   STOP ACKを創作しない（**元標準S49がACKを確認したとは主張できない**）。
4. cleanup中の二次例外により report 自体が保存されない可能性
   （例: `await session.terminate()`の例外）も、原S49を変更できる時点で
   別途fail-closed処理を確認する。今回の純関数テストはそれを実証しない。
5. 最終FAILは旧S49 3決定/2 Action達成自体を遡及否定するものではない。
   Actionの中間成立とセッション全体の資格を区別する。
6. 原S49を直接変更すると19 protected Git blobの一致を破るため、
   S49 ownerの独立レビュー・明示的な保護例外・既存挙動の負対照が揃うまで
   既存原本は絶対に変更しない。新runの成功を歴史的runに上書きしない。

**修正候補のテスト**: clean standard S49（ACKを推測しない）、Node非0/
例外/欠落/bool、Java非0/例外/欠落、暫定status・rc矛盾、
W3欠損／foreign、FAIL/BLOCKED非昇格を synthetic negativeで検査。
original runner自体の修正資格・外部custody・live opt-inは未成立。

`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` は不変。

**用語補足:** `reported_cleanup_consistent` は、producer自己申告による
Node/Java exitの**内部整合性**だけを示す。`cleanup_verified` という
真正証明に読める名称は使用しない。候補出力の
`raw_stdout_independently_replayed=false` /
`external_custody_qualified=false` は常時固定である。


## 13. S49 ownerへ引渡す分類と終了の原子性（2026-10-21）

Original `qualify()` は cleanup前に status=PASS, rc=0 と同時に
`classification=REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED`
（Stage Rでは `DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2`）を設定する。
このため単に終了status/rcをFAILに変えても、資格ラベルだけ残存する。
W4の候補最終化判定は status、rc、**candidate_final_classification** を
同時に計算する。Node/Java cleanup異常、分類欠損、通常/Stage Rラベル不一致、
事前にFAIL/BLOCKEDのいずれかなら分類は
`S49_SESSION_NOT_QUALIFIED` とする。真正に観測していない通常S49の
STOP ACKは推定しない。入力reportは不変とし、候補分類も
`UNTRUSTED_PRODUCER_REPORT_ONLY` に制限。

**S49 ownerの原本修正に必要:** `finally` で両processの終了、cleanup異常、
W3捕捉scopeを全回収し、その後で status/rc/classification の3要素を
1つの最終判定としてレポート書出し。異常な `terminate()` の再例外が
Java cleanup/原report書出しを妨害しないこと、旧FAIL/BLOCKEDを
PASSへ昇格させないこと、3決定/2 ActionとStage Rの正常baselineは維持。
これは**修正候補/テストだけ**で、original S49, 19 protected原本は未変更。


## 14. Phase B オフラインレビュー入口の分類整合ゲート

`review_w4_s49_phase_b_optin_offline()` は、保存済み W3 raw の
独立ローカル replay の前に原S49 report の暫定 `classification` を
`review_s49_cleanup_finalization_candidate(provisional_rc=0)` で検査し、
候補が PASS かつ分類が元のreportと一致し、producer cleanup 内部整合が
成立する場合のみ W3 replay を進める。
未定義ラベル、通常/Stage Rの取り違え、cleanup失敗と旧資格ラベルの残存は
**offline reviewでも拒否**する。これでも original S49 の実装修正、
外部 source custody の取得、実World資格、S10やSCIENCE認可はしていない。

## 15. S49 owner専用隔離パッチの負対照・保護境界（2026-10-21）

S49 original `qualify()` cleanupを隔離修正した証人ブランチ:
`self/product-self-one-command-s49cleanup-20261021`。
基点は W4 `4fb2a74410ec370aea327bab129a644ade3e9529`。
原S49のprotected blobは `fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258`、
隔離候補は `9064982380d1dc7fbc936939c9901ffecd9d8714`。

意図的な `test_s18_and_original_default_routes_are_blob_identical` の失敗は
S49原本固定契約の正常な拒否結果（CI #39515683503）。
このゲートを削除・緩和・期待SHA変更することは禁止する。
一方、証人として一時的に追加したDEV-only独立 workflow
（歴史的 commit `d56c4fc8c9dd69502c41118640eac8a0fa2f7d39`、
run #39518072719）は、Python 3.11/3.12 の両ジョブSUCCESSを返した。
対象は **実original `qualify()` を用い外部processをすべてfake化**した
Node exit7/例外/terminate二次例外、Java exit8/例外、clean、
W3 producer capture complete/ACK欠落/foreign session/nonzero exit の
局所回帰およびprospective finalization policy。これは工学DEVの局所検証
であり、source保護例外の承認、原Minecraft/Node外部custody、
S49物理資格、R/V SCIENCEを一切生成しない。

Sブランチrepository-contractsは許可パス制約を持ち、
このDEV用 workflowと専用新doc追加の恒久化は`Non-S-owner path`と
判定された。そこで **生成済みCI receiptとGit commit履歴は保持しつつ**、
これら新規ファイルは隔離branchの最新treeから取り除き、
監査説明のみ既存・許可済みの本書に収める。元のproduct
`.github/workflows/self-demo.yml` は絶対に変更しない。

**S49 owner decision待ち:** protected 19原本の明示例外/再基準化、
S #545とW4 #634の多世代乖離解決、通常/Stage Rを含む独立監査。
未承認のisolated patchを S #545/W4 #634/main へpush/mergeせず、
`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` を維持する。


## 2026-10-22: independent source-owner admission preflight (DEFAULT OFF)

**This section is a decision packet, not an owner signature, signed grant or
a W4 physical-run entry point.** At time of preparation PR #634 remained
DRAFT/OPEN (original S49 owner approval absent), while PR #635 remained
OPEN/unmerged. The protected process_session/S31A/S34/S49 blob quartet is
unchanged. No reviewed W4 subtype is installed into S49 `qualify()` or
S34 `_new_session()`.

### Fixed candidate and evidence separation

- CI-only PR #635: `008cb0a7863c3189816d7a3da5b67100cafeec9a`,
  CI run #39717268078 4/4 SUCCESS.
- Inert WSL2 instrumented DEV: `c1bc2d64d3cadb272e577cc4be919d8a9c64ff94`;
  newly independent LocalCodex-reported verification run
  `w4-normal-20261022T050205Z-a55a97b6`. Its first non-instrumented
  run with lost originals remains **UNDETERMINED**.
- PR #635 workflow + W4 synthetic DEV test integrated:
  `5ff9dfce5cce5b2831c492906ec498ef2ee5a17b`,
  CI #39745128292 4/4 SUCCESS (FAST and offline FULL).
  This is not an actual Minecraft/Node bridge qualification.
- Present preflight changes only this existing review document and
  `tests/test_self_world_stage_w4_optin_offline.py` in a separate isolated branch.
  These controls are **not** an opt-in implementation.

### Added no-World negative/route controls

The test-only adoption preflight requires the following independent checks,
all running on fake subprocesses with no physical World:

1. **Inherited environment cannot opt in:** for four representative values
   of `RELAYSELF_W4_NH1_ORIENTATION_V0`, an ordinary
   `MineflayerProcessSession.launch()` must explicitly remove that variable
   from the child process environment and continue to return the original class.
2. **Explicit opt-in cannot be guessed/coerced:** non-boolean opt-in or
   unpinned `MineflayerLaunchConfig.version` must reject *before OS spawn*.
3. **Actual S49 factory identity remains original:** for three inherited
   environment variants, `s49._new_session` must be precisely the S34
   factory, invoke the original `MineflayerProcessSession.launch` class, and
   never insert `w4_native_orientation_dev` as an implicit argument.

These checks deliberately *preserve the current fail-closed status*. They
are prerequisites for a **future distinct default-OFF DEV orchestration
proposal**. They do **not** qualify a live W4 session or physically run W4.

### Independent owner decision required before further source work

A separately authenticated original S49/source owner would have to
**explicitly and independently** identify:

- exact proposed protected file paths and expected Git blob SHA for each
  before/after state, without weakening the 19-source/S18 frozen contract;
- a **new** default-OFF, explicit W4 DEV entry point, which does not
  silently replace `s34._new_session()`, mutate the default S49 CLI,
  or issue an additional world Action/observation receiver;
- expected `STARTUP → PREWORLD → WORLD_WINDOW → HOST → ACTION_READ? →
  QUIESCE → SHUTDOWN → CLOSED` lease/collector/decoder boundary conditions,
  with valid Task delegation and cancellation cleanup;
- real raw stdout producer and independently held source custody/pin, an
  independently administered issuer identity, monotonic global spend-once
  authority, and refusal of cloned or rolled-back local ledgers;
- new prospective real-world scenario, source/World/Action authenticity,
  stop rules, physical confidence and explicit one-use run permission.

A PR comment, a green FAST/FULL CI, a synthetic `W4CollectorMarker`, or
`github.run_attempt == 1` does not prove an independently controlled
owner/grant. The latter is only per workflow run, not cross-commit global
one-use. Until the above owner and external trust conditions hold:

**`W4_S49_OPTIN_REVIEW_CONDITIONAL_NO_GO` /
`SOURCE_OWNER_ATTESTATION_UNVERIFIED` /
`W4_LIVE_NO_GO` / `QUALIFICATION_NO_GO` /
`SCIENCE_NOT_RUN`.**


## 2026-10-22 W4専用DEVオーケストレーション v1（実World到達不能）

ソース審査前の **Phase A** として、
`adapters.mineflayer.self_world_stage_w4_optin_offline.run_w4_s49_synthetic_orchestration`
を追加した。これは元S49 `qualify()` / S34 `_new_session()` に接続しない
**別の明示入口**であり、既定OFFである。

呼び出しは `selected_mode="W4_S49_SYNTHETIC_OFFLINE_DEV"` と
`explicit_opt_in=True`、完全な5件の合成JSONL bytes、
preworld probe request ID、および合成一回限りtokenを要求する。
process・server・session・Action callback・任意cmd・World handleは
引数として受け取れない。内部にのみ固定長のprivate in-memory
`OfflineProcess` を作り、`W4DevLeasedSession` と元 decoder、
元 `_await_spawn()`、元PREWORLD bridgeを使用する。

正順:
`STARTUP(adapter_started→spawn) → PREWORLD(probe→ledger1回)
→ WORLD_WINDOW(明示的な合成marker) → HOST(委譲reader1件)
→ QUIESCE → SHUTDOWN → CLOSED`。

readは独立owner Taskのlease内に限り、original process-session
decoder以外を追加しない。HOSTのframeは1件のみ受け取る。
Action/World commandはin-memory Sinkが拒否し、
`physical_run_permitted`・`action_issued`・`s10_permission`・
`science_qualified`・`external_custody_qualified`は必ずfalse。
合成markerは架空パスを表示するだけでファイルを作らない。
実Worldのmarkerやserver tick、真正stdoutを示さない。

試験は追加した成功1件・入力/順序/識別の拒否13件で確認する。
既存12件のdefault-OFF owner preflightも保持。
PR #635形式でFAST/FULL両方をexact HEAD検証すること。
プロセス起動は禁止。初回の原本欠損runはUNDETERMINEDのままとする。

ここで証明できるのは合成local orchestrationと
single-reader ownershipの**ソフトウェアDEVのみ**。
物理read-only DEV・保護元S49 source編集・新Worldシナリオ・
外部raw custody/issuer/grantは別の事前審査を要する。
`W4_LIVE_NO_GO / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`を維持する。

この入口は合成fixture内の **seq 0〜4だけ**（起動、spawn、preworld
2件、host観測1件）を入力として受け取る。上流テスト用の
6件目（seq 5）まで含めた入力は長さ検査で拒否し、
HOST以降の未読frameを暗黙に捨てることはしない。
CIのFULL有効化はあくまでオフラインpytestのみ。


## 2026-10-22 observation-only real Minecraft DEV: protected collector blocker

**`PROTECTED_SOURCE_OWNER_APPROVAL_REQUIRED` — dedicated real observation
entry is NOT implemented or offline-qualified. No real World execution.**

The new user mission requires reusing `_ready_server()` and its one Java stdout
collector, retaining original stdout bytes, and stopping before protected-source
changes if unavoidable. Current start branch is
`self/product-self-one-command-w4-offline-orchestration-20261022`, exact start
`6ee28751545584e36796ff6301830eaabc1e6bcd`. Re-fetched remote agrees. Actions
[#39760396819](https://github.com/rinsakamo/relay-self/actions/runs/39760396819)
is completed/SUCCESS for repository-contracts, lint, pytest and full-regression.
PR #634 remains at `1473c74e4448bb9a527747de0619c8e55ffbd827`, #635 at
`008cb0a7863c3189816d7a3da5b67100cafeec9a`; neither is merged by this work.

### Concrete source obstruction

The protected collector decodes `raw` with `errors="replace"` and writes the
result as UTF-8 text. Inputs `ff`, `fe`, and literal UTF-8 `ef bf bd` all become
the same saved bytes `ef bf bd`. A read-only sidecar of the collected file
cannot recover which bytes arrived. Existing logtap reads this already-collected
file, so it cannot fix the loss. Re-encoding that file as a "raw" artifact would
mislabel derived content. A second pipe reader/collector, launch wrapper,
global monkeypatch, or duplicated server-start implementation is outside the
requested reuse/ownership contract.

Four new executable regression cases in the existing allowlisted
`tests/test_self_world_stage_w4_optin_offline.py` call the unchanged
`_ready_server()` with fake subprocess pipes: valid multibyte UTF-8 preservation,
two distinct invalid-byte losses and literal replacement-character preservation.
They retain synthetic input bytes, actual collected bytes and independent hash
readback under pytest basetemp. These are boundary reproductions, not the
requested dedicated observation-entry positive/negative suite. No process,
Minecraft, World, Action, S16 OUTCOME or S10 update is created by these four tests.
The existing FAST/FULL jobs already include this test file; no CI change needed.

### Exact minimal proposed diff — NOT APPLIED

Proposed path: `adapters/mineflayer/s31a_real_server_ci.py`.
Current/protected start blob: `04a4b20278844528082f9f5c731350418ac3553c`.
Hypothetical proposal blob: `a9b9d96ce896a11fb4221e3ce6c5362eb8efb69d` (not adopted; no protected file edited).

```diff
--- a/adapters/mineflayer/s31a_real_server_ci.py
+++ b/adapters/mineflayer/s31a_real_server_ci.py
@@ -195,11 +195,11 @@

         async def collect() -> None:
             assert server.stdout is not None
-            with log_path.open("w", encoding="utf-8") as logfile:
+            with log_path.open("wb") as logfile:
                 while raw := await server.stdout.readline():
+                    logfile.write(raw)
+                    logfile.flush()
                     line = raw.decode("utf-8", errors="replace")
-                    logfile.write(line)
-                    logfile.flush()
                     if "Done (" in line and "For help" in line:
                         ready.set()
```

This proposal writes the bytes in the **same** existing collector before
readiness decoding, retaining a single stdout reader. Valid UTF-8 log content
on the target POSIX host remains byte-identical; invalid bytes are preserved
instead of replaced. Existing strict UTF-8 marker consumers may reject such a
log, which must fail closed. This small prerequisite proposal does not implement
the observation owner, grant verification, full raw evidence/cleanup contract,
or startup-failure PID evidence. It needs an authenticated original source
owner decision, default-path regression review, and explicit versioned treatment
of the existing protected-source inventory before application. The historical
19-blob guard and approved indivisible S49 four-blob variant are unchanged;
the proposal does not silently widen either one.

### Terminal scope and remaining work

Implementation stopped at the user's explicit protected-source boundary.
`OBSERVATION_ONLY_DEV_READY_FOR_NEW_GRANT` is **not earned**: the dedicated
entry, its complete required negative-control matrix and exact-entry CI remain
unimplemented. Obtain the protected collector source-owner decision first;
then implement the sidecar and all lifecycle/readback controls, fix its SHA and
require new exact-HEAD FAST/FULL SUCCESS. Fresh authenticated one-run DEV grant
has not been found or consumed. The work instruction, historical comments,
synthetic markers and CI success are not such a grant.

Host kernel identifies WSL2, but live dependency/JAR/port/PID/World/run binding
has not been qualified for an execution. No Java server, Mineflayer bridge,
World, physical Action, OUTCOME, S10 update, learning commit or science experiment
was launched. No cleanup/reap success for a live run is claimed. Existing native
OS and adapter unit tests, if run by offline CI, remain their own fixture scope.

Always retain `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN /
EXTERNAL_SOURCE_CUSTODY_UNQUALIFIED / W4_ACTION_LIVE_NOT_AUTHORIZED`.
Neither this code review nor the local synthetic collector evidence proves
Minecraft TCP authenticity or strict server-tick causality.

### Protected originals: current start versus unchanged working bytes

| Path | Before = after Git blob SHA |
| --- | --- |
| `adapters/mineflayer/s49_normal_session_real_ci.py` | `c48e22980d19c79e68c381566fb0edc09b346f1e` |
| `adapters/mineflayer/s34_native_world_cognition_ci.py` | `66728a9667734f4b7164de23f244a938a756dbdc` |
| `adapters/mineflayer/s31a_real_server_ci.py` | `04a4b20278844528082f9f5c731350418ac3553c` |
| `adapters/mineflayer/process_session.py` | `cf5a979d9da38acbe670973c11d7186ade49dbfe` |
| `adapters/mineflayer/normal_action.py` | `0ded8fa296c92076a643de08cd6fc360061e1d08` |
| `adapters/mineflayer/execution.py` | `2af25bc6808f8a4199fe2ee500d1c1dfbea25de2` |
| `adapters/mineflayer/action_outcome.py` | `502a14304c8ab9f5e37bff4a054cf2a21730d294` |
| `src/relay_self/intent.py` | `f4ef9500cd7941e5e9e07fd41ac2b6e4b4d5ac25` |
| `src/relay_self/skill.py` | `61885956810b4125721f685d449b361262b71120` |
| `src/relay_self/action.py` | `869e761cfa2646f48f12e5e8088375ae64f04607` |
| `src/relay_self/action_supervision.py` | `3320caab19d05afa74f046e3e0f143bc1aad5821` |
| `src/relay_self/learning.py` | `9fd949e94e91ded1c070d359378833f354fba577` |
| `src/relay_self/habit.py` | `edc8904753421ef836843ae736f194f5a3a39168` |
| `src/relay_self/action_feedback.py` | `8ae84e2e555550128a59a23c342f67a032a0c859` |
| `src/relay_self/action_outcome.py` | `d28bbc1745104bcd7872061bef2fe6222ceccb2a` |
| `docs/postmain-architecture.json` | `e8419c55b5535d451346fd2a9a3c42326a80aa29` |
| `docs/postmain-architecture.md` | `62b8e807d1b35a7f06d15b61e411434f57fe111d` |
| `tests/test_postmain_architecture_freeze.py` | `d343aa052541b4ee9d2ce3e00653cc1a56d681ce` |
| `src/relay_self/persistent_cognition.py` | `5d4fff3fa10bad78f98118758c8a22d53e8390fb` |


## 2026-10-22 — User-authorized narrow collector DEV patch (isolated review)

**Approval scope:** the user explicitly approved *only* a default-OFF,
same-collector, opt-in preservation of Java server stdout raw bytes.
This is not a W4 Live run grant, independent source-owner signature,
a blanket S18/19-protected-source rebaseline, or approval to merge to
main, S49, #634 or #635.

Isolation branch:
`self/product-self-one-command-w4-raw-owner-review-20261022`, based on
the evidence-only `1ecbe83fc22049c5854a390800f35f67698e6455`.
The only production edit is in
`adapters/mineflayer/s31a_real_server_ci.py`:
`_ready_server(..., *, raw_stdout_path: Path | None = None)`.

- Default `None` continues writing the original replacement-decoded UTF-8
  text file. No second Java stdout reader or alternative launcher exists.
- Explicit DEV opt-in creates an *adjacent fresh* `raw_stdout_path` with
  exclusive `xb` mode **inside the same owned startup/collector lifecycle**.
  Each received raw line is written and flushed **before decoding**; the
  previous text log and readiness detection remain unchanged.
- Different existing path, symlink (including dangling), same log path and
  foreign parent are rejected before starting Java. Raw open exceptions after
  Java spawn follow the existing startup terminate/reap path. An early collector
  failure signals the startup owner instead of waiting indefinitely on
  `ready`; subsequent failures must be checked by the future DEV caller.
- The raw byte artifact is not a Minecraft TCP packet proof, signed server
  tick, external custody, or an independently authenticated receipt.
- The earlier four irreversibility reproductions remain as historical
  **default-OFF** controls. New synthetic tests check the explicit raw path,
  invalid UTF-8 byte identity, rejection-before-spawn and failure/reap.
  No observation-only physical entry/CLI has been installed by this patch.
- The existing historical 19 protected Git blobs and their SHA guard
  expectations were **not** edited or silently updated. Since this branch
  intentionally changes the S31A blob, any versioned protection-guard
  failure must be recorded separately and resolved by a deliberate
  protected-owner variant decision; do not erase or weaken old safeguards.

**Execution gate:** Dedicated observation-only entry with no Action,
its full negative suite, exact-HEAD CI, WSL2/JAR/port/PID checks and
a new authenticated single-run DEV grant are all independent next steps.
Until then `OBSERVATION_ONLY_DEV_READY_FOR_NEW_GRANT` is **not** earned.
Minecraft/Node/Java/World/Action/OUTCOME/S10/SCIENCE run count in this
source-review change: **zero**.


## 2026-10-22 — W4 Observation-only DEV interface (offline-prospective)

Narrow collector user approval is implemented in the isolated review branch.
The **three exact protected-source alternatives** now reside in
`tests/test_self_world_stage_w4_lease.py`:

1. Historical 19-path S18 frozen original, unchanged.
2. Complete indivisible S49 four-blob v1, unchanged.
3. Complete S49 four-blob baseline with only the user-approved S31A
   DEV raw collector blob `d1006006e644add5ae7b4788e9808683e4318003`.

Mixing variants, missing peer blobs, a fifth unrelated change, or a future
edited collector blob is rejected. This is code-version recognition **only**:
no retrospective evidence mutation, original grant reuse, OS authority,
Minecraft execution, Action authorization, S10 update, or R/V science approval.

New `adapters/mineflayer/self_world_observation_only_dev.py` defines
`ObservationOnlyDevSession`, a restricted subclass of the same original
`MineflayerProcessSession`. It passes only **canonical explicit-request
observe** and **canonical shutdown** through the one inherited Node writer,
rejecting all Action/effect commands at the inherited `_send` seam.
No normal Action/S16/L0 route uses this subtype by default.

The pure `review_observation_only_dev_offline` requires same-session typed
adapter startup/spawn/before+after probes, monotonic native seq, distinct
correlated request IDs and provenance, and exact SHA of a bounded expected
console marker. It returns a frozen non-authorizing readback with
`action_count=0`, `outcome_count=0`, `s10_update_count=0` and every
physical/qualification/science flag false. **Ordering booleans are still
producer claims, not independent Java/TCP source custody or server-tick proof**.
Its conservative `time query gametime` console grammar is prospective and
must be checked against actual version-pinned server output before a run.
There is not yet any actual Java/Mineflayer orchestration or physical CLI.

`tests/test_self_world_observation_only_dev.py` adds synthetic positive
and fail-closed cases for command restriction, marker/hash tampering,
foreign session, duplicate native seq, unbound request, and producer order.
The isolated `.github/workflows/self-demo.yml` FAST owner path allowlist
and focused pytest list include these two new S-owned paths. This workflow
change is *only on the isolated review branch*, not adopted into CI-only
PR #635, and requires normal S/CI owner review before merge.

**Current gate:** exact-new-HEAD pytest/FULL must finish; any regression
must be reported as failure. Then require approved final source/CI owner
variant, a separate observation-only physical orchestration + full lifecycle
tests, immutable host/JAR/run identifiers and a fresh authenticated
one-run DEV execution grant. No generic workflow marker or boolean opt-in
can substitute for grant. Until those gates pass:

`OBSERVATION_ONLY_REAL_ENTRY_NOT_IMPLEMENTED /
 FRESH_DEV_GRANT_UNVERIFIED / PREWORLD_BLOCKED /
 QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.


### Observation-only Phase-A synthetic closed lifecycle

The same dedicated module now exports
`run_observation_only_synthetic_dev(raw_frames, before_request, after_request,
marker_line)`. This is an exact six-line **in-memory** adapter process:
original decoder and original `_await_spawn`/`_correlated_observe`, two
canonical probes, a caller-supplied **synthetic** console marker, then a
canonical shutdown. It accepts no live process/server/CLI/grant/callback,
and its fake stdin refuses every original Action method through the same
`ObservationOnlyDevSession._send` gate. The return labels
`world_marker_synthetic=true`, `physical_run_permitted=false`,
`action_issued=false`; no real STOP ACK, World tick or OS PID is claimed.

The dedicated negative controls also reject missing/extra/incomplete frames,
foreign session, replayed native seq, mismatched probe request, marker
corruption and attempts to substitute an Action command. This **does not**
close the real-process-startup/teardown/grant gate. Existing server
collector raw opt-in has no observation-only physical caller yet.


### 2026-10-22 subsequent native EOF / Java raw marker gate

A new W4-observation-only **offline** gate reuses the unchanged W3
original-session receive/capture behavior. When a fresh absolute
`raw_capture_root` was supplied at session construction,
`ObservationOnlyDevSession.shutdown_with_stdout_receipt()` invokes the
inherited `shutdown()` with the same native reader until EOF, and requires
`COMPLETE_NODE_STDOUT`, one `shutdown_ack`, `eof_observed=true`,
`process_exit_code=0` and `seal_reason=clean_shutdown`. A normal uncaptured
`shutdown()` is **not** enough for this gate. Fault-injection tests cover
missing/duplicate ACK, wrong session, seq gaps and missing raw capture.
The W3 receipt remains LOCAL Node→Python content, not TCP attestation.

`wait_for_observation_raw_world_marker` polls only an already-created,
inode-pinned original Java **raw** collector log through the existing W4
read-only cursor/tail helper. The owner would first capture the cursor,
then send a read-only `time query gametime` through the original Java
stdin and inspect a single complete expected console line. Bad grammar,
incomplete lines, duplicates, file replacement and timeouts fail closed.
Version-specific actual Java console grammar has not been verified by
this isolated offline code. The marker is still producer content, **not**
independent Minecraft tick authentication.

`ObservationOnlyDevSession.receive` now rejects overlapping reads
against the inherited one byte stream; this check provides single
in-process receipt *exclusion* but does not authenticate the original
S49 owner or install a W4 live lease.

**No runnable World entry or grant verifier was added.** In particular,
there is no assertion of a real `STOP` on Java console, no independent
Java/Node PID/port reap receipt, no cleanup completion across caller
cancellation, no host/JAR binding, no actual checked one-use grant and no
real producer trace. These missing gates continue to forbid a World.


### 2026-10-23: Inert PREWORLD inventory, CI deliberately stopped

Added self_world_observation_only_entry.py with LOCAL-only inspection of a
clean exact git HEAD, operator-supplied JAR SHA256, a single local bridge hash,
NODE_OPTIONS exclusion and a fresh empty non-symlink disposable directory.
It runs no Minecraft server, Mineflayer bridge, World commands, Action,
grant issuer or S10 updater. Its success status is always PREWORLD_BLOCKED,
with physical_run_permitted=false and external_grant_verified=false.

Local JAR checksum matching is not independent Mojang/custody attestation.
The startup environment's Java 21, Node 22, Mineflayer package identity,
actual port availability, Java/Node OS PIDs and reaps, World disposal,
real console syntax, immutable archive and fresh independently signed
one-use DEV grant are STILL NOT ATTESTED.

The user cancelled the CI queue. This new batch was committed with
[skip ci] intentionally; no new offline job is being claimed successful.
Before any real World, an explicit exact-HEAD operator-owned verification
and separate authenticated grant and actual OS process custody are mandatory.


### 2026-10-23: W4 observation-only local lifetime content join

The DEV-only pure module self_world_observation_only_lifetime.py associates
four already-produced local objects without launching Java/Node or accepting
a grant: a PREWORLD blocked inventory, a typed Mineflayer two-probe readback,
a raw Java collector marker, and a local Node/Java/collector shutdown report.
It refuses absent stop, missing ACK/EOF, corrupt session/seq, nonzero exits,
unsettled collector, marker mismatch, Action/OUTCOME/S10 increments, or
any attempt to assert external source/grant/physical/science qualification.
Negative fixtures are in tests/test_self_world_observation_only_lifetime.py.

A matching join proves ONLY self-consistency of producer-local data. The
inputs do not prove the original server/Node PID existed, that marker
events had physical order, that the source was independently witnessed,
that all OS processes and ports were reaped, or that a fresh one-use DEV
grant existed. There remains NO runnable W4 physical launcher or
independent admission authority. The user paused CI; this batch is
committed with [skip ci] and remains OFFLINE CI NOT RUN at the exact HEAD.


2026-10-23 follow-up: the lifetime join now REQUIRES the archived W3 raw
Node-stdout directory. It invokes the existing audit_w3_sealed_stdout
on the saved received bytes and compares the audited receipt with the
reported Node close object. Truncation, modification, absent archive and
foreign session must block the join. This establishes local archived
byte-content consistency, not original emission completeness, independent
custody, immutable third-party retention or a physical OS process witness.


The new raw-archive audit is deliberately read-only. No claim is made that
the archive bytes have external provenance or that local SHA256 and
same-directory receipt are an independent physical run grant. Exact-HEAD
FAST/FULL must still be run explicitly when CI is re-enabled.


### 2026-10-23 — one synthetic owner exercises entire local lifetime

Added self_world_observation_only_owner_offline.py as the next integration
rehearsal. It creates **in-memory fake Node and Java process objects**, drives
the original MineflayerProcessSession single read/decoder/capture protocol
through adapter_started → native spawn → correlated preprobe → local Java
collector file marker → correlated postprobe → original bounded Node shutdown
and sole Java STOP → original W3 byte replay → pure lifetime join. It
accepts neither --confirm nor grant/callback/real server/JAR/port arguments.
Only two observe and one Node shutdown commands and a fake Java STOP can pass.
No OS subprocess, TCP port, Minecraft World, native actor or S10 owner is
started. Negative fixtures exercise bad source, missing frame, false authority
and corrupt marker.

This is an **OFFLINE rehearsal**, not a runnable World entry or a real live
S49 owner connection. There is no external independently verified new
single-use DEV grant, separate process custody, actual PID/port/World disposal
proof or prospective science qualification. Current HEAD remains
CI_UNVERIFIED because user intentionally paused GitHub Actions; commit is
pushed with [skip ci].


### 2026-10-23: Linux/WSL2 local native disposal snapshots

A separate read-only DEV helper (self_world_observation_only_native_boundary.py)
captures the original live process-handle PID and Linux /proc starttime/boot-ID
as a LOCAL identity. Once an original owner has separately recorded Node/Java
STOP, EOF, zero exit and wait(), the helper requires both numeric PIDs be
absent (including rejecting recycled PIDs), the exact flat disposable World
directory name be absent without symlink aliases, and the reserved loopback
port 127.0.0.1:25565 be temporarily bindable. Any inspection failure,
reboot, process still alive, root still present or occupied port fails closed.
It NEVER launches/terminates a native child, deletes a World, issues commands,
or grants permission. It does NOT create a lock, own a port or verify the
original creator of the World directory. Port probing is transient/racy;
local process handle + /proc fingerprints are not independent custodian proof.

The independent signer/archivist/monotonic global spend-once ledger remains
NO_GO per selfworld-w4-independent-custody.md. This source change runs under
[skip ci] with the user's CI pause, so neither the new tests nor the previous
offline integration tests can be called PASS on the new exact HEAD. World=0,
Action=0, OUTCOME=0, S10=0 and SCIENCE=0 in this branch continuation.


### 2026-10-23 — user-approved simplified DEV real observation opt-in

The user explicitly selected a leaner DEV gate: **NO external signer, third
party archivist, or cryptographic global one-use grant** is needed to attempt
an ordinary disposable, zero-Action developer observation session. This
does NOT reclassify prior W2/W3 custody deficiencies, grant SCIENCE or
QUALIFICATION, or loosen the S10 learning/Action boundaries.

The dedicated real DEV entry is
\`python -m adapters.mineflayer.self_world_observation_only_real_dev\`
with required --confirm DEV_OBSERVATION_ONLY, --head, --repository,
--server-jar, --server-sha256, --world-parent, --evidence-parent, and an
optional unique --run-id (auto-generated otherwise). Only Linux/WSL2.
The SHA256 is an operator-local artifact pin, NOT Mojang independent
signature validation. The paths must be separate absolute roots outside
the checkout and future artifact. Per-run world/evidence directories are
created exclusively; the exact source HEAD and checkout cleanliness are
checked before any process startup. Previous run IDs cannot be reused.

The new entry composes original S31A Java _ready_server (sole RAW stdout
collector), original Mineflayer ObservationOnlyDevSession.launch
(sole Node reader with W3 byte capture), actual spawn and two explicitly
correlated observe requests, a read-only Java console
\`time query gametime\` and matching original collector marker,
then the existing bounded Node/Java STOP owner, raw byte replay/lifetime
join, local PID disappearance, loopback port bind and disposable root
deletion checks. **No Self Action issuer, S10 writer or zombie staging**
is invoked. On incomplete reaping, the disposable root is preserved
for safe manual recovery, never silently unlinked while a process may live.
Producer-local receipts and console grammar are reviewed as DEV evidence,
not independent World tick truth. Report is atomically saved to the
fresh evidence directory.

This is a source implementation only; no physical run and NO CI/focused
test has been executed on this HEAD. Commit carries [skip ci] because the
user stopped CI. A practical real-Wsl run still requires JDK21, Node22,
installed real Mineflayer, official or explicitly pinned Java server JAR
and a dedicated free local 25565 port, checked by the operator. Before
running the new real CLI, independently run offline focused tests of the
frozen exact HEAD. Earlier CI green cannot qualify the new HEAD.
All execution results remain DEV_ONLY, not SCIENCE/QUALIFICATION.
