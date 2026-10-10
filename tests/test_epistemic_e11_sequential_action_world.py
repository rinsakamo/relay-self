"""E11 source-only native avatar handoff: deterministic process doubles.

No Java, Mineflayer, localhost connection, zombie or physical action is used.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

import test_epistemic_e10_action_world as e10_fixture
from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerShutdownAck,
)
from experiments import epistemic_e11_sequential_action_world as e11
from experiments.epistemic_e11_avatar_handoff import (
    E11HandoffRejected,
    SequentialActionHandoff,
    SourceShutdown,
)
from relay_self.action import ActionState


@pytest.fixture(autouse=True)
def no_action_duration_sleep(monkeypatch):
    async def no_sleep(_duration):
        return None
    monkeypatch.setattr("adapters.mineflayer.execution.asyncio.sleep", no_sleep)


def prepared(arm="OBSERVE", price=1, *, mode="executed", fault=None):
    _subject, source_world, args = e10_fixture.prepare(
        arm=arm, price=price, mode=mode,
    )
    action_world = args["action_adapter"]
    events = []
    closes = []
    launches = []
    started = source_world.started

    async def close_source(parent):
        events.append("close")
        closes.append(parent)
        assert parent is source_world
        return SourceShutdown(
            started.session_id,
            MineflayerShutdownAck(session_id=started.session_id, seq=parent.seq),
            None, 0,
        )

    async def launch_action4():
        events.append("launch")
        launches.append(action_world)
        # It is the genuine FIRST seq1 event of the new bridge; the wrapper
        # buffers this same object without rewriting seq/identity.
        action_world.queue(replace(action_world.template, kind="spawn", request_id=None))
        return action_world

    handoff = SequentialActionHandoff(
        close_source=close_source, launch_action4=launch_action4,
    )
    args["action_adapter"] = handoff
    return source_world, action_world, args, handoff, events, closes, launches


def run(args):
    return asyncio.run(e11.run_episode(**args))


@pytest.mark.parametrize("arm,price", [
    ("OBSERVE", 1), ("CHEAP_EXACT", 1),
])
def test_deferred_real_session_boundary_is_after_authorization_before_issue(arm, price):
    world, action_world, args, handoff, events, closes, launches = prepared(arm, price)
    original_auth = args["authorize4"]
    def authorize(proposed):
        events.append("authorize")
        return original_auth(proposed)
    args["authorize4"] = authorize
    result = run(args)
    assert result.decision.selected == "MOVE_AWAY"
    assert events == ["authorize", "close", "launch"]
    assert closes == [world] and launches == [action_world]
    assert result.action4.state is ActionState.OUTCOME
    assert result.handoff is handoff.receipt
    assert result.handoff.source_session_id == world.started.session_id
    assert result.handoff.action_session_id == action_world.started.session_id
    assert result.handoff.action_spawn_seq == 1
    assert result.handoff.position_delta_m == pytest.approx(0)
    assert result.handoff.physically_authenticated is False
    assert result.physically_authenticated is False
    assert result.handoff.same_declared_avatar is True
    assert result.native_frames[2].request_id is not None  # second source probe
    assert any(x.seq == 1 and x.kind == "spawn"
               for x in result.native_frames if isinstance(x, MineflayerObservation))
    assert action_world.commands == [
        ("set_control", "e10:action4"), ("clear_controls", "e10:action4-s15-clear"),
    ]
    with pytest.raises(E11HandoffRejected, match="consumed"):
        asyncio.run(handoff.acquire_after_policy(None, None))


@pytest.mark.parametrize("arm,price", [
    ("NO_OBSERVE", 1), ("CHEAP_EXACT", 4),
])
def test_wait_never_reconnects_or_authorizes_or_issues(arm, price):
    world, action_world, args, handoff, events, _, _ = prepared(arm, price)
    args["authorize4"] = lambda _: pytest.fail("WAIT called authority")
    result = run(args)
    assert result.action4 is None and result.handoff is None
    assert result.physically_authenticated is False
    assert events == [] and handoff.receipt is None
    assert world.observes == ["e10:evaluator"]
    assert action_world.commands == []


def test_denied_action_never_disconnects_or_starts_new_bridge():
    _, action_world, args, _, events, _, _ = prepared()
    args["authorize4"] = lambda p: p.deny(
        at_ns=101, provenance=e10_fixture.P, authority="deny",
    )
    with pytest.raises(e11.E11Rejected, match="denied"):
        run(args)
    assert events == [] and action_world.commands == []


@pytest.mark.parametrize("fault", [
    "no-ack", "wrong-ack-session", "bad-exit", "wrong-config",
    "same-session", "bad-spawn-seq", "bad-spawn-position", "missing-spawn",
])
def test_handoff_identity_and_native_source_anomalies_fail_closed(fault):
    world, action_world, args, handoff, events, _, _ = prepared()
    def replace_close():
        async def bad_close(parent):
            events.append("close")
            ack = MineflayerShutdownAck(
                session_id="alien" if fault == "wrong-ack-session"
                else world.started.session_id, seq=world.seq,
            )
            return SourceShutdown(
                parent.started.session_id, ack if fault != "no-ack" else None,
                None, 42 if fault == "bad-exit" else 0,
            )
        handoff._close_source = bad_close
    if fault in ("no-ack", "wrong-ack-session", "bad-exit"):
        replace_close()
    else:
        async def bad_launch():
            events.append("launch")
            if fault == "wrong-config":
                action_world.started = replace(action_world.started, config=replace(
                    action_world.started.config, username="foreign-user",
                ))
            if fault == "same-session":
                action_world.started = replace(
                    action_world.started, session_id=world.started.session_id,
                )
            if fault != "missing-spawn":
                sample = replace(action_world.template, kind="spawn", request_id=None)
                if fault == "bad-spawn-position":
                    sample = replace(sample, snapshot=replace(
                        sample.snapshot, position=replace(
                            sample.snapshot.position, x=sample.snapshot.position.x + 0.05,
                        ),
                    ))
                action_world.queue(sample)
                if fault == "bad-spawn-seq":
                    sample = action_world.frames.pop()
                    action_world.frames.append(replace(sample, seq=2))
            return action_world
        handoff._launch_action4 = bad_launch
    with pytest.raises((E11HandoffRejected, e11.E11Rejected, ValueError, EOFError)):
        run(args)
    assert action_world.commands == []


def test_handoff_shutdown_and_second_source_are_not_cryptographic_attestation():
    _, _, args, handoff, _, _, _ = prepared()
    result = run(args)
    assert result.handoff.physically_authenticated is False
    assert result.physically_authenticated is False
    assert result.native_frames[-1].session_id == result.handoff.action_session_id
    assert any(isinstance(f, MineflayerShutdownAck) and f.session_id ==
               result.handoff.source_session_id for f in result.native_frames)


def test_e11_has_same_base_offline_action_world_semantics():
    _, _, args, _, _, _, _ = prepared(mode="unavailable")
    result = run(args)
    assert result.action4.state is ActionState.TIMEOUT
    assert result.interpretation4.disposition.value == "unavailable"
    assert result.handoff.physically_authenticated is False
