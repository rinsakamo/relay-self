from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s2_capability_plan


class CapabilityProfileId(str, Enum):
    MEM = "MEM"
    CTL = "CTL"
    CTL_SKL = "CTL+SKL"
    TALK = "TALK"
    MEM_CTL_SKL = "MEM+CTL+SKL"
    MEM_TALK = "MEM+TALK"


@dataclass(frozen=True, slots=True)
class CapabilityProfile:
    """Immutable named selection over the already-declared S2 capability set."""

    profile_id: CapabilityProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s2_capability_plan(enabled_ids=self.enabled_ids)


S4_PROFILES = (
    CapabilityProfile(
        profile_id=CapabilityProfileId.MEM,
        enabled_ids=frozenset({"MEM"}),
    ),
    CapabilityProfile(
        profile_id=CapabilityProfileId.CTL,
        enabled_ids=frozenset({"CTL"}),
    ),
    CapabilityProfile(
        profile_id=CapabilityProfileId.CTL_SKL,
        enabled_ids=frozenset({"CTL", "SKL"}),
    ),
    CapabilityProfile(
        profile_id=CapabilityProfileId.TALK,
        enabled_ids=frozenset({"TALK"}),
    ),
    CapabilityProfile(
        profile_id=CapabilityProfileId.MEM_CTL_SKL,
        enabled_ids=frozenset({"MEM", "CTL", "SKL"}),
    ),
    CapabilityProfile(
        profile_id=CapabilityProfileId.MEM_TALK,
        enabled_ids=frozenset({"MEM", "TALK"}),
    ),
)


def s4_capability_profile(profile_id: CapabilityProfileId) -> CapabilityProfile:
    """Return one frozen S4 qualification profile."""

    if not isinstance(profile_id, CapabilityProfileId):
        raise ValueError("profile_id must be CapabilityProfileId")

    for profile in S4_PROFILES:
        if profile.profile_id is profile_id:
            return profile

    raise ValueError(f"unsupported S4 capability profile: {profile_id}")
