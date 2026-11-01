"""M #616 S49 live callback runner / standalone original verifier bootstrap.

A fake qualify coroutine models the *call site only*. No World, JVM,
Mineflayer, Action, or L2 is started in any test.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import test_metabolism_s49_owner_admission as m_fixture
import test_s49_completed_decision_bridge as s49_owner_test

from experiments.metabolism_s49_owner_admission import S49MAdmissionRejected
from tools.m616_s49_live_owner_dev import (
    M616OriginalS49CompletedTap,
    run_original_s49_with_m_readback,
)


def test_in_world_owner_callback_directly_passes_same_typed_batch_after_s16(tmp_path):
    batch = m_fixture._owner_batch()
    readback = m_fixture._saved_report(batch)
    expected = tuple((id(x.step), id(x.probe), id(x.action_receipt)) for x in batch.steps)
    assert type(s49_owner_test._synthetic_original_shape()) is tuple
    tap = M616OriginalS49CompletedTap(enabled=True)
    calls = []

    async def fake_original_qualify(report, server_log, *, completed_l0, completed_l0_dev):
        calls.append(("s49_original_qualify", completed_l0_dev))
        assert completed_l0 is tap
        assert not server_log.exists()
        completed_l0(batch)
        report.write_text(json.dumps(readback), encoding="utf-8")
        return 0

    code, result = asyncio.run(run_original_s49_with_m_readback(
        original_qualify=fake_original_qualify,
        report_path=tmp_path / "s49-report.json",
        server_log=tmp_path / "s49-server.log",
        tap=tap,
    ))
    assert code == 0
    assert calls == [("s49_original_qualify", True)]
    assert tap.observed_callbacks == 1
    assert result["status"] == "RECORDED"
    assert result["m_admission"]["kind"] == "ORIGINAL_PYTHON_BATCH"
    assert result["m_admission"]["source_attested"] is False
    assert result["m_admission"]["provider_calls"] is None
    assert result["m_admission"]["input_tokens"] is None
    assert result["new_native_reads"] == 0
    assert result["new_model_calls"] == 0
    assert result["new_action_issues"] == 0
    assert expected == tuple((id(x.step), id(x.probe), id(x.action_receipt))
                             for x in batch.steps)
    assert "snapshot" not in repr(result) and "model_text" not in repr(result)


def test_false_S49_completion_is_not_m_admitted_even_if_S49_reports_PASS(tmp_path):
    batch = m_fixture._owner_batch()
    forged = replace(batch, real_b0_decision_supplied=True)
    report = m_fixture._saved_report(batch)
    tap = M616OriginalS49CompletedTap(enabled=True)

    async def fake_owner(path, _log, *, completed_l0, completed_l0_dev):
        assert completed_l0_dev
        completed_l0(forged)
        path.write_text(json.dumps(report), encoding="utf-8")
        return 0

    code, result = asyncio.run(run_original_s49_with_m_readback(
        original_qualify=fake_owner,
        report_path=tmp_path / "S.json",
        server_log=tmp_path / "log",
        tap=tap,
    ))
    assert code == 0
    assert result["status"] == "DEFERRED"
    assert result["m_admission"]["status"] == "DEFERRED"
    assert not result["source_attested"]


def test_S49_world_failure_cannot_be_promoted_by_positive_M_callback(tmp_path):
    batch = m_fixture._owner_batch()
    report = m_fixture._saved_report(batch)
    report["status"] = "FAIL"
    tap = M616OriginalS49CompletedTap(enabled=True)

    async def fake_owner(path, _log, *, completed_l0, completed_l0_dev):
        completed_l0(batch)
        path.write_text(json.dumps(report), encoding="utf-8")
        return 1

    code, result = asyncio.run(run_original_s49_with_m_readback(
        original_qualify=fake_owner,
        report_path=tmp_path / "S.json",
        server_log=tmp_path / "log",
        tap=tap,
    ))
    assert code == 1 and result["status"] == "DEFERRED"
    assert result["m_admission"]["status"] == "RECORDED"


def test_callback_default_off_makes_no_access_to_batch():
    class NoAccess:
        def __getattribute__(self, name):
            raise AssertionError("default OFF touched native owner " + name)

    tap = M616OriginalS49CompletedTap()
    tap(NoAccess())
    assert tap.readout is None and tap.observed_callbacks == 0


def test_replay_source_cannot_gain_second_live_admission():
    batch = m_fixture._owner_batch()
    tap = M616OriginalS49CompletedTap(enabled=True)
    tap(batch)
    assert tap.readout["status"] == "RECORDED"
    tap(batch)
    assert tap.readout["status"] == "DEFERRED"


def test_negative_live_tap_config():
    with pytest.raises(ValueError):
        M616OriginalS49CompletedTap(enabled=1)
    with pytest.raises(ValueError):
        asyncio.run(run_original_s49_with_m_readback(
            original_qualify=lambda *_args, **_kwargs: None,
            report_path=Path("none"), server_log=Path("none"),
            tap=M616OriginalS49CompletedTap(),
        ))


def _run_cli(*args):
    root = Path(__file__).resolve().parents[1]
    owner_root = Path(s49_owner_test.__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join((str(root), str(root / "src")))
    cmd = [sys.executable, "-m", "tools.m616_s49_saved_report_check"]
    return subprocess.run(
        cmd + [*args], cwd=root, env=env, capture_output=True,
        text=True, check=False, timeout=20,
    ), owner_root


def test_standalone_CLI_imports_pinned_S49_without_manual_python_bootstrap(tmp_path):
    report = tmp_path / "original-shape.json"
    report.write_text(json.dumps(m_fixture._saved_report(m_fixture._owner_batch())),
                      encoding="utf-8")
    _, owner_root = _run_cli("--help")
    p, _ = _run_cli(
        "--report", str(report), "--admit-dev",
        "--s49-owner-dir", str(owner_root),
    )
    assert p.returncode == 0, p.stderr
    result = json.loads(p.stdout)
    assert result["status"] == "RECORDED"
    assert result["kind"] == "SAVED_REPORT_JSON"
    assert result["source_attested"] is False
    assert result["provider_calls"] is None
    assert report.exists()


def test_standalone_CLI_rejects_missing_or_unpinned_source(tmp_path):
    report = tmp_path / "record.json"
    report.write_text(json.dumps(m_fixture._saved_report(m_fixture._owner_batch())),
                      encoding="utf-8")
    a, _ = _run_cli("--report", str(report), "--admit-dev")
    assert a.returncode == 2
    assert json.loads(a.stdout)["reason"] == "original_s49_owner_dir_required"
    b, _ = _run_cli(
        "--report", str(report), "--admit-dev",
        "--s49-owner-dir", str(Path(__file__).resolve().parents[1]),
    )
    assert b.returncode == 2
    assert json.loads(b.stdout)["reason"] == "original_s49_checkout_unverified"


def test_live_cli_gate_blocks_before_any_world_even_with_readable_original_checkout(
    tmp_path,
):
    root = Path(__file__).resolve().parents[1]
    owner_root = Path(s49_owner_test.__file__).resolve().parents[1]
    env = dict(os.environ)
    for name in (
        "M616_S49_LIVE_DEV_ONLY", "S49_REAL_SERVER_CI", "S49_COMPLETED_L0_DEV_ONLY",
    ):
        env.pop(name, None)
    env["PYTHONPATH"] = os.pathsep.join((str(root), str(root / "src")))
    proc = subprocess.run(
        [
            sys.executable, "-m", "tools.m616_s49_live_owner_dev",
            "--s49-owner-dir", str(owner_root),
            "--report", str(tmp_path / "s.json"),
            "--server-log", str(tmp_path / "server.log"),
            "--m-report", str(tmp_path / "m.json"),
            "--live-world-dev",
        ],
        cwd=root, env=env, capture_output=True, text=True, check=False,
        timeout=20,
    )
    assert proc.returncode == 2, proc.stderr
    assert json.loads(proc.stdout)["reason"] == "missing_explicit_dev_grant_gates"
    assert list(tmp_path.iterdir()) == []
