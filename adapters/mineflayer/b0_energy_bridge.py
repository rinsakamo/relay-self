"""S-owned B0 native EAT outcome -> unchanged M0 simulated-energy bridge.

No Action authorization or World attestation originates here. Pickup != EAT.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

from adapters.mineflayer.b0_ground_foraging import (
    GroundRejected,
    GroundTarget,
    select_ground_target,
)
from adapters.mineflayer.eat_execution import EatingActionReceipt
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.self_action_evidence import (
    verify_native_action_evidence,
)
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



@dataclass(frozen=True, slots=True)
class DashM0InvoiceDev:
    """Source-joined, P1-replayed Paper callback charge. DEV, not R-attested."""

    session_id: str
    action_id: str
    first_world_tick: int
    last_world_tick: int
    observed_world_ticks: int
    boost_ticks: int
    charge: float
    source_scope: str = "PAPER_P1_CALLBACK_S49_SOURCE_JOIN_DEV_ONLY"


@dataclass(frozen=True, slots=True)
class DashM0DebitDev:
    """Mutation of the *existing B0 ledger* after original native OUTCOME."""

    action_id: str
    session_id: str
    energy_before: float
    energy_after: float
    posted_extra: float
    m0_tick_before: int
    m0_tick_after: int
    world_first_tick: int
    world_last_tick: int
    world_ticks: int
    source_scope: str = "PRODUCER_LOCAL_DEV_NOT_INDEPENDENTLY_ATTESTED"


class B0EnergyLedger:
    """Session-scoped owner; only verified S51 EAT may mint one food unit."""

    def __init__(
        self,
        session_id: str,
        *,
        config: MetabolismConfig | None = None,
        sensor: Interoception | None = None,
        forage_policy: Literal["native_only", "sensor_gate", "no_ground_seek"] = "native_only",
        dev_dash_extra_debit: bool = False,
    ) -> None:
        if type(dev_dash_extra_debit) is not bool:
            raise B0EnergyRejected("DEV DASH debit gate must be boolean")
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
        self._dev_dash_extra_debit = dev_dash_extra_debit
        self._dev_dash_debited_actions: set[str] = set()
        self._dev_dash_last_world_tick: int | None = None
        self._last_eat_seq = -1
        self._last_decision_seq = -1

    @property
    def credit_count(self) -> int:
        return len(self._credits)

    def post_dash_extra_dev(
        self, receipt: NormalActionReceipt, invoice: DashM0InvoiceDev,
        *, native_evidence: dict,
    ) -> DashM0DebitDev:
        """Original S49-ledger owner posts DASH *extra* only after S16 OUTCOME.

        This is ONE M0 transaction for all Paper ticks (not fabricated basal
        transitions for 13 Paper ticks). It cannot mint EAT energy, bypass
        terminal state, or replay an Action/tick. The source is producer-local
        Paper and remains unqualified even when all receipts join.
        """
        if (
            not self._dev_dash_extra_debit
            or not isinstance(receipt, NormalActionReceipt)
            or not isinstance(invoice, DashM0InvoiceDev)
            or receipt.terminal.state is not ActionState.OUTCOME
            or receipt.terminal.action_id != invoice.action_id
            or receipt.consequence.action_id != invoice.action_id
            or receipt.consequence.session_id != self.session_id
            or receipt.consequence.status is not WorldConsequenceStatus.EXECUTED
            or receipt.consequence.movement_distance is None
            or receipt.consequence.movement_distance <= 0.05
            or invoice.session_id != self.session_id
            or not isinstance(invoice.action_id, str) or not invoice.action_id
            or invoice.action_id in self._dev_dash_debited_actions
            or type(invoice.first_world_tick) is not int
            or type(invoice.last_world_tick) is not int
            or type(invoice.observed_world_ticks) is not int
            or not 1 <= invoice.observed_world_ticks <= 80
            or invoice.first_world_tick < 0
            or invoice.last_world_tick != invoice.first_world_tick
                + invoice.observed_world_ticks - 1
            or type(invoice.boost_ticks) is not int
            or not 1 <= invoice.boost_ticks <= invoice.observed_world_ticks
            or type(invoice.charge) not in (int, float)
            or not math.isfinite(invoice.charge)
            or not 0 < invoice.charge <=
                0.20 * 0.05 * invoice.observed_world_ticks + 1e-10
            or invoice.source_scope != "PAPER_P1_CALLBACK_S49_SOURCE_JOIN_DEV_ONLY"
            or self.body.terminal or self.body.energy <= invoice.charge
            or (self._dev_dash_last_world_tick is not None
                and invoice.first_world_tick <= self._dev_dash_last_world_tick)
            or type(native_evidence) is not dict
        ):
            raise B0EnergyRejected("DASH extra source/ownership/energy debit denied")
        verify_native_action_evidence(
            native_evidence, action_id=invoice.action_id,
            session_id=self.session_id,
            movement_m=receipt.consequence.movement_distance,
            allow_dev_forward=True, allow_dev_sprint=True,
        )
        before = self.body
        after = replace(
            before,
            energy=before.energy - invoice.charge,
            tick=before.tick + 1,
        )
        # Atomic local owner mutation ONLY after all native and Paper review.
        self.body = after
        self._dev_dash_debited_actions.add(invoice.action_id)
        self._dev_dash_last_world_tick = invoice.last_world_tick
        return DashM0DebitDev(
            invoice.action_id, self.session_id, before.energy, after.energy,
            invoice.charge, before.tick, after.tick,
            invoice.first_world_tick, invoice.last_world_tick,
            invoice.observed_world_ticks,
        )

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
