"""U17 CPU fixtures for original raw Native rearm join; no real World."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_VERSION,
    MineflayerAdapterStarted,
    MineflayerLaunchConfig,
    MineflayerObservation,
)
from relay_self.owned_paper_world_dev import PaperTickReceipt
from relay_self.q4_place_repeat_source_dev import (
    Q4PlaceRepeatHold,
    Q4PlaceTerminalReadback,
    verify_q4_owned_native_source_for_rearm,
)
from test_i_unified_i4a_place_lease_dev import _acks, _probes
from test_p0d_resident_move_issuer_dev import _probe


def _row(event):
    if isinstance(event, MineflayerAdapterStarted):
        payload = {
            "type": "adapter_started",
            "mineflayer_version": event.mineflayer_version,
            "config": asdict(event.config),
        }
    elif isinstance(event, MineflayerObservation):
        payload = {
            "type": "observation",
            "kind": event.kind,
            "snapshot": asdict(event.snapshot),
            "request_id": event.request_id,
        }
    else:
        payload = {
            "type": "effect_result", "action_id": event.action_id,
            "effect": event.effect, "result": event.result,
            "error": event.error,
        }
    payload.update(session_id=event.session_id, seq=event.seq)
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode()


def _source(tmp_path: Path):
    """Write synthetic exact-stream fixtures with one active FD per role."""
    sid = "native-A"
    action = "new-A"
    started = MineflayerAdapterStarted(
        sid, 0, MINEFLAYER_VERSION, MineflayerLaunchConfig(),
    )
    look, start, stop = _acks(sid, action)
    initial, first, settled = _probes(sid)
    before = [_probe(sid, i, f"old-{i}", 99 + i, 1.0) for i in range(1, 6)]
    stdout_bytes = b"".join(
        _row(item) for item in (
            started, *before, look, start, stop, initial, first, settled,
        )
    )
    stdin_events = [
        {"type": "effect", "effect": effect, "action_id": action + suffix}
        for suffix, effect in (
            ("-look", "look"), ("-start", "set_control"),
            ("-stop", "clear_controls"),
        )
    ]
    stdout = tmp_path / "stdout.jsonl"
    stdin = tmp_path / "stdin.jsonl"
    fds = []
    try:
        for path, wire in (
            (stdout, stdout_bytes),
            (stdin, b"".join(
                (json.dumps(row) + "\n").encode() for row in stdin_events
            )),
        ):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            fds.append(fd)
            os.write(fd, wire)
            os.fsync(fd)
        session = object.__new__(MineflayerProcessSession)
        session._started = started
        session._process = SimpleNamespace(pid=12345, returncode=None)
        session._bounded_place_dev_mode = True
        session._raw_source_audit_finished = False
        session._raw_source_audit_fd = fds[0]
        session._raw_stdin_audit_finished = False
        session._raw_stdin_audit_fd = fds[1]
        session._raw_stdin_audit_path = stdin
        proof = Q4PlaceTerminalReadback(
            look, start, stop, initial, first, settled,
            PaperTickReceipt("paper-1", 110, "paper-s"),
            PaperTickReceipt("paper-1", 120, "paper-m"),
            PaperTickReceipt("paper-1", 130, "paper-e"),
            250.0, 450.0,
        )
        return session, stdout, stdin, proof, fds
    except BaseException:
        for fd in fds:
            os.close(fd)
        raise


def test_u17_raw_original_native_positive_same_session(tmp_path):
    session, stdout, _stdin, proof, fds = _source(tmp_path)
    try:
        verify_q4_owned_native_source_for_rearm(
            session=session, native_stdout_path=stdout, evidence=proof,
        )
    finally:
        for fd in fds:
            os.close(fd)


@pytest.mark.parametrize("tamper", [
    "forged_stop", "repeated_start", "dropped_stop", "swapped_stdout",
    "ended_process", "closed_capture",
])
def test_u17_raw_original_rearm_rejects_nonoriginal_receipt(
    tmp_path, tamper,
):
    session, stdout, stdin, proof, fds = _source(tmp_path)
    try:
        if tamper == "forged_stop":
            proof = replace(proof, stop=replace(
                proof.stop, seq=proof.stop.seq + 1,
            ))
        elif tamper in {"repeated_start", "dropped_stop"}:
            wire = stdin.read_bytes().splitlines(keepends=True)
            if tamper == "repeated_start":
                wire.insert(2, wire[1])
            else:
                wire.pop()
            stdin.write_bytes(b"".join(wire))
            os.fsync(fds[1])
        elif tamper == "swapped_stdout":
            replacement = tmp_path / "replacement.jsonl"
            stdout.rename(replacement)
            stdout.write_bytes(replacement.read_bytes())
        elif tamper == "ended_process":
            session._process.returncode = -15
        elif tamper == "closed_capture":
            session._raw_source_audit_finished = True
        with pytest.raises(Q4PlaceRepeatHold):
            verify_q4_owned_native_source_for_rearm(
                session=session, native_stdout_path=stdout, evidence=proof,
            )
    finally:
        for fd in fds:
            os.close(fd)
