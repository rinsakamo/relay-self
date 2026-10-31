from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s12_capability_plan


class RouteProfileId(str, Enum):
    ROUTE = "ROUTE"
    PLAN_ROUTE = "PLAN+ROUTE"
    HABIT_ROUTE = "HABIT+ROUTE"
    PLAN_HABIT_ROUTE = "PLAN+HABIT+ROUTE"
    FULL_DETERMINISTIC_ROUTE = "ATT+BLF+CNC+PRD+PLAN+HABIT+ROUTE"


@dataclass(frozen=True, slots=True)
class RouteProfile:
    """Immutable S12 integration selection; it owns no runtime state."""

    profile_id: RouteProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s12_capability_plan(enabled_ids=self.enabled_ids)


S12_ROUTE_PROFILES = (
    RouteProfile(
        profile_id=RouteProfileId.ROUTE,
        enabled_ids=frozenset({"ROUTE"}),
    ),
    RouteProfile(
        profile_id=RouteProfileId.PLAN_ROUTE,
        enabled_ids=frozenset({"PLAN", "ROUTE"}),
    ),
    RouteProfile(
        profile_id=RouteProfileId.HABIT_ROUTE,
        enabled_ids=frozenset({"HABIT", "ROUTE"}),
    ),
    RouteProfile(
        profile_id=RouteProfileId.PLAN_HABIT_ROUTE,
        enabled_ids=frozenset({"PLAN", "HABIT", "ROUTE"}),
    ),
    RouteProfile(
        profile_id=RouteProfileId.FULL_DETERMINISTIC_ROUTE,
        enabled_ids=frozenset(
            {"ATT", "BLF", "CNC", "PRD", "PLAN", "HABIT", "ROUTE"}
        ),
    ),
)


def s12_route_profile(profile_id: RouteProfileId) -> RouteProfile:
    if not isinstance(profile_id, RouteProfileId):
        raise ValueError("profile_id must be RouteProfileId")
    for profile in S12_ROUTE_PROFILES:
        if profile.profile_id is profile_id:
            return profile
    raise ValueError(f"unsupported S12 route profile: {profile_id}")
