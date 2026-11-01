# L 実Gemma前仮説feedback — 新規1 World DEV事前固定

Base Draft #678 exact 16df233dbefb6caddee25904b0884cc2b5124628。
#431 / #653 / #537。#677の原World FAIL・必須監査2件FAILは不変。

権限: #537本文「2026-10-14 DEV / QUALIFICATION / SCIENCE」の所有使い捨てローカルDEV運用と2026-11-01の実Gemma接続方針、および今回のユーザーmissionの明示予算に限定。#656専用grant・消費済one-shotを流用しない。科学・資格・main mergeなし。

予算: Paper新規World1、Mineflayer session1、元S49 Action最大3、実Gemma OPEN最大2、retry0。GRASS_BLOCK / MOVE_BACKWARDと既存G3 operator刺激を維持。L2によるAction/条件変更/learning/L1-Habit admission/L0 promotionは全0。最初のJava World startでこの試験を使用済みにする。失敗でも再World禁止。

順序: S49 Action1→S16+WAIT8→OPEN1→H1/P1の原文・typed・SHAをexclusive/fsync保存→Action2→S16+WAIT8→P1対trial2総変位と絶対誤差→H1説明/反証条件/出典を含むOPEN2→H2を保存→Action3。OPEN2にはtrial3を渡さない。

EOFはWorld前にCLI --l-mp11-paper-eof-dev と L_MP11_PAPER_EOF_DEV=1 を固定。既存sole collectorのraw stdout出力を使用し、UTF-8ログとバイト一致を要求。raw原本のSHA/長さ、完全行SHA/長さ、suffixを別記。末尾は改行か改行+正確な2byte `> `のみ。未知末尾・不完全イベント・SHA不一致・未宣言はFAIL。過去FAIL再認定なし。

指標は WAIT8_TOTAL_M、pairごとの PAPER_NEXT_TICK_PREDICTION_M / PAPER_NEXT_TICK_ABS_ERROR_M、PAPER_CHEAP_NEXT_TICK_MAE_M、trial2対象の PRIOR_L2_NEXT_WAIT8_PREDICTION_M / PRIOR_L2_NEXT_WAIT8_ABS_ERROR_M を分離。引用はordinal/pair/role/valueを原typed値に1e-8m以内で検証。自然言語の数値意味・因果妥当性は別途人間可読監査で判定し、形式合格から推定しない。

実行前: Python3.12 focused、Ruff、compile/contracts、source-built Paper plugin、Node22/JDK21、実GGUF/binary SHA、実process argv/maps、loopback API、ctx8192/output512、RTX3060 VRAM、25565/8080競合なしを確認。既存正常llama-serverがあれば二重起動禁止。代替モデル/fixtureで実Gemma成功としない。

独立監査: mp11_g3_paper_one_world_audit.py --expected-live-l2-calls 2 と l_mp11_live_paper_postrun_audit.py を別processで実行。新EOFの2-call G3ではraw prefixから各LivePriorLedger/OPEN要求/応答/typed proposal SHAを再構成し、H1→feedback→H2・数値引用を再検証。独立監査FAILは補足で昇格させない。raw HTTP bytes、frozen H1/H2、W3、Paper、process identity、cleanupとSHA索引を保存。

事前判定:

- World PASS: 元runner PASS、予算遵守、必須2監査PASS、raw/EOF/prefix3/3、元Action/S15/S16/WAIT8×3、全所有process停止・World削除・port解放が揃う。
- A PASS: そのWorld内で実Gemmaが前試行だけを読み、有効OPEN2回完了・出典再監査合格。部分観測や失敗はPARTIAL/FAILのまま。
- B1 PASS: OPEN2がH1を明示参照してKEEP/REVISE/REJECT/ABSTAINを判定し、trial2実測とP1誤差を正しく使用。両者の型付き引用、説明の意味整合、H1 SHA連続を要求。予測なし/意味不整合/単なるlabel変更ではPASSにしない。
- B2: モデル/適用条件の実修正を独立後続観測で反証可能に検証した証拠がなければNOT_ESTABLISHED。仮説名変更は不足。
- C: 今回L2選択/実行/学習は0、NOT_RUN_BY_DESIGN。

証拠root: /home/rinsa/work/l-gemma-feedback-world-evidence-20261101。
実行HEADは検証後commitとpreworld-manifestに固定し、結果報告HEADと区別。判定条件を実行後変更しない。
