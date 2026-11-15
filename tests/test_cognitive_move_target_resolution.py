"""Offline MOVE Need → Goal → selected configured target → geometry.

These tests do not exercise native motor controls, STOP settling or World reach.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition
from experiments.cognitive_minimal_minecraft_dev import (
    execute_one_cognitive_world_turn,
    native_schema_percept,
)
from experiments.cognitive_move_target_resolution import (
    MoveTargetRefusal,
    resolve_selected_move_target,
)
from experiments.controlled_minecraft_vertical import (
    ControlledDestination,
    ControlledScenario,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    Predicate,
    assemble_l1_select,
    cpu_schema_epoch,
    initial_move_pattern,
    initial_patterns,
    initial_patterns_with_move,
    resolve_l1_choice,
)
from relay_self.initial_skill_ir import (
    SkillIRRefusal,
    compile_initial_skill,
    initial_skill_descriptors,
)
from relay_self.intent import IntentCommitment
from relay_self.move_destination_ref import move_destination_ref
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionMode, ProviderDecision, RelayEngine
from test_cognitive_minimal_minecraft_dev import observation

MOVE_ONLY = frozenset({("MOVE", 1)})


def configured(*, targets=("waypoint-1", "waypoint-2")):
    positions = (
        MineflayerPosition(3, 64, 0),
        MineflayerPosition(0, 64, -5),
    )
    destinations = tuple(
        ControlledDestination(
            dest_id, positions[i], "externally declared point",
            Provenance("configured-destination", f"route-{i + 1}"),
        )
        for i, dest_id in enumerate(targets)
    )
    return ControlledScenario(
        hazard_entity_names=frozenset(),
        food_threshold=10,
        edible_item_names=(),
        destinations=destinations,
    )


def prepare(*, scenario=None, need=True, seq=12, skills=MOVE_ONLY):
    scenario = scenario if scenario is not None else configured()
    native = observation(
        seq, kind="probe", food=20, session_id="world-A",
        request_id=f"move-probe-{seq}",
    )
    percept = native_schema_percept(
        native, scenario, self_id="self-A", exploration_need=need,
    )
    frame = cpu_schema_epoch(
        percept, initial_patterns_with_move(),
        allowed_skills=skills, epoch=1,
    )
    return native, scenario, percept, frame


def select(frame, *, skill="MOVE", target="waypoint-1"):
    owner = IntentCommitment()
    round_ = assemble_l1_select(frame, intent_owner=owner)
    if skill == "ESCALATE_L2":
        number = next(n for n, x in round_.numbered if x == skill)
    else:
        number = next(
            n for n, option in round_.numbered
            if getattr(option, "skill_id", None) == skill
            and option.target_ref.startswith(f"destination:{target}@")
        )
    calls = []

    def provider(req, *, mode):
        assert mode is CognitionMode.BOUNDED
        calls.append(req)
        return ProviderDecision.resolved(number)

    result = resolve_l1_choice(
        round_, RelayEngine(provider)(round_.request),
        current_frame=frame, intent_owner=owner, available_skills=MOVE_ONLY,
    )
    assert len(calls) == 1
    assert owner.current_intent is None
    return result


def test_move_pattern_is_optional_and_no_unqualified_motor_mapping():
    pattern = initial_move_pattern()
    assert pattern.predicate is Predicate.EXPLORE
    assert pattern.goal_id == "EXPLORE_WORLD"
    assert pattern.target_kind == "DESTINATION"
    assert len(initial_patterns().patterns) == 3
    assert len(initial_patterns_with_move().patterns) == 4
    descriptor = next(x for x in initial_skill_descriptors() if x.skill_id == "MOVE")
    assert descriptor.status == "NATIVE_BOUNDED_MOVE_DEV_ISSUER_EXISTS"
    assert descriptor.capability_ref == "MOVE"
    native, scenario, percept, frame = prepare()
    selected = select(frame)
    assert selected.status == "READY"
    with pytest.raises(SkillIRRefusal, match="WorldBody did not attest"):
        compile_initial_skill(
            selected.option,
            capability=PhysicalCapability("set_control", 1, "movement", "DESTINATION", True),
        )


def test_move_goal_is_unresolved_without_target_and_escalates_l1_to_l2():
    _, _, percept, frame = prepare(scenario=configured(targets=()))
    assert percept.exploration_need is True
    assert len(frame.goals) == 1
    assert frame.goals[0].goal_id == "EXPLORE_WORLD"
    assert frame.goals[0].unresolved
    assert frame.options == ()
    escalated = select(frame, skill="ESCALATE_L2")
    assert escalated.status == "ESCALATE_L2"
    assert escalated.option is None


def test_move_goal_is_unresolved_if_worldbody_skill_not_admitted():
    _, _, _, frame = prepare(skills=frozenset())
    assert len(frame.goals) == 1
    assert frame.goals[0].unresolved is True
    assert frame.options == ()
    assert select(frame, skill="ESCALATE_L2").status == "ESCALATE_L2"


def test_no_implicit_exploration_need_or_native_claims_for_configured_target():
    native, config, percept, frame = prepare(need=False)
    assert not percept.exploration_need
    assert not any(t.kind == "DESTINATION" for t in percept.targets)
    assert frame.goals == ()
    assert frame.options == ()
    assert all(t.provenance.source != "mineflayer" for t in percept.targets)
    assert native.session_id == "world-A"
    assert len(config.destinations) == 2


@pytest.mark.parametrize("selected_id,expected_distance", [
    ("waypoint-1", 3.0),
    ("waypoint-2", 5.0),
])
def test_existing_l1_option_resolves_exact_configured_move_target_without_issue(
    selected_id, expected_distance,
):
    native, config, percept, frame = prepare()
    assert len(frame.options) == 2
    assert {x.target_ref for x in frame.options} == {
        move_destination_ref(d.destination_id, d.position, d.provenance)
        for d in config.destinations
    }
    assert all(
        t.provenance.source == "configured-destination"
        for t in percept.targets if t.kind == "DESTINATION"
    )
    decision = select(frame, target=selected_id)
    assert decision.status == "READY"
    bound = resolve_selected_move_target(
        decision, frame=frame, percept=percept,
        current_probe=native, scenario=config,
    )
    assert bound.target_ref == move_destination_ref(
        next(d.destination_id for d in config.destinations if d.destination_id == selected_id),
        next(d.position for d in config.destinations if d.destination_id == selected_id),
        next(d.provenance for d in config.destinations if d.destination_id == selected_id),
    )
    assert bound.horizontal_distance == pytest.approx(expected_distance)
    assert bound.vertical_delta == 0
    assert bound.native_position == native.snapshot.position
    assert bound.destination_provenance.source == "configured-destination"
    assert bound.native_probe_provenance == native.provenance
    assert bound.native_request_id == "move-probe-12"
    assert bound.status == "TARGET_BOUND_NO_PHYSICAL_MOVE_CAPABILITY"
    assert not bound.physical_issued
    assert not bound.reached
    assert not bound.stop_settled_attested
    assert -3.2 <= bound.yaw_rad <= 3.2


@pytest.mark.parametrize("change", [
    "target_missing", "source_changed", "native_seq_advanced", "foreign_session",
    "not_probe", "unviable_body", "expired_target", "other_destination",
    "hijacked_l1_target", "misreported_position", "different_world",
])
def test_move_target_recheck_rejects_stale_retargeted_or_unqualified_claims(change):
    native, config, percept, frame = prepare()
    choice = select(frame)
    if change == "target_missing":
        config = configured(targets=())
    elif change == "source_changed":
        dest = config.destinations[0]
        config = replace(config, destinations=(
            replace(dest, provenance=Provenance("configured-destination", "new-revision")),
            config.destinations[1],
        ))
    elif change == "native_seq_advanced":
        native = replace(native, seq=13)
    elif change == "foreign_session":
        native = replace(native, session_id="other-world")
    elif change == "not_probe":
        native = replace(native, kind="move", request_id=None)
    elif change == "unviable_body":
        native = replace(native, snapshot=replace(native.snapshot, health=0))
    elif change == "expired_target":
        percept = replace(percept, targets=tuple(
            replace(t, live=False) if t.ref.startswith("destination:waypoint-1@") else t
            for t in percept.targets
        ))
    elif change == "other_destination":
        dest = config.destinations[0]
        config = replace(config, destinations=(
            replace(dest, position=MineflayerPosition(4, 64, 0)),
            config.destinations[1],
        ))
        # Geometry is bound to the ref digest even if the provenance
        # revision label itself was not updated.
    elif change == "hijacked_l1_target":
        choice = replace(choice, option=replace(choice.option, target_ref="destination:bogus"))
    elif change == "misreported_position":
        native = replace(native, snapshot=replace(
            native.snapshot, position=MineflayerPosition(9, 64, 0),
        ))
        # Geometry is from native current probe; position changing without
        # changing seq/request/source is not detectable from typed records.
        # This test therefore also requires a new source identity.
        native = replace(native, seq=13)
    elif change == "different_world":
        frame = replace(frame, scope=replace(frame.scope, world_session_id="foreign"))
    with pytest.raises(MoveTargetRefusal):
        resolve_selected_move_target(
            choice, frame=frame, percept=percept, current_probe=native,
            scenario=config,
        )


def test_position_equals_current_is_not_an_executable_move():
    config = configured(targets=("waypoint-1",))
    config = replace(config, destinations=(
        replace(config.destinations[0], position=MineflayerPosition(0, 64, 0)),
    ))
    native, config, percept, frame = prepare(scenario=config)
    choice = select(frame)
    with pytest.raises(MoveTargetRefusal, match="not distinct"):
        resolve_selected_move_target(
            choice, frame=frame, percept=percept, current_probe=native,
            scenario=config,
        )


def test_forged_exploration_signal_and_schema_kind_rejected():
    _, config, percept, _ = prepare()
    with pytest.raises(MinimalCognitionError, match="exploration"):
        replace(percept, exploration_need="yes")
    with pytest.raises(MinimalCognitionError):
        native_schema_percept(
            observation(5), config, self_id="self-A",
            exploration_need="yes",
        )


def test_target_digest_binds_exact_geometry_without_changing_config_id():
    d = configured().destinations[0]
    original = move_destination_ref(d.destination_id, d.position, d.provenance)
    moved = move_destination_ref(
        d.destination_id, MineflayerPosition(3.5, 64, 0), d.provenance,
    )
    from_new_source = move_destination_ref(
        d.destination_id, d.position,
        Provenance("configured-destination", "another-version"),
    )
    assert original != moved and original != from_new_source
    assert original == move_destination_ref(d.destination_id, d.position, d.provenance)


@pytest.mark.parametrize("id_value", [
    "space name", "../up", "", "unicode-日本語", "line\\nbreak",
])
def test_unsafe_move_destination_ids_refused_before_option(id_value):
    from relay_self.move_destination_ref import MoveDestinationRefusal

    with pytest.raises(MoveDestinationRefusal):
        move_destination_ref(
            id_value, MineflayerPosition(3, 64, 0),
            Provenance("configured-destination", "ref-1"),
        )


class ProbeOnlySession:
    """One source-qualified native probe; no motor command methods."""

    def __init__(self, original, *, drop_probe=False):
        self.original = original
        self.sent = []
        self.responses = []
        self.drop_probe = drop_probe

    async def send_observe(self, request_id):
        self.sent.append(("observe", request_id))
        if not self.drop_probe:
            self.responses.append(replace(
                self.original, seq=self.original.seq + 1,
                kind="probe", request_id=request_id,
            ))

    async def receive(self):
        if not self.responses:
            raise RuntimeError("no current native response")
        return self.responses.pop(0)


def choose_move_engine():
    def provider(request, *, mode):
        assert mode is CognitionMode.BOUNDED
        assert any("MOVE@1" in choice.description for choice in request.choices)
        return ProviderDecision.resolved("1")

    return RelayEngine(provider)


def one_turn(*, scenario=None, need=True, physical=False):
    scenario = scenario or configured()
    original = observation(
        12, kind="probe", session_id="world-A", request_id="initial",
        food=20,
    )
    session = ProbeOnlySession(original)
    owner = IntentCommitment()
    supervisor = ActionSupervisor()
    result = asyncio.run(execute_one_cognitive_world_turn(
        session, original, scenario,
        self_id="self-A", intent_id="intent-A",
        registry=initial_patterns_with_move(),
        relay_engine=choose_move_engine(), intent_owner=owner,
        supervisor=supervisor, grant_real_world=True,
        allowed_skills=MOVE_ONLY, exploration_need=need,
        issue_native=physical, acknowledge_unfenced_dev=physical,
    ))
    return result, session, owner, supervisor


def test_one_turn_actual_l1_to_native_move_target_stops_before_motor():
    out, session, owner, supervisor = one_turn()
    assert out.status == "MOVE_TARGET_BOUND_NO_ISSUE"
    assert out.selection.option.skill_id == "MOVE"
    assert out.move_target is not None
    assert out.move_target.native_seq == 13
    assert out.move_target.native_request_id == out.probe_request_id
    assert out.move_target.physical_issued is False
    assert out.move_target.stop_settled_attested is False
    assert out.actual_action_outcomes == 0
    assert len(session.sent) == 1
    assert session.sent[0][0] == "observe"
    assert owner.current_intent is None
    assert supervisor.recorded_actions == ()


def test_one_turn_move_cannot_use_legacy_unfenced_issuer():
    with pytest.raises(MinimalCognitionError, match="no qualified physical MOVE"):
        one_turn(physical=True)


def test_one_turn_without_destination_escapes_to_l2_not_random_walk():
    config = configured(targets=())
    original = observation(
        12, kind="probe", session_id="world-A",
        request_id="initial", food=20,
    )
    session = ProbeOnlySession(original)
    owner = IntentCommitment()
    supervisor = ActionSupervisor()

    def escalate(request, *, mode):
        assert len(request.choices) == 2
        assert request.choices[0].description == "ESCALATE_L2"
        return ProviderDecision.resolved("1")

    receipt = asyncio.run(execute_one_cognitive_world_turn(
        session, original, config,
        self_id="self-A", intent_id="intent-A",
        registry=initial_patterns_with_move(),
        relay_engine=RelayEngine(escalate), intent_owner=owner,
        supervisor=supervisor, grant_real_world=True,
        allowed_skills=MOVE_ONLY, exploration_need=True,
    ))
    assert receipt.status == "ESCALATE_L2"
    assert receipt.initial_frame.goals[0].unresolved
    assert receipt.move_target is None
    assert session.sent == []
    assert owner.current_intent is None
    assert supervisor.recorded_actions == ()
