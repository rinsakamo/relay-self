from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s11_capability_plan


class HabitProfileId(str, Enum):
    HABIT = "HABIT"
    PLAN_HABIT = "PLAN+HABIT"


@dataclass(frozen=True, slots=True)
class HabitProfile:
    """Immutable S11 route selection; retained repertoire stays owner-local."""

    profile_id: HabitProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s11_capability_plan(enabled_ids=self.enabled_ids)


S11_HABIT_PROFILES = (
    HabitProfile(
        profile_id=HabitProfileId.HABIT,
        enabled_ids=frozenset({"HABIT"}),
    ),
    HabitProfile(
        profile_id=HabitProfileId.PLAN_HABIT,
        enabled_ids=frozenset({"PLAN", "HABIT"}),
    ),
)


def s11_habit_profile(profile_id: HabitProfileId) -> HabitProfile:
    if not isinstance(profile_id, HabitProfileId):
        raise ValueError("profile_id must be HabitProfileId")
    for profile in S11_HABIT_PROFILES:
        if profile.profile_id is profile_id:
            return profile
    raise ValueError(f"unsupported S11 habit profile: {profile_id}")
