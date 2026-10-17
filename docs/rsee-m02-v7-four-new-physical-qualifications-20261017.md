# R #575 — M0.2 V7残り4条件の新規実World工学資格確認

**2026-10-17 JST。工学的QUALIFICATIONのみ、科学実験ではない。** S所有Draft #545 / R所有Draft #610、main未マージ。

## 判定

`SHAM_ON`、`BASAL_ZERO`、`WALK_ZERO`、`BOTH_ZERO` の各条件を
独立したGitHub Actions runner／Paper World／一回限りの許可／Nodeセッション
として実行し、**4/4条件の工学資格のみ確認**した。2026-10-16の
`BASE_ON` の既存資格とその消費済みgrantは不変。5条件が工学的に揃ったことは
5条件の科学的因果識別やMatched Worldの成立を意味しない。

### 成功した実機資格

- [S実World 38922286471](https://github.com/rinsakamo/relay-self/actions/runs/38922286471)：
  attempt=1、matrix 4/4 terminal **SUCCESS**。実機workflow HEAD
  `deea081c76437d6cc30374b69da4798e69fa8b73`。
  S exact-head CI `38922286462`、R固定CI `38921124894` はWorld起動前に
  必須ジョブがすべて成功。S Java21＋Node／Mineflayer、
  S50 Action MOVEとS51本物のcooked_beef EATを含む。
- **ソースプラグインを歴史的な資格対象JARへ正しく固定**：
  Sビルド参照 `d34c1cc613920a2485a581c25a8010f2a47e1bd6`、
  plugin JAR SHA256
  `a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f`、
  Paper 1.21.8 build60 SHA256
  `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`。
  S producer sourceと実行BINを混同せず、コンテンツ実体をSHA確認。
- R固定ソースHEAD
  `b93ab8c418157b4bed253fee5faa8db173e35d3a` の
  `m02_v7_four_arm_qualification_audit.py` による各条件別独立原ログ判定。
  S50/51 native command／effect ACK、正式Action journal、500件のWorld tick書込、
  初回200件BASAL、NBT seed、source hash、実STOP ACK、
  Java／Node PID消滅・25565ポート解放を各ジョブで確認。
  **各Java起動1／Node 1／retry 0、4 grantは全てCONSUMED。**

| 条件 | Grant（消費済） | BASAL倍率 | WALK倍率 | tick chord距離下限(block) | BASAL先頭200tick requested | WALK native setter input | 実機原ZIP artifact ID |
|---|---|---:|---:|---:|---:|---:|---:|
| SHAM_ON | `USER_M02_V7_SHAM_ON_20261017_ONCE` | 1 | 1 | 1.9389928412050272 | 0.2 | 0.019389928412050277 | `12055677136` |
| BASAL_ZERO | `USER_M02_V7_BASAL_ZERO_20261017_ONCE` | 0 | 1 | 1.7231471919306607 | 0 | 0.01723147191930661 | `12056065364` |
| WALK_ZERO | `USER_M02_V7_WALK_ZERO_20261017_ONCE` | 1 | 0 | 1.9389928412050272 | 0.2 | 0 | `12055886025` |
| BOTH_ZERO | `USER_M02_V7_BOTH_ZERO_20261017_ONCE` | 0 | 0 | 1.9389928412050272 | 0 | 0 | `12055002431` |

各original ZIPのGitHub SHA256:
- SHAM_ON `4457a29700577e340c220cafaa6c254a50a43aae58a29fdcca4c585938e832b2`
- BASAL_ZERO `c9f67f043f3a9c3175bcde10c477350fcb52a13afa7cec4368cee4f1fd7e7cda`
- WALK_ZERO `e06ebb658905e1035051c5413f907bef52f0e108a366ddd2b495dc9732a1b55c`
- BOTH_ZERO `f846bde94769bba7abcdc776126f74ad3480daff780096bdc463da4d78e9e9ca`

各条件の資格クラスは
`R_M02_V7_<ARM>_TICK_CHORD_ENGINEERING_QUALIFIED_ONLY`。
SHAM_ONはBASE_ONと設定バイトが等しいが、別物理Worldを実施して独立に資格取得。

### 別runnerでのR原証拠再読査（実World起動なし）

[R独立オフライン 38923706459](https://github.com/rinsakamo/relay-self/actions/runs/38923706459)：
attempt=1、4/4 terminal **SUCCESS**、R workflow HEAD
`f6b0b7a3597a74ae206715fb78476fa79512020f`。
元の実機原アーカイブをGitHub Actions公式CLIで改めてダウンロードし、
artifact ID／名前／保存されたZIP digestをGitHubメタデータと照合。
R reviewerを実機時と同じ固定ソースから再実行し、各原ファイル
SHA256SUMS／Action／World／native記録／original host witnessを確認。
**新たなJava／Node／World起動0**、実機と再監査のR verdict JSON全体が
各条件で同一。ZIPダウンロード後の生ZIPバイト全体SHAをこのR再読査で
独立再計測したわけではない（GitHubメタデータに登録されたdigest）。
Rの原ファイルSHAと保存済みR verdict一致までが今回の保証。

R独立オフラインのreceiptアーティファクト：
- SHAM_ON `12054803717`
- BASAL_ZERO `12056315065`
- WALK_ZERO `12054858589`
- BOTH_ZERO `12055053262`

### 保存すべき失敗・不変な境界

1. 初回workflow構文NG `38921490386` はジョブなし、起動0。
2. 新資格の初回4条件実行 `38921717987` は**全4件PREWORLD FAIL**。
   別途S/P1 WAIT実装が追加されたHEADからビルドしたJARは登録済み
   `a43afa...` と一致しなかった。4件ともJava起動前、grant未消費、
   初回失敗原アーティファクトを維持。失敗runを成功とは再分類しない。
3. Sは修正後に資格対象の歴史的JARソースを固定、**新run** `38922286471`
   で4件を1回ずつ実機実行・消費。各originalを保存してから元の
   one-shot workflowを `if:false` に凍結。再試行不可。
4. R初回別runner再監査 `38923535392` はZIP取得のHTTP 401でFAIL、
   **物理起動0**、本来の資格原証拠は不変。
   新run `38923706459` はGitHub CLIを使用して4/4再読査SUCCESS。
   この二つを混同しない。

**科学的境界：** 本結果はS50/S51とBASAL/WALKを、定義した実Worldと
原記録で動かせたという工学資格。各Worldで実際のtick-chord移動距離に差がある
（最大1.938993／最小1.723147、差0.2158456492743665 block）。
凍結V7の0.005 block matched-path条件を満たさない。物理連続
sub-tick経路、全World活動の証明、native net hungerへの因果寄与、
生存便益や対照優越を資格化しない。**V7 SCIENCE 0/20、
V6 SCIENCE 0/48、G3/production NO_GO**。
