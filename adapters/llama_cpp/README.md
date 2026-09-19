# RelaySelf llama.cpp RelayEngine adapter

This directory contains the first actual-model realization of the RelaySelf
bounded RelayEngine provider seam.

It is deliberately target-local and small. It is not a provider registry and
does not make llama.cpp a semantic owner.

## Runtime boundary

The core RelayEngine owns only the cognition allocation rule:

    BOUNDED
      -> RESOLVED
      or
      -> explicit THINK
           -> RESOLVED | UNRESOLVED

This adapter realizes each provider attempt through a llama.cpp
OpenAI-compatible chat-completions request.

The adapter uses:

- temperature = 0;
- reasoning_effort = none;
- cache_prompt = false;
- response_format = json_object;
- max_tokens = 48 for BOUNDED;
- max_tokens = 256 for THINK.

The THINK path is therefore an explicit second RelaySelf request with a larger
generation budget and an explicit rationale field. It does not rely on hidden
provider-owned reasoning mode.

## Output contract

BOUNDED requires exactly:

    {"status":"resolved","choice_id":"<id>"}

or:

    {"status":"unresolved","choice_id":null}

THINK requires exactly:

    {"status":"resolved","choice_id":"<id>","rationale":"..."}

or:

    {"status":"unresolved","choice_id":null,"rationale":"..."}

A valid model response may explicitly return cognitive UNRESOLVED, which allows
the core RelayEngine to escalate from BOUNDED to THINK when the caller permits
it.

The llama.cpp request asks for JSON output. RelaySelf still parses only bare JSON from the OpenAI-compatible message content and does not add a Markdown-fence fallback.

Malformed model content, schema-invalid output, non-stop completion, transport
failure, invalid HTTP response envelopes, and unavailable llama.cpp are
operational/provider-protocol failures. They are not relabelled as cognitive
uncertainty and do not trigger automatic THINK or retry.

A resolved choice still does not authorize an Action, mutate Current Intent or
SkillExecution, establish World truth, or become durable cognition.

## Live model qualification

The repository includes a model/system-quality qualification transaction. It
requires a running llama.cpp server that exposes:

- /health
- /v1/models
- /props
- /v1/chat/completions

The transaction requires exactly one served model.

With the local server already running, use the source-checkout launcher:

    bash adapters/llama_cpp/run_relay_engine_qualification.sh \
      --repo-root . \
      --origin http://127.0.0.1:1234

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

Deterministic CI tests only the request/parser/provider and qualification logic
with mocked HTTP/provider behavior. CI does not contact localhost llama.cpp.
