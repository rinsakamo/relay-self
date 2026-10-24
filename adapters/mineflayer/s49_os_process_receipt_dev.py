"""S49 native-OS event log → W3/W4 local receipt linkage, offline DEV.

Replays an existing OS fixture audit JSONL and the original sealed W3
receipt without starting any process. PID + Linux /proc starttime is a
local process identifier, not a signed original issuer/custody credential.
The pre-existing OS events are self-recorded by the Python test fixture.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.self_world_stage_w3_capture import (
    W3CaptureRejected,
    audit_w3_sealed_stdout,
)

_MAX_BYTES = 131072
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ALLOWED = frozenset({
    "spawn", "independent_observer_ack", "wait_enter", "wait_return",
    "final_process", "w3_receipt", "owner_cleanup_settled",
})


def _read_original(path: Path) -> bytes:
    if not isinstance(path, Path) or not path.is_absolute():
        raise BoundaryRejected("absolute native OS original log path required")
    for item in (path, *path.parents):
        try:
            if stat.S_ISLNK(item.lstat().st_mode):
                raise BoundaryRejected("native OS evidence path uses symlink")
        except OSError as exc:
            raise BoundaryRejected("native OS evidence path absent") from exc
    fd = -1
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
                or not 0 < st.st_size <= _MAX_BYTES):
            raise BoundaryRejected("native OS evidence not bounded single-link file")
        data = os.read(fd, _MAX_BYTES + 1)
        after = os.fstat(fd)
        path_st = path.stat(follow_symlinks=False)
        if (len(data) != st.st_size
                or (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
                != (path_st.st_dev, path_st.st_ino, path_st.st_size,
                    path_st.st_mtime_ns)):
            raise BoundaryRejected("native OS evidence changed during original read")
        if not data.endswith(b"\n") or b"\r" in data:
            raise BoundaryRejected("incomplete or altered native OS event stream")
        return data
    except OSError as exc:
        raise BoundaryRejected("native OS evidence original read failed") from exc
    finally:
        if fd != -1:
            os.close(fd)


def _event_rows(data: bytes) -> list[dict]:
    if len(data.splitlines()) not in range(4, 129):
        raise BoundaryRejected("native OS event audit length out of bounds")
    result = []
    test_id = None
    for line in data.splitlines():
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, ValueError) as exc:
            raise BoundaryRejected("invalid native OS original JSONL") from exc
        if (type(row) is not dict or row.get("event") not in _ALLOWED
                or type(row.get("test")) is not str or not row["test"]
                or type(row.get("python")) is not str or not row["python"]
                or type(row.get("utc")) is not str):
            raise BoundaryRejected("malformed native OS event envelope")
        try:
            date = datetime.fromisoformat(row["utc"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise BoundaryRejected("invalid OS event timestamp label") from exc
        if date.utcoffset() is None:
            raise BoundaryRejected("native OS event timestamp has no timezone")
        if test_id is None:
            test_id = row["test"]
        elif test_id != row["test"]:
            raise BoundaryRejected("mixed native OS evidence test IDs")
        result.append(row)
    return result


def _proc_starttime(row: dict, *, pid: int, starttime: str) -> bool:
    original = row.get("proc_stat")
    if type(original) is not str or not original.startswith(str(pid) + " ("):
        return False
    fields = original.rsplit(")", 1)
    if len(fields) != 2:
        return False
    rest = fields[1].split()
    return len(rest) >= 20 and rest[19] == starttime


def review_s49_os_process_receipt_dev(
    *, native_os_log: Path, w3_root: Path,
    producer_review: dict, w4_epoch_review: dict,
) -> dict:
    """Cross-check local process/reap record and a W3 receipt.

    A passing shape only says that one self-emitted OS test record has a
    coherent PID/starttime lifetime and references a matching W3 receipt.
    No original live S49 process/World, independent witness or external
    physical issuer identity is authenticated.
    """
    if (type(producer_review) is not dict or type(w4_epoch_review) is not dict
            or producer_review.get("schema")
            != "S49_EXISTING_W3_PAPER_PRODUCER_FILES_DEV_V1"
            or producer_review.get("status")
            != "LOCAL_PRODUCER_FILE_CONTENT_BOUND_ONLY"
            or w4_epoch_review.get("schema")
            != "S49_W4_LOCAL_READ_EPOCH_SOURCE_DEV_V1"
            or w4_epoch_review.get("status")
            != "LOCAL_ACTION_READ_EPOCH_SHAPE_ONLY"
            or producer_review.get("session_id") != w4_epoch_review.get("session_id")
            or producer_review.get("action_id") != w4_epoch_review.get("action_id")
            or producer_review.get("w3_typed_frame_line_sha256")
            != w4_epoch_review.get("w3_typed_frame_line_sha256")
            or producer_review.get("raw_native_tcp_attested") is not False
            or w4_epoch_review.get("os_process_identity_attested") is not False
            or w4_epoch_review.get("external_custody_qualified") is not False):
        raise BoundaryRejected("W3/W4 provenance or scope invalid")
    if not isinstance(w3_root, Path) or not w3_root.is_absolute():
        raise BoundaryRejected("absolute W3 receipt root required")
    try:
        receipt = audit_w3_sealed_stdout(w3_root)
        receipt_raw = (w3_root / "w3-node-stdout-receipt.json").read_bytes()
    except (W3CaptureRejected, OSError, ValueError) as exc:
        raise BoundaryRejected("W3 original receipt unavailable or corrupt") from exc
    if (receipt.get("session_id") != producer_review.get("session_id")
            or receipt.get("stdout_sha256") != producer_review.get("w3_stdout_sha256")):
        raise BoundaryRejected("OS/W3 source not the correlated original")
    data = _read_original(native_os_log)
    rows = _event_rows(data)
    relevant = {}
    for row in rows:
        kind = row["event"]
        if kind in relevant and kind not in {"wait_enter", "owner_cleanup_settled"}:
            raise BoundaryRejected("ambiguous duplicated OS event or receipt")
        if kind not in {"wait_enter", "owner_cleanup_settled"}:
            relevant[kind] = row
    required = {"spawn", "wait_return", "final_process", "w3_receipt"}
    if not required.issubset(relevant):
        raise BoundaryRejected("OS process/W3 receipt lineage incomplete")
    spawn, waited, final, original = (relevant[k] for k in
                                      ("spawn", "wait_return", "final_process", "w3_receipt"))
    pid, starttime = spawn.get("pid"), spawn.get("starttime")
    if (type(pid) is not int or pid <= 1
            or type(starttime) is not str or not starttime.isdecimal()
            or starttime.startswith("0")
            or type(spawn.get("parent_pid")) is not int
            or spawn["parent_pid"] <= 1
            or type(spawn.get("argv")) is not list or not spawn["argv"]
            or not all(type(item) is str and item for item in spawn["argv"])
            or not _proc_starttime(spawn, pid=pid, starttime=starttime)):
        raise BoundaryRejected("native OS spawn identity not bound to original proc stat")
    for entry in (waited, final):
        if (type(entry.get("pid")) is not int or entry["pid"] != pid
                or type(entry.get("starttime")) is not str
                or entry["starttime"] != starttime
                or type(entry.get("returncode")) is not int
                or entry["returncode"] != 0
                or entry.get("proc_absent") is not True):
            raise BoundaryRejected("OS PID reused, exit absent or unreaped")
    if type(waited.get("result")) is not int or waited["result"] != 0:
        raise BoundaryRejected("OS wait() did not confirm clean reap")
    if "independent_observer_ack" in relevant:
        obs = relevant["independent_observer_ack"]
        if (type(obs.get("pid")) is not int or obs["pid"] != pid
                or obs.get("starttime") != starttime):
            raise BoundaryRejected("OS observer ACK claimed another process")
    if ("owner_cleanup_settled" in (row["event"] for row in rows)
            and any(row.get("pending_tasks") != [] for row in rows
                    if row["event"] == "owner_cleanup_settled")):
        raise BoundaryRejected("original owner has pending cleanup tasks")
    if (original.get("path")
            != str(w3_root / "w3-node-stdout-receipt.json")
            or type(original.get("sha256")) is not str
            or _HEX.fullmatch(original["sha256"]) is None
            or original["sha256"] != hashlib.sha256(receipt_raw).hexdigest()
            or original.get("content") != receipt):
        raise BoundaryRejected("native OS W3 receipt event differs from sealed original")
    positions = {key: rows.index(relevant[key]) for key in required}
    if not (positions["spawn"] < positions["wait_return"]
            < positions["final_process"] < positions["w3_receipt"]):
        raise BoundaryRejected("process lifecycle/receipt event ordering invalid")
    return {
        "schema": "S49_OS_LOCAL_PROCESS_W3_W4_RECEIPT_DEV_V1",
        "status": "OS_EVENT_LOG_AND_W3_RECEIPT_SHAPE_ONLY",
        "action_id": producer_review["action_id"],
        "session_id": receipt["session_id"],
        "w4_local_epoch": w4_epoch_review["local_read_epoch"],
        "os_event_log_sha256": hashlib.sha256(data).hexdigest(),
        "os_recorded_pid": pid,
        "os_recorded_proc_starttime": starttime,
        "w3_receipt_sha256": original["sha256"],
        "w3_stdout_sha256": receipt["stdout_sha256"],
        "os_observer_ack_in_local_log": "independent_observer_ack" in relevant,
        "os_observer_identity_independently_authenticated": False,
        "os_process_identity_attested": False,
        "os_pid_reap_real_world_attested": False,
        "original_s49_owner_process_to_w3_bound": False,
        "native_stdout_producer_attested": False,
        "w4_read_epoch_independently_attested": False,
        "paper_source_process_attested": False,
        "cross_source_issuer_epoch_attested": False,
        "clear_caused_paper_back_off": "NOT_ATTESTED",
        "all_action_issuers_idle": "NOT_ATTESTED",
        "whole_tick_self_inactivity": "NOT_ATTESTED",
        "source_bound_tick": None,
        "wait_interval_ref": None,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "qualification_go": False,
        "science_go": False,
    }
