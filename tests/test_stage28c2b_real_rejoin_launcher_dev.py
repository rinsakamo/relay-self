"""Stage28c2b: CLI grants and independent audit stay fail-closed offline."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import stage28c2b_independent_rejoin_audit_dev as audit
from experiments import stage28c2b_real_recovered_rejoin_dev as runner


@pytest.mark.parametrize("failure", ["termination", "still-running", "raw-close"])
def test_native_cleanup_never_hides_uncertainty(failure):
    class Native:
        process_returncode = None
        _raw_source_audit_finished = False

        async def terminate(self):
            if failure == "termination":
                raise RuntimeError("termination failed")
            if failure != "still-running":
                self.process_returncode = 0

        def finish_raw_source_audit(self):
            if failure == "raw-close":
                raise OSError("close failed")
            self._raw_source_audit_finished = True

    report = {}
    asyncio.run(runner._cleanup_native(Native(), report))
    expected = "raw_source_audit_uncertain" if failure == "raw-close" else "cleanup_uncertain"
    assert report[expected] is True


def _args(tmp_path: Path):
    return [
        "stage28c2b", "--generation", str(tmp_path / "g"),
        "--restored", str(tmp_path / "restored"),
        "--stage28b-evidence", str(tmp_path / "source"),
        "--paper-jar", str(tmp_path / "paper.jar"),
        "--plugin-jar", str(tmp_path / "plugin.jar"),
        "--eula-accepted",
    ]


def test_stage28c2b_inspect_only_never_starts_paper_or_creates_world(
    tmp_path, monkeypatch, capsys,
):
    def never_execute(**_kwargs):
        pytest.fail("inspect-only started a real restored World")

    monkeypatch.setattr(runner, "check_stage24g_pinned_assets",
                        lambda **_kwargs: SimpleNamespace())
    monkeypatch.setattr(runner, "_verify_local_runtime", lambda *_args: None)
    monkeypatch.setattr(runner, "inspect_real_recovered_sources",
                        lambda *_args: (
                            SimpleNamespace(historical_native_sessions=("x", "y", "z")),
                            SimpleNamespace(owners={"A": None, "B": None}),
                        ))
    monkeypatch.setattr(runner, "run_restored_a_b_real_observation", never_execute)
    monkeypatch.setattr(sys, "argv", [*_args(tmp_path), "--inspect-only"])
    assert runner.main() == 0
    assert "world_started=false model_post=false" in capsys.readouterr().out


def test_stage28c2b_requires_explicit_once_grant_before_world(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(sys, "argv", [
        *_args(tmp_path), "--execute-once",
        "--execution-dir", str(tmp_path / "new-world"),
        "--evidence-dir", str(tmp_path / "new-evidence"),
    ])
    assert runner.main() == 2
    assert not (tmp_path / "new-world").exists()


def test_stage28c2b_inspect_rejects_real_world_grant(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        *_args(tmp_path), "--inspect-only", "--real-world-dev-grant",
    ])
    assert runner.main() == 2


@pytest.mark.parametrize("tamper", [
    "missing-classification", "positive-action", "positive-gpu",
    "missing-independent-audit-pending",
])
def test_stage28c2b_independent_audit_does_not_promote_unverified_report(
    tmp_path, tamper,
):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    report = {
        "schema": 1,
        "classification": "REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING",
        "independent_audit_pass": False,
        "original_world_uuid": runner._SOURCE_WORLD,
        "original_committed_sha256": runner._SOURCE_COMMITTED_SHA,
        "fork_branch_id": runner._FORK_BRANCH,
        "real_world_trials": 1,
        "real_gemma_post": 0,
        "real_action_issued": 0,
        "real_peer_sent": 0,
        "physical_action_issue_authorized": False,
        "fresh_l1_run": False,
        "original_stage28b_reverified": True,
    }
    if tamper == "missing-classification":
        report["classification"] = "HOLD"
    elif tamper == "positive-action":
        report["real_action_issued"] = 1
    elif tamper == "positive-gpu":
        report["real_gemma_post"] = 1
    else:
        report["independent_audit_pass"] = True
    file = evidence / "result.json"
    file.write_text(json.dumps(report))
    with pytest.raises(audit.Stage28c2bIndependentAuditHold):
        audit.independently_audit_recovered_real_rejoin(
            file, generation=tmp_path / "gen", restored=tmp_path / "restored",
            stage28b_evidence=tmp_path / "source",
            executable=tmp_path / "executable",
        )
