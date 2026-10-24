# W4 — 原 S49 owner への明示 opt-in 接続レビュー v0

## 2026-10-21 LocalCodex 統合監査追補

開始時の live GitHub readback は W4 `bf0b34632b1d11eb3c45b31653e147c514bec7f9`、
S #545 `3240691a29e1f02bcb89cc20cf650ac9a0e83662`、隔離cleanup候補
`52fda1926991ca41695327746d7b918337ef6118`。W4 run `39537671940` は
必須7件がすべて completed/SUCCESS、full-regression/物理ジョブはSKIPPED。
W4固定基準 `4fb2a74410ec370aea327bab129a644ade3e9529` と開始W4の
保護19 Git blobは全一致。候補との差は原S49 blobのみ
`fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258` →
`9064982380d1dc7fbc936939c9901ffecd9d8714`。本W4修正は19原本を変更しない。

### 実際に修正した互換性とfixture依存

原 `MineflayerEntityFact.name` は `str | None`。原 `qualify().reprobe()` は
対象外entityの `name=None` も `source_pair_trace` にそのまま出力する。
W4が全entityに文字列名を要求していたため、正しいzombieがいても誤拒否した。
W4読取側だけで明示nullを許容し、targetは従来どおり **名前zombie・ID一致が
ちょうど1件**、finite非負距離、event/probe/decision順序一致を要求する。
未知名をzombieに補完しない。既存原qualify fake-port回帰に正規の
`MineflayerEntityFact(..., name=None, ...)` を混在させてserializer出力を直接検査する。

また、opt-inテストの単独実行では `_offline_lines()` が内部の `asyncio.run()` を
実行中loopから呼んで失敗した。先行テストのcacheがある順序では隠れていた。
既存のS42 fixture構築と同様に `asyncio.to_thread` で構築し、テスト順序依存を除く。
検査の削除や負対照の増殖は行わない。

### cleanup候補の独立審査結果

隔離候補の原qualify fake-port 10ケース（clean、Node非0/例外/terminate例外、
Java非0/例外、W3 clean/ACK欠落/foreign session/非0）はローカル3.12でPASS。
ただし専用の外部fake probeで **Node shutdown中の `asyncio.CancelledError` が
候補の `except Exception` を通過し、Java shutdown未呼出し・最終report未保存**を再現した。
staging取消待機、Node terminate、Java collectorでも外側取消との競合を独立に扱う必要がある。
候補の成功テストだけでは採用不可。temp cleanupの例外保存はあるが、
W3 receipt取得自体の例外、取消に抵抗するtask、terminate後の強制kill/reapまでの
最終保証は未成立。保護ゲートの期待SHAは変更しない。
`PROTECTED_SOURCE_CHANGE_NO_GO` とし、候補をW4へcherry-pickしない。

S49 ownerの次作業は、元のcancelを保持しながら、bounded cleanupを所有するtaskの
終了を待ち、二次例外でもJava/collector/temp/reportへの処理を完遂する最小差分の作成。
取消注入・staging例外・temp例外・W3 receipt例外・Stage R実producer回帰を伴う
独立保護例外レビューが必要。rollbackは原blobへ戻すowner commitで行い、
過去reportや期待SHAを再生成しない。

### 実接続の境界とDEV調査

原sessionは `host → filter → reprobe → S14 → 元executor/S16 → 次event` を
順次awaitする。stagingはserver console writerでありNode stdoutを読まない。
server collectorは1つ、W3 captureは元receiveのdecode前hookで第二readerではない。
Stage Rは元reprobeの同期境界でのみHOLD successorを公開し、SelfWorld予測から
S10権限を作らない。W4 leaseは依然として原 `_new_session/qualify` に未配線。
旧3判断/2Action scriptをW4の向き依存target配置として扱うことはできない。

今回のユーザーDEV権限では、既存CLI `self_demo --mode DEV --run-disposable
--self-world-w3-raw-capture` の原S49経路を、fresh run ID・専用flat World・
外部lockfile runtime・単一owner・外部timeout/owned process-group reap監視で
検証対象にできる。外部custody欠如はQUALIFICATION/SCIENCEのblockerであり、
この既存DEV経路の調査を省く理由にはしない。ただしW4 live lease/新stagingは
未配線のままとし、DEV結果をその接続のPASSへ転用しない。
最終exact HEADのテスト/CI/DEV件数・証拠hashと報告readbackは既存#633/#392/#634に記録する。
`W4_EXTERNAL_TRUST_NO_GO`、QUALIFICATION NO_GO、SCIENCE未実施を維持する。


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


## 16. S49 producerの残存cleanup不整合をW4最終read gateで拒否

原本修正候補の隔離DEV回帰（Python 3.11/3.12 両方SUCCESS）とは
独立して、固定19原本を一切変更しない W4読取側で
`node_terminate_error`、`stage_world_cleanup_error`、
`stage_r_cleanup_error`、`temp_cleanup_error` と `error` キーを
**値が空文字でも**明示拒否する。
`stage_r_dev_enabled` は未指定/厳密boolのみ受け入れ、
`"false"` / `1` / `null` などの曖昧入力を拒否する。
producerの `status` の配列・dict・bool等はTypeErrorではなく
`W4PreworldBlocked` で閉鎖する。
W3捕捉も schema、source-scope、seal_reason、外部TCP/独立issuer/
S10/SCIENCEの虚偽attestationを含めて受入条件を統一。
ローカルW3 rawの再照合に成功しても、Phase Bの返り値は
`SYNTHETIC_LOCAL_W3_RAW_REPLAY_NO_EXTERNAL_CUSTODY` のみで
外部World資格を一切主張しない。

この変更は既存W4 readbackに限定し、S49 original source
（protected blob `fd2b06e9...`）・W4原本固定ハッシュ・
S #545・隔離候補のパッチの採否には影響しない。
`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` は維持する。


## 17. S49 original 3決定・2 Action producer narrative整合性（offline only）

W4 report readbackで単に `S49/CLOSED/PASS` および Node/Java cleanup
とW3 raw receiptが整合するだけでは、S49 **3判断・2 Actionの存在**が
欠落したレポートでも Phase B offline review が成立し得る。
このため `audit_original_s49_action_trace_claim_offline()` を
純関数で追加し、S49 owner原 report の
`decisions` 3個（WAIT→MOVE_AWAY→MOVE_AWAY、発行0→1→1、
entity/event/probe seqの一意・単調、finite距離）および
`actual_native_actions` 2個（同一session、対応event/probe/action、
terminal OUTCOME、movement 0.05m以上・finite）を要求する。

**重要:** 検証対象はproducerによる事後JSONの自己申告であり、
Action/Worldの外部真正証拠ではない。偽装者がJSON全体を一貫して
生成することは可能である。W3 raw captureのlocal replayとも独立で、
Node stdoutが実Actionの物理的因果を証明することはない。
この内部整合条件はW4のoffline readback資格の上限を引き上げない。
失敗時は `W4PreworldBlocked`、成功してもすべての
`physical_run_permitted/s10_permission/science_qualified` はfalse。
`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` は不変。


## 18. 原S49 ActionState enum のwire値との実装整合性（2026-10-21）

前回追加した `audit_original_s49_action_trace_claim_offline()` は
`terminal == "OUTCOME"` としていたが、保護された原S49の生産経路は
`receipt.terminal.state.value` を記録し、
`ActionState.OUTCOME.value == "outcome"`（小文字）である。
原producerの正常な結果を合成大文字fixtureが隠して誤拒否する
**内部の相互運用性バグ**を修正。検査側は元の
`ActionState.OUTCOME.value` 定義から値を参照し、成功fixtureも
同じ実enum値から生成する。原S49 `qualify()` をfake portsで実行する
既存テストでも、出力した2件の `terminal` をそのままW4純関数へ通し、
実際に3/2の報告を読取可能かを確認。大文字 `"OUTCOME"` と
`ActionState.UNKNOWN.value` は負対照で拒否する。

原S49の生産wire形式、保護19 SHA、Action/S16/S17の権限境界、
W3 raw replayや実World資格は一切変更しない。
報告JSONの内部整合と外部真正は別であり、
`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` は継続。


## 19. Stage R DEV owner producer claimの偽装拒否（offline only）

原S49 Stage R は `stage_r_dev_enabled=true` と
`DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2` のラベルだけでなく、
実行中の `stage_r_decision_revisions`（1→1→2）と、
`StageRDevSingleWriter.summary()` に保存された
同一L0/S14 owner・exactly one S10 HOLD・2つのAction closure・
後続 native probe に先行する first terminal・独立operator grantを
producerが報告する。W4の旧finalization候補はこの具体的な
single-writer lineage を検査していなかった。

新しい `audit_original_s49_stage_r_owner_claim_offline()` は
Stage Rラベルの producer内部整合を、原Stage R summary schemaの
source/commit/revision/session/closureに照らして検証する。
Stage Rフィールド欠損、revision変更、別issuer、grant再送、
外部attestation偽装、World未収束、reward gain、複数writer、
後続probe不一致をfail-closedに拒否する。通常S49に
`learning_in_world=true` や Stage R owner情報が紛れた場合も拒否。
本検査はPhase-B offline readbackにも適用される。

**重要:** ここで検証するのはproducerの事後JSON自己申告のみであり、
真のS10 commit・単一writer・認知改善・物理Action・外部 source custodyを
証明しない。原 S49とS10/Stage R owner原本、固定19 SHA、
実World実行境界は不変更。`W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED`
を引き続き維持する。


### Stage R の native source時間順序補正

原 `StageRDevSingleWriter.observe_original_probe()` は後続probeの
`next_source_request_id` 中のevent seqも
Action terminal後観測 `terminal_after_native_seq` より**大きい**ことを要求する。
Stage R の正常なproducer報告の必要順序は
`second_action.original_probe_seq < terminal_after_native_seq < next_event_seq < next_probe_seq`。
W4のStage R監査もこの4項の strict 単調性を確認する。
合成正常例は `second_probe=4 / terminal_after=7 / next_event=10 / next_probe=11` とし、
`terminal_after==next_event` を独立負対照として拒否する。
この検査もproducer内部整合のみで、World tick署名/外部native証拠ではない。


## 20. 原S49 source_pair_trace の読取結合（offline only）

原S49の `qualify().reprobe()` は各native event受信後に独立
correlated probeを受け取り、`source_pair_trace` に
`event_seq` / `event_kind` / `event_entities` と
`probe_seq` / `probe_entities` を記録する。
従来のW4 readbackは `decisions` 3件と `actual_native_actions`
2件を整合確認していたが、その3判断が実際のproducer報告の
event/probeペアと合うかを判定していなかった。

新しい `audit_original_s49_event_probe_pairs_offline()` で、
3ペアの存在、各event/probe seqおよび `"entities"` event kind、
対象zombie idの一意な存在、probeで測定したfinite距離と
判断の距離の一致を検査する。20種類の source欠落・順序改ざん・
対象入替・距離不正などの負対照と、原 `qualify()` のfake-port
出力をそのまま読む回帰テストを追加。

この照合はあくまでも **同一producerの事後JSON同士の整合**であり、
Minecraft TCP packet、native sourceの外部独立性、S16の実物理結果、
S10の真正なcommitを証明しない。W3 local raw replayは別ゲートに
据え置き、全permissionと SCIENCEはfalse、PREWORLD_BLOCKEDを維持。
