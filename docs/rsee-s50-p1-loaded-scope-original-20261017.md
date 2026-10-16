# R — S50/P1 ロード済みチャンク・活動イベント原証拠の独立監査（2026-10-17）

Authority: R #575、S #537 / #627、P1 #620（既存Draft #626は変更しない）。新規REST Action、P1疲労回復、工学QUALIFICATION、SCIENCEは実行していない。

## 原証拠と同一性

- 新規S DEV限定の単独Paper 1.21.8 World run [#38976662458](https://github.com/rinsakamo/relay-self/actions/runs/38976662458) attempt1 SUCCESS。source HEAD `3f9e79bfb00f171672c661b024b27a0c18729154`。このsource checkoutとその時点のS Draftの最新HEADは別。
- 原アーカイブ [artifact #12079520551](https://github.com/rinsakamo/relay-self/actions/runs/38976662458/artifacts/12079520551)（30日、2026-11-15まで）。オリジナルZIP sha256 `ff19f1e664a8ee3f329e097e7b7de075b820672a5e8e6880db7d777416b95ec3`。
- 元の新WAIT observer JAR SHA256 `36640f5ff0684bbf361e5f6a2885547dfd5e0d500e78091bb6d8216c2aa932ae`。以前M0.2 V7五条件がQUALIFIEDとなった **別の固定JAR** `a43afa4d0a1fdaf01c633efd2543ed24b6b53b12ee38ed62a33594057e701e8f` を置き換えたとは認定しない。今回の新WAIT observer自体はR未資格。
- 本番ではなくfresh disposable DEV。BASAL、S50、S51等の既存ownerやM標準代謝係数、旧grantは不変。

## 独立再計算

R側に `experiments/standard_env/s50_p1_scope_original_audit.py` を新設。SのPython検証器を読み込まず、R自身の `s50_p1_wait_original_audit` を再利用。原runのSHA/World初期NBT/JAR、S50発行→OUTCOME、元のnative ACK・STOP、Paperの連続World tickを原ログで監査し、追加のscopeソース行8件のworld・marker・tick・counter・集約を照合する。

- `S50_DEV_WAIT_TICK` はtick 60〜67の8連続。XYZ不変。BASAL player tick43→50。
- Paper `S50_DEV_WAIT_SCOPE` も8/8、毎tickの全**ロード済み**チャンク（非ロード領域は対象外）の列挙結果: **3 Worlds、267 loaded chunks、12 entities、Self以外11 entities、他オンラインplayer0**。8サンプル中この集計値とsorted-UUID/type集約digestは不変。
- 主体の累積移動イベント数17、teleport0、velocity0、damage0、interact0、combat0、swing0は、8サンプル間で増加なし。これらは「観測されたイベントカウンター増分なし」であり、「全World tickで入力・外部運動・戦闘が絶対ゼロ」の証明ではない。
- 活動ソースのscopeは `LOADED_CHUNK_SAMPLER_ONLY`、held client controls `NOT_OBSERVED`、entity lifecycle `NOT_ATTESTED` を**明記**。SHAの集約値はsource-generatedであり、個別rosterが保存されていないためRが個体別の完全列挙を独立復元したわけではない。

R初回オフラインCI [#38977041820](https://github.com/rinsakamo/relay-self/actions/runs/38977041820) は旧auditのパラメータ化に伴うテスト用mock default-JARバインディングの互換性欠陥で**FAIL**。古い失敗を上書きしない。修正後の完全独立再読査 [#38977159796](https://github.com/rinsakamo/relay-self/actions/runs/38977159796) **SUCCESS**。90日 [R監査判定artifact #12078968520](https://github.com/rinsakamo/relay-self/actions/runs/38977159796/artifacts/12078968520)、2027-01-14まで保存。R full branch CIは後続の別V8並列pushを含めて別途exact-head確認が必要。

## 判定上限

`R_P1_LOADED_CHUNK_AND_ACTIVITY_SAMPLED_ONLY_NOT_SOLO`。**3 Worlds、Self以外11エンティティが8/8でロードされていた**ので、厳密なSOLO環境はこの記録では成立していない。ただしentity type別の原rosterを保存していないので、11体すべてが自律エージェントであると断定しない。World外からロードされた個体やtick間のspawn/despawnもこのsamplingだけでは否定できない。

**`p1_wait_ticks_admitted=0 / p1_fatigue_recovered=0 / science_go=false`**。真正の全tick WAITを認定するには、source-native Action全件・held controls・event source coverage・entity lifecycleの前後区間閉鎖と、全World native censusが必要。実tickサンプリングは視界を広げたが、連続全期間の否定証拠ではない。blocked MOVEもWAITにならず、P1では新REST Actionを作らず、M0.2 BASALがWAIT中も走る。

## 次の開発に必要な原資料

1. R/P1-Cが、entityのTYPE/UUID/world/chunk lifecycleを再計算できる**完全かつsource-boundedなエンティティ・ロスター**（今回の単なるsha256集計では不十分）とサーバ側spawn/remove/unload/teleport時系列を検査すること。
2. S/L0〜L2の全Action issuerについてWAIT観測中に新issued/in-flightが無いことを、server tickに同じ時刻源で相関させること。move控制ACKとPaper-side実効ON/OFFは引き続き別事実。
3. 原Serverのinput/held-control、collision/external impulse、戦闘など**全tick境界の観測範囲**を証明するか、不足するチャネルを明示的にNOT_ATTESTEDとすること。
4. 候補JAR・設定で改めてR独立QUALIFICATION後、初めてP1 `wait_interval_ref` とBody fatigue計算へ接続。QUAL/SCIENCEの新規grantとV事前登録はそれぞれ別判断。

R/VALIDATIONを偽装しない。五条件M0.2の工学資格は別の原証拠に対するもの。V7 matched path 0.005との差は未修正、科学試験0/20、production NO_GOを保持。
