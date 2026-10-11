"""C15 source-bound Mineflayer endpoint certificate regression tests.

All data are strict existing Mineflayer JSONL fixtures. No server, LLM,
new protocol or live Action is started by this test suite.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import fields

import pytest

from adapters.mineflayer.goal_witness import (
    LIVE_QUALIFICATION,
    SIGNED_ACTION_LABEL,
    EndpointReducer,
    EndpointWitness,
    InvalidSpatialContract,
    Region,
    SpatialContract,
    manifest,
)
from adapters.mineflayer.python_protocol import MINEFLAYER_VERSION

SESSION = "c15-fixture-session"
START_ID = "c15-control-on"
STOP_ID = "c15-controls-stop"
GOAL = (5.0, 64.0, 1.0)
ALTERNATIVE = (-5.0, 64.0, 1.0)
BASELINE = (0.0, 64.0, 1.0)
OUTSIDE = (0.5, 64.0, 1.0)


def spatial_contract() -> SpatialContract:
    return SpatialContract(
        SESSION, START_ID, STOP_ID,
        Region((4.0, 63.0, 0.0), (6.0, 66.0, 2.0)),
        Region((-6.0, 63.0, 0.0), (-4.0, 66.0, 2.0)),
    )


def started() -> dict:
    return {
        "type": "adapter_started", "session_id": SESSION, "seq": 0,
        "mineflayer_version": MINEFLAYER_VERSION,
        "config": {"host": "127.0.0.1", "port": 25565,
                   "username": "RelaySelf", "version": None},
    }


def probe(p: tuple[float, float, float], kind: str = "probe") -> dict:
    return {
        "type": "observation", "session_id": SESSION, "seq": -1, "kind": kind,
        "snapshot": {
            "health": 20.0, "food": 12.0, "food_saturation": 5.0,
            "oxygen_level": None,
            "position": {"x": p[0], "y": p[1], "z": p[2]},
            "time": None, "inventory": [], "nearby_entities": [],
            "nearby_entities_coverage": {
                "source_scope": "mineflayer_entity_registry",
                "max_distance": 16.0, "max_entities": 16,
                "candidate_count": 0, "truncated": False,
            },
        },
    }


def ack(action_id: str, effect: str, result: str = "applied") -> dict:
    return {
        "type": "effect_result", "session_id": SESSION, "seq": -1,
        "action_id": action_id, "effect": effect, "result": result,
        "error": None if result == "applied" else "rejected fixture",
    }


def transcript(endpoint: tuple[float, float, float] = GOAL) -> list[dict]:
    return resequence([
        started(), probe(BASELINE), ack(START_ID, "set_control"),
        ack(STOP_ID, "clear_controls"), probe(endpoint), probe(endpoint),
    ])


def resequence(rows: list[dict]) -> list[dict]:
    for i, value in enumerate(rows):
        value["seq"] = i
    return rows


def decode_qualification(rows: list[dict]) -> EndpointWitness:
    return EndpointReducer().qualify(
        [json.dumps(x) for x in rows], spatial_contract()
    )


def malformed_case(name: str) -> list[dict]:
    rows = transcript()
    if name == "no_terminal_probe":
        rows = rows[:4]
    elif name == "only_one_terminal_probe":
        rows = rows[:5]
    elif name == "outside_both_regions":
        rows[-2]["snapshot"]["position"]["x"] = OUTSIDE[0]
        rows[-1]["snapshot"]["position"]["x"] = OUTSIDE[0]
    elif name == "on_goal_boundary":
        rows[-2]["snapshot"]["position"]["x"] = 4.01
        rows[-1]["snapshot"]["position"]["x"] = 4.01
    elif name == "unstable_position":
        rows[-1]["snapshot"]["position"]["x"] = 5.2
    elif name == "terminal_probes_in_disagreeing_regions":
        rows[-1]["snapshot"]["position"]["x"] = -5.0
    elif name == "preexisting_goal":
        rows[1] = probe(GOAL)
    elif name == "preexisting_alternative":
        rows[1] = probe(ALTERNATIVE)
        rows[-2] = probe(ALTERNATIVE)
        rows[-1] = probe(ALTERNATIVE)
    elif name == "no_displacement":
        # A genuinely unmoved terminal is not an endpoint: pre-existing veto.
        rows[1] = probe(GOAL)
    elif name == "probe_before_stop_only":
        rows = [rows[0],rows[1],rows[2],probe(GOAL)]
    elif name == "missing_control_ack":
        rows.pop(2)
    elif name == "missing_stop_ack":
        rows.pop(3)
    elif name == "rejected_control_ack":
        rows[2] = ack(START_ID, "set_control", "rejected")
    elif name == "rejected_stop_ack":
        rows[3] = ack(STOP_ID, "clear_controls", "rejected")
    elif name == "wrong_control_action_id":
        rows[2] = ack("foreign-control", "set_control")
    elif name == "wrong_stop_action_id":
        rows[3] = ack("foreign-stop", "clear_controls")
    elif name == "interleaved_forcedMove":
        rows.insert(3, probe(GOAL, "forcedMove"))
    elif name == "interleaved_respawn":
        rows.insert(3, probe(GOAL, "respawn"))
    elif name == "interleaved_death":
        rows.insert(3, probe(GOAL, "death"))
    elif name == "nonprobe_after_stop":
        rows.insert(4, probe(GOAL, "move"))
    elif name == "poststop_before_clear_ack":
        rows.insert(3, probe(GOAL))
    elif name == "duplicate_stop_ack":
        rows.insert(4, ack(STOP_ID, "clear_controls"))
    elif name == "duplicate_probe_evidence":
        rows.append(probe(GOAL))
    elif name == "session_change":
        rows[4]["session_id"] = "different-session"
    elif name == "sequence_gap":
        rows[5]["seq"] = 9
        return rows
    elif name == "position_nan_or_nonfinite":
        rows[4]["snapshot"]["position"]["x"] = float("nan")
    elif name == "non_authoritative_move_only":
        rows = [rows[0],rows[1],rows[2], probe(GOAL, "move"), rows[3]]
    elif name == "post_target_moved_back_out":
        rows.insert(3, probe(GOAL, "move"))
        rows[-2] = probe(OUTSIDE)
        rows[-1] = probe(OUTSIDE)
    elif name == "invalid_message_type":
        rows.insert(3, {"type": "unrecognized", "seq": -1,
                        "session_id": SESSION})
    else:
        raise AssertionError("unregistered adverse fixture " + name)
    return resequence(rows)


ADVERSE_TRANSCRIPTS = (
    "no_terminal_probe", "only_one_terminal_probe", "outside_both_regions",
    "on_goal_boundary", "unstable_position",
    "terminal_probes_in_disagreeing_regions", "preexisting_goal",
    "preexisting_alternative", "no_displacement", "probe_before_stop_only",
    "missing_control_ack", "missing_stop_ack", "rejected_control_ack",
    "rejected_stop_ack", "wrong_control_action_id", "wrong_stop_action_id",
    "interleaved_forcedMove", "interleaved_respawn", "interleaved_death",
    "nonprobe_after_stop", "poststop_before_clear_ack",
    "duplicate_stop_ack", "duplicate_probe_evidence", "session_change",
    "sequence_gap", "position_nan_or_nonfinite", "non_authoritative_move_only",
    "post_target_moved_back_out", "invalid_message_type",
)


def test_manifest_frozen_and_source_contract_matches_repo_adapter() -> None:
    m = manifest()
    assert m["version"] == "AC-C-C15-MINEFLAYER-SPATIAL-WITNESS-v1"
    assert m["actual_source"]["adapter_version"] == MINEFLAYER_VERSION
    assert m["qualification_contract"]["post_stop_probe_count"] == 2
    assert m["output"]["signed_negative_action_label"] == SIGNED_ACTION_LABEL
    assert m["output"]["live_goal_attestation"] == LIVE_QUALIFICATION


@pytest.mark.parametrize(("end", "expected"), [
    (GOAL, "GOAL_REGION_OBSERVED"),
    (ALTERNATIVE, "ALTERNATIVE_REGION_OBSERVED"),
])
def test_disjoint_stable_two_post_stop_probes_are_only_spatial(
    end: tuple[float, float, float], expected: str
) -> None:
    report = decode_qualification(transcript(end))
    assert report.status == expected
    assert report.reason == "SPATIAL_ENDPOINT_ONLY"
    assert report.evidence == tuple(f"{SESSION}:{i}" for i in range(6))
    assert isinstance(report, EndpointWitness)
    assert not any(k in {field.name for field in fields(report)} for k in (
        "z", "correct", "signed", "positive", "negative", "skill_success",
        "learning", "habit", "goal_success",
    ))


@pytest.mark.parametrize("name", ADVERSE_TRANSCRIPTS)
def test_adverse_mineflayer_source_is_never_an_endpoint(name: str) -> None:
    result = decode_qualification(malformed_case(name))
    assert result.status == "UNDETERMINED", name
    assert result.reason != "SPATIAL_ENDPOINT_ONLY", name


def test_strict_decoder_rejects_duplicate_original_message_seq() -> None:
    rows = transcript()
    rows[-1]["seq"] = rows[-2]["seq"]
    assert decode_qualification(rows).status == "UNDETERMINED"


def test_source_bounded_move_event_is_not_termination_evidence() -> None:
    rows = transcript()
    rows.insert(3, probe(GOAL, "move"))
    resequence(rows)
    result = decode_qualification(rows)
    assert result.status == "GOAL_REGION_OBSERVED"
    # The two explicit stop-following probes, NOT prior move, identify endpoint.
    assert result.evidence[-2:] == (f"{SESSION}:5", f"{SESSION}:6")


def test_missing_preprobe_even_with_applied_effect_is_undetermined() -> None:
    rows = transcript()
    rows.pop(1)
    assert decode_qualification(resequence(rows)).status == "UNDETERMINED"


def test_no_goal_label_even_on_observed_alternative_region() -> None:
    w = decode_qualification(transcript(ALTERNATIVE))
    assert w.status == "ALTERNATIVE_REGION_OBSERVED"
    assert SIGNED_ACTION_LABEL == "BLOCKED_UNDERDETERMINED"
    assert LIVE_QUALIFICATION == "NOT_RUN"


def test_spatial_reducer_is_replay_closed_even_with_modified_records() -> None:
    reducer = EndpointReducer()
    spec = spatial_contract()
    rows = transcript()
    first = reducer.qualify([json.dumps(x) for x in rows], spec)
    assert first.status == "GOAL_REGION_OBSERVED"
    second = reducer.qualify([json.dumps(x) for x in rows], spec)
    assert second.status == "UNDETERMINED"
    assert second.reason == "DUPLICATE_TRANSACTION"
    changed = transcript(ALTERNATIVE)
    third = reducer.qualify([json.dumps(x) for x in changed], spec)
    assert third.status == "UNDETERMINED"


@pytest.mark.parametrize("bad", [
    Region((4.0, 63.0, 0.0), (6.0, 66.0, 2.0)),
    Region((6.1, 63.0, 0.0), (8.0, 66.0, 2.0)),
    Region((5.0, 64.0, 1.0), (7.0, 66.0, 2.0)),
])
def test_invalid_or_touching_goal_boxes_cannot_qualify(bad: Region) -> None:
    with pytest.raises(InvalidSpatialContract):
        SpatialContract(SESSION, START_ID, STOP_ID, spatial_contract().goal, bad)


@pytest.mark.parametrize(("low", "high"), [
    ((1.0,1.0,1.0),(1.0,2.0,2.0)),
    ((1.0,1.0,1.0),(2.0,0.0,2.0)),
    ((float("nan"),1.0,1.0),(2.0,2.0,2.0)),
    ((1.0,1.0,1.0),(float("inf"),2.0,2.0)),
])
def test_malformed_regions_fail_closed(low: tuple, high: tuple) -> None:
    with pytest.raises(InvalidSpatialContract):
        Region(low,high)


def test_action_and_session_authority_identifiers_are_explicit_and_distinct() -> None:
    s = spatial_contract()
    with pytest.raises(InvalidSpatialContract):
        SpatialContract(s.session_id, START_ID, START_ID, s.goal, s.alternative)
    with pytest.raises(InvalidSpatialContract):
        SpatialContract("", START_ID, STOP_ID, s.goal, s.alternative)
    wrong = SpatialContract("other-session", START_ID, STOP_ID,s.goal,s.alternative)
    result = EndpointReducer().qualify(
        [json.dumps(x) for x in transcript()], wrong
    )
    assert result.status == "UNDETERMINED"


def test_source_json_malformed_or_missing_one_key_not_promoted() -> None:
    rows = transcript()
    del rows[4]["snapshot"]["position"]["z"]
    assert decode_qualification(rows).status == "UNDETERMINED"
    assert EndpointReducer().qualify(["not json"],spatial_contract()).status == "UNDETERMINED"


def test_fixture_report_is_deterministic_and_all_adversarial_fail_closed() -> None:
    result = fixture_report()
    assert result == fixture_report()
    assert result["recognitions"] == 2
    assert result["false_positives"] == 0
    assert result["adverse_undetermined"] == len(ADVERSE_TRANSCRIPTS)
    assert result["live_minecraft_qualification"] == "NOT_RUN"
    assert result["signed_action_label"] == "BLOCKED_UNDERDETERMINED"


def fixture_report() -> dict:
    good = [
        decode_qualification(transcript(p)).status
        for p in (GOAL, ALTERNATIVE)
    ]
    bad = [decode_qualification(malformed_case(name)).status
           for name in ADVERSE_TRANSCRIPTS]
    return {
        "version": manifest()["version"],
        "recognitions": sum(x != "UNDETERMINED" for x in good),
        "adverse_undetermined": sum(x == "UNDETERMINED" for x in bad),
        "false_positives": sum(x != "UNDETERMINED" for x in bad),
        "live_minecraft_qualification": LIVE_QUALIFICATION,
        "signed_action_label": SIGNED_ACTION_LABEL,
        "new_protocol_commands": 0,
        "action_issues": 0,
        "automatic_learning_updates": 0,
    }


def test_ci_emits_machine_readable_C15_result() -> None:
    warnings.warn("C15_RESULT_JSON "+json.dumps(
        fixture_report(), sort_keys=True
    ), UserWarning)
