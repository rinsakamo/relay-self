# D8 — 同一World・同一S49で自然ゾンビ食料2周期（DEV）

親：自然腐肉1食実World成功 [Draft PR #787](https://github.com/rinsakamo/relay-self/pull/787)、実World＋独立監査 [CI #42387610107](https://github.com/rinsakamo/relay-self/actions/runs/42387610107)。子：本Draft PR #788。

## 二周期の定義

1. 1体目：元S49 ATTACK→Paper独立Self killer死亡→バニラ腐肉1/2個を真のItemSpawnで観測→元S49（方向照合）MOVE→同じPaper Item UUID実Pickup→S50/Paper稼働中の現在STOP→元S49発行S51 equip+consumeのEAT→実Food増・肉在庫1減・非MOVE EAT ledger S16 OUTCOME。
2. Worldが前回死亡から**厳密600 server tick**で別ゾンビUUIDをspawn。元S49が新鮮なnative entity/Health/近傍観測を読み、先のIntentを完了・新Intentをcommitする。**同じMineflayer session、同じ元S49 supervisor、全旧Action IDs**を保持。これは経験に続く新しい行動判断であり、単純なAction再生ではない。
3. 元S49の再armingは**1周期目の本物のD7 STOP＋S51 EAT terminal receipt**が元S49内に残り、先の食事の権利が消費済み、すべての物理Action終端がOUTCOME、元新ゾンビIDがfreshなときのみ許す。同じ終了receiptの重複再利用は不可。
4. 2体目：World operatorがNoAI/低HPのターゲットゾンビだけを2.2m後方へDEV配置。元S49が新たにATTACK→実死亡→バニラ自然腐肉（0/1/2、強制しない）→残存腐肉とは別の本物のItem entityへの新規MOVE→実Paper拾得→最後のMOVE clearでlive STOP→元S49の別IDのS51 EATを1回実行。
5. 2回目のFood増と在庫推移を監査。たとえば初回自然2・摂食1で1個保有、その後自然2で3個、2回目摂食1で2個。RNG0は二周期食事未成立（NOT_EXERCISED）として保全する。

## 独立根拠・限界

- Paper監査：同じWorld／player Self killer、**異なる2体のゾンビUUID**、**異なる2つの腐肉Item UUID**、各死亡・spawn・pickup時刻と個数、600tickリスポーンに整合。前の食料を2体目の新たな戦利品と取り違えない。
- S49：前世代と次世代のIntent ID、元S49 owner同一Python参照、以前のS16 OUTCOME・fresh native probe、先行・後続で重複しないAction ID。非MOVE物理ATTACK/EAT ledgerとC1 MOVE pre-ISSUE永続台帳、未解決0。
- STOP：同一S50の**最後の**S15 clear ACK後8以上native physicsTick入力OFF、Paper本物Pickup後末尾8以上server tickほぼ静止、同じ元S49の現在World側body/危険/food判断。このDEV静止証拠はPaperがそのclearを有効化した厳密tickとの因果照合ではない。
- 元S49/S51：EATは装備＋consume native ACK、実Food増と在庫1減、S16 OUTCOME、既存PREPARE永続記録の原本を独立照合。新issuer、Food/肉生成コマンド、WorldBody定数変更はしない。
- World operatorの通常hunger効果とNoAI/低HPゾンビ配置はDEV環境条件であり、自然狩猟・長期自律生存を証明しない。学習や結晶化は対象外。QUALIFICATION_NO_GO／SCIENCE_NOT_RUNを維持。

## 検証の進め方

まずテスト：同Worldに2つの本物のPaper死亡→spawn→pickupがある時のみlive STOPを認め、重複・旧Item偽装・別killer/world・1体目を再利用するケースを拒否。既存D7-F一周期・D6の複数世代0個ドロップレーンの回帰も確認。

成功HEADでのみ新規Paper1.21.8/Mineflayer4.39 Worldを**別コミット1回限り**実行する。原本・独立監査・SHA256・cleanup保存。再試験時は必ず別World/Action IDを使用。

**現在の分類：** DEV_ONLY / D8_TWO_NATURAL_FOOD_CYCLES_IMPLEMENTING / TWO_CYCLES_NOT_YET_PROVEN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。
