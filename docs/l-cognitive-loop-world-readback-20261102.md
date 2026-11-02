# 実Gemma H1→身体経験→H2：実ライブ原本成立、予測誤差自己評価は未成立

新規World1回・再試行0で元S49 Action3/S16 OUTCOME3/WAIT8×3、実Gemma OPEN2を完了し、必須独立G3・live-prefix・feedback原本監査はすべてPASSした。**A（原本から再構成できる実ライブH1/H2）はDEV成立。しかしH1の数値予測はnullで、予測誤差が生成されず、説明文には変位と時間の混同があるためB1は未成立。今回の最終目標である数値予測誤差を使った認知ループ全体は未達。** 再試行や出力の修復は行っていない。

納品は [Draft #686](https://github.com/rinsakamo/relay-self/pull/686)、baseは [Draft #685](https://github.com/rinsakamo/relay-self/pull/685)。#431/#653/#537に報告する。過去#679/#684のFAILは不変。

## Branch・HEADと実装

- Branch: `dev/l-cognitive-loop-world-20261102`
- remote開始HEAD: `51ec50537ecaa88f27b98c1199f2c5e1bda88d17`。#685 Draft/CI SUCCESSをlive確認。
- プローブ/World共通実行HEAD: `167c9128d7a7b057a46b4fb25b4faa42f8bb5d98`
- 最終HEAD: この報告と証拠コピーを含むcommit。最終SHAはPR/Issue読戻しコメントで記録し、実行HEADと区別する。

実行前に2点修正した。`argparse.REMAINDER`がaction以降のoperator引数を飲み込むため、指定runbookどおりのprepare/runが解析できなかった。明示`--`を境にoperator/元S49 argvを解析し、両CLIの回帰を追加。プローブ原報告にexecution_headを記録しprepare/run双方で同一HEADを要求、別HEAD拒否を追加した。元S49/Executor/Action issuerは変更していない。

#537現行本文の2026-10-14 DEV使い捨てrunと2026-11-01認知発達方針、および今回の明示mission/予算を適用。過去のone-shot予算は流用しない。事前登録は [新規試行](l-cognitive-loop-prereg-20261102.md)。

## オフライン検証

Python3.12 focused regression **170 PASS**。最終runゲート変更後の局所回帰 **12 PASS**。Ruff・compileall・repository contracts PASS。CLI prepare/run、別HEAD、symlink/空capture/二重run拒否、元S49/G2/feedback/EOFを含む。JDK21+既存Maven3.9.11でPaper pluginをoffline source build、BUILD SUCCESS。新規downloadなし。

実行HEADのsource-only GitHub Actions: [strict Gemma SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41382898225)、[capture/PID gate SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41382898241)。これらはWorld/認知能力の成功証拠とは別。

## 実Gemma・通信設定

既存llama-serverなし/ports空きを確認後、既存binaryと既存GGUFを1回だけ起動。llama.cpp build10874 / `e2d2c0d6a`。binary SHA `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`。

GGUF `/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf`、SHA `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`。実PID138152/exe/argv/start_ticks/cwdと当該GGUF mmap、API model/props/chat template/slot、応答model/fingerprintを保存。aliasだけから同一性を認定しない。RTX3060 12288MiB、ロード時8599MiB。実設定 `-ngl 999 -c 8192 -np 1 --no-context-shift --flash-attn on --jinja`、context8192/slot1、localhost8080。途中変更なし。

全3 HTTP要求（合成1+World2）でnative `response_format.type=json_schema`、strict true、完全10フィールド、reasoning_effort none、enable_thinking false、temperature0/seed1/stream false/cache_prompt false/max_tokens512。事前プローブは1要求/retry0、206 completion/1041 prompt、finish_reason stop、全schema/合成ID T1_W8/原HTTP SHA PASS。実World応答もstop、完全Schema PASS、reasoning_content/思考マーカーなし。**reasoning_tokensは全件未報告であり、0実測と主張しない。**

## Worldと認知系列

新規World1、retry0、Mineflayer session1、元S49 Action3/S15 clear3/S16 OUTCOME3、WAIT8窓3（24 samples）。L2 OPEN2、L2 Action/条件変更0、learning admission0、L0昇格0。Paper1.21.8-60-main@29c8822、Node22.22.2/Mineflayer4.39.0、Java21/Python3.12.3。

World UUID `2c84b716-2f78-45c5-a4a3-7b414692d6a3`、session `668ade51-8edc-4be8-93e2-7fc46d029ab8`。

| 元Action | S15 clear seq | S16 after seq | Paper WAIT8 ticks | WAIT8総変位m |
| --- | --- | --- | --- | --- |
| s49-native-move-33 | 41 | 42 | 294–301 | 0.064246601508961 |
| s49-native-move-62 | 70 | 72 | 515–522 | 0.06424660150896089 |
| s49-native-move-92 | 100 | 101 | 781–788 | 0.06424660150896111 |

W3 native seq0–109/110 frames、shutdown_ack1、EOF、Node exit0。W3はNode bridge stdout原本でありMinecraft TCP外部sniffではない。各S15 clearはnative ACKであり物理的有効clear tick全証明とは区別する。

順序はAction1→S16/WAIT8→H1受理/凍結→Action2→S16/WAIT8→H2受理/凍結→Action3→WAIT8。元ownerのrelease event以外に第二issuerを追加していない。入力はS49/S16/Paper由来のread-only身体経験viewであり、完全なSelfBody/M/P1統合や科学資格は主張しない。

## H1とH2の内容・意味

H1: OTHER_BOUNDED、KEEP_UNRESOLVED、UNKNOWN、FIRST_HYPOTHESIS、次案VARY_INPUT_DURATION（未承認/未実行）、証拠ID `[T1_W8]`。予測 `null`。172 completion/2804 prompt tokens。

> Initial data shows a discrepancy between predicted and actual wait times in a grass environment.

反証案: `Vary input duration to isolate duration effects.`

H2: OTHER_BOUNDED、KEEP_UNRESOLVED、CONDITIONAL_HYPOTHESIS、**KEEP_PRIOR**、次案VARY_INPUT_DURATION（未承認/未実行）、証拠ID `[T1_W8,T2_W8]`。予測 `null`。188 completion/4940 prompt tokens。

> Discrepancy between predicted and actual wait times in grass environment.

反証案はH1と同じ。全文は [H1 HTTP](evidence/l-cognitive-loop-20261102/world/llama-response-1.raw.json)、[H2 HTTP](evidence/l-cognitive-loop-20261102/world/llama-response-2.raw.json)、凍結原文も保存。

H1 proposal SHA `1990f8f2f4ee4769e5e24cd79733307c47ecc6f4134c3f7bcc1a56075dd71fd4`。H2 SHA `7fb8ea023a7ff9a90e4acb3154f945883055f6616766f72a8aa7413d71710ff2`。H2入力の前仮説SHA/説明/反証案/モデル族/次案/予測とAction2実測の対応を確認。H2がAction3 Outcomeを見ることはない。

**H1予測null → Action2実測0.06424660150896089m → 絶対誤差null（計算不能）。** hostは正しく `PREVIOUS_HYPOTHESIS_NO_NUMERIC_FORECAST` と報告し、0や実測値で補完しなかった。H2に数値予測誤差は渡っていない。

証拠IDは原PaperのWAIT8_TOTAL_Mに正しく解決された。だが両説明の `wait times` は時間ではないメートル変位と不整合で、「予測と実測の不一致」を当該IDだけでは支えない。H1自身は数値予測せず、H2も誤差に基づくKEEPの理由を説明していない。capability UNKNOWN→CONDITIONAL_HYPOTHESISだけを有効改訂/自己評価の証拠にしない。B1未成立の理由は通信互換性や原本監査の失敗とは別である。

## 必須独立原本監査・補足読戻し

World後に別Python processで3監査を実行し、全てexit0/PASS。

1. G3 original Paper (`--expected-live-l2-calls 2`): 3 S49/S16/24 WAIT samples、元Paper SHA/EOF、source窓。
2. live-prefix original: 3 prefix SHAが最終原本と一致、元Action/seq/World/session整合。
3. feedback original公開関数: prior-only request再構成、H1→H2 SHA、source-only ID数値解決、原本文/提案一致。`causal_interpretation_attested=false` は維持。

別readbackで全10フィールドschema制約、raw HTTP⇔journal⇔frozen⇔report、H2前仮説SHA、未来Action3混入なし、W3 byte count/hash/EOF/ACK、process custody/cleanupを追加照合した。補足照合は必須監査を置換していない。

Paper raw 734729 bytes、SHA `335db7c9cff433f427c3faf9116705f7008621a3a906f7b08b7081aa1d81c617`。事前opt-in EOF envelopeはJLine末尾`3e20`を原bytes保持で区別、改行を追記していない。W3 raw71235 bytes、SHA `76f6e89ade9cd97bcdd76da7eb4f9a6bdc85a2366c8002d88676c4af68460fb7`。

## プロセス帰属・cleanup

元runner PID138309配下のJava PID138311/PPID138309/start_ticks16645514/cwd `/tmp/relay-self-s49-zfzyl9w5`、Node PID138422/PPID138309/start_ticks16647409/cwd L専用worktreeを240 snapshotで記録。Java/Node exit0、終了後identity消滅、Java World cwd削除。Nodeのcwdは保持すべきworktreeなので存在が正しい。

Gemma PID138152は実GGUF mmap付きで別帰属、所有identityを再照合してSIGINT終了、PID消滅。8080/25565 bind PASS。過去#679/#684の原本162ファイルSHA一致/変更0。main checkout HEAD/cleanと既存他local branch refs不変。

## 判定と残る課題

| 軸 | 結果 |
| --- | --- |
| A 実ライブ認知 | **PASS（DEV限定）**：実身体経験の後に実H1/H2を受理し原本再構成できる |
| B1 前仮説への自己評価 | **NOT_ESTABLISHED**：予測null/誤差なし、変位と時間の説明混同、KEEP理由が不十分 |
| B2 有効なモデル改訂 | NOT_ESTABLISHED：構造/適用条件変更の独立holdoutなし |
| C 自律的物理実験 | NOT_RUN_BY_DESIGN：L2条件選択/変更/Action0 |

装置・通信と必須原本監査は今回成立したが、missionの数値予測誤差ループは未達。現schemaはnullを許し、ABSTAIN/UNKNOWNを正常受理する。次の別試行では、数値予測不能と明示棄権を区別し、単位・対象とKEEP理由を問うprompt/受理条件をオフラインで見直す必要がある。現在の原本/実行中設定を直さず、新規物理試行は行わない。草地固定でB2/C/学習/資格/科学を主張しない。QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。

全外部原本: `/home/rinsa/evidence/l-cognitive-loop-20261102T034000Z`。
[新規原本コピーSHA索引](evidence/l-cognitive-loop-20261102/SHA256SUMS.json)、[必須監査](evidence/l-cognitive-loop-20261102/world/mandatory-audit-status.json)、[独立読戻し](evidence/l-cognitive-loop-20261102/independent-final-readback.json)。runtime/GGUF/JAR/dependenciesはGitに含めず、原本hashと実環境receiptを保存する。
