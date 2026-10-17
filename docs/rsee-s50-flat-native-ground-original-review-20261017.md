# S50 FLAT-DEV native ground — 原証拠と別runnerのR再照合

2026-10-17 JST。自然地形V8とは別の**DEV専用**ワールド。
World seed `63101`（V8自然地形候補62101..62108とは重ならない）。
Selfの採食試験・科学的介入・代謝JAR工学資格ではない。

## ソースと実World

S #545コード:
`adapters/mineflayer/m02_paper_dev/s50_flat_ground_dev.py`、
`tests/test_s50_flat_ground_dev.py`。
公式 Paper 1.21.8 build60 SHA256
`8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`。

実Paper DEV原 [GitHub Actions #38989215391](https://github.com/rinsakamo/relay-self/actions/runs/38989215391)
HEAD `09f4dc238ee338d3fa421c6e1bf055b49a93ad8d`、attempt1。
`level-type=minecraft:flat` の単独Paper起動後、
地表Y=-61の草ブロック・プレイヤー足元Y=-60/頭上Y=-59の空気を
X,Zそれぞれ{-4,-2,0,2,4}、計**25地点のサーバーnative Execute**
で検査し、各地点の独立`[Server]` source markerを保存した。
25/25 server markers、Java start1、STOP→exit0、port25565解放。
Mineflayer/Node0、食料配置0、S50/S51 Action0。
原Worldデータ13ファイルを保存。

**旧原runの最終WorkflowはFAILED**:
物理S DEV生成自体は成功したが、後続R読み取りの
`server.properties` に対する未正規化literal
`b'level-type=minecraft:flat'` 検査がFAILした。
Javaのproperties出力とraw sourceの表現差を吸収していなかったものであり、
当該原runの履歴・原ファイルを修正／PASSに書き換えない。
別のR runで意味的なflat設定と原Paper native source evidenceを検査する。

[原アーティファクト #12084531180](https://github.com/rinsakamo/relay-self/actions/runs/38989215391/artifacts/12084531180):
90日保存、GitHub provider digest
`sha256:df981ff1d3eb064e78602ff785984a03a22d78943569b8c14dd9591675b103f7`。
原source stopped World／jar／console／props／receiptを保存。
実Worldをもう一度起動して書き直したわけではない。

## R 別runner source-only 再照合

[R workflow #38989400399](https://github.com/rinsakamo/relay-self/actions/runs/38989400399)、
原レビュー用ソースcommit
`2122b71995be0b52b491deaff85d7301dc35f4b0`、
attempt1 terminal **SUCCESS**。

S原アーティファクトを別R runnerへ再取得。
凍結S source runの**失敗ステータスを維持**して原run ID・HEAD・
artifact ID/provider digestを照合。
RがSのparserを使わず、原Paper consoleの
25座標×Grass block+上下airを各1件再計算。
原World level.dat実NBT seed=63101、server.properties
のflat intent、Paper起動・World保存原ログ、
公式Paper binary SHA、
停止World全13ファイルの相対パス/サイズ/SHA256と
元S receiptの一致を独立に照合。
R中にJava/Node/World起動 **0**。

R verdict:
`R_S50_FLAT_REAL_NATIVE_GROUND_ORIGINAL_READBACK_ONLY`

- World `level.dat` SHA256:
  `1cd714e9607a8015ca37918f11717ab92f2e0d44718c439d7d83a9a36dac1845`
- Paper原console SHA256:
  `5f680b13b82f3c2c941e9b61fbf8070b4a2e9fe6c9ccb254d073d7359a193e28`
- 停止Worldファイル: **13**
- grass+two air native marker: **25/25**
- R独立receipt [#12084900258](https://github.com/rinsakamo/relay-self/actions/runs/38989400399/artifacts/12084900258)
  provider digest `sha256:9eb7be5f4046c4f46d438b000904e2cb4e99ca6da7053539b0feda590283fbe5`

元アーカイブZIP全体のSHA256をRで独立再ハッシュしたのではなく、
GitHub provider digestメタデータの同一性＋実保存各ファイルの独立SHA再計算。
物理world sourceによるfloor 25点の構造証明を超えた
entity collision/actual client pose/walking/food inventory/eatingの
真正性を認定しない。

## 次のSゲート

この停止済Worldを**新規の使い捨て起動用コピー**へ複製し、
S50既存Action ownerでSelfのnative spawn pose・World fulltime
とoperator staged cooked_beef（native初期足元高と同じ地表高）、
L0 SEEK→MOVE→PICKUP→S51 EATをDEV観測する。
最初は**BASE_ON一条件**で採食経路の健全性を検証し、
成功／失敗にかかわらず各一回のDEV原証拠を保存。
成功が確認されるまでは5条件比較を繰り返さない。
その後、同一テンプレートから5条件へ広げる。
BASAL/WALKへの未来の操作は現在のV8自然地形scienceとは混在させない。

Source原実験でのS50 Action0、food0、science0、工学QUAL0。
V8 SCIENCE=0、V7旧凍結matched-path不合格、production/G3 NO_GO。
