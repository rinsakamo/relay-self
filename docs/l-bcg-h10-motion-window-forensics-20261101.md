# RelaySelf L-BCG H10 — 保存8 World運動過程・観測窓の事後監査

2026-11-01 / Draft PR #656 / Issue #431 / Issue #537。
対象：H9b実行HEAD `5a29da666f3692c02dbdb03ed0694ce088f124de`、
報告HEAD `56778779a4e4ba40b47965228f80b735d0fc9d53`で保存された
`docs/evidence/l-bcg-h9b-20261101` の原本8 Worldのみ。

## 目的

H9bで元native S42 2.0m/3.5mから予測した
`DEV_REPORTED_INPUT_OFF_SAMPLED_DISPLACEMENT_M` の誤差は、
「敵距離への運動モデルの適合不足」なのか、
「既存元Actionの移動差やPaper観測窓の切り取り」に
影響されているのかを**診断**する。

今回は原因を仮定して新たな物理・認知信号を捏造しない。
H9bの元FIT/EVAL境界、凍結係数、評価結果、H9a元pair REJECTEDは不変。
将来のL1のAction前予測にAction後の観測窓・S16・Paper結果を
入力させない。後知恵をAction前情報と偽らない。

## 原本から検査する項目

各Worldごとに次を別々の原本から照合する。

1. `s49-report.json` raw SHAが、
   `original-sha256.json`および**独立H8** `independent-audit.json`
   に記録されたSHAと一致。
2. 元S49 L0 `WAIT→MOVE_AWAY→WAIT`、native Action1、S16 Outcome1、
   original Action元seq・同session/Action結合とownerの変更なしを確認。
3. native dispatch seq < clear receipt seq < S16 after seq <
   L22 settling probe seq を元**同一native seq系列内の順序として**照合。
   この差分は**nativeシーケンス番号差**であり経過tickやミリ秒ではない。
4. 元S16 Action変位 `movement_m`（ユーザー入力への反応）と
   Paper 8tickのreported-input-OFF各 `displacement_m`（Action後の
   **別の**代理観測）を**別指標として**保存。
5. 8tickがPaperの連続world_tickで、全8tickが`last_reported_input_active=false`
   の状態であり、各変位が非負・有限、既存H9b EVALスコアの保存proxyとも一致。
6. L22 settling元MOVE通知数・元probe数・quiet streakを保存。ただし
   `physically_stopped_proven=false`、`stable_world_ticks_attested=false`、
   `clock_alignment=NOT_ATTESTED`なら、安定性や実効clear tickは主張しない。

## 既存原本からの技術的予備観測

| World | 元S42 | 元Action移動量 | Paper OFF窓の代理変位 |
|---|---:|---:|---:|
| A-F1 | 2.0m | 約0.83229m | 0.12832m |
| B-F1 | 3.5m | 約0.73429m | 0.06425m |
| B-F2 | 3.5m | 約0.73429m | 0.06425m |
| A-F2 | 2.0m | 約0.62691m | 0.06425m |
| B-E1 | 3.5m | 約0.73429m | 0.01475m |
| A-E1 | 2.0m | 約0.62691m | 0.06425m |
| A-E2 | 2.0m | 約0.62691m | 0.06425m |
| B-E2 | 3.5m | 約0.83229m | 0.06709m |

保存元Paper 8 tickのパターンは4種類あり、
**5/8 Worldが基本パターン**
`(0.049492188, 0.009543605, 0.005210808, 0,0,0,0,0)`に
実数許容差1e-9mの範囲で一致している。
A-F1は初期4tickに運動、B-E1は最初の1tickにしか代理変位が出ていない。

同じPaper OFF代理変位0.06425mでも、
A-F2の元Action移動は0.62691m、
B-F1の元Action移動は0.73429mである。

これは、**Action全変位とPaper後続8tick代理指標が別の情報である**
ことを示す。敵距離が原因、tick窓の開始相が原因、または特定の
身体応答が原因とはこの原本だけでは結論できない。

Paper world tick、native sequence、Node clock間の物理時計同一性は
**NOT_ATTESTED**。たとえばnative clear seq差をPaper tick差に換算し、
その時刻が代理変位の変化を説明したとすることは禁止。

## H10のソフトウェア実装

- `src/relay_self/l_bcg_h10_motion_variability.py`：
  単一World元S49 Action/S16/L22/Paper診断、8 Worldの記述統計、
  入力OFF代理変位パターン、ownerと時計の証拠上限。
- `tools/l_bcg_h10_motion_readback.py`：
  H9b保存8 Worldの原本SHAと既存独立H8 auditを読戻し、
  元H9b凍結EVAL4の代理値と整合させるCLI。
- `tests/test_l_bcg_h10_motion_variability.py`：
  既存8 World原本に対する正常系、
  action移動とOFF代理値の非同一性、原本SHA、次epoch混入、
  時計やclear認証の捏造、Paper tick欠落、World再利用を拒否する。

```bash
PYTHONPATH=src:tests:. python tools/l_bcg_h10_motion_readback.py \
  docs/evidence/l-bcg-h9b-20261101
```

**H10の実行World0、Action0、native probe0、provider/model0、
Memory/S10/S11/Learning更新0**。
資格・身体運動モデル・L0 Action issuerは変更しない。

## 次の計測設計への示唆

最初に独立したPaper/Node/native時計対応・Action入力解除の物理
World tick・観測窓の取得開始境界を調べることが、
距離条件を追加して学習能力を主張するより優先度が高い。
ただしこれは**次の別実験**としてWorld/Action/clock証拠の
測定範囲を事前固定する必要がある。

H10の目標は本来の身体経験予測の土台を明瞭にすることであり、
学習モデルが実世界に適合したとか、L1認知が改善したとは主張しない。

**H10_ARCHIVED_EIGHT_WORLD_FORENSIC_DEV_ONLY /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN /
GOAL_UNDETERMINED / EFFECTIVE_CLEAR_NOT_ATTESTED /
QUALIFIED_TRAINING_WORLDS=0 / DEFER_UNKNOWN**。
