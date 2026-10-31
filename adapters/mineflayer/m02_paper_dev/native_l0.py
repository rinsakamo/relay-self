"""Paper-native L0 food decision without any M0/M0.1 virtual energy ledger.

This is a cheap designed reflex policy, not a new Action owner, a learned
preference or proof that Paper's survival physiology is ecologically calibrated.
It only interprets fresh Mineflayer observations; S50/S51 own every Action.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from adapters.mineflayer.b0_ground_foraging import (
    GroundRejected,
    GroundTarget,
    select_ground_target,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.eat_hunger import EatChoice, EatCursor, EatStatus


class PaperL0Rejected(ValueError):
    """Paper L0 requires an authentic fresh session-scoped World probe."""


@dataclass(frozen=True, slots=True)
class PaperL0Decision:
    kind: Literal["WAIT", "SEEK", "EAT"]
    session_id: str
    probe_seq: int
    world_food: float
    eat_choice: EatChoice | None = None
    ground_target: GroundTarget | None = None


class PaperNativeL0:
    """Session-local native hunger policy. No synthetic body/credit/tick."""

    def __init__(self, session_id: str, *, hunger_threshold: float = 14.0) -> None:
        self._eat = EatCursor(session_id, hunger_threshold=hunger_threshold)
        self.session_id = self._eat.session_id

    def decide(self, probe: MineflayerObservation) -> PaperL0Decision:
        if (
            not isinstance(probe, MineflayerObservation)
            or probe.session_id != self.session_id
            or probe.kind != "probe"
            or not probe.request_id
            or probe.provenance.source != "mineflayer"
            or probe.snapshot.food > 20
        ):
            raise PaperL0Rejected("fresh authentic native Paper observation required")
        # EatCursor enforces strictly increasing native seq even when WAIT.
        choice = self._eat.choose(probe)
        if choice.status is EatStatus.CANDIDATE:
            return PaperL0Decision(
                "EAT", probe.session_id, probe.seq, probe.snapshot.food,
                eat_choice=choice,
            )
        if choice.status is EatStatus.NO_FOOD:
            try:
                target = select_ground_target(probe)
            except GroundRejected:
                pass
            else:
                return PaperL0Decision(
                    "SEEK", probe.session_id, probe.seq, probe.snapshot.food,
                    ground_target=target,
                )
        return PaperL0Decision("WAIT", probe.session_id, probe.seq, probe.snapshot.food)
