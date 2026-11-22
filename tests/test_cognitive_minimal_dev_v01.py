"""D1-D8 and L2-pattern Cognitive v0.1 CPU/L1/Owner seam; synthetic DEV only.

WorldBody/ActionPort are NOT exercised; ActionLifecycle remains PROPOSED.
"""
from __future__ import annotations

import json
import threading
from dataclasses import replace

import pytest

from relay_self.action import ActionState
from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    Origin,
    PatternKind,
    Predicate,
    SchemaPattern,
    Target,
    WorldPercept,
    accept_learned_pattern,
    assemble_l1_select,
    cpu_schema_epoch,
    initial_patterns,
    parse_l2_pattern_proposal,
    prepare_existing_owner_action,
    prepare_l2_pattern_request,
    resolve_l1_choice,
)
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    ProviderExpression,
    RelayEngine,
)

SKILLS = frozenset({("EAT", 1), ("ATTACK", 1), ("MOVE", 1), ("REST", 1)})
SCOPE = ScopeRef("self-A", "world-A")


def source(seq: int = 1) -> Provenance:
    return Provenance("gateway", f"native-{seq}")


def target(ref: str, kind: str, *, seq: int = 1, live: bool = True) -> Target:
    return Target(ref, kind, source(seq), "world-A", seq, live)


def percept(
    *,
    hunger: int | None = 10,
    fatigue: bool | None = None,
    targets: tuple[Target, ...] = (),
    seq: int = 1,
) -> WorldPercept:
    return WorldPercept(SCOPE, source(seq), seq, hunger, fatigue, targets)


def frame(p: WorldPercept, *, epoch: int = 1):
    return cpu_schema_epoch(p, initial_patterns(), allowed_skills=SKILLS, epoch=epoch)


def select(choice: str, request):
    calls = []

    def provider(req, *, mode):
        assert mode is CognitionMode.BOUNDED
        calls.append(req)
        return ProviderDecision.resolved(choice)

    out = RelayEngine(provider)(request)
    assert len(calls) == 1
    return out


def find_number(round_, skill: str) -> str:
    return next(n for n, choice in round_.numbered if getattr(choice, "skill_id", None) == skill)


def special(round_, name: str) -> str:
    return next(n for n, choice in round_.numbered if choice == name)


def test_d1_hunger_food_selected_then_original_owner_proposes_not_issues() -> None:
    owner = IntentCommitment()
    f = frame(percept(targets=(target("apple-1", "FOOD"),)))
    assert len(f.goals) == 1 and f.goals[0].goal_id == "HUNGER_RELIEF"
    round_ = assemble_l1_select(f, intent_owner=owner, recent_3self=("MySelf", "SelfWorld", "SelfBody"))
    assert not round_.request.think_allowed
    assert len(round_.request.context) == 1
    decision = resolve_l1_choice(
        round_, select(find_number(round_, "EAT"), round_.request),
        current_frame=f, intent_owner=owner, available_skills=SKILLS,
    )
    assert decision.status == "READY" and decision.option.target_ref == "apple-1"
    prepared = prepare_existing_owner_action(
        decision, intent_owner=owner, intent_id="intent-1", skill_run_id="run-1",
        action_id="action-1", at_ns=20, provenance=source(),
    )
    assert owner.current_intent.intent_id == "intent-1"
    assert prepared.skill.intent_id == "intent-1"
    assert prepared.skill.skill_id == "EAT"
    assert prepared.action.intent_id == "intent-1"
    assert prepared.action.state is ActionState.PROPOSED
    assert prepared.option.target_ref == "apple-1"
    assert prepared.option.skill_version == 1
    assert prepared.world_scope == SCOPE


def test_d2_hunger_and_zombie_both_visible_l1_can_choose_defense() -> None:
    owner = IntentCommitment()
    f = frame(percept(targets=(
        target("apple-1", "FOOD"), target("zombie-7", "ZOMBIE"),
    )))
    assert {g.goal_id for g in f.goals} == {"HUNGER_RELIEF", "DEFEND_SELF"}
    assert f.fast_cues == ("ZOMBIE_NEAR",)
    round_ = assemble_l1_select(f, intent_owner=owner)
    result = resolve_l1_choice(
        round_, select(find_number(round_, "ATTACK"), round_.request),
        current_frame=f, intent_owner=owner, available_skills=SKILLS,
    )
    assert result.status == "READY" and result.option.target_ref == "zombie-7"


def test_d3_unresolved_hunger_without_food_escalates_and_need_remains() -> None:
    owner = IntentCommitment()
    f = frame(percept())
    assert f.goals[0].unresolved and not f.options
    round_ = assemble_l1_select(f, intent_owner=owner)
    chosen = resolve_l1_choice(
        round_, select(special(round_, "ESCALATE_L2"), round_.request),
        current_frame=f, intent_owner=owner, available_skills=SKILLS,
    )
    assert chosen.status == "ESCALATE_L2"
    assert owner.current_intent is None
    assert f.goals[0].goal_id == "HUNGER_RELIEF"


def test_d4_target_despawned_while_l1_inflight_is_rejected_without_owner_mutation() -> None:
    owner = IntentCommitment()
    original = frame(percept(targets=(target("apple-1", "FOOD"),)), epoch=1)
    round_ = assemble_l1_select(original, intent_owner=owner)
    current = frame(percept(seq=2), epoch=2)
    receipt = resolve_l1_choice(
        round_, select(find_number(round_, "EAT"), round_.request),
        current_frame=current, intent_owner=owner, available_skills=SKILLS,
    )
    assert receipt.status == "REJECTED"
    with pytest.raises(MinimalCognitionError):
        prepare_existing_owner_action(
            receipt, intent_owner=owner, intent_id="i", skill_run_id="s",
            action_id="a", at_ns=10, provenance=source(),
        )
    assert owner.events == ()


def test_d5_cpu_schema_and_fast_can_continue_while_gpu_l1_is_blocked() -> None:
    owner = IntentCommitment()
    f = frame(percept(targets=(target("apple-1", "FOOD"),)))
    round_ = assemble_l1_select(f, intent_owner=owner)
    started, released = threading.Event(), threading.Event()
    finished = []

    def blocking_provider(req, *, mode):
        started.set()
        assert released.wait(timeout=5)
        return ProviderDecision.resolved(special(round_, "DEFER"))

    def l1_thread():
        finished.append(RelayEngine(blocking_provider)(round_.request))

    thread = threading.Thread(target=l1_thread)
    thread.start()
    try:
        assert started.wait(timeout=5)
        independently_updated = frame(percept(
            seq=2, targets=(target("zombie-7", "ZOMBIE", seq=2),),
        ), epoch=2)
        assert "ZOMBIE_NEAR" in independently_updated.fast_cues
        assert any(g.goal_id == "DEFEND_SELF" for g in independently_updated.goals)
    finally:
        released.set()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert finished and finished[0].status is DecisionStatus.RESOLVED


def test_d6_goal_less_body_schema_constraint_reaches_l1_current() -> None:
    owner = IntentCommitment()
    f = frame(percept(hunger=20, fatigue=True))
    assert not f.goals and not f.options
    assert [c.sensation for c in f.constraints] == ["FATIGUE_LIMIT"]
    round_ = assemble_l1_select(f, intent_owner=owner)
    assert "FATIGUE_LIMIT" in round_.request.context[0].value_json


def test_d7_unaccepted_invalid_or_unavailable_l2_pattern_never_published() -> None:
    registry = initial_patterns()
    proposal = SchemaPattern("new-hunger", 1, "homeostatic", PatternKind.GOAL,
                             Predicate.HUNGRY, "HUNGER_RELIEF", "EAT", 1, "FOOD",
                             Origin.LEARNED, source())
    with pytest.raises(MinimalCognitionError, match="not Self-accepted"):
        accept_learned_pattern(registry, proposal, accepted_by_self=False,
                               expected_revision=0, allowed_skills=SKILLS)
    with pytest.raises(MinimalCognitionError, match="unavailable"):
        accept_learned_pattern(registry, replace(proposal, skill_id="FLY"),
                               accepted_by_self=True, expected_revision=0,
                               allowed_skills=SKILLS)
    with pytest.raises(MinimalCognitionError, match="unsupported"):
        replace(proposal, predicate="eval('bad')")
    with pytest.raises(MinimalCognitionError, match="stale"):
        accept_learned_pattern(registry, proposal, accepted_by_self=True,
                               expected_revision=1, allowed_skills=SKILLS)
    assert registry.revision == 0 and len(registry.patterns) == 3
    assert len(frame(percept(targets=(target("apple-1", "FOOD"),))).options) == 1


def test_d7_accepted_pattern_reuses_same_cpu_format_without_changing_old_snapshot() -> None:
    old = initial_patterns()
    learned = SchemaPattern("hunger-alt", 1, "homeostatic", PatternKind.GOAL,
                            Predicate.HUNGRY, "HUNGER_RELIEF", "EAT", 1, "FOOD",
                            Origin.LEARNED, source())
    new = accept_learned_pattern(old, learned, accepted_by_self=True,
                                 expected_revision=0, allowed_skills=SKILLS)
    assert len(old.patterns) == 3 and old.revision == 0
    assert len(new.patterns) == 4 and new.revision == 1
    p = percept(targets=(target("apple-1", "FOOD"),))
    assert len(cpu_schema_epoch(p, old, allowed_skills=SKILLS, epoch=1).options) == 1
    assert len(cpu_schema_epoch(p, new, allowed_skills=SKILLS, epoch=1).options) == 2


def test_d8_unrelated_world_update_keeps_selected_dependency_valid() -> None:
    owner = IntentCommitment()
    original = frame(percept(targets=(target("apple-1", "FOOD"),)), epoch=1)
    round_ = assemble_l1_select(original, intent_owner=owner)
    # Other observation changed, but same goal/skill and live target remain.
    updated = frame(percept(seq=2, targets=(target("apple-1", "FOOD", seq=2),),
                            fatigue=True), epoch=2)
    receipt = resolve_l1_choice(
        round_, select(find_number(round_, "EAT"), round_.request),
        current_frame=updated, intent_owner=owner, available_skills=SKILLS,
    )
    assert receipt.status == "READY"
    assert updated.constraints and original.epoch != updated.epoch


def test_negative_busy_owner_defers_new_legacy_single_slot_action() -> None:
    owner = IntentCommitment()
    owner.commit("existing", objective="OTHER_GOAL", at_ns=1, provenance=source())
    f = frame(percept(targets=(target("apple-1", "FOOD"),)))
    round_ = assemble_l1_select(f, intent_owner=owner)
    receipt = resolve_l1_choice(
        round_, select(find_number(round_, "EAT"), round_.request),
        current_frame=f, intent_owner=owner, available_skills=SKILLS,
    )
    assert receipt.status == "DEFER"
    assert owner.current_intent.intent_id == "existing"


def test_negative_unknown_choice_and_lost_skill_and_foreign_session() -> None:
    owner = IntentCommitment()
    f = frame(percept(targets=(target("apple-1", "FOOD"),)))
    round_ = assemble_l1_select(f, intent_owner=owner)
    invalid = RelayEngine(lambda req, *, mode: ProviderDecision.resolved("not-an-option"))(
        round_.request
    )
    assert invalid.status is DecisionStatus.UNRESOLVED
    assert resolve_l1_choice(round_, invalid, current_frame=f, intent_owner=owner,
                             available_skills=SKILLS).status == "RECONSIDER"
    valid = select(find_number(round_, "EAT"), round_.request)
    assert resolve_l1_choice(round_, valid, current_frame=f, intent_owner=owner,
                             available_skills=frozenset()).status == "REJECTED"
    foreign = replace(f, scope=ScopeRef("self-A", "world-B"))
    assert resolve_l1_choice(round_, valid, current_frame=foreign, intent_owner=owner,
                             available_skills=SKILLS).status == "REJECTED"


def test_negative_percept_bounds_reject_foreign_target_and_unknown_hunger_preserved() -> None:
    wrong = replace(target("apple", "FOOD"), world_session_id="world-other")
    with pytest.raises(MinimalCognitionError):
        percept(targets=(wrong,))
    f = frame(percept(hunger=None, fatigue=None))
    assert not f.goals and not f.constraints


def test_d3_l2_open_proposes_only_and_self_must_accept_typed_cpu_pattern() -> None:
    registry = initial_patterns()
    f = frame(percept(hunger=10, targets=()))
    request = prepare_l2_pattern_request(f)
    proposed_json = json.dumps({
        "pattern_id": "l2-hunger-hypothesis-1",
        "version": 1,
        "schema_id": "homeostatic",
        "kind": "GOAL",
        "predicate": "HUNGRY",
        "goal_id": "HUNGER_RELIEF",
        "skill_id": "EAT",
        "skill_version": 1,
        "target_kind": "FOOD",
    })
    calls = []

    def provider(req, *, mode):
        calls.append(mode)
        assert req is request and mode is CognitionMode.OPEN
        return ProviderExpression(proposed_json, source(3))

    expression = RelayEngine(provider).open(request)
    assert calls == [CognitionMode.OPEN]
    proposal = parse_l2_pattern_proposal(
        expression.text, model_provenance=expression.provenance,
    )
    assert proposal.origin is Origin.LEARNED
    assert registry.revision == 0
    with pytest.raises(MinimalCognitionError, match="not Self-accepted"):
        accept_learned_pattern(
            registry, proposal, accepted_by_self=False,
            expected_revision=0, allowed_skills=SKILLS,
        )
    accepted = accept_learned_pattern(
        registry, proposal, accepted_by_self=True,
        expected_revision=0, allowed_skills=SKILLS,
    )
    assert accepted.revision == 1 and registry.revision == 0
    assert len(accepted.patterns) == len(registry.patterns) + 1


def test_l2_invalid_code_and_shape_never_becomes_executable_cpu_pattern() -> None:
    with pytest.raises(MinimalCognitionError, match="not JSON"):
        parse_l2_pattern_proposal(
            "__import__('os').system('echo unsafe')", model_provenance=source(),
        )
    with pytest.raises(MinimalCognitionError, match="fields"):
        parse_l2_pattern_proposal(
            '{"python":"while True: pass"}', model_provenance=source(),
        )
    with pytest.raises(MinimalCognitionError, match="invalid learned"):
        parse_l2_pattern_proposal(json.dumps({
            "pattern_id": "l2-invalid",
            "version": 1,
            "schema_id": "body",
            "kind": "CONSTRAINT",
            "predicate": "exec('while True: pass')",
            "goal_id": None,
            "skill_id": None,
            "skill_version": None,
            "target_kind": None,
        }), model_provenance=source())
    assert len(initial_patterns().patterns) == 3
