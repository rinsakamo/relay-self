# RSEE — /props 1 MiB bounded live binding repair

Authority: #537, stopped Golden #587 (exact `784df44a668b7c5f0b0367588ce59aa796b2a817`).
This child is **offline code and CI only**, never a permission to replay physical
Golden or reinstall any shared runtime. Preserve parent #587 and the first two
sealed attempts; the second trial stopped `RSEE_BINDING_PROPS_BODY_TOO_LARGE`
after GET /v1/models HTTP 200 (603 bytes) and GET /props HTTP 200.
Its saved `rsee_http_props.json` is an intentionally truncated 16,385-byte
prefix, SHA256
`fefcd936ee2325a05820315b3346927c9e9b5f251a254d9b12b4fe74e0822f03`.
The total response length, valid full JSON shape, and final model/slot field
values are **unknown**; `/slots` was not requested. Final operator 49-file index
SHA256 `220fad411fef9da1acf5824c237fdbbe53237baf906cc5d01702fd5be3b58843`.
Do not rewrite either attempt.

## New bounded policy

The source of the failure was our self-owned HTTP binding guard, **not**
evidence of a broken llama.cpp. This child uses endpoint-specific limits:

| Read-only endpoint | Maximum accepted bytes | Upper-bound probe |
| --- | ---: | ---: |
| `GET /v1/models` | 16,384 (16 KiB) | 16,385 |
| `GET /props` | 1,048,576 (1 MiB) | 1,048,577 |
| `GET /slots` | 16,384 (16 KiB) | 16,385 |

Each GET is loopback only, no proxy, a **single** `read(limit+1)`; excess
causes `RSEE_BINDING_<ENDPOINT>_BODY_TOO_LARGE`, original captured prefix
of up to `limit+1` bytes and `response_truncated=true`. It does **not**
become a pass or license unbounded reading. A body of exactly the limit is
accepted for JSON parsing only if valid; duplicate JSON keys, Unicode errors,
malformed/deeply nested JSON, missing identity, incorrect `n_ctx`, wrong
`model_path`, bad build info or `/slots` cardinality all remain BLOCKED.
`GET /v1/models` must contain the **unique expected** request alias.
`/props.model_alias` is optional but must match if present.

A bounded acceptance only qualifies **HTTP-reported config**. It does not
establish actual GPU inference, request-level Thinking OFF, any structured
output, shutdown ACK, native Minecraft Action or Memory/Learning success.

## Optional offline-only inspection of previously captured prefix

This is for **LocalCodex on the physical host** to perform as a separate,
read-only inspection. GitHub cannot read `/home/rinsa` from a remote connector.
No model/World process, socket, file modification, new Golden grant or
retry is needed. The command checks the captured bytes' exact digest and
lists only likely key-token offsets in the **partial prefix**, not values.
A key-token hit does not prove it is a top-level JSON field.

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, json
p = Path("/home/rinsa/.local/share/relay-self/rsee-1.0-20261011/golden-second-20261011-authorized-once/rsee_http_props.json")
expected = "fefcd936ee2325a05820315b3346927c9e9b5f251a254d9b12b4fe74e0822f03"
assert p.is_file() and not p.is_symlink()
raw = p.read_bytes()
assert len(raw) == 16385
assert hashlib.sha256(raw).hexdigest() == expected
tokens = ("model_path", "model_alias", "default_generation_settings", "n_ctx", "total_slots", "build_info")
print(json.dumps({
    "classification": "PARTIAL_PREFIX_KEY_TOKEN_HINTS_ONLY",
    "sha256": expected,
    "bytes_captured": len(raw),
    "total_response_bytes": "UNKNOWN",
    "body_truncated": True,
    "first_non_whitespace_byte": raw.lstrip()[:1].hex(),
    "key_token_offsets": {name: raw.find(('"' + name + '"').encode()) for name in tokens},
}, indent=2, sort_keys=True))
PY
```

A negative offset means **only** that the token was not present in these
captured 16,385 bytes; it does not imply omission from the complete payload.
Do not treat this command as evidence of full response correctness.
If read-only inspection fails to match the digest, stop: never modify,
regenerate, recover or substitute old evidence.

## Offline qualification and future run boundary

Deterministic tests simulate valid JSON /props above 16 KiB and **exactly**
1 MiB; reject >1 MiB (only the 1 MiB+1 prefix captured), over-limit
/models or /slots, invalid/duplicate JSON, source mismatches and stale evidence.
CI is source-only with fake HTTP responses; no Java/GPU/LLM POST.

There is **no** physical Golden authorization in this child.
A new opt-in one-shot grant is required after exact-head CI PASS, and the
Minecraft server EULA assent must be independently established. Preserve
the original first terminal even if later attempts succeed.
