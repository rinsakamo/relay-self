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

B0_SENSOR_SEEK_THRESHOLD = 8.0


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
        forage_policy: Literal["native_only", "sensor_gate", "no_ground_seek"] = "native_only",
    ) -> None:
        if not isinstance(session_id, str) or not session_id:
            raise B0EnergyRejected("nonempty session required")
        if forage_policy not in ("native_only", "sensor_gate", "no_ground_seek"):
            raise B0EnergyRejected("unsupported explicit L0 forage policy")
        if sensor is not None and not isinstance(sensor, Interoception):
            raise B0EnergyRejected("M0 interoception projection required")
        self.session_id = session_id
        self.config = config if config is not None else MetabolismConfig()
        self.sensor = sensor if sensor is not None else Interoception()
        self.forage_policy = forage_policy
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
        # Only the M0 sensor projection enters the optional decision gate.
        # True body energy remains inside M0 and terminal safety is unchanged.
        sensor = observe_energy(self.body, self.sensor)
        kind: Literal["WAIT", "SEEK", "EAT"] = "WAIT"
        target = None
        if choice.status is EatStatus.CANDIDATE:
            kind = "EAT"  # native edible inventory remains available for both arms
        elif choice.status is EatStatus.NO_FOOD:
            try:
                candidate = select_ground_target(probe)
            except GroundRejected:
                pass
            else:
                # The native-only cheap baseline preserves all prior B0 behavior.
                # In the opt-in arm, low *observed* energy admits SEEK; a
                # sensor masked to a fixed high value does not. The strictly
                # opt-in no_ground_seek reference never issues a ground SEEK,
                # but retains native inventory EAT and terminal safety.
                # This is intentionally hand-coded, NOT learned motivation.
                if (
                    self.forage_policy == "native_only"
                    or (
                        self.forage_policy == "sensor_gate"
                        and sensor.reading <= B0_SENSOR_SEEK_THRESHOLD
                    )
                ):
                    target = candidate
                    kind = "SEEK"
        self._last_decision_seq = probe.seq
        return B0Decision(
            kind, probe.seq, sensor.reading, self.body.tick,
            choice if kind == "EAT" else None, target,
        )


def nofood_native_wait(
    ledger: B0EnergyLedger, probe: MineflayerObservation,
) -> tuple[B0Decision, EnergyTransition]:
    """One source-qualified food-free decision/tick, never a fake S16 Action.

    This witnesses the M0 *experimental* metabolism, not Minecraft HP death
    or physiological elapsed-time energy expenditure.
    """
    if not isinstance(ledger, B0EnergyLedger):
        raise B0EnergyRejected("B0 body owner required")
    if not isinstance(probe, MineflayerObservation):
        raise B0EnergyRejected("typed native no-food probe required")
    coverage = probe.snapshot.nearby_entities_coverage
    if (
        ledger.credit_count != 0 or ledger.body.meals != 0
        or coverage.truncated
        or coverage.candidate_count != len(probe.snapshot.nearby_entities)
        or any(item.count > 0 for item in probe.snapshot.inventory)
        or any(entity.name == "item" for entity in probe.snapshot.nearby_entities)
    ):
        raise B0EnergyRejected("no-food source, coverage or body not clean")
    decision = ledger.decide(probe)
    if decision.kind != "WAIT":
        raise B0EnergyRejected("no-food L0 did not choose nonissued WAIT")
    transition = ledger.step("WAIT")
    if (
        transition.intake != 0
        or transition.expenditure != ledger.config.basal_cost
        or ledger.credit_count != 0
        or ledger.body.meals != 0
    ):
        raise B0EnergyRejected("no-food M0 charged unexpected food or action")
    return decision, transition


def verify_starvation_reentry_denied(
    ledger: B0EnergyLedger, probe: MineflayerObservation,
) -> None:
    """Use a NEW correlated World observation to prove terminal non-reentry.

    Both L0 selection and M0 advancement must reject, without state change.
    No Action is proposed or issued here.
    """
    if (
        not isinstance(ledger, B0EnergyLedger)
        or not ledger.body.terminal or ledger.body.energy != 0
        or ledger.credit_count != 0 or ledger.body.meals != 0
        or not isinstance(probe, MineflayerObservation)
        or probe.kind != "probe" or not probe.request_id
        or probe.session_id != ledger.session_id
        or probe.provenance.source != "mineflayer"
        or probe.seq <= ledger._last_decision_seq
    ):
        raise B0EnergyRejected("no qualified post-terminal World observation")
    original = ledger.body
    try:
        ledger.decide(probe)
    except B0EnergyRejected:
        pass
    else:
        raise B0EnergyRejected("dead L0 wrongly admitted a new decision")
    try:
        ledger.step("WAIT")
    except B0EnergyRejected:
        pass
    else:
        raise B0EnergyRejected("terminal M0 body advanced again")
    if ledger.body != original:
        raise B0EnergyRejected("terminal body mutated during denied re-entry")
