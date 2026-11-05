"""Read-only native probes may settle; never infer from an empty first registry."""
import asyncio
from types import SimpleNamespace

import pytest

from tools import bug0_zombie_respawn_r1_world as mod


class NativeFrame:
    def __init__(self, request_id, seq, names):
        self.kind = "probe"
        self.request_id = request_id
        self.seq = seq
        self.session_id = "s"
        self.provenance = SimpleNamespace(reference="mineflayer:native")
        self.snapshot = SimpleNamespace(
            nearby_entities=[
                SimpleNamespace(name=n, entity_type="mob", entity_id=i, distance=6.0)
                for i, n in enumerate(names, 11)
            ],
            nearby_entities_coverage=SimpleNamespace(
                candidate_count=len(names), truncated=False,
            ),
        )


class NativeSession:
    def __init__(self, responses):
        self.requests = []
        self.responses = responses

    async def send_observe(self, request_id):
        self.requests.append(request_id)

    async def receive(self):
        idx = len(self.requests) - 1
        names = self.responses[min(idx, len(self.responses) - 1)]
        return NativeFrame(self.requests[-1], idx + 1, names)


@pytest.fixture(autouse=True)
def fake_classes(monkeypatch):
    monkeypatch.setattr(mod, "MineflayerObservation", NativeFrame)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(mod.asyncio, "sleep", no_sleep)


def test_bounded_source_fresh_native_settling():
    s = NativeSession([[], ["zombie"]])
    result = asyncio.run(mod._native_probe(s, "initial"))
    assert result["read_attempt"] == 2
    assert result["zombie_entity_id"] == 11
    assert result["request_id"] == "initial-2"
    assert result["unready_native_samples"][0]["zombie_count"] == 0
    assert s.requests == ["initial-1", "initial-2"]


def test_no_minted_entity_when_not_observed():
    s = NativeSession([[]])
    with pytest.raises(mod.RespawnR1Rejected, match="10 fresh read-only"):
        asyncio.run(mod._native_probe(s, "initial"))
    assert len(s.requests) == 10
    assert len(set(s.requests)) == 10


def test_ambiguous_multiple_zombies_not_admitted():
    s = NativeSession([["zombie", "zombie"]])
    with pytest.raises(mod.RespawnR1Rejected, match="10 fresh read-only"):
        asyncio.run(mod._native_probe(s, "initial"))
    assert len(s.requests) == 10
