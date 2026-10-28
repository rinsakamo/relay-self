"""Original L1 native decoder + T1f Paper/T2 single-reader DEV negatives."""
import asyncio
import json
from types import SimpleNamespace as NS

import pytest

from adapters.mineflayer.process_session import (
    MineflayerProcessIOError,
    MineflayerProcessSession,
)
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerPaperSnapshot,
    parse_mineflayer_line,
)


def paper(data):
    return json.dumps({
        "type": "paper_snapshot", "session_id": "native-session",
        "seq": 4, "data": data,
    })


def test_paper_schema_routes_to_original_t1f_validator(monkeypatch):
    from adapters.mineflayer import t1f_protocol

    observed = []
    monkeypatch.setattr(t1f_protocol, "validate_result", lambda d: observed.append(d))
    data = {"snapshot": {"index": 3}}
    message = parse_mineflayer_line(paper(data))
    assert isinstance(message, MineflayerPaperSnapshot)
    assert message.paper_sample_index == 3
    assert observed == [data]
    with pytest.raises(MineflayerAdapterProtocolError):
        parse_mineflayer_line(json.dumps({
            "type": "paper_snapshot", "session_id": "native-session",
            "seq": 4, "data": data, "qualified": True,
        }))


def test_invalid_source_cannot_mint_paper_snapshot():
    with pytest.raises(MineflayerAdapterProtocolError):
        parse_mineflayer_line(paper({
            "snapshot": {"index": 1},
            "status": "ADMITTED",
            "qualification": False,
        }))


def session_fixture():
    session = object.__new__(MineflayerProcessSession)
    session._started = NS(session_id="native-session")
    session._l1_t2_owner_dev = None
    return session


def owner_fixture(session_id="native-session"):
    calls = []
    owner = NS(
        session_id=session_id, previous=None, fatigue=None, failed=False,
        observe=lambda frame: calls.append(frame),
    )
    return owner, calls


def test_only_explicit_single_live_same_session_t2_owner(monkeypatch):
    session = session_fixture()
    owner, _ = owner_fixture()
    with pytest.raises(MineflayerProcessIOError):
        session.bind_l1_t2_owner_dev(owner)
    monkeypatch.setenv("S49_L1_T2_CHANNEL_DEV_ONLY", "1")
    wrong, _ = owner_fixture("other-session")
    with pytest.raises(MineflayerProcessIOError):
        session.bind_l1_t2_owner_dev(wrong)
    session.bind_l1_t2_owner_dev(owner)
    assert session._l1_t2_owner_dev is owner
    with pytest.raises(MineflayerProcessIOError):
        session.bind_l1_t2_owner_dev(owner)


def test_same_existing_receive_dispatches_once_and_preserves_message(monkeypatch):
    from adapters.mineflayer import t1f_protocol
    monkeypatch.setattr(t1f_protocol, "validate_result", lambda _: None)
    msg = parse_mineflayer_line(paper({"snapshot": {"index": 3}}))
    session = session_fixture()
    owner, calls = owner_fixture()
    monkeypatch.setenv("S49_L1_T2_CHANNEL_DEV_ONLY", "1")
    session.bind_l1_t2_owner_dev(owner)

    class Stream:
        async def readline(self):
            return b"existing sole native stream line"

    session._process = NS(stdout=Stream(), returncode=None)
    session._raw_capture = None
    session._decoder = NS(decode=lambda _: msg)
    observed = asyncio.run(session.receive())
    assert observed is msg
    assert calls == [msg]


def test_failed_owner_observation_latches_and_refuses_source(monkeypatch):
    from adapters.mineflayer import t1f_protocol
    monkeypatch.setattr(t1f_protocol, "validate_result", lambda _: None)
    msg = parse_mineflayer_line(paper({"snapshot": {"index": 3}}))
    session = session_fixture()
    monkeypatch.setenv("S49_L1_T2_CHANNEL_DEV_ONLY", "1")
    owner, _ = owner_fixture()
    def reject(_):
        raise ValueError("non-consecutive Paper")
    owner.observe = reject
    session.bind_l1_t2_owner_dev(owner)

    class Stream:
        async def readline(self):
            return b"source"

    session._process = NS(stdout=Stream(), returncode=None)
    session._raw_capture = None
    session._decoder = NS(decode=lambda _: msg)
    with pytest.raises(ValueError, match="non-consecutive"):
        asyncio.run(session.receive())
    assert owner.failed


def test_t2_owner_import_reuses_single_original_p1():
    from adapters.mineflayer.t2_tick_accounting import TickAccounting
    from experiments.fatigue_p1 import FatigueProfile
    from experiments.p1_gait_dev import GaitTickDev

    ledger = TickAccounting("native-session")
    assert isinstance(ledger.profile, FatigueProfile)
    assert ledger.fatigue is None and ledger.previous is None
    assert GaitTickDev.__name__ == "GaitTickDev"
