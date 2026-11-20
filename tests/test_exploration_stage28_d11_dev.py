"""D11 CPU-only handoff tests. ALL sources and restores are synthetic.

No real Paper, GPU/Gemma, native Mineflayer or L2 execution occurs here.
Mocked independent D10 proof is used ONLY to test post-audit handoff
mechanics. It does not establish D10 or real World attestation.
"""
from __future__ import annotations

import hashlib
import json
import sys
from types import SimpleNamespace

import pytest

from experiments import stage28_d11_prepare_inert_handoff_dev as d11
from relay_self.exploration_d8_owned_source_dev import (
    D8PinnedSourceHold,
    load_d8_pins,
)
from test_exploration_stage28_d7_dev import _fixture


def _options(expected: dict) -> dict:
    return {
        "manifest_sha256": "a" * 64,
        "manifest_files": 300,
        "world_id": expected["expected_world_id"],
        "source_branch": expected["expected_source_branch_id"],
        "committed_sha256": expected["expected_committed_sha256"],
    }


def _synthetic_after_audit(monkeypatch):
    calls = []
    def verified_source(*args, **kwargs):
        calls.append(("audit", args))
        return SimpleNamespace(original_model_choice_id="1"), "b" * 64

    def verified_d8(*args, **kwargs):
        calls.append(("d8", args))
        return SimpleNamespace(
            owner_roster=("A", "B"),
            real_world_attested=False,
            physical_action_issue_authorized=False,
            l2_dispatch_authorized=False,
        ), object()

    monkeypatch.setattr(d11, "inspect_d11_source", verified_source)
    monkeypatch.setattr(d11, "inspect_d8_original_source", verified_d8)
    return calls


def test_d11_unsealed_synthetic_d7_cannot_pass_real_d10_source(tmp_path):
    scenario = tmp_path / "scenario"
    scenario.mkdir()
    generation, _, _, expected = _fixture(scenario)
    evidence_dir = generation.parent.parent
    with pytest.raises(d11.D11HandoffHold):
        d11.inspect_d11_source(
            evidence_dir, generation, **_options(expected),
        )
    assert not (evidence_dir.parent / "d10-independent-audit.json").exists()


def test_d11_fork_is_inert_and_pins_exact_audit_once(tmp_path, monkeypatch):
    scenario = tmp_path / "scenario"
    scenario.mkdir()
    generation, _, _, expected = _fixture(scenario)
    calls = _synthetic_after_audit(monkeypatch)
    recovered = tmp_path / "recovered-d11"
    pins_file = tmp_path / "new-d11-pins.json"
    options = _options(expected)
    result = d11.prepare_d11_inert_handoff(
        generation.parent.parent, generation, recovered, pins_file,
        restore_id="d11-inert-dev", **options,
    )
    pins = load_d8_pins(pins_file)
    assert result["classification"] == "D11_INERT_HANDOFF_PREPARED_OFFLINE_DEV"
    assert result["d10_independent_audit_sha256"] == "b" * 64
    assert pins.d10_source_audit_sha256 == "b" * 64
    assert pins.world_id == expected["expected_world_id"]
    assert pins.fork_branch_id == result["fork_branch_id"]
    assert pins.stage28b_evidence_files == 300
    assert pins.generation_id == generation.name
    assert result["real_world_execution_attested"] is False
    assert result["real_model_execution_attested"] is False
    assert result["physical_action_issue_authorized"] is False
    assert result["old_l2_replay_authorized"] is False
    assert [x[0] for x in calls] == ["audit", "d8"]
    assert result["d8_source_pins_sha256"] == hashlib.sha256(
        pins_file.read_bytes(),
    ).hexdigest()
    assert (recovered / "world").is_dir()
    assert (recovered / "world_nether").is_dir()
    assert (recovered / "world_the_end").is_dir()
    assert not (recovered / "paper.jar").exists()
    raw = pins_file.read_bytes()
    with pytest.raises(d11.D11HandoffHold, match="fresh"):
        d11.prepare_d11_inert_handoff(
            generation.parent.parent, generation, recovered, pins_file,
            restore_id="d11-second-try", **options,
        )
    assert pins_file.read_bytes() == raw
    assert [x[0] for x in calls] == ["audit", "d8"]


@pytest.mark.parametrize("invalid", [
    "pins_inside_evidence",
    "restored_inside_evidence",
    "pins_inside_restored",
    "existing_pins",
    "existing_restored",
    "missing_restore_id",
])
def test_d11_unsafe_output_paths_hold_before_any_restore(
    tmp_path, monkeypatch, invalid,
):
    scenario = tmp_path / "scenario"
    scenario.mkdir()
    generation, _, _, expected = _fixture(scenario)
    calls = _synthetic_after_audit(monkeypatch)
    evidence = generation.parent.parent
    restored = tmp_path / "fresh-d11"
    pins_file = tmp_path / "fresh-d11-pins.json"
    restore_id = "d11-dev"
    if invalid == "pins_inside_evidence":
        pins_file = evidence / "unsafe.json"
    elif invalid == "restored_inside_evidence":
        restored = evidence / "unsafe-recovered"
    elif invalid == "pins_inside_restored":
        restored.mkdir()
        pins_file = restored / "nested.json"
    elif invalid == "existing_pins":
        pins_file.write_text("do not overwrite")
    elif invalid == "existing_restored":
        restored.mkdir()
    elif invalid == "missing_restore_id":
        restore_id = ""
    with pytest.raises(d11.D11HandoffHold):
        d11.prepare_d11_inert_handoff(
            evidence, generation, restored, pins_file,
            restore_id=restore_id, **_options(expected),
        )
    assert calls == []
    assert not (tmp_path / "fresh-d11-pins.json").exists() or (
        invalid == "existing_pins"
    )


def test_d11_no_publish_when_postrestore_d8_rejects(tmp_path, monkeypatch):
    scenario = tmp_path / "scenario"
    scenario.mkdir()
    generation, _, _, expected = _fixture(scenario)
    _synthetic_after_audit(monkeypatch)
    def refuse(*args, **kwargs):
        raise D8PinnedSourceHold("deliberately tampered original native history")

    monkeypatch.setattr(d11, "inspect_d8_original_source", refuse)
    recovered = tmp_path / "bad-recovery"
    pins_file = tmp_path / "bad-pins.json"
    with pytest.raises(D8PinnedSourceHold):
        d11.prepare_d11_inert_handoff(
            generation.parent.parent, generation, recovered, pins_file,
            restore_id="d11-test-refusal", **_options(expected),
        )
    assert recovered.exists()  # preserved as a failed, nonreusable attempt
    assert not pins_file.exists()
    assert not (recovered / "paper.jar").exists()


def test_d11_cli_inspect_only_never_makes_fork(tmp_path, monkeypatch, capsys):
    scenario = tmp_path / "scenario"
    scenario.mkdir()
    gen, _, _, expected = _fixture(scenario)
    calls = _synthetic_after_audit(monkeypatch)
    args = [
        "d11", "--inspect-only", "--evidence-dir",
        str(gen.parent.parent), "--generation", str(gen),
        "--manifest-sha256", "a" * 64, "--manifest-files", "300",
        "--world-id", expected["expected_world_id"],
        "--source-branch", expected["expected_source_branch_id"],
        "--committed-sha256", expected["expected_committed_sha256"],
    ]
    monkeypatch.setattr(sys, "argv", args)
    assert d11.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["classification"] == "D11_PRE_FORK_SOURCE_BYTES_VERIFIED_DEV"
    assert payload["physical_action_issue_authorized"] is False
    assert len(calls) == 1 and calls[0][0] == "audit"
    assert not (tmp_path / "new-d11-pins.json").exists()
    monkeypatch.setattr(sys, "argv", [
        *args, "--restored", str(tmp_path / "not-allowed"),
    ])
    assert d11.main() == 2
    assert not (tmp_path / "not-allowed").exists()
