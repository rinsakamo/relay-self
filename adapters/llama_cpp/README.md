# RelaySelf llama.cpp RelayEngine adapter

This directory contains the first actual-model realization of the RelaySelf
RelayEngine provider seam.

It is deliberately target-local and small. It is not a provider registry and
does not make llama.cpp a semantic owner.

## Runtime boundary

The core RelayEngine owns two transient request families under the same provider:

    BOUNDED
      -> RESOLVED
      or
      -> explicit THINK
           -> RESOLVED | UNRESOLVED

    OPEN
      -> one transient expression

By default this adapter realizes each provider attempt through a llama.cpp
OpenAI-compatible chat-completions request. An explicit optional Jev/System One
endpoint may instead realize BOUNDED through one finite-choice logits readout.
THINK and OPEN remain chat-completions requests.

The generated baseline uses:

- temperature = 0;
- reasoning_effort = none;
- cache_prompt = false;
- native strict response_format = json_schema for BOUNDED / THINK;
- no decision response schema for OPEN expression text;
- max_tokens = 48 for BOUNDED;
- max_tokens = 256 for THINK;
- max_tokens = 256 for OPEN.

The THINK path is therefore an explicit second RelaySelf request with a larger
generation budget and an explicit rationale field. It does not rely on hidden
provider-owned reasoning mode. OPEN is separately explicit and exactly once; it
does not implicitly enter THINK.

### Optional Jev/System One bounded path

When `LlamaCppRelayProvider(systemone_endpoint=...)` is configured, only
`CognitionMode.BOUNDED` uses that endpoint. The adapter sends the same
provenance-bearing transient state plus finite choices to `/v1/systemone`.
RelaySelf adds one reserved finite option representing cognitive insufficiency.
A normal choice becomes `RESOLVED`; that reserved choice becomes
`UNRESOLVED` and may enter the existing explicit THINK escalation.

This path generates no model output tokens. It does not introduce a confidence
threshold, automatic fallback, second model, provider router, or new semantic
owner. A missing/malformed Jev endpoint is an operational/provider-protocol
failure. It is not silently retried through generated BOUNDED cognition.

The generated BOUNDED path remains available as an explicit baseline until
matched physical evidence justifies canonicalizing the Jev path.

## Output contract

BOUNDED requires exactly:

    {"status":"resolved","choice_id":"<id>"}

or:

    {"status":"unresolved","choice_id":null}

THINK requires exactly:

    {"status":"resolved","choice_id":"<id>","rationale":"..."}

or:

    {"status":"unresolved","choice_id":null,"rationale":"..."}

A valid bounded model response may explicitly return cognitive UNRESOLVED, which
allows the core RelayEngine to escalate from BOUNDED to THINK when the caller
permits it.

The bounded/THINK llama.cpp request carries a mode-specific strict JSON schema.
The schema constrains the declared keys and types and limits choice_id to the
request's finite choices. RelaySelf still validates the returned decision
semantics and parses only bare JSON from the OpenAI-compatible message content;
it does not add a Markdown-fence fallback.

OPEN carries request identity, instruction, optional intent/focus, and
provenance-bearing context without any finite choice surface. The adapter
accepts exactly one non-empty stop-finished text expression and attaches
provider provenance plus the same content-free usage/finish facts used for
evaluation. It does not synthesize RESOLVED/UNRESOLVED, a choice_id, or THINK.

Malformed model content, schema-invalid bounded output, empty OPEN output,
non-stop completion, transport failure, invalid HTTP response envelopes, and
unavailable llama.cpp are operational/provider-protocol failures. They are not
relabelled as cognitive uncertainty and do not trigger automatic THINK or retry.

Neither a resolved choice nor an OPEN expression authorizes an Action, mutates
Current Intent or SkillExecution, establishes World truth, becomes durable
cognition, or proves external delivery.

## Live model qualification

The repository includes a model/system-quality qualification transaction. It
requires a running llama.cpp server that exposes:

- /health
- /v1/models
- /props
- /v1/chat/completions
- /v1/systemone when the optional Jev bounded path is being qualified

The transaction requires exactly one served model.

With the local server already running, use the source-checkout launcher:

    bash adapters/llama_cpp/run_relay_engine_qualification.sh \
      --repo-root . \
      --origin http://127.0.0.1:1234

To qualify the explicit Jev bounded path against a Jev-capable llama.cpp
runtime, add:

    --use-systemone

The launcher derives the repository root from its own path, owns the `src/`
Python import path, changes to the repository root for the top-level
`adapters` namespace, and executes the canonical module with bytecode
disabled. No operator-side `PYTHONPATH` setup is required.

The qualification requires a clean RelaySelf checkout and records the exact
Git HEAD/tree in the report.

The qualification:

1. records the exact RelaySelf HEAD/tree and current llama.cpp runtime identity
   available from those endpoints;
2. creates a real Current Intent and active FLEE SkillExecution;
3. constructs one provenance-bearing bounded FLEE destination request;
4. sends it through the canonical decision-epoch coordinator and RelayEngine;
5. accepts the expected `cave` decision only;
6. records whether explicit THINK escalation occurred;
7. verifies the model-backed decision did not create an Action, terminate the
   Skill, or release Current Intent.

The fixed qualification fixture is intentionally simple: low health, night,
a nearby zombie fact, both routes open, cave shelter=true, ridge shelter=false.
The model is asked only to choose between the two finite destinations.

A successful run is model/system-quality evidence for the exact RelaySelf
revision and served llama.cpp/model condition. It is not Minecraft external
qualification, World truth, general model quality, or proof that all bounded
decisions are correct.

## Matched Jev BOUNDED benchmark

Issue #257 owns a separate model/system-quality measurement of generated
`BOUNDED` versus Jev `BOUNDED` on one already-running Jev-capable llama.cpp
server. The benchmark keeps THINK disabled so the direct comparison contains
exactly one bounded provider call per observation.

Use:

    bash adapters/llama_cpp/run_jev_bounded_benchmark.sh \
      --repo-root . \
      --llama-cpp-root /path/to/kishida-llama.cpp \
      --model-artifact /path/to/model.gguf \
      --origin http://127.0.0.1:1234

The benchmark requires clean RelaySelf and llama.cpp source checkouts, binds the
served runtime build to the selected llama.cpp source HEAD, hashes the exact
GGUF, records the single visible NVIDIA GPU/driver, performs explicit warm-up
calls, then alternates arm order across matched measured pairs. It reports raw
per-call provider/wall latency, prompt/output-token observations, protocol
failures, wrong-choice counts, and median/p95/max latency separately by arm.

The benchmark does **not** qualify prompt/KV cache reuse. RelaySelf currently
uses the Jev fork without a RelaySelf-local cache patch; cross-request
`Jev -> THINK` cache reuse is deferred to #259 after the RelayLM 1.0 cache
correctness repair has independently earned a safe runtime fix.

Deterministic CI tests only the request/parser/provider and qualification logic
with mocked HTTP/provider behavior. CI does not contact localhost llama.cpp.
