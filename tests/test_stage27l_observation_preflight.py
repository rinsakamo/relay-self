from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from experiments.stage27l_observation_preflight import inspect_native_probe


def probe():
    coverage = MineflayerNearbyEntitiesCoverage(
        MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE, MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
        MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES, 0, False)
    snapshot = MineflayerSnapshot(20, 20, 5, None, MineflayerPosition(1, 2, 3),
                                 None, (), (), coverage)
    return MineflayerObservation("native", 2, "probe", snapshot, "request")


def inspect(observation, **kwargs):
    return inspect_native_probe(observation, expected_session=kwargs.get("session", "native"),
                                expected_request_id=kwargs.get("request", "request"),
                                previous_seq=kwargs.get("seq", 1))


def test_probe_preserves_evidence_but_does_not_qualify_world():
    result = inspect(probe())
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "SOURCE_SNAPSHOT_INCOMPLETE"
    assert result["evidence"]["position"] == {"x": 1, "y": 2, "z": 3}
    assert "body_aabb" in result["evidence"]["unavailable"]
    assert "collision_shapes" in result["evidence"]["unavailable"]


@pytest.mark.parametrize("observation,kwargs,reason", [
    (None, {}, "NATIVE_PROBE_UNAVAILABLE"),
    (probe(), {"session": "foreign"}, "NATIVE_SESSION_MISMATCH"),
    (probe(), {"request": "foreign"}, "NATIVE_REQUEST_MISMATCH"),
    (replace(probe(), kind="spawn", request_id=None), {}, "NATIVE_REQUEST_MISMATCH"),
    (probe(), {"seq": 2}, "NATIVE_SEQUENCE_NOT_MONOTONIC"),
    (probe(), {"seq": 3}, "NATIVE_SEQUENCE_NOT_MONOTONIC"),
    (probe(), {"seq": True}, "NATIVE_SEQUENCE_NOT_MONOTONIC"),
])
def test_refusals(observation, kwargs, reason):
    result = inspect(observation, **kwargs)
    assert (result["status"], result["reason_code"]) == ("UNKNOWN", reason)


def test_capture_uses_only_observe_and_preserves_correlation():
    import asyncio
    from types import SimpleNamespace

    from experiments.stage27l_observation_preflight import capture_native_probe

    class Session:
        started = SimpleNamespace(session_id="native")
        request = None

        async def send_observe(self, request_id):
            self.request = request_id

        async def receive(self):
            return replace(probe(), request_id=self.request)

    session = Session()
    result = asyncio.run(capture_native_probe(session, expected_session="native", previous_seq=1))
    assert session.request.startswith("stage27l-")
    assert result["status"] == "UNKNOWN"
    assert result["evidence"]["request_id"] == session.request
