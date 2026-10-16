# L-CF4 — S60-B1 provider-reported usage source candidate

**DEV_ONLY / OFFLINE.** Parent: [L-CF3 PR #629](https://github.com/rinsakamo/relay-self/pull/629) exact HEAD `845435037fbafc3c0793d4641d7eebf39f9fb320`. This branch modifies only L-owned files, tests and a new workflow. It does **not** update S #545, S60-B1 source owner, R, P1, main, Golden or consumed grants.

## Observed implementation gap

Stock S60-B1 validates an HTTP JSON response, ProviderCallFacts usage, finish reason, total token arithmetic and output bound, but its successful Future returns transient **text only**. Existing S logical interruption, host-local client cancel, backend stop acknowledgment and GPU release are distinct. An HTTP 200 response is **not** backend idle or R-qualified original source. L-CF3 therefore could bound a real S60 request but could not obtain original provider-reported usage for independent review.

## Minimal L-owned opt-in

- `MeteredS60Adapter` subclasses the **same existing S60-B1 HTTP adapter**, overrides only payload byte-digest capture and response validation, and preserves the original text-only Future.
- `make_s60_adapter()` selects the opt-in class **only if L cognitive fatigue ON**. OFF returns the exact old S60 adapter and payload contract; no new requirement or fee.
- After stock S60 validates the envelope, the opt-in validates complete nonnegative integer `prompt_tokens / completion_tokens / total_tokens`, exact sum and natural `finish_reason`. Missing/invalid usage turns an otherwise text-only result into `TransportUnconfirmed`, preserving unsettled work.
- `metered_completion` is exposed only after S60 observes a naturally completed successful Future, not during an active transport or after client cancel/error. It binds the already issued S-owned work/session/generation/World and retained revisions, configured model alias, request and original response JSON-body SHA256, requested max output and provider-reported token counts. Its status is explicitly `HTTP_COMPLETION_METER_CANDIDATE`.
- A candidate has `externally_qualified=False`, `backend_stop_ack=False` and `action_authority=False`. SHA identifies bytes *observed through this transport*; it does not independently authenticate a server, binary, physical GPU cost, backend stop, World outcome or science.

## Real effect and important limit

An actual S60-B1 POST sent to an isolated Python fake server is covered by a deterministic regression: S L2 request -> existing S60 HTTP serializer -> bounded JSON output cap -> observed natural response -> metadata candidate; same test confirms evaluator F_c **remains reserved**. An incomplete reply or cancellation cannot generate a valid metered candidate. No real llama.cpp/GPU/Minecraft world was started.

**Do not call `settle_s60_l2()` on an unaudited candidate.** To close the loop, S/R must add independent original source admission: durable request/response capture, exact byte digests, work/session/generation/context and model binding, usage arithmetic and finish reason, monotonic time, stop/release status as applicable, non-replay and externally anchored state checkpoint. A genuine completed request can then enter the already existing `S60ExternalUsage` / `settle_s60_l2` boundary; interrupted work lacking final cumulative usage remains UNDETERMINED and blocks new L2 and idle recovery. Without the source gate, automated L fatigue settlement **is not qualified**.

## Independent ownership and test comparisons

- **S #537:** opt in to the metered candidate on the existing S60 transport at the product owner; preserve L0 independent safety/Action privileges. Provide qualified original request/response and actual S60 admission/terminal receipt; do not treat a local task close as backend stop.
- **R #575:** verify original source bytes/provenance and anchored non-L2 host-monotonic intervals; no conversion of World tick or Body WAIT to guaranteed cognition idle.
- **P1/M:** keep physical Body fatigue WAIT recovery and Energy independent.
- **V #619:** after S/R, prospective OFF/FIXED/LINEAR/NONLINEAR + cheap same-budget comparator and actual World evidence. No scientific effectiveness asserted here.

The tests are `tests/test_cognitive_fatigue_s60_meter.py`, plus L-CF3 and existing S60-B1/L0 regressions. GitHub CI at exact child HEAD provides the only result report; historical parent PASS does not qualify child HEAD.
