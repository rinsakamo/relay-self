"""Default-off product opt-in for original S49 read-only clock (offline only)."""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer import s49_normal_session_real_ci as s49
from adapters.mineflayer import self_demo
from experiments.self_body_host_clock_sidecar_dev import (
    CLOCK_FILE,
    VIEWS_FILE,
    atomic_write_jsonl_new,
    verify_host_clock_source_join,
)
from test_self_dev import args
from test_self_product_passive_views import probe

SEQS = (8, 19, 47)


def native_report():
    return {
        "session_id": "p-native", "status": "PASS", "server_exit": 0,
        "node_exit": 0, "actual_native_actions": [], "decisions": [],
        "source_pair_trace": [
            {
                "event_seq": seq - 1, "probe_seq": seq,
                "probe_entities": [{"name": "zombie", "id": seq}],
            }
            for seq in SEQS
        ],
    }


def fake_owner(monkeypatch, *, created=None):
    async def qualify(report, log, *, live_probe=None):
        assert live_probe is not None
        for seq in SEQS:
            await live_probe(probe(seq))
        if created is not None:
            created.append("original-owner")
        report.write_text(json.dumps(native_report()), encoding="utf-8")
        return 0

    monkeypatch.setattr(s49, "qualify", qualify)


def rows_at(root):
    return [
        json.loads(line)
        for line in (root / CLOCK_FILE).read_text(encoding="utf-8").splitlines()
    ]


def views_at(root):
    return [
        json.loads(line)
        for line in (root / VIEWS_FILE).read_text(encoding="utf-8").splitlines()
    ]


def test_optin_fake_original_s49_single_callback_exact_source_and_sidecar(
    monkeypatch, tmp_path,
):
    seen = []
    fake_owner(monkeypatch, created=seen)
    report = tmp_path / "native_report.json"
    assert asyncio.run(self_demo._run_disposable(
        report, tmp_path / "server.log", passive_host_clock=True,
    )) == 0
    assert seen == ["original-owner"]
    views, clock = views_at(tmp_path), rows_at(tmp_path)
    assert verify_host_clock_source_join(native_report(), views, clock)
    assert [r["native_seq"] for r in clock[:-1]] == list(SEQS)
    assert all(r["sample_kind"] == "PASSIVE_CALLBACK_PROCESSING_ONLY"
               for r in clock[:-1])
    assert all(r["action_issued"] is False for r in clock[:-1])
    assert all(r["physical_timing_attested"] is False for r in clock[:-1])
    assert clock[-1]["source_qualified"] is False
    assert clock[-1]["science_qualified"] is False


def test_default_off_uses_identical_original_call_without_sidecars(
    monkeypatch, tmp_path,
):
    visits = []
    async def qualify(report, log, *, live_probe=None):
        assert live_probe is None
        visits.append("one original owner")
        return 0
    monkeypatch.setattr(s49, "qualify", qualify)
    assert asyncio.run(self_demo._run_disposable(
        tmp_path / "report.json", tmp_path / "server.log",
    )) == 0
    assert visits == ["one original owner"]
    assert not (tmp_path / CLOCK_FILE).exists()
    assert not (tmp_path / VIEWS_FILE).exists()


@pytest.mark.parametrize("conflict", [
    {"passive_self_views": True},
    {"stage_r_dev": True},
    {"raw_capture_root": Path("/tmp/raw-capture")},
    {"self_world_live": True},
    {"self_world_prospective": True},
    {"self_world_typed_closure": True},
    {"self_world_retained_handoff": True},
    {"live_model": ("model", 1234, 2.0)},
])
def test_exclusive_hook_rejected_before_original_owner(
    monkeypatch, tmp_path, conflict,
):
    async def forbidden(*a, **kw):
        raise AssertionError("must not start original owner")
    monkeypatch.setattr(s49, "qualify", forbidden)
    with pytest.raises(self_demo.DemoRejected):
        asyncio.run(self_demo._run_disposable(
            tmp_path / "report.json", tmp_path / "server.log",
            passive_host_clock=True, **conflict,
        ))
    assert not (tmp_path / CLOCK_FILE).exists()


def test_existing_legacy_passive_mode_does_not_add_clock(
    monkeypatch, tmp_path,
):
    fake_owner(monkeypatch)
    assert asyncio.run(self_demo._run_disposable(
        tmp_path / "report.json", tmp_path / "server.log",
        passive_self_views=True,
    )) == 0
    assert (tmp_path / VIEWS_FILE).exists()
    assert not (tmp_path / CLOCK_FILE).exists()


@pytest.mark.parametrize("field,value", [
    ("session_id", "foreign"),
    ("source_ref", "native-probe:other:8:forged"),
    ("native_seq", 199),
    ("sample_kind", "MOTOR_START"),
    ("clock_origin", "SYNTHETIC_DEV_CLOCK"),
    ("callback_elapsed_ns", -1),
    ("callback_elapsed_ms", 99999.0),
    ("action_issued", True),
    ("physical_timing_attested", True),
])
def test_modified_sample_fails_receipt_verifier(
    monkeypatch, tmp_path, field, value,
):
    fake_owner(monkeypatch)
    asyncio.run(self_demo._run_disposable(
        tmp_path / "report.json", tmp_path / "server.log",
        passive_host_clock=True,
    ))
    native, views, clock = native_report(), views_at(tmp_path), rows_at(tmp_path)
    tampered = deepcopy(clock)
    tampered[0][field] = value
    assert not verify_host_clock_source_join(native, views, tampered)


@pytest.mark.parametrize("field,value", [
    ("clock_samples", 2),
    ("native_probes_joined", 4),
    ("advisory_failures", 1),
    ("aborted_callbacks", 1),
    ("source_qualified", True),
    ("physical_timing_attested", True),
    ("legacy_error_overflow", 1),
])
def test_modified_summary_fails_receipt_verifier(
    monkeypatch, tmp_path, field, value,
):
    fake_owner(monkeypatch)
    asyncio.run(self_demo._run_disposable(
        tmp_path / "report.json", tmp_path / "server.log",
        passive_host_clock=True,
    ))
    native, views, clock = native_report(), views_at(tmp_path), rows_at(tmp_path)
    tampered = deepcopy(clock)
    tampered[-1][field] = value
    assert not verify_host_clock_source_join(native, views, tampered)


def test_missing_error_extra_or_replayed_sample_cannot_qualify(
    monkeypatch, tmp_path,
):
    fake_owner(monkeypatch)
    asyncio.run(self_demo._run_disposable(
        tmp_path / "report.json", tmp_path / "server.log",
        passive_host_clock=True,
    ))
    native, views, clock = native_report(), views_at(tmp_path), rows_at(tmp_path)
    for altered in (
        clock[:-2] + [clock[-1]],
        [clock[0], clock[0], clock[2], clock[-1]],
        [clock[0], clock[1], clock[2],
         {"kind": "passive_host_clock_error"}, clock[-1]],
    ):
        assert not verify_host_clock_source_join(native, views, altered)


def test_invalid_native_report_rejected_by_original_source_join(
    monkeypatch, tmp_path,
):
    fake_owner(monkeypatch)
    asyncio.run(self_demo._run_disposable(
        tmp_path / "report.json", tmp_path / "server.log",
        passive_host_clock=True,
    ))
    views, clock = views_at(tmp_path), rows_at(tmp_path)
    native = native_report()
    native["source_pair_trace"][0]["probe_seq"] += 1
    assert not verify_host_clock_source_join(native, views, clock)


def test_atomic_writer_refuses_overwrite_and_symlink(tmp_path):
    dest = tmp_path / CLOCK_FILE
    atomic_write_jsonl_new(dest, ({"kind": "evidence"},))
    first = dest.read_bytes()
    with pytest.raises(FileExistsError):
        atomic_write_jsonl_new(dest, ({"kind": "attack"},))
    assert dest.read_bytes() == first
    link = tmp_path / "clock-symlink.jsonl"
    link.symlink_to(dest)
    with pytest.raises(FileExistsError):
        atomic_write_jsonl_new(link, ({"kind": "attack"},))
    assert dest.read_bytes() == first


def test_atomic_writer_failure_cleans_temporary_file(monkeypatch, tmp_path):
    from experiments import self_body_host_clock_sidecar_dev as sidecar
    def denied(*a, **kw):
        raise OSError("simulated sidecar publication failure")
    monkeypatch.setattr(sidecar.os, "link", denied)
    with pytest.raises(OSError):
        atomic_write_jsonl_new(tmp_path / CLOCK_FILE, ({"kind": "test"},))
    assert not (tmp_path / CLOCK_FILE).exists()
    assert list(tmp_path.iterdir()) == []


def test_cancellation_keeps_original_exception_even_when_sidecar_fails(
    monkeypatch, tmp_path,
):
    from experiments import self_body_host_clock_sidecar_dev as sidecar
    async def cancelled(report, log, *, live_probe=None):
        await live_probe(probe(8))
        raise asyncio.CancelledError("original S49 cancellation")
    monkeypatch.setattr(s49, "qualify", cancelled)
    monkeypatch.setattr(sidecar, "atomic_write_jsonl_new",
                        lambda *a, **kw: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(asyncio.CancelledError, match="original S49"):
        asyncio.run(self_demo._run_disposable(
            tmp_path / "report.json", tmp_path / "server.log",
            passive_host_clock=True,
        ))
    assert not (tmp_path / CLOCK_FILE).exists()
    assert not (tmp_path / VIEWS_FILE).exists()


def test_cancelled_owner_still_writes_incomplete_clock_sidecar(
    monkeypatch, tmp_path,
):
    entered = asyncio.Event()
    cleaned = []
    async def stuck(_view):
        entered.set()
        await asyncio.Future()
    from experiments import self_body_host_clock_s49_liveprobe_dev as bridge
    original = bridge.S49PassiveHostClockDEV
    monkeypatch.setattr(bridge, "S49PassiveHostClockDEV",
                        lambda views: original(views=views, observer=stuck))

    async def qualify(report, log, *, live_probe=None):
        try:
            await live_probe(probe(8))
        finally:
            cleaned.append("cleanup")
    monkeypatch.setattr(s49, "qualify", qualify)
    async def run():
        task = asyncio.create_task(self_demo._run_disposable(
            tmp_path / "report.json", tmp_path / "server.log",
            passive_host_clock=True,
        ))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(run())
    assert cleaned == ["cleanup"]
    clock = rows_at(tmp_path)
    assert len(clock) == 2   # One error + incomplete summary.
    assert clock[0]["kind"] == "passive_host_clock_error"
    assert clock[-1]["clock_samples"] == 0
    assert clock[-1]["aborted_callbacks"] == 1
    assert not (tmp_path / "report.json").exists()


def test_cli_optin_rejected_outside_explicit_dev():
    with pytest.raises(SystemExit) as e:
        self_demo.main(["--self-passive-host-clock", "--smoke"])
    assert e.value.code == 2


def test_dev_preflight_rejects_unapproved_combinations_without_launch(
    monkeypatch, tmp_path,
):
    called = []
    async def forbidden(*a, **kw):
        called.append("owner")
        return 0
    monkeypatch.setattr(self_demo, "_run_disposable", forbidden)
    for i, flags in enumerate((
        {"self_passive_views": True},
        {"self_world_stage_r_dev": True},
        {"self_world_w3_raw_capture": True},
        {"think": True},
    )):
        a = args(tmp_path / ("blocked-" + str(i)),
                 self_passive_host_clock=True)
        for name, value in flags.items():
            setattr(a, name, value)
        assert self_demo._dev_run(a) == 2
        assert called == []


def test_dev_receipt_requires_source_and_clock_join_not_physical_qualification(
    monkeypatch, tmp_path,
):
    monkeypatch.setattr(self_demo.shutil, "which", lambda _name: "/fake-tool")
    monkeypatch.setattr(self_demo.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout="v", stderr=""))
    fake_owner(monkeypatch)
    root = tmp_path / "dev-run"
    result = self_demo._dev_run(args(
        root, self_passive_host_clock=True,
    ))
    receipt = json.loads((root / "dev_receipt.json").read_text())
    assert result == 0
    assert receipt["dev_host_clock"] == "SOURCE_JOINED_CALLBACK_DEV_ONLY"
    assert receipt["dev_host_clock_samples"] == 3
    assert receipt["engineering_qualified"] is False
    assert receipt["science_success"] is False
    assert receipt["dev_host_clock_physical_attestation"] is False
    assert (root / "SHA256SUMS").exists()


def test_failed_original_native_terminal_never_qualifies_clock(
    monkeypatch, tmp_path,
):
    monkeypatch.setattr(self_demo.shutil, "which", lambda _name: "/fake-tool")
    monkeypatch.setattr(self_demo.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout="v", stderr=""))
    async def qualified_but_failed(report, log, *, live_probe=None):
        for seq in SEQS:
            await live_probe(probe(seq))
        native = native_report()
        native["status"] = "FAILED"
        native["server_exit"] = 1
        report.write_text(json.dumps(native), encoding="utf-8")
        return 0

    monkeypatch.setattr(s49, "qualify", qualified_but_failed)
    root = tmp_path / "failed-original"
    code = self_demo._dev_run(args(root, self_passive_host_clock=True))
    receipt = json.loads((root / "dev_receipt.json").read_text())
    assert code == 1
    assert receipt["dev_host_clock"] == "UNDETERMINED"
    assert receipt["dev_host_clock_samples"] == 0
    assert receipt["dev_host_clock_physical_attestation"] is False


@pytest.mark.parametrize("attack", ["missing", "symlink", "foreign_source", "wrong_clock"])
def test_outer_dev_receipt_rejects_corrupted_host_clock_evidence(
    monkeypatch, tmp_path, attack,
):
    monkeypatch.setattr(self_demo.shutil, "which", lambda _name: "/fake-tool")
    monkeypatch.setattr(self_demo.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout="v", stderr=""))
    fake_owner(monkeypatch)
    original = self_demo._run_disposable

    async def tampered(report, log, *, passive_host_clock=False):
        assert passive_host_clock is True
        result = await original(report, log, passive_host_clock=True)
        clock_file = report.parent / CLOCK_FILE
        if attack == "missing":
            clock_file.unlink()
        elif attack == "symlink":
            clock_file.unlink()
            clock_file.symlink_to(report.parent / VIEWS_FILE)
        else:
            rows = rows_at(report.parent)
            if attack == "foreign_source":
                rows[0]["source_ref"] = "foreign-native-source"
            else:
                rows[0]["clock_origin"] = "SYNTHETIC_DEV_CLOCK"
            clock_file.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
        return result

    monkeypatch.setattr(self_demo, "_run_disposable", tampered)
    root = tmp_path / ("corrupt-" + attack)
    assert self_demo._dev_run(args(root, self_passive_host_clock=True)) != 0
    receipt = json.loads((root / "dev_receipt.json").read_text())
    assert receipt["dev_host_clock"] == "UNDETERMINED"
    assert receipt["engineering_qualified"] is False
    assert receipt["science_success"] is False


def test_default_product_dev_receipt_does_not_report_clock(
    monkeypatch, tmp_path,
):
    monkeypatch.setattr(self_demo.shutil, "which", lambda _name: "/fake-tool")
    monkeypatch.setattr(self_demo.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout="v", stderr=""))
    async def original(report, log):
        report.write_text(json.dumps(native_report()), encoding="utf-8")
        return 0

    monkeypatch.setattr(self_demo, "_run_disposable", original)
    root = tmp_path / "default-dev"
    assert self_demo._dev_run(args(root)) == 0
    receipt = json.loads((root / "dev_receipt.json").read_text())
    assert "dev_host_clock" not in receipt
    assert not (root / CLOCK_FILE).exists()


@pytest.mark.parametrize("mutation", ["foreign-self", "duplicate-request", "stale-seq",
                                     "bool-summary", "native-failure"])
def test_new_receipt_source_identity_negatives(monkeypatch, tmp_path, mutation):
    fake_owner(monkeypatch)
    asyncio.run(self_demo._run_disposable(
        tmp_path / "report.json", tmp_path / "server.log", passive_host_clock=True,
    ))
    native, views, clock = native_report(), views_at(tmp_path), rows_at(tmp_path)
    if mutation == "foreign-self":
        views[0]["self_id"] = "foreign-self"
    elif mutation == "bool-summary":
        clock[-1]["aborted_callbacks"] = False
    elif mutation == "native-failure":
        native["status"] = "FAIL"
    elif mutation == "duplicate-request":
        native["source_pair_trace"][1]["event_seq"] = SEQS[0] - 1
        request = views[0]["request_id"]
        views[1]["request_id"] = request
        views[1]["body_source_ref"] = f"native-probe:p-native:{SEQS[1]}:{request}"
        views[1]["world_source_ref"] = f"present:p-native:{SEQS[1]}:{request}"
        clock[1]["source_ref"] = views[1]["body_source_ref"]
    else:
        native["source_pair_trace"] = list(reversed(native["source_pair_trace"]))
        views = list(reversed(views[:-1])) + [views[-1]]
        clock = list(reversed(clock[:-1])) + [clock[-1]]
    assert not verify_host_clock_source_join(native, views, clock)


def test_new_atomic_record_bound(tmp_path):
    with pytest.raises(ValueError):
        atomic_write_jsonl_new(tmp_path / CLOCK_FILE, ({"x": 1},) * 100)
    assert list(tmp_path.iterdir()) == []


def test_new_atomic_primary_io_survives_cleanup_failure(monkeypatch, tmp_path):
    from experiments import self_body_host_clock_sidecar_dev as sidecar
    original_unlink = Path.unlink
    def bad_link(*a, **kw):
        raise OSError("PRIMARY publish failure")
    def bad_unlink(path, *a, **kw):
        original_unlink(path, *a, **kw)
        raise OSError("SECONDARY cleanup failure")
    monkeypatch.setattr(sidecar.os, "link", bad_link)
    monkeypatch.setattr(Path, "unlink", bad_unlink)
    with pytest.raises(OSError, match="PRIMARY"):
        atomic_write_jsonl_new(tmp_path / CLOCK_FILE, ({"x": 1},))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("stage", ["write", "flush", "fsync", "link", "directory-fsync"])
def test_new_atomic_injected_io_failure(monkeypatch, tmp_path, stage):
    import os

    from experiments import self_body_host_clock_sidecar_dev as sidecar
    original_fdopen, original_fsync = os.fdopen, os.fsync
    calls = []
    class BrokenStream:
        def __init__(self, fd):
            self.stream = original_fdopen(fd, "wb")
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            self.stream.close()
        def write(self, data):
            if stage == "write":
                raise OSError("injected write")
            return self.stream.write(data)
        def flush(self):
            if stage == "flush":
                raise OSError("injected flush")
            return self.stream.flush()
        def fileno(self):
            return self.stream.fileno()
    def fsync(fd):
        calls.append(fd)
        if stage == "fsync" or (stage == "directory-fsync" and len(calls) == 2):
            raise OSError("injected fsync")
        return original_fsync(fd)
    monkeypatch.setattr(sidecar.os, "fdopen", lambda fd, mode: BrokenStream(fd))
    monkeypatch.setattr(sidecar.os, "fsync", fsync)
    if stage == "link":
        monkeypatch.setattr(sidecar.os, "link", lambda *a: (_ for _ in ()).throw(
            OSError("injected link")))
    with pytest.raises(OSError):
        atomic_write_jsonl_new(tmp_path / CLOCK_FILE, ({"x": 1},))
    assert not list(tmp_path.glob(".*.tmp"))
    if stage == "directory-fsync":
        assert json.loads((tmp_path / CLOCK_FILE).read_text()) == {"x": 1}
    else:
        assert not (tmp_path / CLOCK_FILE).exists()


def test_new_atomic_permissions_invalid_directory_and_size(tmp_path):
    import stat
    atomic_write_jsonl_new(tmp_path / CLOCK_FILE, ({"x": 1},))
    assert stat.S_IMODE((tmp_path / CLOCK_FILE).stat().st_mode) == 0o600
    for parent in (tmp_path / "missing", tmp_path / CLOCK_FILE):
        with pytest.raises(ValueError):
            atomic_write_jsonl_new(parent / VIEWS_FILE, ({"x": 1},))
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        atomic_write_jsonl_new(alias / VIEWS_FILE, ({"x": 1},))
    with pytest.raises(ValueError):
        atomic_write_jsonl_new(tmp_path / VIEWS_FILE, ({"x": "x" * 65536},))


@pytest.mark.parametrize("damage", ["missing-views", "missing-clock", "bad-json",
                                    "huge", "partial", "symlink", "extra", "array"])
def test_new_outer_receipt_rejects_sidecar_damage(monkeypatch, tmp_path, damage):
    monkeypatch.setattr(self_demo.shutil, "which", lambda _: "/fake-tool")
    monkeypatch.setattr(self_demo.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout="v", stderr=""))
    fake_owner(monkeypatch)
    original = self_demo._run_disposable
    async def damaged(report, log, **options):
        result = await original(report, log, **options)
        clock = report.parent / CLOCK_FILE
        if damage == "missing-views":
            (report.parent / VIEWS_FILE).unlink()
        elif damage == "missing-clock":
            clock.unlink()
        elif damage == "bad-json":
            clock.write_text("{bad}\n")
        elif damage == "huge":
            clock.write_text("x" * 65537)
        elif damage == "partial":
            clock.write_bytes(clock.read_bytes().rstrip(b"\n"))
        elif damage == "symlink":
            clock.unlink()
            clock.symlink_to(report.parent / VIEWS_FILE)
        elif damage == "array":
            clock.write_text("[]\n")
        else:
            with clock.open("a") as stream:
                stream.write('{}\n' * 100)
        return result
    monkeypatch.setattr(self_demo, "_run_disposable", damaged)
    root = tmp_path / "damaged"
    assert self_demo._dev_run(args(root, self_passive_host_clock=True)) != 0
    receipt = json.loads((root / "dev_receipt.json").read_text())
    assert receipt["dev_host_clock"] == "UNDETERMINED"
    assert receipt["engineering_qualified"] is False


@pytest.mark.parametrize("interrupt", [asyncio.CancelledError, KeyboardInterrupt,
                                       SystemExit, BaseException])
@pytest.mark.parametrize("sidecar_failure", [False, True])
def test_new_interrupt_preserves_cleanup_environment_and_no_sample(
    monkeypatch, tmp_path, interrupt, sidecar_failure,
):
    import os

    from experiments import self_body_host_clock_s49_liveprobe_dev as bridge
    from experiments import self_body_host_clock_sidecar_dev as sidecar
    original = bridge.S49PassiveHostClockDEV
    terminal = interrupt("original interrupt")
    cleaned, actions = [], []
    async def interrupted(_view):
        raise terminal
    monkeypatch.setattr(bridge, "S49PassiveHostClockDEV",
                        lambda views: original(views=views, observer=interrupted))
    async def qualify(report, log, *, live_probe=None):
        try:
            await live_probe(probe(8))
            actions.append("forbidden after interrupt")
        finally:
            cleaned.append("cleanup")
    monkeypatch.setattr(s49, "qualify", qualify)
    monkeypatch.setenv("S49_REAL_SERVER_CI", "prior-owner")
    monkeypatch.setenv("S49_STAGE_R_DEV_ONLY", "prior-stage")
    if sidecar_failure:
        monkeypatch.setattr(sidecar, "atomic_write_jsonl_new", lambda *a, **kw:
                            (_ for _ in ()).throw(OSError("sidecar failure")))
    with pytest.raises(interrupt) as result:
        asyncio.run(self_demo._run_disposable(
            tmp_path / "report.json", tmp_path / "server.log", passive_host_clock=True,
        ))
    assert result.value is terminal
    assert cleaned == ["cleanup"] and actions == []
    assert os.environ["S49_REAL_SERVER_CI"] == "prior-owner"
    assert os.environ["S49_STAGE_R_DEV_ONLY"] == "prior-stage"
    assert not (tmp_path / "report.json").exists()
    if not sidecar_failure:
        clock = rows_at(tmp_path)
        assert clock[-1]["clock_samples"] == 0
        assert clock[-1]["aborted_callbacks"] == 1
        assert not any(r["kind"] == "passive_host_clock_sample" for r in clock)


def test_new_advisory_failure_keeps_fake_l0_actions_and_bounded_history(monkeypatch, tmp_path):
    from experiments import self_body_host_clock_s49_liveprobe_dev as bridge
    original = bridge.S49PassiveHostClockDEV
    async def failed(_view):
        raise RuntimeError("advisory")
    monkeypatch.setattr(bridge, "S49PassiveHostClockDEV",
                        lambda views: original(views=views, observer=failed))
    visits = []
    async def qualify(report, log, *, live_probe=None):
        try:
            for seq in SEQS:
                if live_probe is not None:
                    await live_probe(probe(seq))
                visits.append((seq, "original L0", "original fake action"))
            if live_probe is not None:
                for _ in range(20):
                    await live_probe(probe(SEQS[-1]))
            report.write_text(json.dumps(native_report()))
            return 0
        finally:
            visits.append("cleanup")
    monkeypatch.setattr(s49, "qualify", qualify)
    off, on = tmp_path / "off", tmp_path / "on"
    off.mkdir()
    on.mkdir()
    asyncio.run(self_demo._run_disposable(off / "report.json", off / "server.log"))
    expected = list(visits)
    visits.clear()
    asyncio.run(self_demo._run_disposable(on / "report.json", on / "server.log",
                                         passive_host_clock=True))
    assert visits == expected
    clock = rows_at(on)
    assert clock[-1]["clock_samples"] == 0
    assert clock[-1]["advisory_failures"] == 4
    assert clock[-1]["failure_overflow"] > 0
    assert not verify_host_clock_source_join(native_report(), views_at(on), clock)


@pytest.mark.parametrize("flags", [
    {"run_disposable": False}, {"confirm": "no"}, {"dev_scenario": "b0-ground"},
    {"self_world_live": True}, {"self_world_prospective": True},
    {"self_world_typed_closure": True}, {"self_world_retained_handoff": True},
    {"live_think": True},
])
def test_new_preflight_exclusions(monkeypatch, tmp_path, flags):
    a = args(tmp_path / "blocked", self_passive_host_clock=True)
    for name, value in flags.items():
        setattr(a, name, value)
    monkeypatch.setattr(self_demo.subprocess, "run", lambda *a, **kw: pytest.fail("process"))
    monkeypatch.setattr(self_demo, "_run_disposable", lambda *a, **kw: pytest.fail("owner"))
    assert self_demo._dev_run(a) == 2


def test_new_default_off_constructs_no_observers_and_preserves_exact_call(monkeypatch, tmp_path):
    from adapters.mineflayer import self_product_passive_views as passive
    from experiments import self_body_host_clock_s49_liveprobe_dev as bridge
    calls = []
    async def qualify(*positional, **keywords):
        calls.append((positional, keywords))
        return 0
    def forbidden(*a, **kw):
        pytest.fail("default OFF created observer")
    monkeypatch.setattr(s49, "qualify", qualify)
    monkeypatch.setattr(passive, "PassiveSelfViews", forbidden)
    monkeypatch.setattr(bridge, "S49PassiveHostClockDEV", forbidden)
    report, log = tmp_path / "report.json", tmp_path / "server.log"
    assert asyncio.run(self_demo._run_disposable(report, log)) == 0
    assert calls == [((report, log), {})]
    assert list(tmp_path.iterdir()) == []


def test_new_successful_optin_preserves_original_fake_decisions(monkeypatch, tmp_path):
    from adapters.mineflayer import process_session
    from adapters.mineflayer import self_product_passive_views as passive
    counts, decisions, snapshots = [], [], []
    original_observe = passive.PassiveSelfViews.observe
    def observe(views, reading):
        counts.append(id(reading))
        return original_observe(views, reading)
    monkeypatch.setattr(passive.PassiveSelfViews, "observe", observe)
    monkeypatch.setattr(process_session.MineflayerProcessSession, "receive",
                        lambda *a, **kw: pytest.fail("extra native receive"))
    async def qualify(report, log, *, live_probe=None):
        try:
            for seq in SEQS:
                reading = probe(seq)
                if live_probe is not None:
                    await live_probe(reading)
                    assert counts[-1] == id(reading)
                decisions.append((seq, "fake original L0", "fake original action"))
            report.write_text(json.dumps(native_report()))
            return 0
        finally:
            decisions.append("cleanup")
    monkeypatch.setattr(s49, "qualify", qualify)
    for enabled in (False, True):
        root = tmp_path / str(enabled)
        root.mkdir()
        assert asyncio.run(self_demo._run_disposable(root / "report.json", root / "server.log",
                                                    passive_host_clock=enabled)) == 0
        snapshots.append(list(decisions))
        decisions.clear()
    assert snapshots[0] == snapshots[1]
    assert len(counts) == 3
