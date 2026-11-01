# L-BCG H5 — 専用DEV実World（2026-11-01）

継続grant: https://github.com/rinsakamo/relay-self/issues/431#issuecomment-6552384315 。
このレーンの今後のDEV試験も各試験の事前固定を行えば個別承認不要。
Executor HEAD: `9eb335fb82892a8d1d15579e09af42ebfcd710a5`。
Worktree: `/home/rinsa/work/relay-self-l-bcg-h4-20261101`。
外部原本: `/home/rinsa/work/l-bcg-h5-evidence-20261101`。原本を本ディレクトリへbyte一致で複製。

- 新規disposable World **1**、元S49 Action **1**、S16 OUTCOME **1**、再試行 **0**。
- L-BCG追加Action/native probe **0**、モデル呼出し **0**、learning/S10/S11更新・grant **0**。
- S49 sole issuer / L0選択を保持。`WAIT(9→10) → MOVE_AWAY(20→21) → WAIT(55→56)`。
- Action `s49-native-move-20`、S16 before/after **23/30**、変位 **0.6269065734210617 m**。
- session `afa3c38a-6e0b-404f-b46b-10132146ec62`、Paper World `93ca64e6-a7bc-4103-b0ef-e4edbec373fa`。
- 次native Present **56** を元SelfBody/SelfWorldが参照し、第3元L0選択完了後にL-BCG評価。
- `DEFER_UNKNOWN` / `CURRENT_GOAL_GAIT_P1_M_OBSTACLE_SOURCE_NOT_ADMITTED`、Action authority false。
- 観測cueは位置xyz、health、food/saturation、S42 threat距離、実在観測Entity距離の8値。
  Goal残距離/tolerance、歩容、P1疲労、M energy、verified obstacle、World revision、
  qualified post-clear trainingの8条件は不足。推定補完なし。有資格training World **0**。
- 元runnerの6 settling probesとPaper 8 callbacks（252–259）を使用。追加観測はない。
  252–254でlast-reported-input OFF中の変位あり。入力OFFは実効clearではなく、
  8 callbacksは8 Worldでも8 training例でもない。後続0変位を物理安定の認証にしない。
- `independent-audit.json`: 別プロセスで既存S7受送信receipt、S16 terminal、元L0規則、
  Paper prefix/final、packet footer、SelfBody/SelfWorld source、cleanupを照合しPASS。
  保存原本相互の独立読戻しであり、外部TCP認証や物理実効clear認証ではない。
- `host-preflight.json`: 指定CLIの **DEV_BCG_HOST_REPORT_SELF_CONSISTENT_ONLY**。
  一つのhost JSONの自己整合性。独立原本監査とは別判定。
- Python3.12 focused **142 PASS**、Ruff PASS。実行前exact HEAD関連5 workflow SUCCESS。
  H4記録の142 PASSも別記録であり、今回ローカル142 PASSは `preflight/focused.log`。
- Python3.12.3 / Java21.0.12.1 / Node22.22.2 / Mineflayer4.39.0 / Minecraft1.21.8。
  server/plugin/configのSHA一致、起動前port25565空きとclean worktree確認。
  Paper profile ACTIVE_METABOLISM_NOT_PASSIVE。モデル起動なし。
- Node **62553 exit 0**、Java **62445 exit 0**、所有子PID消滅、
  `/tmp/relay-self-s49-u1m2w5ke` 削除、port25565再bind PASS。
- 実測不一致・失敗は今回なし。runner stdoutのNode deprecation warningも原状保存。
  H4の初回FAILは既存H4証拠に保存されたまま。再試行・silent repairなし。

Paper原本は既存sole collectorのUTF-8 `server.log`。今回raw binary captureは使用せず、
これを独立raw stdout/TCP取得と呼ばない。L16 targetはoperator-localで独立Goal ownerではない。
L-BCG条件学習・heldout汎化・cheap比改善を測定した試験ではない。

**DEV_H5_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED /
GOAL_UNDETERMINED / EFFECTIVE_CLEAR_NOT_ATTESTED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
