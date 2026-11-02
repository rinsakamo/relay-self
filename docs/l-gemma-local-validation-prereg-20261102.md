# L PR #682 ローカル検証 事前固定

Base: Draft #682 `1edc89716af7253341165d44bd0e48398a470fa6`。
子branch: `dev/l-gemma-local-validation-20261102`。今回のユーザーmission、現行 #537 DEV運用、#431/#653の発達方針の範囲。科学/資格grant、過去one-shotは流用しない。

新規証拠root: `/home/rinsa/evidence/l682-local-validation-20261102T013000Z`。
最初に実Gemma合成HTTPプローブ1要求、retry0、World0。完全な10フィールドnative json_schema、strict true、reasoning_effort none、enable_thinking false、temperature0、seed1、stream/cache_prompt false、max_tokens512を固定。実GGUF SHA、exe/argv/maps、API、chat template、GPU、context/slotsを別保存。正常な既存サーバーがないことを確認してから既存binary/modelを起動し、downloadしない。プローブFAILならWorldを起動せず、通信互換性/予算/意味上の誤りを分ける。

プローブPASS時のみ新規Paper World1、session1、元S49 Action最大3、実World OPEN最大2、retry0。既存S49 ownerとGRASS/MOVE_BACKWARD条件、S15/S16/WAIT8を維持。H1原文とSHA凍結→Action2実測とH1誤差→H2凍結→Action3。無効OPENは次Actionを解放しない。L2 Action/条件変更/learning admission/L0 promotionは0。

EOF envelopeはこの新Worldに実行前opt-inする。Paper/raw HTTP/frozen H1/H2/native原本は成功失敗とも保存し、過去 #679 FAIL原本を変更・再認定しない。必須G3（expected-live-l2-calls2）、live-prefix、feedback original auditを別processで実行。feedback auditはCLI未実装なので公開関数を明示呼出しする。raw HTTPと報告/frozen本文・SHAも別照合する。必須失敗なら全World PASSを主張しない。

Aは有効OPEN2回と原本再構成、B1はH1→実測→誤差とH2の意味整合を別判定。B2は独立holdout不在でNOT_ESTABLISHED、Cは設計上NOT_RUN。CHEAP単発優位は今回の必須条件としない。

事前コード修正: プローブはキー存在と一部IDだけでなく、全10フィールドの型/enum/文字長/配列一意性/有限数値範囲と重複JSONキーを検査する。サーバーのgrammar自己申告を信用しない。
オフライン: 初期189 PASS。修正後Node22/JDK21固定で268 PASS（S49 cleanup/native custodyを含む）。初回拡張runはPATH不足で12 FAIL/256 PASS、原ログ保持。Ruff0.16.7、compileall、repository contracts PASS。Python環境にRuffがないため既存別venvの実Ruffを使用。実行HEADはこの文書を含むcommit後に外部execution-head.txtへ固定する。
