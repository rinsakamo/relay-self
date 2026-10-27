# RelaySelf — T1o: 通常DEVの同期Node timing traceをOFF（明示ON/OFF A/B）

Baseline: T1n HEAD `9e5b98e5379cf89efb86dabe2383c94fd536993e`.

**DEV_ONLY / OFFLINE_IMPL_ADDED / T1O_NATIVE_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
T1nの3正常World＋1起動FAILと約59ms writeSync局所化は**独立した既存証拠**。T1o新Worldは、この実装の時点ではまだ観測していない。

## 設計変更は最小限

元の `bridge.mjs` はすでに `RELAYSELF_PAPER_TICK_TRACE_DEV` が未指定であれば同期trace OFF。T1e DEVランナーが毎回この環境変数を設定していたため、通常DEVでも毎tick同期 `writeSync` がクリティカルパスに入っていた。

T1oでは**`bridge.mjs` やT1f admission、Node stdout、snapshot wire、Motor issuerには触れず**、T1eランナーだけで、`--node-trace off|on`（既定`off`）を導入。

- **通常DEV/OFF**：`RELAYSELF_PAPER_TICK_TRACE_DEV` を明示的に削除。新しい `node_timing.jsonl` は存在しない。Pythonの `measure()` は正規 `native.jsonl`（Node stdoutを唯一のreaderが取得した原本）でADMITTED/seq/Action等を集計。Node固有の相対trace timestampがない指標は`None`、もしくは`node_clock_trace_available=false`として未計測を明示する。source/ledger/cleanupを未計測扱いにはしない。
- **A/BのON**：同じ `t1l_source_soak` を`--node-trace on`で起動したときだけ既存traceを生成。ONとOFFは**別の新規DEV World**で行う。診断は元sourceの判定を上書きしない。
- **明示的診断ケース** `t1m_source_soak` / `t1n_source_soak` はケース自体が診断ONを意味するので、過去のタイミング詳細契約を維持する。
- OFFではtraceファイル不在を検査。ONでは既存traceが原本nativeの対象イベントの完全なサブセットに一致し、Node単調clockを持つことを検査する。診断欠落はFAILだが元source成功やcleanupを捏造しない。
- 過去のtrace付きレポートをread-only再解析する `measure(root,{})` は、その既存ファイルがある場合に従来のtraceを使用する。**新しいrunは必ず明示的な`node_trace_enabled`をレポートに保持**。
- trace OFFでも、snapshot payload内の既存`challenge_sent_ns`/`received_ns`/`evaluation_completed_ns`/`age_upper_ns`は元nativeで取得できる。これらは元T1f admissionに由来し、Node traceとは別。OFFでもA分布が分析できる一方、legacy timing-only `node_shadow_emit_to_clear_applied_ms`などはUNKNOWN。

**不変**：150ms因果年齢上界、25ms評価budget、T1f 2,400 challenge cap、T1l 2,300 stop guard、M0/P1式、単一native reader、Action/STOP所有権、latch、R/V/SCIENCE保護。

## LocalCodex: 最短の実機検証

作業branch：`self/dev-t1o-trace-optin-ab-20261028`。最初にremote HEAD/祖先/cleanを確認。T1n既存原本、Draft #545/#634/main、S18、R/Vは不変。

**Focused/FAST**：
```sh
PYTHONPATH=src:tests python3.12 -m pytest -q \
  tests/test_t1o_trace_policy_dev.py \
  tests/test_t1e_native_dev.py \
  tests/test_t1l_source_diagnostic_dev.py \
  tests/test_t1l_source_soak_dev.py

# focused成功後に既存Python 3.12 FAST、Ruff/contracts。
# 必要ならNode22関連テスト。Javaソース変更なし、既存JAR SHA確認でよい。
```

実行前に`--help`、既存Paper1.21.8、今回使用するPlugin JAR SHA、物理runtime rootを確認。
**新Worldを2個**作る（出力先は毎回新規絶対path）：

```sh
# OFF: 通常DEVの新既定値。node_timing.jsonlなしで1200連続tickを確認。
PYTHONPATH=src:tests python3.12 -m adapters.mineflayer.t1e_native_dev \
  --output /NEW/ABSOLUTE/T1O-OFF-001 \
  --paper /EXISTING/READONLY/PAPER-1.21.8.jar \
  --plugin /EXISTING/VERIFIED/relay-metabolism-dev.jar \
  --bootstrap /EXISTING/READONLY/BOOTSTRAP \
  --confirm T1E-DISPOSABLE-DEV-ONLY \
  --soak-ticks 1200 --node-trace off --cases t1l_source_soak

# ON: 同条件・別World、明示的にtraceだけON。
PYTHONPATH=src:tests python3.12 -m adapters.mineflayer.t1e_native_dev \
  --output /NEW/ABSOLUTE/T1O-ON-001 \
  --paper /EXISTING/READONLY/PAPER-1.21.8.jar \
  --plugin /EXISTING/VERIFIED/relay-metabolism-dev.jar \
  --bootstrap /EXISTING/READONLY/BOOTSTRAP \
  --confirm T1E-DISPOSABLE-DEV-ONLY \
  --soak-ticks 1200 --node-trace on --cases t1l_source_soak
```

本比較はCPU負荷を意図的に加えない。ホスト環境/TPS/開始時刻/論理条件は記録し、必要な場合のみ交互にOFF/ONを別Worldで追加反復する。M0/P1会計とsource/cleanupがPASSしたときのみ通常試験PASS。期待が外れたら元FAILを保存し、修正・新Worldで再実行する。DEVでの修正・再試験は追加許可不要。

### 必須の検証項目

- OFFでNode traceファイル**0**、native Paperと会計1,200/1,200、元Paper全ADMITTED、native seq・WorldTick欠測0、session identity不変、元snapshotのage分布が取得できる。
- ONでtraceファイルが存在し、正規native原本の対応イベント数・seq・内容が一致し、Node単調時計がある。
- OFFでも診断用trace欠落を理由にsource FAILへしない。ONの破損・欠落は診断FAIL。
- 両WorldともMotor/MOVE/EAT/STOP/Resume/LLM/TPS actuator0、M0式・P1式不変、食事credit0、架空WAITなし。
- 各Worldで真のshutdown ACK + connection_end、Node/Java exit 0、PID回収、port再bind。
- native原本・World全ファイル・報告・起動argv/envのSHA256を保存し読み戻す。
- A median/p95/p99/max、超過150ms数、最初の拒否とlatchを比較する。実効TPS、T2会計、源のsource seqも比較する。
- ON/OFFの差は1回ずつでは因果断定できない。OFFで外れ値が減る傾向を観測できても、全スケジューリング停止が解消したとは報告しない。T1n59msを新Worldの原因へ遡及適用しない。

### CI/資格

小変更：構文・Ruff。モジュール成立：Python3.12 focused+FAST。Node22関連必要に応じて。Java変更なしならSHA検証のみ。FULL/main merge/R/V資格World/SCIENCEは実施しない。
commit/push、local/remote/clean照合、Issue #150/#627/#537/#616へ結果報告・本文読み戻し。#626はモデル式未変更なら不要。

最終判定は実測結果に応じて `DEV_ONLY / DEV_WORLD_OBSERVED` または FAIL保持、常に `QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。T1o実World未実施時は `T1O_NATIVE_UNVERIFIED` を維持する。
