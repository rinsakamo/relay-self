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

## 2026-11-02 — 実Gemma構造化S60 model-only DEV受理

**DEV_ONLY / WORLD_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。** 実行HEADは `c2b85f7d08cb80fadd5bfe073a1bcb544a743dc8`。今回のユーザー指示の1回限定model-only試験として実施し、過去のWorld grantは再利用していない。専用detached worktreeで実装を変更せず、以前のnative callback原本（seq10/21、SHA256 `f73583fbf716aceca4ae6b2d0c38864144289d7aaefae4b7d1d2fb1611cafb83`）を値一致確認のうえread-onlyで復元した。これは**過去sourceのオフラインreplay**であり、現在のMinecraft観測ではない。

実Gemma呼出しは **1 POSTのみ**。同じ1応答を既存 `LiveL2Observer` → `LoopbackDisplacementAdapter` → `BestEffortDisplacement` の本実装で検証した。追加provider、validation変更、retry、World起動はない。外部DEV harnessは既存メソッドへ委譲する記録ラッパーでpayload・読み取ったHTTP bytes・gate結果を保存した。既存Future/lease/deadline/owner tick/stale fenceは不変更。実行中sourceを進めず、12秒の元deadline内で完了した。

| 段階 | 今回の実測 |
| --- | --- |
| Gemma / HTTP | 1件、HTTP 200、Content-Length 777 bytesとbody完全一致 |
| request | 元5-key + `reasoning_effort="none"` + pinned strict `wb_l2_uncertainty` Schema、stream=false、temperature=0、max_tokens=96 |
| completion | alias `wb-gemma4`、finish_reason=stop、prompt=1155 / completion=41 / total=1196 tokens |
| reasoning/content | `reasoning_content`フィールドなし、非空contentにSchema適合JSON。内部reasoning token数=0という証明ではない |
| S60-B1 | `SOCKET_POST_SENT` → `HTTP_COMPLETION_OBSERVED`、envelope受理1件 |
| S60-A | `NEW_REQUEST_STARTED` → `BACKEND_COMPLETION_OBSERVED`、完了1件、失効/cancel 0件 |
| L2 | `ACCEPTED_READ_ONLY_SAME_PRESENT` 1件、offline source seq21で採用。有効な実World中L2採用は0件 |
| 効果 | World 0、Action 0、S16 OUTCOME 0、Memory/Learning更新0 |

真の `message.content` は次のとおり。補修・再生成していない。

```json
{"uncertainty": "The prediction_review for entity-3's label is marked as 'undetermined' because the target or property was not observed."}
```

GGUF SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`、server SHA256 `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536` を起動前に実ファイルから再計算した。実binary versionはbuild10874 / revision `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`と一致。所有PID126560のexe/cmdline、GGUF mmap、`/health`・`/v1/models`・`/props`・`/slots`、応答fingerprint `b10874-e2d2c0d6a` を保存。Thinking OFF指定は記録requestの `reasoning_effort="none"` であり、同revision `server-common.cpp` のnone→`inputs.enable_thinking=false`処理と照合する。モデル名だけから対応を推定していない。

既存server/port占有がない状態を確認し、協調host flockを保持して所有serverを1回だけ起動した。alias `wb-gemma4`、127.0.0.1:16669、ctx8192、parallel1、GPU layers60、`--no-context-shift --slots`。GPU表示は起動前706MiB→load8599MiB→終了後706MiB。所有serverはSIGTERMでexit0、SIGKILLなし、PID消滅とlistener不在を確認。即時bindは失敗原本を保持し、待受け不在とTCP接続の残留を区別する。**backend STOP ACKはUNATTESTED、GPU allocation解放の資格は未成立**。serverログのslot releaseやnvidia-smiの総量復帰をSTOP ACKへ昇格しない。観測replayのsemantic owner行にある `model_binary_identity_verified=false` / HTTP `UNRECORDED` はその実装自身のclaim ceilingであり、外部取得のidentity/raw HTTP証拠と区別して原文を保持する。

今回の3段階にはUNCONFIRMEDは残らない。ただし過去WorldのUNCONFIRMEDは、当時のHTTP原本がないため原因未特定のまま維持する。Thinking OFF/Schemaの追加が過去失敗の原因だったと断定しない。JSONの安全な受理は認知的有用性、学習、World中の採用、物理qualificationを証明しない。次段階は別の有効なDEV World grantの下でWB→L2統合を検討できるが、本作業では自動開始しない。

実行前のexact-head FAST CIは [41364185955](https://github.com/rinsakamo/relay-self/actions/runs/41364185955) の対象7チェックSUCCESS。今回focused S60-A/B1・WB試験196件PASS、Ruff・構文・repository contracts PASS。ローカルFASTと最終報告HEAD CIのterminal結果はPR/owner Issueの実行報告に記録する。証拠はrepo外 `/home/rinsa/evidence/wb-669-structured-gemma-20261102/` にrequest、HTTP raw/envelope、serverログ、source hash、S60前後receipts、process maps/API identity、cleanup、失敗原本、試験ログとmanifestを保存。ローカル保管は独立custody資格を意味しない。

## 2026-11-02 — next live World source-admission DEV guard (World NOT RUN)

The preceding model-only source replay at head `c2b85f7d08cb80fadd5bfe073a1bcb544a743dc8` proved a real Gemma -> S60-B1 -> S60-A structured reply in a saved-native-source offline replay. It **did not** establish adoption during an actual Minecraft World. This follow-up adds a **host-source-order receipt**, not a clock correlation claim or a second sensor.

When WB live structured L2 has been admitted by the original S60 owner, the existing live observer captures one short `wb_structured_acceptance_host_order` record containing the admitted source sequence, latest native callback sequence at acceptance, bounded callback count, whether close had begun, and the prior S60 owner completion receipt. The record persists even when later source advancement makes `text_current=false` / `EXPIRED_WORLD_ADVANCED`. It does not record model output in the timing receipt or claim independent Paper timestamp, server-side native I/O order, STOP ACK, GPU release or World goal success.

The original S49 DEV receipt now **independently cross-joins** the structured sidecar source sequence and WB source reference to original `source_pair_trace` event/probe pairs. It distinguishes:
- `ACCEPTED_CURRENT_HOST_SOURCE_BOUND`: admitted structured JSON while the host observer was active, still current at sidecar close, matched to original S49 source-pair evidence.
- `ACCEPTED_THEN_WORLD_ADVANCED_HOST_SOURCE_BOUND`: same admitted JSON but a later original source invalidated it before close.
- `NOT_ACCEPTED_OR_UNQUALIFIED`: missing, forged, stale, unparseable or unqualified admission. A valid HTTP completion alone never triggers a positive label.

This **host-order DEV** evidence requires independent local original World/server receipts, exact model/server attestation and output data before any real-World scientific claim. No fabricated native observation, S16 closure, new model calls, provider, Action or STOP ACK are introduced.

A separate negative boundary is closed: an exception from the **optional** `LiveL2Observer.observe` callback is caught only at the S49 caller boundary (`Exception`, **not** cancellation), recorded as sanitized `SOURCE_CALLBACK_UNCONFIRMED`, and no future observer output may be accepted after that error. The original S49 L0 callback continues; this does not change or suppress errors from S49 or its own physical owner. Regression tests use only synthetic/native fixtures and a fake HTTP server.

**Next LocalCodex real World DEV acceptance check** (only with currently valid grant and exclusive disposable-world lease): on the exact pushed code HEAD, first confirm FAST, model/binary SHA and local raw evidence options. Use the already provided explicit `--wb-structured-l2 --wb-cognition-slice --live-think --self-world-live` flags in the original `native-selfworld` DEV entry, with a single original S49 issuer and no new native reads. Retain the complete original source pair, original S49 Action/OUTCOME, `live_l2.jsonl`, `dev_wb_structured_l2`, S60 receipts, raw HTTP and server logs; distinguish actual provider completion from live adopted and still-current, live adopted-then-invalidated, and unconfirmed. Fail/cleanup evidence must be preserved. No main merge or scientific/R qualification.

**State for this change:** `DEV_ONLY / LIVE_SOURCE_ADMISSION_GUARD_OFFLINE / REAL_WORLD_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## 実World・実Gemma構造化L2統合DEV（2026-11-02）

**DEV_ONLY / ACCEPTED_THEN_WORLD_ADVANCED_HOST_SOURCE_BOUND / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。** 実行HEAD `1f4305e507494af9e989390d794cc3c60914524c`、独立detached worktree `/home/rinsa/work/wb-669-world-20261102`、起動時clean。今回のユーザー指示と最新 #537 の所有使い捨てWorld DEV方針を確認し、新規Worldを**1回、失敗0、再試行0**実行した。過去のmodel-only replay採用1件と、過去WorldのUNCONFIRMEDを今回の成果へ算入していない。

既存CLI `--mode DEV --dev-scenario native-selfworld --run-disposable --live-think --self-world-live --wb-cognition-slice --wb-structured-l2 --model-alias wb-gemma4 --model-port 16669 --model-timeout 12 --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD` を使用。新output rootは `/home/rinsa/work/wb-669-live-world-output-20261102-01`。元S49の判断・Action・観測順を変更せず、L2完了を待つ停止・sleep・追加probeを入れていない。外部証拠スクリプトは受信済みcallback、既存HTTP readerとowner receiptsの値を複写するだけで、元provider/owner/validationへ委譲する。起動確認APIは推論要求ではなく、実completion POSTは1回だけ。

| 独立した判定 | 今回の観測 |
| --- | --- |
| 実Gemma推論開始 | 1、server task 1 |
| HTTP正常完了 / S60-B1受理 | 1 / 1、HTTP 200・Content-Lengthとbody一致・HTTP_COMPLETION_OBSERVED |
| S60-A完了 / 採用 | 1 / 1、BACKEND_COMPLETION_OBSERVED後の実採用receipt |
| 有効構造化JSON | 1、非空uncertaintyのみ、Thinking OFF・strict Schema |
| 採用時native callback seq | 21、latest_native_seq_at_acceptance=21、observer open、callback count=2 |
| World更新前の採用 / 採用後失効 | 1 / 1、後続callback seq49でEXPIRED_WORLD_ADVANCED |
| World終了時の有効L2 | 0、text_current=false |
| 最終認知callback / 最後の保存S15 native frame | 49 / 57。全native frameと認知callbackのseqを混同しない |
| S49 decision | WAIT(seq9) → MOVE_AWAY(seq21) → MOVE_AWAY(seq49) |
| 実Action / S16 OUTCOME | 2 / 2、元ExecutorのMOVE_BACKWARDのみ、S15 clear_controls applied各1 |
| WB追加Action / 追加native probe | 0 / 0、単一native receiver・S49 issuer維持 |
| Memory / Learning / Habit更新 | 0 / 0 / 0、既存retained入力の読取り・投影は新規学習ではない |
| callback例外 / L2再試行 / L0自動昇格 | 0 / 0 / 0 |

今回の実応答（修復なし）:

```json
{"uncertainty": "The prediction_review for entity-2's label is marked as 'undetermined' because the target_or_property_unobserved reason indicates the property was not observed in the prior source."}
```

message.content非空、reasoning_contentフィールドなし、finish_reason=stop、prompt1152 / completion54（上限96）/ total1206 tokens。生成文の意味的正しさ・有用性は今回評価していない。元source_pair_traceと保存callbackのsession/request/seq/entity値を照合し、同じ受信済みsourceから再投影したpromptは実POSTのuser contentと完全一致した。読戻し時の再投影はモデル呼出しやWorld replayではない。

### L0非ブロック・時系列の資格

Python同一host monotonic記録で、callback9/21/49の処理時間は0.536 / 1.123 / 0.211ms。seq21 callbackはHTTP完了の**2814.799ms前にreturn**している。既存S49はモデルをawaitせず、元3 decision / 2 Actionを完了した。採用の正確なmonotonic timestampは未記録で、B1完了後からcallback49前までのhost-order区間と採用時seq21を証明する。精密な採用遅延や物理反応時間を推定しない。

- Python: monotonic_ns、owner receiptsとcallbackのhost順序。receiptはS60-A tickによる実受理後だけ生成される。
- Node: 同一sessionのdecoded native seq。認知側へ渡すsourceは9/21/49、S15観測には22/29/50/57等もある。採用時に全native frameが停止していたことや、source21が全Worldの最新状態だったことは主張しない。
- llama.cpp: server相対clock、eval計2807.44ms。別clockとのtimestamp差分を取らない。
- Minecraft: **既存launcherはMojang vanilla 1.21.8でありPaperではない**。独立Paper full_time observerは今回使用しておらず、Paper物理chronologyの資格はない。native S15/S16 decoded証拠とhost source失効のDEV観測に限定する。

### 実モデル同一性・cleanup

GGUF SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`、server SHA256 `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536` を実ファイルから照合。build10874、revision `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`。所有PID135299のexe/binary mapping、GGUF mmap、cmdline、API alias wb-gemma4、127.0.0.1:16669、slot1/ctx8192を保存。指定 `-ngl 999 -c 8192 -np 1 --no-context-shift --slots`。別レーンのprocessに触れず、GPU協調flockと空きportを確認してから起動した。

Java21.0.12.1 PID135376 / Node22.22.2 PID135464のexe/hash/cmdline、元Mojang server jar SHA256 `2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7`、server.properties原本を保存。World seedはSERVER_GENERATED_NOT_ATTESTEDのまま。

元S49 Action clear、Java/Node exit0、owned World namespace空、対象3 PID消滅。Gemmaは自己所有PIDのみSIGTERM、exit0、SIGKILLなし。即時16669 bind失敗を原本保存し、listener不在とTIME_WAITを区別した。時間経過後の25565/16669通常再bindはともにPASS。GPU表示706→8599→706MiBだが、**STOP ACK UNATTESTED / GPU解放資格false**。client cancellation・slot release・総量復帰をbackend STOP ACKや物理idleへ昇格しない。grant-consumed.jsonには今回のDEV権限と1回のCLI呼出しを記録し、過去ledgerは不変。

### 実行後の最小補強・検証・証拠

実行後のreadback監査で、receipt側の独立joinに「採用seqと元S49のL2入力refの直接一致」を追加した。以前の存在確認だけでは、同一runに実在する別seqと入力refを混ぜた合成sidecarを拒否できなかった。新負対照はsource seq47と入力ref seq19の混線を拒否する。S60 owner/期限/stale fence・S49の原本・判断・Actionは不変更。今回の正しい実原本はseq21/ref21で新条件も満たす。**修正後のWorld再実行は0**、実行HEADと報告HEADを区別する。

実行前focused299 PASS、最小補強後focused300 PASS。Ruff・構文PASS。contractsはnpm依存内READMEの欠落リンクを拾う初回失敗を保存し、git tracked snapshotでPASSを確認した。FASTおよび報告HEADのCI terminal結果・最終SHAはPR #669 / owner #632/#633の最終報告に記録する。実行HEAD CI [41379339432](https://github.com/rinsakamo/relay-self/actions/runs/41379339432) は対象7/7 SUCCESS、full-regression/物理jobsはSKIPPED。

外部証拠 `/home/rinsa/evidence/wb-669-live-world-20261102/`: request.json、HTTP raw/envelope、received-probes、S60 before/after/result、server log、process maps/identity、events、cleanup audit、失敗原本、試験ログ、SHA256 manifest。元World出力は上記output root、元SHA256SUMS検査PASS。`audit-live.py` はlocal read-only整合確認であり、独立R custodyではない。sidecar自身のmodel_binary_identity_verified=false / HTTP UNRECORDEDは書換えず、外部取得証拠と区別する。

未解決: 独立STOP/GPU解放資格、Paper物理時系列、正確な採用時刻、L2の認知的有用性、live L0/L1 slice利用、情報予算利益、学習・結晶化。今回の実WorldでL2受理1件と後続の正しい失効1件を観測したが、qualification/scienceへ昇格しない。

## 2026-11-02 — WB current-vs-past L2 uncertainty read port (DEV, no physical inference)

The previous **real World** DEV at execution HEAD `1f4305e507494af9e989390d794cc3c60914524c` accepted one actual Gemma structured L2 response for native source seq **21** and invalidated it on the later S49 callback seq **49**. S49 issued two original Actions with two S16 OUTCOME; the L2 observer issued **zero additional Action or native probe**, and no Memory/Learning/Habit was committed. That earlier real-World evidence is not rerun or reclassified by this change. Independent Paper timestamps, exact L2 adoption timestamp, STOP ACK and GPU release remain unavailable.

### A question is not a learned physical hypothesis

The currently admitted JSON schema has exactly one field: `{"uncertainty":"..."}`. This is an **L2-generated question**. It is not a predicted physical value, a verified counterfactual or a learning update. Consequently, this WB step must never call it a confirmed World model or a learned Habit merely because a later native source invalidated the current answer.

The new pure `src/relay_self/wb_l2_read_port.py` exposes an immutable `WBL2UncertaintyRead` projection with three disjoint states:

- `CURRENT_EPOCH_READ_ONLY`: source-bound S60-admitted uncertainty is available for **read-only attention** while native source seq remains unchanged; `current_uncertainty` is populated and `past_review_candidate` is empty.
- `PAST_EPOCH_REVIEW_ONLY`: a later original native callback has invalidated current applicability; **only** `past_review_candidate` contains the old question, tagged with original source ref/seq. This is not an experience store or an automatic transfer to L1/Learning.
- `UNAVAILABLE`: no qualifying S60 acceptance, bad/duplicate JSON, invalid/foreign/stale-source ref, missing source, source callback failure, or unsupported metadata. No current or past content is exposed.

All views have `source_attested=false` (independent S49/physical attestation remains upstream), `origin=L2_GENERATED_UNCERTAINTY_NOT_WORLD_FACT`, and `authority=READ_ONLY_NO_ACTION_MEMORY_LEARNING_HABIT`. Outputs never include an Action field, prediction result, memory write or learning grant.

The WB live observer supports a **pure read** via `read_wb_l2_uncertainty()` only while the observer is open and S60 has actually completed; a subsequent source observation yields `PAST_EPOCH_REVIEW_ONLY`. The `wb_l2_readonly_at_close` sidecar field is a final native-source snapshot for DEV evidence, **not** a persistent live consumer: calls after close return `UNAVAILABLE`.

The original S49 DEV receipt independently projects `dev_wb_l2_uncertainty_read` from the already persisted sidecar text **and S49's own source-pair refs and latest native probe sequence**. A positive read requires previous `dev_wb_structured_l2` acceptance, source reference equality, source-seq alignment, full JSON validation and an unchanged S60 owner. This is a DEV host-order readback only, not a Paper physical chronology or a separate second model.

Offline negative controls cover mismatched original source, untrusted sidecar latest-seq, wrong session, stale past presented as current, duplicate JSON keys, extra Action content, reasoning-only content, empty/truncated JSON, callback failure and owner noncompletion. Normal WB OFF and earlier S60 default behavior are unchanged.

**Scope / current status:** Read-only port implementation and offline regressions, no new World, no new Gemma call, no L1 consumer installed, no learned hypothesis or L0 crystallization. Future **L Lane** integration may take a `PAST_EPOCH_REVIEW_ONLY` question as a source-bound **review candidate** only after independently observing relevant outcomes and verifying applicability; it must not auto-commit this object as Memory, S10 feedback or a Habit. `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## 2026-11-02 — WB L1 ATT shadow / post-expiry source-bound question review

This stage attaches the **previous read-only WB L2 uncertainty port** to the existing bounded `select_attention` machinery as a **shadow**. It does not authorize an actual L1 decision or change the existing S49/ATT/Habit/Learning owners. The only schema permitted from Gemma remains `{"uncertainty":"..."}`, so a generated question cannot be declared a physical-model hypothesis or a fact.

- New pure `src/relay_self/wb_l2_attention_handoff.py`: `project_wb_l1_attention_shadow` turns an already-valid `CURRENT_EPOCH_READ_ONLY` question into one `AttentionCandidate` with `Provenance("wb-s60-generated-uncertainty-not-world-fact", source_ref)`, selected through the existing `select_attention` / explicit `AttentionCriterion`. `ATT_SELECTED_READ_ONLY` is an ATT **shadow selection**, not a governed L1 policy/Action or a Habit. Current-invalid/expired sources return `UNAVAILABLE`.
- `project_wb_past_review_handoff` takes a `PAST_EPOCH_REVIEW_ONLY` question plus a **later same-session source pointer** and returns `PENDING_INDEPENDENT_OUTCOME` only if sequences and native-source refs are monotonic and coherent. This does not compare observations semantically or assert whether the question has been answered. `outcome_verified=false` and `learning_authorized=false` are invariant; only a separately authorized future L-lane evaluation could use this as a review candidate.
- The existing live observer now exposes `read_wb_l1_attention_shadow()` and `read_wb_past_review_handoff()`. The live L1 ATT shadow is evaluated once at S60 L2 admission as an ephemeral **read-only witness**, without changing S49 Action/L0 scheduling. After original native source advancement, only the past-review surface can be populated. `wb_l1_attention_at_admission`, `wb_l1_attention_at_close` and `wb_l2_past_review_at_close` are bounded observational sidecar fields. `close()` invalidates further live reads.
- The original S49 DEV receipt independently joins **original S49 source_pair_trace** with the source-bound uncertainty result. It exposes `dev_wb_l1_attention_shadow` only if the S60-host accepted source and the admission-time ATT witness agree; it exposes `dev_wb_past_review_handoff` only if the later native ref matches the original latest source and the sidecar's final review agrees. Missing, foreign or forged data fail closed to `UNAVAILABLE`.
- Synthetic HTTP and S49-native stubs cover current vs expired shadow, provider failure, invalid/foreign source, forged admission ATT witness, forged later source, no spontaneous L1/Action/Memory/Learning/Habit and unchanged S60 default-OFF. These fixtures do **not** constitute a new real Minecraft World, independent Paper time verification or learned behavior.

**Limit:** The prior real World accepted a structured Gemma L2 response at seq21, then expired it at seq49. This implementation does not rerun that World; no new actual Gemma call, original Action or native probe was made. It does not prove that L1's actual policy selected the shadow, does not save experience to Memory and does not autonomously revise a hypothesis. Future L Lane owns experiment/outcome correlation and learning conditions, not this read-only WB projection.

**Classification:** `DEV_ONLY / L1_ATT_SHADOW_AND_REVIEW_HANDOFF_OFFLINE / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
