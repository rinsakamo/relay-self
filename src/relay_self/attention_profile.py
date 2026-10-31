from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s5_capability_plan


class AttentionProfileId(str, Enum):
    ATT = "ATT"
    ATT_TALK = "ATT+TALK"


@dataclass(frozen=True, slots=True)
class AttentionProfile:
    """Immutable S5 qualification selection; it owns no runtime state."""

    profile_id: AttentionProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s5_capability_plan(enabled_ids=self.enabled_ids)


S5_ATTENTION_PROFILES = (
    AttentionProfile(
        profile_id=AttentionProfileId.ATT,
        enabled_ids=frozenset({"ATT"}),
    ),
    AttentionProfile(
        profile_id=AttentionProfileId.ATT_TALK,
        enabled_ids=frozenset({"ATT", "TALK"}),
    ),
)


def s5_attention_profile(profile_id: AttentionProfileId) -> AttentionProfile:
    """Return one frozen S5 ATT qualification profile."""

    if not isinstance(profile_id, AttentionProfileId):
        raise ValueError("profile_id must be AttentionProfileId")

    for profile in S5_ATTENTION_PROFILES:
        if profile.profile_id is profile_id:
            return profile

    raise ValueError(f"unsupported S5 attention profile: {profile_id}")
