from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s6_capability_plan


class BeliefProfileId(str, Enum):
    BLF = "BLF"
    ATT_BLF = "ATT+BLF"


@dataclass(frozen=True, slots=True)
class BeliefProfile:
    """Immutable S6 qualification selection; it owns no runtime state."""

    profile_id: BeliefProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s6_capability_plan(enabled_ids=self.enabled_ids)


S6_BELIEF_PROFILES = (
    BeliefProfile(
        profile_id=BeliefProfileId.BLF,
        enabled_ids=frozenset({"BLF"}),
    ),
    BeliefProfile(
        profile_id=BeliefProfileId.ATT_BLF,
        enabled_ids=frozenset({"ATT", "BLF"}),
    ),
)


def s6_belief_profile(profile_id: BeliefProfileId) -> BeliefProfile:
    """Return one frozen S6 BLF qualification profile."""

    if not isinstance(profile_id, BeliefProfileId):
        raise ValueError("profile_id must be BeliefProfileId")

    for profile in S6_BELIEF_PROFILES:
        if profile.profile_id is profile_id:
            return profile

    raise ValueError(f"unsupported S6 belief profile: {profile_id}")
