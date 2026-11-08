# SOUL matched choice — 実Gemma DEV結果

分類: DEV_ONLY / MATCHED_MODEL_CHOICE_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。
推論HEAD `3971437bd8f191b7147a63e14cd53f5c1c65055b`。4条件を事前登録順に各1 POST、自動再試行なし。初回サーバーのバックグラウンド起動はPIDを残さず終了、POST前に別の専用foregroundプロセスで起動した。旧原本SHA256SUMSは12+8+8+10件全一致（外部署名ではない）。GGUF SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`、llama-server build10874、実体SHA256 `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`。専用PID 458820のargv、mmap、GPU、APIモデルID、単一slotと8192 contextをruntime記録に保持。各推論後に原本および同一PID・mmap・API・slotを確認した。

| 条件 | 生選択 | Schema / 意味Validator | 仮説 / PROBE / 予測 | prompt / completion tokens | 秒 |
| --- | --- | --- | --- | --- | --- |
| Neutral | PROBE | PASS / 拒否 | MOTION_EFFECT_CHANGED / MOTION_REGIME_PAIR / UNKNOWN | 3568 / 335 | 12.714 |
| Curious | PROBE | PASS / 受理 | MOTION_EFFECT_CHANGED / MOTION_REGIME_PAIR / A_FAILS_B_SUCCEEDS | 3610 / 275 | 11.775 |
| Cautious | PROBE | PASS / 受理 | MOTION_EFFECT_CHANGED / MOTION_REGIME_PAIR / A_FAILS_B_SUCCEEDS | 3609 / 295 | 12.319 |
| Bold | PROBE | PASS / 拒否 | MOTION_EFFECT_CHANGED / MOTION_REGIME_PAIR / UNKNOWN | 3609 / 223 | 10.294 |

独立監査 `matched-audit.json` は原本とreportの一致、SOUL以外のrequest一致、Schemaと意味Validatorの再計算を確認。Raw statusは同じ、予測と受理可否は異なる。受理された2件の行動関連signatureは同一で、理由文と参照IDは異なる。4条件の差は理由文だけではないが、受理済み判断の間で行動方策差は観測されない。全てSkillなしのためSkill実行条件・予算の比較対象なし。modelの理由文はモデル出力であり物理的事実の認定ではない。

実行コードはSkill holdoutを無効化し、PROBEも実行しない。模擬Action、実S49 Action、holdout使用は0。監査はreportと実装の境界を確認するもので外部の物理実行監査ではない。予約seed 20261126、20261205、20261213は開いていない。cleanupで専用PID消失、port閉鎖、GPU 808 MiB（開始時と同値）を確認。他レーンを停止していない。

各1回、固定順、SOUL長・時系列の交絡がある。持続的SOUL効果・人格・実World学習は未実証。#220 CLASS Eは不変。次は固定した文と独立状況を用いる事前登録・順序均衡反復を検討し、SkillやPROBEの実行は別途の権限と検証が必要。
