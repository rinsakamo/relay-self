"""Untrusted L22 real external Goal readback is diagnostic only."""
from __future__ import annotations

import json

import pytest

from adapters.mineflayer.slm_external_goal_candidate_dev import (
    SCHEMA,
    ExternalGoalCandidateRejected,
    PreviousExternalGoalDiagnostic,
    read_external_goal_diagnostic,
)
from adapters.mineflayer.slm_passive_dev import S49SLMDevOwner
from test_s49_slm_passive_dev import decide, setup


def real_shaped_review():
    return PreviousExternalGoalDiagnostic(
        source_session_id="0b7d893c-9985-4e0e-a9a1-b99c107b7367",
        original_action_id="s49-native-move-24",
        source_l22_ref="451270faa1281889494f933a5eda33a71e88834f:run1",
        native_received_sha256="22c8100795e7e37acd91dea50a4db4943a4b448431d8b2b994d4d7aac72c6ea7",
        native_sent_sha256="97a7d70ac524f563e2e48de7a1921429b0d91fae1417bd34f8ee90968130e06f",
        original_s16_sha256="4f2d0a8f3c78d1046e094ee282fe477cad9395f034a42dcf63fbba4b66018f7b",
        separate_client_original_sha256="51f3280d19224ef26709cba8554101d551d0b1a2e7deee4d2a196cf3af00445a",
        separate_client_observation="NOT_REACHED",
        native_goal_status="UNDETERMINED",
        geometric_goal_candidate="NOT_REACHED",
        settling_state="SETTLING_OBSERVED",
        move_events_after_s16=6,
    )


def store(tmp_path, row):
    root = tmp_path / "prior"
    root.mkdir()
    (root / "external-goal-dev-review.json").write_text(
        json.dumps(row, sort_keys=True),
    )
    return root


def test_review_source_is_reported_but_zero_learning_and_original_s49_kept():
    external = real_shaped_review()
    owner, host, supervisor, native, event = setup()
    linked = S49SLMDevOwner(retention_enabled=True, previous_external_goal=external)
    # Bind to the same original host (not another motor issuer).
    linked.bind(host, supervisor)
    original = linked.cognition
    step = decide(linked, host, native, event)
    result = linked.finish([])
    assert step.choice.selection.value == "MOVE_AWAY"
    assert host.action_requests == 1
    assert linked.cognition is original
    assert result["one_l8_memory_owner"] is True
    assert result["observer_errors"] == 0
    assert result["l8_training_admissions"] == 0
    assert result["rows"][0]["l1_status"] == "no_admissible_l1_proposal"
    assert result["rows"][0]["l1_candidate"] is None
    assert result["rows"][0]["learning_updates"] == 0
    assert result["previous_external_goal"]["separate_client_observation"] == "NOT_REACHED"
    assert result["previous_external_goal"]["accepted_goal_status"] == "UNDETERMINED"
    assert result["previous_external_goal"]["qualified_l8_training_pairs"] == 0
    assert result["previous_external_goal"]["external_owner_authenticated"] is False
    assert result["previous_external_goal"]["action_authority"] is False
    assert result["previous_external_goal"]["learning_authority"] is False


def test_bounded_readback_is_not_third_party_authentication(tmp_path):
    expected = real_shaped_review()
    root = store(tmp_path, expected.audit_row())
    got = read_external_goal_diagnostic(root)
    assert got == expected
    assert not got.learning_authority
    assert got.qualified_l8_training_pairs == 0


@pytest.mark.parametrize("mutation", (
    {"accepted_goal_status": "NOT_REACHED"},
    {"external_owner_authenticated": True},
    {"physical_stability_attested": True},
    {"independently_attested_nonintervention": True},
    {"action_authority": True},
    {"learning_authority": True},
    {"qualified_l8_training_pairs": 1},
    {"source_l22_ref": "not-the-pinned-original"},
    {"native_goal_status": "NOT_REACHED"},
    {"settling_state": "STABLE_WORLD_TICKS"},
    {"original_s16_sha256": "0" * 64},
    {"move_events_after_s16": -1},
    {"reason": "LEARNING_GRANTED"},
))
def test_authority_or_origin_mutations_rejected(tmp_path, mutation):
    row = real_shaped_review().audit_row()
    row.update(mutation)
    root = store(tmp_path, row)
    if mutation == {"original_s16_sha256": "0" * 64}:
        # A forged but shape-valid digest is not authenticated by the summary
        # reader. The original byte audit must check digest before writing it.
        assert read_external_goal_diagnostic(root).learning_authority is False
        return
    with pytest.raises(ExternalGoalCandidateRejected):
        read_external_goal_diagnostic(root)


def test_other_schema_unknown_keys_and_duplicate_json_rejected(tmp_path):
    for mutate in (
        lambda d: {**d, "schema": "L13_QUALIFIED"},
        lambda d: {**d, "external_owner_signed": True},
        lambda d: {k: v for k, v in d.items() if k != "source_l22_ref"},
    ):
        r = store(tmp_path, mutate(real_shaped_review().audit_row()))
        with pytest.raises(ExternalGoalCandidateRejected):
            read_external_goal_diagnostic(r)
        (r / "external-goal-dev-review.json").unlink()
        r.rmdir()
    r = store(tmp_path, real_shaped_review().audit_row())
    file = r / "external-goal-dev-review.json"
    file.write_text('{"schema":"'+SCHEMA+'","schema":"'+SCHEMA+'"}')
    with pytest.raises(ExternalGoalCandidateRejected):
        read_external_goal_diagnostic(r)


def test_same_world_cannot_be_its_own_external_goal_source():
    external = real_shaped_review()
    _, host, supervisor, _, _ = setup()
    from adapters.mineflayer.normal_action import NormalWorldL0

    same = NormalWorldL0(
        external.source_session_id, host.intent_id, host.retained,
    )
    with pytest.raises(ValueError, match="current World"):
        S49SLMDevOwner(previous_external_goal=external).bind(same, supervisor)
