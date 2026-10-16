# S V8 — 自然地形停止Worldの原本生成と5条件複製（DEVのみ）

関連: S #537 / Draft #545、R #575 / Draft #610、V #619 / Draft #625。

## 目的と現在の資格範囲

V8の候補設計（seed 62101〜62108 × BASAL/WALK 5条件）は
地形・chunk・World初期状態を5条件で固定し、**実際の移動距離・衝突・迂回**
は操作後の結果として残す設計。既存V7の凍結0.005-block経路一致制約は
変更せず、V7科学試験を過去の工学証拠で埋めない。

`adapters/mineflayer/m02_paper_dev/v8_stopped_world_clone_dev.py` は
Sが所有するDEV専用ツール。RやVの代行ではない。

1. 絶対パス＋事前の資産SHAが一致する公式Paper 1.21.8 build60
   （SHA256 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`）
   を1つの新規廃棄Worldで、seed62101・hard／survival／通常地形・
   loopback・no mob の固定設定で起動する。
2. Paperの正式な起動完了を確認し、既存S31Aのstdin `stop` で停止、
   Java終了値0と25565ポート再解放を確認。**この時点ではMineflayer/
   Self/Actionは動かさない**。
3. 終了済み原本 `isolated-server/world/` のlevel.datと少なくとも
   1件のregion/*.mcaを含む全ファイルを記録し、同一の停止原本から
   `clones/{BASE_ON,SHAM_ON,BASAL_ZERO,WALK_ZERO,BOTH_ZERO}`
   を一件ずつ完全コピーする。各ファイルの相対パス／サイズ／SHA256が
   一致しなければDEVコピーを失敗させ、生成中のclone出力は破棄する。
   元の停止原本は変更しない。
4. **別checkout R**の
   `experiments/standard_env/v8_stopped_world_clone_preflight.py` で
   5コピーを再読査し、
   `v7_m02_world_nbt_audit.review_level_dat(..., expected_seed=62101)`
   で原本NBT seedの内容を独立照合する。R判定はbyte parityだけ。
5. GitHub Actionsの原ログ、停止証拠、World原本、5クローン、
   S receiptとR readbackをアーティファクトに保存。

DEV実機workflowの**歴史的固定ソース**はS commit
`537947b0011620769fd72da5f78320267ea8a614` の
`.github/workflows/v8-stopped-world-five-clones-dev.yml`。
実行済みGitHub Actions #38976820099と90日原証拠は固定されている。
Sの通常ブランチは非S所有の`.github/workflows/`新規ファイルを許さないため、
実行後にこの一時workflowはS Draftの最新HEADから取り除いた。
実機runを偽装・削除したのではなく、原ソースと実runはGitHub履歴に残る。
DEVで再実行する場合も、新規隔離実験として別ソース・別runを保全する。

停止済みの既存Worldから複製する場合（Java起動なし）:

```sh
PYTHONPATH=src:tests:. python -m adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev \
  --source /ABSOLUTE/stopped-world \
  --output /ABSOLUTE/new-five-clone-root \
  --seed 62101 \
  --confirm V8-DEV-ISOLATED-PAPER-STOPPED-CLONES-ONLY
```

**このDEVの限界:** cloneのWorldデータが同じことと、
「同じWorld full-time/位置/環境でSelfが行動を始めたこと」は別。
まだbot spawn・初期XYZ/yaw/pitch・食料有限配置・World時刻同期・
L0 SEEK/MOVE/EAT・飢餓生存・host Action terminalの記録は無い。
cloneごとのBASAL/WALK pluginをインストールしていない。
新しいS/P1 WAIT JARやL0適応を、過去の5条件資格済みJARと同一視しない。

`s-v8-dev-paper-receipt.json` と `source-clone-producer.json` は
S生産報告であり、R真正性の代替ではない。DEV成功もV8 SCIENCE試行として
数えず、`R_V8_STOPPED_WORLD_CLONE_BYTE_PARITY_ONLY_NOT_QUALIFIED`
のスコープ外の主張は行わない。

**進むべき次ゲート:** Sは停止World複製から別々に起動するDEV runnerを実装し、
各条件で真の同一初期姿勢・サーバー時刻／有限食料配置／L0行動／
Native food+saturation・terminal・STOP証拠を保存する。
Rは新しいsource+JAR・NBT+chunk・Action・全tick／Pose・食料元データを
独立監査する。Vは盲検・一次指標・比較対照・停止規則・サンプル数・
未実行40枠の権限を別途固定する。

現状V8 SCIENCE=0、V7 SCIENCE=0/20、V6 SCIENCE=0/48、
G3/production NO_GO。
