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
