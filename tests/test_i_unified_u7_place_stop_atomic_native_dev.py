"""U7: original PLACE quarantine STOP and final synchronous native write race guards.

Only synthetic original Owner, WAL, and FakeProcess/native stdin are used.
No authenticated real Native/Paper/World receipt or STOP settlement is claimed.
"""
from __future__ import annotations

import asyncio
import json
import threading
from types import SimpleNamespace

import pytest

from adapters.mineflayer.process_session import (
    MineflayerEffectAdmissionError,
    MineflayerProcessSession,
)
from relay_self.physical_action_journal import _exclusive
from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from test_i_unified_original_place_custody_dev import (
    _bind,
    _lease,
    _prepare,
    _rechecksum,
    _setup,
)
from test_mineflayer_process_session import FakeProcess, started_line


def _submit(gate, owner, action_id, effect="look", *, write=None):
    gate.submit_native_effect(
        self_id="A", native_session_id=owner.native_session_id,
        effect=effect, action_id=action_id,
        write=write if write is not None else lambda: None,
    )


def test_stop_is_denied_without_previously_submitted_start(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    parent = typed[0].action_id
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _submit(gate, owner, parent + "-look")
        gate.quarantine_resident(
            self_id="A", native_session_id=owner.native_session_id,
        )
        emitted = []
        with pytest.raises(PhysicalIssueFenceError):
            _submit(
                gate, owner, parent + "-stop", "clear_controls",
                write=lambda: emitted.append("stop"),
            )
        assert emitted == []
    assert journal.unresolved


def test_quarantined_stop_works_after_original_cognition_fence_and_wal_drift(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    parent = typed[0].action_id
    emitted = []
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _submit(gate, owner, parent + "-start", "set_control",
                write=lambda: emitted.append("start"))
        gate.quarantine_resident(
            self_id="A", native_session_id=owner.native_session_id,
        )
        bridge.cognitive_work.fence_self("A")
        # WAL may be tampered/replaced after START, but refusing STOP would
        # leave movement running. No new Action/source permission is granted.
        _rechecksum(
            journal.path,
            lambda body: body["actions"][0].__setitem__(
                "action_id", "modified-history-after-start",
            ),
        )
        for effect, action_id in (
            ("set_control", parent + "-start"),
            ("look", parent + "-look"),
            ("clear_controls", "another-stop"),
        ):
            with pytest.raises(PhysicalIssueFenceError):
                _submit(
                    gate, owner, action_id, effect,
                    write=lambda: emitted.append("wrong"),
                )
        with pytest.raises(PhysicalIssueFenceError):
            gate.submit_native_effect(
                self_id="A", native_session_id="wrong-native",
                effect="clear_controls", action_id=parent + "-stop",
                write=lambda: emitted.append("foreign"),
            )
        _submit(gate, owner, parent + "-stop", "clear_controls",
                write=lambda: emitted.append("stop"))
        with pytest.raises(PhysicalIssueFenceError):
            _submit(gate, owner, parent + "-stop", "clear_controls",
                    write=lambda: emitted.append("replay"))
    assert emitted == ["start", "stop"]
    assert journal.unresolved


def test_quarantine_wins_before_start_no_native_write(tmp_path, monkeypatch):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    parent = typed[0].action_id
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        gate.quarantine_resident(
            self_id="A", native_session_id=owner.native_session_id,
        )
        emitted = []
        with pytest.raises(PhysicalIssueFenceError):
            _submit(gate, owner, parent + "-start", "set_control",
                    write=lambda: emitted.append("start"))
        with pytest.raises(PhysicalIssueFenceError):
            _submit(gate, owner, parent + "-stop", "clear_controls",
                    write=lambda: emitted.append("stop"))
        assert emitted == []


def test_original_physical_quarantine_cannot_split_check_from_native_write(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    parent = typed[0].action_id
    started, finished = threading.Event(), threading.Event()
    threads = []
    emitted = []

    def quarantine():
        started.set()
        gate.quarantine_resident(
            self_id="A", native_session_id=owner.native_session_id,
        )
        finished.set()

    def write_native():
        worker = threading.Thread(target=quarantine)
        threads.append(worker)
        worker.start()
        assert started.wait(timeout=5)
        # The physical gate is held continuously by final admission +
        # synchronous native write, so quarantine cannot run between them.
        assert not finished.wait(timeout=0.03)
        emitted.append("look")

    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _submit(gate, owner, parent + "-look", write=write_native)
        assert finished.wait(timeout=5)
        with pytest.raises(PhysicalIssueFenceError):
            _submit(gate, owner, parent + "-start", "set_control",
                    write=lambda: emitted.append("start"))
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert emitted == ["look"]


def test_original_wal_writer_cannot_split_final_native_write(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    started, acquired = threading.Event(), threading.Event()
    threads = []
    emitted = []

    def conflicting_writer():
        started.set()
        with _exclusive(journal.path):
            acquired.set()

    def write_native():
        worker = threading.Thread(target=conflicting_writer)
        threads.append(worker)
        worker.start()
        assert started.wait(timeout=5)
        # Original canonical .lock is held through the entire write.
        assert not acquired.wait(timeout=0.03)
        emitted.append("look")

    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _submit(gate, owner, typed[0].action_id + "-look",
                write=write_native)
        assert acquired.wait(timeout=5)
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert emitted == ["look"]


def test_failed_native_write_consumes_child_and_does_not_resolve_wal(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    parent = typed[0].action_id
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)

        def fail_write():
            raise BrokenPipeError("native process exited at byte write")

        with pytest.raises(BrokenPipeError):
            _submit(gate, owner, parent + "-look", write=fail_write)
        with pytest.raises(PhysicalIssueFenceError):
            _submit(gate, owner, parent + "-look")
    assert journal.unresolved


def test_rechecksummed_prepared_wal_denied_at_atomic_writer_not_buffered(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    parent = typed[0].action_id
    with _lease(gate, owner, typed):
        _prepare(journal, typed)
        _bind(gate, bridge, owner, journal, typed)
        _rechecksum(
            journal.path,
            lambda body: body["actions"][0].__setitem__(
                "action_id", "rehashed-old-S1-after-bind",
            ),
        )
        emitted = []
        with pytest.raises(PhysicalIssueFenceError):
            _submit(
                gate, owner, parent + "-look",
                write=lambda: emitted.append("forged"),
            )
        assert emitted == []


def test_real_python_native_send_uses_atomic_callback_and_emergency_stop(
    tmp_path, monkeypatch,
):
    bridge, owner, gate, journal, typed = _setup(tmp_path, monkeypatch)
    proc = FakeProcess([started_line()])
    session = MineflayerProcessSession(proc)
    # Source-scoped synthetic native identity, not a real spawned process.
    session._started = SimpleNamespace(session_id=owner.native_session_id)
    session.install_effect_admission(
        lambda sid, effect, action_id: gate.require_native_effect(
            self_id="A", native_session_id=sid,
            effect=effect, action_id=action_id,
        )
    )
    session.install_atomic_effect_sender(
        lambda sid, effect, action_id, writer: gate.submit_native_effect(
            self_id="A", native_session_id=sid,
            effect=effect, action_id=action_id, write=writer,
        )
    )
    with pytest.raises(MineflayerEffectAdmissionError):
        session.install_atomic_effect_sender(lambda *_: None)

    async def run():
        parent = typed[0].action_id
        with _lease(gate, owner, typed):
            _prepare(journal, typed)
            _bind(gate, bridge, owner, journal, typed)
            await session.send_look(parent + "-look", yaw=0.0, pitch=0.0)
            await session.send_set_control(
                parent + "-start", control="forward", state=True,
            )
            gate.quarantine_resident(
                self_id="A", native_session_id=owner.native_session_id,
            )
            bridge.cognitive_work.fence_self("A")
            with pytest.raises(PhysicalIssueFenceError):
                await session.send_set_control(
                    "forged-start", control="forward", state=True,
                )
            await session.send_clear_controls(parent + "-stop")
            with pytest.raises(PhysicalIssueFenceError):
                await session.send_clear_controls(parent + "-stop")
        assert journal.unresolved

    asyncio.run(run())
    assert [json.loads(b)["effect"] for b in proc.stdin.writes] == [
        "look", "set_control", "clear_controls",
    ]
    assert proc.stdin.drain_count == 3
