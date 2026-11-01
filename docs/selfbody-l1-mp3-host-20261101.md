# L1-MP3 host観測前固定（DEV）

#653 最新grant（[6551090255](https://github.com/rinsakamo/relay-self/issues/653#issuecomment-6551090255)）に基づく1 World限定。基点84adf1ae。過去grantは使用しない。

元S49 hostのroute B opt-in `--l1-prediction-journal`。元唯一Java stdout readerがflushするDEV専用ログsink内の同期callbackで、各WAIT_TICK読取り後に次tick予測を計算しexclusive journalへfsyncしてから次readlineへ進む。追加probe/Action/model/learningは0。係数trainingはWorld開始前固定、session/Action/markerはPRE_FORWARD送信前にarm、WorldはPRE_FORWARD受信時固定。subjectはtrainingと同一の予定値であり後続元INPUTで必ず照合する。後付けで凍結時刻を変更しない。

**HOST_BEFORE_NEXT_READ_ONLY / PAPER_PHYSICAL_PREQUENTIAL_NOT_ATTESTED**。OS/Paperのbufferに次callbackが既に存在する可能性を排除する同期機構は元sourceにない。したがってこのhost hookの試験成功をPaper物理観測前固定の成功へ昇格しない。source生成時刻との競合は未決定のまま保持する。batch採点とは分離し7つの先行保存値を照合する。対象不一致/欠測/順序異常は失敗で保存、再Worldなし。

0/last/training mean/same-information cheap linearを同じ7対で比較。cheapとの同値、Goal UNDETERMINED、L10/S10/S11/P1=0、QUALIFICATION_NO_GO、SCIENCE_NOT_RUN。実結果は終了後追記。

初回事前CI 41256883106は共通collectorの保護blob変更で19 FAIL / 409 PASS。原ログ保存。共通collectorを基点bytesへ戻し、保護manifest/testsを変更せずDEV hostのPathログsinkだけで同期通知する形へ修正。World未消費。
