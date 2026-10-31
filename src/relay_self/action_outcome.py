from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.provenance import Provenance


class ActionOutcomeError(ValueError):
    """Base error for explicit World-consequence to Action closure."""


class InvalidActionOutcomeData(ActionOutcomeError):
    """Raised when an interpreted Action outcome violates S16 contracts."""


class ActionOutcomeDisposition(str, Enum):
    """Existing Action-owner transition justified by one consequence."""

    OUTCOME = "outcome"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ActionOutcomeInterpretation:
    """Immutable audit bridge from environment consequence to Action owner."""

    action_id: str
    binding_id: str
    action_ref: str
    skill_execution_id: str
    intent_id: str
    session_id: str
    source_status: str
    disposition: ActionOutcomeDisposition
    reason_code: str
    world_provenance: Provenance
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("action_id", self.action_id)
        _require_identifier("binding_id", self.binding_id)
        _require_identifier("action_ref", self.action_ref)
        _require_identifier("skill_execution_id", self.skill_execution_id)
        _require_identifier("intent_id", self.intent_id)
        _require_identifier("session_id", self.session_id)
        _require_identifier("source_status", self.source_status)
        if not isinstance(self.disposition, ActionOutcomeDisposition):
            raise InvalidActionOutcomeData(
                "disposition must be ActionOutcomeDisposition"
            )
        _require_identifier("reason_code", self.reason_code)
        _require_provenance("world_provenance", self.world_provenance)
        _require_provenance("interpretation provenance", self.provenance)


def record_interpreted_action_outcome(
    supervisor: ActionSupervisor,
    interpretation: ActionOutcomeInterpretation,
    *,
    at_ns: int,
) -> ActionLifecycle:
    """Apply one already-interpreted result through the existing Action owner.

    S16 does not mutate ActionLifecycle directly. OUTCOME and UNKNOWN are
    delegated to ActionSupervisor, which remains the retained terminal-state
    owner and continues to enforce currentness, transition legality, replay
    rejection, and monotonic processing time.
    """

    if not isinstance(supervisor, ActionSupervisor):
        raise InvalidActionOutcomeData(
            "supervisor must be ActionSupervisor"
        )
    if not isinstance(interpretation, ActionOutcomeInterpretation):
        raise InvalidActionOutcomeData(
            "interpretation must be ActionOutcomeInterpretation"
        )
    _require_at_ns(at_ns)

    if interpretation.disposition is ActionOutcomeDisposition.UNAVAILABLE:
        raise InvalidActionOutcomeData(
            "unavailable consequence interpretation cannot close Action"
        )

    current = supervisor.get(interpretation.action_id)
    if current.skill_execution_id != interpretation.skill_execution_id:
        raise InvalidActionOutcomeData(
            "supervised skill_execution_id does not match interpretation"
        )
    if current.intent_id != interpretation.intent_id:
        raise InvalidActionOutcomeData(
            "supervised intent_id does not match interpretation"
        )

    if interpretation.disposition is ActionOutcomeDisposition.OUTCOME:
        return supervisor.record_outcome(
            interpretation.action_id,
            at_ns=at_ns,
            provenance=interpretation.world_provenance,
        )
    if interpretation.disposition is ActionOutcomeDisposition.UNKNOWN:
        return supervisor.mark_unknown(
            interpretation.action_id,
            at_ns=at_ns,
            provenance=interpretation.world_provenance,
        )

    raise InvalidActionOutcomeData("unsupported Action outcome disposition")


def _require_identifier(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidActionOutcomeData(f"{name} must be a non-empty string")
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidActionOutcomeData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_at_ns(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidActionOutcomeData(
            "Action outcome time must be a non-negative integer"
        )


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidActionOutcomeData(f"{name} must be Provenance")
