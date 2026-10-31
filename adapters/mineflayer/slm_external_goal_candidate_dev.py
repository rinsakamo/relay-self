"""DEV-only past *separate client* Goal observation, always withheld from L8.

The real L22 source review is performed by pinned original L21/L22 owners.
This accepts only a bounded untrusted review summary for diagnostics; it
cannot authenticate the third party, admit a Goal, train or influence S49.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}\Z")
SCHEMA = "S49_L22_PREVIOUS_EXTERNAL_GOAL_DEV_V1"


class ExternalGoalCandidateRejected(ValueError):
    """Unbounded, forged, stale or authority-bearing DEV summary."""


@dataclass(frozen=True, slots=True)
class PreviousExternalGoalDiagnostic:
    source_session_id: str
    original_action_id: str
    source_l22_ref: str
    native_received_sha256: str
    native_sent_sha256: str
    original_s16_sha256: str
    separate_client_original_sha256: str
    separate_client_observation: str
    native_goal_status: str
    geometric_goal_candidate: str
    settling_state: str
    move_events_after_s16: int
    accepted_goal_status: str = "UNDETERMINED"
    external_owner_authenticated: bool = False
    physical_stability_attested: bool = False
    independently_attested_nonintervention: bool = False
    action_authority: bool = False
    learning_authority: bool = False
    qualified_l8_training_pairs: int = 0
    reason: str = "WITHHELD_EXTERNAL_GOAL_OWNER_AND_STABILITY_UNVERIFIED"

    def __post_init__(self):
        if (
            not all(_TOKEN.fullmatch(x) for x in (
                self.source_session_id, self.original_action_id,
            ))
            or not self.source_l22_ref.startswith(
                "451270faa1281889494f933a5eda33a71e88834f:"
            )
            or any(not _SHA.fullmatch(x) for x in (
                self.native_received_sha256, self.native_sent_sha256,
                self.original_s16_sha256, self.separate_client_original_sha256,
            ))
            or self.separate_client_observation not in (
                "REACHED", "NOT_REACHED", "UNDETERMINED",
            )
            or self.native_goal_status != "UNDETERMINED"
            or self.geometric_goal_candidate not in (
                "REACHED", "NOT_REACHED", "UNDETERMINED",
            )
            or self.settling_state not in (
                "SETTLING_OBSERVED", "STABILITY_UNPROVEN",
            )
            or type(self.move_events_after_s16) is not int
            or not 0 <= self.move_events_after_s16 <= 32
            or self.accepted_goal_status != "UNDETERMINED"
            or self.external_owner_authenticated is not False
            or self.physical_stability_attested is not False
            or self.independently_attested_nonintervention is not False
            or self.action_authority is not False
            or self.learning_authority is not False
            or type(self.qualified_l8_training_pairs) is not int
            or self.qualified_l8_training_pairs != 0
            or self.reason != "WITHHELD_EXTERNAL_GOAL_OWNER_AND_STABILITY_UNVERIFIED"
        ):
            raise ExternalGoalCandidateRejected("not a non-authorizing L22 DEV review")

    def audit_row(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "source_session_id": self.source_session_id,
            "original_action_id": self.original_action_id,
            "source_l22_ref": self.source_l22_ref,
            "native_received_sha256": self.native_received_sha256,
            "native_sent_sha256": self.native_sent_sha256,
            "original_s16_sha256": self.original_s16_sha256,
            "separate_client_original_sha256": self.separate_client_original_sha256,
            "separate_client_observation": self.separate_client_observation,
            "native_goal_status": self.native_goal_status,
            "geometric_goal_candidate": self.geometric_goal_candidate,
            "settling_state": self.settling_state,
            "move_events_after_s16": self.move_events_after_s16,
            "accepted_goal_status": "UNDETERMINED",
            "external_owner_authenticated": False,
            "physical_stability_attested": False,
            "independently_attested_nonintervention": False,
            "action_authority": False,
            "learning_authority": False,
            "qualified_l8_training_pairs": 0,
            "reason": self.reason,
        }


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for k, v in pairs:
        if k in result:
            raise ExternalGoalCandidateRejected("duplicate JSON field")
        result[k] = v
    return result


def read_external_goal_diagnostic(root: Path) -> PreviousExternalGoalDiagnostic:
    """Bounded post-review read; no untrusted JSON can authorize training."""
    path = root / "external-goal-dev-review.json"
    if (
        not isinstance(root, Path) or not root.is_absolute()
        or not root.is_dir() or root.is_symlink()
        or any(part.is_symlink() for part in root.parents)
        or not path.is_file() or path.is_symlink()
        or not 0 < path.stat().st_size <= 4096
    ):
        raise ExternalGoalCandidateRejected("fresh bounded review is required")
    try:
        doc = json.loads(path.read_bytes(), object_pairs_hook=_unique)
        if (
            type(doc) is not dict or doc.get("schema") != SCHEMA
            or set(doc) != set(PreviousExternalGoalDiagnostic.__dataclass_fields__) | {"schema"}
        ):
            raise ExternalGoalCandidateRejected("unrecognized review keys or schema")
        return PreviousExternalGoalDiagnostic(
            **{k: v for k, v in doc.items() if k != "schema"}
        )
    except (ValueError, TypeError, OSError, UnicodeError) as exc:
        raise ExternalGoalCandidateRejected("external Goal diagnostic invalid") from exc
