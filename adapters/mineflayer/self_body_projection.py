"""Minecraft-specific, read-only bridge from existing Present and S16 evidence.

No packets, commands, physical resource writes, or native runtime imports.
"""
from __future__ import annotations

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.present_projection import MinecraftPresent, project_mineflayer_present
from relay_self.action_outcome import ActionOutcomeDisposition, ActionOutcomeInterpretation
from relay_self.self_body import BodyField, BodyObservation, InvalidSelfBodyData


def project_body_present(present: MinecraftPresent) -> BodyObservation:
    """Convert source-qualified target Present without manufacturing M/P1 states."""
    if not isinstance(present, MinecraftPresent):
        raise InvalidSelfBodyData("requires existing MinecraftPresent")
    if present.provenance.source != "mineflayer":
        raise InvalidSelfBodyData("requires mineflayer Present provenance")
    x, y, z = present.body_position
    return BodyObservation(
        session_id=present.session_id,
        native_seq=present.seq,
        request_id=present.request_id,
        fields=(
            BodyField("position_x", x),
            BodyField("position_y", y),
            BodyField("position_z", z),
            BodyField("health", present.health),
            BodyField("food", present.food),
            BodyField("food_saturation", present.food_saturation),
        ),
        source_provenance=present.provenance,
    )


def project_body_action_readback(
    consequence: WorldConsequence,
    outcome: ActionOutcomeInterpretation,
) -> BodyObservation:
    """Only exact S15 consequence and S16 interpreted execution yield readback.

    ACK or a known adapter rejection is not sufficient. The original native
    before/after probes must be ordered and session-bound; no guessed movement.
    """
    if not isinstance(consequence, WorldConsequence) or not isinstance(
        outcome, ActionOutcomeInterpretation
    ):
        raise InvalidSelfBodyData("requires exact S15 and S16 typed inputs")
    if (consequence.status is not WorldConsequenceStatus.EXECUTED
            or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
            or outcome.reason_code != "observed_execution"
            or consequence.action_id != outcome.action_id
            or consequence.binding_id != outcome.binding_id
            or consequence.action_ref != outcome.action_ref
            or consequence.session_id != outcome.session_id
            or consequence.provenance != outcome.world_provenance):
        raise InvalidSelfBodyData("Action readback lacks exact executed S15/S16 match")
    before = consequence.before_observation
    after = consequence.after_observation
    if (before is None or after is None
            or before.session_id != outcome.session_id
            or after.session_id != outcome.session_id
            or before.seq >= after.seq):
        raise InvalidSelfBodyData("missing, foreign, or unordered native before/after")
    present = project_mineflayer_present(after)
    observation = project_body_present(present)
    return BodyObservation(
        session_id=observation.session_id,
        native_seq=observation.native_seq,
        request_id=observation.request_id,
        fields=observation.fields,
        source_provenance=observation.source_provenance,
        action_id=outcome.action_id,
        consequence_provenance=outcome.world_provenance,
    )
