# S31-B LocalCodex / WSL2 独立資格化

2026-10-09、Issue #391 に基づく独立ローカル実行 **PASS**。
凍結 S31-A runner を改変せず、ユーザーの Windows 11 Home
build 26200 / Ubuntu 24.04.4 WSL2 上で一回だけ実行した。
実 World を使う本実験に test shim / fake World は使用していない。
LLM calls / Self Action / autonomous cognition / Skill / learning は 0。

## Fresh authority と実測対象

- #391 全文、#368 本文・現在 HEAD・実測 receipt、main、open Draft PRs、
  main ruleset、primary checkout、WSL2 環境を開始前に照合した。
- #368 は OPEN / DRAFT、指定 SHA と一致。
  main は `75ae5a7d2ac809f66cd4fd8d0056145634fd4e96`、main protection は active。
- primary HEAD `32fe105fc12cbf54abd11bfba7c8a75d319939df`、開始時 clean。
  primary のファイルを変更せず、別 detached worktree で実測した。
- **実際に物理実行した HEAD:** `2f3af780508a51b66513043b4cfedf80d20ff1a0`
- **実際に物理実行した tree:** `c7bb81a82416ac92505f3a643b3b009d8273731f`
- 実行前後とも同一 HEAD/tree、追跡・非追跡ファイル状態 clean。
  実行後にのみ S31-B branch と新規ファイルを追加した。
  PR 最終 HEAD/tree はこの物理実測 SHA と別で、PR metadata を参照する。

## Runtime と実行

WSL2 kernel `6.18.33.2-microsoft-standard-WSL2`、Python 3.12.3、
Linux Node v22.22.2、npm 10.9.7、Ubuntu OpenJDK 21.0.12.1。
Node は既存ユーザー管理インストールを PATH に指定した。権限昇格・新規 runtime
導入・外部プロセス停止は行っていない。
事前 localhost bind 成功、MemAvailable 約14.8GiB、空きディスク約814GiB。
runtime injection variables は空。凍結 lockfile で `npm ci` exit 0、
production bridge から解決される genuine Mineflayer 4.39.0 を確認。
Node/Java ELF と runner/bridge/process_session/lockfile SHA256 は
[identity.json](s31b-evidence/local-001/identity.json) に保存した。

`--help` で runner flags を確認し、次を一回実行した。
実際の絶対証拠パスは非公開のローカル領域に記録し、ここでは `$EVIDENCE` と表記する。

```bash
PATH=<existing-linux-node22-bin>:$PATH PYTHONPATH=src S31A_REAL_SERVER_CI=1 \
  python3 -B -m adapters.mineflayer.s31a_real_server_ci \
  --report "$EVIDENCE/s31a-report.json" \
  --server-log "$EVIDENCE/minecraft-server.log" > "$EVIDENCE/runner.log" 2>&1
```

runner exit **0**。Minecraft Java **1.21.8**、公式 jar **57,555,044 bytes**、
Mojang 公開 SHA1 `6bce4ef400e4efaa63a13d5e6f6b500be969ef81` に一致。
使い捨て offline-auth flat World、`127.0.0.1:25565` のみ、RCON 無効。
実 Java server・実 Node OS process・実 localhost TCP 接続が成立した。

## 原本に基づく観測

| 項目 | 独立ローカル実測 |
| --- | --- |
| status / stage | PASS / SUCCESS |
| session | `459b3ba4-26d6-4812-9a6a-7379060ce546` |
| spawn / initial probe seq | 1 / 2 |
| initial request ID | `s31a-initial:001` |
| bot position | `[-2.5,-60.0,2.5]` |
| zombie ID / position | 32 / `[-0.5,-60.0,2.5]` |
| 3D Euclidean distance | 2.0m |
| target request ID / seq | `s31a-target:000` / 17 |
| native provenance | `459b3ba4-26d6-4812-9a6a-7379060ce546:17` |
| coverage | native entity registry、candidate 1、truncated=false |
| duplicate rejection seq | 18 (`duplicate_probe_request_id`) |
| Node / Minecraft exit | 0 / 0 |
| 後処理 localhost bind | 成功、test listener は残存しない |

16m coverage は凍結 Python decoder が `max_distance=16.0` を強制検証する。
runner JSON は radius 自体を出力しないため、このコード上の根拠と実測 JSON の
candidate/truncated を区別して記録した。
重複エラー文字列も runner が検査し、原本にはその seq を記録する。
console で NoAI zombie を約2mに召喚した後、native observation から幾何を検証した。
原本 JSON を S31-B 名義に書き換えていない。`milestone=S31-A` と
`live_minecraft=QUALIFIED_LOCAL_CI_SANDBOX` は frozen runner の固定文字列であり、
実際の実行 lane は別 identity envelope の LocalCodex / WSL2。

## CI と比較できる保存証拠

- [ローカル JSON 原本](s31b-evidence/local-001/s31a-report.json)
  SHA256 `9d4b8ecd9aa4c759321f95cc019dcc82092a665f9fd3d37b9f4b5f11872cbd2a`
- [ローカル server log](s31b-evidence/local-001/minecraft-server.log)
  SHA256 `5b3b46f1e3c138f4da23d4cbea961b8adf4b5eb9f049e9ceea5e9c9fe87232fb`
- [ローカル runner stdout/stderr](s31b-evidence/local-001/runner.log) と
  [npm ci log](s31b-evidence/local-001/npm-ci.log)、[全証拠 SHA256](s31b-evidence/SHA256SUMS)
- S31-A [push run 37861978950](https://github.com/rinsakamo/relay-self/actions/runs/37861978950)
  / [artifact 11585864900](https://github.com/rinsakamo/relay-self/actions/runs/37861978950/artifacts/11585864900)
  / [取得済み JSON 原本](s31b-evidence/s31a-push/s31a-report.json)
- S31-A [PR run 37861999744](https://github.com/rinsakamo/relay-self/actions/runs/37861999744)
  / [artifact 11585899980](https://github.com/rinsakamo/relay-self/actions/runs/37861999744/artifacts/11585899980)
  / [取得済み JSON 原本](s31b-evidence/s31a-pr/s31a-report.json)

両 CI は指定 exact HEAD に対する五つの job が SUCCESS、実測 JSON は PASS。
ローカルと公式 jar identity、Minecraft/Mineflayer versions、2.0m 幾何、
相関、重複拒否、両 exit 0 が一致する。session は三つとも異なる。
CI の entity ID 2 / target seq7 に対しローカルは ID32 / seq17。
native spawn/entity allocation と unsolicited frame 数の差で、固定 ID/seq を要求せず
相関と順序を確認する。原因の細部を WSL 固有と断定しない。

## 保存・検証・制約

ローカル原本と authority snapshot は Git 外の専用証拠領域に保存した。
公開するコピーは個人パス・秘密の有無を確認し、原本と byte equality を検査した。
実験は一回、失敗の隠れた再試行や二回目の実験はない。
S31-B の変更は再現手順、report template、offline receipt consistency checker /
negative tests、この資格化記録と証拠のみ。既存 S31-A / production / S18–S48 /
RelayTheory R6 / Paper2 MAIN40 / SKIPPED 記録は変更していない。

ローカル検証は全 pytest **1,445 passed / 156.75秒 / exit 0**、
S31-A + S31-B targeted tests **36 passed / exit 0**、
Node adapter checks **33 passed / exit 0**、全 Ruff **exit 0**、
source-only repository contracts **exit 0**。
offline checker と原本-copy equality / SHA256 全件検査も PASS。
pytest/Node/Ruff/contracts の log は Git 外のローカル証拠領域に保存した。
repository checker はインストール済 node_modules の上流 README まで検査すると
リンクエラーを報告した。test-owned dependency directory を証拠領域に移して
source-only で再検査し PASS。checker や凍結コードを変更していない。

server log の `No key layers in MapLike[{}]` は起動前の診断として原本に残した。
続いて Done、実接続・観測・正常終了が成立している。
npm deprecation notices / Node punycode warning も改変せず保存した。
清掃に約24秒を要したが、35秒の frozen shutdown bound 内で server exit 0。

これは controlled Minecraft native World の独立環境再現であり、暗号学的 source
attestation、任意 gameplay の安全性、S27 ancestry、自律認知の資格化ではない。
チェックサム・offline tests 単独から物理 PASS を作らない。
新規 PR は S31-A exact branch を base にした Draft として維持し、マージしない。
