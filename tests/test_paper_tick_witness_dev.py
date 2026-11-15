"""#860: adversarial Paper main-thread tick spool and owned-process provenance."""
from __future__ import annotations

import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.paper_tick_witness_dev import (
    PaperMainThreadTickReader,
    PaperTickWitnessError,
)

WORLD_UUID = "aaaabbbb-1111-4222-8333-444455556666"


def _spool(tmp_path: Path) -> Path:
    root = tmp_path / "p0d-ticks"
    (root / "requests").mkdir(parents=True)
    (root / "acks").mkdir()
    return root


def _run_witness(
    root: Path,
    log: dict[str, bytes],
    *, boot: str, tick: str = "110", world: str = WORLD_UUID,
    echoed_session: str | None = None, echoed_nonce: str | None = None,
    source: str = "PAPER_MAIN_THREAD", write_log: bool = True,
):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        matches = list((root / "requests").glob("*.request"))
        if matches:
            request = matches[0]
            data = dict(x.split("=", 1) for x in request.read_text().splitlines())
            # Match the real Paper plugin: consume each nonce request exactly once.
            request.rename(request.with_suffix(".handled"))
            nonce = echoed_nonce or data["nonce"]
            session = echoed_session or data["server_session_id"]
            rows = {
                "boot_id": boot, "nonce": nonce, "paper_tick": tick,
                "server_session_id": session, "source": source, "world_uuid": world,
            }
            ack = (root / "acks" / (data["nonce"] + ".ack"))
            staging = ack.with_suffix(".tmp")
            staging.write_text("".join(f"{key}={rows[key]}\n" for key in sorted(rows)))
            staging.replace(ack)
            if write_log:
                marker = (
                    f"P0D_TICK_ACK nonce={nonce} boot={boot} session={session}"
                    f" world={world} tick={tick} source={source}"
                )
                log["value"] = (
                    "[P0BRecorder] P0D_TICK_READY boot=" + boot
                    + " source=PAPER_MAIN_THREAD\n"
                    + "[P0BRecorder] " + marker + "\n"
                ).encode()
            return
        time.sleep(0.01)
    raise AssertionError("Paper witness request not created")


def _one(
    tmp_path, *, boot=None, tick="110", world=WORLD_UUID,
    echoed_session=None, echoed_nonce=None, source="PAPER_MAIN_THREAD",
    write_log=True, timeout=0.3,
):
    root = _spool(tmp_path)
    log = {"value": b""}
    server = "paper-owned-" + str(uuid.uuid4())
    boot_id = boot or str(uuid.uuid4())
    thread = threading.Thread(
        target=_run_witness,
        args=(root, log),
        kwargs={
            "boot": boot_id, "tick": tick, "world": world,
            "echoed_session": echoed_session, "echoed_nonce": echoed_nonce,
            "source": source, "write_log": write_log,
        },
    )
    reader = PaperMainThreadTickReader(
        spool_dir=root, expected_world_uuid=WORLD_UUID,
        read_owned_log=lambda _session: log["value"],
        timeout_seconds=timeout,
    )
    thread.start()
    try:
        return reader(server)
    finally:
        thread.join(timeout=4)
        assert not thread.is_alive()


def test_matching_main_thread_tick_ack_plus_owned_log(tmp_path):
    result = _one(tmp_path)
    assert result.tick == 110
    assert result.server_session_id.startswith("paper-owned-")
    assert result.source_ref.startswith("paper-main-thread:p0d:")
    assert "sha256:" in result.source_ref


@pytest.mark.parametrize(("variant", "options", "error"), [
    ("foreign-world", {"world": "aaaaaaaa-1111-4222-8333-444455556666"}, "stale/foreign"),
    ("foreign-session", {"echoed_session": "paper-owned-foreign"}, "stale/foreign"),
    ("wrong-nonce", {"echoed_nonce": "22222222-2222-4222-8222-222222222222"}, "stale/foreign"),
    ("wrong-source", {"source": "MINEFLAYER_INFERRED"}, "main-thread source"),
    ("malformed-tick", {"tick": "00110"}, "noncanonical Paper tick"),
    ("missing-log", {"write_log": False}, "ACK/log not correlated"),
])
def test_forged_or_unmatched_paper_tick_witness_holds(tmp_path, variant, options, error):
    with pytest.raises(PaperTickWitnessError, match=error):
        _one(tmp_path, **options)


def test_same_plugin_boot_id_cannot_qualify_two_different_paper_processes(tmp_path):
    root = _spool(tmp_path)
    shared_log = {"value": b""}
    shared_boot = str(uuid.uuid4())
    reader = PaperMainThreadTickReader(
        spool_dir=root, expected_world_uuid=WORLD_UUID,
        read_owned_log=lambda _sid: shared_log["value"],
        timeout_seconds=0.5,
    )

    def one_process():
        session = "paper-owned-" + str(uuid.uuid4())
        worker = threading.Thread(
            target=_run_witness,
            args=(root, shared_log), kwargs={"boot": shared_boot},
        )
        worker.start()
        try:
            return reader(session)
        finally:
            worker.join(timeout=4)
            assert not worker.is_alive()

    assert one_process().tick == 110
    with pytest.raises(PaperTickWitnessError, match="stale/foreign boot"):
        one_process()


def test_acked_tick_refuses_reuse_of_same_paper_session(tmp_path):
    root = _spool(tmp_path)
    state = {"value": b""}
    session = "paper-owned-" + str(uuid.uuid4())
    reader = PaperMainThreadTickReader(
        spool_dir=root, expected_world_uuid=WORLD_UUID,
        read_owned_log=lambda _sid: state["value"],
        timeout_seconds=0.5,
    )
    worker = threading.Thread(
        target=_run_witness,
        args=(root, state), kwargs={"boot": str(uuid.uuid4())},
    )
    worker.start()
    assert reader(session).tick == 110
    worker.join(timeout=4)
    with pytest.raises(PaperTickWitnessError, match="reused"):
        reader(session)


def test_no_ack_in_bounded_window_cannot_create_paper_tick(tmp_path):
    root = _spool(tmp_path)
    reader = PaperMainThreadTickReader(
        spool_dir=root, expected_world_uuid=WORLD_UUID,
        read_owned_log=lambda _sid: b"no plugin observed",
        timeout_seconds=0.06,
    )
    with pytest.raises(PaperTickWitnessError, match="bounded timeout"):
        reader("paper-owned-" + str(uuid.uuid4()))


def test_owned_process_source_tick_join_over_two_real_os_process_restarts(tmp_path):
    """Real OS child process; it EMULATES the plugin and Paper console only."""
    world = tmp_path / "world"
    world.mkdir()
    (world / "level.dat").write_bytes(b"simulated level")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    spool = _spool(tmp_path)
    fake = tmp_path / "faux_paper_with_p0d.py"
    fake.write_text(
        "import os,select,sys,time,uuid\n"
        "from pathlib import Path\n"
        "root=Path(sys.argv[1]); world=sys.argv[2]\n"
        "boot=str(uuid.uuid4()); tick=110\n"
        "print('Done (0.8s)',flush=True)\n"
        "print(f'P0D_TICK_READY boot={boot} source=PAPER_MAIN_THREAD',flush=True)\n"
        "while True:\n"
        "    for request in (root/'requests').glob('*.request'):\n"
        "        d=dict(x.split('=',1) for x in request.read_text().splitlines())\n"
        "        request.rename(request.with_suffix('.handled'))\n"
        "        nonce=d['nonce']; session=d['server_session_id']\n"
        "        body=(f'boot_id={boot}\\nnonce={nonce}\\npaper_tick={tick}\\n'\n"
        "              f'server_session_id={session}\\nsource=PAPER_MAIN_THREAD\\n'\n"
        "              f'world_uuid={world}\\n')\n"
        "        (root/'acks'/(nonce+'.ack')).write_text(body)\n"
        "        print(f'P0D_TICK_ACK nonce={nonce} boot={boot} '\n"
        "              f'session={session} world={world} tick={tick} '\n"
        "              'source=PAPER_MAIN_THREAD',flush=True)\n"
        "    if select.select([sys.stdin],[],[],.02)[0]:\n"
        "        for cmd in os.read(sys.stdin.fileno(),4096).decode().splitlines():\n"
        "            if cmd=='save-all flush': print('Saved the game',flush=True)\n"
        "            if cmd=='stop':\n"
        "                print('Stopping server',flush=True); sys.exit(0)\n",
        encoding="utf-8",
    )
    owner_ref = {}

    def owned_log(session):
        return owner_ref["owner"].read_owned_log(session)

    reader = PaperMainThreadTickReader(
        spool_dir=spool, expected_world_uuid=WORLD_UUID,
        read_owned_log=owned_log, timeout_seconds=2,
    )
    owner = OwnedPaperWorld(
        server_dir=tmp_path, world_dir=world, evidence_dir=evidence,
        command=(sys.executable, "-u", str(fake), str(spool), WORLD_UUID),
        world_id="world-1", branch_id="source",
        tick_readback=reader, timeout_seconds=3,
    )
    owner_ref["owner"] = owner
    try:
        first = owner.start_owned()
        receipt1 = owner.stop_and_save()
        assert receipt1.old_server_session_id == first
        assert receipt1.tick_source_ref.startswith("paper-main-thread:p0d:")
        second = owner.restart_same_source_world().new_server_session_id
        receipt2 = owner.stop_and_save()
        assert second != first
        assert receipt2.old_server_session_id == second
        assert receipt2.tick_source_ref != receipt1.tick_source_ref
        assert receipt2.logical_tick == 110
        assert not owner.held_uncertain
    finally:
        if owner.owned_session_id is not None:
            owner.stop_and_save()
