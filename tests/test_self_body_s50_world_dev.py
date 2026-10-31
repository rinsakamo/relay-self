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
