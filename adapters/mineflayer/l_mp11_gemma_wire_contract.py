"""Gemma-4 + llama.cpp contract for opt-in source-bound L2 evidence-ID OPEN.

Existing RelaySelf prior RSEE physical successes used native strict JSON Schema
AND reasoning off. A JSON-only grammar does not prove that thinking is disabled.
This module constrains the transport; it does not authenticate local GGUF bytes.
"""
from __future__ import annotations

import json

from adapters.mineflayer.l_mp11_b1_forecast_contract import schema_v2_additions
from adapters.mineflayer.l_mp11_g3_archived_l2_prefix import (
    MODEL_FAMILIES,
    NEXT_TESTS,
    RECONSIDERATIONS,
)
from adapters.mineflayer.l_mp11_typed_feedback import RELATIONS

GEMMA_SCHEMA_NAME = "relay_l2_typed_evidence_v1"
GEMMA_MAX_COMPLETION = 512
REQUIRED = (
    "referenced_prior_ordinals",
    "reconsideration",
    "model_family",
    "next_test",
    "explanation",
    "falsification_test",
    "predicted_wait_total_m",
    "capability_assessment",
    "prior_hypothesis_relation",
    "evidence_ids",
)


class GemmaWireRejected(ValueError):
    """Missing capability/shape or reasoning-contaminated llama.cpp response."""


def _typed_ids_from_open_request(body: dict) -> tuple[tuple[str, ...], int]:
    """Only inspect canonical model-facing *request*, never untrusted output."""
    try:
        messages = body["messages"]
        raw_user = messages[1]["content"]
        payload = json.loads(raw_user)
        source = [c for c in payload["context"]
                  if c.get("key") == "typed_Paper_evidence_ID_catalog"]
        if len(source) != 1:
            raise GemmaWireRejected("one typed evidence source required")
        attestation = source[0]["provenance"]
        if attestation["source"] != "l.mp11.live.paper.numeric.role-table.readonly":
            raise GemmaWireRejected("not an original previous Paper view")
        catalog = json.loads(json.dumps(source[0]["value"]))
        records = catalog["indexed"]
        ids = tuple(record["evidence_id"] for record in records)
        prior = [c for c in payload["context"] if c.get("key") == "paper_prior_experience"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise GemmaWireRejected("no canonical typed prior evidence catalog") from exc
    if (
        not isinstance(messages, list) or len(messages) != 2
        or type(records) is not list or not 16 <= len(ids) <= 34
        or any(type(x) is not str or len(x) > 18 for x in ids)
        or len(set(ids)) != len(ids)
        or len(prior) > 1
    ):
        raise GemmaWireRejected("bounded evidence catalog violated")
    # Validate the visible original trial count without deriving a model claim.
    n = len({record.get("trial_ordinal") for record in records
             if record.get("metric_role") == "WAIT8_TOTAL_M"})
    if n not in (1, 2):
        raise GemmaWireRejected("only one or two completed original trials")
    return ids, n


def strict_gemma_evidence_schema(
    request_body: dict, *, b1_contract_v2: bool = False,
) -> dict:
    """Native llama.cpp json_schema with a finite enumeration of original IDs."""
    if type(request_body) is not dict:
        raise GemmaWireRejected("canonical llama.cpp OPEN request object required")
    if type(b1_contract_v2) is not bool:
        raise GemmaWireRejected("B1 contract flag not a boolean")
    ids, count = _typed_ids_from_open_request(request_body)
    def options(values):
        return {"type": "string", "enum": sorted(values)}
    properties = {
        "referenced_prior_ordinals": {
            "type": "array", "items": {"type": "integer", "enum": list(range(1, count+1))},
            "minItems": 1, "maxItems": count, "uniqueItems": True,
        },
        "reconsideration": options(RECONSIDERATIONS),
        "model_family": options(MODEL_FAMILIES),
        "next_test": options(NEXT_TESTS),
        "explanation": {"type": "string", "minLength": 16, "maxLength": 120},
        "falsification_test": {"type": "string", "minLength": 16, "maxLength": 120},
        "predicted_wait_total_m": {
            "anyOf": [
                {"type": "number", "minimum": 0, "maximum": 3},
                {"type": "null"},
            ],
        },
        "capability_assessment": options(("UNKNOWN", "CONDITIONAL_HYPOTHESIS")),
        "prior_hypothesis_relation": options(
            ("FIRST_HYPOTHESIS",) if count == 1
            else tuple(x for x in RELATIONS if x != "FIRST_HYPOTHESIS")
        ),
        "evidence_ids": {
            "type": "array", "items": options(ids),
            "minItems": 1, "maxItems": 1 if count == 1 else 2,
            "uniqueItems": True,
        },
    }
    if b1_contract_v2:
        properties.update(schema_v2_additions())
    return {
        "type": "json_schema",
        "json_schema": {
            "name": (
                "relay_l2_b1_explicit_forecast_v2"
                if b1_contract_v2 else GEMMA_SCHEMA_NAME
            ),
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": list(REQUIRED),
                "additionalProperties": False,
            },
        },
    }


def enforce_gemma_thinking_off(response: object) -> None:
    """A successful HTTP status doesn't prove thinking OFF. Fail closed.

    Gemma-4 + grammar has been observed to leak a thought channel even with
    enable_thinking=false. Canonical owner must never accept that as a qualified
    L2 hypothesis; the raw response is separately journaled first.
    """
    if type(response) is not dict:
        raise GemmaWireRejected("llama.cpp response must be object")
    try:
        choices = response["choices"]
        if type(choices) is not list or len(choices) != 1:
            raise GemmaWireRejected("one nonstreaming model choice required")
        message = choices[0]["message"]
        reasoning = message.get("reasoning_content")
        if reasoning not in (None, ""):
            raise GemmaWireRejected("Gemma reasoning channel present despite thinking OFF")
        if message.get("content") is None or type(message["content"]) is not str:
            raise GemmaWireRejected("missing real answer content")
        if any(marker in message["content"] for marker in (
            "<think>", "</think>", "<thought>", "</thought>",
            "<|channel>", "<channel|>",
        )):
            raise GemmaWireRejected("reasoning markers in constrained output")
        details = response.get("usage", {}).get("completion_tokens_details") or {}
        if type(details) is not dict or details.get("reasoning_tokens", 0) not in (0, None):
            raise GemmaWireRejected("reasoning tokens observed despite thinking OFF")
    except (KeyError, TypeError, AttributeError) as exc:
        raise GemmaWireRejected("malformed llama.cpp reasoning attestation") from exc


def pin_gemma_wire(
    body: dict, *, evidence_ids: bool, b1_contract_v2: bool = False,
) -> dict:
    """Mutate canonical L2 request in place, before raw journal and HTTP."""
    if (
        type(evidence_ids) is not bool or type(body) is not dict
        or type(b1_contract_v2) is not bool
        or (b1_contract_v2 and not evidence_ids)
    ):
        raise GemmaWireRejected("explicit real Gemma protocol gate required")
    body.update(
        max_tokens=GEMMA_MAX_COMPLETION,
        temperature=0,
        seed=1,
        stream=False,
        cache_prompt=False,
        reasoning_effort="none",
        chat_template_kwargs={"enable_thinking": False},
    )
    if evidence_ids:
        body["response_format"] = strict_gemma_evidence_schema(
            body, b1_contract_v2=b1_contract_v2,
        )
    else:
        body["response_format"] = {"type": "json_object"}
    return body
