"""I1 Stage28 CLI opt-in and fail-closed real World preflight (offline)."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import stage28c2b_real_recovered_rejoin_dev as runner
from test_stage28c2b_real_rejoin_launcher_dev import _args


def test_i1_inspect_mode_cannot_accept_world_grant(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runner, "run_restored_a_b_real_observation",
        lambda **_kwargs: pytest.fail("inspect mode started a World"),
    )
    monkeypatch.setattr(sys, "argv", [
        *_args(tmp_path), "--inspect-only", "--i1-original-cpu-sense",
        "--real-world-dev-grant",
    ])
    assert runner.main() == 2
    assert not (tmp_path / "new-world").exists()


def test_i1_explicit_execute_once_flag_is_passed_without_extra_grants(
    tmp_path, monkeypatch,
):
    seen = []

    def stub_assets(**_kwargs):
        return SimpleNamespace(
            paper_jar=tmp_path / "paper.jar", plugin_jar=tmp_path / "plugin.jar",
        )

    async def fake_run(**kwargs):
        seen.append(kwargs)
        return Path(tmp_path / "fixture-not-executed")

    monkeypatch.setattr(runner, "check_stage24g_pinned_assets", stub_assets)
    monkeypatch.setattr(runner, "_verify_local_runtime", lambda *_args: None)
    monkeypatch.setattr(runner, "require_i1_native_preflight",
                        lambda **_kw: SimpleNamespace(
                            mineflayer_version="4.39.0",
                            entities_sha256="f" * 64,
                            node_module_warning_code=None,
                            node_module_stderr_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                            node_module_stderr_raw="",
                        ))
    monkeypatch.setattr(runner, "inspect_real_recovered_sources",
                        lambda *_args: (SimpleNamespace(historical_native_sessions=()),
                                        SimpleNamespace(owners={"A": None, "B": None})))
    monkeypatch.setattr(runner, "run_restored_a_b_real_observation", fake_run)
    monkeypatch.setattr(sys, "argv", [
        *_args(tmp_path), "--execute-once", "--real-world-dev-grant",
        "--execution-dir", str(tmp_path / "new-world"),
        "--evidence-dir", str(tmp_path / "new-evidence"),
        "--i1-original-cpu-sense",
    ])
    assert runner.main() == 0
    assert seen and seen[0]["i1_original_cpu_sense"] is True


def test_i1_cannot_run_an_unreviewed_combined_gpu_and_cpu_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runner, "_verify_local_runtime",
        lambda *_args: pytest.fail("invalid combined ownership entered runtime"),
    )

    async def external_gpu_cognition(**_kwargs):
        pass

    with pytest.raises(runner.Stage28c2bRealRejoinHold):
        asyncio.run(runner.run_restored_a_b_real_observation(
            generation=tmp_path / "g", restored=tmp_path / "restored",
            stage28b_evidence=tmp_path / "evidence",
            execution_dir=tmp_path / "unused-world",
            evidence_dir=tmp_path / "unused-evidence",
            paper_jar=tmp_path / "paper.jar", plugin_jar=tmp_path / "plugin.jar",
            java="java", node="node", on_reconnected=external_gpu_cognition,
            i1_original_cpu_sense=True,
        ))


@pytest.mark.parametrize("mode", [False, True])
def test_i1_vs_legacy_capture_requires_its_own_pending_audit_class(mode):
    expected = (
        "I1_ORIGINAL_CPU_SENSE_CAPTURED_INDEPENDENT_AUDIT_PENDING"
        if mode else "REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING"
    )
    report = {
        "classification": expected,
        "i1_original_cpu_sense_enabled": mode,
        "i1_normal_continuous_native_observed": mode,
    }
    if mode:
        report["i1_cpu_epochs"] = {"epochs": []}
    runner.require_stage28_capture_classification(
        report, i1_original_cpu_sense=mode,
    )
    for bad in (
        {**report, "classification": "REAL_REJOIN_HOLD"},
        {**report, "i1_original_cpu_sense_enabled": not mode},
        {**report, "classification": (
            "REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING"
            if mode else "I1_ORIGINAL_CPU_SENSE_CAPTURED_INDEPENDENT_AUDIT_PENDING"
        )},
    ):
        with pytest.raises(runner.Stage28c2bRealRejoinHold):
            runner.require_stage28_capture_classification(
                bad, i1_original_cpu_sense=mode,
            )
    if mode:
        with pytest.raises(runner.Stage28c2bRealRejoinHold):
            runner.require_stage28_capture_classification(
                {**report, "i1_normal_continuous_native_observed": False},
                i1_original_cpu_sense=True,
            )
