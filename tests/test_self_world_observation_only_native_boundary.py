"""W4 local PID/World/port close checks: no Minecraft or subprocesses."""
from __future__ import annotations

from dataclasses import asdict, replace

import pytest

import adapters.mineflayer.self_world_observation_only_native_boundary as native
from adapters.mineflayer.self_world_observation_only_lifetime import (
    ObservationOnlyLocalLifetime,
)

BOOT = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setattr(native.sys, "platform", "linux")
    monkeypatch.setattr(native, "_read_boot_id", lambda: BOOT)
    monkeypatch.setattr(native, "_read_proc_starttime", lambda pid: None)
    monkeypatch.setattr(native, "_loopback_port_can_bind", lambda port: True)
    return dict(
        java_before=native.NativePidFingerprint(1001, 30, BOOT),
        node_before=native.NativePidFingerprint(1002, 31, BOOT),
        close={
            "schema": "W4_OBSERVATION_ONLY_LOCAL_CLOSE_DEV_V1",
            "classification": "LOCAL_PRODUCER_CLOSE_ONLY",
            "errors": [],
            "java_exit": 0, "node_exit": 0,
            "java_stop_requested": True, "java_collector_settled": True,
            "node_stdout_receipt": {
                "session_id": "local-session", "status": "COMPLETE_NODE_STDOUT",
            },
            "external_custody_qualified": False,
            "physical_run_permitted": False, "science_qualified": False,
        },
        local_lifetime=ObservationOnlyLocalLifetime(
            schema="W4_OBSERVATION_ONLY_LOCAL_LIFETIME_JOIN_V1",
            exact_head="a" * 40, session_id="local-session",
            before_seq=3, after_seq=5,
            local_world_marker_sha256="b" * 64, local_game_time=1234,
        ),
        disposable_world_root=tmp_path / "w4-observe-0123456789abcdef",
        world_parent=tmp_path,
    )


def test_local_os_disposal_is_never_independent_grant(case):
    result = native.audit_observation_only_local_disposal(**case)
    data = asdict(result)
    assert data["schema"] == "W4_OBSERVATION_ONLY_NATIVE_LOCAL_DISPOSAL_V1"
    assert data["java_pid_absent"] and data["node_pid_absent"]
    assert data["loopback_bind_probe_available"]
    assert data["disposable_world_dir_absent"]
    assert data["java_pid"] == 1001 and data["node_pid"] == 1002
    assert data["port"] == 25565
    assert all(data[x] is False for x in (
        "independent_pid_owner_attested", "independent_port_lease_attested",
        "independent_world_disposal_attested", "external_grant_verified",
        "physical_run_permitted", "qualification_approved", "science_qualified",
    ))


@pytest.mark.parametrize("fault", (
    "same_pid", "java_alive", "node_alive", "pid_reused", "java_exit",
    "node_exit", "reboot", "port_busy", "world_exists", "world_symlink",
    "wrong_world_name", "wrong_port", "bool_exit", "bad_pid", "nested_root",
    "missing_stop", "missing_collector", "wrong_session", "untrusted_lifetime",
))
def test_native_disposal_denies_unconfirmed_os_cleanup(case, monkeypatch, fault):
    args = dict(case)
    if fault == "same_pid":
        args["node_before"] = replace(args["node_before"], pid=1001)
    elif fault in {"java_alive", "node_alive", "pid_reused"}:
        owner = 1001 if fault in {"java_alive", "pid_reused"} else 1002
        monkeypatch.setattr(
            native, "_read_proc_starttime",
            lambda pid: 999999 if pid == owner else None,
        )
    elif fault == "java_exit":
        args["close"]["java_exit"] = -9
    elif fault == "node_exit":
        args["close"]["node_exit"] = -15
    elif fault == "reboot":
        args["node_before"] = replace(args["node_before"], boot_id="different")
    elif fault == "port_busy":
        monkeypatch.setattr(native, "_loopback_port_can_bind", lambda port: False)
    elif fault == "world_exists":
        args["disposable_world_root"].mkdir()
    elif fault == "world_symlink":
        args["disposable_world_root"].symlink_to(args["world_parent"])
    elif fault == "wrong_world_name":
        args["disposable_world_root"] = args["world_parent"] / "unrelated"
    elif fault == "wrong_port":
        args["port"] = 25566
    elif fault == "bool_exit":
        args["close"]["java_exit"] = False
    elif fault == "bad_pid":
        args["java_before"] = replace(args["java_before"], pid=-1)
    elif fault == "nested_root":
        args["disposable_world_root"] = (
            args["world_parent"] / "nested" / "w4-observe-0123456789abcdef"
        )
    elif fault == "missing_stop":
        args["close"]["java_stop_requested"] = False
    elif fault == "missing_collector":
        args["close"]["java_collector_settled"] = False
    elif fault == "wrong_session":
        args["close"]["node_stdout_receipt"]["session_id"] = "foreign"
    elif fault == "untrusted_lifetime":
        args["local_lifetime"] = replace(
            args["local_lifetime"], external_grant_verified=True,
        )
    with pytest.raises(native.ObservationOnlyNativeBoundaryBlocked):
        native.audit_observation_only_local_disposal(**args)


def test_capture_reads_original_linux_handle_and_denies_fakes(monkeypatch):
    monkeypatch.setattr(native.sys, "platform", "linux")
    monkeypatch.setattr(native, "_read_boot_id", lambda: BOOT)
    monkeypatch.setattr(native, "_read_proc_starttime", lambda pid: 123 if pid == 800 else None)
    class Proc:
        pid = 800
        returncode = None
    assert native.capture_original_native_pid(Proc()) == native.NativePidFingerprint(
        800, 123, BOOT
    )
    Proc.returncode = 0
    with pytest.raises(native.ObservationOnlyNativeBoundaryBlocked):
        native.capture_original_native_pid(Proc())
    Proc.returncode = None
    Proc.pid = 801
    with pytest.raises(native.ObservationOnlyNativeBoundaryBlocked):
        native.capture_original_native_pid(Proc())


def test_native_pid_gate_has_no_grant_or_launcher_argument(case):
    with pytest.raises(TypeError):
        native.audit_observation_only_local_disposal(**case, grant="fake")
    with pytest.raises(TypeError):
        native.audit_observation_only_local_disposal(**case, confirm=True)
