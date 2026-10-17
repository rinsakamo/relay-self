# R #575 → V #619 / V8 — 停止時World cloneの原バイト一致ゲート（source-only）

2026-10-17 JST。R Draft #610 の新しい**オフライン／事前資格用**ゲート。
V Draft #625 の `v8_m02_ecology_candidate.py` /
`v8_m02_admission_bridge.py` の要求「同一seed・停止時chunk完全コピー」を
R側で先に実行可能な検証器へ落としたもの。Vによる科学実験登録や
Sの実機World実装をRが代行するものではない。

## 接続

V8候補はseed 62101..62108の各5条件
`BASE_ON / SHAM_ON / BASAL_ZERO / WALK_ZERO / BOTH_ZERO`。
計画上40枠は**全件NOT_RUN**、powerや正式なseed割付は未承認。
既存V7の実績も**V7 SCIENCE 0/20**、V6は0/48。
V8では実距離の不一致・衝突・迂回をWorld結果として記録する予定であり、
古いV7の0.005-block gateを事後的に書き換えない。

R新実装
`experiments/standard_env/v8_stopped_world_clone_preflight.py` は、
**サーバー起動前に**、一つの停止済み原World treeと5つの別々の
staged clone rootを実際に読み、同一相対パス集合・バイト長・ファイルSHA256
を全ファイルで照合する。level.datだけ、同一seed宣言だけ、
World tree digestを自己申告するだけ、はいずれも拒否。
少なくともlevel.datと非空のregion/*.mcaが必要で、entities、
POI、data、session.lock、datapacksなど存在するファイルを全て比較する。
変更行動がある場合は原Worldへ戻す（後出し除外・過去証拠改変は禁止）。
symlink、relative path、同一／入れ子root、追加／欠損ファイル、
変造chunk/Entities、未登録seed・arm、過大ファイルを拒否。
ファイル読取後の再読も必要。

`tests/test_rsee_v8_stopped_world_clone_preflight.py` は**合成バイト**
による形状試験であり、有効なMCA/NBTの実World試験ではない。
R focused CIに登録した。

例（原Worldおよび5複製を予め外部で用意する。Minecraft起動なし）:

```sh
PYTHONPATH=src:tests:. python -m experiments.standard_env.v8_stopped_world_clone_preflight \
  --seed 62101 --source /ABSOLUTE/stopped-source-world \
  --arm-root BASE_ON=/ABSOLUTE/stopped-clone-base \
  --arm-root SHAM_ON=/ABSOLUTE/stopped-clone-sham \
  --arm-root BASAL_ZERO=/ABSOLUTE/stopped-clone-basal0 \
  --arm-root WALK_ZERO=/ABSOLUTE/stopped-clone-walk0 \
  --arm-root BOTH_ZERO=/ABSOLUTE/stopped-clone-both0
```

成功分類 `R_V8_STOPPED_WORLD_CLONE_BYTE_PARITY_ONLY_NOT_QUALIFIED` は
「**停止したWorld treeのバイト同一性**」のみを意味し、
cloneの独立したproducer真正性、NBTの期待seed内容、
サーバーが同じ地形をロードした事実、起動時の物理XYZ/yaw/pitch、
World full-time基準、同一food配置・有限性、Weather/Difficulty、
ホストのSTOP、Action/EAT、障害物観測、P1 WAIT、代謝sourceの独立
資格を意味しない。純粋なchecksum shapeだけではこれらを照合できない。
出力は必ず `worlds_physically_started=0`、
`v8_trials_credited=0`、`science_grant_issued=false`、
`science_go=false`、`production_go=false`。

## この先に必須の責務

S #537: 同じ生成済み停止時Worldを5 cloneへコピーするDEVランナー、
同一native初期姿勢とWorld full-time marker、
可視化されたfinite cooked_beef等の非補給資源の固定位置、
L0 SEEK/MOVE/EAT／blocked-detour・true hunger/terminal／host-cleanup
の**真正原証拠**を一件ずつ作る。ワールド起動の許可と原本保存はDEV/
QUAL/SCIENCEを区別する。旧4+1資格で新V8 pluginを自動資格化しない。

R #575: S候補の止めWorld cloneと原Worldのバイト同一性をまずこの
gateで照合、実起動後はfresh source HEAD/JAR/原物件/World tick/姿勢/
食料配置/行動結果/STOPを独立証拠として再確認する。
`level.dat`のseed一致だけで同一collisionやnative時刻を宣言しない。
V8用の**新しい**pluginのsource資格は別ゲート。

V #619: ロスター（40 NOT_RUN）のblind/seed randomization、
無介入安価対照、primary estimand、sample/power、terminal/censor、
full-roster止め規則を事前登録してから独立認証し、
新しいSCIENCE許可を得た場合にのみ開始する。
距離不一致を捨てるpost-treatment selectionや有利なrunだけの採用禁止。

**未充足状態:** V8 SCIENCE 0、V7 SCIENCE 0/20、
V6 SCIENCE 0/48、G3/production NO_GO。
