# RelaySelf — T1m A区間内部の受動計測 / DEV

基底：`self/dev-t1l-source-continuity-20261027` /
`59092920ff91678ed3589646857890619d9ec546`。

**DEV_ONLY / OFFLINE_IMPL_ADDED / T1M_NATIVE_UNVERIFIED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
T1l の既存 1,200/2,000 WorldTick PASS は別の
`DEV_WORLD_OBSERVED` として維持する。

## 目標

T1k の 191–491ms 拒否は、T1lによりNode同一時計の
A＝challenge送信→snapshot受信の複合区間に集中した。
B/C＝Node受信後の評価には顕著な集中がない。

T1mは元のT1f admissionを修正せず、A区間内部で
**JVM同一時計の受信→callback→送信処理復帰** と
**Node同一時計のchallenge送信→snapshot受信** を
challenge IDとPaper indexでjoinし、環境依存の外れ値を調べる。
前者の経過時間と後者の差は、片道通信遅延ではない。
直接JVM時計の絶対値からNode時計の絶対値を減算しない。

## 変更概要

- Paper Plugin config `t1m-timing-dev: false`（既定OFF）。
  `t1f-snapshot-dev=true` かつ `adaptive-tick-observer-dev=true`
  でだけ有効。既存 incoming challenge と既存 tick callback 内に
  `T1M_DEV_JVM_CHALLENGE_RX` と `T1M_DEV_JVM_CALLBACK` を追加。
  JVMの `System.nanoTime()` による
  `rx_to_callback_ns` / `callback_to_send_return_ns` は
  それぞれ同一JVM内の経過時間。
  **sendPluginMessage()の復帰は受信保証ではない。**
  JVM loggerを含めこの計測自体が負荷を増やす可能性がある。
- Nodeは `RELAYSELF_T1M_TRACE_DEV` が新規絶対パスのときだけ
  `wx` で専用sidecarを開く。元の `paper_snapshot` envelope、
  seq・protocol data・single reader・Motor issuerは不変。
  各challengeの `node_sent_ns`・write返却、および各snapshotの
  `node_received_ns`・evaluation終端を保存。
  `perf_hooks.monitorEventLoopDelay({resolution:10})` の
  区間最大値を参考値として記録するが、特定のcallbackや個別packetへ
  原因を帰属しない。サイドカーは完全にDEV-onlyで既定OFF。
- `adapters/mineflayer/t1m_timing_join_dev.py` は
  `paper.log` / `t1m_node_timing.jsonl` /
  原本 `native.jsonl` を独立に照合。challenge IDとindex、
  WorldTick、Node同一時計の A、元のstatus・reason・age、
  JVM同一時計の2区間を比較。不一致・欠落・重複は
  `source_integrity_violations` として記録し、判定を捏造しない。
  既存 source ADMITTED/STALE/MISSING等は絶対に再判定しない。
- 元T1eの `t1m_source_soak` caseは、T1lと同じ既存
  `run_source_soak` の単一readerを利用し、Actionを送らず
  M0/P1連続会計する。新規source validationの原本診断を保ち、
  JVM/Node sidecarを正常cleanup後に照合する。

**既存制約はすべて維持**：
Node causal-age 150ms・Node評価25ms・T1f challenge上限2400、
T1lのindex2300停止境界、M0/P1式、既存L0/S49所有権、
no synthetic gap/WAIT、S18保護、QUALIFICATION_NO_GO。

## LocalCodexの検証順序

1. WSL2 Ubuntu24.04 / Python3.12 / Node22 / JDK21。
   branch `self/dev-t1m-causal-age-instrument-20261027` で
   専用worktree。既存のT1l World原本とT1k原本は読み取り専用。
2. Node tests：`node --test adapters/mineflayer/t1m_paper_timing.test.mjs
   adapters/mineflayer/paper_snapshot_admission.test.mjs`。
   Python3.12：`PYTHONPATH=src:tests python3.12 -m pytest -q
   tests/test_t1m_timing_join_dev.py tests/test_t1l_source_diagnostic_dev.py
   tests/test_t1l_source_soak_dev.py`。
   Java21 Pluginビルド、Ruff、focused後のFAST。失敗時は安全境界を
   緩めず隔離修正。main mergeやFULLは行わない。
3. 使用中の正確なJAR/bootstrapを前回T1l原本から確認。
   新規使い捨てWorldごとに空の絶対outputを使用する。
   まず通常負荷を2試行、各600～1200tick。
   ```sh
   PYTHONPATH=src:tests python3.12 -m adapters.mineflayer.t1e_native_dev \
      --output /NEW/ABSOLUTE/T1M-BASELINE-001 \
      --paper /EXISTING/READONLY/PAPER-1.21.8.jar \
      --plugin /EXISTING/BUILT/relay-metabolism-dev.jar \
      --bootstrap /EXISTING/READONLY/BOOTSTRAP \
      --confirm T1E-DISPOSABLE-DEV-ONLY \
      --soak-ticks 1200 --cases t1m_source_soak
   ```
4. 軽度ホスト負荷の比較は別の新規World・別の明示的な
   負荷条件とする。ベンチマークのためにT1fの上限を変更しない。
   高負荷でSTALEが生じたらFAILとsource latchを保持し、
   再接続や実行再試行で同一sessionに見せかけない。
   過剰負荷でホストやMinecraftを不安定化させない。
5. runごとにPaper JVM `rx_to_callback_ns` /
   `callback_to_send_return_ns`、Node A、event-loop-delay window、
   causal-age median/p95/p99/max、JVM/Node原本結合率、
   source seq・WorldTick・challenge index、拒否数、
   M0/P1会計行・0 Action/0 credit・cleanup・PID/portを報告。
   Sidecarを入れたことで測定分布が変わる観測バイアスも記録し、
   T1l非計測結果と一概に比較しない。

### 今回のChatGPT環境で成立していること

GitHub隔離DEVへのソース・テスト・runbookのcommit/push。
実WSL2/Paper試験、Python3.12/Node22/Java21のテストはこの環境では
まだ行っていない。JVM/Node実原本のjoin、性能原因の確定、
source長期安定性の新たな実証はまだ主張しない。
