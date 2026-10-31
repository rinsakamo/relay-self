"""Host integration boundaries; synthetic typed inputs, no World claims."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from adapters.mineflayer import self_body_s50_world_dev as host
from adapters.mineflayer.self_body_s50_original_closure import (
    SelfBodyS50ClosedOwnerLease,
    observe_original_s49_selfbody_closure,
)
from test_self_body_s50_original_closure import synthetic_original_closed


@pytest.mark.parametrize("attack", ["missing_after", "provenance", "clear_ack_only"])
def test_host_original_callback_rejects_incomplete_sources(attack):
    from adapters.mineflayer.normal_action import _READ_ONLY_CLOSURE
    original = synthetic_original_closed()
    if attack == "missing_after":
        from adapters.mineflayer.execution import WorldConsequenceStatus
        original = replace(original, consequence=replace(
            original.consequence, after_observation=None,
            status=WorldConsequenceStatus.FAILED, error="missing after",
        ))
    elif attack == "provenance":
        original = replace(original, consequence=replace(
            original.consequence, provenance=original.original_probe.provenance,
        ))
    else:
        original = original.consequence.cleanup_receipt
    lease = SelfBodyS50ClosedOwnerLease(self_id="self")
    try:
        with observe_original_s49_selfbody_closure(lease):
            _READ_ONLY_CLOSURE.get()(original)
        assert not lease.status()["typed_original_ready"]
    finally:
        lease.close()


def test_host_never_enters_default_two_action_route(tmp_path, monkeypatch):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    def forbidden(*args, **kwargs):
        pytest.fail("must reject before World startup")
    monkeypatch.setattr(host, "_ready_server", forbidden)
    output = tmp_path / "report.json"
    assert asyncio.run(host.qualify(output, tmp_path / "server.log")) != 0
    report = json.loads(output.read_bytes())
    assert "requires single-Action L23" in report["error"]
    assert not report["actual_native_actions"]


@pytest.mark.parametrize("foreign", [None, "before", "after"])
def test_original_s15_correlates_existing_probes_without_extra_controls(foreign):
    import test_mineflayer_execution_qualification as s15
    from adapters.mineflayer.execution import (
        WorldConsequenceStatus,
        build_mineflayer_command,
        execute_mineflayer_command,
    )
    *_, binding, _, supervisor, issued = s15.issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding)
    fixture = s15.successful_session(command)
    messages = list(fixture._messages)
    before_id = f"s15:s15-session:{command.action_id}:before"
    after_id = f"s15:s15-session:{command.action_id}:after"
    messages[0] = replace(messages[0], request_id="foreign" if foreign == "before" else before_id)
    messages[-1] = replace(messages[-1], request_id="foreign" if foreign == "after" else after_id)

    class CorrelatedSession(s15.FakeSession):
        async def send_observe(self, request_id=None):
            self.sent.append(("observe", request_id))

    adapter = CorrelatedSession(messages)
    result = asyncio.run(execute_mineflayer_command(
        adapter, command, provenance=s15.provenance("correlated-dev"),
        correlate_native_probes_dev=True,
    ))
    if foreign is None:
        assert result.status is WorldConsequenceStatus.EXECUTED
        assert result.before_observation.request_id == before_id
        assert result.after_observation.request_id == after_id
    else:
        assert result.status is not WorldConsequenceStatus.EXECUTED
    assert sum(x[0] == "set_control" for x in adapter.sent) == (0 if foreign == "before" else 1)
    assert sum(x[0] == "clear_controls" for x in adapter.sent) == (0 if foreign == "before" else 1)
    assert sum(x[0] == "observe" for x in adapter.sent) == (1 if foreign == "before" else 2)


def test_actual_producer_asdict_shape_joins_original_typed_lease(monkeypatch):
    from dataclasses import asdict

    import test_s50_selfbody_motion_source as source_fixture
    original = synthetic_original_closed()
    sid, action = original.interpretation.session_id, original.interpretation.action_id
    monkeypatch.setattr(source_fixture, "SID", sid)
    monkeypatch.setattr(source_fixture, "ACTION", action)
    monkeypatch.setattr(source_fixture, "MARKER", f"{action}-{sid}")
    producer = asdict(source_fixture.project())
    assert isinstance(producer["paper_samples"], tuple)
    normalized = host.normalize_s50_diagnostic({"physical_body_diagnostic": producer})
    assert isinstance(normalized["physical_body_diagnostic"]["paper_samples"], list)
    assert json.loads(json.dumps(producer)) == normalized["physical_body_diagnostic"]
    lease = SelfBodyS50ClosedOwnerLease(self_id="self", expected_action_id=action)
    try:
        lease.observe_original_closed(original)
        joined = lease.consume_s50_once(normalized["physical_body_diagnostic"])
        assert joined.self_body.outcome is original.interpretation
        assert len(joined.ticks) == 8
    finally:
        lease.close()
