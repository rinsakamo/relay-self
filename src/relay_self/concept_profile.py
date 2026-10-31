from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan
from relay_self.execution_descriptor import s7_capability_plan


class ConceptProfileId(str, Enum):
    CNC = "CNC"
    BLF_CNC = "BLF+CNC"
    ATT_BLF_CNC = "ATT+BLF+CNC"


@dataclass(frozen=True, slots=True)
class ConceptProfile:
    """Immutable S7 qualification selection; it owns no runtime state."""

    profile_id: ConceptProfileId
    enabled_ids: frozenset[str]

    def plan(self) -> CapabilityPlan:
        return s7_capability_plan(enabled_ids=self.enabled_ids)


S7_CONCEPT_PROFILES = (
    ConceptProfile(
        profile_id=ConceptProfileId.CNC,
        enabled_ids=frozenset({"CNC"}),
    ),
    ConceptProfile(
        profile_id=ConceptProfileId.BLF_CNC,
        enabled_ids=frozenset({"BLF", "CNC"}),
    ),
    ConceptProfile(
        profile_id=ConceptProfileId.ATT_BLF_CNC,
        enabled_ids=frozenset({"ATT", "BLF", "CNC"}),
    ),
)


def s7_concept_profile(profile_id: ConceptProfileId) -> ConceptProfile:
    """Return one frozen S7 CNC qualification profile."""

    if not isinstance(profile_id, ConceptProfileId):
        raise ValueError("profile_id must be ConceptProfileId")

    for profile in S7_CONCEPT_PROFILES:
        if profile.profile_id is profile_id:
            return profile

    raise ValueError(f"unsupported S7 concept profile: {profile_id}")
