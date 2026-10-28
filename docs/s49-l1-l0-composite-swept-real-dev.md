# L1動的再計画 × L0危険割込み — ローカル実機DEV

2026-10-28 JST。`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。

開始時remote `self/dev-l1-grid-refresh-inflight-l0-20261028` は指定先行HEAD
`d071b06d0c959768efd781ceceef1e739ed53a38` と一致。cleanなprimary main
`32fe105fc12cbf54abd11bfba7c8a75d319939df` を保存し、先行HEADから新worktreeと
`self/dev-l1-l0-composite-swept-20261028` を作成した。main、#545、#634は変更していない。

## 実装

42セル・4近傍BFSを維持。半径0.30mの連続区間を含む矩形の全占有列について
足元・頭部CLEAR、床BLOCKEDを要求する。UNKNOWN、範囲外、支持欠落は通行不可。
境界への接触のみで体積が重ならない隣接セルは占有に含めない。
現在姿勢→開始セル、BFSの各辺、各MOVE発行直前の観測姿勢→Waypointを検査する。
矩形は斜め補正の円掃引より大きいため、通れる経路をDEFERする場合がある。

既存S49 Supervisorが唯一の発行者。元readerのdecode前stdout captureを利用し、
追加readerを作らずnative原本を保存。L1は閉じたS16・Waypoint安定後のみ再計画し、
新revisionへ置換する。L0は実APPLIED後のnative live probeで割込み、UNKNOWNを再実行しない。
Worldコマンドは刺激であり、nativeの観測値との一致を別途検証する。

## ローカル実Worldの結果

[成功原本](evidence/l1-l0-composite-20261028/attempt03/HAZARD/goal_report.json) と
[decode前native bytes](evidence/l1-l0-composite-20261028/attempt03/HAZARD/w3-node-stdout.raw.jsonl)。
同一Java World、同一Mineflayer 4.39.0プロセス。公式Minecraft 1.21.8 / Java21 / Node22.22.2。

- 元L2 Goal・許容誤差を保持。最初の壁への2 MOVEはOUTCOME 1件とUNKNOWN 1件。
- revision 1の最初のWaypointまで3 MOVE OUTCOME。安定後、石を(2,2)へ追加。
- 同じreaderの最新ボクセルからrevision 2へ更新。旧経路の(2,2)を破棄し迂回。
- revision 2のMOVE `goal-approach-demo-grid-2-grid-turn-0-step-6` がAPPLIED seq **103**。
- その後ゾンビを出現。native危険検知 **106**、距離 **0.552025269708119m**。
- CLEAR ACK **107**、S16 **108**（primitive FAILED / Supervisor UNKNOWN）。
- 実MOVE **6件**、経路更新 **1回**（revision数2）、割込み後Action **0件**。
- 最終Goalは **INTERRUPTED_NOT_REACHED**。元target (1.5,-2.5) は不変。
- Node/Java exit 0、shutdown ACK、connection_end、World保存、25565再bind確認。
  これは高位STOP ACK・全tick停止・停止遅延の資格証明ではない。

同じWorldでseed **20261028**により複数配置を設置し、元readerで各42列を再観測。
REACHABLE / CHANGED はSELECTEDで異なる経路、SEALED / UNSUPPORTEDはDEFER。
この配置試験ではAction 0件。元配置を戻してnative再観測してから複合試験を進めた。
UNKNOWNは保存観測の行をUNKNOWNへmaskしたoffline負例とfocused testで検証した。
**実native UNKNOWN発生の実機検証はNATIVE_UNVERIFIED**。

## 原本監査と検証

[独立監査結果](evidence/l1-l0-composite-20261028/attempt03/composite_review.json)。
別モジュールがsealed SHA256・session/sequence・ボクセル・ACK・native危険entity・
全MOVE IDと割込み後0件・連続通過検査を保存bytesに照合し、BFSを再構成した。
S16のUNKNOWNは既存Supervisorの派生reportでありnative packetそのものではない。
stdout bytesはMinecraft TCP packet原本とは区別する。

Python3.12 focused **66 PASS**。Ruff、Node構文、diff whitespace検査PASS。
ACK、配置観測、掃引判定、Goalのreport改変を拒否する監査負例を含む。
CI/FULL regression・LLM・GPU・QUAL・SCIENCEは実行していない。

最初のshell起動はPATH空白の引用不備で実プロセス起動前に失敗しログを保存。
[attempt02](evidence/l1-l0-composite-20261028/attempt02/HAZARD/goal_report.json) は
壁接触の矩形境界計算により安全DEFER（runnerの局所判定PASS、複合missionは未成立）。
元bytesとWorldログを保存し、境界計算修正後に新Worldのattempt03で成立した。
初回監査のentity_id/id schema参照ミスも保存。同じ原本への監査修正で解決した。

## 再実行

新しい絶対output-dirを使い、既存 `s49_goal_loop_real_dev` に
`--offset-m 4.0 --obstacle-wall-dev --detour-after-wall-dev --native-voxel-map-dev
--local-grid-search-dev --left-lane-block-dev --grid-refresh-dev
--grid-midroute-obstacle-dev --grid-inflight-hazard-dev` を渡す。
confirmは `S49-GOAL-L0-DEV-DISPOSABLE-WORLD`。
既存workflowにあるDEV環境gate群を設定し、Pythonは `PYTHONPATH=src:tests:.`。
監査は `python -m adapters.mineflayer.s49_grid_composite_review_dev --root <HAZARDの親>`。

## 残る制約

平面・全立方体の配置、7×6×3 loaded cache、Waypoint境界更新に限定。
ジャンプ・階段・垂直移動、部分形状の床支持、任意の移動障害物、観測後の変化、
速度・惰性を含む実軌跡全時刻の掃引包絡、一般的な安全保証は未検証。
発行前の観測姿勢と直線通過矩形の検査であり、World全体の連続安全性の証明ではない。
