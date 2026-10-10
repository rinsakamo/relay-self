"""E7 native bridge typed trace audit: deliberately synthetic raw JSONL controls.

These fixture frames are protocol-shaped copies, not physical World evidence.
Even a complete, apparently live raw JSONL replay cannot grant E5 permission.
"""
from __future__ import annotations

import copy
import json
from dataclasses import FrozenInstanceError, replace

import pytest

import test_postmain_source_native_world as s27
from adapters.mineflayer.python_protocol import (
    MineflayerEntityFact,
    MineflayerPosition,
    MineflayerStreamDecoder,
)
from experiments import epistemic_e7_native_trace_gate as e7


def synthetic_frames() -> list[dict]:
    _data, _failed, _inputs, args = s27._fixture(distance_m=1.8)
    native = args["observation"]
    session = native.session_id
    far = native.snapshot
    origin = far.position
    near_target = MineflayerEntityFact(
        entity_id=43, name="zombie", entity_type="mob", distance=0.2,
        position=MineflayerPosition(origin.x + 0.2, origin.y, origin.z),
    )
    near = replace(far, nearby_entities=(near_target,))
    gone = replace(
        far, nearby_entities=(),
        nearby_entities_coverage=replace(
            far.nearby_entities_coverage, candidate_count=0,
        ),
    )

    def obs(kind, seq, snapshot, *, request_id=None):
        val = {
            "type": "observation", "session_id": session, "seq": seq,
            "kind": kind, "snapshot": s27._snapshot_wire(snapshot),
        }
        if request_id is not None:
            val["request_id"] = request_id
        return val

    return [
        {
            "type": "adapter_started", "session_id": session, "seq": 0,
            "mineflayer_version": s27.MINEFLAYER_VERSION,
            "config": {
                "host": "127.0.0.1", "port": 25565,
                "username": "RelaySelf", "version": None,
            },
        },
        obs("spawn", 1, gone),
        obs("entities", 2, far),
        obs("probe", 3, far, request_id=e7.MANIFEST["first_request_id"]),
        obs("entities", 4, gone),
        obs("entities", 5, near),
        obs("probe", 6, near, request_id=e7.MANIFEST["second_request_id"]),
        {"type": "shutdown_ack", "session_id": session, "seq": 7},
    ]


def raw(items: list[dict]) -> bytes:
    return ("\n".join(json.dumps(x, separators=(",", ":")) for x in items) + "\n").encode()


def fail(mutator, *, match: str | None = None):
    items = synthetic_frames()
    mutator(items)
    with pytest.raises(e7.E7Rejected, match=match):
        e7.audit_jsonl(raw(items))


def test_prospective_frozen_technical_source_version_v11():
    assert e7.digest() == e7.MANIFEST_SHA256
    assert e7.MANIFEST["base_e6"] == "4c4a5e2481468b94708df3296173c5ec9c1fdfe0"
    assert e7.MANIFEST["geometry_cm"] == [180, 20]
    assert e7.MANIFEST["policy_s24_boundary_cm"] == 100
    assert "DIFFERENT near entity" in e7.MANIFEST["source"]
    assert "not granted" in e7.MANIFEST["real_world_authorization"]
    amended = dict(e7.MANIFEST, geometry_cm=[200, 20])
    assert e7.digest(amended) != e7.MANIFEST_SHA256
    assert e7.MAX_FRAMES <= 256 and e7.MAX_BYTES <= 1_000_000


def test_exact_synthetic_native_typed_full_stream_and_strong_source_transition():
    fixture = synthetic_frames()
    typed = e7.audit_jsonl(raw(fixture), source_kind="SYNTHETIC")
    assert typed.classification == "SYNTHETIC_TYPED_TRACE_ONLY"
    assert typed.physically_authenticated is False
    assert typed.world_launched_by_e7 is False
    assert typed.can_start_e5_physical_study is False
    assert typed.e5_action3_parent_qualified is False
    assert typed.e5_survival_or_damage_effect == "UNDETERMINED"
    assert typed.new_physical_approval is False
    assert typed.total_frames == 8
    assert typed.first_probe_seq == 3 and typed.second_probe_seq == 6
    assert typed.far_distance_cm == 180 and typed.near_distance_cm == 20
    assert typed.far_entity_id == 42 and typed.near_entity_id == 43
    assert typed.seen_old_entity_absent and typed.seen_new_entity_spawn
    assert typed.session_id == fixture[0]["session_id"]
    with pytest.raises(FrozenInstanceError):
        typed.physically_authenticated = True


def test_same_trace_called_live_remains_unattested_with_nonzero_cli_exit(tmp_path, capsys):
    f = tmp_path / "supposed-real-mineflayer.jsonl"
    f.write_bytes(raw(synthetic_frames()))
    assert e7.main(["--audit", str(f)]) == 3
    report = json.loads(capsys.readouterr().out)
    assert report["classification"] == "UNATTESTED_NATIVE_TRACE"
    assert report["physically_authenticated"] is False
    assert report["can_start_e5_physical_study"] is False
    assert report["new_physical_approval"] is False


def test_safe_plan_has_no_world_runtime_and_no_source_evidence(capsys):
    assert e7.main(["--plan"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["classification"] == "E7_PHYSICAL_SOURCE_NOT_QUALIFIED"
    assert report["world_launched_by_e7"] is False
    assert report["new_physical_approval"] is False
    assert report["expected_cm"] == [180, 20]


@pytest.mark.parametrize("index,key,value", [
    (0, "session_id", "different-source"),
    (3, "session_id", "another-session"),
    (6, "session_id", "another-session"),
    (7, "session_id", "another-session"),
    (0, "seq", 1),
    (3, "seq", 2),
    (6, "seq", 5),
    (7, "seq", 6),
    (0, "mineflayer_version", "unknown-version"),
    (3, "request_id", "unknown-far-probe"),
    (6, "request_id", "unknown-near-probe"),
    (6, "request_id", e7.MANIFEST["first_request_id"]),
    (3, "request_id", ""),
    (6, "request_id", None),
    (3, "kind", "entities"),
    (6, "kind", "entities"),
    (4, "kind", "probe"),
    (5, "kind", "probe"),
    (5, "kind", "death"),
    (5, "kind", "respawn"),
    (5, "kind", "forcedMove"),
    (0, "type", "observation"),
    (7, "type", "adapter_started"),
])
def test_strict_session_cursor_nonce_native_kind_or_terminal_failure(index, key, value):
    fail(lambda frames: frames[index].__setitem__(key, value))


@pytest.mark.parametrize("index,distance", [
    (3, 1.79),
    (3, 2.0),
    (6, 0.19),
    (6, 0.21),
    (6, 1.8),
    (5, 0.25),
])
def test_actual_geometry_from_native_coordinates_overrides_claimed_distance(index, distance):
    def mutate(items):
        target = items[index]["snapshot"]["nearby_entities"][0]
        target["distance"] = distance
        target["position"]["x"] = (
            items[index]["snapshot"]["position"]["x"] + distance
        )
    fail(mutate)


@pytest.mark.parametrize("index", [2, 3, 4, 5, 6])
def test_distance_must_match_geometry_within_one_micro_meter(index):
    if index == 4:  # gone has no zombie; emulate fake reflected ghost
        fail(lambda items: items[4]["snapshot"]["nearby_entities"].append(
            copy.deepcopy(items[3]["snapshot"]["nearby_entities"][0])
        ))
    else:
        fail(lambda items: items[index]["snapshot"]["nearby_entities"][0].__setitem__(
            "distance", 4.0,
        ))


@pytest.mark.parametrize("index", [2, 3, 5, 6])
def test_duplicate_zombie_ambiguous_and_coverage_truncation_rejected(index):
    def duplicate(items):
        snap = items[index]["snapshot"]
        snap["nearby_entities"].append(copy.deepcopy(snap["nearby_entities"][0]))
        snap["nearby_entities_coverage"]["candidate_count"] = 2
    fail(duplicate)
    def truncated(items):
        snap = items[index]["snapshot"]
        snap["nearby_entities_coverage"]["truncated"] = True
        snap["nearby_entities_coverage"]["candidate_count"] = 17
    fail(truncated)


@pytest.mark.parametrize("index", [2, 3, 5, 6])
def test_identity_and_source_coverages_guard_all_native_frames(index):
    def empty(items):
        snap = items[index]["snapshot"]
        snap["nearby_entities"] = []
        snap["nearby_entities_coverage"]["candidate_count"] = 0
    fail(empty)
    def source_scope(items):
        items[index]["snapshot"]["nearby_entities_coverage"]["source_scope"] = "world_model"
    fail(source_scope)


def test_initial_far_entity_spawn_must_precede_far_request_and_match_identity():
    fail(lambda items: items[2].__setitem__("kind", "health"))
    fail(lambda items: items[3]["snapshot"]["nearby_entities"][0].__setitem__(
        "id", 777,
    ))
    fail(lambda items: items[2]["snapshot"]["nearby_entities"][0].__setitem__(
        "id", 777,
    ))


def test_removed_far_entity_must_be_witnessed_by_unsolicited_entities():
    fail(lambda items: items[4].__setitem__("kind", "health"))
    fail(lambda items: items[4].__setitem__("kind", "probe"))
    def not_gone(items):
        snap = items[4]["snapshot"]
        snap["nearby_entities"] = copy.deepcopy(items[3]["snapshot"]["nearby_entities"])
        snap["nearby_entities_coverage"]["candidate_count"] = 1
    fail(not_gone)


def test_no_retroactive_world_change_and_same_id_teleport_cannot_replace_new_entity():
    fail(lambda items: items[5]["snapshot"]["nearby_entities"][0].__setitem__("id", 42))
    fail(lambda items: items[6]["snapshot"]["nearby_entities"][0].__setitem__("id", 42))
    fail(lambda items: items[6]["snapshot"]["nearby_entities"][0].__setitem__("id", 777))


@pytest.mark.parametrize("index", [2, 3, 4, 5, 6])
def test_bot_motion_and_collision_side_effects_cannot_fake_stationary_calibration(index):
    def shifted(items):
        items[index]["snapshot"]["position"]["z"] += 0.02
    fail(shifted)
    def large_health_change(items):
        items[index]["kind"] = "death"
    fail(large_health_change)


def test_native_stream_wrong_order_or_missing_gap_must_fail():
    fail(lambda items: items.__delitem__(4))
    fail(lambda items: items.__delitem__(5))
    def duplicate_end(items):
        items.insert(-1, copy.deepcopy(items[6]))
        items[-1]["seq"] += 1
    fail(duplicate_end)


def test_native_stream_does_not_accept_action_effect_or_hurt_frames():
    def effect(items):
        items[5] = {
            "type": "effect_result", "session_id": items[5]["session_id"],
            "seq": 5, "action_id": "illegally-issued-action",
            "effect": "set_control", "result": "applied", "error": None,
        }
    fail(effect)
    def bad_hurt(items):
        items[5] = {
            "type": "entity_hurt", "session_id": items[5]["session_id"],
            "seq": 5, "entity_id": 42, "source_entity_id": None,
            "actor_entity_id": 13,
        }
    fail(bad_hurt)


def test_new_third_probe_cannot_pass_strict_two_requests():
    def third(items):
        extra = copy.deepcopy(items[6])
        extra["seq"] = 7
        extra["request_id"] = "e7:unexpected:third"
        items.insert(-1, extra)
        items[-1]["seq"] = 8
    fail(third)


@pytest.mark.parametrize("data", [
    b"", b"invalid\n", b"{broken}\n", b"{}\n",
    b"\xff\n", b"\x00\n", b" \n",
    b"{}\r\n", b"{}",
])
def test_raw_invalid_native_frame_never_becomes_world_success(data):
    with pytest.raises(e7.E7Rejected):
        e7.audit_jsonl(data)


def test_limits_and_cli_no_data_no_authentication(tmp_path, capsys):
    with pytest.raises(e7.E7Rejected):
        e7.audit_jsonl(raw(synthetic_frames()) + b"x" * e7.MAX_BYTES)
    with pytest.raises(e7.E7Rejected):
        e7.audit_jsonl(b"{}\n" * (e7.MAX_FRAMES + 1))
    nofile = tmp_path / "missing.jsonl"
    assert e7.main(["--audit", str(nofile)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "E7_TRACE_REJECTED"
    assert result["physically_authenticated"] is False


def test_untrusted_direct_typed_messages_cannot_claim_live_world_authentication():
    source = raw(synthetic_frames()).decode().splitlines()
    decoder = MineflayerStreamDecoder()
    typed = [decoder.decode(line) for line in source]
    report = e7.audit_decoded(typed, source_kind="UNATTESTED")
    assert report.classification == "UNATTESTED_NATIVE_TRACE"
    assert report.physically_authenticated is False
    assert report.new_physical_approval is False
    with pytest.raises(e7.E7Rejected):
        e7.audit_decoded(typed, source_kind="AUTHENTICATED")
    with pytest.raises(e7.E7Rejected):
        e7.audit_decoded(typed, source_kind=True)
