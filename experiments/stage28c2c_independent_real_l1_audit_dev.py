"""Stage28c2c: independent second-process RAW HTTP + original A/B audit.

Never POST, load models, start Paper, or infer a choice from a runner flag.
A correct runner report is necessary but insufficient: independently
reconstruct original saved CPU Schema and compare ACTUAL native stdout,
strict llama.cpp request/response entity bytes and retired owner evidence.

This auditor does not prove HTTP packet headers or distributed atomicity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from adapters.llama_cpp.relay_engine import (
    _extract_completion,
    parse_llama_cpp_decision,
    render_llama_cpp_request,
)
from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    parse_mineflayer_line,
)
from experiments.stage24g_model_gate_dev import PINNED_STAGE24G_GGUF_SHA256
from experiments.stage28c2b_independent_rejoin_audit_dev import (
    _sha,
    independently_audit_recovered_real_rejoin,
)
from experiments.stage28c2b_real_recovered_rejoin_dev import (
    inspect_real_recovered_sources,
)
from relay_self.cognitive_minimal_dev import (
    Predicate,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
)
from relay_self.common_io import ScopeRef
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    project_identity_context,
)
from relay_self.stage28_cognitive_recovery_gate_dev import Stage28ForkPaperEpoch
from relay_self.stage28c2c_fresh_recovered_l1_dev import _freeze_hash


class Stage28c2cAuditHold(RuntimeError):
    """Original saved cognition/new native/body/real model source disagrees."""


def _request_from_saved(source: dict) -> BoundedChoiceRequest:
    """Rehydrate typed canonical request, don't trust model prompt summary."""
    if type(source) is not dict:
        raise Stage28c2cAuditHold("original typed L1 request missing")
    try:
        context = tuple(
            CognitionDatum(
                key=row["key"], value_json=row["value_json"],
                provenance=Provenance(**row["provenance"]),
            ) for row in source["context"]
        )
        identity = source["identity_context"]
        return BoundedChoiceRequest(
            request_id=source["request_id"],
            instruction=source["instruction"],
            intent_id=source["intent_id"],
            focus=source["focus"],
            choices=tuple(BoundedChoice(**row) for row in source["choices"]),
            context=context,
            identity_context=CognitionDatum(
                key=identity["key"], value_json=identity["value_json"],
                provenance=Provenance(**identity["provenance"]),
            ),
            soft_wall_time_budget_s=source["soft_wall_time_budget_s"],
            think_allowed=source["think_allowed"],
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise Stage28c2cAuditHold("original L1 request not canonical") from exc


def _native_source(evidence: Path, sid: str, native: str, request_ref: str):
    path = evidence / f"native-Relay{sid}-{native}.jsonl"
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        obj = parse_mineflayer_line(line)
        if (
            isinstance(obj, MineflayerObservation)
            and obj.kind == "probe"
            and obj.session_id == native
            and obj.request_id == request_ref
        ):
            found.append(obj)
    if len(found) != 1:
        raise Stage28c2cAuditHold("original matching raw native probe missing")
    return found[0]


def _validate_model_original_one(
    *, evidence: Path, sid: str, ordinal: int, report: dict,
    original_owner, boot: Stage28ForkPaperEpoch,
    gate: dict,
) -> dict:
    turns = report.get("stage28c2c_original_turns")
    results = report.get("stage28c2c_l1_results")
    if not isinstance(turns, dict) or not isinstance(results, dict):
        raise Stage28c2cAuditHold("original candidate/model evidence absent")
    t, result = turns.get(sid), results.get(sid)
    if type(t) is not dict or type(result) is not dict:
        raise Stage28c2cAuditHold("original A/B model ticket not independently archived")
    n = report["native_login_evidence"][sid]
    native = n["native_session_id"]
    probe = _native_source(evidence, sid, native, n["observation_ref"])
    request = _request_from_saved(t.get("request"))
    scope = t.get("owner_scope")
    if (
        type(scope) is not list or len(scope) != 3
        or type(scope[0]) is not int or scope[0] < 1
        or scope[1] != native or scope[2] != boot.world_epoch
        or t.get("self_id") != sid
        or t.get("native_probe_ref") != n["observation_ref"]
        or t.get("native_probe_seq") != probe.seq
        or t.get("paper_session_id") != boot.paper_session_id
        or t.get("paper_boot_id") != boot.paper_boot_id
        or t.get("pattern_registry_revision")
        != original_owner.pattern_registry.revision
        or t.get("allowed_skills") != []
        or t.get("presets") != []
        or t.get("original_owner_adopted") is not True
        or t.get("old_l1_result_reused") is not False
        or t.get("physical_action_issue_authorized") is not False
        or request.think_allowed
        or not request.request_id.startswith("stage28c2c-" + sid + "-")
        or [ (c.choice_id, c.description) for c in request.choices]
        != [("1", "ESCALATE_L2"), ("2", "DEFER")]
        or request.identity_context != project_identity_context(
            original_owner.retained.identity
        )
        or probe.snapshot.time is None
        or probe.session_id in boot.historical_native_sessions
    ):
        raise Stage28c2cAuditHold("original fresh Self/native/Registry L1 lineage mismatched")
    # Independently compute the actual owner's original CPU Schema Goal
    # summary, not merely trust both raw request and the runner's report.
    snap = probe.snapshot
    percept = WorldPercept(
        scope=ScopeRef(sid, native), source=probe.provenance,
        sequence=probe.seq,
        hunger=int(snap.food) if float(snap.food).is_integer() else None,
        fatigue_high=None, targets=(),
        threat_cue=any(x.name == "zombie" for x in snap.nearby_entities),
        exploration_need=any(
            pattern.predicate is Predicate.EXPLORE
            for pattern in original_owner.pattern_registry.patterns
        ),
        oxygen_reserve=snap.oxygen_level,
    )
    frame = cpu_schema_epoch(
        percept, original_owner.pattern_registry,
        allowed_skills=frozenset(), epoch=scope[0],
    )
    expected_round = assemble_l1_select(
        frame, intent_owner=original_owner.intent,
    )
    if (
        frame.options
        or len(request.context) != len(expected_round.request.context) + 1
        or request.context[0].value_json
        != expected_round.request.context[0].value_json
        or request.context[0].provenance != probe.provenance
    ):
        raise Stage28c2cAuditHold("original saved Registry/Need/Goal not model context")
    fresh = request.context[-1]
    if fresh.key != "fresh_recovered_worldbody" or fresh.provenance != probe.provenance:
        raise Stage28c2cAuditHold("model prompt not sourced to native observation")
    info = json.loads(fresh.value_json)
    if (
        info.get("native_session_id") != native
        or info.get("native_seq") != probe.seq
        or info.get("native_request_id") != probe.request_id
        or info.get("paper_session_id") != boot.paper_session_id
        or info.get("world_uuid") != boot.source_world_id
        or info.get("fork") != boot.fork_branch_id
        or info.get("self_epoch") != scope[0]
        or info.get("source_clock") != "native-world-day-not-paper-process-tick"
        or info.get("health") != snap.health
        or info.get("food") != snap.food
        or info.get("oxygen") != snap.oxygen_level
        or info.get("position") != [
            snap.position.x, snap.position.y, snap.position.z,
        ]
        or info.get("observed_targets") != []
        or info.get("inventory_count") != len(snap.inventory)
        or info.get("nearby_entity_count") != len(snap.nearby_entities)
        or info.get("nearby_entity_coverage_truncated")
        != snap.nearby_entities_coverage.truncated
    ):
        raise Stage28c2cAuditHold("native raw WorldBody changed in model prompt")
    frozen = _freeze_hash(
        sid, tuple(scope), request, boot, probe,
        original_owner.pattern_registry.revision, (),
    )
    if (
        t.get("candidate_set_sha256") != frozen
        or result.get("candidate_set_sha256") != frozen
        or result.get("request_id") != request.request_id
        or result.get("self_id") != sid
        or result.get("native_session_id") != native
        or result.get("self_epoch") != scope[0]
        or result.get("world_epoch") != scope[2]
        or result.get("original_owner_same") is not True
        or result.get("old_l1_result_reused") is not False
        or any(result.get(key) is not False for key in (
            "action_issued", "skill_started",
            "intent_committed", "peer_sent",
        ))
        or result.get("selected_goal_id") is not None
        or result.get("selected_skill_id") is not None
        or result.get("selected_target_ref") is not None
        or result.get("selected_preset_ref") is not None
    ):
        raise Stage28c2cAuditHold("original owner/candidate result not frozen")
    folder = evidence / "stage28c2c-llama-original"
    prefix = f"bounded-{ordinal}"
    req_path = folder / f"{prefix}-request-body.bin"
    resp_path = folder / f"{prefix}-response-body.bin"
    log_path = folder / f"{prefix}-http-evidence.json"
    req_raw, resp_raw = req_path.read_bytes(), resp_path.read_bytes()
    http_receipt = json.loads(log_path.read_text(encoding="utf-8"))
    for path in (req_path, resp_path, log_path):
        if _sha(path) != report.get("stage28c2c_model_raw_sha256", {}).get(path.name):
            raise Stage28c2cAuditHold("raw model evidence bytes changed")
    if (
        http_receipt.get("schema") != 1
        or http_receipt.get("ordinal") != ordinal
        or http_receipt.get("capture_type")
        != "urllib_http_entity_bodies_not_wire_headers"
        or http_receipt.get("http_status") != 200
        or http_receipt.get("request_body_sha256")
        != hashlib.sha256(req_raw).hexdigest()
        or http_receipt.get("response_body_sha256")
        != hashlib.sha256(resp_raw).hexdigest()
        or http_receipt.get("request_body_bytes") != len(req_raw)
        or http_receipt.get("response_body_bytes") != len(resp_raw)
    ):
        raise Stage28c2cAuditHold("real model POST/response manifest invalid")
    expected = render_llama_cpp_request(
        request, mode=CognitionMode.BOUNDED,
        model=gate["model_alias"],
    )
    original_expected_bytes = json.dumps(
        expected, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if req_raw != original_expected_bytes:
        raise Stage28c2cAuditHold("model original request differs from original CPU choice")
    try:
        wire = json.loads(resp_raw)
        completion, tokens = _extract_completion(wire, request_body=expected)
        parsed = parse_llama_cpp_decision(
            completion, mode=CognitionMode.BOUNDED,
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise Stage28c2cAuditHold("original model response invalid") from exc
    if (
        parsed.status is not DecisionStatus.RESOLVED
        or parsed.choice_id not in {"1", "2"}
        or result.get("choice_id") != parsed.choice_id
        or result.get("selection_status")
        != ("ESCALATE_L2" if parsed.choice_id == "1" else "DEFER")
        or result.get("model_status") != DecisionStatus.RESOLVED.value
        or result.get("prompt_tokens") != tokens.prompt_tokens
        or result.get("completion_tokens") != tokens.completion_tokens
        or result.get("backend_ref")
        != "stage28c2c-pid-" + str(gate["llama_pid"])
    ):
        raise Stage28c2cAuditHold("actual Gemma bounded choice not provenance-bound")
    return {
        "self_id": sid,
        "model_choice_id": parsed.choice_id,
        "original_request_id": request.request_id,
        "original_candidate_sha256": frozen,
        "native_session_id": native,
        "request_body_sha256": hashlib.sha256(req_raw).hexdigest(),
        "response_body_sha256": hashlib.sha256(resp_raw).hexdigest(),
        "actual_model_tokens": {
            "prompt": tokens.prompt_tokens,
            "completion": tokens.completion_tokens,
        },
        "physical_action_issued": False,
    }


def independently_audit_real_original_l1(
    *, result: Path, generation: Path, restored: Path,
    stage28b_evidence: Path, execution_dir: Path,
) -> dict:
    """Separate-process verifier; require both full real model and Paper proof."""
    evidence = result.parent
    report = json.loads(result.read_bytes())
    if (
        report.get("real_gemma_post") != 2
        or report.get("model_post_attempted") != 2
        or report.get("fresh_l1_run") is not True
        or report.get("real_action_issued") != 0
        or report.get("real_peer_sent") != 0
        or report.get("physical_action_issue_authorized") is not False
        or report.get("stage28c2c_l1_results") is None
        or report.get("stage28c2c_model_gate") is None
        or report.get("cleanup_uncertain")
        or report.get("raw_source_audit_uncertain")
    ):
        raise Stage28c2cAuditHold("original real Gemma/physical effect boundary failed")
    # The proven Stage28c2b independent verifier re-reads all immutable
    # native/Paper/owner/WAL/retirement from raw files before GPU model audit.
    base = independently_audit_recovered_real_rejoin(
        result, generation=generation, restored=restored,
        stage28b_evidence=stage28b_evidence,
        executable=execution_dir, expected_gemma_posts=2,
    )
    if (
        base.get("fresh_l1_run") is not True
        or base.get("real_gemma_post") != 2
        or base.get("real_action_issued") != 0
    ):
        raise Stage28c2cAuditHold("original A/B real World rejoin insufficient")
    gate = report["stage28c2c_model_gate"]
    if type(gate) is not dict or type(gate.get("model_alias")) is not str:
        raise Stage28c2cAuditHold("actual GGUF model identity missing")
    pinned = json.loads(
        (evidence / "stage28c2c-model-preflight.json").read_text(encoding="utf-8")
    )
    if (
        pinned != gate
        or gate.get("gguf_sha256") != PINNED_STAGE24G_GGUF_SHA256
        or type(gate.get("llama_pid")) is not int
        or gate["llama_pid"] <= 1
        or type(gate.get("slot_count")) is not int
        or gate["slot_count"] != 1
        or gate.get("slot_id") != 0
        or _sha(Path(gate["gguf_path"])) != gate["gguf_sha256"]
        or gate.get("gpu_name") is None
        or type(gate.get("native_cmdline_sha256")) is not str
        or len(gate["native_cmdline_sha256"]) != 64
        or type(gate.get("maps_sha256")) is not str
        or len(gate["maps_sha256"]) != 64
    ):
        raise Stage28c2cAuditHold("original owned GGUF/GPU/model gate not verified")
    if report.get("stage28c2c_backend_terminal_idle", {}).get("is_processing") is not False:
        raise Stage28c2cAuditHold("actual backend terminal /slots not idle")
    original, state = inspect_real_recovered_sources(
        generation, restored, stage28b_evidence,
    )
    if len(original.historical_native_sessions) < 3:
        raise Stage28c2cAuditHold("historical original session denylist incomplete")
    boot = Stage28ForkPaperEpoch(**report["paper_boot"])
    compared = []
    for sid, ordinal in (("A", 1), ("B", 2)):
        source_path = (
            Path(execution_dir) / "selves" / sid / "owner-state.json"
        )
        if _sha(source_path) != _sha(
            Path(generation) / "selves" / sid / "owner-state.json"
        ):
            raise Stage28c2cAuditHold("persistent original Intent/Skill owner cut mutated")
        compared.append(_validate_model_original_one(
            evidence=evidence, sid=sid, ordinal=ordinal,
            report=report, original_owner=state.owners[sid],
            boot=boot, gate=gate,
        ))
    if compared[0]["original_request_id"] == compared[1]["original_request_id"]:
        raise Stage28c2cAuditHold("A/B L1 request replay/collision")
    return {
        "classification": "REAL_RESTORED_A_B_FRESH_GEMMA_L1_BOUNDED_CHOICE_DEV",
        "original_stage28c2b_verified": True,
        "model_alias": gate["model_alias"],
        "real_model_post_count": 2,
        "verified_original_owners": compared,
        "physical_action_count": 0, "skill_execution_count": 0,
        "fresh_l2_run": False, "60s_autosave_attested": False,
        "qual_go": False, "science_run": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--stage28b-evidence", type=Path, required=True)
    parser.add_argument("--execution-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        audited = independently_audit_real_original_l1(
            result=args.result, generation=args.generation,
            restored=args.restored, stage28b_evidence=args.stage28b_evidence,
            execution_dir=args.execution_dir,
        )
        print(json.dumps(audited, sort_keys=True), flush=True)
        return 0
    except BaseException as exc:
        print(f"STAGE28C2C_INDEPENDENT_HOLD={type(exc).__name__}:{exc}",
              file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
