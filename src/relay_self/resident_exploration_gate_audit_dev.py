"""Stage24c: source-qualified, read-only explanation of exploration admission.

No sensor fallback, no physical permission and no invented air value. UNKNOWN
blocks low-pressure exploration rather than assuming safety.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.intent import IntentCommitment


@dataclass(frozen=True, slots=True)
class ExplorationGateCheck:
    predicate: str
    status: str  # PASS | BLOCKED | UNKNOWN


@dataclass(frozen=True, slots=True)
class ExplorationGateAudit:
    native_session_id: str
    native_seq: int
    native_request_id: str
    checks: tuple[ExplorationGateCheck, ...]
    eligible: bool
    physical_authorized: bool = False

    @property
    def blocking_codes(self) -> tuple[str, ...]:
        return tuple(
            check.predicate + ":" + check.status
            for check in self.checks if check.status != "PASS"
        )


def audit_exploration_gate(
    probe: MineflayerObservation, *, intent_owner: IntentCommitment,
) -> ExplorationGateAudit:
    """Use exactly the predicates that gate the original Stage24a exploration.

    Known oxygen 0 is BLOCKED; missing oxygen is UNKNOWN, never zero or
    assumed to be ambient air. The capability gate is applied separately
    by the original candidate builder.
    """
    if (
        not isinstance(probe, MineflayerObservation)
        or not isinstance(intent_owner, IntentCommitment)
    ):
        raise TypeError("typed WorldBody observation and original intent owner required")
    body = probe.snapshot
    truncated = body.nearby_entities_coverage.truncated

    def check(name: str, status: str) -> ExplorationGateCheck:
        return ExplorationGateCheck(name, status)

    checks = (
        check("no_current_intent",
              "PASS" if intent_owner.current_intent is None else "BLOCKED"),
        check("health_at_least_16", "PASS" if body.health >= 16 else "BLOCKED"),
        check("food_at_least_18", "PASS" if body.food >= 18 else "BLOCKED"),
        check("oxygen_known_positive",
              "UNKNOWN" if body.oxygen_level is None
              else "PASS" if body.oxygen_level > 0 else "BLOCKED"),
        check("world_time_observed", "UNKNOWN" if body.time is None else "PASS"),
        check("entity_coverage_complete", "UNKNOWN" if truncated else "PASS"),
        check("nearby_entities_absent",
              "BLOCKED" if body.nearby_entities
              else "UNKNOWN" if truncated else "PASS"),
    )
    return ExplorationGateAudit(
        native_session_id=probe.session_id,
        native_seq=probe.seq,
        native_request_id=probe.request_id or "",
        checks=checks,
        eligible=all(item.status == "PASS" for item in checks),
    )
