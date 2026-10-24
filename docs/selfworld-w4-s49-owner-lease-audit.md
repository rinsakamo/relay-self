# W4 原 S49 owner への DEV native-read lease — freeze 影響審査 v0

**Authority:** SelfWorld #633 / Draft #634。S18 single-transaction freeze #354。S 統合 #537。  
**基点:** `0a46a4107ece338891f36a3cb85dabb82c88cadf`（LocalCodex W4_PREHOST_OWNER_INTEGRATION_UNDETERMINED）。  
**本資料の資格:** `W4_S49_OWNER_LEASE_DESIGN_REVIEW_ONLY`。コード変更・World 試行・lease 資格化ではない。

## 0. 結論と範囲

**判定:** `DESIGN_CONDITIONALLY_ADMISSIBLE / LIVE_WIRING_NOT_AUTHORIZED`。
S18 の凍結所有者境界と両立可能な**一時的・owner-local の I/O 排他**として設計できるが、
現状の元 `qualify()` / `_new_session()` には導入されていない。
World 行動・S16・学習の別 owner を設ける設計、元 S49 既定経路の意味を変更する設計は却下。

- S18 は S1–S17 の単一認知→行動→フィードバック→明示学習 transaction を凍結する。
  `WORLD_EXEC` に認知や Action 許可・学習権限はない。lease は受信ストリームの排他と監査だけ。
- 現在の `W4OfflineS49Owner` は元 `MineflayerProcessSession` decoder、`_await_spawn()`、
  `NativeObservationOnly`、`NormalWorldL0.run_session()`、`_correlated_observe()` と
  元サーバー collector を**合成 fixture**上で結合しているが、実 S49 の live
  `session` に ownership lease を付与していない。
- **既存の W3 +0.09595129995869334m ×2 = HOLD** は固定 Stage S
  `delta_m=0.100`、`min_motion_m=0.050` に従い不変。物理 DEV/QUALIFICATION/SCIENCE
  の再判定に流用しない。
- **現時点で live `NH1 PREWORLD_BLOCKED / W4_EXTERNAL_TRUST_NO_GO` 維持。**
  新 World/Action/OUTCOME/S10 を発生させない。

## 1. 元コードで確認した接続／競合点

| 所有境界 | 元コード | 現在の意味 | DEV lease が要求すること |
| --- | --- | --- | --- |
| Node startup | `MineflayerProcessSession.launch()` | `asyncio.wait_for(session.receive())` で started を収集、後に session を返す | startup の読取も accounting 対象。`wait_for` の子 Task を owner と誤認せず、意図された委譲と束縛する |
| native spawn | `s34._new_session()` → `s31a._await_spawn()` | 元 session で spawn を単独で待つ。W4 orientation は opt-in されていない | 原 spawn を読んだ同じ session で、World 前 native yaw/pitch を取る。既定の R/V/S49 起動と分離 |
| preworld | `W4PrehostOwnerBridge` | 一回の send_observe/receive で自前 loss-accounting、非 probe は preworld ledger として保持 | live へ注入するなら*原単一 owner*が stage/host 以前に取得。ledger は事後 L0 刺激にしない |
| server World 変更 | 元 `S49.stage_world()` | 原 console writer が stage task で起動。stdin drain は World 適用完了の証明ではない | 既存 writer/collector の時点・対象・失敗を照合。**server stdout 二重 reader 禁止** |
| native host | `S49.host.run_session(NativeObservationOnly(session))` | 元 host が native event を読む。現在 `asyncio.wait_for(host.run_session(...),95)` の**子 Task**で動く | host に受信権限を**明示移譲**する。prehost Task の固定 ID をそのまま要求しない |
| probe callback | `S49.reprobe()` → `_correlated_observe()` | Entity event **後**の probe。World 配置前証拠に変換できない | 元 host の task/actor 内で probe を継続。異 request/seq を拒否 |
| original S16 | `NormalSessionActionExecutor.execute()` | `isinstance(session,MineflayerProcessSession)` を要求して元の唯一の Action owner が実行 | lease adapter は**base の真正 subclass**等で型を満たす必要がある。Action issuer や S16 を複製しない |
| execution read | `execution._receive_until()` | `await asyncio.wait_for(adapter.receive(), timeout)` を繰り返す。**毎回子 Task**が読める | 明示された S16 実行区間内で one-at-a-time read を委譲。Task ID 一個への生涯固定は不可 |
| cleanup | `S49.finally` / `session.shutdown()` | staging cancel/await → Node shutdown（raw capture 時には EOF まで read）→ Java shutdown/collector | host/action read 完了・キャンセル閉鎖を確認してから shutdown reader に移譲。失敗後に再利用不可 |

**既存オフライン試験との相違:** `W4OfflineS49Owner.run_host()` は `host.run_session()` を直接 `await` する。原 `S49.qualify()` の `asyncio.wait_for(host.run_session(...), timeout=95)` による Task 境界は再現していない。この差が、今回のオフラインPASSを元 S49 lease 資格へ昇格させられない具体的理由の一つである。\n\n**重大な罠:** `asyncio.wait_for` は別 Task で coroutine を実行し得る。
単に `asyncio.current_task() == first_owner_task` とする lease では、
正常な `host.run_session` や S16 `_receive_until` を拒否する。
逆に、`ContextVar` が継承されるという理由だけで読取可能にすると、
子 Task に継承された token を用いた順序外 read を許し得る。
必要なのは **許可された操作単位での明示委譲 + 共通の排他読取地点 + 失効**。

## 2. 推奨する最小 DEV 追加方式

**選択肢 B を推奨: 原 session の subclass に、独立した一時 read lease を束縛する。**

1. W4 DEV 専用 `MineflayerProcessSession` 派生 session を別 adapter module に追加する。
   既定の `MineflayerProcessSession`、`process_session.py`、`execution.py` を
   第一段階では変更しない。既存 S16 `isinstance` を成立させる。
2. ただし `_new_session()` は現在 base class を launch するため、
   subclass を**新しい W4 DEV 専用 owner 構築経路**から launch する。
   新しい start/World 試行 CLI は作らない。元の `S49.qualify()` へ暗黙適用しない。
   W4 orientation は `w4_native_orientation_dev=True` を明示する条件とする。
3. subclass の `receive()` が**唯一のローカル排他 enforcement point**。
   `_busy` による concurrent read 拒否だけでなく、
   `phase`、owner-local operation epoch、外部 task への限定委譲、
   cancel/exception後の `BLOCKED`、別session/再入の拒否を持つ。
   `send_observe()` も同じ request/phase に結び付ける。
4. ただし固定 `asyncio.Task` ID ではなく、
   `STARTUP`（launch の `wait_for` 子 Task）→
   `PREWORLD`（prehost 元 owner）→
   `WORLD_WINDOW`（server writer/collector と検証）→
   `HOST`（S49 host の `wait_for` 子 Task）→
   `ACTION_READ`（既存 S16 `_receive_until` 子 Task）→
   `QUIESCE` → `SHUTDOWN`（EOF drain）→ `CLOSED`
   を、**owner だけが**開閉できる臨時 lease epoch とする。
   Phase が増えても意味論的な新しい認知 owner や長寿命 scheduler を作らない。
5. 原 host callback の WAIT/MOVE admission、ActionSupervisor、
   intent/Skill/Action lifecycle、S17/S10 grant は従来の owner からしか動かさない。
   lease が行える操作は **native read 許可・観測 provenance/bytes の記録・拒否**だけ。
   World command 送信・L0 方針変更・自動再試行・学習 commit をしてはならない。
6. original task → child task の委譲は scope 名だけで認可しない。
   元 owner が `read_kind`、request/action ID、session、operation epoch、
   intended origin、`max_concurrent=1` を登録し、委譲失効後は子 Task を待ち切る。
   `asyncio.wait_for` の内部子 Task・例外・timeout・cancel 下で
   native read が未完了のまま次所有者へ移動できないことを試験する。
7. 元 S49への将来の明示 opt-in は、別契約レビュー後のみ。
   **default OFF**、環境変数混入防止、元物理結果への遡及影響なし。
   1つの session の同一 raw stream に対する元 host/probe/action/cleanupの完全接続を
   別途確認するまでは `owner_attested=false`。

**却下する方法:**
- 原 Node stdout や Java server stdout を第二の task で直接読むこと。
- S16型ガードを取り外して proxy session を無審査で許すこと。
- `asyncio.Lock` だけで「同じ owner の許可」を証明したと扱うこと
  （順番に不正 read が入り込むのを止められない）。
- ContextVar の継承だけで子 task を資格化すること。
- `asyncio.sleep` / console `say` / `stdin.drain` を真正 server tick と扱うこと。
- preworld の非probe frame を捨てたり、World後のL0 eventに再分類すること。
- 元S49 `qualify()` の内側へ直接 W4 staging や任意 Action経路を追加すること。

## 3. Freeze impact matrix（S18）

| 対象 | 想定変化 | 判定 |
| --- | --- | --- |
| S18 `docs/postmain-architecture.{json,md}` / frozen tests | 一切変更なし | **MUST REMAIN IDENTICAL** |
| S1–S17 ATT/BLF/CNC/PRD/PLAN/ROUTE/ADMISSION/EXEC_BIND/LRN/HABIT | semantic/retained owner 不変 | **MUST REMAIN IDENTICAL** |
| `ActionSupervisor`, `NormalSessionActionExecutor`, S16/S17/S10 | Action/learningの許可者と遷移不変 | **MUST REMAIN IDENTICAL** |
| `MineflayerProcessSession` の W4 DEV subclass | I/O排他、読取計測のみ（永続 retained owner でない） | **CONDITIONALLY ADMISSIBLE** |
| `_new_session()` / `S49.qualify()` | opt-in の追加でも起動・観測順序に影響 | **REVIEW REQUIRED BEFORE EDIT** |
| 原 S49 の `stage_world` / `reprobe` / `on_action` | frozen evidence/基準/権限を変えない | **NO DEFAULT CHANGE** |
| W4 source readback / receipt / preworld ledger | producer内容の添付、明示的な unqualified flags | **DEV ONLY** |
| 外部 archivist / public pin / signer / global spend-once | 別主体・別資格審査 | **BLOCKED/UNIMPLEMENTED** |
| V SCIENCE の予備登録・試行 | 現在の DEVから昇格禁止 | **NO_GO** |

**解釈上の注意:** S18凍結は S1–S17 の認知・権限・終端契約であり、
全 adapter I/O 改修を一律禁止する主張ではない。ただし S49 は別途
実World/Action資格のもとで使われた runtimeなので、
起動順序を変えた DEV 版を**同一の既資格ランナー**と呼ぶことは禁止。
新しい DEV lease の受入れは、その版を対象とする独立回帰と
原 Action/World/S10 の非干渉証拠に条件付ける。

## 4. DEVオフラインで先に実証すべき負対照

**Phase/Task:** startup `wait_for` の子 task、host `wait_for` の子 task、
S16 receive `wait_for` の子 task（すべて合法な委譲として動く）。
foreign task / copied ContextVar / invalid epoch / double-start / late-after-stop /
parent cancellation と未完了 child reader を明示的に拒否する。

**Session/ordering:** 同一sessionのprobeとrequest、厳密seq、先行 unsolicited
frame 全記録、preworld hostile entity/別session、owner token replay、
host前/後に不許可のprobe、preworldを後段L0刺激として再利用拒否。

**Action separation:** 元 `NormalSessionActionExecutor.execute()` の
`isinstance(MineflayerProcessSession)` を維持し、原 S16の収集窓（before / effect /
cleanup / after）で正常なreceiveの委譲を通す。
Actionのgrant/propose/issueなしでは **実行不能**。
fake transport 上で MOVEを実行しても世界事実・S16資格に数えない。

**Closure/cleanup:** S49 host timeout、S16 timeout、partial frame、EOF、
異常 Node exit、未完了 read、staging cancel で `BLOCKED`、
あらゆる lease 失効後に再送・再読込・grant再利用を拒否。
最終 STOP ACK/exit/collector shutdown の整合。
偽 completion は資格なし。

**Default regression:** opt-inしない `S49/R/V` session launch argv/env、
reader所有者、既存CI/凍結証拠、元 S49 WAIT/MOVE二件と
Stage S固定閾値を一切変更しない。通常実行に新しい preprobe を挿入しない。

**Evidence:** guarded `raw` decoderの受信 seq / owner-operation epoch
/ attempted receive / delivery先 / terminal stateを不変記録。
synthetic は `DEV_ONLY`、原world/physicalを示す field は常にfalse。

## 5. 次工程の受入れ条件／停止規則

1. 第一PR内で新規 **offline subclass/protocol** と負対照、S18 freeze regression、
   default path differential contract のみ。元 S49 / S31A /
   `process_session.py` / `execution.py` のprotected blobは不変が第一希望。
2. WSL2の独立 worktree で exact HEAD 新規 focused / Python FAST / Node / Ruff /
   S18 freeze を実行し、元before/after blob SHA、CI、証拠と失敗を記録。
3. 成功すれば `W4_S49_DEV_LEASE_OFFLINE_ENGINEERING_PASS` と**限定的に**評価。
   実 `qualify()` に接続していなければ
   `W4_S49_ORIGINAL_OWNER_LIVE_LEASE_UNDETERMINED` はそのまま。
4. 元 S49へのopt-in接続が不可避なら、保護ファイルを変更する理由・
   default OFF の実証・前後の挙動差分と freeze 影響をPR/Issueに**先に提示**する。
   無断で原本に修正を適用しない。既存 Draft #634を維持、mergeしない。
5. 外部保管者、原生source pin、独立 issuer、全体単調 single-use が
   資格化されるまでは **物理 W4-NH1/QUALIFICATION/SCIENCE を実行しない**。
   `PREWORLD_BLOCKED / W4_EXTERNAL_TRUST_NO_GO` を維持。

## 6. 今回この監査で資格化していないこと

この文書・同一プロセスの lease コードでは OS-level owner 隔離、
Minecraft TCP 原証拠、Java tickの真正性、外部 custody、live Session排他、
World command の適用、S49 original physical qualification、S10 grantを証明しない。
`W4_PREHOST_OWNER_INTEGRATION_UNDETERMINED` は継続。
