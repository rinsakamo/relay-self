# S × M 実Gemma・実World費用統合: 実行前検査

検査対象は S Draft [#672](https://github.com/rinsakamo/relay-self/pull/672)、
`1aaa911ad757b255c70d0388836f9c2f69223534`。
M Draft [#670](https://github.com/rinsakamo/relay-self/pull/670) の
`c58cc4f41c5f839487d19d50841b344bd242eb0f` 上の実装を確認した。

**統合未完了。DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。**
新規World、実Gemma要求、物理Actionはいずれも0。この検査は実World・実モデルの
認知費用、学習、習熟、省資源化を実証しない。

## source admission の未成立箇所

既存 `SPostEpochL2OpenRuntime.execute` は元の完了S42 epochと、その同一objectを
保持するRECORDEDなS/L8/M tapを要求する。正規 `LlamaCppRelayProvider` と
`RelayEngine.open`、別L2 companion、Mの `CognitiveWorkReceipt` は再利用可能。
欠測tokenと不確定な送信結果をUNKNOWNに保つ既存処理も維持する。

しかし、固定S product `087fe095a87594505392262da1d341cf0c65b2b2` の
`s49_normal_session_real_ci.qualify(live_probe=...)` が渡すのは**判断前のprobe**。
`NormalWorldL0._check` は元の `WorldConditionedChoice` を返すが、そのlive経路は
S42 `DecisionEpochResult` と元B0 decision、L8 snapshotの完了ハンドオフを供給しない。
Mの `S49PassiveSourceLease` は後でこれらの元objectが供給されることを要求する。
offlineテストの型が一致するだけでは、このlive接続が実装されたことにならない。

したがってprobeだけからRECORDED tapを構築したり、後から別のcoordinatorを走らせた
結果を元S49 epochと呼んだり、fixtureのB0/L8値を実Worldへ移植したりしない。
元S42結果をOPEN結果に置換しない。実Worldの開始前にS owner側の完了ハンドオフを
実装・検証する必要があり、grantだけでこの技術的不足は解消しない。

Mの `observe_completed_s_cost_window` は元S epoch内のEngine resultを読む契約である。
固定WorldConditionedChoiceはそのままUNMEASUREDとし、別L2費用には既存companionの
usageを `CognitionCostSample` と `summarize_cognitive_lifecycle` へ渡す。
安価な元判断の費用と、後続OPENの追加費用を二重計上・混同しない。

## ローカル資材検査

- Python 3.12.3、Java 21.0.12.1、Node 22.22.2、Mineflayer 4.39.0。
- NVIDIA GeForce RTX 3060、VRAM 12288 MiB、検査時使用706 MiB。
- loopback ports 1234 / 25565 はbind可能。モデルserver、Java World、Mineflayer sessionは未起動。
- GGUF `/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf`、7381384864 bytes、
  SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`。
  これはローカルファイルidentityであり、ロード済みserverとのbindingや生成成功の証明ではない。
- Paper jar SHA256 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`。
- 既存Paper DEV plugin SHA256 `405657013fa315d76aab3730c6324b3583f9b30facf9233ef0b88fda9026585a`、
  config SHA256 `2fd8f5bac2fea7fe857b1e7712a6979a2b76b78f626c374af7fbc7fee44e72d0`。
  資材hash一致は今回のWorld source認証ではない。過去Worldは再起動しない。

## 権限と実行順

[#537現行本文](https://github.com/rinsakamo/relay-self/issues/537) の通常S DEV規則は
使い捨てlocal Worldでの開発・修正・再実行を許容する。過去one-shotを再消費しない。
他レーンのL-BCG専用grantをS×Mへ転用しない。実Gemma追加呼出しについては今回の
明示予算を照合する。技術的source gateも満たした後だけ実行する。

初回候補予算: 新規DEV World最大1、元S49 Action最大2、別Shadow OPEN最大3、
各要求最大256出力token、timeout 60秒、timeout・不確定送信の自動再試行0。
この記述自体はgrantでも実行済み記録でもない。
L2本文はAction/Memory更新へ流さず、B0/P1/L8既存owner・数式・認可を変更しない。

実行前に、fresh HEAD/PR、単一Action executor、同一session/probe/request、
完了S42 epoch identity、元B0/L8 source、S15/S16 terminal、未使用出力root、
モデルbinding、EULA由来、所有PID/portと停止手順を固定する。
最小epochの成立後だけ同一World内の複数epochへ拡張する。
未知・既知・変化のphaseは外部注記とし、学習による既知化を推測しない。
全試行・失敗・UNKNOWNを残し、Node/Java/llama.cppの所有PID終了・port解放と
VRAMを別々に検査する。

## 証拠

隔離worktree `/home/rinsa/work/relay-self-s537-real-cost-20261101`。
外部証拠 `/home/rinsa/work/s537-real-cost-evidence-20261101/preflight/`。
`runtime.json` は今回のhash・version・GPU・ports・未起動を記録する。
`pinned-regression.py` は既存S workflowと同じ固定S/L8 import overlayを使用する。
`pinned-regression.log` は初回中断を保存し、後続の詳細診断ログと区別する。
後続 `pinned-diagnostic.log` はPython 3.12.3で **126 PASS / 125.20秒**。
Ruffとrepository contractsもPASS。初回の中断をテスト失敗や実World失敗とは数えない。
既存実装HEADのGitHub CI run `41301715679` は今回jobs APIでSUCCESSを読戻した。
実行後の試験結果と報告HEADはPR/Issueの追記に記録する。
