from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s10_capability_plan


class LearningProfileId(str, Enum):
    LRN = "LRN"
    PLAN_LRN = "PLAN+LRN"


@dataclass(frozen=True, slots=True)
class LearningProfile:
    """Immutable S10 qualification selection; retained state remains owner-local."""

    profile_id: LearningProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s10_capability_plan(enabled_ids=self.enabled_ids)


S10_LEARNING_PROFILES = (
    LearningProfile(
        profile_id=LearningProfileId.LRN,
        enabled_ids=frozenset({"LRN"}),
    ),
    LearningProfile(
        profile_id=LearningProfileId.PLAN_LRN,
        enabled_ids=frozenset({"PLAN", "LRN"}),
    ),
)


def s10_learning_profile(
    profile_id: LearningProfileId,
) -> LearningProfile:
    """Return one frozen S10 LRN qualification profile."""

    if not isinstance(profile_id, LearningProfileId):
        raise ValueError("profile_id must be LearningProfileId")

    for profile in S10_LEARNING_PROFILES:
        if profile.profile_id is profile_id:
            return profile

    raise ValueError(f"unsupported S10 learning profile: {profile_id}")
