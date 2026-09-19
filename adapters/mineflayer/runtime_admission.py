from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from adapters.mineflayer.python_protocol import (
    MineflayerDecodedMessage,
    MineflayerEffectResult,
    MineflayerObservation,
)
from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.runtime_coordination import (
    DecisionEpochResult,
    coordinate_decision_epoch,
)

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")

_MATERIAL_OBSERVATION_KINDS = frozenset(
    {"spawn", "health", "forcedMove", "death", "respawn"}
)


@dataclass(frozen=True, slots=True)
class MineflayerEpochResult(Generic[ResponseT]):
    """Target-local trace for one admitted Mineflayer decision epoch."""

    message: MineflayerDecodedMessage
    action_closure: ActionLifecycle | None
    decision_epoch: DecisionEpochResult[ResponseT]


def mineflayer_message_requires_epoch(message: MineflayerDecodedMessage) -> bool:
    """Return the first bounded adapter-local admission decision.

    A primitive effect result is material because it can close one issued
    RelaySelf Action. The selected observations represent low-frequency
    body/session changes that may alter Present. Ordinary Mineflayer move
    events are intentionally not admitted automatically because they are a
    high-frequency controller signal rather than a requirement for high-level
    cognition on every movement update.
    """

    if isinstance(message, MineflayerEffectResult):
        return True
    if isinstance(message, MineflayerObservation):
        return message.kind in _MATERIAL_OBSERVATION_KINDS
    return False


def coordinate_mineflayer_message(
    message: MineflayerDecodedMessage,
    supervisor: ActionSupervisor,
    *,
    at_ns: int,
    decision_step: (
        Callable[[MineflayerDecodedMessage, ActionLifecycle | None], RequestT | None]
        | None
    ) = None,
    relay_engine: Callable[[RequestT], ResponseT] | None = None,
) -> MineflayerEpochResult[ResponseT] | None:
    """Admit one concrete Mineflayer message into the canonical coordinator.

    Target-native effect results close the matching primitive Action as a known
    OUTCOME before the admitted decision epoch. OUTCOME means a known target
    result, not Skill success: an applied and a rejected Mineflayer effect are
    both externally known results whose interpretation remains above the Action
    lifecycle.

    Other admitted observations do not mutate Action state directly. The
    canonical RelaySelf coordinator still owns the ordering of due Action
    supervision before caller-owned deterministic/reprojection work and any
    optional cognition request.

    Non-admitted messages return None without touching owner-local runtime
    state. This function does not create a generic event type, own Present,
    select a Skill, change Current Intent, or define a RelayEngine request
    schema.
    """

    if not mineflayer_message_requires_epoch(message):
        return None

    action_closure: ActionLifecycle | None = None
    if isinstance(message, MineflayerEffectResult):
        action_closure = supervisor.record_outcome(
            message.action_id,
            at_ns=at_ns,
            provenance=message.provenance,
        )

    def run_decision_step() -> RequestT | None:
        if decision_step is None:
            return None
        return decision_step(message, action_closure)

    epoch = coordinate_decision_epoch(
        supervisor,
        at_ns=at_ns,
        provenance=message.provenance,
        decision_step=run_decision_step,
        relay_engine=relay_engine,
    )
    return MineflayerEpochResult(
        message=message,
        action_closure=action_closure,
        decision_epoch=epoch,
    )
