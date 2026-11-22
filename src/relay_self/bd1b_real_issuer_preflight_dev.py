"""Read-only real-Gemma ingress gate for original B+D Question adoption.

This code DOES NOT start Paper or a model. A genuine original Owner/Native/
Paper/Schema source and already-running exclusive local llama-server must
qualify BEFORE attaching the original inference lane or creating World work.
"""
from dataclasses import dataclass
from pathlib import Path

from experiments.stage24g_model_gate_dev import (
    Stage24gModelGateReceipt,
    verify_stage24g_model_gate,
)
from relay_self.bd1b_coverage_adoption_turn_dev import (
    CHOICES,
    CoverageAdoptionTurn,
    prepare_coverage_adoption_turn,
    validate_coverage_adoption_turn_cpu,
)
from relay_self.innate_schema import SchemaMode
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge


class BD1bRealIssuerHold(RuntimeError):
    """Refuse an unqualified real-model attempt before any model POST."""


@dataclass(frozen=True, slots=True)
class BD1bRealIssuerPreflight:
    """A source-pinned candidate, NOT an issuer result or decision authority."""

    turn: CoverageAdoptionTurn
    gate: Stage24gModelGateReceipt
    action_issue_authorized: bool = False
    model_post_attempted: bool = False


def require_live_bd1b_source(*, bridge, boot, world, links, self_id):
    """Check original-owner Schema and Body before permitting GPU inspection.

    A restored Stage28c2b Owner without independently qualified persisted
    exploration Schema activation must HOLD. Never bootstrap one on the fly.
    """
    if (not isinstance(bridge, OwnedResidentPhysicalBridge)
            or bridge.cognitive_work is None or bridge.inference_lane is not None
            or not bridge.physical.observation_only
            or bridge.physical.active_action_ids
            or self_id not in ("A", "B")):
        raise BD1bRealIssuerHold("original inert bridge and A/B Self required")
    resident = bridge.cognitive_work
    with resident.lock:
        if set(resident.owners) != {"A", "B"}:
            raise BD1bRealIssuerHold("original two-Self roster required")
        for sid in ("A", "B"):
            try:
                schema = resident.present_schema(sid)
            except (ValueError, RuntimeError, KeyError, AttributeError) as exc:
                raise BD1bRealIssuerHold(
                    "RESTORED_SCHEMA_ACTIVATION_NOT_ATTESTED"
                ) from exc
            activation = schema.get("exploratory")
            if (schema.self_id != sid or activation is None or activation.spec.version != 1
                    or activation.mode is not SchemaMode.FULL
                    or "EXPLORATION_NEED" not in activation.spec.signal_kinds
                    or schema.revision != resident.owners[sid].pattern_registry.revision):
                raise BD1bRealIssuerHold("current original exploration Schema not qualified")
        turn = prepare_coverage_adoption_turn(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
        )
        if (turn.request.choices != CHOICES or turn.request.think_allowed
                or turn.request.focus != turn.inquiry.question_ref
                or turn.owner is not resident.owners[self_id]):
            raise BD1bRealIssuerHold("source-frozen original bounded candidates invalid")
        validate_coverage_adoption_turn_cpu(
            bridge=bridge, boot=boot, world=world, links=links, turn=turn,
        )
        return turn


def inspect_bd1b_real_issuer(*, bridge, boot, world, links, self_id,
                            gguf_path: Path, llama_pid: int, model_alias: str,
                            llama_endpoint: str) -> BD1bRealIssuerPreflight:
    """Inspect original source and real loaded model before issuing any work."""
    turn = require_live_bd1b_source(
        bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
    )
    gate = verify_stage24g_model_gate(
        gguf_path=gguf_path, llama_pid=llama_pid, model_alias=model_alias,
        llama_endpoint=llama_endpoint, systemone_endpoint=llama_endpoint,
    )
    if (type(gate) is not Stage24gModelGateReceipt
            or gate.llama_pid != llama_pid or gate.model_alias != model_alias
            or gate.slot_count != 1 or gate.slot_id != 0):
        raise BD1bRealIssuerHold("real local single-slot model owner missing")
    validate_coverage_adoption_turn_cpu(
        bridge=bridge, boot=boot, world=world, links=links, turn=turn,
    )
    return BD1bRealIssuerPreflight(turn, gate)
