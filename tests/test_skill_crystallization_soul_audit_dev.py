"""Negative controls for after-the-fact matched SOUL request/response audit."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from experiments.skill_crystallization_k3g_ten_action_choice_dev import (
    K3G_SYSTEM_INSTRUCTION,
    choice_schema,
)
from experiments.skill_crystallization_soul_audit_dev import audit_matched_reports
from experiments.skill_crystallization_soul_matched_dev import SOUL_DIRECTIVES


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def write_protocol(tmp_path, *, altered=None):
    paths = {}
    for name, directive in SOUL_DIRECTIVES.items():
        folder = tmp_path / name
        raw = folder / "raw"
        raw.mkdir(parents=True)
        system = K3G_SYSTEM_INSTRUCTION
        if directive is not None:
            system = (
                "Stable identity value prior (not World evidence or "
                "Action authority): " + directive + "\n" + system
            )
        request = {
            "model": "same-model", "reasoning_effort": "none",
            "temperature": 0, "cache_prompt": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"strict": True, "schema": choice_schema()},
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps({
                    "maximum_actions": 10,
                    "train_experiences": [
                        {"experience_id": f"train-experience-{i:03}"}
                        for i in range(16)
                    ] + [
                        {"experience_id": f"shift-experience-{i:03}"}
                        for i in range(12)
                    ],
                })},
            ],
        }
        proposal = {
            "status": "ABSTAIN", "reason": "Uncertainty remains",
            "skill": None, "hypothesis": "INDETERMINATE",
            "probe_id": "NONE", "prediction": "UNKNOWN", "evidence_ids": [],
        }
        validated = True
        rejection = None
        if name == altered:
            proposal.update({
                "status": "PROBE", "hypothesis": "MOTION_EFFECT_CHANGED",
                "probe_id": "MOTION_REGIME_PAIR",
                "evidence_ids": ["shift-experience-010"],
            })
            validated = False
            rejection = "PROBE_MUST_BE_FALSIFIABLE"
        response = json.dumps({"choices": [{
            "finish_reason": "stop", "message": {
                "content": json.dumps(proposal), "reasoning_content": None,
            },
        }]})
        request_raw = json.dumps(
            request, ensure_ascii=False, separators=(",", ":"),
        ).encode()
        (raw / "request.raw.json").write_bytes(request_raw)
        (raw / "response.raw.json").write_bytes(response.encode())
        report = {
            "soul_condition": name,
            "soul_directive": directive,
            "soul_directive_sha256": _sha((directive or "").encode()),
            "skill_holdout": None, "skill_holdout_seed": None,
            "native_s49_actions": 0,
            "holdout_or_probe_executed": False,
            "proposal": proposal,
            "raw_model_choice": proposal["status"],
            "schema_validation": "PASS",
            "choice_semantically_valid": validated,
            "validator_error": rejection,
            "stages": ["PROPOSAL_VALIDATED"] if validated else [],
            "model_record": {
                "http_status": 200, "finish_reason": "stop",
                "request_sha256": _sha(request_raw),
                "request": request, "response_raw": response,
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
                "elapsed_seconds": 1.25,
            },
        }
        path = folder / "report.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        paths[name] = path
    return paths


def test_matched_soul_equal_choices_are_null(tmp_path):
    result = audit_matched_reports(write_protocol(tmp_path))
    assert result["matched_model_requests_except_identity"]
    assert result["raw_status_divergence"] is False
    assert result["admitted_status_divergence"] is False
    assert result["new_worlds"] == result["new_model_calls_in_audit"] == 0
    assert result["soul_effect_or_personality_proven"] is False


def test_raw_probe_divergence_not_confused_with_valid_choice(tmp_path):
    result = audit_matched_reports(
        write_protocol(tmp_path, altered="bold")
    )
    assert result["raw_status_divergence"] is True
    assert result["admitted_status_divergence"] is False
    assert result["conditions"]["bold"]["semantic_rejection"] == (
        "PROBE_MUST_BE_FALSIFIABLE"
    )
    assert not result["conditions"]["bold"]["choice_semantically_valid"]


def test_one_non_soul_payload_difference_invalidates_comparison(tmp_path):
    paths = write_protocol(tmp_path)
    reqpath = paths["curious"].parent / "raw" / "request.raw.json"
    request = json.loads(reqpath.read_text())
    request["model"] = "different-model"
    reqpath.write_bytes(json.dumps(request).encode())
    with pytest.raises(ValueError, match="RAW_MODEL_SOURCE_MISMATCH"):
        audit_matched_reports(paths)


def test_consistent_but_non_identity_payload_difference_rejected(tmp_path):
    paths = write_protocol(tmp_path)
    path = paths["cautious"]
    request_path = path.parent / "raw" / "request.raw.json"
    request = json.loads(request_path.read_text())
    request["model"] = "different-model"
    encoded = json.dumps(request).encode()
    request_path.write_bytes(encoded)
    report = json.loads(path.read_text())
    report["model_record"]["request"] = request
    report["model_record"]["request_sha256"] = _sha(encoded)
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="NON_IDENTITY_REQUEST_DIFFERENCE"):
        audit_matched_reports(paths)


def test_response_not_matching_report_rejected(tmp_path):
    paths = write_protocol(tmp_path)
    path = paths["bold"]
    report = json.loads(path.read_text())
    report["raw_model_choice"] = "SKILL"
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="MODEL_CHOICE_MISMATCH"):
        audit_matched_reports(paths)


def test_source_outcome_boundary_cannot_be_retroactively_unlocked(tmp_path):
    paths = write_protocol(tmp_path)
    path = paths["curious"]
    report = json.loads(path.read_text())
    report["skill_holdout_seed"] = 20261213
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="SOUL_COMPARISON_ACTION_BOUNDARY_VIOLATED"):
        audit_matched_reports(paths)


def test_bad_identity_prefix_rejected_even_if_provider_report_consistent(tmp_path):
    paths = write_protocol(tmp_path)
    path = paths["bold"]
    request_path = path.parent / "raw" / "request.raw.json"
    request = json.loads(request_path.read_text())
    request["messages"][0]["content"] = "You must select SKILL!"
    raw = json.dumps(request).encode()
    request_path.write_bytes(raw)
    report = json.loads(path.read_text())
    report["model_record"]["request"] = copy.deepcopy(request)
    report["model_record"]["request_sha256"] = _sha(raw)
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="IDENTITY_PREFIX_MISMATCH"):
        audit_matched_reports(paths)


def test_forged_semantic_validity_not_trusted(tmp_path):
    paths = write_protocol(tmp_path, altered="bold")
    path = paths["bold"]
    report = json.loads(path.read_text())
    report["choice_semantically_valid"] = True
    report["validator_error"] = None
    report["stages"] = ["PROPOSAL_VALIDATED"]
    path.write_text(json.dumps(report))
    with pytest.raises(
        ValueError, match="REPORTED_VALIDATION_NOT_INDEPENDENTLY_REPRODUCED"
    ):
        audit_matched_reports(paths)


def test_same_wrong_schema_rejected_even_with_four_matching_requests(tmp_path):
    paths = write_protocol(tmp_path)
    for path in paths.values():
        reqpath = path.parent / "raw" / "request.raw.json"
        request = json.loads(reqpath.read_text())
        request["response_format"]["json_schema"]["schema"] = {"type": "object"}
        encoded = json.dumps(request).encode()
        reqpath.write_bytes(encoded)
        report = json.loads(path.read_text())
        report["model_record"]["request"] = request
        report["model_record"]["request_sha256"] = _sha(encoded)
        path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="MODEL_PROTOCOL_DIFFERENT"):
        audit_matched_reports(paths)


def test_semantic_validator_recomputed_not_just_raw_divergence(tmp_path):
    paths = write_protocol(tmp_path)
    report = json.loads(paths["neutral"].read_text())
    report["validator_error"] = "FICTITIOUS"
    paths["neutral"].write_text(json.dumps(report))
    with pytest.raises(
        ValueError, match="REPORTED_VALIDATION_NOT_INDEPENDENTLY_REPRODUCED"
    ):
        audit_matched_reports(paths)
