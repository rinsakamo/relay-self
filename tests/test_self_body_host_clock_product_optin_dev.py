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
    assert receipt.get("dev_host_clock") != "SOURCE_JOINED_CALLBACK_DEV_ONLY"
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
