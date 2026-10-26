"""S51 issued native EAT: equip -> consume -> correlated World evidence.

The command stream is non-idempotent. A failed/incomplete read remains UNKNOWN
and no automatic reissue is permitted. Not a food acquisition/crafting Skill.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
    MineflayerPaperSnapshot,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.eat_hunger import (
    EatChoice,
    EatingOutcome,
    EatStatus,
)


class EatingExecutionRejected(ValueError):
    """Stale, unsupervised or physically unverified native eating."""


@dataclass(frozen=True, slots=True)
class EatingActionReceipt:
    terminal: ActionLifecycle
    outcome: EatingOutcome


def _check_eat_paper(frame, session_id):
    if (frame.session_id != session_id or frame.data["status"] != "ADMITTED"
            or frame.data["assessment"] not in {"NO_KNOWN_URGENT_SIGNAL", "LOW_FOOD"}):
        raise EatingExecutionRejected("EAT Paper monitor refused freshness/safety")


def _eat_stop_check(stop_requested_dev: Callable[[], bool] | None) -> None:
    if stop_requested_dev is None:
        return
    result = stop_requested_dev()
    if type(result) is not bool or result:
        raise EatingExecutionRejected(
            "T1i owner STOP: EAT physical completion undetermined; never retry consume"
        )


async def _eat_receive(session, stop_requested_dev: Callable[[], bool] | None):
    if stop_requested_dev is None:
        return await asyncio.wait_for(session.receive(), timeout=9)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 9
    while True:
        _eat_stop_check(stop_requested_dev)
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError("T1i native EAT receipt deadline exceeded")
        try:
            return await asyncio.wait_for(session.receive(), timeout=min(.025, remaining))
        except TimeoutError:
            _eat_stop_check(stop_requested_dev)
            if loop.time() >= deadline:
                raise


async def _expect(session, action_id: str, effect: str, *, paper_tick_dev=False,
                  stop_requested_dev: Callable[[], bool] | None = None) -> MineflayerEffectResult:
    for _ in range(100):
        frame = await _eat_receive(session, stop_requested_dev)
        if isinstance(frame, MineflayerEffectResult):
            if frame.action_id == action_id and frame.effect == effect:
                if frame.result != "applied":
                    raise EatingExecutionRejected(f"native {effect} rejected: {frame.error}")
                return frame
        elif paper_tick_dev and isinstance(frame, MineflayerPaperSnapshot):
            _check_eat_paper(frame, session.started.session_id)
        elif not isinstance(frame, MineflayerObservation):
            raise EatingExecutionRejected("source lost before EAT receipt")
    raise EatingExecutionRejected("EAT effect receipt absent")


async def _observed_after(session, request_id: str, *, paper_tick_dev=False,
                          stop_requested_dev: Callable[[], bool] | None = None) -> MineflayerObservation:
    for _ in range(100):
        frame = await _eat_receive(session, stop_requested_dev)
        if isinstance(frame, MineflayerObservation):
            if frame.kind == "probe":
                if frame.request_id != request_id:
                    raise EatingExecutionRejected("foreign after-EAT probe")
                return frame
        elif paper_tick_dev and isinstance(frame, MineflayerPaperSnapshot):
            _check_eat_paper(frame, session.started.session_id)
        else:
            raise EatingExecutionRejected("EAT source ended")
    raise EatingExecutionRejected("after-EAT probe missing")



def verify_eating_subactions(
    issued_action_id: str, choice: EatChoice, before: MineflayerObservation,
    equip: MineflayerEffectResult, consume: MineflayerEffectResult,
    after: MineflayerObservation,
) -> EatingOutcome:
    """Actual Mineflayer child effects need DIFFERENT deduped command IDs.

    S46's abstract verifier assumes one shared action_id for both effects.
    The genuine Node bridge rejects a reused command ID, so this target-
    specific refinement keeps one supervised parent Action and two distinct
    child commands, requiring native chronological receipts for both.
    """
    if (
        not isinstance(issued_action_id, str) or not issued_action_id
        or not isinstance(choice, EatChoice)
        or choice.status is not EatStatus.CANDIDATE
        or choice.item_name is None
        or not isinstance(before, MineflayerObservation)
        or not isinstance(after, MineflayerObservation)
        or not isinstance(equip, MineflayerEffectResult)
        or not isinstance(consume, MineflayerEffectResult)
        or before.kind != "probe" or after.kind != "probe"
        or not before.request_id or not after.request_id
        or before.request_id == after.request_id
        or choice.session_id != before.session_id
        or after.session_id != choice.session_id
        or equip.session_id != choice.session_id
        or consume.session_id != choice.session_id
        or before.seq != choice.probe_seq
        or before.provenance != choice.provenance
        or not before.seq < equip.seq < consume.seq < after.seq
        or equip.action_id != issued_action_id + "-equip"
        or consume.action_id != issued_action_id + "-consume"
        or equip.effect != "equip_item" or consume.effect != "consume_held"
        or equip.result != "applied" or consume.result != "applied"
        or after.snapshot.food <= choice.food_before
        or after.snapshot.food > 20
        or before.snapshot.food != choice.food_before
    ):
        raise EatingExecutionRejected("real separate equip/consume lineage unverified")
    before_item = sum(
        i.count for i in before.snapshot.inventory
        if i.name == choice.item_name
    )
    after_item = sum(
        i.count for i in after.snapshot.inventory
        if i.name == choice.item_name
    )
    if (
        before_item < 1
        or after_item >= before_item
        or not any(
            item.name == choice.item_name and item.slot == choice.item_slot
            for item in before.snapshot.inventory
        )
    ):
        raise EatingExecutionRejected(
            f"consumption not proven: item_count_before={before_item}, "
            f"item_count_after={after_item}, food_before={choice.food_before}, "
            f"food_after={after.snapshot.food}; "
            f"before_slots={[(i.name, i.count, i.slot) for i in before.snapshot.inventory]}, "
            f"after_slots={[(i.name, i.count, i.slot) for i in after.snapshot.inventory]}"
        )
    return EatingOutcome(
        session_id=choice.session_id, action_id=issued_action_id,
        food_before=choice.food_before, food_after=after.snapshot.food,
        consumed_item=choice.item_name, count_before=before_item,
        count_after=after_item, after_probe_seq=after.seq,
        provenance=after.provenance,
    )


class IssuedEatingExecutor:
    def __init__(self) -> None:
        self._attempted: set[str] = set()

    async def execute(
        self, session: MineflayerProcessSession,
        supervisor: ActionSupervisor,
        issued: ActionLifecycle,
        choice: EatChoice,
        before: MineflayerObservation,
        *, paper_tick_dev: bool = False,
        stop_requested_dev: Callable[[], bool] | None = None,
    ) -> EatingActionReceipt:
        if (
            not isinstance(session, MineflayerProcessSession)
            or not isinstance(supervisor, ActionSupervisor)
            or not isinstance(issued, ActionLifecycle)
            or not isinstance(choice, EatChoice)
            or not isinstance(before, MineflayerObservation)
            or session.process_returncode is not None
            or choice.status is not EatStatus.CANDIDATE
            or issued.state is not ActionState.ISSUED
            or not issued.is_current_snapshot
            or supervisor.get(issued.action_id) is not issued
            or supervisor.open_actions != (issued,)
            or issued.action_id in self._attempted
            or choice.session_id != session.started.session_id
            or before.session_id != choice.session_id
            or before.seq != choice.probe_seq
            or before.provenance != choice.provenance
            or choice.item_name is None
        ):
            raise EatingExecutionRejected("requires fresh issued current EAT authority")
        if type(paper_tick_dev) is not bool:
            raise EatingExecutionRejected("Paper DEV opt-in must be boolean")
        if stop_requested_dev is not None and (
            not paper_tick_dev or not callable(stop_requested_dev)
        ):
            raise EatingExecutionRejected("T1i EAT STOP requires explicit Paper DEV owner")
        # Reserve even a STOP-before-send Action; it is already ISSUED in the
        # original Supervisor and must become UNKNOWN, never remain ISSUED.
        self._attempted.add(issued.action_id)
        at_ns = (supervisor.last_at_ns or 0) + 1
        try:
            _eat_stop_check(stop_requested_dev)
            equip_id = issued.action_id + "-equip"
            consume_id = issued.action_id + "-consume"
            _eat_stop_check(stop_requested_dev)
            await session.send_equip_item(equip_id, item_name=choice.item_name)
            equip = await _expect(
                session, equip_id, "equip_item", paper_tick_dev=paper_tick_dev,
                stop_requested_dev=stop_requested_dev,
            )
            _eat_stop_check(stop_requested_dev)
            await session.send_consume_held(consume_id)
            consume = await _expect(
                session, consume_id, "consume_held", paper_tick_dev=paper_tick_dev,
                stop_requested_dev=stop_requested_dev,
            )
            _eat_stop_check(stop_requested_dev)
            # Poll new correlated observations only; NEVER repeat consume.
            # Server food/slot sync may lag behind applied consume receipt.
            last_error: EatingExecutionRejected | None = None
            for attempt in range(8):
                request_id = f"{issued.action_id}-after-eating-{attempt:02d}"
                _eat_stop_check(stop_requested_dev)
                await session.send_observe(request_id)
                after = await _observed_after(
                    session, request_id, paper_tick_dev=paper_tick_dev,
                    stop_requested_dev=stop_requested_dev,
                )
                try:
                    outcome = verify_eating_subactions(
                        issued.action_id, choice, before, equip, consume, after,
                    )
                except EatingExecutionRejected as exc:
                    last_error = exc
                    await asyncio.sleep(0.25)
                else:
                    break
            else:
                raise EatingExecutionRejected(
                    f"native food/inventory not jointly observed in "
                    f"8 correlated probes: {last_error}"
                )
            _eat_stop_check(stop_requested_dev)
            closed = supervisor.record_outcome(
                issued.action_id, at_ns=at_ns, provenance=after.provenance,
            )
            return EatingActionReceipt(closed, outcome)
        except BaseException:
            if supervisor.get(issued.action_id).state is ActionState.ISSUED:
                supervisor.mark_unknown(
                    issued.action_id, at_ns=at_ns, provenance=before.provenance,
                )
            raise
