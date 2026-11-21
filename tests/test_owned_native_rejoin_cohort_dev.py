"""#860 Stage 14: process-shaped native A/B rejoin, not live Minecraft."""
import asyncio

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_VERSION,
    MineflayerAdapterStarted,
    MineflayerLaunchConfig,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)
from relay_self.owned_native_rejoin_cohort_dev import (
    NativeCohortRejoinError,
    OwnedNativeRejoinCohort,
)
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)


def _snap():
    return MineflayerSnapshot(
        20, 20, 5, 20, MineflayerPosition(1, 64, 1),
        MineflayerTime(100, 0, True), (), (),
        MineflayerNearbyEntitiesCoverage(
            "mineflayer_entity_registry", 16.0, 16, 0, False,
        ),
    )


class NativeSession:
    def __init__(self, sid, config, *, fault=None):
        self.started = MineflayerAdapterStarted(sid, 0, MINEFLAYER_VERSION, config)
        self.process_returncode = None
        self.admission = None
        self.request = None
        self.fault = fault
        self.receives = 0
        self.terminated = False

    def install_effect_admission(self, callback):
        assert self.admission is None
        self.admission = callback

    async def receive(self):
        self.receives += 1
        if self.fault == "connection":
            raise ConnectionError("native connection ended")
        if self.receives == 1:
            return MineflayerObservation(
                self.started.session_id, 1, "spawn", _snap(),
            )
        if self.fault == "stalled":
            await asyncio.Event().wait()
        return MineflayerObservation(
            self.started.session_id, self.receives, "probe", _snap(), self.request,
        )

    async def send_observe(self, request_id):
        self.request = request_id

    async def terminate(self):
        self.terminated = True
        self.process_returncode = -15
        return self.process_returncode


def _cohort(fault=None):
    configs = {
        sid: MineflayerLaunchConfig(
            host="127.0.0.1", port=25565, username="Relay" + sid, version="1.21.8",
        ) for sid in ("A", "B")
    }
    existing = {
        sid: NativeSession("old-" + sid, config)
        for sid, config in configs.items()
    }
    physical = PhysicalIssueAdmission({sid: s.started.session_id for sid, s in existing.items()})
    launched = []

    async def launch(config):
        sid = config.username[-1]
        result = NativeSession("new-" + sid, config, fault=fault if sid == "B" else None)
        launched.append(result)
        return result

    cohort = OwnedNativeRejoinCohort(
        sessions=existing, configs=configs, physical=physical,
        launch=launch, probe_timeout_s=0.05,
    )
    return cohort, existing, physical, launched


def test_real_native_session_protocol_seam_and_full_rebind():
    manager, previous, physical, launched = _cohort()
    assert [p.self_id for p in manager.participants_now()] == ["A", "B"]
    with pytest.raises(PhysicalIssueFenceError, match="requires active"):
        previous["A"].admission("old-A", "attack_entity", "unleased")
    fence = physical.close()

    async def run():
        a = await manager.prepare_rejoin("A", "paper-after", "old-A")
        b = await manager.prepare_rejoin("B", "paper-after", "old-B")
        return a, b

    assert asyncio.run(run()) == ("new-A", "new-B")
    assert previous["A"].terminated and previous["B"].terminated
    assert len(launched) == 2
    for sid in ("A", "B"):
        receipt = manager.prepared_receipt(sid, "paper-after", "old-" + sid)
        assert receipt.spawn_seq == 1
        assert receipt.probe_seq > receipt.spawn_seq
        assert receipt.old_process_terminated
        assert receipt.effect_admission_installed
        assert not receipt.gpu_tasks_fenced
        assert not receipt.stale_transport_fenced
        with pytest.raises(PhysicalIssueFenceError, match="stale|blocked"):
            manager.sessions[sid].admission(receipt.new_native_session_id, "attack_entity", "x")
        physical.rotate_native_session(
            fence_ref=fence.fence_ref, self_id=sid, old_session_id="old-" + sid,
            new_session_id="new-" + sid,
        )
    physical.release(fence.fence_ref)
    assert not physical.closed
    assert [p.session.started.session_id for p in manager.participants_now()] == [
        "new-A", "new-B",
    ]
    # The same old session can never send a native effect after rotation.
    with pytest.raises(PhysicalIssueFenceError, match="stale"):
        previous["A"].admission("old-A", "attack_entity", "x")


@pytest.mark.parametrize("fault", ["connection", "stalled"])
def test_b_failure_poisoned_even_after_a_prepared(fault):
    manager, previous, physical, launched = _cohort(fault)
    physical.close()

    async def run():
        assert await manager.prepare_rejoin("A", "paper", "old-A") == "new-A"
        await manager.prepare_rejoin("B", "paper", "old-B")

    with pytest.raises((ConnectionError, TimeoutError)):
        asyncio.run(run())
    assert physical.closed
    assert manager.prepared_receipt("A", "paper", "old-A").new_native_session_id == "new-A"
    assert previous["A"].terminated and previous["B"].terminated
    assert launched[-1].terminated


def test_old_process_and_unclosed_checkpoint_cannot_rejoin():
    manager, previous, physical, launched = _cohort()
    with pytest.raises(NativeCohortRejoinError, match="unfenced"):
        asyncio.run(manager.prepare_rejoin("A", "paper", "old-A"))
    assert physical.closed
    assert not launched
    assert not previous["A"].terminated


def test_config_refuses_wrong_world_or_duplicate_actor():
    configs = {
        sid: MineflayerLaunchConfig(
            "127.0.0.1", 25565, "Duplicate", "1.21.8",
        ) for sid in ("A", "B")
    }
    existing = {
        sid: NativeSession("old-" + sid, config) for sid, config in configs.items()
    }
    physical = PhysicalIssueAdmission({sid: s.started.session_id for sid, s in existing.items()})
    with pytest.raises(NativeCohortRejoinError, match="distinct"):
        OwnedNativeRejoinCohort(sessions=existing, configs=configs, physical=physical)



def test_real_initial_owned_native_cohort_two_spawns_and_probes():
    manager, previous, physical, launched = _cohort()
    proofs = asyncio.run(manager.verify_initial_cohort())
    assert set(proofs) == {"A", "B"}
    assert all(seq == 1 and later > seq and request.startswith("p0d-rejoin-")
               for seq, later, request in proofs.values())
    assert not physical.closed
    assert len(launched) == 0
    assert all(previous[sid].receives == 2 for sid in ("A", "B"))
    with pytest.raises(NativeCohortRejoinError, match="already read"):
        asyncio.run(manager.verify_initial_cohort())


def test_real_initial_b_failure_holds_both_native_issuers():
    manager, previous, physical, launched = _cohort()
    previous["B"].fault = "connection"
    with pytest.raises(ConnectionError):
        asyncio.run(manager.verify_initial_cohort())
    assert previous["A"].receives == 2
    assert physical.closed
    assert not launched
    with pytest.raises(PhysicalIssueFenceError, match="blocked"):
        previous["A"].admission("old-A", "attack_entity", "any")
