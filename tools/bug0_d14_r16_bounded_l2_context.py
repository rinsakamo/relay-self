"""R16: bounded native-token preflight for R12/R13 source-audited L2.

No model inference, no physical Action and no owner Memory/Habit writer.
Model context is a source-exact *subset*, never invented or paraphrased.
Requires same local llama.cpp server's /apply-template and /tokenize.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from tools.bug0_d14_r13_action_catalog import action_catalog

MAX_L2_CTX_TOKENS = 8192
MAX_L2_OUTPUT_TOKENS = 1024
TOKEN_SAFETY_RESERVE = 256
PRESELECT_VERSION = "D14_R16_EXACT_EVENTS_AND_COMPACT_CATALOG_V1"


class R16Rejected(ValueError):
    """No reliable source catalog/token budget; refuse model POST."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def compact_action_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """Expose typed Action reference without verbose owner ABI introspection.

    Every entry still has its source file/method, contract hash, action kind,
    guard, binding, params, preconditions, observed limitations and owner.
    The complete immutable audited Catalog is retained in the projection.
    """
    if catalog != action_catalog():
        raise R16Rejected("R16_FULL_ACTION_CATALOG_IS_NOT_CURRENT")
    entries = []
    for entry in catalog["entries"]:
        entries.append({
            "action": entry["action"],
            "kind": entry["kind"],
            "owner": entry["owner"],
            "guard": entry["guard"],
            "binding": entry["binding"],
            "parameters": entry["parameters"],
            "preconditions": entry["preconditions"],
            "possible_observations": entry["possible_observations"],
            "limits": entry["limits"],
            "source": entry["source"],
            "owner_contract_sha256": _digest(entry["owner_contract"]),
        })
    return {
        "version": catalog["version"],
        "catalog_sha256": catalog["catalog_sha256"],
        "scope": catalog["scope"],
        "no_implicit_action_grant": True,
        "no_skill_execution_or_installation": True,
        "entries": entries,
    }


def _required_event_indices(events: list[dict[str, Any]]) -> set[int]:
    if not events:
        return set()
    return {0, len(events) - 1} | {
        i for i, event in enumerate(events)
        if event["event_kind"] == "LIFE_ACTION"
    }


def _candidate_context(
    full: dict[str, Any], indices: list[int],
) -> dict[str, Any]:
    events = full["experience_events"]
    if not isinstance(events, list) or len(set(indices)) != len(indices):
        raise R16Rejected("R16_INVALID_SOURCE_EVENT_IDS")
    selected = [events[i] for i in indices]
    excluded = [event["experience_id"] for i, event in enumerate(events)
                if i not in set(indices)]
    return {
        **full,
        "action_catalog": compact_action_catalog(full["action_catalog"]),
        "experience_events": selected,
        "budget_selection": {
            "version": PRESELECT_VERSION,
            "full_source_event_count": len(events),
            "model_visible_event_count": len(selected),
            "omitted_source_event_count": len(excluded),
            "omitted_source_event_ids_sha256": _digest(excluded),
            "selected_source_event_ids": [
                event["experience_id"] for event in selected
            ],
            "original_full_catalog_sha256": full[
                "action_catalog"
            ]["catalog_sha256"],
            "source_fidelity": "EXACT_UNMODIFIED_EVENTS_ONLY",
        },
    }


def verify_bounded_context(
    full: dict[str, Any], chosen: dict[str, Any],
) -> None:
    """Verify no source facts, owner bindings or evidence IDs were fabricated."""
    if type(full) is not dict or type(chosen) is not dict:
        raise R16Rejected("R16_CONTEXT_SHAPE_INVALID")
    original = full.get("experience_events")
    selected = chosen.get("experience_events")
    if type(original) is not list or type(selected) is not list:
        raise R16Rejected("R16_MISSING_EXPERIENCE_LIST")
    if len({e["experience_id"] for e in original}) != len(original):
        raise R16Rejected("R16_DUPLICATE_ORIGINAL_EXPERIENCES")
    by_id = {e["experience_id"]: (i, e) for i, e in enumerate(original)}
    try:
        indices = [by_id[e["experience_id"]][0] for e in selected]
        if (indices != sorted(set(indices))
                or any(e != original[i] for i, e in zip(indices, selected))
                or not _required_event_indices(original) <= set(indices)):
            raise R16Rejected("R16_SOURCE_EVENTS_MODIFIED_OR_ANCHORS_MISSING")
        if chosen != _candidate_context(full, indices):
            raise R16Rejected("R16_SOURCE_CONTEXT_OR_CATALOG_CHANGED")
    except (KeyError, IndexError, TypeError) as exc:
        raise R16Rejected("R16_EVIDENCE_IDENTIFIERS_NOT_IN_ORIGINAL") from exc


def select_token_bounded_context(
    full: dict[str, Any], request_for_context: Callable[[dict[str, Any]], dict],
    count_tokens: Callable[[dict[str, Any]], tuple[int, dict[str, Any]]],
    *, context_limit: int = MAX_L2_CTX_TOKENS,
    output_tokens: int = MAX_L2_OUTPUT_TOKENS,
    margin: int = TOKEN_SAFETY_RESERVE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bounded deterministic selection; no inference, no guessed token count.

    Retain the original first & last experiences, and ALL physical
    Action outcomes. Trim earliest intermediate decision events only,
    preserving the exact original source order and content.
    """
    if (
        type(context_limit) is not int or context_limit != MAX_L2_CTX_TOKENS
        or type(output_tokens) is not int
        or not 1 <= output_tokens <= MAX_L2_OUTPUT_TOKENS
        or type(margin) is not int or margin < TOKEN_SAFETY_RESERVE
        or margin >= context_limit - output_tokens
    ):
        raise R16Rejected("R16_INVALID_MODEL_CONTEXT_RESERVE")
    events = full.get("experience_events")
    if type(events) is not list:
        raise R16Rejected("R16_MISSING_ORIGINAL_EVENTS")
    # Initial check validates all source identities as well as catalog.
    full_indices = list(range(len(events)))
    required = _required_event_indices(events)
    remove_order = [i for i in range(len(events)) if i not in required]
    candidates = full_indices
    trial_counts: list[dict[str, Any]] = []
    while True:
        selected = _candidate_context(full, candidates)
        verify_bounded_context(full, selected)
        request = request_for_context(selected)
        if (not isinstance(request, dict)
                or request.get("max_tokens") != output_tokens
                or request.get("reasoning_effort") != "none"
                or request.get("response_format", {}).get("json_schema", {}).get(
                    "strict"
                ) is not True):
            raise R16Rejected("R16_REQUEST_IS_NOT_ORIGINAL_STRICT_JSON")
        actual, evidence = count_tokens(request)
        if (type(actual) is not int or actual < 1
                or actual > 200_000 or not isinstance(evidence, dict)):
            raise R16Rejected("R16_UNTRUSTED_MODEL_TOKEN_COUNT")
        trial_counts.append({
            "selected_events": len(candidates),
            "measured_prompt_tokens": actual,
            "request_sha256": hashlib.sha256(_canonical(request)).hexdigest(),
        })
        if actual + output_tokens + margin <= context_limit:
            receipt = {
                "classification": "DEV_R16_NATIVE_PRETOKENIZED_NO_INFERENCE",
                "selection_version": PRESELECT_VERSION,
                "source_context_sha256": _digest(full),
                "selected_context_sha256": _digest(selected),
                "model_request_sha256": _digest(request),
                "catalog_sha256": full["action_catalog"]["catalog_sha256"],
                "selected_experience_ids": [
                    e["experience_id"] for e in selected["experience_events"]
                ],
                "model_id": request["model"],
                "ctx_limit": context_limit,
                "max_completion_tokens": output_tokens,
                "safety_margin_tokens": margin,
                "input_token_budget": context_limit - output_tokens - margin,
                "measured_prompt_tokens": actual,
                "measurement": evidence,
                "measurement_attempts": trial_counts,
                "new_model_inference_posts": 0,
                "new_world_actions": 0,
                "new_skill_installs": 0,
            }
            return selected, receipt
        if not remove_order:
            raise R16Rejected(
                "R16_MODEL_CONTEXT_EXCEEDED_EVEN_WITH_REQUIRED_SOURCE_ANCHORS"
            )
        # Don't keep synthetic paraphrases or invent source events to fit.
        removed = remove_order.pop(0)
        candidates = [i for i in candidates if i != removed]


def verify_preflight_receipt(
    full: dict[str, Any], chosen: dict[str, Any],
    request: dict[str, Any], receipt: dict[str, Any],
) -> None:
    verify_bounded_context(full, chosen)
    if (type(receipt) is not dict
            or receipt.get("classification")
            != "DEV_R16_NATIVE_PRETOKENIZED_NO_INFERENCE"
            or receipt.get("selection_version") != PRESELECT_VERSION
            or receipt.get("source_context_sha256") != _digest(full)
            or receipt.get("selected_context_sha256") != _digest(chosen)
            or receipt.get("model_request_sha256") != _digest(request)
            or receipt.get("catalog_sha256") != full[
                "action_catalog"
            ]["catalog_sha256"]
            or receipt.get("model_id") != request.get("model")
            or receipt.get("ctx_limit") != MAX_L2_CTX_TOKENS
            or receipt.get("max_completion_tokens") != request.get(
                "max_tokens"
            )
            or receipt.get("safety_margin_tokens") != TOKEN_SAFETY_RESERVE
            or receipt.get("input_token_budget") != (
                MAX_L2_CTX_TOKENS - request.get("max_tokens", 0)
                - TOKEN_SAFETY_RESERVE
            )
            or type(receipt.get("measured_prompt_tokens")) is not int
            or not 0 < receipt["measured_prompt_tokens"] <= receipt[
                "input_token_budget"
            ]
            or receipt.get("selected_experience_ids") != [
                e["experience_id"] for e in chosen["experience_events"]
            ]
            or receipt.get("new_model_inference_posts") != 0
            or receipt.get("new_world_actions") != 0
            or receipt.get("new_skill_installs") != 0
            or receipt.get("measurement", {}).get("method")
            != "LLAMA_CPP_APPLY_TEMPLATE_AND_TOKENIZE"
    ):
        raise R16Rejected("R16_PREFLIGHT_CONTEXT_OR_COUNT_NOT_VERIFIABLE")


def _local_server(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        or parsed.username is not None or parsed.password is not None
        or parsed.port is None
        or parsed.query or parsed.fragment
        or parsed.path != "/v1/chat/completions"
    ):
        raise R16Rejected("R16_ONLY_LOCAL_MODEL_SERVER_ALLOWED")
    if parsed.hostname == "localhost":
        # The caller must control DNS/process mapping; explicit local name.
        pass
    return f"{parsed.scheme}://{parsed.netloc}"


def native_llamacpp_token_counter(
    endpoint: str, *, timeout: float = 25.0,
) -> Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]:
    """Only read-only template/token endpoints on the identical local server.

    These endpoints apply prompt template/tokenizer, *not* inference.
    Context/runtime identity must also be checked by LocalCodex process
    mapping and /props before any separately authorized L2 inference.
    """
    base = _local_server(endpoint)
    if not 1 <= timeout <= 30:
        raise R16Rejected("R16_TOKENIZER_TIMEOUT_OUT_OF_RANGE")

    def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
        raw = _canonical(payload)
        http = Request(
            base + path, data=raw, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(http, timeout=timeout) as response:
                # Prevent unbounded server response from growing local memory.
                body = response.read(2_000_001)
        except (OSError, ValueError) as exc:
            raise R16Rejected("R16_LOCAL_TOKEN_ENDPOINT_UNAVAILABLE") from exc
        if len(body) > 2_000_000:
            raise R16Rejected("R16_TOKEN_RESPONSE_TOO_LARGE")
        try:
            result = json.loads(body)
        except (ValueError, TypeError) as exc:
            raise R16Rejected("R16_TOKEN_RESPONSE_NOT_JSON") from exc
        if not isinstance(result, dict):
            raise R16Rejected("R16_TOKEN_RESPONSE_NOT_OBJECT")
        return result

    def count(request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        template = post_json("/apply-template", {
            "messages": request["messages"],
        })
        prompt = template.get("prompt")
        if type(prompt) is not str or not prompt:
            raise R16Rejected("R16_SERVER_CHAT_TEMPLATE_UNAVAILABLE")
        tokens = post_json("/tokenize", {
            "content": prompt, "add_special": True,
            "parse_special": True, "with_pieces": False,
        }).get("tokens")
        if (
            not isinstance(tokens, list)
            or not tokens
            or len(tokens) > 200_000
            or any(type(token) is not int or token < 0 for token in tokens)
        ):
            raise R16Rejected("R16_SERVER_TOKENIZER_COUNT_NOT_TRUSTED")
        return len(tokens), {
            "method": "LLAMA_CPP_APPLY_TEMPLATE_AND_TOKENIZE",
            "server_endpoint_scope": base,
            "applied_prompt_sha256": hashlib.sha256(
                prompt.encode("utf-8")
            ).hexdigest(),
            "token_ids_sha256": _digest(tokens),
            "tokens": len(tokens),
            "add_special": True,
            "parse_special": True,
            "chat_format_verified_against_real_completion": False,
        }

    return count
