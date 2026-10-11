# RSEE — Golden Run first-terminal HTTP binding diagnosis (offline fix)

Authority: Self 1.0 #537 and Golden Run original first terminal under #586.
The first physical Golden attempt at exact `cbf8c40d83e149ec438a9af024c5416cff4df0dc`
**consumed** the one-shot permission: one owned Gemma4/llama-server load,
then `RSEE_LIVE_BINDING_UNCONFIRMED`, zero LLM POST/World/Action.
Original operator evidence `SHA256SUMS.final` SHA256
`a37a624820db50900f4c0365ce0066140cd6d8c11e259d84dccf19ec4ee04455`
must never be overwritten. The true failed /props or /slots field cannot be
reconstructed after shutdown; do not claim it was `model_alias`.

## Problem & bounded repair

The former strict gate treated `/props.model_alias` as mandatory; upstream
llama.cpp's `GET /props` documented payload does not guarantee that key.
This version instead uses:

- `GET /v1/models`: exactly one expected `data[].id` = supplied alias.
- `GET /props`: real `model_path` resolves to selected exact SHA-checked GGUF;
  `default_generation_settings.n_ctx=8192`,
  `total_slots=1`, nonempty string `build_info`.
  If optional `model_alias` exists, it must agree; absence is permitted.
- `GET /slots`: array of precisely one object, `n_ctx=8192`.

No other setting is relaxed. Every malformed structure or mismatch is
BLOCKED and the disposable World is never launched. This only qualifies
reported HTTP configuration and does not prove GPU compute, no-thinking,
structured output, physical stop ACK, or successful gameplay.

## Product evidence, available only in any *new*, separately authorized run

One bounded (maximum 16,385 bytes read) non-proxied loopback GET per endpoint,
**no retries, no POST**, in the owned process before World start:

- `rsee_http_models.json` — original /v1/models bytes
- `rsee_http_props.json` — original /props bytes
- `rsee_http_slots.json` — original /slots bytes
- `rsee_live_binding_diagnostic.json` — typed PASS/FAIL per field,
  HTTP status/length/body hash, first transport/format failure if present,
  and an explicit disclaimer that no LLM or Minecraft was attempted by
  the binding probe

All response files use exclusive creation (x/x b), never overwrite. When a
GET fails, only receipts of reached endpoints exist. Over-limit responses
are recorded as a truncated 16,385-byte capture with an explicit
`response_truncated=true` flag and **remain rejected**. The summary is
written in `finally`, **before** stopping the owned backend. If evidence
cannot be persisted, launch cannot progress to World. No asynchronous
capture, no unowned endpoint/proxy requests, no suppressing exceptions.

The owner `owned_llama_receipt.json` points to the diagnostic on a blocked
binding. `RSEE_LIVE_BINDING_UNCONFIRMED` remains the terminal classification;
new detail must be read from the diagnostic, not guessed from status.

## Qualification & execution boundary

This change is code/tests/CI only. Frozen #586, #583 native World and
all Golden first-run files and post-run receipts are preserved.
Do not start llama-server or Minecraft, no LLM POST, no model load and
no new World Action under the consumed permission. Synthetic endpoint
tests include documented absent optional alias, foreign alias/model path,
ctx/slot/build mismatch, duplicate JSON, oversized response,
HTTP non-200 and exclusive evidence creation. CI is not real HTTP proof.
Any *future* physical run needs a new, separately recorded explicit
one-shot user authorization for model+World and Minecraft server EULA.
