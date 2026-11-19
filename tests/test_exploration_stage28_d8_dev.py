"""D8 original B-owned real launcher: strict new D source pins, no launch in CI."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import stage28_d8_independent_rejoin_audit_dev as auditor
from experiments import stage28_d8_real_rejoin_dev as runner
from relay_self.exploration_d8_owned_source_dev import (
    D8OwnedSourcePins,
    D8PinnedSourceHold,
    inspect_d8_original_source,
    load_d8_pins,
)
from test_exploration_stage28_d7_dev import _fixture


def _pins(source):
    return D8OwnedSourcePins(
        generation_id=source["expected_generation_id"],
        world_id=source["expected_world_id"],
        source_branch_id=source["expected_source_branch_id"],
        fork_branch_id=source["expected_fork_branch_id"],
        committed_sha256=source["expected_committed_sha256"],
        stage28b_evidence_sha256="b" * 64,
        stage28b_evidence_files=300,
    )


def _historical_fixture(monkeypatch, *, historical=("native-old-A", "native-old-B")):
    invoked = []
    def inspect(_evidence, _generation, *,
                expected_manifest_sha256, expected_files=285):
        invoked.append((expected_manifest_sha256, expected_files))
        return SimpleNamespace(
            historical_native_sessions=historical,
        )
    monkeypatch.setattr(
        "relay_self.stage28c2b_historical_native_sessions_dev."
        "inspect_original_stage28b_native_sessions", inspect,
    )
    return invoked


def test_d8_actual_d7_b_source_is_pinned_not_hardcoded_b_prior_world(
    tmp_path, monkeypatch,
):
    generation, fork, _, expected = _fixture(tmp_path)
    pins = _pins(expected)
    checks = _historical_fixture(monkeypatch)
    candidate, history = inspect_d8_original_source(
        generation, fork, tmp_path / "nonexistent-evidence-mocked",
        pins=pins,
    )
    assert candidate.world_id == "world-A"
    assert candidate.committed_sha256 == pins.committed_sha256
    assert candidate.generation_id == pins.generation_id
    assert candidate.real_native_rejoin_attested is False
    assert len(candidate.selves) == 2
    assert history.historical_native_sessions == ("native-old-A", "native-old-B")
    assert checks == [("b" * 64, 300)]  # new inventory not old B's fixed 285
    assert candidate.l2_dispatch_authorized is False


@pytest.mark.parametrize("bad", [
    {"stage28b_evidence_files": True},
    {"stage28b_evidence_files": 0},
    {"stage28b_evidence_files": 100001},
    {"stage28b_evidence_sha256": "0" * 63},
    {"generation_id": "../g-000000000000"},
    {"world_id": ""},
    {"committed_sha256": "f" * 63},
])
def test_d8_invalid_original_manifest_pins_hold(bad, tmp_path):
    generation, fork, _, expected = _fixture(tmp_path)
    values = asdict(_pins(expected))
    values.update(bad)
    with pytest.raises(D8PinnedSourceHold):
        D8OwnedSourcePins(**values)


def test_d8_missing_a_or_b_historical_native_prevents_world(tmp_path, monkeypatch):
    generation, fork, _, expected = _fixture(tmp_path)
    _historical_fixture(monkeypatch, historical=("native-old-A",))
    with pytest.raises(D8PinnedSourceHold, match="sources disagree"):
        inspect_d8_original_source(
            generation, fork, tmp_path / "old-evidence",
            pins=_pins(expected),
        )
    assert not (fork / "paper.jar").exists()


def test_d8_cannot_label_b_old_source_as_new_d_cut(tmp_path, monkeypatch):
    generation, fork, _, expected = _fixture(tmp_path)
    checks = _historical_fixture(monkeypatch)
    pins = _pins(expected)
    with pytest.raises(D8PinnedSourceHold):
        inspect_d8_original_source(
            generation, fork, tmp_path / "no-new-original",
            pins=D8OwnedSourcePins(
                **{**asdict(pins), "world_id": "old-b-hardcoded-uuid"}
            ),
        )
    assert checks == []  # D7 rejects source before B historical call.


def test_d8_strict_pins_json_missing_extra_or_symlink(tmp_path):
    path = tmp_path / "pins.json"
    path.write_text(json.dumps({"world_id": "world-A"}))
    with pytest.raises(D8PinnedSourceHold):
        load_d8_pins(path)
    path.write_text(json.dumps({
        "generation_id": "g-000000000000",
        "world_id": "world-A",
        "source_branch_id": "source",
        "fork_branch_id": "fork",
        "committed_sha256": "a" * 64,
        "stage28b_evidence_sha256": "b" * 64,
        "stage28b_evidence_files": 300,
        "unguarded_execution": True,
    }))
    with pytest.raises(D8PinnedSourceHold):
        load_d8_pins(path)
    alias = tmp_path / "linked-pins.json"
    alias.symlink_to(path)
    with pytest.raises(D8PinnedSourceHold):
        load_d8_pins(alias)


def _argv(tmp_path, pins, mode, *, grant=False):
    source = tmp_path / "pins.json"
    source.write_text(json.dumps(asdict(pins)))
    result = [
        "D8", "--generation", str(tmp_path / "generation"),
        "--restored", str(tmp_path / "restored"),
        "--stage28b-evidence", str(tmp_path / "historical"),
        "--source-pins-json", str(source),
        "--paper-jar", str(tmp_path / "paper.jar"),
        "--plugin-jar", str(tmp_path / "plugin.jar"),
        "--eula-accepted", mode,
    ]
    if grant:
        result += [
            "--real-world-dev-grant",
            "--execution-dir", str(tmp_path / "run"),
            "--evidence-dir", str(tmp_path / "proof"),
        ]
    return result


def test_d8_inspect_only_no_world_or_model_or_action(
    tmp_path, monkeypatch, capsys,
):
    generation, fork, _, expected = _fixture(tmp_path)
    pins = _pins(expected)
    monkeypatch.setattr(runner, "check_d8_pinned_assets",
                        lambda **kwargs: SimpleNamespace())
    monkeypatch.setattr(runner, "_verify_local_runtime", lambda *_: None)
    monkeypatch.setattr(runner, "inspect_real_recovered_sources",
                        lambda *a, **k: (
                            SimpleNamespace(historical_native_sessions=("oldA", "oldB")),
                            SimpleNamespace(owners={"A": object(), "B": object()}),
                        ))
    async def never_run(**kwargs):
        pytest.fail("inspect-only started owned Paper/Native/Gemma")
    monkeypatch.setattr(runner, "run_restored_a_b_real_observation", never_run)
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, pins, "--inspect-only"))
    assert runner.main() == 0
    captured = capsys.readouterr()
    assert "world_started=false model_post=false" in captured.out
    assert not (tmp_path / "run").exists()
    assert not (tmp_path / "proof").exists()


def test_d8_execute_without_explicit_one_shot_grant_holds_before_world(
    tmp_path, monkeypatch, capsys,
):
    _, _, _, expected = _fixture(tmp_path)
    pins = _pins(expected)
    monkeypatch.setattr(
        runner, "check_d8_pinned_assets",
        lambda **kwargs: pytest.fail("asset/World operation before grant"),
    )
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, pins, "--execute-once"))
    assert runner.main() == 2
    assert "HOLD" in capsys.readouterr().err
    assert not (tmp_path / "run").exists()


def test_d8_independent_audit_refuses_unbound_or_tampered_d_source(
    tmp_path, monkeypatch,
):
    generation, fork, _, expected = _fixture(tmp_path)
    _historical_fixture(monkeypatch)
    pins = _pins(expected)
    # This mock is the source readout, NOT a forged real native witness.
    report = tmp_path / "result.json"
    for mutation in ("no-d8", "wrong-source", "wrong-attempts"):
        candidate, history = inspect_d8_original_source(
            generation, fork, tmp_path / "historic-fixture", pins=pins,
        )
        body = {
            "schema": 1,
            "classification": "REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING",
            "independent_audit_pass": False,
            "original_generation": pins.generation_id,
            "original_world_uuid": pins.world_id,
            "original_committed_sha256": pins.committed_sha256,
            "fork_branch_id": pins.fork_branch_id,
            "real_world_trials": 1,
            "real_gemma_post": 0,
            "real_action_issued": 0,
            "real_peer_sent": 0,
            "physical_action_issue_authorized": False,
            "fresh_l1_run": False,
            "original_stage28b_reverified": True,
            "d8_source_pins": asdict(pins),
            "d8_cognitive_candidate": asdict(candidate),
        }
        if mutation == "no-d8":
            del body["d8_source_pins"]
        elif mutation == "wrong-source":
            body["d8_source_pins"]["committed_sha256"] = "0" * 64
        else:
            body["d8_cognitive_candidate"]["selves"][0]["attempt_refs"] = []
        report.write_text(json.dumps(body))
        with pytest.raises(auditor.Stage28c2bIndependentAuditHold):
            auditor.independently_audit_recovered_real_rejoin(
                report, generation=generation, restored=fork,
                stage28b_evidence=tmp_path / "historical-fixture",
                executable=tmp_path / "execution-never-started",
                pins=pins,
            )
    assert not (tmp_path / "execution-never-started").exists()
