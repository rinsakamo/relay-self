# K3-H 実Gemma DEV 検証

分類: DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。推論時HEAD `4443807a517a0d8114d74c8bd02a58ab0636e0cb`。#802、親 #797。GitHub checks は推論後時点で0件、未実施。ローカルの focused pytest は199件通過、Ruff全対象・repository contracts通過。初回pytestは未承認proposalの拒否エラー順序1件、Ruffはimport 2件で失敗し、原本を保存。修正後に再実行。元4入力manifest全件通過。10 Actionは専用予算、旧Skill上限4不変。UNKNOWN、有効予算、偽source、不明ID、Goal停止、Outcome改ざんをfocused testsで確認。

モデルは実測GGUF SHA c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed、llama.cpp build10874、専用PID 462143、argv/maps/GPU/API/slot をruntime.txtに保存。温度0、reasoning none、strict schema要求、各1 POST・再試行0。strict指定のサーバ側強制そのものは独立証明していない。最初のbackground serverは残らずPOST前に終了、ログとPID保存。cleanupで専用PID終了、GPU 808 MiBへ復帰。

Phase A: `TRY_MOVE` A、上限10、予測 `UNKNOWN`、schema PASS、意味Validator PASS。理由原文: “Arm A represents the standard movement regime. Given the increased action budget of 10, I can reliably reach the target distance of 3.2m on a normal surface.” 予測UNKNOWNと理由内の強い到達見込みは分けて保存。HTTP 200、prompt 3512 / completion 194 tokens、8.615秒。

Phase B: 明示grant、seed 20261219、Aのみ、2 Action、trace 2.4 → 3.037183 → 3.696063、Goal成功で停止。新ID `k3h-experience-A`。別プロセスの再実行と別算術実装双方で照合。旧予約seedは未開封。実World/S49 Actionは0。

Phase C: HTTP 200、prompt 3527 / completion 257 tokens、11.191秒。schema PASS、意味Validator PASS。次 `TRY_MOVE`、Skill null。原文: “The fresh mock observation (k3h-experience-A) confirms that on a 'normal' surface, the 'MOVE_AWAY' action is highly effective, reaching a final distance of 3.696 (exceeding the 3.2 target) in just 2 actions. This reinforces the reliability of Arm A for the current environment. While some 'shift' experiences showed failures at 5 actions, the 'train' experiences and the new mock data confirm that the standard movement regime is robust for the target distance.”

判断カテゴリはTRY_MOVEのまま。新観測の数値は正しいが、一例による reliability/robust の一般化は未実証。独立意味Validatorは予算とID等を検査し、説明の真実性や理解の証明ではない。Skill候補なし、実行意味の変化なし、独立holdout・正式Learning/Habit更新・Skill install・L0昇格なし。SOUL注入なし。科学的効果・実World能力・学習成功は未実証。
