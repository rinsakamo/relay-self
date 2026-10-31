"""L22 runtime probes: local fake stream, no Minecraft/Java/LLM."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_l15_s49_original_goal_preflight as l15
from adapters.mineflayer.l22_post_s16_settling import inspect_l22_settling
from adapters.mineflayer.l22_runtime_settling import (
    L22RuntimeRejected,
    observe_bounded_settling,
)
from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
from test_l16_s49_first_action_original_capture import fixture as l16_fixture
from test_l22_post_s16_settling import archived_run2


class FakeSoleReader:
    def __init__(self, *, session_id, base, moves=(), drifting=False, foreign=False):
        self.started = SimpleNamespace(session_id=session_id)
        self.base = base
        self.moves = set(moves)
        self.drifting = drifting
        self.foreign = foreign
        self.sent = []
        self.pending = []
        self.seq = 100

    async def send_observe(self, request_id):
        i = len(self.sent) + 1
        self.sent.append(request_id)
        if i in self.moves:
            self.pending.append(replace(
                self.base, seq=self.seq, kind="move", request_id=None,
            ))
            self.seq += 1
        pos = self.base.snapshot.position
        if self.drifting:
            pos = replace(pos, x=pos.x + i * 0.2)
        probe = replace(
            self.base, seq=self.seq, kind="probe",
            request_id="foreign" if self.foreign else request_id,
            snapshot=replace(self.base.snapshot, position=pos),
        )
        self.seq += 1
        self.pending.append(probe)

    async def receive(self):
        if not self.pending:
            raise EOFError("no source response")
        return self.pending.pop(0)


def fake_source(**kwargs):
    orig = l16_fixture()
    decoder = MineflayerStreamDecoder()
    frames = [
        decoder.decode(line.decode())
        for line in orig["received_original"].splitlines(keepends=True)
    ]
    return FakeSoleReader(
        session_id=orig["session_id"], base=frames[-1], **kwargs,
    ), orig


@pytest.mark.parametrize(("moving", "drifting", "status"), [
    ((), False, "QUIET_SAMPLES_ONLY"),
    ((1, 2, 3, 4, 5, 6), False, "UNDETERMINED"),
    ((), True, "UNDETERMINED"),
])
def test_bounded_live_observer_never_admits_goal(monkeypatch, moving, drifting, status):
    async def immediate(_secs):
        return None
    monkeypatch.setattr(
        "adapters.mineflayer.l22_runtime_settling.asyncio.sleep", immediate,
    )
    session, orig = fake_source(moves=moving, drifting=drifting)
    window = asyncio.run(observe_bounded_settling(
        session, session_id=orig["session_id"],
        action_id=orig["action_id"], max_probes=6,
    ))
    assert window.window_status == status
    assert 3 <= len(session.sent) <= 6
    assert window.request_ids == tuple(session.sent)
    assert window.accepted_goal_status == "UNDETERMINED"
    assert not window.stable_world_ticks_attested
    assert window.qualified_real_learning_pairs == 0
    if moving:
        assert len(window.observed_move_seqs) == 6
    if drifting:
        assert window.quiet_streak == 1


@pytest.mark.parametrize("fault", ["foreign", "wrong_session", "bad_count"])
def test_runtime_rejects_foreign_or_invalid_optin(monkeypatch, fault):
    async def immediate(_secs):
        return None
    monkeypatch.setattr(
        "adapters.mineflayer.l22_runtime_settling.asyncio.sleep", immediate,
    )
    session, orig = fake_source(foreign=fault == "foreign")
    kwargs = dict(
        session_id="unknown" if fault == "wrong_session" else orig["session_id"],
        action_id=orig["action_id"],
        max_probes=9 if fault == "bad_count" else 6,
    )
    with pytest.raises(L22RuntimeRejected):
        asyncio.run(observe_bounded_settling(session, **kwargs))


def test_s7_sole_original_accepts_only_bounded_settling_prefix():
    args = archived_run2()
    rows = [json.loads(line) for line in args["received_original"].splitlines()]
    outgoing = [json.loads(l) for l in args["sent_original"].splitlines()]
    settle_ids = [
        f"l22:{args['session_id']}:{args['action_id']}:settle-{i}"
        for i in range(1, 4)
    ]
    extra = []
    for i, request_id in enumerate(settle_ids):
        sample = dict(rows[31])
        sample["seq"] = 32 + i
        sample["request_id"] = request_id
        extra.append(sample)
    for row in rows[32:]:
        row["seq"] += len(extra)
    rows[32:32] = extra
    outgoing[-2:-2] = [
        {"type": "observe", "request_id": rid} for rid in settle_ids
    ]
    def compact(row):
        return (json.dumps(
            row, separators=(",", ":"), sort_keys=True,
        ) + "\n").encode()
    args["received_original"] = b"".join(map(compact, rows))
    args["sent_original"] = b"".join(map(compact, outgoing))
    args["s7_receipt"] = l15.l14._index(
        args["received_original"], args["sent_original"],
    )
    result = inspect_l22_settling(**args)
    assert result.settling_probe_seqs == (32, 33, 34)
    assert result.move_event_seqs == (35, 37)
    assert result.geometric_goal_candidate == "NOT_REACHED"
    assert result.accepted_goal_status == "UNDETERMINED"


@pytest.mark.parametrize("probes", [True, 2, 9])
def test_l22_preflight_rejects_unpaired_or_out_of_range_before_java(
    tmp_path, monkeypatch, probes,
):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    def no_java(*_args, **_kwargs):
        pytest.fail("invalid L22 opt-in must not start Minecraft")
    monkeypatch.setattr(s49, "_fetch_official_server", no_java)
    report = tmp_path / "report.json"
    status = asyncio.run(s49.qualify(
        report, tmp_path / "server.log", l22_settling_probes=probes,
    ))
    assert status == 2
    assert json.loads(report.read_text())["status"] == "BLOCKED"
    assert not (tmp_path / "server.log").exists()
