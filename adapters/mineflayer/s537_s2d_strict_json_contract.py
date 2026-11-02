"""S #537 S2-D: fixed, opt-in, strictly validated llama.cpp chat JSON profile.

The request profile asks llama.cpp for schema-constrained output and disables
model template thinking at request level. Actual backend support and Gemma
reasoning OFF must still be verified on the owned process at runtime.
No generic model, tool, Action, or code-execution channel is exposed.
"""
from __future__ import annotations

import json
from collections.abc import Mapping

PROFILE = "S537_S2D_READ_ONLY_JSON_V1"
OUTPUT_FIELDS = ("assessment", "uncertainty", "next_observation")
OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "assessment": {"type": "string", "minLength": 1, "maxLength": 240},
        "uncertainty": {"type": "string", "minLength": 1, "maxLength": 240},
        "next_observation": {"type": "string", "minLength": 1, "maxLength": 240},
    },
    "required": list(OUTPUT_FIELDS),
    "additionalProperties": False,
}
RESPONSE_FORMAT = {"type": "json_schema", "schema": OUTPUT_SCHEMA}
REQUEST_EXTRAS = {
    "response_format": RESPONSE_FORMAT,
    "chat_template_kwargs": {"enable_thinking": False},
    "reasoning_effort": "none",
}


def check_request_extras(payload: Mapping[str, object]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("not a chat request")
    if set(payload) != {
        "model", "messages", "temperature", "max_tokens", "stream",
        *REQUEST_EXTRAS,
    }:
        raise ValueError("unexpected strict protocol keys")
    # JSON round-trip avoids non-JSON class comparisons and alternate
    # mapping implementations, rejects NaN/Inf values.
    extras = {key: payload[key] for key in REQUEST_EXTRAS}
    if json.dumps(extras, sort_keys=True, allow_nan=False) != json.dumps(
        REQUEST_EXTRAS, sort_keys=True, allow_nan=False,
    ):
        raise ValueError("invalid exact structured JSON/no-reasoning profile")


def validate_response_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1600:
        raise ValueError("missing bounded JSON output")

    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = item
        return result

    parsed = json.loads(
        value, object_pairs_hook=unique,
        parse_constant=lambda _x: (_ for _ in ()).throw(ValueError()),
    )
    if not isinstance(parsed, dict) or set(parsed) != set(OUTPUT_FIELDS):
        raise ValueError("wrong exact JSON output fields")
    for field in OUTPUT_FIELDS:
        item = parsed[field]
        if (
            not isinstance(item, str) or not 1 <= len(item.strip()) <= 240
            or "<think" in item.lower() or "</think" in item.lower()
        ):
            raise ValueError("empty, unbounded or reasoning-marked output")
    # Stable canonical JSON in existing S60-A string result field.
    return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
