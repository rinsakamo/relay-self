"""I2e separate-process RAW L2+L1 entity-body/cognition auditor.

This has NO external World source authority by itself. It independently
reconstructs both typed requests and model results from the original raw
entity bodies and verifies exact source-linked Owner cognition deltas.
Even a passing audit is CPU/source-bundle evidence, not REAL_WORLD_DEV_PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

from adapters.llama_cpp.relay_engine import (
    _extract_completion,
    parse_llama_cpp_decision,
    render_llama_cpp_open_request,
    render_llama_cpp_request,
)
from relay_self.cognitive_minimal_dev import (
    Origin,
    PatternKind,
    Predicate,
    accept_learned_pattern,
    parse_l2_pattern_proposal,
)
from relay_self.i_lane_i2d_self_schema_adoption_dev import _fingerprint
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    OpenCognitionRequest,
    RelayEngine,
)
from relay_self.resident_llama_inference_lane_dev import ResidentInferenceTicket


class I2eIndependentAuditHold(RuntimeError):
    """Independent original model/cognition source or scope not verified."""


def _exact(obj, fields):
    if type(obj) is not dict or set(obj) != fields:
        raise I2eIndependentAuditHold("exact typed original model field set missing")
    return obj


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _request_common(raw: dict, *, bounded: bool):
    keys = {"request_id", "instruction", "intent_id", "focus",
            "context", "identity_context"}
    if bounded:
        keys |= {"choices", "soft_wall_time_budget_s", "think_allowed"}
    _exact(raw, keys)
    def context(x):
        return CognitionDatum(
            key=_exact(x, {"key", "value_json", "provenance"})["key"],
            value_json=x["value_json"],
            provenance=Provenance(**_exact(
                x["provenance"], {"source", "reference"},
            )),
        )
    values = {
        "request_id": raw["request_id"],
        "instruction": raw["instruction"],
        "intent_id": raw["intent_id"],
        "focus": raw["focus"],
        "context": tuple(context(x) for x in raw["context"]),
        "identity_context": (
            context(raw["identity_context"])
            if raw["identity_context"] is not None else None
        ),
    }
    if bounded:
        return BoundedChoiceRequest(
            **values,
            choices=tuple(BoundedChoice(**_exact(
                c, {"choice_id", "description"},
            )) for c in raw["choices"]),
            soft_wall_time_budget_s=raw["soft_wall_time_budget_s"],
            think_allowed=raw["think_allowed"],
        )
    return OpenCognitionRequest(**values)


def _ticket(raw: dict) -> ResidentInferenceTicket:
    original = _exact(raw, {
        "self_id", "work_ref", "request_id", "mode", "self_epoch",
        "native_session_id", "world_epoch", "backend_ref",
        "action_issue_authorized",
    })
    return ResidentInferenceTicket(
        **{**original, "mode": CognitionMode(raw["mode"])},
    )


def _original_raw(directory: Path, label: str, ordinal: int,
                  mode: str, expected_body: dict) -> tuple[str, dict]:
    request_path = directory / f"{label}-request-body.bin"
    response_path = directory / f"{label}-response-body.bin"
    receipt_path = directory / f"{label}-http-evidence.json"
    for path in (request_path, response_path, receipt_path):
        if path.is_symlink() or not path.is_file():
            raise I2eIndependentAuditHold("missing or symlinked original HTTP entity bytes")
    request_bytes, response_bytes = request_path.read_bytes(), response_path.read_bytes()
    if not request_bytes or not response_bytes or len(response_bytes) > 1024 * 1024:
        raise I2eIndependentAuditHold("partial or unbounded actual model evidence")
    exact_expected = json.dumps(
        expected_body, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode()
    if request_bytes != exact_expected:
        raise I2eIndependentAuditHold("raw model request differs from typed original request")
    receipt = json.loads(receipt_path.read_bytes())
    _exact(receipt, {
        "schema", "ordinal", "mode", "http_status", "capture_type",
        "request_body_sha256", "response_body_sha256",
        "request_body_bytes", "response_body_bytes",
    })
    if (
        receipt["schema"] != 1 or receipt["ordinal"] != ordinal
        or receipt["mode"] != mode or receipt["http_status"] != 200
        or receipt["capture_type"] != "urllib_http_entity_bodies_not_wire_headers"
        or receipt["request_body_sha256"] != _sha(request_bytes)
        or receipt["response_body_sha256"] != _sha(response_bytes)
        or receipt["request_body_bytes"] != len(request_bytes)
        or receipt["response_body_bytes"] != len(response_bytes)
    ):
        raise I2eIndependentAuditHold("original HTTP raw receipt doesn't match bytes")
    actual_response = json.loads(response_bytes)
    content, facts = _extract_completion(actual_response, request_body=expected_body)
    if facts.finish_reason != "stop":
        raise I2eIndependentAuditHold("actual model must complete with stop")
    return content, {
        "request_sha256": _sha(request_bytes),
        "response_sha256": _sha(response_bytes),
        "prompt_tokens": facts.prompt_tokens,
        "completion_tokens": facts.completion_tokens,
    }


def independently_audit_i2e_model_bundle(directory: Path) -> dict:
    """Read-only; the separate Native/Paper/World admission still must HOLD."""
    if (
        type(directory) is not Path or directory.is_symlink()
        or not directory.is_dir()
    ):
        raise I2eIndependentAuditHold("original evidence directory not available")
    filenames = {
        "open-l2-request-body.bin", "open-l2-response-body.bin",
        "open-l2-http-evidence.json", "bounded-l1-request-body.bin",
        "bounded-l1-response-body.bin", "bounded-l1-http-evidence.json",
        "before-cognition.json", "after-cognition.json",
        "i2e-dual-model-report.json",
    }
    if {p.name for p in directory.iterdir()} != filenames:
        raise I2eIndependentAuditHold("exact one-L2/one-L1 original evidence roster required")
    if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
        raise I2eIndependentAuditHold("untrusted symlink or directory in evidence")
    try:
        report = json.loads((directory / "i2e-dual-model-report.json").read_bytes())
        _exact(report, {
            "schema", "source_category", "self_id", "model_alias",
            "backend_ref", "open_l2_request", "bounded_l1_request",
            "open_l2_ticket", "bounded_l1_ticket", "handoff",
            "l2_pattern", "outcome", "before_cognition_sha256",
            "after_cognition_sha256", "all_physical_actions",
            "world_independent_audit_attested",
        })
        sid = report["self_id"]
        if (report["schema"] != 1 or sid not in ("A", "B")
                or type(report["model_alias"]) is not str
                or not report["model_alias"]
                or type(report["backend_ref"]) is not str
                or not report["backend_ref"]
                or report["source_category"] != "original_bridge_unattested_world"
                or report["all_physical_actions"] != 0
                or report["world_independent_audit_attested"] is not False):
            raise I2eIndependentAuditHold("model evidence cannot claim World qualification")
        handoff = report["handoff"]
        if (handoff["self_id"] != sid
                or handoff["status"] != "NO_QUALIFIED_EXPLORATION_GOAL"
                or handoff["goal_candidates"] != []
                or handoff["need_signal_ref"] is not None
                or handoff["question_candidate_ref"] is not None
                or handoff["action_issue_authorized"] is not False
                or type(handoff["material_sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", handoff["material_sha256"]) is None):
            raise I2eIndependentAuditHold("I2 source was not original unqualified exploration")
        open_request = _request_common(report["open_l2_request"], bounded=False)
        bounded_request = _request_common(report["bounded_l1_request"], bounded=True)
        suffix = handoff["bounded_request"]["request_id"]
        if (re.fullmatch(r"i2-original-" + sid + r"-[0-9a-f]{32}", suffix) is None
                or open_request.request_id != "i2d-l2:" + suffix
                or bounded_request.request_id != "i2d-l1:" + suffix
                or open_request.focus != "LEARN_NONMOTOR_EXPLORATION_PATTERN"
                or bounded_request.focus != "SELF_ACCEPT_LEARNED_EXPLORATION_SCHEMA"
                or bounded_request.think_allowed
                or tuple((c.choice_id, c.description) for c in bounded_request.choices)
                != (("1", "ACCEPT_UNBOUND_EXPLORATION_SCHEMA"), ("2", "DEFER"))
                or open_request.identity_context is None
                or open_request.identity_context != bounded_request.identity_context
                or open_request.intent_id != bounded_request.intent_id
                or len(open_request.context) < 2
                or len(bounded_request.context) != len(open_request.context) + 1
                or bounded_request.context[:-1] != open_request.context):
            raise I2eIndependentAuditHold("L2/L1 original same-Self request linkage absent")
        binding = open_request.context[-1]
        if binding.key != "i2d_source_binding":
            raise I2eIndependentAuditHold("source binding missing from L2 prompt")
        source_binding = json.loads(binding.value_json)
        if source_binding.get("material_sha256") != handoff["material_sha256"]:
            raise I2eIndependentAuditHold("I2 source hash differs between prompts")
        ticket_l2, ticket_l1 = (
            _ticket(report["open_l2_ticket"]),
            _ticket(report["bounded_l1_ticket"]),
        )
        if any(
            (
                ticket.self_id != sid
                or ticket.backend_ref != report["backend_ref"]
                or ticket.action_issue_authorized
                or ticket.work_ref != request.request_id
                or ticket.request_id != request.request_id
                or ticket.native_session_id != handoff["native_session_id"]
                or ticket.self_epoch != handoff["resident_epoch"]
            )
            for ticket, request in (
                (ticket_l2, open_request),
                (ticket_l1, bounded_request),
            )
        ) or (
            ticket_l2.mode is not CognitionMode.OPEN
            or ticket_l1.mode is not CognitionMode.BOUNDED
            or ticket_l2.world_epoch != ticket_l1.world_epoch
            or ticket_l2.self_epoch != ticket_l1.self_epoch
            or ticket_l2.work_ref == ticket_l1.work_ref
        ):
            raise I2eIndependentAuditHold("original A/B shared lane tickets unqualified")
        model = report["model_alias"]
        open_content, open_facts = _original_raw(
            directory, "open-l2", 1, "OPEN",
            render_llama_cpp_open_request(open_request, model=model),
        )
        bounded_content, bounded_facts = _original_raw(
            directory, "bounded-l1", 2, "BOUNDED",
            render_llama_cpp_request(
                bounded_request, mode=CognitionMode.BOUNDED, model=model,
            ),
        )
        original_provenance = Provenance(
            "llama.cpp", f"request:{open_request.request_id}:model:{model}",
        )
        learned = parse_l2_pattern_proposal(
            open_content, model_provenance=original_provenance,
        )
        if (learned.origin is not Origin.LEARNED
                or learned.kind is not PatternKind.GOAL
                or learned.predicate is not Predicate.EXPLORE
                or learned.schema_id != "exploration"
                or learned.version != 1
                or learned.goal_id != "EXPLORE_WORLD"
                or any(x is not None for x in (
                    learned.skill_id, learned.skill_version, learned.target_kind
                ))
                or report["l2_pattern"] != {
                    "pattern_id": learned.pattern_id,
                    "provenance": {
                        "source": learned.provenance.source,
                        "reference": learned.provenance.reference,
                    },
                }):
            raise I2eIndependentAuditHold("L2 raw output is not an unbound Self proposal")
        proposal_context = bounded_request.context[-1]
        if proposal_context.key != "i2d_model_proposal":
            raise I2eIndependentAuditHold("L1 did not consume original L2 expression")
        payload = json.loads(proposal_context.value_json)
        if (
            payload != {
                "pattern": json.loads(open_content),
                "model_provenance": original_provenance.reference,
                "l2_ticket": repr(ticket_l2),
                "l2_request_sha256": _fingerprint(open_request),
            } or proposal_context.provenance != original_provenance
        ):
            raise I2eIndependentAuditHold("actual L1 proposal payload differs from L2 result")
        decision = parse_llama_cpp_decision(
            bounded_content, mode=CognitionMode.BOUNDED,
        )
        resolved = RelayEngine(
            lambda request, *, mode: decision
        )(bounded_request)
        selection = (
            resolved.choice_id if resolved.status is DecisionStatus.RESOLVED
            else None
        )
        expected_outcome = (
            "SELF_ACCEPTED_NONMOTOR_EXPLORATION_SCHEMA" if selection == "1"
            else "DEFER" if selection == "2" else "UNRESOLVED"
        )
        result = report["outcome"]
        if (result["self_id"] != sid
                or result["outcome"] != expected_outcome
                or result["l2_ticket"] != report["open_l2_ticket"]
                or result["l1_ticket"] != report["bounded_l1_ticket"]
                or result["goal_unresolved"] is not True
                or any(result[x] is not False for x in (
                    "question_adopted", "intent_committed",
                    "physical_action_authorized",
                ))):
            raise I2eIndependentAuditHold("model selection differs from reported original Owner result")
        before_path = directory / "before-cognition.json"
        after_path = directory / "after-cognition.json"
        if (report["before_cognition_sha256"] != _sha(before_path.read_bytes())
                or report["after_cognition_sha256"] != _sha(after_path.read_bytes())):
            raise I2eIndependentAuditHold("Owner durable cognition raw changed")
        before = load_persistent_cognition(before_path)
        after = load_persistent_cognition(after_path)
        if (before.identity.self_id != sid or after.identity != before.identity
                or before.pattern_registry is None
                or any(p.schema_id == "exploration"
                       for p in before.pattern_registry.patterns)):
            raise I2eIndependentAuditHold("original Self/Registry before model unqualified")
        if selection == "1":
            expected_registry = accept_learned_pattern(
                before.pattern_registry, learned, accepted_by_self=True,
                expected_revision=before.pattern_registry.revision,
                allowed_skills=frozenset(),
            )
            if (after != replace(before, pattern_registry=expected_registry)
                    or result["pattern_registry_revision"] != expected_registry.revision):
                raise I2eIndependentAuditHold("accepted Schema not same original durable Owner")
        elif (before != after
              or result["pattern_registry_revision"] != before.pattern_registry.revision):
            raise I2eIndependentAuditHold("DEFER/UNRESOLVED changed original cognition")
        return {
            "classification": "I2E_DUAL_RAW_MODEL_AND_OWNER_CPU_BUNDLE_AUDITED",
            "self_id": sid,
            "backend_ref": report["backend_ref"],
            "model_alias": model,
            "l2": open_facts,
            "l1": bounded_facts,
            "model_result": expected_outcome,
            "original_durable_owner_replay_consistent": True,
            "original_native_paper_world_independently_verified": False,
            "real_world_dev_pass": False,
            "qual_go": False,
            "science_run": False,
            "physical_action_count": 0,
        }
    except I2eIndependentAuditHold:
        raise
    except (OSError, KeyError, ValueError, TypeError, IndexError, AttributeError) as exc:
        raise I2eIndependentAuditHold(
            "original raw model/Owner evidence missing or invalid"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = independently_audit_i2e_model_bundle(args.raw_dir)
    except BaseException as exc:
        print(f"I2E_INDEPENDENT_HOLD={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
