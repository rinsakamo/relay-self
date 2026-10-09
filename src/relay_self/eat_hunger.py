"""S46 low-cost Mineflayer hunger/food candidate with grounded effect check.

Only the native target-specific transport may equip and consume. The candidate
is never an Action authorization and neither an applied receipt nor food
absence is retroactively treated as successful nutrition.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from relay_self.provenance import Provenance

# One explicit controlled Minecraft food inventory, not a general nutrition API.
ALLOWED_FOODS = ("cooked_beef", "bread", "baked_potato", "apple")


class EatRejected(ValueError):
    """Stale, foreign, under-specified or physically inconclusive eating."""


class EatStatus(str, Enum):
    NOT_HUNGRY = "NOT_HUNGRY"
    CANDIDATE = "CANDIDATE"
    NO_FOOD = "NO_FOOD"


@dataclass(frozen=True, slots=True)
class EatChoice:
    status: EatStatus
    session_id: str
    probe_seq: int
    food_before: float
    item_name: str | None
    item_slot: int | None
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class EatingOutcome:
    session_id: str
    action_id: str
    food_before: float
    food_after: float
    consumed_item: str
    count_before: int
    count_after: int
    after_probe_seq: int
    provenance: Provenance


def _count(read: MineflayerObservation, name: str) -> int:
    return sum(item.count for item in read.snapshot.inventory if item.name == name)


class EatCursor:
    def __init__(self, session_id: str, *, hunger_threshold: float = 14.0):
        if (
            not isinstance(session_id, str) or not session_id
            or type(hunger_threshold) not in (int, float)
            or not 1 <= hunger_threshold <= 19
        ):
            raise EatRejected("session and bounded hunger threshold required")
        self.session_id = session_id
        self.threshold = hunger_threshold
        self._last_seq = -1

    def choose(self, probe: MineflayerObservation) -> EatChoice:
        if (
            not isinstance(probe, MineflayerObservation)
            or probe.session_id != self.session_id
            or probe.kind != "probe" or not probe.request_id
            or probe.seq <= self._last_seq
            or probe.provenance.source != "mineflayer"
            or probe.snapshot.food > 20
        ):
            raise EatRejected("fresh complete native food+inventory probe required")
        if probe.snapshot.food >= self.threshold:
            status, chosen = EatStatus.NOT_HUNGRY, None
        else:
            chosen = next(
                (item for name in ALLOWED_FOODS
                 for item in probe.snapshot.inventory
                 if item.name == name and item.count > 0),
                None,
            )
            status = EatStatus.CANDIDATE if chosen else EatStatus.NO_FOOD
        self._last_seq = probe.seq
        return EatChoice(
            status, self.session_id, probe.seq, probe.snapshot.food,
            None if chosen is None else chosen.name,
            None if chosen is None else chosen.slot, probe.provenance,
        )


def verify_eating_effect(
    before: EatChoice, before_probe: MineflayerObservation,
    equip: MineflayerEffectResult, consume: MineflayerEffectResult,
    after: MineflayerObservation,
) -> EatingOutcome:
    """No physical nutrition claim without two real applied effects + new probe."""
    if (
        not isinstance(before, EatChoice) or before.status is not EatStatus.CANDIDATE
        or not isinstance(before_probe, MineflayerObservation)
        or not isinstance(equip, MineflayerEffectResult)
        or not isinstance(consume, MineflayerEffectResult)
        or not isinstance(after, MineflayerObservation)
        or before.item_name not in ALLOWED_FOODS
        or before.probe_seq != before_probe.seq
        or before.provenance != before_probe.provenance
        or before_probe.kind != "probe" or after.kind != "probe"
        or not before_probe.request_id or not after.request_id
        or after.request_id == before_probe.request_id
        or any(x.session_id != before.session_id for x in (
            before_probe, equip, consume, after,
        ))
    ):
        raise EatRejected("typed source-linked eating receipts required")
    if (
        not before_probe.seq < equip.seq < consume.seq < after.seq
        or equip.effect != "equip_item" or consume.effect != "consume_held"
        or equip.result != "applied" or consume.result != "applied"
        or equip.action_id != consume.action_id
        or before_probe.snapshot.food != before.food_before
        or after.snapshot.food <= before.food_before
        or after.snapshot.food > 20
        or _count(after, before.item_name) >= _count(before_probe, before.item_name)
    ):
        raise EatRejected("nutrition and consumed inventory not actually observed")
    return EatingOutcome(
        before.session_id, equip.action_id, before.food_before,
        after.snapshot.food, before.item_name,
        _count(before_probe, before.item_name),
        _count(after, before.item_name), after.seq, after.provenance,
    )
