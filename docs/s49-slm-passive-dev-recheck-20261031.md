# S49 × SelfBody × L8 × M 修正後DEV再確認（2026-10-31）

検証対象は `7577c632a5f730a5503ad4f92774d89391e40a2f`。
local worktree `/home/rinsa/work/relay-self-s49-slm-20261031` とremoteの
`integration/s49-slm-passive-dev-20261031` が一致し、開始時はclean。
mainと他レーンは変更していない。本報告追加後のHEADはdocs-only commit。

## 実Worldの実施境界

Issue #537 の前回報告（comment 6538673639）と保存原本では、前回grantは
`c6a3e275ee8277f8a694a7627ac5eb030f168c90` の起動FAILで消費済み。
今回の依頼はfresh grantの明示承認を実行条件としており、新たな承認は確認できない。
したがって今回は **NOT_RUN / FRESH_GRANT_REQUIRED**。Java/Node/Worldの起動なし。
実Action 0、S16 OUTCOME 0、モデル呼出し0、学習更新0。
S42/SelfBody/L8/Mの実World診断は引き続き未検証であり、DEV実World成功とはしない。

前回FAIL原本は上書きせず、既存SHA256SUMSの全10件一致を確認した。
原因は `native` capture root未生成によるW3CaptureRejected。
前回Action 0、model calls 0、server_exit 0、slm_dev.rows空。
今回のcleanupは物理プロセスを起動しないため対象なし。前回のcleanup結果とは区別する。

## オフライン確認

修正はrunnerでqualify前にnativeディレクトリを作る1行。
既存focused試験で実W3コンストラクタを起動せずに実行し、同一root再利用を拒否する。
元NormalSessionActionExecutorクラスは固定S原本とAST一致。
ReactiveL0、ActionSupervisor、bridge、execution、action_outcomeの対象パスも差分なし。
既存の唯一のreader/Action issuer/supervisorを維持し、新しい物理ownerは追加しない。
S42は同一probeを既存coordinatorに渡し、SelfBody/Mは後段の受動投影、L8はretention OFF。
結合回帰はsynthetic fixture由来で、native authenticityや物理成功の証拠ではない。

結合回帰: 172 passed in 132.86s (0:02:12)。
Ruff PASS。repository契約検査はローカルnode_modules内MarkdownリンクでFAILし、
原ログを保持した。git archive HEADによる追跡ファイルのみのsnapshotではPASS。
検査器や契約は変更していない。

## 保存証拠と再開条件

前回原本: `/home/rinsa/work/evidence-s49-slm-20261031/`。
今回: `/home/rinsa/work/evidence-s49-slm-recheck-20261031/`。
focused.log、ruff.log、contracts.log（初回FAIL）、contracts-tracked.log、
unchanged-owner-paths.log、result.json、SHA256SUMSを保存する。

fresh grant承認後にのみ、別の未使用rootで既存runnerを1回実行する。
失敗時は原本保存し、無断retryしない。今回Paper/P1会計、実学習、QUALIFICATION、
SCIENCEを成功条件へ追加していない。

**DEV_ONLY / OFFLINE_RECHECK / REAL_WORLD_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**
