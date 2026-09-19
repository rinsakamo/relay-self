import asyncio

import pytest

from adapters.mineflayer.qualify_live import (
    MineflayerQualificationError,
    qualify_mineflayer_session,
)
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_VERSION,
    MineflayerAdapterStarted,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)


def snapshot(x: float) -> MineflayerSnapshot:
    return MineflayerSnapshot(
        health=20,
        food=18,
        oxygen_level=20,
        position=MineflayerPosition(x=x, y=64, z=0),
        time=None,
        inventory=(),
        nearby_entities=(),
    )


def observation(seq: int, kind: str, x: float) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="session-live",
        seq=seq,
        kind=kind,
        snapshot=snapshot(x),
    )


def effect_result(
    seq: int,
    *,
    action_id: str,
    effect: str,
    result: str = "applied",
    error: str | None = None,
) -> MineflayerEffectResult:
    return MineflayerEffectResult(
        session_id="session-live",
        seq=seq,
        action_id=action_id,
        effect=effect,
        result=result,
        error=error,
    )


class FakeLiveSession:
    def __init__(self, messages: list[object]) -> None:
        self.started = MineflayerAdapterStarted(
            session_id="session-live",
            seq=0,
            mineflayer_version=MINEFLAYER_VERSION,
            config=MineflayerLaunchConfig(),
        )
        self._messages = list(messages)
        self.sent: list[tuple[object, ...]] = []

    async def receive(self):
        if not self._messages:
            return MineflayerConnectionEnd(
                session_id="session-live",
                seq=999,
                reason="fixture exhausted",
            )
        return self._messages.pop(0)

    async def send_set_control(
        self,
        action_id: str,
        *,
        control: str,
        state: bool,
    ) -> None:
        self.sent.append(("set_control", action_id, control, state))

    async def send_clear_controls(self, action_id: str) -> None:
        self.sent.append(("clear_controls", action_id))

    async def shutdown(self, *, timeout_s: float = 5.0) -> int:
        self.sent.append(("shutdown", timeout_s))
        return 0


def test_qualification_requires_action_outcome_and_actual_position_delta() -> None:
    session = FakeLiveSession(
        [
            observation(1, "spawn", 0.0),
            effect_result(
                2,
                action_id="action-live-forward",
                effect="set_control",
            ),
            observation(3, "move", 0.2),
            effect_result(
                4,
                action_id="action-live-stop",
                effect="clear_controls",
            ),
        ]
    )

    report = asyncio.run(
        qualify_mineflayer_session(
            session,
            evidence_timeout_s=1.0,
            action_timeout_s=1.0,
            minimum_movement_distance=0.05,
        )
    )

    assert report.qualified is True
    assert report.session_id == "session-live"
    assert report.movement_distance == pytest.approx(0.2)
    assert report.spawn_health == 20
    assert report.spawn_food == 18
    assert report.forward_action_state == "outcome"
    assert report.stop_action_state == "outcome"
    assert report.skill_state == "started"
    assert report.intent_id == "intent-live-qualification"
    assert report.observed_kinds == ("spawn", "move")
    assert session.sent == [
        ("set_control", "action-live-forward", "forward", True),
        ("clear_controls", "action-live-stop"),
    ]


def test_applied_control_without_observed_movement_does_not_qualify() -> None:
    session = FakeLiveSession(
        [
            observation(1, "spawn", 0.0),
            effect_result(
                2,
                action_id="action-live-forward",
                effect="set_control",
            ),
            observation(3, "move", 0.0),
            MineflayerConnectionEnd(
                session_id="session-live",
                seq=4,
                reason="fixture stop",
            ),
        ]
    )

    with pytest.raises(
        MineflayerQualificationError,
        match="connection ended",
    ):
        asyncio.run(
            qualify_mineflayer_session(
                session,
                evidence_timeout_s=1.0,
                action_timeout_s=1.0,
                minimum_movement_distance=0.05,
            )
        )


def test_rejected_forward_effect_does_not_qualify() -> None:
    session = FakeLiveSession(
        [
            observation(1, "spawn", 0.0),
            effect_result(
                2,
                action_id="action-live-forward",
                effect="set_control",
                result="rejected",
                error="not_spawned",
            ),
        ]
    )

    with pytest.raises(
        MineflayerQualificationError,
        match="forward control was rejected",
    ):
        asyncio.run(
            qualify_mineflayer_session(
                session,
                evidence_timeout_s=1.0,
                action_timeout_s=1.0,
            )
        )
