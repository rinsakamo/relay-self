# L 実Gemma前仮説feedback DEV — 1 World FAIL、再試行0

Draft #679（base #678）、#431 / #653 / #537。実行HEAD **bfd8bbb486cc230d4191cdbca7358686c2b517ea**。結果公開は別の文書・証拠commitで、実行HEADへ遡及しない。#677のWorld FAIL、必須監査2件FAIL、有効改訂UNDETERMINEDは変更していない。

**新規Paper World1 / Mineflayer session1 / 元Action1 / 実Gemma HTTP要求1 / 有効OPEN0 / retry0。全体FAIL。** 実Gemmaの応答は512生成tokensに到達し、finish_reason=length。既存canonical providerのstop要求が拒否し、H1の採用前に停止。Action2/3・OPEN2は未到達。条件緩和、別モデル、fixture、応答再送、再Worldなし。

## 実装と事前検証

- H1の説明・反証条件・Action/trial/World/session/prefixとP1対trial2実測・誤差をOPEN2へ渡す。H1/H2は排他的作成とfsyncが成功した後だけ次刺激を解放。
- L専用canonical HTTP requestでresponse bytesをdecode前に保存し、不正UTF-8/JSON/HTTP errorも原文を保持。最大512生成tokens・1要求1試行・timeout・Action権限0は維持。
- 新EOF opt-inのみ既存sole Paper collectorのraw stdout機能を使用。rawとliveログのbyte一致を要求し、原本と完全行のSHA/長さを分離。既存strict parserは不変。bool/int envelope偽装も拒否。
- 新方式の2-call G3独立監査では、Paper prefixからtyped ledger、各OPEN要求、原応答、proposal SHA、数値引用、H1→feedback→H2を再構成。中断OPENはfailed_closedに固定。
- 事前判定は[prereg文書](l-gemma-feedback-world-prereg-20261101.md)と原manifestへ固定。A/B1/B2/Cを結果後変更していない。

Python3.12回帰 **237 PASS**、その後の取消/envelope型負対照追加を含むfocused **67 PASS**（重複あり、合計しない）。Ruff、compile、repository contracts、JDK21 source plugin build PASS。初回拡大テストのNode/JDK PATH不足12 FAILを保存し、既存Node22/JDK21指定の237 PASSで解消。World前の既存177件もPASS。

実行HEAD CI **5/5 COMPLETED SUCCESS**（source-only、モデルはfixture）:
[EOF/feedback](https://github.com/rinsakamo/relay-self/actions/runs/41317304179)、[OPEN](https://github.com/rinsakamo/relay-self/actions/runs/41317304238)、[prior source](https://github.com/rinsakamo/relay-self/actions/runs/41317304246)、[G2](https://github.com/rinsakamo/relay-self/actions/runs/41317304249)、[G3](https://github.com/rinsakamo/relay-self/actions/runs/41317304219)。

## 実World・モデル原本

World UUID **8bcb1db7-4e3c-4e73-88da-2c982cfe7ded**、session **2cd745a5-769a-4ea0-8f73-bd8963418af0**。元GRASS/MOVE_BACKWARDを維持。Action **s49-native-move-41**、before43→dispatch44→S15 clear49→S16 after51、元変位 **0.7342911432182311m**。Paper WAIT ticks **292–299**、総変位 **0.064246601508961m**、7 forecast pairs。報告のactual_native_actionsとdecisions一覧は任意OPEN callback終了後の追記前に失敗したため空だが、typed_s16_actions・raw W3には1件がある。原reportは修正せず、[独立失敗run読戻し](evidence/l-gemma-feedback-world-20261101/independent-failed-run-readback.json)へ実件数を別記。

GGUF `/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf`:
`c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`。
llama.cpp binary SHA `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`。
実PID103190のexe/argv/GGUF process mapping、localhost8080 API/aliasを確認。ctx8192、parallel1、max output512、RTX3060 12GB。読込後VRAM約8599MiB、Paper同時稼働snapshot保存。既存サーバーなしを確認して1回のみ起動、モデルdownload/代替なし。

HTTP1: **16.218483574秒、prompt2004 / output512 tokens**、response ID **chatcmpl-qMjF7KTfNY9LHfIo9HafPbDZ4vBlaIiF**。実HTTP要求/応答raw bytesとjournalを保存。返答contentは閉じたJSONでもfinish_reason=lengthであり、有効OPENへ読み替えない。

## H1/H2・予測と数値意味

**有効H1なし、H2未生成。** 不採用応答候補はOTHER_BOUNDED / KEEP_UNRESOLVED、次案CHECK_PAPER_CALLBACK_PHASE。「予測誤差0.032mとcheap-zero約0.002mからsystematic offset」と説明し、異なるblock typeで持続するか反証する案。候補の次WAIT8予測値は **0.064246601508961m**（直前実測の反復）。trial2がないため対応する次実測・絶対誤差は **NOT_AVAILABLE**。trial1実測と候補予測が一致しても、次試行検証として採点しない。

形式検証へ到達しなかった数値引用も、別のreadonly再照合で **1/4一致、3/4不一致**:

| role / trial / pair | モデル引用 m | 元typed値 m | 結果 |
| --- | ---: | ---: | --- |
| CHEAP_NEXT_TICK_MAE / 1 / 0 | 0.0021077733153767 | 0.0021077733153767675 | 一致 |
| NEXT_TICK_PREDICTION / 1 / 1 | 0.0062033431985539 | 0.032169922395860355 | 不一致（次pair値） |
| NEXT_TICK_ABS_ERROR / 1 / 1 | 0.0009925349117687 | 0.0226263174750082 | 不一致（次pair値） |
| NEXT_TICK_PREDICTION / 1 / 2 | 0.0033870253864104 | 0.006203343198553902 | 不一致（次pair値） |

説明の0.032mはpair1の予測変位で、誤差ではない。実誤差は約0.0226263m。CHEAP MAEは閾値やWAIT8総変位誤差とは別。一つのgrass試行からglobal offsetやsurface依存の因果は確定できない。モデルがstop終了していたとしても、この引用は既存strict検証で拒否される。

## EOFと必須監査

Paper raw original **441640 bytes** / SHA **7dab6bf88c5bd83feb51157eb281d0b7787a52a016c93c5027720b8722b0f44c**。
完全行 **441638 bytes** / SHA **3e1b5877e708c15ed2ce2fe5aaa3b408c0f71bbf29c06457bd76aab9a83eff0c**。
末尾 **3e20**（正確なJLine `> `）。rawとUTF-8 viewは全byte一致。保存prefix SHAは **d137d13b80385852345b933aafa60b0e64a042905b5d538ddb6c834f98fba0e4**、原本との照合 **1/1**。3/3は未到達。

runnerは既にFAILのため成功後のEOF sealing区間へ進まず、原reportにenvelopeなし。別processが実行前manifest/原rawからEOF形状を再確認しただけであり、World/必須監査のPASSではない。

1. `mp11_g3_paper_one_world_audit.py --expected-live-l2-calls 2`: **exit1 / FAIL**。
2. `l_mp11_live_paper_postrun_audit.py`: **exit1 / FAIL**。

どちらも元runの非成功を拒否。`--expected-live-l2-calls 2`は要求された検証期待値として使用したが、実績2回とは主張しない。補足readback・EOF形状確認でFAILを昇格させていない。

W3 original SHA **6c1af0e609ad025112f43504ce45f2866d88f9dee51d392e0ab83465beb33c5f**。
原report SHA **a330e2185ca447c45967e32a19c524e84ff2e716d12a9b4453e788f9d8ddb52b**。
Node stdout JSONLは独立Minecraft TCP認証ではない。共通物理時計、実効clear tick、Goalは未認証。

## 個別判定とcleanup

| 項目 | 判定 |
| --- | --- |
| A 実ライブL2・有効OPEN2回 | **FAIL（有効0/2、実HTTP1）** |
| B1 H1を次経験で自己評価 | **NOT_REACHED** |
| B2 有効モデル改訂と独立後続検証 | **NOT_ESTABLISHED** |
| C 自律物理実験 | **NOT_RUN_BY_DESIGN** |

L2追加Action/条件変更/learning admission/L1-Habit採用/L0 promotionすべて0。Goal UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。

Java103286 / Node103399はexit0、PID消失。World `/tmp/relay-self-s49-ml2z6k9x`削除。所有Gemma103190もSIGINTでexit0/PID消失。25565/8080再bind確認。再起動・再試行なし。

[証拠とSHA索引](evidence/l-gemma-feedback-world-20261101/SHA256SUMS.json)、[原report](evidence/l-gemma-feedback-world-20261101/report.json)、[実応答原文](evidence/l-gemma-feedback-world-20261101/llama-response-1.raw.json)、[独立補足script](evidence/l-gemma-feedback-world-20261101/independent_failed_run_readback.py)。外部原本root `/home/rinsa/work/l-gemma-feedback-world-evidence-20261101`。

次の実装課題は、**別のprospective試験**に向けて512tokens内のコンパクトな出力と明示的な1-based pair/role表を用意し、数値取り違えの拒否を維持すること。失敗時にも実Action件数・EOF envelopeを独立して保存するhost報告順序の改善が必要。今回のresponseを修復・再送・再採用せず、今回の成功条件/予算を変更しない。新規WorldでのA/B1達成は未完了。
