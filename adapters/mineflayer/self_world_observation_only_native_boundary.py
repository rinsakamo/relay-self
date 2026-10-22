"""W4 real-host LOCAL PID/port/world-disposal gate (read-only DEV).

No child launch, new stdout reader, grant verifier, console command, and no
deletion. Linux /proc and TCP bind are local snapshots, NOT an independently
authenticated original process, global lease or proof of a past World run.
"""
from __future__ import annotations

import re
import socket
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.self_world_observation_only_lifetime import (
    ObservationOnlyLocalLifetime,
)


class ObservationOnlyNativeBoundaryBlocked(ValueError):
    """Local physical cleanup could not be established."""


@dataclass(frozen=True, slots=True)
class NativePidFingerprint:
    pid: int
    starttime_ticks: int
    boot_id: str


@dataclass(frozen=True, slots=True)
class NativeLocalDisposalReadback:
    schema: str
    java_pid: int
    node_pid: int
    boot_id: str
    port: int
    world_dir_name: str
    java_pid_absent: bool = True
    node_pid_absent: bool = True
    loopback_bind_probe_available: bool = True
    disposable_world_dir_absent: bool = True
    classification: str = "LOCAL_OS_POSTCLOSE_SNAPSHOT_ONLY"
    independent_pid_owner_attested: bool = False
    independent_port_lease_attested: bool = False
    independent_world_disposal_attested: bool = False
    external_grant_verified: bool = False
    physical_run_permitted: bool = False
    qualification_approved: bool = False
    science_qualified: bool = False


def _read_boot_id() -> str:
    try:
        value = Path("/proc/sys/kernel/random/boot_id").read_text(
            encoding="ascii"
        ).strip()
    except OSError as exc:
        raise ObservationOnlyNativeBoundaryBlocked("Linux boot ID unavailable") from exc
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", value):
        raise ObservationOnlyNativeBoundaryBlocked("invalid Linux boot ID")
    return value


def _read_proc_starttime(pid: int) -> int | None:
    """Linux proc stat field 22; absence is distinct from unreadable state."""
    path = Path(f"/proc/{pid}/stat")
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError) as exc:
        raise ObservationOnlyNativeBoundaryBlocked("PID inspection unavailable") from exc
    if ")" not in raw:
        raise ObservationOnlyNativeBoundaryBlocked("malformed Linux process stat")
    fields = raw.rsplit(")", 1)[1].split()
    if len(fields) < 20:
        raise ObservationOnlyNativeBoundaryBlocked("incomplete Linux process stat")
    try:
        value = int(fields[19])
    except ValueError as exc:
        raise ObservationOnlyNativeBoundaryBlocked("invalid PID starttime") from exc
    if value < 0:
        raise ObservationOnlyNativeBoundaryBlocked("negative PID starttime")
    return value


def capture_original_native_pid(process: object) -> NativePidFingerprint:
    """Capture a *local* original process object's Linux PID while alive."""
    if sys.platform != "linux":
        raise ObservationOnlyNativeBoundaryBlocked("Linux/WSL2 proc required")
    pid = getattr(process, "pid", None)
    if type(pid) is not int or pid <= 1 or getattr(process, "returncode", 1) is not None:
        raise ObservationOnlyNativeBoundaryBlocked("live original child handle required")
    boot = _read_boot_id()
    start = _read_proc_starttime(pid)
    if start is None:
        raise ObservationOnlyNativeBoundaryBlocked("original child PID not visible")
    return NativePidFingerprint(pid=pid, starttime_ticks=start, boot_id=boot)


def _loopback_port_can_bind(port: int) -> bool:
    # This is a transient bind probe, NOT a port reservation for startup.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
            return sock.getsockname()[1] == port
    except OSError:
        return False


def _validate_world_target(root: Path, parent: Path) -> None:
    if (
        not isinstance(root, Path) or not root.is_absolute()
        or not isinstance(parent, Path) or not parent.is_absolute()
        or root.parent != parent
        or re.fullmatch(r"w4-observe-[0-9a-f]{16}", root.name) is None
    ):
        raise ObservationOnlyNativeBoundaryBlocked("one exact disposable World root required")
    try:
        for component in (parent, *parent.parents):
            if stat.S_ISLNK(component.lstat().st_mode):
                raise ObservationOnlyNativeBoundaryBlocked("symlink parent denied")
        if not parent.is_dir():
            raise ObservationOnlyNativeBoundaryBlocked("World parent unavailable")
        # lstat, not exists(): dangling symlink must fail, not imply cleanup.
        try:
            root.lstat()
        except FileNotFoundError:
            return
    except OSError as exc:
        raise ObservationOnlyNativeBoundaryBlocked("World root inspection unavailable") from exc
    raise ObservationOnlyNativeBoundaryBlocked("disposable World root still exists")


def audit_observation_only_local_disposal(
    *, java_before: NativePidFingerprint, node_before: NativePidFingerprint,
    close: dict[str, object], local_lifetime: ObservationOnlyLocalLifetime,
    disposable_world_root: Path, world_parent: Path, port: int = 25565,
) -> NativeLocalDisposalReadback:
    """Fail-closed local post-close snapshot; NEVER a runnable World grant.

    Both process waits must separately be documented by their original
    owner. These caller-supplied results are checked but not authenticated.
    """
    if sys.platform != "linux":
        raise ObservationOnlyNativeBoundaryBlocked("Linux/WSL2 is mandatory")
    if (
        type(java_before) is not NativePidFingerprint
        or type(node_before) is not NativePidFingerprint
        or type(java_before.pid) is not int
        or type(node_before.pid) is not int
        or java_before.pid <= 1 or node_before.pid <= 1
        or java_before.pid == node_before.pid
        or type(java_before.starttime_ticks) is not int
        or type(node_before.starttime_ticks) is not int
        or java_before.starttime_ticks < 0 or node_before.starttime_ticks < 0
        or type(port) is not int or port != 25565
    ):
        raise ObservationOnlyNativeBoundaryBlocked("native process/exit/port binding absent")
    if (
        type(close) is not dict
        or close.get("schema") != "W4_OBSERVATION_ONLY_LOCAL_CLOSE_DEV_V1"
        or close.get("classification") != "LOCAL_PRODUCER_CLOSE_ONLY"
        or close.get("errors") != []
        or type(close.get("java_exit")) is not int or close["java_exit"] != 0
        or type(close.get("node_exit")) is not int or close["node_exit"] != 0
        or close.get("java_stop_requested") is not True
        or close.get("java_collector_settled") is not True
        or type(local_lifetime) is not ObservationOnlyLocalLifetime
        or local_lifetime.schema != "W4_OBSERVATION_ONLY_LOCAL_LIFETIME_JOIN_V1"
        or local_lifetime.classification != "LOCAL_PRODUCER_LIFETIME_ONLY"
        or any(getattr(local_lifetime, field) is not False for field in (
            "external_grant_verified", "external_owner_attested",
            "external_source_qualified", "actual_pid_port_disposal_attested",
            "physical_run_permitted", "qualification_approved",
            "science_qualified",
        ))
        or any(type(getattr(local_lifetime, field)) is not int
               or getattr(local_lifetime, field) != 0 for field in (
                   "action_count", "outcome_count", "s10_update_count",
               ))
        or type(close.get("node_stdout_receipt")) is not dict
        or close["node_stdout_receipt"].get("session_id") != local_lifetime.session_id
        or close["node_stdout_receipt"].get("status") != "COMPLETE_NODE_STDOUT"
        or any(close.get(field) is not False for field in (
            "external_custody_qualified", "physical_run_permitted",
            "science_qualified",
        ))
    ):
        raise ObservationOnlyNativeBoundaryBlocked("original local close/lifetime not bound")
    boot = _read_boot_id()
    if (
        java_before.boot_id != boot
        or node_before.boot_id != boot
    ):
        raise ObservationOnlyNativeBoundaryBlocked("host boot identity changed")
    # Fail closed even for numeric PID reuse: require the PID fully absent.
    if _read_proc_starttime(java_before.pid) is not None:
        raise ObservationOnlyNativeBoundaryBlocked("Java PID still allocated")
    if _read_proc_starttime(node_before.pid) is not None:
        raise ObservationOnlyNativeBoundaryBlocked("Node PID still allocated")
    _validate_world_target(disposable_world_root, world_parent)
    if not _loopback_port_can_bind(port):
        raise ObservationOnlyNativeBoundaryBlocked("Minecraft loopback port not free")
    return NativeLocalDisposalReadback(
        schema="W4_OBSERVATION_ONLY_NATIVE_LOCAL_DISPOSAL_V1",
        java_pid=java_before.pid,
        node_pid=node_before.pid,
        boot_id=boot,
        port=port,
        world_dir_name=disposable_world_root.name,
    )
