# S50 × L23 Paper input DEV — 2026-10-31

DEV PASS. 新規World 1回。先行run1はcaptureディレクトリ未作成によるPREWORLD BLOCKED（Java/Node/Action=0）、修正後run2で初めてWorldを起動した。失敗原本も保持。

S50実WorldソースHEAD: `62e02ec003e95c76f3060f356fa4eff15bd0f5b8`。
L23実行器HEAD: `d51b34b859cb18c4965681422163f9a1cfad3a8d`。
S50 branch: `dev/s50-paper-input-witness-20261031`。environment.jsonのbranch欄はL23実行器のbranchを表す。

Java21/Maven BUILD SUCCESS。初回システムJDKのrelease21コンパイラ不足を保存し、完全JDK21で再ビルド。Python3.12 focused26 PASS、関連FAST183 PASS、Ruff/構文/repository contracts PASS。関連FAST初回161 PASS/2 FAILは標準config追加とV7固定SHAの衝突。固定SHAを変えず歴史的16-action設定を専用テンプレートへ保存して修正。

Paper1.21.8 build60は公式v3情報とSHA/size照合済み。新S50 JAR使用。実験configは全16設定を保持。M0.2はexhaustion介入を行うため受動観測ではない。全資産SHAはassets/pins.json。

S49 Action1件 `s49-native-move-19`、S15 clear ACK seq28 applied、S16 OUTCOME after_seq29 executed。同一session `3e63cfbc-1011-4dd1-b1ca-f3a6f596f5bf`、Paper World `6993349a-b2c3-433f-b2c8-7f32b5fe64c8`。S16後native move6件、追加変位0.2404601368784256m。

Paper PRE_FORWARD244 / POST_CLEAR250 / WAIT_BEGIN251。WAIT_TICK252〜259は8件連続、活動252/253/254。S50 INPUT_TICKは同じ8tick、全7フラグfalse、overflow=false。INPUT_EVENT0件、各input_events=0 / last_input_event_tick=-1で更新tick未取得。更新イベントなしをsnapshot欠損と混同しない。入力ONと移動の対応は未観測。clear ACKとサーバー入力更新tickの関係も未観測で、時計を推定接続しない。

| World tick | last reported input | sampled位置差 m |
|---|---|---:|
|252|全OFF|0.05168390408372403|
|253|全OFF|0.009966234637660776|
|254|全OFF|0.005441564112162567|
|255〜259|全OFF|各0|

OFFでも移動を観測。後半のサンプル静穏は完全な物理静止の証明ではない。入力値はLAST_REPORTED_INPUT_CALLBACK_SAMPLE_ONLY。

L23独立再読出しPASS（Paper/S7最終座標差0m）、S50独立readback PASS。L23は原本照合のみ。Node/Java exit0、所有PID消滅、World削除、port25565再bind成功。既存World/他laneは操作していない。

EFFECTIVE_CLIENT_CLEAR_TICK=NOT_ATTESTED / FULL_TICK_INPUT_COVERAGE_NOT_ATTESTED / STABILITY_UNPROVEN / GOAL_UNDETERMINED / L10_PAIRS_0 / S10_UPDATES_0 / S11_GRANTS_0 / P1_WAIT_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。

次の最小実装: 既存唯一のMineflayer bridgeで1.21.8入力更新packetの送信実態を読み取り診断し、イベント0件とlast-reported全OFFの原因を切り分ける。新Motor/Action issuer/clear ownerは作らない。今回の観測をL8経験・Goal・P1 WAITに受理しない。

外部原本: `/home/rinsa/work/s50-input-evidence-20261031/`。run2/captureにS7送受信/receipt・S16原本、server.logにPaper全原本。独立監査・比較・cleanup・environment・SHA256SUMSを併置。GitHubにはJAR/World以外の小さい原本を保存。旧L23実World結果とは別run。
