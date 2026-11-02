# PR #682 実ローカル検証 — プローブPASS / World実行準備FAIL

**実GemmaのStructured JSON / Reasoning OFFプローブはPASS。実WorldはW3 captureパスの準備不足でFAIL、再試行0。H1/H2は未到達で、認知能力の否定結果ではない。**

対象は [Draft #682](https://github.com/rinsakamo/relay-self/pull/682)、納品はその子 [Draft #684](https://github.com/rinsakamo/relay-self/pull/684)。#431/#653/#537。main・他レーン・過去 #679 FAIL原本を変更していない。

## HEADと変更

- Branch: `dev/l-gemma-local-validation-20261102`
- 開始base: `1edc89716af7253341165d44bd0e48398a470fa6`
- 実プローブHEAD: `ec9a4c27ea37d180d9506b7b01c7557f27b176fa`
- 実World HEAD: `d8043917ffb59d4d5470071638ed71dc20a53937`
- World後の修正HEAD: `3bcddd671c22e3ddefe5f6536bf73702bdcc6288`
- 最終HEADはこの報告と証拠を含むcommit。実行HEADとは異なる。最終SHAはPR/Issue最終コメントに記録する。

プローブ受理が10キーと一部IDだけを検査していたため、全フィールドの型・enum・文字長・配列長/一意性・有限数値範囲と重複JSONキーを検査するよう修正。実GGUFテンプレートにある `<|channel>` / `<channel|>` もcontent内の拒否対象に追加した。

World後には、L live-prefixモードで実在する空の絶対・非symlink W3 captureディレクトリをJava起動前に要求する検査を追加した。欠落・相対・ファイル・使用済・symlink・symlink祖先を負対照で拒否。S49/S15/S16 issuer、Executor、L2のAction権限は変更していない。この修正後に新Worldは起動していない。

## 検証

初期189 PASS、World前271 PASS、World後修正277 PASS。元S49 cleanup、実Node/Javaの不活性fixtureによるcustody、G2/G3、H1/H2 SHA、未来Outcome拒否、EOF/過去FAIL非昇格を含む。Ruff0.16.7・構文10ファイル・repository contracts PASS。Paper pluginを既存Maven3.9.11/JDK21でsource buildし、Java自己テスト113+15 checks PASS（Minecraftなし）。Python3.12.3、Node22.22.2、Mineflayer4.39.0を実import確認。

初回拡張テストはPATH不足で12 FAIL/256 PASS、初回buildは`mvn`未解決、指定PythonにはRuffがなく失敗。全初回ログを外部rootに保存し、既存絶対パスで修正後再検証した。初期失敗を隠していない。

修正HEAD [3bcddd67のGitHub CI](https://github.com/rinsakamo/relay-self/actions/runs/41372599820) は8/8 SUCCESS。CIはsource-onlyで物理成功の証明には使わない。最終HEADのCIは最終コメントで別確認する。

## 実モデルの同一性と設定

既存llama-server/Paperなし、8080/25565空きを確認して、既存binary/GGUFを1回だけ起動。downloadなし。

- llama.cpp `0.4.0-dev build10874 / e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`、API fingerprint `b10874-e2d2c0d6a`。
- binary `/home/rinsa/src/llama.cpp/build/bin/llama-server`、SHA `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`。
- GGUF `/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf`、SHA `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`。
- GGUF実metadata: `general.architecture=gemma4`、`general.name=Google_Gemma 4 12B It`、48 blocks。APIはQ4_K Medium・11,907,350,576 params。alias単独で同一性を認定していない。
- 実PID129904のexe/argv、GGUF mmap2箇所、`/v1/models`・`/props`・`/slots`とテンプレート原文を保存。
- 実argv: `-ngl 999 -c 8192 -np 1 --no-context-shift --flash-attn on --jinja`、loopback8080。APIもcontext8192、slot1を確認。
- RTX3060 12288MiB、ロード後全体8599MiB、GPU process PID129904。allocation単位の解放は主張しない。

実buildのserver-common.cppはnative `response_format.json_schema.schema`を読み、reasoning_effort noneとboolean enable_thinking falseを処理する。実テンプレートはOFF時に空のthought channelをprompt側へ閉じる。これは応答が思考を漏らさない保証ではないため、原応答も検査した。関連する上流報告は [llama.cpp #30256](https://github.com/ggml-org/llama.cpp/issues/30256)。

## 実HTTP事前プローブ

合成入力のHTTP能力試験であり、実身体経験ではない。要求1、retry0。完全な10フィールドschema、`strict=true`、`reasoning_effort=none`、`enable_thinking=false`、temperature0、seed1、stream/cache_prompt false、max_tokens512を原文で確認。

**PASS:** HTTP200、完全JSON、全schema制約と`T1_W8`/trial1を再検証。`finish_reason=stop`、completion206/prompt1041 tokens。`reasoning_content`なし、`completion_tokens_details.reasoning_tokens`は未報告（測定値0と断定しない）、content思考マーカーなし。応答model/指紋は当該実serverと一致。原HTTP SHA読戻しPASS。json_object/Reasoning ONへのfallbackなし。

- request SHA: `2bc8c1794e2da7c9c3747fbc73796a5b8817db899064ee1a247c1f821bf26410`
- response SHA: `b77854ffefa48254734413227104b9d2637d7e98356df3846fbeb169a13ac6d7`

[成功プローブ原報告](evidence/l682-local-validation-20261102/gemma-strict-wire-probe/gemma-structured-preflight.json)、[要求原文](evidence/l682-local-validation-20261102/gemma-strict-wire-probe/llama-request-1.raw.json)、[応答原文](evidence/l682-local-validation-20261102/gemma-strict-wire-probe/llama-response-1.raw.json)。合成応答の予測0.4mや説明をH1として扱わない。

## Worldの第一terminalと監査

新規World1、session確立0、retry0。実Paper1.21.8起動後、`W3CaptureRejected: fresh absolute non-symlink evidence root required`。実行担当が新しいnative captureディレクトリを事前作成し忘れ、W3 constructorが拒否した。runnerはその条件をJava後にしか検査していなかった。新しい原本を後付け作成して成功へ変えず、そのままFAILを保持した。

元S49 Action0 / S15解除0 / S16 OUTCOME0 / WAIT8窓0 / 実World Gemma要求0 / 有効OPEN0。native sequenceはcaptureがなく**UNAVAILABLE**。Node spawnはW3 constructorの前に試行されるが、原reportにNode PID/exitなし。起動ゼロやSTOP ACK成功を推測しない。

H1/H2・選択した実World証拠ID・H1予測/次実測/誤差は全て未生成。実HTTP総要求は合成プローブの1回のみ。

必須監査を別processで実行し、全てexit1/FAIL:

1. G3 `--expected-live-l2-calls 2`: complete World runtime不成立。
2. live-prefix: complete World runtime不成立。
3. feedback original公開関数: session_id自体がなく再構成不能。元toolにはCLIがないため、公開関数を明示的に実行。

[World原報告](evidence/l682-local-validation-20261102/world/report.json)、[Paper raw原本](evidence/l682-local-validation-20261102/world/paper-stdout-original.log.raw)、[必須監査結果](evidence/l682-local-validation-20261102/world/mandatory-audit-status.json)。Paper8353 bytes、SHA `827436e99b0ef8b6e01e679666107f51a86be4b26e341ab7956fe0250ad75b45`、通常logとraw一致。事前宣言されたEOFの末尾は`3e20`で、形状のみ認識。完全World/Paper窓の合格ではない。

cleanup: 原runnerのPaper exit0、server/collector reap記録あり。現時点のJava/Node/llama-server process0、8080/25565 bind成功、`/tmp/relay-self-s49-*`残存0。所有Gemma PID129904はidentity確認後SIGINTで終了しPID消滅。**Worldの外部snapshotにargv照合ミスがあり、Java PID/cwdを捕捉できていないため、exact owned PID/cwdの独立帰属監査は未成立。** 空集合をcleanup PASSにしない。誤った初期派生cleanup判定も外部rootに保存し、[独立最終読戻し](evidence/l682-local-validation-20261102/independent-final-readback.json)でこの限界を訂正した。原ログ/原reportは変更していない。

過去 #679 rootのトップレベル原本とnative原本35ファイルは実行前後SHA一致、変更0。過去World FAIL・512 tokens length・OPEN0・必須監査FAILを維持。

## 認知判定と次の課題

| 判定 | 結果 |
| --- | --- |
| A 実ライブ認知 | NOT_ESTABLISHED：装置準備で停止、H1/H2未到達 |
| B1 前仮説の自己評価 | NOT_EVALUATED：前仮説/次実測/誤差なし |
| B2 有効なモデル改訂 | NOT_ESTABLISHED：独立holdoutなし |
| C 自律的実験 | NOT_RUN_BY_DESIGN |

設定互換性は今回の合成プローブでPASS。実Worldの長いpromptの512 token完結性・認知能力は未検証。正式学習admission0、L0昇格0、QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。

次回は別試行として実行回数・権限を再照合し、新rootにW3用空ディレクトリを作成してJava前gateを通す。外部snapshotはabsolute jar pathを含むargvで照合する。H1→Action2誤差→H2の意味を実World原本から検査することが残る。今回の試行を再試行していない。

全外部原本root: `/home/rinsa/evidence/l682-local-validation-20261102T013000Z`。
[GitHub保存証拠のSHA索引](evidence/l682-local-validation-20261102/SHA256SUMS.json)は外部原本からbyte一致コピー47ファイルを検証した索引。GGUF・runtime依存・JARはGitへ追加していない。
