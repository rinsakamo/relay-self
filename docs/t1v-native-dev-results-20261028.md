# T1v 実Minecraft DEV — 初期静止成立、連続歩容会計は未成立

**DEV_ONLY / DEV_WORLD_OBSERVED / PHYSICAL_IDLE_VERIFIED / NATIVE_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

作業branch: `self/dev-t1v-physical-idle-boundary-20261028`。開始remote HEAD
`1f14e52b3f8b47b041f653dfffaaef3dca462d43` は期待値と一致。
T1u `754602008010d6cd719a866d54be2df65c8d748a` と
T1s `946708c2daab0741b34f3b669efafb4622262a43` は祖先。
実行は開始HEAD＋保存済みdiff。各launch JSONとsourceコピーのSHAで実行コードを特定する。
配送commitのexact HEADは外部delivery記録とGitHub投稿に記録する。

## 実装と検証

- 既存T1v初期静止実装を実機検証。T2の拒否条件を維持し、既存の因果WAITとJOG矛盾のエラー診断を復元。
- T1v reportへ拒否tick/source seqを保存。
- 解除ACK後、拒否済みP1/M0とActionを再開せず、既存単一readerで最大24 source tickを診断採録。後続Actionなし。
- Python 3.12.3、指定9ファイル: 初回183 PASS / 1 FAIL（既存負対照のエラー文不整合）、修正後186 PASS。広めfocused **215 PASS**。
- 影響FAST **831 PASS / 50 files**。Ruff・repository contracts・構文494ファイルPASS。Node 22.22.2 snapshot **17 PASS**。
- Java21 / Paper1.21.8 / Mineflayer4.39.0を実機で使用。Node/Javaソース変更なし。T1u plugin jarをSHA照合して再利用、再build不要。FULL未実施。
- Ruff初回FAILと診断テストfixture初回FAILも外部ログに保存。負対照を緩和していない。
- 元P1 blob **`d241978d0eba1843e3a6caed96c90e3c16e8dc39`** とmodel test blobは不変。単一P1、単一既存M0 owner。

## 新規World 2個

|run|runner|source ADMITTED連続範囲|会計範囲|初期PHYSICAL_IDLE|JOG/back|WAIT_DEV|MOVE/OUTCOME/UNKNOWN/clear ACK|最大因果年齢 ms|
|---|---|---|---|---:|---:|---:|---|---:|
|T1V-001|FAIL|1015–1035 (21 ticks)|1034–1034|1|0|0|1 / 0 / 1 / 1|94.681696|
|T1V-002|FAIL|1012–1057 (46 ticks)|1032–1032|1|0|0|1 / 0 / 1 / 1|111.52607|

各runとも最初の会計anchorは非課金。初期PHYSICAL_IDLEはAction開始前で、
clear_seq/terminal_seqなし。両端の位置・motion counter・実適用controls OFF・速度属性・source identityを照合。
既存 `advance_gait_dev(WAIT)` を各1回のみ適用し、S49のWAIT_DEVは作っていない。
P1初期値0なので、累積負荷0・内部回復0・会計直後値0。既存式
`F_after = F_before * exp(-0.12 * 0.05)` と一致する。
**非ゼロ疲労からの実World回復は未検証**（非ゼロ回復はoffline testのみ）。
各runのM0: `12 - 0.001 basal - 0.0001 cognition - 0 movement = 11.9989`。
拒否tick以降のP1現在値はUNKNOWN、M0は未計上。0/11.9989を尾部の確定状態として扱わない。

## MOVE開始と解除・惰性の境界

T1V-001の1035、T1V-002の1033でINITIAL→MOVING。
前端は全OFF、後端はback ON、Paper inputは0のまま、位置とmotion counterは
約0.0980000385 block変化。開始の単一WorldTickへの適用時間・modeを確定できず、
元providerがUNDETERMINEDで拒否。P1/M0不変、Action UNKNOWN、clear ACK各1。
第2MOVEを発行していない。

T1V-002では拒否後24 frames (1034–1057) を同一readerから採録。
1035にはcontrols全OFFのCLEARED観測でもmotion counterが
**0.08272340052596977 block増加**。入力解除と物理移動終了を同一視できない証拠。
これはsample間の実移動であり、tick全体の惰性modeや適用時間の確定ではない。
1036–1038はmotion counter不変でも座標端点の完全静止条件が揃わず、
1039–1057の19 pairで厳格なsampled physical-idle条件を満たした。
UNKNOWNを越えて会計を再開せず、この19 pairもWAIT_DEVやP1回復には使っていない。

### A/Bを採用できない理由

既存Paper ownerはscheduler callbackでpose/currentInput/速度属性と、
PlayerMoveEventからの累積距離を観測する。`getCurrentInput()`は今回back移動を示していない。
Nodeは**snapshot受信callback時点**の`getControlState()`とphase/generationを記録する。
Mineflayer4.39.0のphysicsは独立した50ms accumulatorで、
`simulatePlayer(...controlState).apply(bot)`→`physicsTick`→`updatePosition`。
backの`setControlState()`は内部値変更であり、sneak/sprintとは異なり
対応するplayer_inputを送らない。

従ってPaperのscheduler WorldTickとclient physics stepは同一時間区間とは証明されず、
受理移動イベントにも対応physics step/適用power/effective tickの識別子がない。
AのtickごとmodeとBの信頼できる部分tick時間はいずれも未成立。
平均速度や別clockの差で補完せず、固定0.05秒モデルの部分tick流用もしていない。
新しい疲労ゲージ・reader・Motor writer・physics actuatorは追加していない。

## 原本監査と保全

停止・cleanup完了後のread-only監査でnative/commands/paper/t2/report、
実行sourceコピー、profile、World本体、設定、boundary tailを照合。
実行中のTickAccountingを再利用せず、原本から初期静止・P1遷移・M0収支を再計算した。
初期anchor非課金、tick1回更新、拒否後不変、Action UNKNOWN/clear、source連続性を確認。
これはR独立source認証や連続会計成功の監査ではない。

両runともtrace OFF、Node/Java exit0・PID不在・transport closure・World保存・cleanup PASS。
port25565を独立再bind。重複Action0、LLM0、food credit0、追加Motor0、TPS actuator0、
DASH追加M0未決済0、欠損補間0。shutdown tail各1 Paper tickは補填しない。
T1q/T1r/T1s/T1uの全原本manifest読戻し一致。main/保護Draft HEADは配送時にも照合する。

原本root: `/home/rinsa/work/t1v-evidence-20261028`。
外部manifest: `/home/rinsa/work/t1v-evidence-20261028/originals-manifest.json`、**1999 files**、
SHA256 **`724828b892a8c51b67b57e0765907cb69975240aad689572d0b2639681cb1f36`**。全ファイル読戻し一致。
監査script: `/home/rinsa/work/t1v-evidence-20261028/audit.py`、SHA256 `47d0c0c3a234b3d49085c59aa0a10870c34f2512ebe8e7b1a76863f554ee58cb`。
詳細: [JSON](t1v-native-dev-results-20261028.json)。

## 未成立事項と次工程

連続歩容会計、安定JOG負荷、因果WAIT回復、第2MOVE、WALK/RUN/DASHの実適用証拠は未成立。
次工程は既存owner内でclient physics適用stepとserver受理運動をsource identityへ結ぶ
受領境界を設計・負対照化し、WorldTickへ一意に帰属できるか検証すること。
それでも帰属不能なら単一P1の不確実性表現が必要だが、確定疲労やAction認可に使わない。
成立後の新Worldで2 MOVE / 2 OUTCOME / 2 clearと全tick再計算を検証する。
QUALIFICATION・SCIENCE・main統合・人体生理認定は実施していない。
