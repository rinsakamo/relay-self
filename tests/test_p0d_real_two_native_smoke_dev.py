"""#860 Stage 15: offline negative controls for disposable real two-native trial."""
from __future__ import annotations

import asyncio
import hashlib
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from experiments.p0d_real_paper_smoke_dev import RealPaperSmokeRefusal
from experiments.p0d_real_two_native_smoke_dev import (
    TwoNativePaperRefusal,
    preflight_two_native,
    run_native_two_cycle_smoke,
    two_native_server_properties,
)
from relay_self.checkpoint_stop_neutralization_dev import (
    StopCohortReady,
    StopParticipant,
)
from relay_self.coordinated_autosave_runtime_dev import (
    RestartedWorldReceipt,
    StoppedWorldReceipt,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission


def _jar(path: Path, *, paper: bool = False) -> str:
    with zipfile.ZipFile(path, "w") as jar:
        if paper:
            jar.writestr("META-INF/MANIFEST.MF", "Main-Class: Paperclip\n")
        else:
            jar.writestr("plugin.yml", "name: P0BRecorder\n")
            jar.writestr("io/github/rinsakamo/p0b/Recorder.class", b"test")
            jar.writestr("io/github/rinsakamo/p0b/TickWitness.class", b"test")
            jar.writestr("io/github/rinsakamo/p0b/ResidentPresenceWitness.class", b"test")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_two_native_properties_are_loopback_only_and_without_action_services():
    props = two_native_server_properties(48123).splitlines()
    assert "server-ip=127.0.0.1" in props
    assert "server-port=48123" in props
    assert "online-mode=false" in props
    assert "max-players=2" in props
    assert "enable-rcon=false" in props
    assert "enable-query=false" in props
    assert "difficulty=peaceful" in props
    assert "gamemode=creative" in props
    assert not any(line.startswith("server-ip=0.0.0.0") for line in props)
    for port in (0, 22, 65536, True, "48123"):
        with pytest.raises(TwoNativePaperRefusal, match="port"):
            two_native_server_properties(port)


@pytest.mark.parametrize(
    ("accepted", "paper_bad", "expected"),
    [
        (False, False, "explicitly accept"),
        (True, False, "only pinned official Paper"),
        (True, True, "SHA256"),
    ],
)
def test_preflight_rejects_fake_binary_or_missing_eula_without_any_world(
    tmp_path: Path, accepted: bool, paper_bad: bool, expected: str,
):
    paper = tmp_path / "paper.jar"
    plugin = tmp_path / "plugin.jar"
    paper_sha = _jar(paper, paper=True)
    plugin_sha = _jar(plugin)
    with pytest.raises((RealPaperSmokeRefusal, TwoNativePaperRefusal), match=expected):
        preflight_two_native(
            paper_jar=paper, paper_sha256="0" * 64 if paper_bad else paper_sha,
            plugin_jar=plugin, plugin_sha256=plugin_sha,
            scratch_parent=tmp_path, accepted_eula=accepted,
            java="java", node="node", timeout_s=120, heap_mb=1536,
            check_native_runtime=False,
        )
    assert not list(tmp_path.glob("p0d-real-two-native-*"))
    assert not (tmp_path / "eula.txt").exists()


class FakePaper:
    def __init__(self, root: Path, world_id: str, *, omit_b: bool = False):
        self.evidence_dir = root / "evidence"
        self.evidence_dir.mkdir()
        self.owned_session_id = "paper-1"
        self.world_id = world_id
        self.stop_count = 0
        self.omit_b = omit_b
        for i in (1, 2):
            log = "RelayA joined the game\n"
            if not omit_b:
                log += "RelayB joined the game\n"
            (self.evidence_dir / f"paper-{i}.log").write_text(log, encoding="utf-8")

    def read_owned_log(self, paper_session: str) -> bytes:
        assert self.owned_session_id == paper_session
        return (self.evidence_dir / (paper_session + ".log")).read_bytes()

    def stop_and_save(self) -> StoppedWorldReceipt:
        self.stop_count += 1
        prior = self.owned_session_id
        assert prior is not None
        self.owned_session_id = None
        return StoppedWorldReceipt(
            self.world_id, "native-test", prior, 100 * self.stop_count,
            f"paper-main-thread:p0d:test-{self.stop_count}",
            f"owned-process-log:{prior}", 0, True,
        )

    def restart_same_source_world(self) -> RestartedWorldReceipt:
        assert self.owned_session_id is None
        self.owned_session_id = "paper-2"
        return RestartedWorldReceipt(self.world_id, "native-test", "paper-2", True)


class FakeNative:
    def __init__(self):
        self.configs = {
            sid: MineflayerLaunchConfig(
                host="127.0.0.1", port=48123, username="Relay" + sid,
                version="1.21.8",
            ) for sid in ("A", "B")
        }
        self.sessions = {
            sid: SimpleNamespace(started=SimpleNamespace(session_id="old-" + sid))
            for sid in ("A", "B")
        }
        self.prepared = {}

    def participants_now(self):
        return tuple(
            StopParticipant(sid, session) for sid, session in sorted(self.sessions.items())
        )

    async def prepare_rejoin(self, sid: str, paper_session: str, old: str):
        assert paper_session == "paper-2"
        assert old == "old-" + sid
        fresh = "fresh-" + sid
        self.prepared[sid] = fresh
        self.sessions[sid] = SimpleNamespace(started=SimpleNamespace(session_id=fresh))
        return fresh

    def prepared_receipt(self, sid: str, paper_session: str, old: str):
        return SimpleNamespace(new_native_session_id=self.prepared[sid])


def _fixture(tmp_path):
    world = tmp_path / "world"
    world.mkdir()
    world_id = str(uuid.uuid4())
    (world / "uid.dat").write_bytes(uuid.UUID(world_id).bytes)
    (world / "level.dat").write_bytes(b"fake-NBT")
    owner = FakePaper(tmp_path, world_id)
    native = FakeNative()
    physical = PhysicalIssueAdmission({"A": "old-A", "B": "old-B"})
    stop_dir = owner.evidence_dir / "stop"
    stop_dir.mkdir()
    return owner, native, physical, world, world_id, stop_dir


def test_native_only_two_cycle_protocol_barrier_with_stopped_world_hashes(
    tmp_path: Path, monkeypatch,
):
    owner, native, physical, world, world_id, stop_dir = _fixture(tmp_path)
    stop_events = []

    async def fake_stop(admission, *, participants, audit_dir, timeout_s):
        assert not admission.closed
        assert len(participants) == 2
        assert [p.self_id for p in participants] == ["A", "B"]
        stop_events.append(tuple(
            p.session.started.session_id for p in participants
        ))
        n = len(stop_events)
        receipt = audit_dir / f"stop-{n}.verified.json"
        receipt.write_text("verified only in fake test\n", encoding="utf-8")
        return StopCohortReady(
            f"physical-cohort-{n}", ("A", "B"), (receipt,),
        )

    monkeypatch.setattr(
        "experiments.p0d_real_two_native_smoke_dev.prepare_stop_before_autosave",
        fake_stop,
    )
    steps = asyncio.run(run_native_two_cycle_smoke(
        owner=owner, native=native, physical=physical,
        world_root=tmp_path, world_dir=world,
        stop_audit_dir=stop_dir, evidence_dir=owner.evidence_dir,
        world_id=world_id, timeout_s=60,
    ))
    assert len(steps) == 2
    assert stop_events == [("old-A", "old-B"), ("fresh-A", "fresh-B")]
    assert steps[0]["paper_session_id"] == "paper-1"
    assert steps[1]["paper_session_id"] == "paper-2"
    assert steps[0]["native_rejoined_sessions"] == {"A": "fresh-A", "B": "fresh-B"}
    assert steps[1]["same_world_uuid"]
    assert steps[0]["cognitive_state_saved"] is False
    assert (owner.evidence_dir / "native-cycle-2-world" / "world" / "level.dat").is_file()
    assert owner.owned_session_id is None
    assert physical.closed


def test_wrong_stop_fence_holds_before_any_world_save(tmp_path: Path, monkeypatch):
    owner, native, physical, world, world_id, stop_dir = _fixture(tmp_path)

    async def wrong_stop(admission, *, participants, audit_dir, timeout_s):
        receipt = audit_dir / "wrong.verified.json"
        receipt.write_text("wrong fence", encoding="utf-8")
        return StopCohortReady("foreign-fence", ("A", "B"), (receipt,))

    monkeypatch.setattr(
        "experiments.p0d_real_two_native_smoke_dev.prepare_stop_before_autosave",
        wrong_stop,
    )
    with pytest.raises(TwoNativePaperRefusal, match="fence refs differ"):
        asyncio.run(run_native_two_cycle_smoke(
            owner=owner, native=native, physical=physical,
            world_root=tmp_path, world_dir=world, stop_audit_dir=stop_dir,
            evidence_dir=owner.evidence_dir, world_id=world_id, timeout_s=60,
        ))
    assert owner.stop_count == 0
    assert physical.closed


def test_missing_second_player_never_enters_stop(tmp_path: Path, monkeypatch):
    owner, native, physical, world, world_id, stop_dir = _fixture(tmp_path)
    owner.omit_b = True
    (owner.evidence_dir / "paper-1.log").write_text(
        "RelayA joined the game\n", encoding="utf-8",
    )

    async def forbidden(*args, **kwargs):
        raise AssertionError("STOP must not be issued if second native actor is absent")

    monkeypatch.setattr(
        "experiments.p0d_real_two_native_smoke_dev.prepare_stop_before_autosave",
        forbidden,
    )
    with pytest.raises(TwoNativePaperRefusal, match="both native player"):
        asyncio.run(run_native_two_cycle_smoke(
            owner=owner, native=native, physical=physical,
            world_root=tmp_path, world_dir=world, stop_audit_dir=stop_dir,
            evidence_dir=owner.evidence_dir, world_id=world_id, timeout_s=60,
        ))
    assert physical.closed
    assert owner.stop_count == 0
