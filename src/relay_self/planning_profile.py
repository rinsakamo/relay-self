from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s9_capability_plan


class PlanningProfileId(str, Enum):
    PLAN = "PLAN"
    PRD_PLAN = "PRD+PLAN"
    ATT_BLF_CNC_PRD_PLAN = "ATT+BLF+CNC+PRD+PLAN"


@dataclass(frozen=True, slots=True)
class PlanningProfile:
    """Immutable S9 qualification selection; it owns no runtime state."""

    profile_id: PlanningProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s9_capability_plan(enabled_ids=self.enabled_ids)


S9_PLANNING_PROFILES = (
    PlanningProfile(
        profile_id=PlanningProfileId.PLAN,
        enabled_ids=frozenset({"PLAN"}),
    ),
    PlanningProfile(
        profile_id=PlanningProfileId.PRD_PLAN,
        enabled_ids=frozenset({"PRD", "PLAN"}),
    ),
    PlanningProfile(
        profile_id=PlanningProfileId.ATT_BLF_CNC_PRD_PLAN,
        enabled_ids=frozenset({"ATT", "BLF", "CNC", "PRD", "PLAN"}),
    ),
)


def s9_planning_profile(
    profile_id: PlanningProfileId,
) -> PlanningProfile:
    """Return one frozen S9 PLAN qualification profile."""

    if not isinstance(profile_id, PlanningProfileId):
        raise ValueError("profile_id must be PlanningProfileId")

    for profile in S9_PLANNING_PROFILES:
        if profile.profile_id is profile_id:
            return profile

    raise ValueError(f"unsupported S9 planning profile: {profile_id}")
