"""Read-only strict after-the-fact audit of four matched SOUL decision-only calls.

Never invokes Gemma, touches a hidden seed, or executes mock/real Actions.
Requires all four original request/response files and matching reports.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.skill_crystallization_k3g_ten_action_choice_dev import (
    K3G_SYSTEM_INSTRUCTION,
    _independent_schema_check,
    choice_schema,
    validate_choice,
)
from experiments.skill_crystallization_soul_matched_dev import SOUL_DIRECTIVES


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _decision_signature(value: dict[str, Any]) -> dict[str, Any]:
    """Only prospective choice-relevant fields: not style or uncited rhetoric."""
    status = value.get("status")
    if status == "SKILL":
        skill = value.get("skill")
        if not isinstance(skill, dict):
            return {"status": status, "skill": None}
        return {
            "status": status,
            "skill_execution": {
                key: skill.get(key) for key in (
                    "version", "surface", "min_distance", "max_distance",
                    "target_distance", "max_actions", "on_failure",
                )
            },
        }
    if status == "PROBE":
        return {
            "status": status,
            "hypothesis": value.get("hypothesis"),
            "probe_id": value.get("probe_id"),
            "prediction": value.get("prediction"),
        }
    return {"status": status}


def audit_matched_reports(paths: dict[str, Path]) -> dict[str, Any]:
    if set(paths) != set(SOUL_DIRECTIVES):
        raise ValueError("MATCHED_FOUR_CONDITIONS_REQUIRED")
    rows: dict[str, Any] = {}
    baseline_request: dict[str, Any] | None = None
    baseline_system: str | None = None
    for condition in SOUL_DIRECTIVES:
        report_path = paths[condition]
        raw_dir = report_path.parent / "raw"
        saved_request = (raw_dir / "request.raw.json").read_bytes()
        saved_response = (raw_dir / "response.raw.json").read_bytes()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        request = json.loads(saved_request)
        response = json.loads(saved_response)
        provider = report.get("model_record")
        if not isinstance(provider, dict):
            raise ValueError("MISSING_PROVIDER_SOURCE")
        if (provider.get("http_status") != 200
                or provider.get("finish_reason") != "stop"):
            raise ValueError("INCOMPLETE_MODEL_RESPONSE")
        if (provider.get("request_sha256") != _sha(saved_request)
                or provider.get("request") != request
                or provider.get("response_raw") != saved_response.decode("utf-8")):
            raise ValueError("RAW_MODEL_SOURCE_MISMATCH")
        if report.get("soul_condition") != condition:
            raise ValueError("SOUL_CONDITION_REPORT_MISMATCH")
        directive = SOUL_DIRECTIVES[condition]
        if (report.get("soul_directive") != directive
                or report.get("soul_directive_sha256") != _sha(
                    (directive or "").encode("utf-8"))):
            raise ValueError("SOUL_DIRECTIVE_SOURCE_MISMATCH")
        if (report.get("skill_holdout") is not None
                or report.get("skill_holdout_seed") is not None
                or report.get("native_s49_actions") != 0
                or report.get("holdout_or_probe_executed") is not False):
            raise ValueError("SOUL_COMPARISON_ACTION_BOUNDARY_VIOLATED")
        wire_schema = request["response_format"]["json_schema"]
        user_context = json.loads(request["messages"][1]["content"])
        experiences = user_context.get("train_experiences")
        if (request["response_format"]["type"] != "json_schema"
                or wire_schema["strict"] is not True
                or wire_schema["schema"] != choice_schema()
                or request["reasoning_effort"] != "none"
                or request["temperature"] != 0 or request["cache_prompt"] is not False
                or user_context["maximum_actions"] != 10
                or not isinstance(experiences, list)
                or any(not isinstance(row, dict)
                       or type(row.get("experience_id")) is not str
                       for row in experiences)):
            raise ValueError("MODEL_PROTOCOL_DIFFERENT")
        source_ids = [row["experience_id"] for row in experiences]
        if len(source_ids) != len(set(source_ids)) or len(source_ids) != 28:
            raise ValueError("MALFORMED_EXPERIENCE_SCOPE")
        choices = response["choices"]
        if (not choices or choices[0]["finish_reason"] != "stop"
                or choices[0]["message"].get("reasoning_content")):
            raise ValueError("MODEL_RESPONSE_NOT_FINAL")
        response_value = json.loads(choices[0]["message"]["content"])
        if response_value != report.get("proposal"):
            raise ValueError("MODEL_PROPOSAL_NOT_RAW_RESPONSE")
        sys = request["messages"][0]["content"]
        normalized = copy.deepcopy(request)
        if condition == "neutral":
            if sys != K3G_SYSTEM_INSTRUCTION:
                raise ValueError("NEUTRAL_ORIGINAL_SYSTEM_CHANGED")
            baseline_system = sys
            baseline_request = normalized
        else:
            prefix = ("Stable identity value prior (not World evidence or "
                      "Action authority): " + directive + "\n")
            if not sys.startswith(prefix):
                raise ValueError("IDENTITY_PREFIX_MISMATCH")
            normalized["messages"][0]["content"] = sys[len(prefix):]
            if normalized != baseline_request or sys[len(prefix):] != baseline_system:
                raise ValueError("NON_IDENTITY_REQUEST_DIFFERENCE")
        if condition == "neutral":
            normalized["messages"][0]["content"] = sys
        status = report.get("raw_model_choice")
        if status != response_value.get("status"):
            raise ValueError("MODEL_CHOICE_MISMATCH")
        try:
            _independent_schema_check(response_value)
        except ValueError as exc:
            independent_schema = (
                "UNAVAILABLE" if str(exc) == "JSONSCHEMA_UNAVAILABLE"
                else "REJECTED"
            )
            independent_error = str(exc)
            valid_choice = False
        else:
            independent_schema = "PASS"
            try:
                validate_choice(response_value, evidence_ids=set(source_ids))
            except ValueError as exc:
                independent_error = str(exc)
                valid_choice = False
            else:
                independent_error = None
                valid_choice = True
        if (report.get("schema_validation") != independent_schema
                or report.get("choice_semantically_valid") is not valid_choice
                or report.get("validator_error") != independent_error
                or ("PROPOSAL_VALIDATED" in report.get("stages", [])) != valid_choice):
            raise ValueError("REPORTED_VALIDATION_NOT_INDEPENDENTLY_REPRODUCED")
        rows[condition] = {
            "raw_status": status,
            "decision_signature": _decision_signature(response_value),
            "reason": response_value.get("reason"),
            "schema_validation": report.get("schema_validation"),
            "choice_semantically_valid": report.get("choice_semantically_valid"),
            "semantic_rejection": report.get("validator_error"),
            "request_sha256": _sha(saved_request),
            "response_sha256": _sha(saved_response),
            "prompt_tokens": (provider.get("usage") or {}).get("prompt_tokens"),
            "completion_tokens": (provider.get("usage") or {}).get("completion_tokens"),
            "elapsed_seconds": provider.get("elapsed_seconds"),
        }
    results = [r["raw_status"] for r in rows.values()]
    signatures = [
        json.dumps(r["decision_signature"], sort_keys=True) for r in rows.values()
    ]
    admitted = [
        (name, r["raw_status"]) for name, r in rows.items()
        if r["choice_semantically_valid"]
    ]
    admitted_signatures = [
        json.dumps(r["decision_signature"], sort_keys=True) for r in rows.values()
        if r["choice_semantically_valid"]
    ]
    return {
        "classification": "DEV_ONLY_MATCHED_SOUL_RAW_CHOICE_AUDIT",
        "conditions": rows,
        "matched_model_requests_except_identity": True,
        "raw_status_divergence": len(set(results)) > 1,
        "raw_decision_signature_divergence": len(set(signatures)) > 1,
        "reason_text_divergence": len(set(r["reason"] for r in rows.values())) > 1,
        "admitted_choices": admitted,
        "admitted_status_divergence": len(set(s for _, s in admitted)) > 1,
        "admitted_decision_signature_divergence": (
            len(set(admitted_signatures)) > 1
        ),
        "soul_effect_or_personality_proven": False,
        "new_worlds": 0, "new_model_calls_in_audit": 0,
        "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for condition in SOUL_DIRECTIVES:
        p.add_argument(f"--{condition}-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    paths = {
        c: getattr(a, c + "_report") for c in SOUL_DIRECTIVES
    }
    result = audit_matched_reports(paths)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print("SOUL matched audit raw divergence=",
          result["raw_status_divergence"],
          "valid divergence=", result["admitted_status_divergence"])


if __name__ == "__main__":
    main()
