"""S27: bounded Mineflayer entity-registry fact to fresh S24 World evidence."""
from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

import test_postmain_local_recovery_action as s23
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MINEFLAYER_VERSION,
    MineflayerAdapterProtocolError,
    MineflayerEntityFact,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerStreamDecoder,
)
from relay_self.action import ActionState
from relay_self.postfailure_cognition import run_explicit_postfailure_epoch
from relay_self.source_native_world import (
    InvalidSourceNativeWorldEvidence,
    project_source_native_threat,
)

ROOT = Path(__file__).resolve().parents[1]
ENTITY_ID = 42


def _fixture(*, distance_m=1.8, seq=5):
    data, failed, inputs, _proposal, _authorized, _issued, _bound, _handoff, consequence, _interpretation, closed = s23._completed()
    assert closed.state is ActionState.OUTCOME
    assert consequence.after_observation is not None
    after = consequence.after_observation
    origin = after.snapshot.position
    target = MineflayerEntityFact(
        entity_id=ENTITY_ID,
        name="zombie",
        entity_type="mob",
        distance=distance_m,
        position=MineflayerPosition(origin.x + distance_m, origin.y, origin.z),
    )
    coverage = MineflayerNearbyEntitiesCoverage(
        source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
        max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
        max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
        candidate_count=1,
        truncated=False,
    )
    observation = MineflayerObservation(
        session_id=consequence.session_id,
        seq=seq,
        kind="probe",
        snapshot=replace(
            after.snapshot, nearby_entities=(target,),
            nearby_entities_coverage=coverage,
        ),
    )
    args = {
        "supervisor": data["supervisor"],
        "action": closed,
        "consequence": consequence,
        "observation": observation,
        "target_entity_id": ENTITY_ID,
        "target_name": "zombie",
        "observed_at_ns": 65,
        "inspected_at_ns": 67,
        "max_age_ns": 5,
    }
    return data, failed, inputs, args


def _project(args, **changes):
    return project_source_native_threat(**{**args, **changes})


def _snapshot_wire(snapshot):
    return {
        "health": snapshot.health,
        "food": snapshot.food,
        "food_saturation": snapshot.food_saturation,
        "oxygen_level": snapshot.oxygen_level,
        "position": asdict(snapshot.position),
        "time": None if snapshot.time is None else asdict(snapshot.time),
        "inventory": [asdict(item) for item in snapshot.inventory],
        "nearby_entities": [
            {
                "id": e.entity_id, "name": e.name,
                "type": e.entity_type, "distance": e.distance,
                "position": asdict(e.position),
            }
            for e in snapshot.nearby_entities
        ],
        "nearby_entities_coverage": asdict(snapshot.nearby_entities_coverage),
    }


def _wire_message(message):
    if isinstance(message, MineflayerObservation):
        return json.dumps({
            "type": "observation",
            "session_id": message.session_id,
            "seq": message.seq,
            "kind": message.kind,
            "snapshot": _snapshot_wire(message.snapshot),
        })
    return json.dumps({
        "type": "effect_result",
        "session_id": message.session_id,
        "seq": message.seq,
        "action_id": message.action_id,
        "effect": message.effect,
        "result": message.result,
        "error": message.error,
    })


def test_native_exact_snapshot_distance_projects_through_s24_cognition():
    choices = []
    for distance, expected in ((0.2, "MOVE_AWAY"), (1.8, "WAIT")):
        data, failed, inputs, args = _fixture(distance_m=distance)
        receipt = _project(args)
        assert receipt.source.provenance == receipt.evidence.provenance
        assert receipt.evidence.provenance.source == "mineflayer"
        assert receipt.target_entity_id == ENTITY_ID
        assert receipt.target_name == "zombie"
        assert receipt.evidence.threat_clearance_cm == int(distance * 100 + 0.5)
        assert receipt.evidence.action_id == s23.ACTION3
        assert receipt.evidence.session_id == s23.SESSION3
        assert receipt.evidence.binding_id == s23.BINDING3
        assert receipt.parent_after_seq == args["consequence"].after_observation.seq

        # S24 itself is unchanged: source-native typed evidence supplies only
        # its World distance field, and no Action authorization is produced.
        trace = run_explicit_postfailure_epoch(
            data["supervisor"], args["action"], args["consequence"],
            inputs["recovery_skill"], data["intent"],
            data["commit"].new_state, receipt.evidence,
            at_ns=70, provenance=s23.p("s27-explicit-native-epoch"),
        )
        assert trace.selected_candidate == expected
        assert receipt.evidence.provenance in trace.source_provenance
        assert data["supervisor"].open_actions == ()
        assert failed.is_terminal
        assert inputs["recovery_skill"].is_current_snapshot
        assert data["commit"].new_state.revision == 1
        choices.append(trace.selected_candidate)
    assert choices == ["MOVE_AWAY", "WAIT"]
    document = json.loads(
        (ROOT / "docs/postmain-s27-native-observation.json").read_text(encoding="utf-8")
    )
    assert document["near"]["distance_cm"] == 20
    assert document["far"]["distance_cm"] == 180
    assert document["near"]["candidate"] == "MOVE_AWAY"
    assert document["far"]["candidate"] == "WAIT"


def test_protocol_decoder_contiguous_native_sequence_qualifies_new_observation():
    _data, _failed, _inputs, args = _fixture()
    parent = args["consequence"]
    started = {
        "type": "adapter_started", "session_id": parent.session_id,
        "seq": 0, "mineflayer_version": MINEFLAYER_VERSION,
        "config": {"host": "127.0.0.1", "port": 25565, "username": "RelaySelf", "version": None},
    }
    decoder = MineflayerStreamDecoder()
    decoder.decode(json.dumps(started))
    for prior in (
        parent.before_observation, parent.dispatch_receipt,
        parent.cleanup_receipt, parent.after_observation,
    ):
        decoder.decode(_wire_message(prior))
    decoded = decoder.decode(_wire_message(args["observation"]))
    assert decoder.session_id == parent.session_id
    assert decoder.next_seq == args["observation"].seq + 1
    assert decoded == args["observation"]
    receipt = _project(args, observation=decoded)
    assert receipt.evidence.provenance.reference == f"{parent.session_id}:5"
    with pytest.raises(MineflayerAdapterProtocolError):
        decoder.decode(_wire_message(args["observation"]))


@pytest.mark.parametrize(
    "field,change",
    [
        ("observation", "old_seq"),
        ("observation", "wrong_session"),
        ("observation", "non_probe"),
        ("target_entity_id", "wrong_target"),
        ("target_name", "wrong_name"),
        ("observed_at_ns", "before_outcome"),
        ("inspected_at_ns", "future"),
        ("inspected_at_ns", "expired"),
        ("max_age_ns", "zero"),
        ("consequence", "wrong_parent_action"),
        ("action", "wrong_action"),
        ("consequence", "unknown_outcome"),
    ],
)
def test_lineage_identity_and_freshness_fail_closed(field, change):
    data, _failed, _inputs, args = _fixture()
    val = args[field]
    if change == "old_seq":
        val = replace(val, seq=args["consequence"].after_observation.seq)
    elif change == "wrong_session":
        val = replace(val, session_id="another-session")
    elif change == "non_probe":
        val = replace(val, kind="move")
    elif change == "wrong_target":
        val = 55
    elif change == "wrong_name":
        val = "creeper"
    elif change == "before_outcome":
        val = 60
    elif change == "future":
        val = 64
    elif change == "expired":
        val = 71
    elif change == "zero":
        val = 0
    elif change == "wrong_parent_action":
        val = replace(val, action_id="other-action")
    elif change == "wrong_action":
        val = data["closed1"]
    elif change == "unknown_outcome":
        val = replace(val, status=type(val.status).UNDETERMINED)
    else:
        raise AssertionError(change)
    before = data["supervisor"].last_at_ns
    with pytest.raises(InvalidSourceNativeWorldEvidence):
        _project(args, **{field: val})
    assert data["supervisor"].last_at_ns == before
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize(
    "variant",
    ["missing", "duplicate_id", "renamed", "truncated", "wrong_coverage",
     "bad_distance", "bad_position", "out_of_range", "unknown_name"],
)
def test_incomplete_or_inconsistent_entity_registry_is_not_safety_evidence(variant):
    data, _failed, _inputs, args = _fixture()
    observation = args["observation"]
    snapshot = observation.snapshot
    entity = snapshot.nearby_entities[0]
    coverage = snapshot.nearby_entities_coverage
    if variant == "missing":
        snapshot = replace(
            snapshot, nearby_entities=(),
            nearby_entities_coverage=replace(coverage, candidate_count=0),
        )
    elif variant == "duplicate_id":
        snapshot = replace(
            snapshot, nearby_entities=(entity, entity),
            nearby_entities_coverage=replace(coverage, candidate_count=2),
        )
    elif variant == "renamed":
        snapshot = replace(snapshot, nearby_entities=(replace(entity, name="creeper"),))
    elif variant == "truncated":
        # A structurally valid truncated 16-of-17 registry snapshot.
        entities = tuple(
            replace(entity, entity_id=i + 1)
            for i in range(MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES)
        )
        snapshot = replace(
            snapshot, nearby_entities=entities,
            nearby_entities_coverage=replace(
                coverage, candidate_count=17, truncated=True,
            ),
        )
    elif variant == "wrong_coverage":
        snapshot = replace(
            snapshot,
            nearby_entities_coverage=replace(coverage, candidate_count=2),
        )
    elif variant == "bad_distance":
        snapshot = replace(snapshot, nearby_entities=(replace(entity, distance=2.2),))
    elif variant == "bad_position":
        snapshot = replace(
            snapshot,
            nearby_entities=(replace(
                entity, position=replace(entity.position, x=entity.position.x + 0.4),
            ),),
        )
    elif variant == "out_of_range":
        snapshot = replace(
            snapshot,
            nearby_entities=(replace(
                entity, position=replace(entity.position, x=entity.position.x + 17),
                distance=18.8,
            ),),
        )
    elif variant == "unknown_name":
        snapshot = replace(snapshot, nearby_entities=(replace(entity, name=None),))
    else:
        raise AssertionError(variant)
    before = data["supervisor"].last_at_ns
    with pytest.raises(InvalidSourceNativeWorldEvidence):
        _project(args, observation=replace(observation, snapshot=snapshot))
    assert data["supervisor"].last_at_ns == before


def test_absent_target_never_generates_far_or_wait_candidate():
    data, _failed, _inputs, args = _fixture()
    observation = args["observation"]
    empty = replace(
        observation, snapshot=replace(
            observation.snapshot,
            nearby_entities=(),
            nearby_entities_coverage=replace(
                observation.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
        ),
    )
    with pytest.raises(InvalidSourceNativeWorldEvidence):
        _project(args, observation=empty)
    assert data["supervisor"].last_at_ns == 60
    assert data["supervisor"].open_actions == ()


def test_receipt_is_explicit_about_source_and_no_field_authentication():
    receipt = json.loads(
        (ROOT / "docs/postmain-s27-receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["base_head"] == "33690ff475f4a040bd5b0d4821e3f0175d823bda"
    assert receipt["classification"] == "SOURCE_NATIVE_BOUNDED_MINEFLAYER_WORLD_EVIDENCE_PROJECTION_QUALIFIED"
    assert receipt["live_minecraft"] == "NOT_RUN"
    assert receipt["cryptographic_source_authentication"] is False
    assert receipt["absent_target_means_safe"] is False
    assert receipt["automatic_epoch_reentry"] is False
