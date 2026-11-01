# H9a 実Minecraft A/B原本 — 条件識別成立、pair SHA gate不成立

2026-11-01 / Draft #656 / #431 / #537。
実行HEAD: `38b8b722b5ff431bae98df4331443f36b9c31946`。
remote初期HEAD `6d79f50145f2a2e5fae6d93b229af5a3daadc93b` のCIは
H9a CLIのRuff I001で失敗。空行1行を修正し、新HEADの関連8 CI全件SUCCESSを
確認してからWorld Aを開始した。mainと他レーンは変更していない。

## 結果

| 実World | A | B |
|---|---|---|
| 要求S42 / 実測S42 | 2.0 / 2.0m | 3.5 / 3.5m |
| 許容差±0.15m | PASS（差0） | PASS（差0） |
| 元L0 | WAIT → MOVE_AWAY → WAIT | WAIT → MOVE_AWAY → WAIT |
| 元native event/probe | 8/9 → 20/21 → 56/57 | 9/10 → 20/22 → 55/56 |
| 元Action / S16 | 1 / 1 | 1 / 1 |
| CHEAP（同一pre-Action S42 < 3.0m） | true | false |
| Paper reported-input-OFF変位合計 | 0.06709170283354737m | 0.06424660150896089m |
| session | 1ba73115-4038-40ef-8435-90ad7c7e8f92 | b7a49586-27bf-4ce2-b012-49f477451a45 |
| Paper World UUID | 48e59ab1-dba7-440c-8a6e-e63b064a9f27 | cb941137-9e11-4a8d-a08a-6b81a1d91cb6 |
| 独立H8監査 / cleanup | PASS / PASS | PASS / PASS |

新規World各1、retry各0。追加L-BCG Action/native probe/model calls/
Learning/Memory/S10/S11更新は各0。元S49の4m危険閾値とsole issuerを維持し、
期待でL0を上書きしていない。A原本保存・独立監査・cleanup確認後にBを開始。
H5/H8 Worldの流用なし。異なるsession、World UUID、report SHAを確認。

## Pair CLIはREJECTED — 探索的比較PASSを主張しない

`tools/l_bcg_h9a_pair_readback.py` は
`critical Paper/plugin/config asset SHA differs between Worlds` でexit2。
Paperが起動時に再保存した `server.properties` の日時コメントが異なる。
A: `#Sun Nov 01 16:09:46 JST 2026`、B: `#Sun Nov 01 16:10:48 JST 2026`。
生成後ファイルのSHA一致を実行前に保証できていなかった。

- A raw SHA: `dbcae461ab304682b8d97d7876de46748501ad9fab83300387d4218f5743487c`
- B raw SHA: `288b1cfb719d2b6d8c964cc37b77fffd5b708e7e9d988445c7e8731898748c36`

非コメント設定行は一致しているが、これはraw SHA一致の代用にしない。
原本編集・SHA正規化による判定緩和・追加World・自動再試行は実施しない。
Paper本体 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`、
plugin `405657013fa315d76aab3730c6324b3583f9b30facf9233ef0b88fda9026585a`、
plugin config `2fd8f5bac2fea7fe857b1e7712a6979a2b76b78f626c374af7fbc7fee44e72d0`
と実行HEADは一致した。各armの読戻しは個別に監査し、pair PASSに代えていない。

**最優先の観測目的**である2.0m/3.5m身体経験条件は、元S42と同じprobeの
Body/World source・H8 sidecarから区別できた。CHEAPもtrue/falseで区別できた。
一方、全runtime SHA一致を条件とする **H9A探索的pair PASSは不成立**。

## 保存・監査・上限

[a](a/predeclared.json) / [b](b/predeclared.json) にWorld前宣言とSHA。
各run1は元S7送受信、S16、Paper、packet、H8 sidecar、Body/World、runtime設定、
process ownership、environment、cleanup原本。独立processのH8監査に加えH6/H7/H8
読戻しを各Worldで実施。全native commandの元S49順序、source digestとnative seq、
Node/Java exit0、所有PID消滅、World削除、port再bindを確認。
[最終cleanup照合](pair/final-original-immutability-cleanup.json) はA原本不変も確認。
[拒否ログ](pair/pair-readback.log) と [拒否結果](pair/result-rejected.json) を保持。
外部原本rootは `/home/rinsa/work/l-bcg-h9a-{a,b,pair}-evidence-20261101`。

Python3.12 focused241 PASS、周辺回帰172 PASS、Ruff/compileall/contracts PASS。
World後H9a/H8 focusedも実施し結果ログを保存。実行HEADのCI全件SUCCESSは
[pair/preflight/ci-pre-world-success.json](pair/preflight/ci-pre-world-success.json)。
初回CI失敗ログも保存。報告HEADのCIはGitHub最終報告で別に読戻す。

DEV: 各World原本・条件識別PASS / pair runtime-SHA gate REJECTED。
QUALIFICATION: NO_GO。SCIENCE: NOT_RUN。
GOAL_UNDETERMINED / EFFECTIVE_CLEAR_NOT_ATTESTED /
QUALIFIED_TRAINING_WORLDS=0 / DEFER_UNKNOWN を維持。
Paper変位はDEV代理指標。各条件1Worldでは汎化・因果的改善・学習改善は未証明。
H9b以降の学習による判断改善と分離する。
