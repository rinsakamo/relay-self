# WB lane — bounded SelfWorld / SelfBody cognition slices (2026-11-01)

**Status:** DEV implementation on a branch stacked on the existing [SelfBody/SelfWorld Draft #634](https://github.com/rinsakamo/relay-self/pull/634), which itself is stacked on S #545. No main merge or new Action authority. Owner Issues: [#632](https://github.com/rinsakamo/relay-self/issues/632), [#633](https://github.com/rinsakamo/relay-self/issues/633). Developmental-learning direction: [#537](https://github.com/rinsakamo/relay-self/issues/537), [#431](https://github.com/rinsakamo/relay-self/issues/431), MP11 [#653](https://github.com/rinsakamo/relay-self/issues/653).

## Problem and boundary

`SelfBodyView` and `SelfWorldView` already represent one source-bound, fallible decision epoch; the new need is **bounded presentation** to L0/L1/L2, not another mutable body/world model or a second place that learns physics. In simple familiar situations fixed L0 can and should remain the cheap path. Unfamiliarity or error may justify higher-level detail and experiment selection, but projection alone does not run an LLM, update beliefs or establish learning.

`relay_self.self_cognition_slice.project_cognition_slice` is a pure read-only helper. A caller must first construct a **qualified** `SelfWorldView` using the existing owner projection, with the optional exact `SelfBodyView` join. The helper checks identity/session/epoch and, where both native observations exist, sequence/request/provenance equality. This secondary check is **not independent native source attestation**. Source provenance is carried through to the returned immutable observations.

- **L0:** at most 2 observed body fields (health, food), 1 nearest observed exterior entity, no memory/model payload.
- **L1:** at most 4 observed body fields, 3 exterior entities, no hypotheses or retained content.
- **L2:** at most 6 body fields, 8 exterior entities, 4 own previously selected Memory **IDs**, 4 scenario **IDs**. No Memory content, private other-Self state, or hypothetical prediction is ever presented as physical observation.
- All tiers: `UNKNOWN` if there is no Present, otherwise `BOUNDED` or `TRUNCATED`. No implicit `CLEAR` state; zero visible entities does **not** prove global absence/safety. `detail_available` indicates bounded omission or alternate read-only evidence that may be explicitly requested from its existing owner; it does not authorize sensor polling or a physical LOOK.
- All tiers: `world_omitted`, `body_omitted`, `remembered_omitted`; a stable presentation order by distance is not a threat model or action priority.
- `source_attested=False` explicitly marks that upstream independent physical qualification has not occurred in this projection.

## Cross-lane contract

WorldBody and the single original S49/Action owner remain the sole physical interface. Existing native Present/S16 → SelfBody/SelfWorld → this bounded cognition slice → existing L0/L1/L2 consumers. Any extra detail is a **read-only local request** to existing views, not a new packet, observation, retained update, native reader, or external model call. S integration decides whether and when to expose the slice; it is **not wired to the live L0 selector by this DEV change**. Existing S10/S11 admission and L0 promotion gates remain untouched.

The L lane owns model family/applicability revision and experience crystallization. WB only preserves correct epistemic labels and bounded context from already qualified received information. M owns true energy/fatigue and resource accounting. WB does not turn Food into M Energy or predictions into actual capability.

## Verification and explicit gaps

Synthetic offline tests cover missing Body/World, L0 continuity, bounded tier size, full-vs-truncated coverage, provenance, cross-Self/session rejection and immutable outputs. Exact-source live Paper verification, effect on real L1/L2 decisions, budget/latency telemetry, native time/freshness revalidation, retention transfer, cognition-resource payoff and scientific value all remain **NOT_RUN** until separate owner-controlled integration. No real Minecraft or Gemma run is implied.

**Classification:** DEV_ONLY / OFFLINE_CONTEXT_SLICE / NO_NEW_SENSOR_OR_ISSUER / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.

## Next step implemented: existing L2 observer read-only hookup (DEV opt-in)

The already existing `LiveL2Observer` performs its own one native S49 Present → source-bound Body/World composition and review. When explicitly instantiated with `self_world_live=True, wb_cognition_slice=True`, or when the existing disposable native-selfworld DEV is launched with the **additional** `--wb-cognition-slice` flag (alongside its pre-existing `--live-think --self-world-live` requirements), the L2 **advisory-only prompt** now shows a bounded `observed` list (max 8) plus source/status/omission metadata from the shared WB projection. The prior model-review evidence and body health/food source remain in the prompt. There is no second native probe, no additional LLM call, and no change to the single original S49 Action owner. Invalid flags fail before World execution. The default-off path retains its legacy prompt.

The existing `S60` model-provider and L2 cancellation/expiry boundary is unchanged; only the optional **model-facing input** changes. The new `wb_cognition_budget` metadata explicitly states `source_attested=false`: a source-bearing projection is not independent physical attestation. An LLM response remains advisory, not a World fact or retained model update. More concise context is a candidate benefit, **not measured token, latency or cognitive-quality improvement**.

Synthetic tests use an in-process fake one-shot loopback provider to exercise the existing observer. This does **not** establish a real Gemma run, World experience, retained learning, L0 policy change, R qualification or V science. Physical integration remains NOT_RUN and any actual owner-run must be recorded separately.

## 2026-11-01 WB DEV integration result

Fresh remote/PR/owner readback confirmed #669 at `31df88b7ab71609f2aa824d55b87106daa9e8e78` and the #537 DEV disposable-World rule. Its FAST pytest failed four tests. The repair at `bb4098666877808bf13aa5baa1f42aae584afa94` keeps the default-off `_run_disposable` call signature unchanged (only opt-in passes the WB keyword), and corrects the new test's Body reference to `native-probe:…`; World references remain `present:…`. No source reference was rewritten to make a test pass. An additional omission regression checks that a prior target outside the nearest eight observations still has its prediction review retained, including an observed mismatch.

### Actual World and model boundary

One fresh vanilla Minecraft 1.21.8 World, Mineflayer 4.39.0, Java 21 / Node 22, run `dee27145998f4713896094f4ee8bacb9`, session `8b60ffd8-48d1-4d6c-8529-c38999262d79`. The existing `self_demo --mode DEV --dev-scenario native-selfworld` entrypoint used `--live-think --self-world-live --wb-cognition-slice`. S49's only three decision probes were seq **10,21,51**; decisions WAIT, MOVE_AWAY, MOVE_AWAY. Exactly **two** original S49 MOVE_BACKWARD Actions reached OUTCOME: `s49-native-move-20` (before/after seq22/30, movement 0.7342911432182309m) and `s49-native-move-50` (seq52/59, 0.6269065734210617m). WB issued zero Actions and added zero native probes. L0 did not wait for L2. The existing S16 offline source audit found two positive label-persistence comparisons; this does not establish learned dynamics or Goal success.

The existing S60-B1 observer submitted **one actual Gemma inference**, not a fake provider: existing llama.cpp build10874/e2d2c0d6a, binary SHA256 `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`, Gemma4 12B Q4_K_M SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`. Backend log records 1153 prompt tokens, 96 generated tokens, 3929.65ms total backend evaluation. **S60 provider status is UNCONFIRMED, accepted text is null.** Real inference occurred; successful usable Gemma completion is NOT established. The original strict transport/completion gate was preserved. The exact rejection subcause is UNDETERMINED; no speculative diagnosis is reported as fact. S49's own `real_model_calls=0` excludes the separately enabled L2 observer.

The live source pair seq10→21 had different zombie IDs; the original target was unobserved, so prediction review correctly stayed `undetermined / target_or_property_unobserved`. Energy/fatigue remained UNKNOWN. No model output entered Action, learning, Memory, M/P1 or L0 promotion.

### Same-source comparison (offline, no additional inference)

The same three already received immutable callback objects were copied for evidence; the first two were projected after the World run with WB off/on. No replay into the live observer, extra native receiver or World effect was introduced. Two `/tokenize` calls used the loaded model tokenizer, without inference.

| Metric | WB off | WB on |
| --- | ---: | ---: |
| Current source seq | 21 | 21 |
| Observed exterior cues | 2 | 2 |
| User prompt UTF-8 bytes | 1819 | 2317 |
| User prompt tokenizer tokens (no chat template) | 840 | 1118 |
| Projection time, single offline sample | 0.341ms | 0.524ms |
| Omitted current entities | 0 | 0 |

Body health/food and UNKNOWN energy/fatigue, observer/source metadata and the complete prediction-review object compare equal. Entity identity/label/position/distance are preserved; Both retain origin and visible-action fields; WB adds explicit budget metadata. No important received cue was lost in this two-entity case. The synthetic ten-entity regression deliberately omits two entities, including the farther prior target, while retaining its mismatch review. It does not prove those omissions harmless for other decisions. At low density WB costs **278 extra tokens (+33.1%)**. Neither efficiency nor decision-quality superiority is established. Only WB-on had live inference; model latency/quality of WB-off is NOT_RUN. The two projection times are not a controlled performance benchmark.

### Custody, cleanup and unresolved work

Original evidence is outside the checkout: `/home/rinsa/evidence/wb-669-20261101/` (failed initial CI log, local checks, received probes, prompts, tokenizer comparison, model process lifetime and backend log); World receipt/native report/logs and original manifest are `/home/rinsa/work/wb-669-world-20261101-01/`. Physical runtime HEAD was `bb4098666877808bf13aa5baa1f42aae584afa94`; `git_dirty=true` is retained, not silently changed: generated untracked Python caches existed at launch, and the later omission-only test was added during the run. Runtime source was not edited during execution. Later test/documentation commits are not represented as a new physical run.

Java and Node exited 0, the fresh World directory was removed, and the owned Gemma process exited 0 after SIGTERM without SIGKILL. Native STOP ACK remains **UNATTESTED**; process cleanup is not physical idle or GPU-release qualification. Unresolved: usable S60 Gemma completion/rejection diagnosis, actual L0/L1 slice consumers (this change wires only advisory L2), grounded omission importance across larger scenes, controlled token/latency payoff, source-independent qualification and scientific evaluation. **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.** Main and all other lanes/frozen evidence remain unchanged; no merge.


## 2026-11-01 next WB step — S60 receipt-bound diagnostics (no new World)

The prior actual World established that the Gemma backend executed inference but the existing S60 client returned `UNCONFIRMED` and `accepted_text=null`. It did **not** establish whether the first cause was HTTP envelope validation, a transport/host timeout, or invalidation by the next World observation. The original local raw evidence remains at `/home/rinsa/evidence/wb-669-20261101/`; GitHub alone cannot independently inspect that path.

The opt-in `LiveL2Observer` now reports `wb_s60_diagnostic` in its existing read-only `l2_live_observer` row. No change is made to `LoopbackDisplacementAdapter`, `BestEffortDisplacement`, L0, or the provider acceptance gates.

- `transport_events_before_cleanup` and `transport_events_after_cleanup` distinguish native model-result processing from cancellation performed by cleanup. They are the existing S60-B1 adapter event names, not packet or server logs.
- `owner_events_before_cleanup` and bounded `source_advance_samples` (max eight) capture the existing S60-A receipt names and transport receipt names **before** the original owner observes the next native source. Each snapshot carries only the newer native sequence number and sanitized host event names.
- `http_completion_observed_before_cleanup` is TRUE **only** if the existing transport emitted `HTTP_COMPLETION_OBSERVED` before cleanup. This is a host-side validated HTTP completion, not successful L2 acceptance or backend-idle attestation.
- `accepted_current_text`, `root_cause=UNDETERMINED`, and `native_stop_ack=UNATTESTED` deliberately preserve the difference between valid source-scoped content, unknown failure cause and missing physical stop verification.
- `wb_s60_diagnostic` is **absent when the WB feature is OFF**. There is no extra native read, model query, cancellation, or retry.

Offline fake-server tests distinguish validated transport followed by later source invalidation from HTTP 503 failure; they require all Action/LRN counts to remain zero. These tests do not explain the **previous** real Gemma run. To distinguish that run, LocalCodex must inspect the already saved immutable callback/model receipts first. Only if an additional DEV real World is justified may the existing explicit disposable World lease be used, retaining all negative and cleanup evidence. No new real World or model inference was run for this diagnostics-only change.

A follow-up comparison should separately count L2 prompt payload, completion acceptance, provider timing, source-advance ordering, omitted cues and no-action safety. The prior WB ON +278 tokenizer tokens remains a negative efficiency result; diagnostics alone does not demonstrate a token reduction.

**Current label for this diagnostics change:** `DEV_ONLY / SOURCE_ORDER_DIAGNOSTIC_ONLY / ROOT_CAUSE_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## 2026-11-02 — S60/Gemma UNCONFIRMED 原本診断

**最終分類: DEV_ONLY / PROVIDER_FAILURE_BEFORE_WORLD_DISPLACEMENT / HTTP_OR_ENVELOPE_CAUSE_UNDETERMINED。** 元WorldをPASSへ変更しない。新規World、実Gemma推論、追加Action、追加native probeは今回すべて0。S60-A/B1、S49、S16/S17、Memory、L、M/P1のowner実装・受理条件は変更しない。

### 原本・source identity

- `/home/rinsa/evidence/wb-669-20261101/SHA256SUMS`: 40件全一致。
- `/home/rinsa/work/wb-669-world-20261101-01/SHA256SUMS`: 6件全一致。
- 実行receiptはHEAD `bb4098666877808bf13aa5baa1f42aae584afa94`、`git_dirty=true`。clean checkoutだったとは主張しない。保存済みcleanup auditにある4 runtime blob SHA256はそのHEADのGit blobと一致。後続の`fb52bf67…`は報告時HEADであり実行HEADではない。
- 現行S60-A/B1の2 sourceファイルは実行HEADのblobとバイト一致。新しい診断は過去World実行時にはなく、当時のtransport receiptsを復元できない。
- 今回の外部証拠: `/home/rinsa/evidence/wb-669-diagnostic-20261102/`。保存済みcallbackを読み戻すスクリプト・結果、focused/FAST/Ruff/contractsログを保存する。原本は上書きしない。

### 時系列と証拠の限界

別clock間を結合せず、native sequence、owner receipt配列順、backend相対clockを独立して示す。

| 系列 | 保存された順序・値 | 判定できる範囲 |
| --- | --- | --- |
| S49 callback | event/probe 9/10 → 20/21 → 50/51 | WAIT → MOVE_AWAY → MOVE_AWAY。L2 source seq=21、最新seq=51 |
| S60 owner | NEW_REQUEST_STARTED → PROVIDER_UNCONFIRMED → DISPLACED → HOST_CANCEL_REQUESTED → HOST_CANCEL_UNCONFIRMED | provider未確認は後続Worldによるdisplacementより先。後のcancelを最初の失敗原因とはしない |
| llama.cpp相対clock | 26.955秒 task 0開始 → 30.884秒 timing/slot release → 44.257秒終了cleanup | prompt=1153、generated=96、total=3929.65ms。HTTP受信・S60採用・STOP ACKの証明ではない |
| 終了 | text=null、text_current=false、UNCONFIRMED | 有効L2採用0。モデル推論1と区別 |

HTTP status、Content-Length/chunked framing、response body、model alias、choices/message.content/finish_reason、transport receipt配列、各callback/受理時刻は原本にない。`TRANSPORT_UNCONFIRMED`は現行B1ではconnect/read/framing/envelope等の例外を共通イベントへ集約する箇所にあるが、元runでの当該イベント自体は未保存。`HTTP_COMPLETION_OBSERVED`/`BACKEND_COMPLETION_OBSERVED`/`STALE_REJECTED`は元owner配列にはなく、前者はそもそもtransport配列未保存。HTTPが届かなかったとも、有効HTTPが届いたとも断定しない。deadline超過を直接証明する時刻もない。ownerの配列と実装からprovider失敗経路まで絞れるが、低層原因の確定には足りない。

S60-B1は完全にframedされたHTTP 200と有効envelopeを検証してから`HTTP_COMPLETION_OBSERVED`、S60-Aは成功Futureをtickで処理して`BACKEND_COMPLETION_OBSERVED`を記録する。後者の名称はこのclient/provider契約内のcompletionでありGPU idleの独立証明ではない。`finish_reason="length"`かつcompletion_tokens=96は要求上限96の範囲で許容される。**96 tokensに達したこと自体は拒否理由ではない。** reasoningのみでcontent空、alias不一致、不正metadata等は候補として再現できるが、実応答が未保存なので元runの原因とは断定できない。

### WB修正とオフライン検証

既存`wb_s60_diagnostic`に独立したhost事実と`completion_state`を追加する。HTTP status/framing/envelope詳細は`UNRECORDED`、root_causeは`UNDETERMINED`のまま保持する。body/headers/例外文やpromptを診断へコピーせず、新しいtransport hook/observer/providerを作らない。

- HTTP完了未確認とprovider失敗を区別して表示。
- HTTP検証済みでもownerが未処理、またはSTALE_REJECTEDだった場合を別表示。
- 実際に採用した後のWorld更新は`ACCEPTED_THEN_WORLD_ADVANCED`。HTTP成功だけでは採用済みとしない。
- cleanup前のlease active、owner completion、過去の採用有無、source/latest seqを既存ownerから読む。cleanup後イベントと混同せず、lease activeをbackend稼働の物理証明に使わない。

追加23件: WB OFF/ON × 9 HTTPケース（200 length上限ちょうど、chunked、503、不正JSON、alias不一致、空content、reasoning-only、上限超過、未知metadata）=18、World前/後・deadline・cleanup境界=4、HTTP完了後owner poll前にWorld更新してSTALE_REJECTED=1。fixture barrierで順序を制御する。すべて合成HTTPであり実モデル呼出しではない。既存S60-A/B1負例も実施。

Focused合計182 PASS。保存済み3 callbackはwire/dataclass名を明示変換し、JSON正規化後の全フィールド一致を検査してから既存decode/projectionを利用。保存済みsource + 合成HTTPの3ケース（current採用、応答前更新、採用後更新）はPASS。元応答・元時刻のreplayではない。S60 ownerの不具合を確定する再現は得られていないため、owner実装の修正案やゲート緩和は採用しない。

### 認知予算・cleanup・残件

元の同一source比較 **WB OFF/ON = 840/1118 user-prompt tokens (+278)、1819/2317 bytes** を維持する。少数entityで情報量削減は未成立。今回はprompt構造を変更しない。今後はsource参照の重複を同一入力内でまとめる案と、大規模観測の有界要約を検討できる。ただし対象・予測誤差・適用条件・UNKNOWN/TRUNCATED・出典を保持し、重要対象がnearest-eightから省略されてもprediction reviewを残す必要がある。token削減や単発CHEAP/L2勝敗を必須ゲートにしない。判断価値・重要対象の省略率は未評価であり、WBは学習や結晶化を所有しない。

元Worldは実Action 2、S16 OUTCOME 2、実Gemma 1、有効L2採用0、再試行0。元cleanup auditではport 25565/16669再bind、World namespace空、model子プロセスexit=0、Node/Java exit=0。これは保存されたhost cleanup証拠であり、STOP ACKは引き続きUNATTESTED、backend_stop_ack=false、gpu_release_verified=false。新しいWorldを起動していないため今回のJava/Node/Gemma子PID・World cleanupは該当なし。

残件は元HTTP/envelope失敗の特定、有効な実Gemma L2採用のDEV観測、将来のowner側content-free stage診断の要否、live L0/L1 consumerおよび判断価値の評価。追加実Worldは未実施。**QUALIFICATION_NO_GO / SCIENCE_NOT_RUN** を維持する。

## 2026-11-02 — optional S60 structured L2 / Thinking OFF request (DEV, no physical inference)

RelayLM's existing qualified llama.cpp build10874 request realization carries **Thinking OFF** as `reasoning_effort="none"` and uses `response_format.type="json_schema"` for native structured extraction. The older `chat_template_kwargs.enable_thinking=false` fixture is **not** the current RelayLM citable wire. Neither qualified request field was present in WB's earlier real Gemini/Gemma S60 model call; that absence is a **possible** cause of empty assistant content / provider rejection, but the earlier HTTP body and headers were not retained, so the original `UNCONFIRMED` is unchanged.

This change adds a **default-OFF, DEV-only** `--wb-structured-l2` option layered on existing `--mode DEV --dev-scenario native-selfworld --live-think --self-world-live --wb-cognition-slice` arguments. It is not enabled for existing non-WB S60 clients. The sole existing `LoopbackDisplacementAdapter` accepts exactly two additional keys **only when its explicit config `structured_json_off=True` is supplied**: `reasoning_effort="none"` and a pinned strict JSON Schema named `wb_l2_uncertainty` with a single string key `uncertainty`; other keys, response formats, or template controls are rejected before network POST. The caller keeps the existing bounded request and one S60 provider attempt. No new provider/World observer/Action executor is created.

In this opt-in mode, the existing WB L2 observer parses the returned `message.content` as JSON and admits a bounded, nonempty `uncertainty` string (up to 300 code points) **only after the unchanged S60-A/B1 HTTP validation, completion lease and source-freshness gates**. Invalid JSON, extra fields (including a hypothetical `command`), empty strings, or semantic errors result in `STRUCTURED_CONTENT_UNCONFIRMED`, not a physical Action or Memory update. Normal and earlier WB inputs retain their historical five-key request and one-sentence free text result. This DEV switch is an explicit operator opt-in; it does not infer binary, model, or chat-template attestation from a model name, and **does not establish a real llama.cpp/Gemma success**.

Offline tests must verify the two opt-in fields and fixed schema, S60 default-off rejection of extra request fields, negative envelope/JSON controls, source expiration, CLI no-World refusal, single-model-call and zero-action properties. The original saved real World and its provider-before-displacement `UNCONFIRMED` classification are unchanged. A further **LocalCodex-owned** one-shot, model-only test on an independently attested exact pinned model/server condition is needed before enabling this in a disposable real World. Use an existing single-slot S60 backend and preserve raw failure evidence. Any execution must report actual model calls, accepted current L2 text separately from backend tokens, and whether the pinned schema is compatible with that exact runtime.

**State: DEV_ONLY / REQUEST_WIRE_IMPLEMENTED / REAL_GEMMA_NOT_RUN / ORIGINAL_PROVIDER_FAILURE_UNCHANGED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
