## S2-B Original Owner Epoch — 新規実World DEV PASS（2026-11-02）

**DEV_ONLY / S2B_ORIGINAL_OWNER_REAL_WORLD_JOIN_PASS / SOURCE_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

- Branch `dev/s537-s2b-original-owner-epoch-read-20261102`。開始HEAD `564ee56aa7396f1625d843c1d62b937dbe47a748` はGitHub PR #696と一致。独立clean S worktreeで実行HEAD **`cc6f8e815e3658211f05cf09062aaad028bd7d3e`** を検証。納品HEADは本報告の読戻し記録に追記する。
- Issue #537の現行DEV方針と今回の指示に基づき、使い捨てWorld **1回成功／失敗0／再試行0**。予算World1・元Action最大2・モデル0・S60投入0。Gemma/GPU/llama.cpp起動なし、NODE_OPTIONSなし。
- Python 3.12.3、Java 21.0.12.1、Node 22.22.2、Minecraft Java **Mojang vanilla 1.21.8**、Mineflayer 4.39.0。Paper実行ではない。固定元S49 #674 `702f75c9fab3c42053ca0c89af670db1e306c892`、WB #669 `944db858186a4d9449946b6acdcb8c8e5998e071`、M #676 `9afce6bde1079f8a42aaf3c4e515ef35fc6b0396`。M/WB clean exact SHA確認。
- 変更後オフライン **150 PASS / 0 FAIL**。元S49回帰、固定M/WB、S2-A/S2-B負対照、合成原本監査、cleanup・observer例外隔離を含む。Ruff／compile／repository contracts PASS。初回contractsは未追跡npm依存READMEのリンク走査で失敗し、ログ保存後、依存を一時退避した同一ソース検査でPASS。検証条件を緩和していない。

実World session **`20a2c581-f90d-4ddd-be60-00a3ce2e8826`**。元S49判断 **WAIT → MOVE_AWAY → MOVE_AWAY**。元Action **2**、S15 clear **2**、S16 OUTCOME **2**、未解決Action **0**（元S49 PASSゲートで確認）、追加issuer Action **0**。

| epoch | event → native probe | 元Action | before → dispatch → S15 → S16 after | owner generation / retained revision |
| --- | --- | --- | --- | --- |
| 1 | 10 → 11 | WAIT、なし | — | 1 / 1 |
| 2 | 24 → 25 | s49-native-move-24 | 26 → 27 → 32 → 33 | 1 / 1 |
| 3 | 51 → 52 | s49-native-move-51 | 53 → 54 → 59 → 60 | 1 / 1 |

元Action24の **closure after33 → 次probe52** を、実行中のhost callback順序で保存。S2-A previous S16付き入力 **1件**。World後の結合だけで判定していない。

WB L1 **3件**、元native Python sourceと同一session/request/seqの一致 **3/3**、SelfWorld/SelfBody refs一致。M original batch **ORIGINAL_PYTHON_BATCH_RECORDED / RECORDED**。S16 closure callback **2件**。S2-B元L0/Intent owner context **3/3**、前S16付き入力にも同じepoch context成立。Intent owner ID `escape-threat`、実履歴 `len(intent.events)` **[1,1,1]**、実 `host.retained.revision` **[1,1,1]**。Intentに独立revision属性があるとの主張ではなく、固定値代用でもない。retainedの起源は元S49既存の **S19_FROZEN_SYNTHETIC_GOVERNED_REV1** であり、Worldで学習した状態ではない。

別Pythonプロセスの `tools.s537_s2b_original_owner_audit` **PASS**（入力3・閉鎖Action2・前S16付き1）。元native verifierを再利用し、session/probe/request、dispatch→S15→S16、closure→次入力、WB refs、owner epoch/Intent ID/generation/revisionを照合。異session・owner交換・replay/copy probe・retained交換・Intent prefix破壊/世代後退・未来S16・Action/S15/S16欠落・observer例外等の負対照を検証。

モデル呼出し **0**、S60投入 **0**、追加native reads **0**、追加Action **0**、学習更新 **0**、Energy debit **0**。原本JSONのcounterと実行経路に基づく。Energy信用や物理消費量を証明するものではない。

Cleanup **PASS**：Java PID157103 exit0、Node PID157191 exit0、Python PID157095 exit0、所有PID全消滅、`/tmp/relay-self-s49-a4gowugj`削除、port25565通常bind成功。S1/S2-A原本 **49ファイル不変**、main・他branch refs不変、固定owner不変。新規原本・stdout/stderr・実行HEAD・owner HEAD・独立監査・SHA256 manifestを保存。失敗World原本は該当なし。初回contracts失敗ログは保存。

Evidence: `/home/rinsa/work/s2b-world-evidence-20261102`。公開コピー: `docs/evidence/s537-s2b-world-20261102/`。Draft [PR #696](https://github.com/rinsakamo/relay-self/pull/696)、統合 [Issue #537](https://github.com/rinsakamo/relay-self/issues/537)。最終HEADのCI・remote一致・clean・GitHub API全文読戻しは納品記録へ追記する。

次の接続条件：今回のowner witness＋WB L1＋前S16を既存S60-A admissionへ渡し、S60-B1 async HTTP → 実Gemma L2 → 応答時source/session/epoch再照合 → current advisoryまたはstale/deferredへ接続する。実Gemmaのartifact hash・所有process/mapping・応答metadataと適用可能な実行予算を別途確認する。元L0は完了を待たない。遅延・timeout・transport不確実性は既存S60規則で処理し、GemmaにAction／Learning更新権限を与えない。今回その段階は未実行。

これは保存原本間の整合性と同一プロセスread-only接続のDEV検証であり、独立Paper/W3 source attestationではない。実Gemma、L2判断有効性、L1学習優位性、自己改訂、L2→L1→L0結晶化、QUALIFICATION／SCIENCEは未成立。
