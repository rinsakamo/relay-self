# L-Z2b 実Gemma・実Paper統合検証（2026-11-02）

**Z2b-P/W/E: PASS_DEV。DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。** 実Gemmaが過去2 Worldだけから準備したSTATIONARYを、新規の実Paper Worldで事前固定し、exact +20 tickの水平誤差を測定した。CHEAPへの優位性、学習済みL1、B1全成立、B2、Cは主張しない。

## 実行と納品の分離

- Branch: `dev/l-z2b-real-validation-20261102`。親Draft [#699](https://github.com/rinsakamo/relay-self/pull/699)、祖先Draft [#698](https://github.com/rinsakamo/relay-self/pull/698)、追跡 [#693](https://github.com/rinsakamo/relay-self/issues/693)。独立worktreeで実施し、main・他レーン・既存PRのコードは変更していない。
- 実行HEAD: `ca4877579a69eea8351778d808e0e7459aa40bec`。GitHubと一致し、開始時7/7 SUCCESS。実行前ソース変更なし。最終納品HEADは本書を含む子PRのhead OIDを参照（実行HEADとは異なる）。
- 現在のユーザー指示を実行予算とし、HTTP completion **1**、HTTP retry **0**、新規World **1**、World retry **0**、追跡ゾンビ **1**。World内Gemma **0**、Self Action **0**、Learning admission **0**、L0権限変更・昇格 **0**。
- 原本・監査: [SHA索引](evidence/l-z2b-real-20261102/SHA256SUMS.json)、[独立Paper監査](evidence/l-z2b-real-20261102/independent-prepared-world-audit.json)、[独立帰属・cleanup監査](evidence/l-z2b-real-20261102/independent-custody-cleanup.json)、[意味監査](evidence/l-z2b-real-20261102/semantic-original-review.json)。外部保全先 `/home/rinsa/work/l-z2b-real-evidence-20261102`。失敗した初回オフラインビルドログも保全。

## 原本と実モデル

過去原本はActions [Z1b run41409851129](https://github.com/rinsakamo/relay-self/actions/runs/41409851129) artifact13124703525と [Z2a run41414648412](https://github.com/rinsakamo/relay-self/actions/runs/41414648412) artifact13127615709を新規ディレクトリへ取得した。別SHA計算プロセスでそれぞれ `31dd510390c75492c023889f7f0d876c702bebea422314fe8151474762b7e49e`、`3e70f39251d30cd16952e8a2fdf8a5141bbe0ea777c6160ba7a0b5609fb6c32d` に一致。さらに独立parserで31tickとZ2a freezeを検証し、既存レポートで代用していない。取得した全過去原本の実行前後SHAは不変。

実GGUF: Gemma-4-12B-it Q4_K_M、SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`。実ファイルhash、専用PID167622のargv/exe/GGUF mmap、localhost APIと実応答model alias `relay-self-gemma4-12b-q4km` を確認。llama.cpp **build10874 / commit e2d2c0d6a**、context8192、1 slot。RTX3060 12GB、モデルロード後VRAM8599MiB、nvidia-smiに同PIDを記録。既存Gemma/Paperは不在で、重複起動なし。

`http://127.0.0.1:8080/v1/chat/completions` へ実要求1回。native strict JSON Schema、`reasoning_effort=none`、`enable_thinking=false`、temperature0、seed1、stream/cache_prompt false。finish_reason=stop、prompt873 / completion197 tokens。途中切れ・Reasoning混入なし。原要求・応答を排他的保存し、別プロセスでprepared archiveを再構成した。新Worldの座標・UUID・結果は入力に含まれない。応答保存はWorld起動より前。

| SHA連鎖 | SHA256 |
| --- | --- |
| 原HTTP要求 | `5572136f4941b1bad3aef9134f86beca9388679e930a29d572f6148ba2041e91` |
| 原HTTP応答 | `abdcb54e06cb766ea52365e476fd216cabad008f2a24344a8bda8a41e0e4a09c` |
| prepared policy | `5ab25d00180e72b739474f4aaca93317421b2f275975cb737775b7061dbde4ed` |
| 新World原stdout | `1c20c9e7aa456cdf163edf56a3caab3eead2431febb3f40743896054730e4815` |

Gemma選択は **STATIONARY / speed=null / CONDITIONS_UNRESOLVED**。両過去WorldのIDを引用した。原理由は “Limited evidence; chase_causality is NOT_ATTESTED and no current player coordinates are available for TARGET_APPROACH.”。原反証文は “If zombie moves > 1.5m from start_xz_m, then CONSTANT_VELOCITY is false.”。

この反証文は選択したSTATIONARYと一致しない。またTARGET_APPROACHは準備時に現在座標を必要とせず、新Worldのfreeze時にplayer座標を使える。Gemma理由はこの段階の区別を混同している。原応答を訂正・再生成していない。1.5mは検証済みの許容誤差ではなく、今回の誤差がそれ未満でも予測成功へ読み替えない。

## 新規Worldと数値結果

Paper1.21.8 build60実JAR: SHA256 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`、52,811,717bytes。Java21.0.12.1、Node22.22.2、Mineflayer4.39.0。実行プラグインSHA256 `1116216bd49b9d2e9007750126c9c85fde32335f962a951d788646ddeb7ec033`。JVM PID167754とNode PID167894の/proc argv・exe・starttimeを別監視プロセスで保全し、World-local実プラグイン・configも保全。原stdoutのPaper versionとプラグインenableを照合。

run ID `27e36af3595b5841`。World UUID `0c73cad5-ad84-4112-a708-4a1fb9ff9fc4`。Zombie UUID `1427da04-3095-4045-93b1-74a8f9d17b8f` / entity ID24。AI有効ゾンビ1体を、resistance・regeneration・saturationで保護したsurvival playerに対して配置。自律L0安全性や追跡因果性の資格判定ではない。

ARM → tick27(offset0)〜57(offset30)の31連続同一World/UUID/entity ID → ENDを原stdoutで確認。offset10=tick37の行の後、offset11=tick38の前にCHEAPとprepared policyのfreezeが各1件。計算はPaper main threadの同期的な軽量算術のみ。未来結果・HTTP待ち・World pauseなし。

| 方法 / 実測 | 水平座標 x,z (m) | exact tick57との水平誤差 (m) |
| --- | --- | --- |
| Gemma準備STATIONARY | (-2.5, -1.5) | 1.4837801948120548 |
| CHEAP_STATIONARY | (-2.5, -1.5) | 1.4837801948120548 |
| CHEAP_CONSTANT_VELOCITY | (-2.5, -1.5) | 1.4837801948120548 |
| +20 tick実測 | (-3.983553173838, -1.525954708854) | — |

offset0とoffset10のゾンビ位置が同じため、今回のCHEAP速度推定は0。3方式は同点。player freeze位置は(-6.5,-1.5)。独立監査が原HTTP→policy SHA→Paper freeze→座標再計算→exact +20tick誤差を再現した。これはホストが誤差を測定できた結果であり、Gemma自身が誤差を認識した証明ではない。

Native Mineflayerはbefore seq11 / after seq46（session `74b6298f-1525-4aa4-93eb-14673a27a492`）で同じentity ID24を観測。Paper exact tickへの対応は証明していないため **CLIENT_TICK_JOIN_UNATTESTED** を維持する。プラグインmarker session `z1-client-1` はnative sessionとのjoin証明ではない。

## 独立判定

| 判定 | 結果 / 限界 |
| --- | --- |
| Z2b-P | PASS_DEV：実Gemmaが過去2経験の入力から規則を選択し両IDを引用。経験への因果依存・適切なモデル選択能力は未証明 |
| Z2b-W | PASS_DEV：別の実Worldで規則を適用し未来前に固定 |
| Z2b-E | PASS_DEV：exact +20tick、同情報時点CHEAP 2方式と公平に誤差比較 |
| B1-N | UNDETERMINED：数値予測と誤差のホスト算術は成立。モデルへ誤差を戻しておらず、モデルの数値・誤差認識は未成立 |
| B1-U | PARTIAL_DEV_ONLY：limited evidence / CONDITIONS_UNRESOLVEDの表明あり。ABSTAIN選択・適用外認識の信頼性は未証明 |
| B1-Q | NOT_ESTABLISHED：選択規則・反証文の不整合と、準備時/実行時の座標可用性の混同あり |
| B2 | NOT_RUN：誤差からのモデル構造/適用条件修正、holdout、学習なし |
| C | NOT_RUN：実験・予算はoperator指定。自律選択なし |

## 検証とcleanup

実行前の回帰207 PASS、Ruff PASS、repository contract PASS、Java plugin BUILD SUCCESS。初回ビルドはOSのJRE21にjavac21がなく別コンパイラを拾って `release version 21 not supported` で失敗した。原失敗ログを保存し、完全な既存JDK21にJAVA_HOME/PATHを固定してオフラインビルドを完了してから実機予算を使った。

World終了後に独立CLIプロセスで原stdoutを監査してPASS。別プロセスの帰属/cleanup監査もPASS。Java/Node exit0、collector settled、全owned PID消滅、25565/8080 bind可能、disposable World削除を確認。専用GemmaもSIGTERMで終了し、GPU解放後原nvidia-smiを保存。保護mainのHEAD・statusと過去原本全ファイルSHAは不変。

納品時のsaved-original readbackは68保全ファイルのSHAと原HTTP/Paper計算を再検証する。CIは保存原本の整合性検査であり、新規実機実行・ライブ物理帰属の再証明ではない。必要な次回実験は新しい実行予算で扱い、今回の予算では追加HTTP/Worldを実行しない。
