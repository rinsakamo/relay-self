"""SelfBody #632 S50 #645 companion; no new S49/L0/World authority."""
from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_motion_companion import (
    SampledBodyMotion,
    SelfBodyS50MotionRejected,
    compose_self_body_s50_motion_companion,
)
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.self_body import BodyOrigin, compose_self_body_view
from test_self_body import observation, outcome, prov


def s50() -> dict:
    motion = [
        {
            "world_tick": 251 + i,
            "displacement_m": d,
            "last_reported_input_active": False,
            "source_scope": "PAPER_CALLBACK_SAMPLE_ONLY",
        }
        for i, d in enumerate((0.05903579322217567, 0.005210808286785218, *([0.] * 6)))
    ]
    effects = [
        {
            "effect": effect, "node_record_index": index,
            "local_controls_active": active,
            "source_scope": "CLIENT_LOCAL_CONTROL_SNAPSHOT_ONLY",
        }
        for effect, index, active in (
            ("set_control", 236, True), ("clear_controls", 245, False),
            ("shutdown_clear_controls", 269, False),
        )
    ]
    return {
        "schema": "S50_SELFBODY_MOTION_DIAGNOSTIC_V0",
        "provenance_ceiling": "DIAGNOSTIC_ONLY_NOT_NATIVE_PRESENT",
        "session_id": "S",
        "action_id": "move1",
        "marker_id": "move1-S",
        "paper_world_uuid": "w-123",
        "subject_uuid": "p-123",
        "paper_original_sha256": "a" * 64,
        "client_original_sha256": "b" * 64,
        "paper_samples": motion,
        "client_effects": effects,
        "observed_motion_while_reported_input_off_ticks": [251, 252],
        "client_player_input_write_returns": 0,
        "client_position_write_returns": 23,
        "paper_player_input_callbacks": 0,
        "client_packet_diagnostic": "NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH",
        "cross_clock_alignment": "NOT_ATTESTED",
        "effective_s15_clear_world_tick": "NOT_ATTESTED",
        "full_tick_input_coverage": False,
        "physically_stopped_attested": False,
        "goal_admitted": False,
        "p1_wait_ticks_admitted": 0,
        "l10_pairs_admitted": 0,
        "s10_updates_admitted": 0,
        "s11_grants_admitted": 0,
    }


def existing_body(*, action_source=True):
    source = observation()
    if action_source:
        source = replace(
            source, action_id="move1",
            consequence_provenance=prov("world-consequence"),
        )
    return compose_self_body_view(
        self_id="self", session_id="S", epoch_id="epoch-1",
        observation=source, outcome=outcome(ActionOutcomeDisposition.OUTCOME),
    )


def test_original_selfbody_view_preserved_and_sampled_motion_available():
    owner = existing_body()
    before = owner.observed("position_x")
    companion = compose_self_body_s50_motion_companion(owner, s50())
    assert companion.self_body is owner
    assert owner.observed("position_x") == before
    assert owner.observed("position_x").origin is BodyOrigin.OBSERVATION
    assert owner.observed("paper_motion").origin is BodyOrigin.UNKNOWN
    assert companion.action_id == "move1"
    assert companion.sampled_at(251).sampled_motion is SampledBodyMotion.SAMPLED_POSITION_CHANGED
    assert companion.sampled_at(252).sampled_motion is SampledBodyMotion.SAMPLED_POSITION_CHANGED
    assert companion.sampled_at(258).sampled_motion is SampledBodyMotion.SAMPLED_ZERO_DELTA
    assert companion.sampled_at(259) is None
    assert math.isclose(companion.sampled_at(251).displacement_m, 0.05903579322217567)
    assert companion.sampled_at(258).physical_stability_attested is False
    assert companion.client_control_effects == (
        "set_control", "clear_controls", "shutdown_clear_controls")
    assert companion.client_player_input_write_returns == 0
    assert companion.client_position_write_returns == 23
    summary = companion.cognitive_summary()
    assert summary["changed_with_last_reported_input_off"] == (251, 252)
    assert summary["world_client_clock_alignment"] == "NOT_ATTESTED"
    assert summary["effective_clear_world_tick"] == "NOT_ATTESTED"
    assert summary["native_present_minted"] is False
    assert summary["goal_admitted"] is False
    assert summary["p1_wait_granted"] is False
    assert summary["learning_updates"] == 0
    assert summary["action_issued"] is False
    assert summary["model_calls"] == 0
    assert companion.self_body.observation is owner.observation
    with pytest.raises(FrozenInstanceError):
        companion.physically_stopped_attested = True


def test_l0_s16_observation_without_matching_action_lineage_fails_closed():
    owner = existing_body(action_source=False)
    with pytest.raises(SelfBodyS50MotionRejected, match="native Present"):
        compose_self_body_s50_motion_companion(owner, s50())
    assert owner.observed("paper_motion").origin is BodyOrigin.UNKNOWN


@pytest.mark.parametrize("bad", [
    "no_owner_outcome", "unavailable_s16", "other_session",
    "other_action", "other_marker", "other_present_action",
    "wrong_ceiling", "no_source_schema", "bad_digest",
    "missing_tick", "duplicate_tick", "false_stability", "false_wait",
    "foreign_node_clock", "negative_distance", "nan_distance", "changed_off_ticks",
    "clear_still_on", "no_clear", "unbounded_packet", "wrong_packet_label",
])
def test_fail_closed_without_forging_cognitive_truth(bad):
    owner = existing_body()
    source = s50()
    if bad == "no_owner_outcome":
        owner = compose_self_body_view(session_id="S", epoch_id="e")
    elif bad == "unavailable_s16":
        owner = compose_self_body_view(
            session_id="S", epoch_id="e",
            outcome=outcome(ActionOutcomeDisposition.UNAVAILABLE),
        )
    elif bad == "other_session":
        source["session_id"] = "foreign"
    elif bad == "other_action":
        source["action_id"] = "other"
    elif bad == "other_marker":
        source["marker_id"] = "other-S"
    elif bad == "other_present_action":
        owner = compose_self_body_view(
            session_id="S", epoch_id="e", outcome=outcome(ActionOutcomeDisposition.OUTCOME),
            observation=observation(),
        )
        # An action-associated Present from a different Action is disallowed by
        # compose_self_body_view itself. Exercise that owner invariant separately.
        assert owner.observation.action_id is None
        source["action_id"] = "other"
    elif bad == "wrong_ceiling":
        source["provenance_ceiling"] = "VERIFIED_NATIVE_PRESENT"
    elif bad == "no_source_schema":
        source.pop("schema")
    elif bad == "bad_digest":
        source["paper_original_sha256"] = "unknown"
    elif bad == "missing_tick":
        source["paper_samples"].pop()
    elif bad == "duplicate_tick":
        source["paper_samples"][3]["world_tick"] = 253
    elif bad == "false_stability":
        source["physically_stopped_attested"] = True
    elif bad == "false_wait":
        source["p1_wait_ticks_admitted"] = 1
    elif bad == "foreign_node_clock":
        source["client_effects"][1]["node_record_index"] = 200
    elif bad == "negative_distance":
        source["paper_samples"][2]["displacement_m"] = -1
    elif bad == "nan_distance":
        source["paper_samples"][2]["displacement_m"] = float("nan")
    elif bad == "changed_off_ticks":
        source["observed_motion_while_reported_input_off_ticks"] = []
    elif bad == "clear_still_on":
        source["client_effects"][1]["local_controls_active"] = True
    elif bad == "no_clear":
        source["client_effects"][1]["effect"] = "set_control"
    elif bad == "unbounded_packet":
        source["client_position_write_returns"] = 100000
    elif bad == "wrong_packet_label":
        source["client_packet_diagnostic"] = "BOTH_WRITE_AND_CALLBACK_SEEN_IDENTITY_UNPROVEN"
    with pytest.raises(SelfBodyS50MotionRejected):
        compose_self_body_s50_motion_companion(owner, source)


def test_no_unqualified_native_selfbody_readback_allowed():
    owner = compose_self_body_view(session_id="S", epoch_id="unqualified")
    with pytest.raises(SelfBodyS50MotionRejected, match="S16"):
        compose_self_body_s50_motion_companion(owner, s50())
    with pytest.raises(SelfBodyS50MotionRejected):
        compose_self_body_s50_motion_companion(existing_body(), [])
    with pytest.raises(SelfBodyS50MotionRejected):
        compose_self_body_s50_motion_companion(existing_body(), {**s50(), "action_id": True})
