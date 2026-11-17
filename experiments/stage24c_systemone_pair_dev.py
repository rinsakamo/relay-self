"""Stage24c: opt-in TWO-CALL synthetic Jev control; never a World experiment.

Uses the ORIGINAL Stage24a CPU+choice builder and llama.cpp Jev request
renderer/parser. One synthetic UNKNOWN-oxygen vs known-positive-oxygen
contrast. Raw HTTP BODY bytes are archived BEFORE interpretation. No Self
resident lane, native action, World runner, optimizer, or automatic retries.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from dataclasses import asdict
from pathlib import Path

from adapters.llama_cpp.relay_engine import (
    LlamaCppRelayProvider,
    parse_llama_cpp_jev_decision,
    render_llama_cpp_jev_request,
)
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)
from experiments.p0d_real_paper_smoke_dev import _write_bytes_new, file_sha256
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import PhysicalCapability
from relay_self.resident_exploration_gate_audit_dev import audit_exploration_gate
from relay_self.resident_l1_move_options_dev import build_resident_l1_move_turn
from relay_self.resident_llama_inference_lane_dev import LlamaCppSingleSlotWitness


class Stage24cCalibrationRefusal(RuntimeError):
    """No model result can promote offline synthetic input to World truth."""


def synthetic_control_pair():
    """Exactly ONE changed field: oxygen unknown vs known positive.

    Position, health, food, time, nearby coverage and owner are synthetic.
    No result can establish that the real World was breathable or safe.
    """
    capability = PhysicalCapability("MOVE", 1, "locomotion", "RELATIVE", True)
    controls = []
    for case_name, oxygen in (
        ("oxygen_unknown", None), ("oxygen_known_positive", 300.0),
    ):
        snapshot = MineflayerSnapshot(
            health=20, food=20, food_saturation=5,
            oxygen_level=oxygen,
            position=MineflayerPosition(10.5, 121, 9.5),
            time=MineflayerTime(6000, 0, True),
            inventory=(), nearby_entities=(),
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES, 0, False,
            ),
        )
        probe = MineflayerObservation(
            "SYNTHETIC-STAGE24C-NOT-REAL-WORLD", 42, "probe",
            snapshot, f"synthetic-stage24c-{case_name}",
        )
        owner = IntentCommitment()
        turn = build_resident_l1_move_turn(
            probe, self_id="B", intent_owner=owner,
            capability=capability, epoch=1,
        )
        audit = audit_exploration_gate(probe, intent_owner=owner)
        # Stage24c historic source-HEAD compared two *different* candidate
        # sets. Stage24e deliberately removes that motor permission gate.
        # The old outcome remains immutable; a new run has new semantics.
        if not turn.exploration_need_active:
            raise Stage24cCalibrationRefusal("innate exploration Need missing")
        controls.append((case_name, turn, audit))
    return tuple(controls)


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def synthetic_jev_payloads(model: str) -> tuple[tuple[str, object, object, dict], ...]:
    if type(model) is not str or not model.strip():
        raise Stage24cCalibrationRefusal("explicit actual model alias required")
    return tuple(
        (name, turn, audit, render_llama_cpp_jev_request(
            turn.round.request, model=model,
        ))
        for name, turn, audit in synthetic_control_pair()
    )


def run_stage24c_calibration(
    *, evidence_dir: Path, model: str, endpoint: str,
    systemone_endpoint: str, backend_ref: str,
    grant_real_llm: bool, execute_model: bool,
) -> tuple[dict[str, object], ...]:
    """Write synthetic requests; optionally send at most ONE per control.

    Dedicated owned PID/model/sole client is operator verified. A real model
    call must have an idle exclusive n_parallel=1 /slots witness on the SAME
    backend before and after inference. Never interpret as a physical grant.
    """
    if evidence_dir.exists():
        raise Stage24cCalibrationRefusal("new evidence directory required")
    payloads = synthetic_jev_payloads(model)
    provider = None
    witness = None
    if execute_model:
        if grant_real_llm is not True:
            raise Stage24cCalibrationRefusal("real model permission missing")
        provider = LlamaCppRelayProvider(
            endpoint=endpoint, systemone_endpoint=systemone_endpoint,
            model=model, timeout=60.0,
        )
        witness = LlamaCppSingleSlotWitness(
            provider=provider, backend_ref=backend_ref,
        )
        witness.require_idle()
    elif grant_real_llm:
        raise Stage24cCalibrationRefusal("inspection never authorizes real GPU")
    evidence_dir.mkdir(mode=0o700, parents=False)
    records = []
    for name, turn, audit, body in payloads:
        request_file = evidence_dir / f"{name}-jev-request.json"
        _write_bytes_new(request_file, _json_bytes(body))
        record = {
            "case": name,
            "schema": "STAGE24E_SYNTHETIC_JEV_CONTROL",
            "exploration_policy": "INNATE_NEED_NOT_BODY_GATE",
            "historic_stage24c_outcome_reproduced": False,
            "source_kind": "SYNTHETIC_NOT_WORLD_EVIDENCE",
            "original_eligibility_audit": asdict(audit),
            "original_candidate_ids": tuple(
                body["questions"]["decision"]["criteria"],
            ),
            "request_file": str(request_file),
            "request_sha256": file_sha256(request_file),
            "actual_model_executed": False,
            "physical_action_authorized": False,
        }
        if execute_model:
            assert witness is not None and provider is not None
            witness.require_idle()
            request = urllib.request.Request(
                provider.systemone_endpoint,
                data=_json_bytes(body),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            start_ns = time.perf_counter_ns()
            with urllib.request.urlopen(request, timeout=60.0) as response:
                raw_body = response.read(1024 * 1024 + 1)
                status = response.status
            elapsed_ns = time.perf_counter_ns() - start_ns
            # Never process a response truncated by the evidence bound.
            if status != 200 or len(raw_body) > 1024 * 1024:
                raise Stage24cCalibrationRefusal(
                    "non-200 or oversized Jev response; no retry"
                )
            raw_file = evidence_dir / f"{name}-jev-raw-http-body.json"
            _write_bytes_new(raw_file, raw_body)
            witness.require_idle()
            # Parse through the production adapter, but only AFTER raw bytes
            # have been fsynced and secured for later independent readback.
            decision = parse_llama_cpp_jev_decision(
                json.loads(raw_body), request=turn.round.request,
            )
            record.update({
                "actual_model_executed": True,
                "raw_http_body_file": str(raw_file),
                "raw_http_body_sha256": file_sha256(raw_file),
                "http_status": status,
                "model_elapsed_ns": elapsed_ns,
                "provider_status": decision.status.value,
                "provider_choice_id": decision.choice_id,
                "provider_reason": decision.reason,
                "provider_facts": asdict(decision.call_facts),
            })
        record_file = evidence_dir / f"{name}-receipt.json"
        _write_bytes_new(record_file, _json_bytes(record))
        records.append(record)
    manifest = evidence_dir / "stage24c-manifest.json"
    _write_bytes_new(
        manifest, _json_bytes({
            "classification": "STAGE24C_SYNTHETIC_NO_WORLD",
            "cases": records,
            "model_requests_sent": int(execute_model) * len(records),
            "physical_actions_issued": 0,
            "worlds_created": 0,
        }),
    )
    return tuple(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--model", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect-only", action="store_true")
    mode.add_argument("--execute-model-pair", action="store_true")
    parser.add_argument("--grant-real-llm", action="store_true")
    parser.add_argument("--llama-endpoint", default="")
    parser.add_argument("--systemone-endpoint", default="")
    parser.add_argument("--backend-ref", default="")
    args = parser.parse_args()
    try:
        records = run_stage24c_calibration(
            evidence_dir=args.evidence_dir, model=args.model,
            endpoint=args.llama_endpoint,
            systemone_endpoint=args.systemone_endpoint,
            backend_ref=args.backend_ref,
            grant_real_llm=args.grant_real_llm,
            execute_model=args.execute_model_pair,
        )
    except Exception as exc:
        print(f"STAGE24C_CALIBRATION_HOLD={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2
    print(
        "STAGE24C_SYNTHETIC_NO_WORLD "
        + " ".join(
            f"{r['case']}:{r.get('provider_status', 'NOT_RUN')}"
            for r in records
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
