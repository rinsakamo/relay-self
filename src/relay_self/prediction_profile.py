from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s8_capability_plan


class PredictionProfileId(str, Enum):
    PRD = "PRD"
    CNC_PRD = "CNC+PRD"
    ATT_BLF_CNC_PRD = "ATT+BLF+CNC+PRD"


@dataclass(frozen=True, slots=True)
class PredictionProfile:
    """Immutable S8 qualification selection; it owns no runtime state."""

    profile_id: PredictionProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s8_capability_plan(enabled_ids=self.enabled_ids)


S8_PREDICTION_PROFILES = (
    PredictionProfile(
        profile_id=PredictionProfileId.PRD,
        enabled_ids=frozenset({"PRD"}),
    ),
    PredictionProfile(
        profile_id=PredictionProfileId.CNC_PRD,
        enabled_ids=frozenset({"CNC", "PRD"}),
    ),
    PredictionProfile(
        profile_id=PredictionProfileId.ATT_BLF_CNC_PRD,
        enabled_ids=frozenset({"ATT", "BLF", "CNC", "PRD"}),
    ),
)


def s8_prediction_profile(
    profile_id: PredictionProfileId,
) -> PredictionProfile:
    """Return one frozen S8 PRD qualification profile."""

    if not isinstance(profile_id, PredictionProfileId):
        raise ValueError("profile_id must be PredictionProfileId")

    for profile in S8_PREDICTION_PROFILES:
        if profile.profile_id is profile_id:
            return profile

    raise ValueError(f"unsupported S8 prediction profile: {profile_id}")
