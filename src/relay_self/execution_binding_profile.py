from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s14_capability_plan


class ExecutionBindingProfileId(str, Enum):
    EXEC_BIND = "CTL+SKL+ADMISSION+EXEC_BIND"
    ROUTE_ADMISSION_EXEC_BIND = "CTL+SKL+ROUTE+ADMISSION+EXEC_BIND"
    FULL_DETERMINISTIC_EXECUTION_BINDING = (
        "CTL+SKL+ATT+BLF+CNC+PRD+PLAN+HABIT+ROUTE+ADMISSION+EXEC_BIND"
    )


@dataclass(frozen=True, slots=True)
class ExecutionBindingProfile:
    """Immutable S14 integration selection; it owns no execution state."""

    profile_id: ExecutionBindingProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s14_capability_plan(enabled_ids=self.enabled_ids)


S14_EXECUTION_BINDING_PROFILES = (
    ExecutionBindingProfile(
        profile_id=ExecutionBindingProfileId.EXEC_BIND,
        enabled_ids=frozenset({"CTL", "SKL", "ADMISSION", "EXEC_BIND"}),
    ),
    ExecutionBindingProfile(
        profile_id=ExecutionBindingProfileId.ROUTE_ADMISSION_EXEC_BIND,
        enabled_ids=frozenset(
            {"CTL", "SKL", "ROUTE", "ADMISSION", "EXEC_BIND"}
        ),
    ),
    ExecutionBindingProfile(
        profile_id=ExecutionBindingProfileId.FULL_DETERMINISTIC_EXECUTION_BINDING,
        enabled_ids=frozenset(
            {
                "CTL",
                "SKL",
                "ATT",
                "BLF",
                "CNC",
                "PRD",
                "PLAN",
                "HABIT",
                "ROUTE",
                "ADMISSION",
                "EXEC_BIND",
            }
        ),
    ),
)


def s14_execution_binding_profile(
    profile_id: ExecutionBindingProfileId,
) -> ExecutionBindingProfile:
    if not isinstance(profile_id, ExecutionBindingProfileId):
        raise ValueError("profile_id must be ExecutionBindingProfileId")
    for profile in S14_EXECUTION_BINDING_PROFILES:
        if profile.profile_id is profile_id:
            return profile
    raise ValueError(f"unsupported S14 execution-binding profile: {profile_id}")
