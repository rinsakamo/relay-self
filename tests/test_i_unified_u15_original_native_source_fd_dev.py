"""U15 same-process original Native stdout file-descriptor custody tests.

These are OS file probes, not a real Mineflayer child or World. The original
MineflayerProcessSession owns the raw FD; its outer World harness must start
the capture only once before both Q4 Actions, then close/freeze it afterward.
"""
from __future__ import annotations

import os

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from relay_self.i_lane_i4a_s2_owned_native_runner_dev import (
    I4AS2OwnedNativeHold,
    require_i4a_s2_owned_native_source_audit,
)


def _session(fd):
    native = object.__new__(MineflayerProcessSession)
    native._raw_source_audit_fd = fd
    native._raw_source_audit_finished = False
    return native


def test_native_stdout_original_fd_remains_one_capture_for_two_actions(tmp_path):
    path = tmp_path / "original-native.jsonl"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        native = _session(fd)
        require_i4a_s2_owned_native_source_audit(native, path)
        os.write(fd, b'{"effect":"first"}\n')
        os.fsync(fd)
        require_i4a_s2_owned_native_source_audit(native, path)
        os.write(fd, b'{"effect":"second"}\n')
        os.fsync(fd)
        assert b"first" in path.read_bytes()
        assert b"second" in path.read_bytes()
        assert native._raw_source_audit_fd == fd
        assert not native._raw_source_audit_finished
    finally:
        os.close(fd)


@pytest.mark.parametrize("fault", [
    "replaced", "foreign_path", "symlink", "mode", "closed", "wrong_type",
])
def test_original_native_stdout_source_cannot_be_swapped_or_reused(
    tmp_path, fault,
):
    path = tmp_path / "original-native.jsonl"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        native = _session(fd)
        suspect = path
        if fault == "replaced":
            path.unlink()
            path.write_text('{"forged":true}\n', encoding="utf-8")
        elif fault == "foreign_path":
            suspect = tmp_path / "other.jsonl"
            suspect.write_text("{}\n", encoding="utf-8")
            suspect.chmod(0o600)
        elif fault == "symlink":
            suspect = tmp_path / "alias.jsonl"
            suspect.symlink_to(path)
        elif fault == "mode":
            path.chmod(0o644)
        elif fault == "closed":
            native._raw_source_audit_finished = True
        else:
            suspect = str(path)
        with pytest.raises(I4AS2OwnedNativeHold):
            require_i4a_s2_owned_native_source_audit(native, suspect)
    finally:
        os.close(fd)


def test_no_source_without_active_original_audit(tmp_path):
    path = tmp_path / "original-native.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    path.chmod(0o600)
    native = _session(None)
    with pytest.raises(I4AS2OwnedNativeHold, match="one original active"):
        require_i4a_s2_owned_native_source_audit(native, path)
