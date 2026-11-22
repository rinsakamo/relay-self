"""Strict real-ingress preflight using synthetic original A/B source fixtures.

No actual llama-server, GPU, Paper or Self autonomy is exercised.
"""
from dataclasses import replace
from pathlib import Path

import pytest

import relay_self.bd1b_real_issuer_preflight_dev as preflight
from experiments.stage24g_model_gate_dev import Stage24gModelGateReceipt
from relay_self.bd1b_real_issuer_preflight_dev import (
    BD1bRealIssuerHold,
    inspect_bd1b_real_issuer,
    require_live_bd1b_source,
)
from relay_self.innate_schema import SchemaMode
from test_bd1b_coverage_adoption_turn_dev import arguments
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _gate():
    return Stage24gModelGateReceipt(
        32145, "model", "/models/pin.gguf", "a" * 64, "RTX 3060",
        "b" * 64, "c" * 64, 0, 1, "d" * 64,
    )


def _qualified(case, *, sid="A"):
    return require_live_bd1b_source(**arguments(case, sid))


def test_original_owner_schema_and_frozen_question_precede_model(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    before = _files(case[1])
    turn = _qualified(case)
    assert turn.inquiry.question_ref.startswith("coverage-inquiry:v1:")
    assert turn.owner is case[1].owners["A"]
    assert not turn.request.think_allowed
    assert case[1].inference_lane is None
    assert _files(case[1]) == before


def test_preflight_model_receipt_rechecks_original_turn(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    monkeypatch.setattr(preflight, "verify_stage24g_model_gate", lambda **kw: _gate())
    before = _files(case[1])
    args = arguments(case)
    args.update(gguf_path=Path("/models/pin.gguf"), llama_pid=32145,
                model_alias="model", llama_endpoint="http://127.0.0.1:8080")
    outcome = inspect_bd1b_real_issuer(**args)
    assert outcome.turn.self_id == "A"
    assert outcome.gate == _gate()
    assert not outcome.action_issue_authorized
    assert not outcome.model_post_attempted
    assert _files(case[1]) == before


@pytest.mark.parametrize("variant", [
    "no-registration", "foreign-snapshot", "schema-disabled",
    "schema-need-missing", "registry-drift", "other-registration",
    "unqualified-physical", "action-open", "foreign-self", "stale-probe",
])
def test_misqualified_original_source_never_checks_model(tmp_path, monkeypatch, variant):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, _, _, _, _ = case
    if variant == "no-registration":
        bridge.cognitive_work._present_schemas.pop("A")
    elif variant == "foreign-snapshot":
        snapshot, registry = bridge.cognitive_work._present_schemas["A"]
        bridge.cognitive_work._present_schemas["A"] = (replace(snapshot, self_id="B"), registry)
    elif variant == "schema-disabled":
        snapshot, registry = bridge.cognitive_work._present_schemas["A"]
        activation = replace(snapshot.modules[0], mode=SchemaMode.OFF)
        bridge.cognitive_work._present_schemas["A"] = (
            replace(snapshot, modules=(activation,)), registry,
        )
    elif variant == "schema-need-missing":
        snapshot, registry = bridge.cognitive_work._present_schemas["A"]
        act = snapshot.modules[0]
        spec = replace(act.spec, signal_kinds=("QUESTION_CANDIDATE",))
        bridge.cognitive_work._present_schemas["A"] = (
            replace(snapshot, modules=(replace(act, spec=spec),)), registry,
        )
    elif variant == "registry-drift":
        bridge.owners["A"].pattern_registry = replace(
            bridge.owners["A"].pattern_registry, revision=2,
        )
    elif variant == "other-registration":
        bridge.cognitive_work._present_schemas.pop("B")
    elif variant == "unqualified-physical":
        bridge.physical._observation_only = False
    elif variant == "action-open":
        bridge.physical._active["wrong"] = type("Active", (), {"action_id": "wrong"})()
    elif variant == "foreign-self":
        pass
    else:
        bridge.owners["A"].current_worldbody_observation = replace(
            bridge.owners["A"].current_worldbody_observation,
        )
    monkeypatch.setattr(preflight, "verify_stage24g_model_gate",
                        lambda **kw: pytest.fail("model inspected before original source"))
    before = _files(bridge)
    args = arguments(case)
    args["self_id"] = "C" if variant == "foreign-self" else "A"
    args.update(gguf_path=Path("/models/pin.gguf"), llama_pid=32145,
                model_alias="model", llama_endpoint="http://127.0.0.1:8080")
    with pytest.raises((BD1bRealIssuerHold, ValueError, RuntimeError)):
        inspect_bd1b_real_issuer(**args)
    assert _files(bridge) == before


@pytest.mark.parametrize("variant", ["pid", "alias", "slot", "foreign-model", "changed-probe"])
def test_model_or_concurrent_source_mismatch_holds(tmp_path, monkeypatch, variant):
    case = _configured(tmp_path, monkeypatch, need=True)
    before = _files(case[1])

    def verifier(**kw):
        if variant == "changed-probe":
            case[1].owners["A"].current_worldbody_observation = replace(
                case[1].owners["A"].current_worldbody_observation,
            )
        if variant == "pid":
            return replace(_gate(), llama_pid=5)
        if variant == "alias":
            return replace(_gate(), model_alias="another")
        if variant == "slot":
            return replace(_gate(), slot_count=2)
        if variant == "foreign-model":
            return object()
        return _gate()

    monkeypatch.setattr(preflight, "verify_stage24g_model_gate", verifier)
    args = arguments(case)
    args.update(gguf_path=Path("/models/pin.gguf"), llama_pid=32145,
                model_alias="model", llama_endpoint="http://127.0.0.1:8080")
    with pytest.raises((BD1bRealIssuerHold, ValueError, RuntimeError)):
        inspect_bd1b_real_issuer(**args)
    assert _files(case[1]) == before


def test_original_restored_schema_cannot_be_inferred_from_registry(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    resident = case[1].cognitive_work
    resident._present_schemas.clear()
    assert all(o.pattern_registry.revision == 1 for o in resident.owners.values())
    with pytest.raises(BD1bRealIssuerHold, match="RESTORED_SCHEMA_ACTIVATION_NOT_ATTESTED"):
        _qualified(case)
