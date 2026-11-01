"""MP4 host→Paper console contract; all tests use fake stdin/no Minecraft."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_l1_host_prediction import HostPrediction
from adapters.mineflayer.self_body_s50_l1_paper_dispatch import (
    ForecastCommand,
    ForecastDispatchRejected,
    PaperForecastDispatch,
    require_paper_gate_config,
)

S = "a" * 64


def item(n=254, marker="marker", world="new-world", subject="body"):
    return ForecastCommand(marker, world, subject, n, n+1, float(n)/10000, S)


def test_command_exact_console_only_and_finite_bounded():
    assert item().wire() == f"relaydevforecast marker 254 255 0.0254 {S}"
    for changed in [
        replace(item(), marker="bad\nstop"),
        replace(item(), world="unbound world"),
        replace(item(), subject_uuid="wrong\nstimulus"),
        replace(item(), ticket_sha256="z"*64),
        replace(item(), target_tick=254),
        replace(item(), target_tick=257),
        replace(item(), prior_tick=True),
        replace(item(), predicted_m=float("nan")),
        replace(item(), predicted_m=float("inf")),
        replace(item(), predicted_m=-0.2),
        replace(item(), predicted_m=65.0),
        replace(item(), predicted_m=True),
    ]:
        with pytest.raises(ForecastDispatchRejected):
            changed.wire()


def test_bounded_no_unbounded_queue_no_cross_world_no_rearm():
    dispatcher = PaperForecastDispatch(marker="marker", world="new-world", subject_uuid="body")
    with pytest.raises(ForecastDispatchRejected):
        dispatcher.offer(item(world="other"))
    with pytest.raises(ForecastDispatchRejected):
        dispatcher.offer(item(marker="other"))
    with pytest.raises(ForecastDispatchRejected):
        dispatcher.offer(item(subject="other"))
    for n in range(254, 261):
        dispatcher.offer(item(n))
    assert dispatcher.queued == 7
    with pytest.raises(ForecastDispatchRejected):
        dispatcher.offer(item(261))
    dispatcher.close()
    with pytest.raises(ForecastDispatchRejected):
        dispatcher.offer(item())


def test_config_true_pinned_and_no_ambiguous_duplicate(tmp_path):
    path = tmp_path / "config.yml"
    baseline = (
        "dev-enabled: true\ns50-tick-meter-dev: true\n"
        "s50-forecast-gate-dev: true\ns50-input-witness-dev: true\n"
    )
    path.write_text(baseline)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    require_paper_gate_config(path, sha)
    with pytest.raises(ForecastDispatchRejected):
        require_paper_gate_config(path, "b"*64)
    with pytest.raises(ForecastDispatchRejected):
        require_paper_gate_config(tmp_path / "absent", sha)
    for modified in [
        baseline.replace("s50-forecast-gate-dev: true", "s50-forecast-gate-dev: false"),
        baseline.replace("dev-enabled: true", "dev-enabled: false"),
        baseline.replace("s50-tick-meter-dev: true", "s50-tick-meter-dev: false"),
        baseline + "s50-forecast-gate-dev: true\n",
        baseline.replace("s50-input-witness-dev: true", "s50-input-witness-dev: false"),
        baseline.replace("s50-forecast-gate-dev: true", "s50-forecast-gate-dev: maybe"),
    ]:
        path.write_text(modified)
        require_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        with pytest.raises(ForecastDispatchRejected):
            require_paper_gate_config(path, require_sha)


class FakePipe:
    def __init__(self):
        self.lines = []
        self.drains = 0

    def write(self, value):
        self.lines.append(value)

    async def drain(self):
        self.drains += 1


class FakeServer:
    returncode = None

    def __init__(self):
        self.stdin = FakePipe()


def test_pump_writes_console_once_never_claims_paper_acceptance():
    async def run():
        p = PaperForecastDispatch(marker="marker", world="new-world", subject_uuid="body")
        server = FakeServer()
        sent = []
        task = asyncio.create_task(p.pump(server, on_sent=sent.append))
        for n in range(254, 261):
            p.offer(item(n))
        await p._queue.join()
        p.close()
        await asyncio.wait_for(task, timeout=2)
        assert p.sent == 7 and p.queued == 7
        assert len(sent) == 7
        assert sent == [item(n) for n in range(254, 261)]
        assert server.stdin.drains == 7
        assert [line.decode() for line in server.stdin.lines] == [
            item(n).wire() + "\n" for n in range(254, 261)
        ]
    asyncio.run(run())


def test_no_retry_and_no_send_when_original_java_ended():
    async def run():
        p = PaperForecastDispatch(marker="marker", world="new-world", subject_uuid="body")
        server = FakeServer()
        server.returncode = 0
        p.offer(item())
        p.close()
        with pytest.raises(ForecastDispatchRejected, match="ended"):
            await p.pump(server)
        assert p.sent == 0
        assert server.stdin.lines == []
    asyncio.run(run())


def test_mp3_host_observer_requires_pre_forward_and_queues_only_after_fsync(tmp_path):
    journal = tmp_path / "forecast.jsonl"
    host = HostPrediction(journal)
    host.enable_paper_gate()
    with pytest.raises(ForecastDispatchRejected):
        host.enable_paper_gate()
    host.arm("session", "action", "marker")
    assert host.dispatch is None
    host.observe(b"M02_DEV_S50_PHASE marker_id=marker phase=PRE_FORWARD world=new-world\n")
    assert host.ticket is not None
    assert host.dispatch is not None
    assert host.dispatch.queued == 0
    assert host.dispatch.subject_uuid == host.training.subject_uuid
    assert host.dispatch.world == "new-world"
    assert host.ticket.model.slope == 0.20331885786720635
    for index, tick in enumerate(range(254, 262), 1):
        host.observe((
            f"S50_DEV_WAIT_TICK marker_id=marker world=new-world tick={tick} "
            f"index={index} from_x=0 from_y=0 from_z=0 x=0.01 y=0 z=0\n"
        ).encode())
    records = [json.loads(line) for line in journal.read_text().splitlines()]
    assert len([x for x in records if x["kind"] == "PREDICTION_FIXED"]) == 7
    assert len([x for x in records if x["kind"] == "PAPER_COMMAND_QUEUED"]) == 7
    assert all(x["status"] == "NOT_YET_SENT_OR_PAPER_ACCEPTED"
               for x in records if x["kind"] == "PAPER_COMMAND_QUEUED")
    assert host.dispatch.queued == 7
    assert host.dispatch.sent == 0
    requests = list(host.dispatch._queue._queue)
    assert [x.prior_tick for x in requests] == list(range(254, 261))
    assert [x.target_tick for x in requests] == list(range(255, 262))
    assert all(x.ticket_sha256 == host.ticket.ticket_sha256 for x in requests)
    with pytest.raises(ForecastDispatchRejected):
        host.dispatch.offer(requests[0])


def test_opt_in_must_precede_arm(tmp_path):
    host = HostPrediction(tmp_path / "forecast.jsonl")
    host.arm("session", "action", "marker")
    with pytest.raises(ForecastDispatchRejected):
        host.enable_paper_gate()
