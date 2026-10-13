"""S-owned B0 native EAT outcome -> unchanged M0 simulated-energy bridge.

No Action authorization or World attestation originates here. Pickup != EAT.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from adapters.mineflayer.b0_ground_foraging import (
    GroundRejected,
    GroundTarget,
    select_ground_target,
)
from adapters.mineflayer.eat_execution import EatingActionReceipt
from adapters.mineflayer.python_protocol import MineflayerObservation
from experiments.metabolism_viability import (
    BodyState,
    EnergyTransition,
    Interoception,
    MetabolismConfig,
    initial_body,
    metabolism_step,
    observe_energy,
)
from relay_self.action import ActionState
from relay_self.eat_hunger import ALLOWED_FOODS, EatChoice, EatCursor, EatStatus


class B0EnergyRejected(ValueError):
    """Untrusted World evidence, replay, or irreversible starvation."""


@dataclass(frozen=True)
class B0Decision:
    kind: Literal["WAIT", "SEEK", "EAT"]
    probe_seq: int
    sensor_reading: float
    body_tick: int
    eat_choice: EatChoice | None = None
    ground_target: GroundTarget | None = None


class B0EnergyLedger:
    """Session-scoped owner; only verified S51 EAT may mint one food unit."""

    def __init__(
        self,
        session_id: str,
        *,
        config: MetabolismConfig | None = None,
        sensor: Interoception | None = None,
    ) -> None:
        if not isinstance(session_id, str) or not session_id:
            raise B0EnergyRejected("nonempty session required")
        self.session_id = session_id
        self.config = config if config is not None else MetabolismConfig()
        self.sensor = sensor if sensor is not None else Interoception()
        self.body: BodyState = initial_body(self.config)
        self._credits: set[str] = set()
        self._last_eat_seq = -1
        self._last_decision_seq = -1

    @property
    def credit_count(self) -> int:
        return len(self._credits)

    def step(
        self, action: Literal["WAIT", "MOVE"], *,
        eating: EatingActionReceipt | None = None,
    ) -> EnergyTransition:
        if action not in ("WAIT", "MOVE") or self.body.terminal:
            raise B0EnergyRejected("unsupported step or terminal body")
        units = 0
        if eating is not None:
            if not isinstance(eating, EatingActionReceipt):
                raise B0EnergyRejected("typed issued S51 receipt required")
            terminal, outcome = eating.terminal, eating.outcome
            if (
                action != "WAIT"
                or terminal.state is not ActionState.OUTCOME
                or terminal.action_id != outcome.action_id
                or not outcome.action_id
                or outcome.action_id in self._credits
                or outcome.session_id != self.session_id
                or outcome.provenance.source != "mineflayer"
                or outcome.consumed_item not in ALLOWED_FOODS
                or outcome.count_before - outcome.count_after != 1
                or outcome.count_after < 0
                or not 0 <= outcome.food_before < outcome.food_after <= 20
                or outcome.after_probe_seq <= self._last_eat_seq
                or outcome.after_probe_seq <= self._last_decision_seq
            ):
                raise B0EnergyRejected("unverified/replayed native EAT")
            units = 1
        result = metabolism_step(
            self.body, action=action,
            consumed_food_units=units, config=self.config,
        )
        self.body = result.after
        if eating is not None:
            self._credits.add(eating.outcome.action_id)
            self._last_eat_seq = eating.outcome.after_probe_seq
        return result

    def decide(self, probe: MineflayerObservation) -> B0Decision:
        """Designed cheap L0 tropism, not an emergent instinct."""
        if (
            self.body.terminal
            or not isinstance(probe, MineflayerObservation)
            or probe.session_id != self.session_id
            or probe.kind != "probe" or not probe.request_id
            or probe.provenance.source != "mineflayer"
            or probe.seq <= self._last_eat_seq
            or probe.seq <= self._last_decision_seq
        ):
            raise B0EnergyRejected("requires living body + fresh World probe")
        choice = EatCursor(self.session_id).choose(probe)
        kind: Literal["WAIT", "SEEK", "EAT"] = "WAIT"
        target = None
        if choice.status is EatStatus.CANDIDATE:
            kind = "EAT"
        elif choice.status is EatStatus.NO_FOOD:
            try:
                target = select_ground_target(probe)
            except GroundRejected:
                pass
            else:
                kind = "SEEK"
        sensor = observe_energy(self.body, self.sensor)
        self._last_decision_seq = probe.seq
        return B0Decision(
            kind, probe.seq, sensor.reading, self.body.tick,
            choice if kind == "EAT" else None, target,
        )
