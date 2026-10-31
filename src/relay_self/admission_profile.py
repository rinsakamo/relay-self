from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s13_capability_plan


class AdmissionProfileId(str, Enum):
    ADMISSION = "ADMISSION"
    ROUTE_ADMISSION = "ROUTE+ADMISSION"
    PLAN_HABIT_ROUTE_ADMISSION = "PLAN+HABIT+ROUTE+ADMISSION"
    FULL_DETERMINISTIC_ADMISSION = (
        "ATT+BLF+CNC+PRD+PLAN+HABIT+ROUTE+ADMISSION"
    )


@dataclass(frozen=True, slots=True)
class AdmissionProfile:
    """Immutable S13 integration selection; it owns no authority state."""

    profile_id: AdmissionProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s13_capability_plan(enabled_ids=self.enabled_ids)


S13_ADMISSION_PROFILES = (
    AdmissionProfile(
        profile_id=AdmissionProfileId.ADMISSION,
        enabled_ids=frozenset({"ADMISSION"}),
    ),
    AdmissionProfile(
        profile_id=AdmissionProfileId.ROUTE_ADMISSION,
        enabled_ids=frozenset({"ROUTE", "ADMISSION"}),
    ),
    AdmissionProfile(
        profile_id=AdmissionProfileId.PLAN_HABIT_ROUTE_ADMISSION,
        enabled_ids=frozenset({"PLAN", "HABIT", "ROUTE", "ADMISSION"}),
    ),
    AdmissionProfile(
        profile_id=AdmissionProfileId.FULL_DETERMINISTIC_ADMISSION,
        enabled_ids=frozenset(
            {
                "ATT",
                "BLF",
                "CNC",
                "PRD",
                "PLAN",
                "HABIT",
                "ROUTE",
                "ADMISSION",
            }
        ),
    ),
)


def s13_admission_profile(
    profile_id: AdmissionProfileId,
) -> AdmissionProfile:
    if not isinstance(profile_id, AdmissionProfileId):
        raise ValueError("profile_id must be AdmissionProfileId")
    for profile in S13_ADMISSION_PROFILES:
        if profile.profile_id is profile_id:
            return profile
    raise ValueError(f"unsupported S13 admission profile: {profile_id}")
