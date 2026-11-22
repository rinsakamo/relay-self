"""Historical Stage24c body-condition audit; no longer an action permit.

These predicates document why the *archived* Stage24c CPU policy removed
MOVE options. Stage24e deliberately decouples all such observations from
the standing EXPLORE_WORLD Need. Do NOT use `eligible` or `blocking_codes`
to generate candidates, reject selected Skills, or authorize motor output.
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
    """Read only the retired historical conditions; not a current gate.

    Known oxygen 0 and unknown are different observations; neither can
    suppress a Stage24e exploration Goal or predetermine physical Outcome.
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
