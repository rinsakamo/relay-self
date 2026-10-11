# RSEE 1.0 — Golden Run 実ホスト read-only 最終照合

Authority: #537 (Self 1.0), #575 (RSEE profile), stacked parent #584
exact HEAD `22c5e188c63c3f7d5fb89690e0fa8f6eb783d07d`.

このドキュメントはGolden Run本番の許可ではない。
前回のMinecraft-only bootstrap許可は#583の実機試験で消費済み。
実行するのは既存ファイルの読み戻し・hash・Python/Node import・
Java/Nodeバージョン検査・git参照・Linux listener table参照だけ。
**モデル生成、llama-server起動、Minecraft起動、GPU計算、World Actionは0。**

## LocalCodexでの一括read-only入場審査

1. GitHubの子Draft最終HEADを読み取り、独立worktreeでそのexact HEADを
   checkoutする。main・既存Draft・他レーンを触らない。
2. `npm ci`等のローカル依存インストールが必要なら、
   本番監査の外で既存runbook #580に沿って用意する。
   Pythonは#580の専用venv、Node22はPATHを明示。
3. Golden本番用の新規evidence directoryは作らない。
   既存でない空きpath名だけを`--new-output-dir`へ渡す。
4. 以下を一度実行しJSON receipt（stdout）をGit外の別監査フォルダへ保存。
   保存先の編集はオペレーター側の責任であり監査器自身は一切書かない。
   `HEAD`はGitHubで確認した今回の子Draftのexact値を使用する。

```bash
export PATH=/home/rinsa/.nvm/versions/node/v22.22.2/bin:$PATH
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
HEAD=<EXACT-CHILD-HEAD-AT-THE-TIME>
NEW_OUTPUT="$BASE/golden-run-first-once"

"$BASE/venv/bin/python" -m experiments.standard_env.golden_host_gate \
  --expected-head "$HEAD" \
  --new-output-dir "$NEW_OUTPUT" \
  --jar "$BASE/minecraft-1.21.8.jar" \
  --snapshot "$BASE/bootstrap-approved-20261011-once/snapshot" \
  --manifest "$BASE/bootstrap-approved-20261011-once/snapshot_manifest.json" \
  --initial-evidence "$BASE/bootstrap-approved-20261011-once/initial_native_observation.json" \
  --gguf /home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf \
  --llama-server /home/rinsa/src/llama.cpp/build/bin/llama-server
```

成功時の唯一の分類は
`RSEE_GOLDEN_HOST_FILES_READY_NOT_AUTHORIZED`。
当該ホストでjar・GGUF・llama-serverを再SHA256計算し、
Node/Mineflayer/Python/Java product preflightを検証し、
#583の唯一の資格済みmanifest（26ファイル）および
native初期sidecarに二重拘束する。

また、git HEADのexact一致、コミット済みtracked diffなし、
新規run出力先不存在、NODE_OPTIONS空、Linux
/proc/net/tcpとtcp6のLISTEN(1234/25565)を検査。
listener tableの観測は**排他的ポート確保の証明ではない**。
実際の実行直前にowner launcherが再確認する必要がある。

FAILは`RSEE_GOLDEN_HOST_OFFLINE_BLOCKED`。
異なるGGUF、binary、初期World、sidecar、HEAD、ポート、古い出力先を
自動選択しない。前回のWorld許可・旧#580の「World未拘束」説明を
最新の物理資格として流用しない。

## 資格の上限

- 結果がPASSしても`physical_execution_authorized=false`。
- 一度もllama-serverを起動しないため、
  実`/props`/`/slots`、GPU層・VRAM使用、Thinking OFF、
  `reasoning_content`/`content`の分離はまだ実証していない。
- 製品側のlive L2はread-only commentary
  (`max_tokens=96`)であり、厳格JSON-schema応答を
  成功させたという意味ではない。
- #583の停止World byte/native資格は、
  将来のMinecraft tick運動・Action/OUTCOME・Memory・
  cleanup STOP ACK・GPU解放を保証しない。
- Golden Run本番には別途、ユーザーの明示的な**単発**許可が必要。
  対象はこのexact HEAD、同じsnapshot、同じmodel/binary、
  新しいevidence path、モデルGPU/LLM POSTおよびS49 World Action
  を含む1試行でなければならない。
  失敗時の再実行・fallbackは禁止。過去のbootstrap許可は無効。

この監査に成功した時点で、次の判断は
「Golden Runを1回実行するか／しないか」の人間承認。
オフラインPASSを自動GOと解釈しない。
