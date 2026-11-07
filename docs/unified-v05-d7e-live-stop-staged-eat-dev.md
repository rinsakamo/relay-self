# D7-E — 原S49のMOVE後、実STOP観測からS51 EATを1回接続（DEV）

**親**：D7-D [#785](https://github.com/rinsakamo/relay-self/pull/785)。**子**：D7-E [#786](https://github.com/rinsakamo/relay-self/pull/786)。Bug-0 [#742](https://github.com/rinsakamo/relay-self/issues/742)。

## 既存実装を再利用

- D6-Cの実績あるoperator-staged rotten_flesh地面配置、既存原S49が発行する一度限りの方向照合済み `MOVE_BACKWARD`、S15 native clear/S16 OUTCOME/C1永続PREPARE。
- D7-A/Dの元Mineflayerプロセスに既存のS50七入力読取り、D7-BのPaper main-thread source（連続server tick、七入力最終受信値、座標、速度、ground）、元PaperアイテムUUIDの `EntityPickupItemEvent`。
- 原S49 `NormalSessionActionExecutor` は物理Actionの**唯一のissuer**。新しいWorldBody物理操作やS50側のSTOP/EAT Actionを作らない。食事は既存のS51 `IssuedEatingExecutor` と元S49の非MOVE物理PREPARE台帳を使用。

## DEV-only STOPを判断する現在World内の順序

1. その場の元S49の同じ `NormalActionReceipt` のS16 terminal、元S15 clear `-s15-clear` ACK/native seq、既存のsource-bound readback、未解決Action0を確認する。
2. 同一Paper UUIDの実配置アイテムをその個体が拾ったことを確認。R2から旧World/旧Actionは再利用不可。
3. 同じMineflayerの生のS50入力原本に、実clear ACKと**その後8 tick以上の入力OFF**を要求。Paperは**本物の拾得以後8 tick以上の現在末尾の位置/水平速度ほぼ0＋七入力OFF**。World/player/item UUID、tick連続・単一セッション、データの有限性、途中の入力再開を照合。過去だけのquiet streakは不合格。
4. 連続する二つの新鮮な元Mineflayer probeで、Health/酸素/周辺entity観測・原位置安定・腐肉在庫・food不足を確認。食べるかどうかは**既存S49 L0とEatCursor**が新鮮なprobeから決める。
5. その**元S49 ownerのメソッドだけ**が、上記実原本を直接読み取り、一度きりのD7 DEV EAT枠を発行。元のMOVE後のフェンスを明示的に一時解除する。食事発行の直前にこの枠を消費し、フェンスを戻す。UNKNOWN、途中失敗、古いAction、連続入力再開は再発行不可。
6. 既存S49のEAT PROPOSE/ISSUE、S51 equip+consumeのnative効果と食料/在庫差、元S49非MOVE永続EAT ledger、次native probeを独立照合する。

**物理STOP観測の限界**：Paper `getCurrentInput()` は直近受信入力で、元S49のS15 clearが**サーバーで有効化した厳密なtick**の一意ACKではない。今回の規約は**実World DEV動作判定**であり、R/QUALの因果的STOP資格やSCIENCE成立は主張しない。意思決定/身体限界/WorldBody法則は変更しない。

## DEV環境の固定外部条件

今回の食料は **operator-staged item**（ゾンビ自然ドロップではない）。食べる理由を再現するため、World運用者だけがバニラのhunger effectを与える。Selfはfood/腐肉在庫を直接書き換えない。ゾンビ撃破/探索/自然ドロップ/二周期/長期生存・学習成功をこの試験のPASS条件に含めない。

## 検証順

- Offline：新しいread-only live source試験・偽server/world/player/clear/inputs/food/EAT・永続履歴拒否、既存D4/D6/D7/Action/S51回帰、Paperの既存2プラグインビルド。
- 新規disposable World（R1）：元S49 MOVE→本物のPaper staged pickup→native腐肉増→同一session中live STOP readout→元S49/S51 EAT1件→Food増・在庫減→EAT S16 terminalと永続台帳一致→独立post→SHA manifest・cleanup。
- 失敗時も新Worldや同Actionの自動再試行は禁止。修正した場合は別World/別実行IDでDEV再検証、旧原本不変。

分類：`DEV_ONLY / S49_S51_POST_MOVE_EAT_ENGINEERING / PAPER_CLEAR_EFFECTIVE_TICK_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。
