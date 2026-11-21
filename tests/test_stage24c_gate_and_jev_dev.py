"""Stage24c source gate + Jev differential: offline synthetic, no World."""
from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from adapters.llama_cpp.relay_engine import (
    parse_llama_cpp_jev_decision,
    render_llama_cpp_jev_request,
)
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEntityFact,
    MineflayerPosition,
)
from experiments import stage24c_systemone_pair_dev as calibration
from relay_self.intent import IntentCommitment
from relay_self.relay_engine import DecisionStatus
from relay_self.resident_exploration_gate_audit_dev import audit_exploration_gate


def _fixture(oxygen=300):
    name, turn, audit = next(
        (n, t, a) for n, t, a in calibration.synthetic_control_pair()
        if (oxygen is None) == (n == "oxygen_unknown")
    )
    return name, turn, audit


def _status(audit):
    return {x.predicate: x.status for x in audit.checks}


def _replace_snapshot(probe, **changes):
    return replace(probe, snapshot=replace(probe.snapshot, **changes))


def test_unknown_oxygen_is_legacy_condition_but_not_exploration_permission():
    controls = calibration.synthetic_control_pair()
    assert len(controls) == 2
    unknown, known = controls
    assert unknown[0] == "oxygen_unknown"
    assert known[0] == "oxygen_known_positive"
    assert unknown[1].initial_probe.snapshot.oxygen_level is None
    assert known[1].initial_probe.snapshot.oxygen_level == 300
    # Preserve the historical Stage24c audit as read-only evidence.
    assert not unknown[2].eligible
    assert _status(unknown[2])["oxygen_known_positive"] == "UNKNOWN"
    assert unknown[2].blocking_codes == ("oxygen_known_positive:UNKNOWN",)
    assert known[2].eligible
    # Stage24e intentionally changes candidate-generation semantics; the
    # archived Stage24c A/B model response is not rerun or rewritten.
    for _, turn, audit in controls:
        assert turn.exploration_need_active
        assert len(turn.prebound_moves) == 4
        assert {g.goal_id for g in turn.round.frame.goals} == {"EXPLORE_WORLD"}
        assert [c.choice_id for c in turn.round.request.choices] == [
            "1", "2", "3", "4", "5", "6",
        ]
        assert not audit.physical_authorized


@pytest.mark.parametrize(
    ("field", "value", "code", "expected"),
    [
        ("health", 15, "health_at_least_16", "BLOCKED"),
        ("food", 17, "food_at_least_18", "BLOCKED"),
        ("oxygen_level", 0, "oxygen_known_positive", "BLOCKED"),
        ("time", None, "world_time_observed", "UNKNOWN"),
    ],
)
def test_separate_gate_observations_preserve_blocked_vs_unknown(
    field, value, code, expected,
):
    _, turn, _ = _fixture()
    probe = _replace_snapshot(turn.initial_probe, **{field: value})
    gate = audit_exploration_gate(probe, intent_owner=IntentCommitment())
    assert not gate.eligible
    assert _status(gate)[code] == expected
    assert gate.blocking_codes == (code + ":" + expected,)


def test_truncated_coverage_distinguishes_unknown_from_present_entity():
    _, turn, _ = _fixture()
    probe = turn.initial_probe
    coverage = replace(probe.snapshot.nearby_entities_coverage, truncated=True,
                       candidate_count=17)
    observed = tuple(
        MineflayerEntityFact(
            i, "unknown", "mob", 2.0, MineflayerPosition(1, 64, 0),
        )
        for i in range(16)
    )
    truncated = _replace_snapshot(
        probe, nearby_entities=observed, nearby_entities_coverage=coverage,
    )
    audit = audit_exploration_gate(truncated, intent_owner=IntentCommitment())
    assert not audit.eligible
    assert _status(audit)["entity_coverage_complete"] == "UNKNOWN"
    # A truncated registry MUST contain 16 observed entries; absence
    # is already disproved, not merely unknown.
    assert _status(audit)["nearby_entities_absent"] == "BLOCKED"

    entity = MineflayerEntityFact(
        4, "zombie", "mob", 2.0, MineflayerPosition(1, 64, 0),
    )
    full = replace(
        coverage, truncated=False, candidate_count=1,
    )
    occupied = _replace_snapshot(
        probe, nearby_entities=(entity,), nearby_entities_coverage=full,
    )
    audit = audit_exploration_gate(occupied, intent_owner=IntentCommitment())
    assert not audit.eligible
    assert _status(audit)["nearby_entities_absent"] == "BLOCKED"


def test_oxygen_known_not_a_permission_or_replacement_for_capability():
    _, turn, audit = _fixture()
    assert audit.eligible
    assert audit.physical_authorized is False
    assert turn.round.request.think_allowed is False
    # This is a synthetic candidate set, not a physical action.
    assert all(c.option.target_ref.startswith("relative:")
               for c in turn.prebound_moves)
    assert turn.initial_probe.snapshot.nearby_entities_coverage.source_scope == (
        MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE
    )


def test_original_jev_response_parser_distinguishes_unresolved_and_explicit_choice():
    _, turn, _ = _fixture(None)
    raw_request = render_llama_cpp_jev_request(
        turn.round.request, model="synthetic-gemma",
    )
    criteria = raw_request["questions"]["decision"]["criteria"]
    assert set(criteria) == {
        "1", "2", "3", "4", "5", "6", "__relay_self_unresolved__",
    }
    for choice, status, expected in (
        ("__relay_self_unresolved__", DecisionStatus.UNRESOLVED, None),
        ("6", DecisionStatus.RESOLVED, "6"),
    ):
        parsed = parse_llama_cpp_jev_decision(
            {
                "answers": {"decision": {"type": "choice", "choice": choice}},
                "usage": {"input_tokens": 314, "output_tokens": 0},
            },
            request=turn.round.request,
        )
        assert parsed.status == status
        assert parsed.choice_id == expected
        if choice.startswith("__relay"):
            assert parsed.reason == "jev_model_unresolved"


def test_synthetic_inspect_never_contacts_gpu_or_world(tmp_path, monkeypatch):
    def no_gpu(*args, **kwargs):
        raise AssertionError("inspect-only MUST NOT call original model")

    monkeypatch.setattr(calibration.urllib.request, "urlopen", no_gpu)
    directory = tmp_path / "controls"
    result = calibration.run_stage24c_calibration(
        evidence_dir=directory, model="synthetic-model",
        endpoint="", systemone_endpoint="", backend_ref="",
        grant_real_llm=False, execute_model=False,
    )
    assert len(result) == 2
    assert (directory / "stage24c-manifest.json").is_file()
    manifest = json.loads((directory / "stage24c-manifest.json").read_text())
    assert manifest["model_requests_sent"] == 0
    assert manifest["physical_actions_issued"] == 0
    assert manifest["worlds_created"] == 0
    assert not list(directory.glob("*raw-http*"))
    assert result[0]["actual_model_executed"] is False
    with pytest.raises(calibration.Stage24cCalibrationRefusal, match="new evidence"):
        calibration.run_stage24c_calibration(
            evidence_dir=directory, model="synthetic-model",
            endpoint="", systemone_endpoint="", backend_ref="",
            grant_real_llm=False, execute_model=False,
        )


def test_calibration_requires_explicit_model_grant_before_creating_evidence(tmp_path):
    directory = tmp_path / "denied"
    with pytest.raises(calibration.Stage24cCalibrationRefusal, match="permission"):
        calibration.run_stage24c_calibration(
            evidence_dir=directory, model="gemma",
            endpoint="http://127.0.0.1:8080/v1/chat/completions",
            systemone_endpoint="http://127.0.0.1:8080/v1/systemone",
            backend_ref="operator-owned",
            grant_real_llm=False, execute_model=True,
        )
    assert not directory.exists()


def test_synthetic_real_model_pair_preserves_raw_body_before_parsing(
    tmp_path, monkeypatch,
):
    class FakeWitness:
        def __init__(self, **kwargs):
            self.readbacks = 0

        def require_idle(self):
            self.readbacks += 1
            return SimpleNamespace(is_processing=False, n_slots=1)

    class FakeResponse:
        status = 200

        def __init__(self, raw):
            self.raw = raw

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, max_bytes):
            assert max_bytes == 1024 * 1024 + 1
            return self.raw

    calls = []

    def fake_post(request, timeout):
        assert request.get_method() == "POST"
        assert timeout == 60.0
        body = json.loads(request.data)
        choices = body["questions"]["decision"]["criteria"]
        calls.append(tuple(choices))
        choice = (
            "__relay_self_unresolved__"
            if "3" not in choices else "4"
        )
        raw = json.dumps({
            "answers": {"decision": {"type": "choice", "choice": choice}},
            "usage": {"input_tokens": 314, "output_tokens": 0},
        }).encode()
        return FakeResponse(raw)

    monkeypatch.setattr(calibration, "LlamaCppSingleSlotWitness", FakeWitness)
    monkeypatch.setattr(calibration.urllib.request, "urlopen", fake_post)
    out = tmp_path / "real-provider-synthetic-state"
    records = calibration.run_stage24c_calibration(
        evidence_dir=out, model="synthetic-test-only",
        endpoint="http://127.0.0.1:8080/v1/chat/completions",
        systemone_endpoint="http://127.0.0.1:8080/v1/systemone",
        backend_ref="synthetic-backend",
        grant_real_llm=True, execute_model=True,
    )
    assert len(calls) == 2
    assert [r["provider_status"] for r in records] == [
        "resolved", "resolved",
    ]
    assert [r["provider_choice_id"] for r in records] == ["4", "4"]
    assert all(r["exploration_policy"] == "INNATE_NEED_NOT_BODY_GATE"
               for r in records)
    assert all(r["historic_stage24c_outcome_reproduced"] is False
               for r in records)
    assert records[1]["source_kind"] == "SYNTHETIC_NOT_WORLD_EVIDENCE"
    assert all(not r["physical_action_authorized"] for r in records)
    assert all((out / f"{r['case']}-jev-raw-http-body.json").is_file()
               for r in records)
    assert json.loads((out / "stage24c-manifest.json").read_text())[
        "physical_actions_issued"
    ] == 0
