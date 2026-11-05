"""D1 native inventory truth never manufactures World loot/drop facts."""
from types import SimpleNamespace

import pytest

from adapters.mineflayer import loot_pickup_readback as subject


class FakeObservation:
    def __init__(self, seq, amount, *, session="s", source="mineflayer",
                 kind="probe", request_id=None, health=20):
        self.kind = kind
        self.request_id = request_id or f"p{seq}"
        self.seq = seq
        self.session_id = session
        self.provenance = SimpleNamespace(source=source, reference=f"{source}:{seq}")
        self.snapshot = SimpleNamespace(
            health=health,
            inventory=(SimpleNamespace(name="rotten_flesh", count=amount, slot=9),)
            if amount else tuple(),
        )


@pytest.fixture(autouse=True)
def mock_observation_class(monkeypatch):
    monkeypatch.setattr(subject, "MineflayerObservation", FakeObservation)


def test_exact_native_gain_does_not_claim_world_provenance():
    before, after = FakeObservation(3, 0), FakeObservation(7, 1)
    receipt = subject.read_rotten_flesh_gain(before, after)
    assert (receipt.before_count, receipt.after_count) == (0, 1)
    assert receipt.outcome_scope == "NATIVE_INVENTORY_DELTA_ONLY"
    assert receipt.after_probe_seq == 7


@pytest.mark.parametrize("before,after", [
    (FakeObservation(3, 0), FakeObservation(5, 0)),
    (FakeObservation(3, 0), FakeObservation(5, 2)),
    (FakeObservation(3, 0), FakeObservation(2, 1)),
    (FakeObservation(3, 0), FakeObservation(5, 1, session="other")),
    (FakeObservation(3, 0), FakeObservation(5, 1, source="paper")),
    (FakeObservation(3, 0), FakeObservation(5, 1, kind="entities")),
    (FakeObservation(3, 0), FakeObservation(5, 1, health=0)),
    (FakeObservation(3, 0), FakeObservation(3, 1)),
])
def test_fail_closed(before, after):
    with pytest.raises(subject.LootPickupReadbackRejected):
        subject.read_rotten_flesh_gain(before, after)


def test_not_a_physical_issuer():
    assert not hasattr(subject, "ActionSupervisor")
    assert not hasattr(subject, "send_set_control")
