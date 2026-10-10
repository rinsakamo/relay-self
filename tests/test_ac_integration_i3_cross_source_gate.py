"""I3: exact owner chain + independently sourced B11/B12 are NOT one World lineage."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import test_ac_integration_i2_governed_projection as i2fixture
from experiments import ac_integration_i3_cross_source_gate as i3


def _case(distance=0.2):
    inputs, data, failed, kwargs, grant = i2fixture._subject(distance)
    return inputs, data, failed, kwargs, grant, i3.b11_readonly_scope()


def _run(inputs, data, grant, b11, **changes):
    return i3.adjudicate_i3(
        inputs, data["commit"], data["feedback"], grant, b11, **changes,
    )


def test_frozen_three_independent_successful_ci_refs_and_null():
    m = i3.frozen_manifest()
    assert (m["base_i2"], m["b11_head"], m["b12_head"]) == (
        i3.FROZEN_I2, i3.FROZEN_B11, i3.FROZEN_B12
    )
    assert (m["i2_ci"], m["b11_ci"], m["b12_ci"]) == (
        38030431852, 38030146847, 38030776737
    )
    assert m["shared_world_witness_present"] is False
    assert m["measured_cost_advantage"] is False
    assert m["production_s11_owner_present"] is False


@pytest.mark.parametrize(
    ("distance", "band", "candidate"),
    [(0.2, "near", "MOVE_AWAY"), (1.8, "far", "WAIT")],
)
def test_actual_i2_chain_denies_cross_world_transfer(distance, band, candidate):
    inputs, data, failed, kwargs, grant, scope = _case(distance)
    before = (
        data["supervisor"].get("action-move-backward-1"),
        inputs["action3"],
        inputs["current_retained"],
        inputs["cognition"],
    )
    result = _run(inputs, data, grant, scope)
    assert result.classification == "I3_CROSS_SOURCE_NONTRANSFER_AND_CHEAP_NULL_CI_PASS"
    assert result.i2_source_session == "s23-recovery-session-3"
    assert result.b11_source_session == "b11-sim-world"
    assert result.i2_source_request_id == "s29-probe:one.1"
    assert result.i2_cue_band == band
    assert result.i2_before_candidate == "WAIT"
    assert result.i2_after_candidate == result.i2_cheap_candidate == candidate
    assert result.b11_training_actions_reported == 8
    assert result.b11_heldout_habit_reported == 12
    assert result.b11_heldout_cheap_reported == 12
    assert result.causal_join is False
    assert result.shared_world_witnesses is False
    assert result.shared_action_space is False
    assert result.common_cue_semantics is False
    assert result.production_habit_owner is False
    assert result.native_source_attested is False
    assert result.benefit_over_cheap_rule is False
    assert result.joint_runtime_go is False
    assert data["supervisor"].get(before[0].action_id) is before[0]
    assert data["supervisor"].get(before[1].action_id) is before[1]
    assert inputs["current_retained"] is before[2]
    assert inputs["cognition"] is before[3]
    assert data["supervisor"].open_actions == ()
    assert failed.is_terminal
    assert kwargs["adapter"].sent_ids == ["s29-probe:one.1"]


@pytest.mark.parametrize("name,value", [
    ("session", "s23-recovery-session-3"),
    ("session", "b11-sim-world-cloned"),
    ("revision", 1),
    ("revision", True),
    ("source_kind", "PHYSICALLY_ATTESTED"),
    ("cue_kind", "clearance_band"),
    ("actions", ("WAIT", "MOVE_AWAY")),
    ("actions", (False, True)),
    ("event_ids", ("action-move-backward-1",) * 8),
    ("event_ids", tuple(f"b11-sim-world:event:{n}" for n in range(1, 8))),
    ("heldout_total", 13),
    ("heldout_total", True),
    ("habit_correct", 13),
    ("cheap_tags_correct", 11),
    ("grant_kind", "S10_LEARNING_UPDATE_AUTHORITY"),
    ("grant_kind", "PRODUCTION_S11_HABIT_GRANT"),
    ("physical_origin_attested", True),
    ("production_s11_owner", True),
])
def test_untrusted_b11_metadata_cannot_relabel_same_world_or_production(name, value):
    args, data, _, _, grant, scope = _case()
    with pytest.raises(i3.I3Rejected):
        _run(args, data, grant, replace(scope, **{name: value}))


@pytest.mark.parametrize("request", [
    "production", "physical", "automatic_l2", "issue_action",
    "commit_habit", "L0", "join_by_CI", "join_by_matching_labels",
])
def test_green_cis_or_text_labels_cannot_promote_authority(request):
    args, data, _, _, grant, scope = _case()
    with pytest.raises(i3.I3Rejected):
        _run(args, data, grant, scope, request=request)


@pytest.mark.parametrize("change", ["missing_source", "fake_request", "fake_seq",
                                    "false_s24", "fabricated_memory_pointer",
                                    "wrong_owner", "missing_test_grant",
                                    "wrong_test_grant", "wrong_action_feedback"])
def test_actual_i2_chain_required_before_any_cross_lane_adjudication(change):
    args, data, _, _, grant, scope = _case()
    args = dict(args)
    fb = data["feedback"]
    if change == "missing_source":
        args.pop("owner_receipt")
    elif change == "fake_request":
        r = replace(args["owner_receipt"], request_id="stale")
        args["owner_receipt"] = args["supplied_receipt"] = r
    elif change == "fake_seq":
        r = replace(args["owner_receipt"], probe_seq=999)
        args["owner_receipt"] = args["supplied_receipt"] = r
    elif change == "false_s24":
        args["trace"] = replace(args["trace"], selected_candidate="WAIT")
    elif change == "fabricated_memory_pointer":
        args["memory_id"] = "invented-reference"
    elif change == "wrong_owner":
        args["current_retained"] = data["commit"].previous_state
    elif change == "missing_test_grant":
        grant = None
    elif change == "wrong_test_grant":
        grant = replace(grant, source_session="b11-sim-world")
    else:
        fb = replace(fb, action_id="b11-sim-world:event:1")
    with pytest.raises(ValueError):
        i3.adjudicate_i3(args, data["commit"], fb, grant, scope)


def test_b11_ids_are_not_source_attestation_even_with_valid_metadata():
    args, data, _, _, grant, scope = _case()
    assert scope.event_ids == tuple(
        f"b11-sim-world:event:{n}" for n in range(1, 9)
    )
    assert scope.source_kind == "LOCAL_SIMULATOR_OBJECT_IDENTITY"
    assert scope.actions == (0, 1)
    assert _run(args, data, grant, scope).causal_join is False
    # No same-process B11 QualifiedLedger/world issuer object is transported.
    # Even accurately transcribed external IDs are only source *references*.


def test_reconstructed_equal_i2_receipt_is_not_exact_owner_source():
    args, data, _, _, grant, scope = _case()
    args = dict(args)
    args["supplied_receipt"] = replace(args["owner_receipt"])
    with pytest.raises(ValueError):
        _run(args, data, grant, scope)


def test_manifest_tamper_rejected_before_any_audit(monkeypatch, tmp_path):
    source = i3.frozen_manifest()
    source["shared_world_witness_present"] = True
    bad = tmp_path / "tampered.json"
    bad.write_text(json.dumps(source), encoding="utf-8")
    monkeypatch.setattr(i3, "MANIFEST", bad)
    with pytest.raises(i3.I3Rejected):
        i3.frozen_manifest()


def test_manifest_duplicate_keys_rejected(monkeypatch, tmp_path):
    path = tmp_path / "dup.json"
    path.write_text('{"version":"x","version":"y"}', encoding="utf-8")
    monkeypatch.setattr(i3, "MANIFEST", path)
    with pytest.raises(i3.I3Rejected):
        i3.frozen_manifest()


def test_integration_does_not_import_b11_b12_or_add_action_scheduler():
    src = i3.__file__
    with open(src, encoding="utf-8") as file:
        text = file.read()
    for forbidden in (
        "from experiments.ac_b_b11_", "from experiments.ac_b_b12_",
        "commit_learning_update(", "commit_experiment_habit(", ".issue(",
        ".authorize(", "request_correlated_post_action_probe(",
        "MineflayerProcessSession(", "asyncio.create_task(",
        "production_go=True", "native_source_attested=True",
    ):
        assert forbidden not in text
