# L-BCG H9a — 実Minecraft S42 2.0m / 3.5m 独立World比較

2026-11-01 / Draft PR #656 / Issue #431 / #537。

## Mission

元S49のAction前S42敵距離を**独立Worldの元probeで**読み取り、
2.0m対3.5mの2水準を観測できるか検証する。両方4m以内で
元L0 MOVE_AWAYが期待されるが、**期待で元L0選択を上書きしない**。
CHEAPは両群で同じnative S42の固定閾値 **3.0m未満**。
元Actionは元S49 sole issuerによる1件以下。

H9aは条件別の**DEV代理観測**の比較である。
2 World（各群1）だけでは因果効果、学習の汎化、World間再現性、
Action改善を主張できない。H9aでは正式training World0、
正式heldout World0、Goal UNDETERMINED、EFFECTIVE_CLEAR NOT_ATTESTED、
QUALIFICATION NO_GO、SCIENCE NOT_RUNを固定する。

## 既存S49変更点（DEV opt-inのみ）

`adapters/mineflayer/self_body_s50_world_dev.py` に
`--l-bcg-h9a-near-distance-m 2.0|3.5`。
H8/route B単一Actionの`--l-bcg-shadow-dev`、
`--selfbody-live-next-epoch-dev`、L22 settling probes必須。
数値は厳密に2.0または3.5のみ、float NaN/Inf、bool、4.0m、
他レーンやroute Aには通さない。指定なしでは**旧2.0mへ完全復帰**。
既存`stage_world`の`(10,5)`→`(near,8)`→`(10,postwindow)`
のうち、near側のゾンビ召喚距離だけ変更する。
元L0/S42、S15/S16、追加Actionなし、追加native probeなし。

`src/relay_self/l_bcg_h9a_stimulus.py`は
要求stimulusを構造化するが、要求=実測ではない。
`src/relay_self/l_bcg_h9a_pair.py`は各World元S42とH8 sidecar/
S7/S16/Paper/cleanupの独立原本監査後にだけ比較する。
実Worldごとに`tools/l_bcg_h8_world_readback.py`相当の
独立source監査を実行し、その原本に基づいてH9a比較する。
`tools/l_bcg_h9a_pair_readback.py`は両World
`run1/`原本と各Worldの事前固定`predeclared.json`を受け付ける。

```bash
PYTHONPATH=src:tests:. python tools/l_bcg_h9a_pair_readback.py \
  /home/rinsa/work/l-bcg-h9a-a-evidence-20261101/run1 \
  /home/rinsa/work/l-bcg-h9a-a-evidence-20261101/predeclared.json \
  /home/rinsa/work/l-bcg-h9a-b-evidence-20261101/run1 \
  /home/rinsa/work/l-bcg-h9a-b-evidence-20261101/predeclared.json \
  --output /home/rinsa/work/l-bcg-h9a-pair-evidence-20261101/result.json
```

CLIは新Worldを起動しない。存在しないWorldの結果を合成しない。

## 事前固定：2つの独立World、再試行0

ユーザーのL-BCG DEV継続grant:
https://github.com/rinsakamo/relay-self/issues/431#issuecomment-6552384315

A: 要求距離2.0m。B: 要求距離3.5m。
両方とも実行HEAD・Python/Node/JavaとPaper/plugin/config等の
資材SHA、Goal operator plan、S49 mode、原本監査手順を固定する。
条件差は**ゾンビ近距離配置だけ**。各Worldごと事前宣言を作成・SHA記録し、
World開始前にexclusive `WORLD_ATTEMPT_STARTED.json`保存。
一方のWorldの失敗を同一World内で無断再試行せず、
原因と失敗原本を記録。成功Worldを失敗Worldに複製しない。

各Worldの制限:

- 新規disposable World1、元S49 Action最大1件、S16最大1件
- BCG追加Action0／native probe0／model calls0／S10/S11/Memory更新0
- replay、未承認他lane統合、独立Goal認証捏造、L0変更0
- 原node S7、S16、Paper sole collector、packet、元Body/World、
  H8 preaction sidecar、server/Node exit、PID消滅、World/port解放を保存

事前宣言JSONの必須キー:

`schema=L_BCG_H9A_ARM_PREREG_V1`,
`source_ceiling=H9A_DEV_EXPLORATORY_NO_PHYSICAL_LEARNING`,
`arm_id=A/B`,
`requested_distance_m=2.0/3.5`,
`cheap_threshold_m=3.0`,
`executor_head=<同一の実行コードHEAD40桁>`,
`worlds=1`, `max_original_actions=1`, `retries=0`,
`additional_l_bcg_actions=0`, `additional_native_probes=0`,
`model_calls=0`, `learning_updates=0`,
`qualified_training_worlds=0`。

実World後、元native move距離が要求から±0.15m以内、
かつ4m未満・MOVE_AWAYなら操作者のstimulus条件を
**native観測水準で**受理する。逸脱すればarm不成立として保存し、
2World比較PASSとしない。

## 比較と結論の上限

H9a pairで必ず別session UUID／Paper World UUID／原report SHA、
同じ実行HEAD、元S49 L0 WAIT→MOVE_AWAY→WAIT、
同じ元Action時刻のS42 native/probe/sidecar、同じCHEAP固定閾値。
AのCHEAP=true、BのCHEAP=false（閾値3m）。
Paper reported-input-OFF中の変位は浮動小数proxyの範囲比較のみ。
入力OFFは独立な実効clear tickでなく、Goal・P1・M0・歩容・障害物の
不足8条件はUNKNOWNのままにする。
2Worldの数値差を「学習が改善した」「因果効果」と断定しない。

H9bで比較実験を続けるなら、2条件それぞれ複数独立Worldを
初回からtraining候補/heldout候補へWorldごとに分割し、
cheapに対する事前固定評価基準を導入する。
ただし正式BCG trainerに渡すには別途Goal owner/物理実効clearと
full pre-Action cue qualificationが必要で、DEV proxyだけでは不可。

## 現在の達成範囲

この文書とH9a実装・GitHub CIは、Worldを起動していない。
実MinecraftのH9a A/BはLocalCodexが実行し原本と結果を保存するまで
**NOT_RUN**。既存H8 WorldをH9a 2Worldに数えない。
H8とH9a CIの合格は実World成功とは別。

**H9A_OFFLINE_PREPARED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**
