# RSEE 1.0 — Golden Run前のWorld byte binding（offline-only）

Authority: #575 / #580（WSL2 local artifacts）, product #537 / #545,
RSEE opt-in #579。今回の子Draftは `e4e6b5f412921db882807e1b8afe6f1874e9ac69`
をbaseとし、他のDraft・main・RelayTheory・Lane A/B/Cを変更しない。

**結論: source-byte再現性用のコードができても、物理資格化ではない。
Golden Runは BLOCKED / NOT_RUN のまま。**

## 実装と権限分離

- `experiments/standard_env/world_binding.py` にRSEE専用の拘束と
  停止済みsnapshotのbyte再現機構を置く。Python stdlibのみ。
- 専用Worldを明示した時だけ `S49.qualify(..., rsee_world=...)` が
  従来の `_fetch_official_server` を使わず、**local jar本体**をコピーして
  Worldを復元する。元S49 Action/grant/L0/World outcomeコードは不変。
- Minecraft 1.21.8 jar SHA256:
  `2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7`
  （#580で検査済みの当該ホスト内artifact）。
- manifestはschema `RSEE_STOPPED_WORLD_BYTES_V1`、
  version=1.21.8、level-name=`s31a-ephemeral`、seed=575、jar SHA256、
  初期観測sidecar SHA256、相対ファイルpath/size/SHA256全リストを要求。
  重複キー、追加/欠損ファイル、symlink、異常ファイル、サイズ超過を拒否。
  `level.dat`をgzip+NBTで直接パースし
  `Data.WorldGenSettings.seed` の**native long 575**を照合。
- Sourceとcopy後を両方検査し、`server.properties`は既存S31Aの
  既定を再利用して `level-seed=575` のみを追加。
  Snapshot原本に書かない。実験毎に一時ディレクトリへコピー。
  再利用先が既存/非空なら拒否。入力変更はfail-closed。
- 元のCLI以外へ勝手に継承されない独立フラグとして以下を追加。
  `--rsee-world-jar`、`--rsee-world-snapshot`、
  `--rsee-world-manifest`、`--rsee-initial-evidence`、
  `--rsee-eula-accepted`。
  モデル起動前に全World sourceを検査し、
  本来のWorld開始直前に同じ入力を再照合する。
  **独立EULA同意がなければ、WorldはもちろんLLMも起動禁止。**

## manifestの必要な構造（値は形式例。実Worldの証拠ではない）

```json
{
  "schema": "RSEE_STOPPED_WORLD_BYTES_V1",
  "minecraft_version": "1.21.8",
  "level_name": "s31a-ephemeral",
  "seed": 575,
  "jar_sha256": "<actual verified SHA256>",
  "initial_evidence_sha256": "<actual observed-byte SHA256>",
  "files": [
    {"path": "level.dat", "size": 12345, "sha256": "<actual file SHA256>"}
  ]
}
```

上記の数値は説明用であり有効なmanifest/snapshotを生成しない。
manifestは、実Worldの**正常停止後**に取得するWorld全ファイルを
相対path辞書順に網羅する。新たな物理実験のownerが
Minecraft由来の初期Health/Food/位置/向き、Inventory、
time/weather、gamerulesを別sidecarとして記録する。
同sidecarのSHA256をmanifestに拘束するが、**字句的な値やSHAの一致だけで
native観測を独立資格化したことにはならない**。

停止済みWorldの初回生成、native観測、Minecraft EULA同意、正式な
stop receipt、snapshot収集は実機が要る。今回のCIは
synthetic NBT/小規模fixtureとモックS49のみ。
actual World snapshotはまだ存在が確認されておらず、
偽のsnapshot、既存Worldコピー、過去実機結果の遡及採用は禁止。

## オフライン停止条件

- `--rsee-required` だがWorld flagの一つでも欠落、EULA未同意。
- jar SHA256不一致、manifest欄やbytesの不一致、level.dat seed違い。
- snapshot入場後のfile追加/削除/改変、symlink、相対path外への参照。
- 一時Worldへのcopy後にByte/SHA/seedが一致しない。
- Minecraft開始時に予期せぬWorld状態、実LLM/GPU/cleanupが不明。

以上はBYPASS不可。新しいルールが実機で動くことや
初期Worldが認知的に同等であることは、ここから推論しない。

## 次工程

1. exact HEAD offline CIを確認（現PRのPython、lint、Node）。
2. 本人の**独立した物理許可**の下で、RSEE snapshot **作成専用**
   disposable World（黄金本番とは別）を新規起動し初期native frame、
   settings/gamerules、Jar、seedを拘束する。
3. serverを正常停止して全ファイルのsize+SHA256 manifest、
   初期native sidecarを保存・監査する。
4. そのsnapshotの入場を別途資格化してから、
   固定Worldを使うGolden Runを一回のみ承認・実施する。

このスレッドでは実LLM POST / GPU model launch / Java / Mineflayer /
Minecraft World / 科学実験いずれも **0**。
