# S #537 — separate post-S42 L2 cost companion (DEV, 2026-11-01)

## Why this is an S-owner task

M [Draft #670](https://github.com/rinsakamo/relay-self/pull/670) already has a bounded, read-only multi-epoch cognition cost collector. But the original S42 `DecisionEpochResult.cognition_requested=True` often means *deterministic* `WorldConditionedChoice`, not a model call. The M/L8 original S/L8/M joined tap **requires** that WorldConditionedChoice. Replacing its original cognition result with an L2 `OpenCognitionResult` would invalidate original L8 admission and would be a forged source rebind.

**S owner policy:** Keep the genuine completed S42 choice as-is. When S has separately and explicitly authorized an L2 OPEN computation and the existing RelayEngine has ALREADY returned, an optional S-owned post-epoch companion may reference it for independent cost analysis. This additional L2 effort is **not** billed as the original S42 cheap choice, is not Action/Goal authority, and is not a replay or substitute for the original S decision.

## Source and execution boundary

`adapters/mineflayer/s_owner_postepoch_l2_companion.py`:

- Default-OFF `SPostEpochL2CompanionLease`; OFF does not examine source or call a provider. ON accepts the **original** completed S42 `DecisionEpochResult` (or executed planned wrapper), and the genuine already-RECORDED original S/L8/M `SLMDevTapResult` referring to the *same original object*.
- Verifies the unchanged, quiescent WorldConditionedChoice selected by S, the M allowlisted original native session/probe/request, and an **independent** `OpenCognitionRequest + OpenCognitionResult` with matching request ID. An externally supplied `OwnerEpochEngineBinding` must refer to the same native source and declare `level=L2`. Usage is extracted from existing `ProviderCallFacts` and measured engine wall-time. Missing tokens remain UNKNOWN; CPU/GPU remain UNKNOWN, never inferred from wall-time.
- The post-S L2 result remains **separate**: `cost_origin=POST_S_SEPARATE_L2_COMPANION_NOT_CHEAP_S_COST`. `bounded_s_l2_companion_cost_row` exports only bounded source IDs, counts, token/time fields and zero/false Action/Memory/Energy authority; never raw LLM prompt/response, original S object or World body.
- The owner's *single lease object* permits at most eight original S epoch/model return pairs; rejects repeat S object, repeat model result and repeated native source on that lease. It does NOT authenticate model execution from arbitrary external Python objects, and no global cross-process replay resistance is claimed. Fresh owner run must qualify source independently.

## Exact test boundary

The new S-specific workflow pins the unchanged original S/B0 product at `087fe095a87594505392262da1d341cf0c65b2b2` and original L8 at `4defb6e8b78f2e050921b521eb2253a14bc260c4`, then runs M's original one-probe product test and new S owner test **in one process**.

In the positive test, original S produces a genuine deterministic WorldConditionedChoice, B0 owner/L8/M genuine typed original source objects are retained, the test **later** executes `RelayEngine.open` once with a **fixture provider**, then S's source-bound companion reads the returned model result. No re-bound/synthetic replacement of the original S/L8/M tap is needed. M's existing `summarize_cognitive_lifecycle` receives the original audit row and *separate* L2 usage, preserving the distinction.

**Limit:** This is an offline owner contract, not a deployed S49 hook or actual Gemma/World. The test's provider is not the physical GPU model. The original Minecraft S49 Action loop and original owner models are unmodified. The method itself invokes no provider or model, and does not install a live L2 policy. No proof of genuine autonomous exploration, learning superiority, retention, reduced costs, or science qualification.

## Next

S #537 must introduce an explicitly budgeted/approved L2 call into an existing live S-owned cognition process, **only after existing native/Action owner admission**, and supply its genuinely completed request/result to this separate companion. Verify actual source, lifecycle, usage/latency and cleanup in a disposable DEV World; then M can account unknown→familiar→shift/recovery across epochs. No extra issuer and no automatic L0/L1 promotion.

Classification: `DEV_ONLY / OFFLINE_ORIGINAL_S_OWNER_AND_FIXTURE_PROVIDER / SOURCE_ATTESTATION_FALSE / S49_LIVE_NOT_INSTALLED / REAL_GEMMA_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## S-owned optional local llama.cpp call (2026-11-01 next increment)

`adapters/mineflayer/s_owner_postepoch_l2_runtime.py` adds the **executable, caller-driven** `SPostEpochL2OpenRuntime`, reusing canonical `LlamaCppRelayProvider` and `RelayEngine.open` rather than creating a new LLM implementation. It does **not** install itself into the original S49 loop or supply a Minecraft session.

- Explicit `enabled=True` on a newly created S-owned runtime (default OFF), and `max_calls=1..3`. The S caller must already own and supply an original completed quiescent S42 decision, its exact already-RECORDED S/L8/M tap, `OwnerEpochEngineBinding(level=L2)`, and `OpenCognitionRequest(focus=POST_S_L2_SHADOW_DEV)`. No request can replace or rewrite original S42. The bound native source is *caller-provided* and structurally verified but is not independently physical source attestation.
- Before any HTTP request, require the canonical llama.cpp provider object pointed to **HTTP loopback only** and exact `/v1/chat/completions` route; reject remote origins, HTTPS, credentials, query or fragment and nonlocal providers. The canonical serializer enforces `OPEN_MAX_TOKENS=256`, `cache_prompt=False`, `reasoning_effort=none`, and provider-side timeout.
- **Burn the S-local source/call lease before initiating HTTP**. At most one POST per owner invocation; even a connection failure/timeout/invalid response is terminal for that source, not silently retried or refunded. A failed call could have reached the backend: status `CALL_UNCERTAIN`, `observed_provider_calls=None`, tokens/latency UNKNOWN; never zero.
- On successfully completed typed OpenCognitionResult, attach it through `SPostEpochL2CompanionLease.observe_after_owner` and M's existing cognitive work receipt. Provider-reported prompt/completion tokens are measured when provided; absent fields remain UNKNOWN. Model response, prompt, credentials, World body, true Energy and owner source objects do **not** leave the bounded audit.
- `tests/test_s_owner_postepoch_l2_runtime.py` uses the genuine canonical HTTP request serializer with an **in-memory fake urllib response** to cover request shape, call reservation, no extra calls, invalid source and off-state before network, missing usage, ambiguous timeout and malformed response. CI **does not contact actual llama.cpp or Gemma**, never launches Minecraft, and does not prove L2 learned or the model weights identity.

**Remaining S owner step:** explicitly wire this callable from S's *real* source-admitted running cognition phase and run with operator-provided local llama.cpp endpoint and model alias under separate DEV evidence and resource budget. The existence of an executable callable is not evidence it was invoked. Avoid attaching real L2 costs to the original cheap S42 result. Model-generated text is transient and never authorized as Action/Memory.
