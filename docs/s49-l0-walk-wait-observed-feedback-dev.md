# RelaySelf S49 — observed L0 micro WALK / genuine WAIT DEV

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Starting source: `445796b3e63966eb873f31f63a3b00336be33e5c`; prior `S49_L0_THREE_REAL_S16_DEV_PASS` tested original Minecraft 1.21.8 S16 movements 3.030m → 0.815m → 0.324m. Second/third scalar travel 1.139m versus relative 1.0m target (overshoot +0.139m). No Paper/Node forced synchronization.

## Choice/action separation

Both arms run separate fresh vanilla Mojang Minecraft 1.21.8 disposable Worlds with original `NormalWorldL0`, existing NativeObservationOnly `session.receive()`, unchanged S14→S15→S16 issuer and independent grants. Each real World receives a far zombie event (original WAIT), two near zombies (original MOVE_AWAY) and a fourth fresh native zombie event. No extra action issuer, observer, replay, model call or S10/P1 authority.

**WALK**: after second native S16, original L0 independently chooses third MOVE_AWAY on fourth zombie; DEV bound S14 action ref for third Action is `MOVE_FORWARD` instead of `MOVE_FORWARD_SPRINT_DEV`, with same existing Mineflayer `set_control('forward', true)` effect. The third input duration is `clamp(residual / observed second-action speed, 0.10..0.60s)`; World physics/latency determine the actual movement. Original S16 reports the third WALK horizontal distance. This does **not** implement global WALK/JOG/RUN/DASH controller.

**WAIT**: original second S16 residual within explicit 0.20m deadband and no immediate threat (<1.5m) allows the **same** NormalWorldL0 to arm a source-identified stop criterion. On fourth independent real zombie/probe pair it chooses `WAIT` itself. `ReactiveL0.run_session` passes **no Action grant**, does not invoke Action request callback, and its Action budget stays at two real actions. Source carries the previous second closed S16 ID; no observer simulates the WAIT event. Outside deadband, mismatched session, stale Action, immediate danger or missing owner gates fail closed or preserve native threat MOVE. In this DEV, the 0.20m stop criterion concerns **relative 1.0m step scalar distance**, not absolute World coordinates. A real MOVE request cannot be secretly converted to WAIT in an action callback.

## Source gates / safety

Only when separately opted in: `S49_L0_OBSERVED_FEEDBACK_DEV_ONLY`, `S49_L0_RESIDUAL_THIRD_DEV_ONLY` (WALK), `S49_L0_WALK_THIRD_DEV_ONLY` (WALK), `S49_L0_GOAL_WAIT_DEV_ONLY` (WAIT), original `S49_NEXT_EPOCH_DEV_ONLY`, original S49/Mineflayer owners. No forced tick count, no always-on synchronous trace. The WALK and WAIT flags are mutually exclusive; all result receipts remain original S49 typed S16.

Workflow `.github/workflows/self-l0-walk-wait-two-worlds-dev.yml` performs Python 3.12 focused tests and Ruff, Node22 bridge syntax, original Mineflayer install, then two fresh real Worlds; archives raw source even on failure. A wrong Action count, missing S16 / STOP evidence, or a third Action in WAIT arm rejects the run. main and Draft #545/#634 remain unchanged.

### Limits

The WALK and WAIT World instances are distinct and their threat event timing is not phase matched. The near-target WAIT policy could choose to wait despite a zombie 2m away, but only in this explicit step-calibration DEV gate; real escape safety and integrated intent prioritization need separate real testing. This exercise is not QUAL/SCIENCE evidence or proof of actual absolute target position.

## 実機結果 — 2026-10-28 / exact SHA validated

[GitHub Actions #40628789022](https://github.com/rinsakamo/relay-self/actions/runs/40628789022): **completed/SUCCESS**。実行対象source HEAD `2f6384f0f25739d27403054753a294757b0ecc9f`、Python 3.12 focused pytest PASS、Ruff PASS、Node22 syntax PASS、Java21 original Mojang 1.21.8 / Mineflayer 4.39.0 / two independent Worldsの両方がPASS。独立Session UUID、元S49のtyped S14/S15/S16 original Action ownerと真のnative movement evidence。原本 artifact `s49-l0-walk-wait-two-worlds-40628789022-1` / ID **12790920388** / ZIP SHA256 **0f4b37c893f745309e4512261beed33d9e281a4e5f3a533af94ab459e93c87ea**。

**WALK World**: session `76066a43-0e18-422f-9a32-3453a2b2ac4a`。第一原S16 3.0301571644943626m、第二原S16 0.8149785454473797m、第二入力0.1980095313307358s、第三入力 **WALK 0.10s**（本物の `MOVE_FORWARD` / `set_control`）、第三S16 0.24950809810395602m。第二+第三のスカラー移動合計 **1.0644866435513358m**、希望ステップ距離1.0mに対する絶対誤差 **0.06448664355133582m**、第二だけの誤差 **0.1850214545526203m**。同一World内で誤差は0.120534811001m改善、ただし6.45cm過剰移動。前run #40627959223 の第三SPRINT試験（0.139m誤差）より小さいが、**異なるWorld・位相のため一般的WALK優位の因果判定ではない**。

**WAIT World**: session `790f2ea2-3a4c-48bb-b6e2-17fd354fc011`。第一S16 3.0301571644943626m、第二S16 0.8149785454473797m。第二終了時の1.0m relative-step残差は **0.1850214545526203m**。DEV tolerance 0.20m内に入ったため同一 original L0 が第二closed Action IDとsessionを元にowner-local STOPをarm。第四fresh original native zombie event seq **83** のL0実判断が **WAIT**、第三Action発行 **0**、計2 native Actions、両方S16 OUTCOME。これは後からキャンセルしたActionではなく `ReactiveL0.run_session` の本来のWAIT（grantなし・on_action_request呼出しなし）。

両World共に original L0/S14/S15/S16を維持、追加packet reader/Action issuer=0、実LLM呼出し=0、Paper/Node tick強制同期なし。STOPは実Worldの相対移動距離の許容差へのDEV criterionであり、絶対位置・経路追従・ゾンビ回避の成功を意味しない。危険距離1.5m未満なら本DEV WAIT基準より通常の脅威優先。ただし実Worldは2m脅威のものなので一般的な安全を証明しない。

**失敗原本**: run #40628715907 は新しいFocusedテストのRuff E701×7件でWorld起動前 FAIL。修正後 #40628789022 は独立にSUCCESS。 main・Draft PR #545/#634未変更、QUAL/SCIENCE未実行。

**次の実装優先順位**: S16スカラー移動の足し算から **同じWorld基準での始点・終点XZ位置差**へ変更（距離と方向を混同しない）。その上で、WALKの最小操作/加減速による行き過ぎのモデル化、STOP後の静止維持と危険割込みをL0に組み込む。今回が証明したのは限定的な「観測→L0選択→微移動／停止」であり、任意の目標位置への到達はまだ未実装。

最終分類：`DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。
