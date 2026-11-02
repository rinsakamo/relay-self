# S #537 S1: original single-World S49 → WB L1 and M passive admission

## 2026-11-02 実World DEV結果

**`S1_REAL_WORLD_DEV_INTEGRATION_PASS / SOURCE_UNATTESTED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`**。
新規使い捨てWorld **1回、成功1、失敗0、再試行0**。
実行HEAD `0d2ff99a4fcdcb670e8356c90f3cbfc5451f95c3`、branch
`dev/s537-s1-live-wb-m-join-20261102`。同一session
`d02497ea-f6c5-455f-add1-5c37aafa2e4d`、同一Self
`self-s537-s1-native`でWB/M接続が成立した。

### 実測と監査

元S49の判断列は **WAIT → MOVE_AWAY → MOVE_AWAY**。native event/probeは
8/9、19/20、47/48。元Executorのみが2 Actionを発行し、元S15 clear 2件、
S16 OUTCOME 2件、未解決Action 0で元ownerの完了条件を通過した。

| Action | before | dispatch | S15 clear | S16 after | xz変位 m |
| --- | --- | --- | --- | --- | --- |
| s49-native-move-19 | 21 | 22 | 27 | 28 | 0.6269065734210599 |
| s49-native-move-47 | 49 | 50 | 55 | 56 | 0.6269065734210617 |

**Action1 → S16 after seq28 → 新しい元probe seq48 → 次L0 MOVE_AWAY**を確認。
単なる同一ファイル内の共存ではなく、元ownerがS16 terminalを検査してから
次イベントを処理する実行順序と、その前後のnative seqが対応する。
これは元ownerの実行順とdecoded観測のDEV証拠であり、独立Paper時系列認証ではない。

WB #669の本物のL1 CognitionSliceは3/3。SelfWorld/SelfBodyのsession・epoch・
request ID・probe seq・source refを一致させ、同じprobe Python objectを照合した。
worldはBOUNDED、bodyはOBSERVED。追加native read・L0判断・Action権限は0。
M #676の同一Pythonプロセスの元 `S49OriginalCompletedBatch` admissionは
`RECORDED / ORIGINAL_PYTHON_BATCH_RECORDED`。completed callback 1回、observer error 0。
S0内のWB L2 port欄 `NOT_SUPPLIED` は意図どおりであり、S1のWB L1欄とは別契約。

別Pythonプロセスの読戻し監査で#674 exact sourceの
`verify_native_action_evidence`をbyte照合して使用し、2 Actionのsession/ID/
dispatch/clear/after順序・変位再計算をPASS。変更コピー8件
（異session・Action ID・clear失敗・S16順序違反 × 2 Action）をすべて拒否した。
元S49/S1 reportは変更していない。raw TCP/W3全frame収録は今回のCLIにはなく、
`source_attested=false`を維持する。

### 変更・検証・cleanup

実行ロジックの追加修正は不要。S用testに、replay・古いprobe・異session拒否3件と、
observer例外をDEFERREDとして元owner継続を確認する1件を追加した。
元S49/Executor/bridge/S15/S16は#674からbyte不変。M/WB受理条件も不変。
M `9afce6bde1079f8a42aaf3c4e515ef35fc6b0396`、
WB `944db858186a4d9449946b6acdcb8c8e5998e071`はclean独立worktree。
M #683は未使用・必須依存なし。

Python3.12: 元S49/S0 **47 PASS**、固定M/WB original実装の統合 **9 PASS**。
追加後S1 test **12 PASS**（既存8＋新規4）、合計unique **60 PASS**。
Ruff・compileall・Repository contracts PASS。
contracts初回はnpm依存READMEの欠損リンクによりFAIL。その原本を保持し、
untracked node_modulesのみ一時退避したrepository範囲でPASSを確認した。
既存CIの過去失敗も訂正・削除していない。

WSL2 Ubuntu24.04、Python3.12.3、Java21.0.12.1、Node22.22.2、
Mineflayer4.39.0、Minecraft Java1.21.8。
既存S49の公式Mojangサーバーを使用（Paperへ変更していない）。
NODE_OPTIONS shimなし。実モデル呼出し0。
Python PID144960 exit0、Java PID144968 exit0、Node PID145051 exit0。
3 PID消滅、World `/tmp/relay-self-s49-2xf85pbw` 削除、
port25565通常bind PASS。main・他レーン変更なし、Draft mergeなし。

外部原本: `/home/rinsa/work/s1-live-evidence-20261102`。
[原本SHA索引](evidence/s537-s1-world-20261102/SHA256SUMS.json)、
[元S49](evidence/s537-s1-world-20261102/s49.json)、
[独立S1](evidence/s537-s1-world-20261102/s1.json)、
[別process監査](evidence/s537-s1-world-20261102/audit.json)、
[終了状態](evidence/s537-s1-world-20261102/lifecycle.json)、
[source/runtime](evidence/s537-s1-world-20261102/source-runtime-readback.json)。
索引内の監査/launcher/元verifier .pyは外部原本に保持し、owner codeをvendorしない。
[Draft PR #690](https://github.com/rinsakamo/relay-self/pull/690) /
[Issue #537](https://github.com/rinsakamo/relay-self/issues/537)。

### 未成立事項とS2最小インターフェース

S42/B0/L8原本はNOT_SUPPLIED、モデル使用量・実EnergyはUNKNOWN。
energy_debits=0は追加会計操作なしの意味で、物理Energyの実測0ではない。
元reportの歴史的分類語QUALIFIEDをR資格へ転用しない。
L1学習優位・L2自己改訂・L0結晶化・R資格・V科学成功は未成立。

S2は既存live_probe seamの同じsession/self/epoch、probe seq/request ID、
world/body source refを持つ読み取り専用L1 sliceと、直前に完了したAction ID/
S16 after seqのみを入力境界にできる。L2 workerはL0を待たせず、session・入力epoch・
期限・source ref付きの結果を既存WB read portへ返す。遅延結果は過去epoch review、
異session/replay/未来観測は拒否、timeout/errorはDEFERREDとする。
Action issuer・STOP/clear・M admission・learning ownerは移さない。
これは次段の境界整理だけで、S2実装・新規Gemma呼出しは行っていない。

## Architecture and source ownership

Base: S0 Draft #688 exact `c939dce957c946c0eba7bc1d3f163c6159703cd0`.
This S-only descendant never vendors the M/WB owner code; operator must provide
**read-only clean original worktrees pinned to exact SHA**:

- M #676 `9afce6bde1079f8a42aaf3c4e515ef35fc6b0396`
- WB #669 `944db858186a4d9449946b6acdcb8c8e5998e071`
- Original S49/S16 #674 remains the only native reader / Action issuer.

A S49 `live_probe` callback projects *already received* native Present into
original SelfBody + SelfWorld and the original pinned WB L1 `CognitionSlice`.
After the original S49 L0 loop and genuine S16 closure, original
`completed_l0` calls the S-only observer; pinned M original
`S49MAdmissionLease` consumes the SAME `S49OriginalCompletedBatch`.
S0's typed join verifies original S49/M; S1 independently matches each
WB projection with **the identical native probe Python object**, native
sequence, request and session, plus an original S16 after-seq preceding
a later original S49 probe. This does **not** create the missing original
S42/B0/L8 epochs, measure Gemma costs, mutate learning or Action.

No WB L2 / Gemma call occurs in S1. WB L1 is an information presentation,
not a learned policy, physical fact beyond native evidence, or new Action.

## Runtime command (user's actual WSL dev workspace only)

Use existing S49 #688 descendant checkout with clean approved M and WB
checkout at the two pinned revisions. Fresh unique output files under
an existing disposable evidence directory, never historical evidence.

```bash
export PYTHONPATH=src:.:tests
export S49_REAL_SERVER_CI=1
export S49_COMPLETED_L0_DEV_ONLY=1
export S537_S1_LIVE_DEV_ONLY=1

python -m tools.s537_s1_live_wb_m_dev \
  --m-owner-dir /absolute/clean/m676-worktree \
  --wb-owner-dir /absolute/clean/wb669-worktree \
  --report /absolute/new/evidence/s49.json \
  --server-log /absolute/new/evidence/server.log \
  --s1-report /absolute/new/evidence/s1.json \
  --live-world-dev
```

This is **not** an instruction to rerun any consumed QUALIFICATION/SCIENCE
one-shot. S #537 authorizes isolated, explicitly opted-in disposable DEV
Worlds under existing safe owner controls. Before running, verify Java21,
Node22, required game files, ports, original S49 owner gates, evidence
root, and ownership of Java/Node process. No inference about an external
running World or retained grant from successful GitHub CI.

## Offline success and physical gate

CI checks the real pinned M/WB source modules in one process using
synthetic original S49-shaped fixture inputs. A positive fixture is
not a physical Minecraft execution or source-independent verification.
Existing owner code rejects foreign, stale, replayed or malformed sources;
the new S1 code does not loosen either owner.

Physical S1 qualifies **only** when original S49 report PASS,
original callback returned after S16, original decision/source trace
matches S1 L1 WB sources, M same-Python original typed admission RECORDED,
and at least one S16 after→next genuine native probe is ordered in
the same World. Any missing/foreign/observer callback is DEFERRED.
Original physical Action itself cannot be retroactively vetoed.

Scope remains `DEV_ONLY / SOURCE_UNATTESTED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`; STOP ACK, independent Paper
chronology, L2 behavioral benefit, genuine learning, crystallization,
R qualification, and V causal science are not claimed.

## Next boundary

After *actual* S1 same-World DEV source join, S2 can optionally attach
the single existing S60 nonblocking L2 shadow and carry source-limited
prior cognition into the next epoch, without stalling L0. Separate
Learning owner #431 must still prove usable numeric prediction errors;
L #686 H1/H2's null forecast does not count as model revision.
