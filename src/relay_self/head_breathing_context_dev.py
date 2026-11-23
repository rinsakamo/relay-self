"""Stage24d: read-only breathing-volume epistemic context (not air supply).

A head/eye block survey can describe physical medium but never prove that
self oxygen metadata is positive or authorize MOVE. Loaded/fresh/source-
qualified inputs are prerequisites; synthetic observations remain synthetic.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.provenance import Provenance


@dataclass(frozen=True, slots=True)
class HeadVolumeCell:
    loaded: bool
    material: str | None  # AIRLIKE | SOLID | FLUID | OTHER | None
    fluid: str | None  # WATER | LAVA | NONE | None

    def __post_init__(self) -> None:
        if type(self.loaded) is not bool:
            raise ValueError("head cell load state must be explicit")
        if self.material not in {None, "AIRLIKE", "SOLID", "FLUID", "OTHER"}:
            raise ValueError("head cell material must be typed or unknown")
        if self.fluid not in {None, "WATER", "LAVA", "NONE"}:
            raise ValueError("head cell fluid must be typed or unknown")


@dataclass(frozen=True, slots=True)
class HeadBreathingContext:
    session_id: str
    source_seq: int
    source_request_id: str
    source: Provenance
    measured_head_position: bool
    fresh: bool
    eye_cell: HeadVolumeCell
    upper_head_cell: HeadVolumeCell
    is_in_water: bool | None = None

    def __post_init__(self) -> None:
        if (
            not self.session_id or not self.source_request_id
            or type(self.source_seq) is not int or self.source_seq < 0
            or not isinstance(self.source, Provenance)
            or type(self.measured_head_position) is not bool
            or type(self.fresh) is not bool
            or not isinstance(self.eye_cell, HeadVolumeCell)
            or not isinstance(self.upper_head_cell, HeadVolumeCell)
            or self.is_in_water not in (None, True, False)
        ):
            raise ValueError("source-qualified head-volume observation required")


@dataclass(frozen=True, slots=True)
class BreathingContextAssessment:
    classification: str
    reason: str
    proven_breathable: bool = False
    grants_move: bool = False


def assess_head_breathing_context(
    reading: HeadBreathingContext,
) -> BreathingContextAssessment:
    """No 'BREATHABLE' conclusion from spatial data without owned oxygen.

    Even an airlike head cell might lack sufficient native oxygen metadata.
    This is a separate physical medium observation, not a substitute for
    Mineflayer's owned self Entity air-supply sensor.
    """
    if not isinstance(reading, HeadBreathingContext):
        raise TypeError("typed head-volume context required")
    if not reading.measured_head_position or not reading.fresh:
        return BreathingContextAssessment("UNKNOWN", "missing_or_stale_head_position")
    cells = (reading.eye_cell, reading.upper_head_cell)
    if any(
        not cell.loaded or cell.material is None or cell.fluid is None
        for cell in cells
    ):
        return BreathingContextAssessment("UNKNOWN", "unloaded_or_ambiguous_head_cells")
    if any(cell.fluid != "NONE" or cell.material == "FLUID" for cell in cells):
        return BreathingContextAssessment("HEAD_FLUID_PRESENT", "fluid_at_head_volume")
    if any(cell.material == "SOLID" for cell in cells):
        return BreathingContextAssessment("HEAD_OBSTRUCTED", "solid_at_head_volume")
    if all(cell.material == "AIRLIKE" and cell.fluid == "NONE" for cell in cells):
        return BreathingContextAssessment(
            "HEAD_AIRLIKE_OBSERVED", "medium_observed_but_oxygen_unverified",
        )
    return BreathingContextAssessment("UNKNOWN", "other_head_medium_unresolved")
