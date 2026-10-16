# R #575 / V8 — seed62101 実Paper停止Worldの5条件複製・別runner原証拠再読査

2026-10-17 JST。**DEV source evidence only**、V8 SCIENCE 0、工学的QUALIFICATIONではない。

## 実行ソース

- S producer GitHub Actions [#38976820099](https://github.com/rinsakamo/relay-self/actions/runs/38976820099):
  exact S HEAD `537947b0011620769fd72da5f78320267ea8a614`、
  attempt1、completed **SUCCESS**、実Paper1.21.8 build60 JAR
  SHA `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`。
  Java一回、正常STOP、exit0、port25565解放。Mineflayer/Node 0。
  この実World起動はseed62101原World一つのみ。5条件Worldは停止バイト複製であり、
  各クローンは一度も起動していない。
- S original archive #12078239418 (90日、expires 2027-01-14)、
  GitHub provider artifact SHA256
  `301cc25bae4c796ca7d19fab89cdd0f85f748562abd9f10cffe94ba9daf72200`。
  原本のlevel.dat／regionなど停止済Worldの12ファイルと、
  BASE_ON/SHAM_ON/BASAL_ZERO/WALK_ZERO/BOTH_ZEROの5コピー、
  Paper原log、S producer receipt、同runner R reader結果を保存。
- 元のS runner内のR reader（固定ソース
  `6547726d0cb188b1c890ab345ab9c802d091f2b6`）は
  12ファイルの相対パス・バイト長・SHA256が全5コピーで一致を確認。
  `level.dat` の実NBT seed=62101。
  source World tree SHA256
  `9f02533f5dae57fe8bc28ab188c08c3cbe9d28309aa8cdc6e3d016fbe053e49d`、
  level.dat SHA256
  `9dcbe19609a088d03b5418032f4bb618c1a6cf61dedc356cdb7e57b3e8895b70`。

## 別runner R offline rereview

[R workflow #38977085205](https://github.com/rinsakamo/relay-self/actions/runs/38977085205):
attempt1 **terminal SUCCESS**、R commit
`536cb62ab66a2d89556e55b4fba75c30e8fe09af` が
オフライン再読査用のワークフローを追加。
GitHub Actions CLI経由で改めてS artifactを取得し、
run ID／S producer SHA／provider保存digest／artifact名を固定、
固定R reader HEAD `6547726d0cb188b1c890ab345ab9c802d091f2b6` で
**元バイトの全12ファイルと5つのWorld複製を再読査**。
さらにNBTのseed62101、元Paper `Done (` logの存在、
S producer報告と保存された初回R verdict、level.dat SHAを突合。
すべてPASS、結果
`R_V8_DEV_REAL_STOPPED_WORLD_ARCHIVED_BYTES_REREAD_ONLY`。
この別runnerが追加でJava/Node/Minecraftを起動した回数は**0**。

別runner receiptアーティファクト #12079028263、
90日保存、SHA256 `4814b10ba56393c07693a8f196f615e20da6dccff3216022902d109649f41e76`。
**注:** 今回はGitHubのアーカイブprovider digestメタデータを照合したが、
ダウンロード後の元ZIPファイル全体のSHA256は独立に再計算していない。
内部元WorldファイルはRが自ら読みSHA256を再計算した。

## 保存した失敗とsource authority

元のS workflowを用意したDEVの2つの前段試行は
[#38976649171](https://github.com/rinsakamo/relay-self/actions/runs/38976649171)
（テストassertion違反）と
[#38976739214](https://github.com/rinsakamo/relay-self/actions/runs/38976739214)
（Ruff import違反）で **PRE-JAVA FAIL**。
両方とも元実機World起動0。
修正後に**新しい** run #38976820099で初めてPaperを起動。
実行源の新一時workflow
`.github/workflows/v8-stopped-world-five-clones-dev.yml`
はS Draft #545のownership repository-contracts非適合だったため、
S通常ブランチの最新HEADから削除し、歴史的ソースcommit #537947bと
原証拠archiveだけを保存した。
過去成功をメイン実装完了として昇格しない。

## 引き渡し・判定上限

この証拠で確認したのは、**実Paperで一回生成し停止したWorldから、
同一のファイル内容を持つ5つの新規停止Worldルートを作れること**。
現実の各cloneを起動して同じnative spawn pose／World full-time
でSelfが判断した事実はない。食料は設置していない。
5条件の代謝pluginも起動していない。
新V8のsource/JAR資格と実Worldの行動/食料/飢餓/死亡効果は**未確認**。

次はSがこの元停止Worldで5条件各クローンを独立に起動し、
native初期姿勢・World tick、等しい有限食料機会、
L0 SEEK/MOVE/EAT、真正なfood/saturation/terminalとSTOPを
原ログ化するDEV資格候補。
Rはその各物理原本を独立照合し、
Vは盲検割付・power・endpoint・censor／停止規則・
新しいSCIENCE権限を独立固定する。
V8 40候補枠は全件NOT_RUN。V7の旧0.005 block一致ゲートはFAIL、
V7 SCIENCE 0/20、V6 SCIENCE 0/48、G3/production NO_GO。
