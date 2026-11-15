"""#860 Stage19: actual original PhysicalIssueAdmission + WAL/owner in inert DEV.

Native sessions are source-shaped synthetic Mineflayer objects and Paper is
an owned OS subprocess mimicking its console. NO real Minecraft / LLM here.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerInventoryItem,
    MineflayerLaunchConfig,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitiveOwnerFiles,
)
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.owned_paper_world_dev import OwnedPaperWorld, PaperTickReceipt
from relay_self.owned_resident_physical_bridge_dev import (
    OwnedResidentBridgeError,
    OwnedResidentPhysicalBridge,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkError,
    ResidentCognitiveWorkOwner,
)
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalUnresolved,
)
from relay_self.physical_action_port import PhysicalActionBinding
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.provenance import Provenance
from relay_self.world_only_owned_checkpoint_dev import (
    WorldOnlyOwnedPaperCheckpoint,
)
from relay_self.world_resident_lifecycle_dev import (
    Presence,
    WorldLifetime,
    WorldResidentLifecycle,
)


def _fake_paper(root: Path) -> OwnedPaperWorld:
    paper_dir = root / "paper"
    paper_dir.mkdir()
    world_dir = paper_dir / "world"
    world_dir.mkdir()
    (world_dir / "level.dat").write_bytes(b"faux-paper-level")
    evidence = root / "paper-evidence"
    evidence.mkdir()
    script = paper_dir / "fake-paper.py"
    script.write_text(
        "import sys\n"
        "print('Done (0.1s)',flush=True)\n"
        "for line in sys.stdin:\n"
        "  if line.strip()=='save-all flush':\n"
        "    print('Saved the game',flush=True)\n"
        "  if line.strip()=='stop':\n"
        "    print('Stopping server',flush=True)\n"
        "    sys.exit(0)\n",
        encoding="utf-8",
    )
    reads = [0]

    def read_tick(sid):
        reads[0] += 1
        return PaperTickReceipt(sid, 100 + 10 * reads[0], f"faux-tick:{reads[0]}")

    return OwnedPaperWorld(
        server_dir=paper_dir, world_dir=world_dir, evidence_dir=evidence,
        command=(sys.executable, "-u", str(script)),
        world_id="world-live", branch_id="source",
        tick_readback=read_tick, timeout_seconds=3.0,
    )


class FakeNativeResident:
    """Test injection: emulate the typed native stream; no actual Node child."""

    def __init__(self, config, session_id, *, bad_probe=False):
        self.started = SimpleNamespace(session_id=session_id, config=config)
        self.process_returncode = None
        self.events = []
        self.effect_gate = None
        self.seq = 1
        self.bad_probe = bad_probe
        self.events.append(self._observation("spawn", None))

    def _observation(self, kind, request_id):
        self.seq += 1
        return MineflayerObservation(
            self.started.session_id, self.seq, kind,
            MineflayerSnapshot(
                health=20, food=16, food_saturation=5, oxygen_level=20,
                position=MineflayerPosition(1, 64, 2),
                time=MineflayerTime(180, 0, True), inventory=(),
                nearby_entities=(),
                nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                    0, False,
                ),
            ), request_id,
        )

    def install_effect_admission(self, gate):
        assert self.effect_gate is None
        self.effect_gate = gate

    async def send_observe(self, request_id):
        self.events.append(self._observation(
            "probe", "unrelated-request" if self.bad_probe else request_id,
        ))

    async def receive(self):
        if self.events:
            return self.events.pop(0)
        raise EOFError("missing native source message")

    async def terminate(self):
        self.process_returncode = 0
        return 0

    def send_test_effect(self, effect, action_id):
        assert self.effect_gate is not None
        self.effect_gate(self.started.session_id, effect, action_id)


class ResidentFixture:
    def __init__(self, root: Path, n: int, *, cognitive_work: bool = False):
        self.paper = _fake_paper(root)
        paper_session = self.paper.start_owned()
        self.names = tuple(f"S{i:03d}" for i in range(n))
        self.original_ids = {
            sid: f"offline-born-{sid}" for sid in self.names
        }
        self.physical = PhysicalIssueAdmission(
            self.original_ids, resident_mode=True, initially_offline=True,
        )
        self.owners = {}
        for sid in self.names:
            folder = root / ("owner-" + sid)
            folder.mkdir()
            wal = folder / "physical-wal.json"
            PhysicalActionJournal.create(wal, self_id=sid)
            self.owners[sid] = CheckpointedCognitiveOwner(
                retained=PersistentCognition(
                    IdentitySpecification(
                        sid, ("Separate identity across Worlds",),
                        Provenance("synthetic", sid),
                    )
                ),
                intent=IntentCommitment(),
                pattern_registry=initial_patterns(),
                native_session_id=self.original_ids[sid],
                last_observed_tick=100,
                files=CognitiveOwnerFiles(
                    folder, folder / "cognition.json", wal,
                ),
                physical_supervisor=ActionSupervisor(),
            )
        self.lifecycle = WorldResidentLifecycle(
            world=WorldLifetime(
                "world-live", "source", paper_session, 0, 100,
            ),
            persisted_self_refs={
                sid: "retained:boot:" + sid for sid in self.names
            },
        )
        self.configs = {
            sid: MineflayerLaunchConfig(
                host="127.0.0.1", port=25565,
                username=sid, version="1.21.8",
            ) for sid in self.names
        }
        self.launched = []
        self.failed_probe_id = None

        async def launch(config):
            sid = config.username
            value = FakeNativeResident(
                config, f"native-{sid}-{len(self.launched) + 1}",
                bad_probe=sid == self.failed_probe_id,
            )
            self.launched.append(value)
            return value

        self.cognitive = (
            ResidentCognitiveWorkOwner(self.owners) if cognitive_work else None
        )
        self.bridge = OwnedResidentPhysicalBridge(
            lifecycle=self.lifecycle, physical=self.physical,
            paper=self.paper, configs=self.configs, owners=self.owners,
            launch=launch, cognitive_work=self.cognitive,
        )

    def stop_paper(self):
        if self.paper.owned_session_id is not None and not self.paper.held_uncertain:
            self.paper.stop_and_save()


@pytest.mark.parametrize("count", [2, 10, 100])
def test_one_resident_logout_does_not_stop_n_minus_one_original_issuers(
    tmp_path, count,
):
    f = ResidentFixture(tmp_path, count)

    async def scenario():
        for sid in f.names:
            await f.bridge.login(sid)
        assert set(f.physical.resident_states.values()) == {"ONLINE"}
        target = f.names[-1]
        old = f.bridge.sessions[target]
        assert old.effect_gate is not None
        assert f.physical.current_native_sessions[target] == old.started.session_id
        proof = await f.bridge.logout(target)
        assert proof.native_terminated and proof.physical_wal_clear
        assert f.lifecycle.view(target).status is Presence.OFFLINE
        assert f.physical.resident_states[target] == "OFFLINE"
        assert all(
            f.lifecycle.view(s).status is Presence.ONLINE
            for s in f.names[:-1]
        )
        assert not f.physical.closed
        with pytest.raises(PhysicalIssueFenceError):
            with f.physical.lease(
                self_id=target, native_session_id=old.started.session_id,
                action_id="stale-EAT", effect_family="EAT",
            ):
                pytest.fail("old child acquired effect permission")
        with pytest.raises(PhysicalIssueFenceError):
            old.send_test_effect("consume_held", "stale-EAT")
        active = f.names[0]
        with f.physical.lease(
            self_id=active,
            native_session_id=f.bridge.sessions[active].started.session_id,
            action_id="EAT-other", effect_family="EAT",
        ):
            f.bridge.sessions[active].send_test_effect(
                "consume_held", "EAT-other",
            )
        f.lifecycle.world_tick(
            paper_session_id=f.paper.owned_session_id,
            tick=125, source_ref="synthetic-paper-tick",
        )
        await f.bridge.login(target)
        assert f.physical.resident_states[target] == "ONLINE"
        assert f.bridge.sessions[target].started.session_id != old.started.session_id
        assert not f.lifecycle.view(target).action_issue_authorized
        for sid in f.names:
            await f.bridge.logout(sid)
        assert f.physical.all_residents_offline
        assert f.bridge.world_only_quiescence().native_sessions_absent

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()


@pytest.mark.parametrize("count", [2, 10, 100])
def test_active_one_self_cannot_complete_logout_or_fence_peers(
    tmp_path, count,
):
    f = ResidentFixture(tmp_path, count)

    async def scenario():
        for sid in f.names:
            await f.bridge.login(sid)
        target = f.names[0]
        session_id = f.bridge.sessions[target].started.session_id
        peer = f.names[-1]
        with f.physical.lease(
            self_id=target, native_session_id=session_id,
            action_id="pending-attack", effect_family="ATTACK",
        ):
            with pytest.raises(OwnedResidentBridgeError, match="in-flight"):
                await f.bridge.logout(target)
            assert f.lifecycle.view(target).status is Presence.QUARANTINED
            assert f.physical.resident_states[target] == "QUARANTINED"
            assert f.lifecycle.view(peer).status is Presence.ONLINE
            with pytest.raises(PhysicalIssueFenceError):
                f.bridge.sessions[target].send_test_effect(
                    "attack_entity", "pending-attack",
                )
            with f.physical.lease(
                self_id=peer,
                native_session_id=f.bridge.sessions[peer].started.session_id,
                action_id="peer-eat", effect_family="EAT",
            ):
                f.bridge.sessions[peer].send_test_effect(
                    "consume_held", "peer-eat",
                )
        # A finished lease does NOT transform an earlier failed logout
        # into a verified OFFLINE state without full native+WAL readback.
        assert f.lifecycle.view(target).status is Presence.QUARANTINED
        assert f.physical.resident_states[target] == "QUARANTINED"
        await f.bridge.logout(target)
        assert f.lifecycle.view(target).status is Presence.OFFLINE
        for sid in f.names[1:]:
            await f.bridge.logout(sid)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()


def test_one_native_probe_failure_quarantines_self_without_any_issue(tmp_path):
    f = ResidentFixture(tmp_path, 2)
    f.failed_probe_id = f.names[1]

    async def scenario():
        await f.bridge.login(f.names[0])
        with pytest.raises(Exception, match="unmatched"):
            await f.bridge.login(f.names[1])
        assert f.lifecycle.view(f.names[1]).status is Presence.QUARANTINED
        assert f.physical.resident_states[f.names[1]] == "OFFLINE"
        assert f.lifecycle.view(f.names[0]).status is Presence.ONLINE
        assert f.physical.resident_states[f.names[0]] == "ONLINE"
        assert f.launched[-1].process_returncode is not None
        with f.physical.lease(
            self_id=f.names[0],
            native_session_id=f.bridge.sessions[f.names[0]].started.session_id,
            action_id="peer-continues",
        ):
            pass
        await f.bridge.logout(f.names[0])

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()


def test_physical_wal_unresolved_prevents_one_self_retirement(tmp_path):
    f = ResidentFixture(tmp_path, 2)

    async def scenario():
        for sid in f.names:
            await f.bridge.login(sid)
        target = f.names[0]
        # Simulate a damaged/unreadable original physical WAL: never call
        # retire() with a fabricated "all clear" while the file is absent.
        wal = f.owners[target].files.physical_wal_file
        wal.rename(wal.with_suffix(".unresolved"))
        try:
            with pytest.raises(Exception):
                await f.bridge.logout(target)
            assert f.lifecycle.view(target).status is Presence.QUARANTINED
            assert f.physical.resident_states[target] == "QUARANTINED"
            assert f.lifecycle.view(f.names[1]).status is Presence.ONLINE
            assert not f.physical.all_residents_offline
        finally:
            wal.with_suffix(".unresolved").rename(wal)
        # Once original WAL has been reconciled, native already terminated,
        # a separate operator recovery path is required; do NOT auto resume.

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()


def test_world_only_checkpoint_accepts_original_issuer_after_all_logout(tmp_path):
    f = ResidentFixture(tmp_path, 2)
    store = tmp_path / "world-store"
    store.mkdir()

    async def scenario():
        for sid in f.names:
            await f.bridge.login(sid)
        for sid in f.names:
            await f.bridge.logout(sid)

    try:
        asyncio.run(scenario())
        receipt = f.bridge.world_only_quiescence()
        assert receipt.original_physical_issuer_closed
        assert receipt.checked_self_ids == f.names
        result = WorldOnlyOwnedPaperCheckpoint(
            lifecycle=f.lifecycle, owned_paper=f.paper,
            store=store, issuer_quiescence=f.bridge.world_only_quiescence,
        ).cycle()
        assert result.new_world.epoch == 1
        assert f.lifecycle.self_roster == f.names
        assert all(
            f.lifecycle.view(s).status is Presence.OFFLINE
            for s in f.names
        )
        assert not (result.checkpoint_dir / "selves").exists()
        # A fresh World epoch requires a fresh source-matched native child.
        asyncio.run(f.bridge.login(f.names[0]))
        assert f.lifecycle.view(f.names[0]).status is Presence.ONLINE
        asyncio.run(f.bridge.logout(f.names[0]))
    finally:
        f.stop_paper()


def test_no_compute_scope_fails_closed_per_self_without_disrupting_peer(tmp_path):
    f = ResidentFixture(tmp_path, 2)

    async def scenario():
        for sid in f.names:
            await f.bridge.login(sid)
        with pytest.raises(OwnedResidentBridgeError, match="GPU"):
            f.bridge.work.reject_gpu_task(f.names[0], "untracked-task")
        with pytest.raises(OwnedResidentBridgeError, match="scope"):
            await f.bridge.logout(f.names[0])
        assert f.physical.resident_states[f.names[0]] == "QUARANTINED"
        assert f.lifecycle.view(f.names[1]).status is Presence.ONLINE
        with f.physical.lease(
            self_id=f.names[1],
            native_session_id=f.bridge.sessions[f.names[1]].started.session_id,
            action_id="peer-scope-still-active",
        ):
            pass

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()



def test_original_wal_prepared_unresolved_blocks_individual_logout(tmp_path):
    """Actual CAS journal PREPARED, not a missing-file or mocked boolean."""
    f = ResidentFixture(tmp_path, 2)

    async def scenario():
        for sid in f.names:
            await f.bridge.login(sid)
        sid = f.names[0]
        native = f.bridge.sessions[sid].started.session_id
        snapshot = MineflayerSnapshot(
            health=20, food=14, food_saturation=5, oxygen_level=20,
            position=MineflayerPosition(1, 64, 2),
            time=MineflayerTime(181, 0, True),
            inventory=(MineflayerInventoryItem("bread", 1, 9),),
            nearby_entities=(),
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
                0, False,
            ),
        )
        probe = MineflayerObservation(
            native, 88, "probe", snapshot, "prepare-eat-1",
        )
        binding = PhysicalActionBinding(
            ScopeRef(sid, native),
            intent_id="intent-eat",
            goal_id="hunger-relief",
            skill_id="EAT", skill_version=1,
            skill_execution_id="skill-exec-eat",
            action_id="eat-prepared-only",
            capability_ref="EAT", capability_version=1,
            body_channel="hand",
            target_kind="FOOD", target_ref="inventory:bread",
            native_seq=88, native_request_id="prepare-eat-1",
            native_source=probe.provenance,
        )
        wal = f.owners[sid].files.physical_wal_file
        original = PhysicalActionJournal.restore(wal, self_id=sid)
        original.prepare_eat(binding, probe)
        assert PhysicalActionJournal.restore(
            wal, self_id=sid,
        ).unresolved
        with pytest.raises(PhysicalJournalUnresolved, match="possible physical"):
            await f.bridge.logout(sid)
        assert f.lifecycle.view(sid).status is Presence.QUARANTINED
        assert f.physical.resident_states[sid] == "QUARANTINED"
        assert f.lifecycle.view(f.names[1]).status is Presence.ONLINE
        assert not f.physical.closed
        with f.physical.lease(
            self_id=f.names[1],
            native_session_id=f.bridge.sessions[f.names[1]].started.session_id,
            action_id="unrelated-peer-still-allowed", effect_family="EAT",
        ):
            f.bridge.sessions[f.names[1]].send_test_effect(
                "consume_held", "unrelated-peer-still-allowed",
            )
        with pytest.raises(Exception):
            f.bridge.world_only_quiescence()
        assert PhysicalActionJournal.restore(
            wal, self_id=sid,
        ).records[-1]["status"] == "PREPARED_UNRESOLVED"

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
