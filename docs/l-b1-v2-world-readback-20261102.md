# B1 V2実機読戻し：採点不能の認識はDEV成立、数値自己修正・定性的KEEPの根拠は未成立

新規実Gemma合成プローブ1 HTTP、実World1回・再試行0、元S49 Action3 / S15 clear3 / S16 OUTCOME3、Paper WAIT8×3、World内実Gemma OPEN2を完了。実行HEADで別プロセスのG3・live-prefix・feedback必須原本監査は全PASS。**A=PASS_DEV、B1-U=限定的PASS_DEV（数値予測なし・採点不能の認識）、B1-N/B1-QはNOT_ESTABLISHED。総合B1は部分成果であり、予測誤差による自己修正は未成立。** B2は未成立、Cは設計上未実行。QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。

## Branch・実行コードと納品コード

- 親Draft #687のlive HEAD `88f620776c22ac75a86a691624c73feea0ed28d6`、base #686 `9cfb0418efbb1f10025a2c961328ce1366334dae`。開始時10/10 CI SUCCESSをlive確認。
- プローブ・World・必須独立監査共通実行HEAD: **`88f620776c22ac75a86a691624c73feea0ed28d6`**。
- 実行worktree: `/home/rinsa/work/l-b1-v2-validation-20261102`、detached・cleanで保持。
- 子branch: `dev/l-b1-v2-world-readback-20261102`。納品worktree: `/home/rinsa/work/l-b1-v2-delivery-20261102`。最終HEADはPR/Issueの読戻しコメントで明記する。
- mainと既存他branch refsは不変。mergeなし。新規子PRは#687をbaseとする。

現行#537本文の2026-10-14 DEV運用、2026-11-01発達方針と今回の明示mission予算を照合し、今回の独立DEVを実行。過去消費grantは流用していない。事前登録とlive GitHub本文を保存。

## 実装監査・発見した制限・修正

9指定モジュールを照合。V1/V2 parser・凍結型・schema名・モードゲートは分離。14 required / additionalProperties=false、有限0..3mと棄権null、H1 null時error null、SCORED_ERRORの数値H1/T2_H1ERR/T2_W8依存、QUALITATIVE_ONLYのT1_W8/T2_W8、原S49 sole issuerとprior-only prefixを確認。実HTTPはStrict Schema/Reasoning OFFを原本から確認できる。旧#686原本のV2再分類なし。

ただし、**実行前の監査ではlive instruction内の旧「EXACT ten keys」と後段V2「14 JSON keys」の矛盾を見落とした。** 原要求の独立読戻しで確認したため、今回を「矛盾のないV2 promptの実機検証」とはしない。実HTTP schemaはV2のみで、両応答は14フィールド完結したが、schema遵守は指示の意味理解を証明しない。

子PRでV2 live指示をfourteen keys / 16..120 chars（実schemaと一致）に修正。V1のten keys / 16..60 charsは保持し、両modeを直接検査する回帰を追加。**修正はWorld後であり、追加実Gemma・Worldは0。** 必須監査は変更しない実行worktree/HEADで実施済み。納品HEADで今回の入力を新promptとして再構成してはいけない。

その他、字句guardは否定文でも「prediction error」等を拒否し得るため一般的意味検査ではない。今回の応答を修復/再受理せず、意味評価は以下で独立に行った。

## オフライン・CI

- 実行前Python3.12 focused **192 PASS**（V2/V1、Strict Schema/Reasoning負対照、null/数値、KEEP、単位、証拠ID/SHA、H1→H2、G2/G3/S49/EOF、capture/PID gate）。W3/native OS custody追加 **31 PASS**。
- Ruff、9ファイルAST構文、repository contracts PASS。JDK21 + Maven3.9.11 offline plugin build SUCCESS。新GGUF/依存downloadなし。
- 納品prompt修正後focused **193 PASS**、Ruff/diff check PASS。納品HEAD CIはGitHub読戻しコメントを参照。実行HEAD CI10/10 SUCCESSと区別する。
- 初回cleanチェックはoffline Maven生成target/で停止。生成物を外部rootへ移し、clean確認後にHTTPを実行。物理試行の再試行ではない。

## 実モデル同一性・V2合成プローブ

llama.cpp実binary `/home/rinsa/src/llama.cpp/build/bin/llama-server`、build10874 / `e2d2c0d6a`、SHA `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`。
GGUF `/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf`、SHA **`c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`**。既存健全serverがないことを確認後1回起動し、PID141141のexe/argv/cwd/start_ticks/GGUF mappingを保存。RTX3060/VRAM、API models/props/slots、Jinja原templateも保存。

実設定 `-ngl 999 -c 8192 -np 1 --no-context-shift --flash-attn on --jinja`、context8192/slot1。endpoint `http://127.0.0.1:8080/v1/chat/completions`、alias `relay-self-gemma4-12b-q4km`。全要求 `json_schema / relay_l2_b1_explicit_forecast_v2 / strict=true`、required14、reasoning_effort=none、enable_thinking=false、temperature0/seed1/stream=false/cache_prompt=false/max_tokens512。

合成プローブ1要求・retry0、**finish_reason=stop、260 completion / 1515 prompt tokens**。14 keys・T1_W8・棄権null整合・原HTTP SHA PASS。合成入力であり実World認知能力の証明ではない。request SHA `be286acbb448ee520b52909fb245e8a37f8232b9a0198a1ae33adf5701fe3b0c`、response SHA `d42fb4552fe0e78e57a2769f7046f4a69d921f367deb01f60855826c89262789`。

全3応答はstop、思考channel/markerなし。reasoning_tokensは未報告なので「0を実測」としない。

## 実WorldとH1→H2

Paper1.21.8-60-main@29c8822、Java21、Node22.22.2/Mineflayer4.39.0。World UUID `bb847b68-7a7b-4a93-814a-43aaf1cbe382`、session `63584a86-41b4-44a0-8048-8b9b71fb382f`。

| 元Action | S16 after seq | WAIT8総変位 m |
| --- | --- | --- |
| s49-native-move-40 | 50 | 0.064246601508961 |
| s49-native-move-72 | 81 | 0.06424660150896089 |
| s49-native-move-105 | 116 | 0.06424660150896111 |

H1: `ABSTAIN_INSUFFICIENT_EVIDENCE`、予測null、`FIRST_UNTESTED / FIRST_HYPOTHESIS`、OTHER_BOUNDED、UNKNOWN、T1_W8。

> Initial observation of displacement over 8 ticks on grass surface.

理由: `No prior prediction available to compare against current displacement data.`
H1 SHA `83b4fe4f46da2bb72bb7ab18e6129137e2ee534868460109ae12c6fe6a679482`。棄権を明示したが、過去予測の欠如だけでは「次試行の予測に何の情報が不足するか」は十分説明していない。

Action2実測 **0.06424660150896089 m**。H1予測nullのため絶対予測誤差null、採点不能。hostの `PREVIOUS_HYPOTHESIS_NO_NUMERIC_FORECAST` をH2へ渡し、T2_H1ERRを生成しない。

H2: `ABSTAIN_INSUFFICIENT_EVIDENCE`、次予測null、`QUALITATIVE_ONLY / KEEP_PRIOR`、OTHER_BOUNDED、UNKNOWN、T1_W8/T2_W8。

> H1 lacked a numeric forecast; comparison is based on qualitative observation of displacement.

説明: `Observation of displacement over 8 ticks on grass surface.` 反証案はH1/H2とも `Vary input duration to isolate movement.`、未承認・未実行。

H1/H2は248/262 completion、3282/5432 prompt tokens。全文・凍結SHAは[独立読戻し](evidence/l-b1-v2-world-20261102/independent-final-readback.json)。正しい証拠IDと単位、数値予測がなかった事実を認識した点は限定的B1-U。だが実測二つの一致/差異・傾向や具体的KEEP根拠を説明していないためB1-Q未成立。誤差を使うB1-Nとも分ける。棄権理由の妥当性・較正一般、前仮説の十分な意味評価は未証明。

Action1→S16/WAIT8→H1凍結→Action2→S16/WAIT8→H2凍結→Action3→WAIT8。Action3未来結果はH2入力になく、H1はAction2結果を含まない。W3 native seq0–123、124 frames、shutdown_ack1。S15 clear3はnative ACKであり全tickの物理的有効clear証明ではない。

## 独立原本監査・cleanup・保全

[必須3監査](evidence/l-b1-v2-world-20261102/world/mandatory-audit-status.json)は全exit0/PASS（G3はexpected live L2 calls=2）。原Paper/EOF/SHA・3 WAIT8、元S49/S15/S16、原HTTP⇔journal⇔凍結⇔report、V2 schema/thinking OFF、H1→H2 SHA/typed feedback/数値・target一致を追加の別processで照合。意味検査は[別判定](evidence/l-b1-v2-world-20261102/semantic-original-review.json)。形式監査PASSを意味理解PASSに読み替えない。

owned Java141376・Node141504とrunner141372を273 snapshotsで追跡し、終了後identity消滅。Java World cwd削除、Node worktreeは保持。Gemma141141も所有identity照合後SIGINT終了・消滅。8080は終了直後TIME_WAITによる初回bind失敗を保持し、listenerなし確認後、別read-only closureで8080/25565通常bind PASS。プロセス/Worldの再起動なし。

L2 Action/実験条件変更/新issuer/学習admission/L0昇格は全0。過去外部原本・tracked原本/依存を含む**6659ファイルSHA一致・変更0**、#686の63ファイル索引と原本を保持し、過去B1未成立の判定は不変。

## 残る問題・次の実験

今回は装置と原本再構成がDEV成立し、数値予測なしの認識が限定的に観測できた。数値自己修正・十分な定性的前仮説評価・モデル構造改訂は未達。prompt矛盾も今回の制限として残す。

次の別予算試行では、修正済み14-key promptを新しい合成プローブで確認後、棄権時に「欠ける観測」と「二つの実測の具体的比較・KEEP/棄却理由」を短く要求する設計を先にoffline検証する。数値出力を強制せず、棄権と採点可能予測を別評価する。B2は条件/構造修正後の独立holdout、CはL2自身の条件選択に別gateが必要。

外部原本: `/home/rinsa/work/l-b1-v2-evidence-20261102`。Gitにはbinary/runtime依存を除く83原本・検証scriptを保存。[SHA索引](evidence/l-b1-v2-world-20261102/SHA256SUMS.json)。以後の納品CI/GitHub読戻しは別delivery receiptとし、この索引の原本を変更しない。
