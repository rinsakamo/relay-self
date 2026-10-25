# RelaySelf S49/P1 — MotorEnvelope と逆順の実World比較 (DEV)

2026-10-25。隔離ブランチ `self/dev-p1-motor-envelope-reverse-pair-20261025`。
**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

## 実装

前回のP1モデル仮説を直接 `MineflayerCommand.duration_s` に置換していた
DEV経路を、型付き・不変 `DevMotorEnvelope` の2段階に変更した。

- `adapters/mineflayer/s49_p1_motor_envelope_dev.py`:
  `bind_motor_envelope_dev()` は発行済みの元S49 `MOVE_BACKWARD`、
  6番目のsource-qualified native probe、同一action ID、5番目の
  source結合済P1仮説、仮定したモデル効率・時間の整合、
  既存0.2秒以下かつDEV最小0.05秒以上を検査し、Action権限を作らない。
  `apply_motor_envelope_dev()` は同じコマンドの `duration_s` だけを変更する。
- `s49_paper_world_first_dev.py` の既存DEV transportに接続。
  元L0の選択・grant、S14/S16の通常許可・終端処理、単一native receiver、
  Java/Node終了所有者は変更しない。新しいAction発行者は0。
- `tests/test_s49_p1_motor_envelope_dev.py` は既存/強ストレス両条件、
  偽造Action ID・異session/古いprobe・失効したモデル入力・不正時間・
  追加issuer等の負対照を追加。
- 元 `adapters/mineflayer/normal_action.py` のblob
  `0ded8fa296c92076a643de08cd6fc360061e1d08`、
  元 `experiments/fatigue_p1.py` のblob
  `bd4f35a4079da0770ef11cdec921dbba31de9b81` は不変。

## 逆順の実Minecraft試験

追加試験: [Actions #40182251879](https://github.com/rinsakamo/relay-self/actions/runs/40182251879)
（実行HEAD `90580bdcd1792bf25f9be14927f03a8bbdf23b23`） **SUCCESS**。
[ZIP artifact #12594776424](https://github.com/rinsakamo/relay-self/actions/runs/40182251879/artifacts/12594776424)
をダウンロードし、2件の元S49 JSON/2件のDEV report/2件のPaperログ/
`paired_world_review_dev.json` を読み戻し確認した。

前回の独立比較:
[Actions #40181302973](https://github.com/rinsakamo/relay-self/actions/runs/40181302973)
（実行HEAD `dce06b9a2f52ce94c4f63f5352e30c1280023a13`） **SUCCESS**。
[ZIP artifact #12594212819](https://github.com/rinsakamo/relay-self/actions/runs/40181302973/artifacts/12594212819)。

新規は条件の実行順を逆にした。
- 第1組: 既存P1モデル → 未校正の強ストレスモデル。
- 第2組: 未校正の強ストレスモデル → 既存P1モデル。

両組とも新Worldが2つ、独立の元S49 session IDが2つ。
合計 **4 World / 4 original S49 sessions / 24 L0 decisions / 16 native
S14/S16 Action OUTCOMEs**。各sessionの6判断は
`WAIT → MOVE_AWAY → MOVE_AWAY → MOVE_AWAY → WAIT → MOVE_AWAY`。
すべての元S49 reportおよび外側DEV reportはPASS、各Java/Node exit0/0。
Python 3.12 focused + MotorEnvelope負対照・構文・Ruff・Paper/Nodeセットアップ成功。

| 指標 | 第1組 | 第2組（逆順） |
| --- | ---: | ---: |
| 既存P1: MOVE rate | 0.04 | 0.04 |
| 強ストレス: MOVE rate | 6.0（人工的） | 6.0（人工的） |
| 既存P1: 6番目S15実コマンド時間 (s) | 0.19648932318884205 | 0.19648932318884205 |
| 強ストレス: 6番目S15実コマンド時間 (s) | 0.06000000000000001 | 0.06000000000000001 |
| 既存P1: 6番目実MOVE距離 (block) | 0.6269065734210617 | 0.6269065734210617 |
| 強ストレス: 6番目実MOVE距離 (block) | 0.09800003853258321 | 0.09800003853258288 |
| 距離差 (強ストレス − 既存P1) | −0.5289065348884785 | −0.5289065348884788 |
| sixth MOVE直前の敵距離/体力/満腹度/y | 2/20/20/−60 | 2/20/20/−60 |
| 全4セッションS16 terminal | PASS | PASS |

第2組では強ストレス仮説を先に動かしても、
元S49の実距離差が実質同じであることを観測。
2組の差の差は `−3.33×10^-16` block（浮動小数点丸めの範囲）。
これは **固定入力時間のWorld上の応答が、この2回の条件と順序で再現**した
という小規模DEVエンジニアリング結果である。

## 境界・次にすべきこと

- 身体疲労の実測ではない。強ストレスの `move_per_block=6.0` は
  意図的・未校正の感度条件であり、元P1を改変しない。
- 2つの独立Worldの絶対座標や全tick履歴の一致は未証明。
  物理的な疲労に距離差を帰属できず、Action時間の差以外の条件が
  完全にランダム化されているわけでもない。
- P1の `SourceBoundTick` はなく、R-admitted WAIT=0。
  R本番計測・S10更新・SCIENCE実験は未実施。
- モデルが認知選択 `MOVE_AWAY/WAIT` を変えたのではなく、
  **既存認可後の運動コマンド時間だけを変更**した。
- `s49_normal_session_real_ci.py` は親DEV以来の保護source変更を含み、
  owner/source審査までは #545 / #634 / main に採用しない。

次は、累積疲労をWorld-tickとの接地なしに実測と呼ぶことを避けつつ、
最小限のP1 BodyCapabilityをCognition側の読み出し形式へ接続する。
繰り返しのDEV World実行を儀式化せず、必要な時だけ使う。
