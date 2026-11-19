"""D Lane CPU-offline DEV, adversarial A-F + owner/source fences.

No Paper/Gemma, ActionPort calls, checkpoint writes or Memory revisions.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    Origin,
    PatternKind,
    PresetAcceptanceReceipt,
    Target,
    WorldPercept,
    accept_learned_pattern,
    accept_skill_parameter_preset,
    initial_patterns_with_move,
    parse_l2_pattern_proposal,
    resolve_l1_choice,
)
from relay_self.common_io import Clock, ClockStamp, CommonEnvelope, ScopeRef
from relay_self.exploration_goal_dev import (
    ExplorationBasis,
    ExplorationContractError,
    ExplorationDisposition,
    ExplorationEvidence,
    NeedReadout,
    form_exploration_round,
    prepare_exploration_l2,
    propose_exploration_need,
    review_l2_target_reference,
)
from relay_self.exploration_owner_admission_dev import (
    ExplorationOwnerError,
    GoalDisposition,
    GoalReviewPolicy,
    GoalReviewStatus,
    OwnerGoalReadout,
    begin_adopted_exploration_intent,
    review_exploration_goal,
)
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.innate_schema import (
    SchemaActivation,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
    with_schema_mode,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderDecision, RelayEngine
from relay_self.skill_invocation import SkillBudget, SkillConstraints, SkillParameterPreset
from relay_self.three_self_present import (
    EpistemicStatus,
    project_present_frame,
    project_three_self,
)

SOURCE = Provenance("gateway-dev", "native-13")
OWNER = Provenance("self-owner", "read-only")
ALLOWED = frozenset({("MOVE", 1), ("EAT", 1), ("ATTACK", 1)})
DEFINITIONS = {(d.skill_id, d.version): d for d in initial_skill_definitions()}


def envelope(scope, kind, event_id):
    return CommonEnvelope(
        event_id=event_id, kind=kind, scope=scope,
        occurred_at=ClockStamp(Clock.WORLD_TICK, 13),
        received_at=ClockStamp(Clock.HOST_MONOTONIC_NS, 100),
        provenance=SOURCE, source_refs=(SOURCE,),
    )


def setup(self_id="self-A", *, evidence_count=2, pressure=0.0,
          curiosity=1.0, with_target=True, with_preset=True,
          hunger=20, live_intent=False, mode=SchemaMode.FULL):
    scope = ScopeRef(self_id, "world-A")
    question_ref = "question:ridge" if self_id == "self-A" else "question:forest"
    retained = PersistentCognition(
        IdentitySpecification(self_id, ("Curious",), OWNER),
    )
    sources = ("native-13", "present-1")
    projection = project_three_self(
        retained=retained, scope=scope, epoch_ref="epoch-1",
        source_revision_refs=sources,
    )
    spec = SchemaModuleSpec(
        schema_id="exploratory", version=1,
        supported_modes=frozenset({SchemaMode.FULL}),
        signal_kinds=("EXPLORATION_NEED",), dependencies=(), provenance=OWNER,
    )
    snapshot = SchemaSnapshot(self_id, 7, (
        SchemaActivation(spec, mode),
    ))
    present = project_present_frame(
        three_self=projection, snapshot=snapshot,
        current_registry_revision=7,
        current_source_revision_refs=sources, frame_revision=1,
        active_question_refs=(question_ref,),
        attention_refs=("attention:unfamiliar",),
        need_refs=("hunger",),
    )
    evidence = (
        ExplorationEvidence(
            ExplorationBasis.OPEN_QUESTION, question_ref,
            EpistemicStatus.UNKNOWN,
        ),
        ExplorationEvidence(
            ExplorationBasis.NOVELTY, "attention:unfamiliar",
            EpistemicStatus.INFERRED,
        ),
    )[:evidence_count]
    need = propose_exploration_need(
        present=present, snapshot=snapshot, schema_id="exploratory",
        evidence=evidence, other_needs=(NeedReadout("hunger", pressure, 0),),
        disposition=ExplorationDisposition(curiosity=curiosity),
        signal_envelope=envelope(scope, "COGNITIVE_SIGNAL", "signal:explore-1"),
        current_registry_revision=7, current_source_revision_refs=sources,
    )
    if need is not None:
        present = project_present_frame(
            three_self=projection, snapshot=snapshot,
            current_registry_revision=7, current_source_revision_refs=sources,
            frame_revision=2, signals=(need.signal,),
            active_question_refs=(question_ref,),
            attention_refs=("attention:unfamiliar",), need_refs=("hunger",),
        )
    registry = initial_patterns_with_move()
    if with_preset:
        definition = DEFINITIONS[("MOVE", 1)]
        preset = SkillParameterPreset(
            "exploration-move", "DefaultMove", 1,
            definition.definition_ref, SkillConstraints(),
            SkillBudget(2, 2000, max_observations=4),
            Provenance("self-schema-preset", "move-1"),
        )
        registry = accept_skill_parameter_preset(
            registry, preset, definition=definition,
            receipt=PresetAcceptanceReceipt(
                self_id, "accept-preset-1", preset.preset_ref, OWNER,
            ),
            accepted_by_self=True, expected_revision=registry.revision,
            available_skills=ALLOWED,
        )
    target = (Target("destination:ridge", "DESTINATION", SOURCE,
                     "world-A", 13),) if with_target else ()
    percept = WorldPercept(
        scope, SOURCE, 13, hunger=hunger, fatigue_high=False, targets=target,
    )
    intent_owner = IntentCommitment()
    if live_intent:
        intent_owner.commit(
            "intent:ongoing", objective="BUILD_SHELTER", at_ns=5,
            provenance=OWNER,
        )
    return {
        "scope": scope, "retained": retained, "sources": sources,
        "snapshot": snapshot, "present": present, "need": need,
        "registry": registry, "percept": percept, "owner": intent_owner,
    }


def build(c, *, threshold=0.20, owner_revision=4):
    return form_exploration_round(
        present=c["present"], need=c["need"],
        snapshot=c["snapshot"], percept=c["percept"],
        registry=c["registry"], intent_owner=c["owner"],
        owner_revision=owner_revision,
        allowed_skills=ALLOWED, definitions=DEFINITIONS,
        epoch=3, goal_threshold=threshold,
    )


def choose(c, round_, selected):
    choice_id = next(k for k, v in round_.l1.numbered
                     if v == selected or v is selected)
    result = RelayEngine(lambda req, *, mode:
                         ProviderDecision.resolved(choice_id))(round_.l1.request)
    return resolve_l1_choice(
        round_.l1, result, current_frame=round_.frame,
        intent_owner=c["owner"], available_skills=ALLOWED,
    )


def test_a_stable_unknown_world_generates_motivated_goal_and_immutable_l1_option():
    c = setup()
    before_memory = c["retained"].memories
    r = build(c)
    assert c["need"].intensity > 0.2
    assert len(c["need"].basis) == 2
    assert r.proposals[0].route == "KNOWN_PRESET_BOUND"
    assert r.proposals[0].question_refs == ("question:ridge",)
    option = next(x for x in r.frame.options if x.schema_id == "exploration")
    assert option.invocation is not None
    assert option.invocation.target.ref == "destination:ridge"
    assert option.invocation.parameter_preset_ref.startswith("skill-preset:v1@")
    assert choose(c, r, option).status == "READY"
    assert choose(c, r, "DEFER").status == "DEFER"
    assert c["owner"].current_intent is None
    assert c["owner"].events == ()
    assert c["retained"].memories == before_memory


def test_b_no_target_keeps_goal_and_offers_numbered_l2_not_fake_move():
    c = setup(with_target=False)
    r = build(c)
    assert r.proposals[0].goal.unresolved
    assert r.proposals[0].route == "NEEDS_L2"
    assert r.proposals[0].target_refs == ()
    assert r.frame.options == ()
    assert tuple(item for _, item in r.l1.numbered) == ("ESCALATE_L2", "DEFER")
    selected = choose(c, r, "ESCALATE_L2")
    task = prepare_exploration_l2(
        r, selection=selected, current_owner_revision=4,
        attempted_keys=frozenset(),
    )
    assert task is not None
    assert task.question_ref == "question:ridge"
    assert task.request.intent_id is None


def test_b_known_target_but_no_self_accepted_preset_is_not_executable():
    c = setup(with_preset=False)
    r = build(c)
    assert r.proposals[0].route == "NEEDS_L2"
    assert r.frame.options == ()
    assert r.frame.goals[0].unresolved


def test_c_high_hunger_preserves_both_need_and_goal_without_move_gate():
    c = setup(pressure=1.0, hunger=6)
    r = build(c)
    assert c["need"].intensity > 0
    assert c["need"].other_needs == (NeedReadout("hunger", 1.0, 0),)
    assert {g.goal_id for g in r.frame.goals} == {
        "HUNGER_RELIEF", "EXPLORE_WORLD",
    }
    assert any(o.skill_id == "MOVE" for o in r.frame.options)
    assert any(g.goal_id == "HUNGER_RELIEF" for g in r.frame.goals)
    assert c["percept"].hunger == 6
    assert not c["percept"].exploration_need


def test_busy_self_and_existing_intent_are_not_replaced_by_exploration():
    c = setup(live_intent=True)
    events = c["owner"].events
    r = build(c)
    assert r.proposals[0].continuity_hint == "KEEP_CURRENT_INTENT"
    option = next(o for o in r.frame.options if o.schema_id == "exploration")
    assert choose(c, r, option).status == "DEFER"
    assert c["owner"].events == events
    assert c["owner"].current_intent.intent_id == "intent:ongoing"


def test_need_strength_changes_goal_route_without_idleness_or_body_gating():
    vigorous = setup()
    quiet = setup(curiosity=0.1)
    assert vigorous["need"].intensity > quiet["need"].intensity
    assert build(vigorous).proposals
    assert build(quiet).proposals == ()
    assert quiet["need"].signal.signal_kind == "EXPLORATION_NEED"


def test_d_fast_crisis_is_not_blocked_and_no_action_is_emitted():
    c = setup(live_intent=True, hunger=5)
    c["percept"] = replace(c["percept"], threat_cue=True)
    r = build(c)
    assert any(g.goal_id == "DEFEND_SELF" for g in r.frame.goals)
    assert r.proposals[0].continuity_hint == "KEEP_CURRENT_INTENT"
    assert c["owner"].current_intent is not None
    # No nested Action, no lifecycle mutation or physical port in D output.
    assert not hasattr(r, "issue")
    assert not hasattr(r, "world_outcome")
    assert len(c["owner"].events) == 1


def test_e_l2_cancel_timeout_unresolved_retains_question_and_fences_retry():
    c = setup(with_target=False)
    r = build(c)
    selected = choose(c, r, "ESCALATE_L2")
    task = prepare_exploration_l2(
        r, selection=selected, current_owner_revision=4,
        attempted_keys=frozenset(),
    )
    for outcome in ("CANCELLED", "TIMEOUT", "UNRESOLVED"):
        result = review_l2_target_reference(
            task=task, result_status=outcome, result_text=None,
            result_provenance=OWNER, percept=c["percept"],
            current_source_revision_refs=c["sources"],
        )
        assert result.status == outcome
        assert result.question_ref == "question:ridge"
        assert result.target is None
    assert prepare_exploration_l2(
        r, selection=selected, current_owner_revision=4,
        attempted_keys=frozenset({task.attempt_key}),
    ) is None
    assert c["present"].active_question_refs == ("question:ridge",)
    assert c["owner"].events == ()


@pytest.mark.parametrize("invalid", [
    '{"kind":"TARGET_REFERENCE","question_ref":"question:ridge","target_ref":"invented","target_kind":"DESTINATION"}',
    '{"kind":"TARGET_REFERENCE","question_ref":"foreign","target_ref":"destination:ridge","target_kind":"DESTINATION"}',
    '{"kind":"CODE","question_ref":"question:ridge","target_ref":"destination:ridge","target_kind":"DESTINATION"}',
    '{"kind":"TARGET_REFERENCE","question_ref":"question:ridge","target_ref":"destination:ridge","target_kind":"DESTINATION","budget":99999}',
])
def test_l2_target_proposal_cannot_mint_target_or_change_parameters(invalid):
    c = setup(with_target=True, with_preset=False)
    # Deliberately no Preset: the Goal remains unresolved despite known Target.
    r = build(c)
    task = prepare_exploration_l2(
        r, selection=choose(c, r, "ESCALATE_L2"),
        current_owner_revision=4, attempted_keys=frozenset(),
    )
    assert task is not None
    with pytest.raises(ExplorationContractError):
        review_l2_target_reference(
            task=task, result_status="RESOLVED", result_text=invalid,
            result_provenance=OWNER, percept=c["percept"],
            current_source_revision_refs=c["sources"],
        )


def test_l2_only_refs_a_real_current_target_and_does_not_install_anything():
    c = setup(with_preset=False)
    r = build(c)
    task = prepare_exploration_l2(
        r, selection=choose(c, r, "ESCALATE_L2"),
        current_owner_revision=4, attempted_keys=frozenset(),
    )
    obj = {"kind": "TARGET_REFERENCE", "question_ref": task.question_ref,
           "target_ref": "destination:ridge", "target_kind": "DESTINATION"}
    result = review_l2_target_reference(
        task=task, result_status="RESOLVED", result_text=json.dumps(obj),
        result_provenance=OWNER, percept=c["percept"],
        current_source_revision_refs=c["sources"],
    )
    assert result.target is c["percept"].targets[0]
    assert c["registry"].accepted_presets == ()
    with pytest.raises(ExplorationContractError, match="stale"):
        review_l2_target_reference(
            task=task, result_status="RESOLVED", result_text=json.dumps(obj),
            result_provenance=OWNER, percept=c["percept"],
            current_source_revision_refs=("different-revision",),
        )


def test_existing_typed_cpu_pattern_parser_rejects_code_and_unaccepted_install():
    text = json.dumps({
        "pattern_id": "investigate-area", "version": 1,
        "schema_id": "exploration", "kind": "GOAL", "predicate": "EXPLORE",
        "goal_id": "INVESTIGATE_AREA", "skill_id": "MOVE",
        "skill_version": 1, "target_kind": "DESTINATION",
    })
    proposal = parse_l2_pattern_proposal(text, model_provenance=OWNER)
    assert proposal.origin is Origin.LEARNED
    assert proposal.kind is PatternKind.GOAL
    reg = initial_patterns_with_move()
    with pytest.raises(MinimalCognitionError, match="not Self-accepted"):
        accept_learned_pattern(
            reg, proposal, accepted_by_self=False,
            expected_revision=reg.revision, allowed_skills=ALLOWED,
        )
    accepted = accept_learned_pattern(
        reg, proposal, accepted_by_self=True,
        expected_revision=reg.revision, allowed_skills=ALLOWED,
    )
    assert accepted.revision == reg.revision + 1
    assert reg.patterns != accepted.patterns
    assert accepted.accepted_presets == ()
    for invalid in ('{"kind":"EXEC","code":"while True: attack()"}', text[:-1]):
        with pytest.raises(MinimalCognitionError):
            parse_l2_pattern_proposal(invalid, model_provenance=OWNER)


def test_off_switch_and_unknown_do_not_delete_existing_question():
    c = setup()
    off = with_schema_mode(
        c["snapshot"], schema_id="exploratory", mode=SchemaMode.OFF,
    )
    off_present = project_present_frame(
        three_self=c["present"].three_self, snapshot=off,
        current_registry_revision=off.revision,
        current_source_revision_refs=c["sources"], frame_revision=3,
        active_question_refs=("question:ridge",),
    )
    assert propose_exploration_need(
        present=off_present, snapshot=off, schema_id="exploratory",
        evidence=(ExplorationEvidence(
            ExplorationBasis.OPEN_QUESTION, "question:ridge",
            EpistemicStatus.UNKNOWN,
        ),),
        other_needs=(), disposition=ExplorationDisposition(),
        signal_envelope=envelope(c["scope"], "COGNITIVE_SIGNAL", "signal:new"),
        current_registry_revision=off.revision,
        current_source_revision_refs=c["sources"],
    ) is None
    assert off_present.active_question_refs == ("question:ridge",)
    assert c["retained"].memories == ()


def test_foreign_present_evidence_and_revision_do_not_cross_self_scope():
    a = setup("self-A")
    b = setup("self-B", with_preset=False)
    assert build(a).frame.scope.self_id == "self-A"
    assert build(b).frame.scope.self_id == "self-B"
    assert build(b).frame.options == ()
    assert a["present"].active_question_refs != b["present"].active_question_refs
    with pytest.raises(ExplorationContractError):
        form_exploration_round(
            present=a["present"], need=a["need"], snapshot=a["snapshot"],
            percept=b["percept"], registry=a["registry"],
            intent_owner=a["owner"], owner_revision=3,
            allowed_skills=ALLOWED, definitions=DEFINITIONS, epoch=3,
        )
    with pytest.raises(ExplorationContractError, match="evidence"):
        propose_exploration_need(
            present=a["present"], snapshot=a["snapshot"],
            schema_id="exploratory",
            evidence=(ExplorationEvidence(
                ExplorationBasis.NOVELTY, "b:unseen", EpistemicStatus.UNKNOWN,
            ),),
            other_needs=(), disposition=ExplorationDisposition(),
            signal_envelope=envelope(a["scope"], "COGNITIVE_SIGNAL", "new"),
            current_registry_revision=7,
            current_source_revision_refs=a["sources"],
        )


def test_l2_requires_actual_finite_escalation_receipt_and_current_owner():
    c = setup(with_target=False)
    r = build(c)
    from relay_self.cognitive_minimal_dev import Selection
    assert prepare_exploration_l2(
        r, selection=Selection("DEFER", None, "L1 deferred"),
        current_owner_revision=4, attempted_keys=frozenset(),
    ) is None
    with pytest.raises(ExplorationContractError, match="stale"):
        prepare_exploration_l2(
            r, selection=choose(c, r, "ESCALATE_L2"),
            current_owner_revision=5, attempted_keys=frozenset(),
        )


def test_no_evidence_means_no_exploration_signal_or_automatic_goal():
    c = setup(evidence_count=0)
    assert c["need"] is None
    assert c["present"].active_question_refs == ("question:ridge",)
    assert c["owner"].events == ()

def test_unknown_attention_cannot_be_labeled_observed_by_exploration():
    c = setup()
    with pytest.raises(ExplorationContractError, match="only observed"):
        propose_exploration_need(
            present=c["present"], snapshot=c["snapshot"],
            schema_id="exploratory",
            evidence=(ExplorationEvidence(
                ExplorationBasis.NOVELTY, "attention:unfamiliar",
                EpistemicStatus.OBSERVED,
            ),),
            other_needs=(), disposition=ExplorationDisposition(),
            signal_envelope=envelope(
                c["scope"], "COGNITIVE_SIGNAL", "signal:attempted-fact",
            ),
            current_registry_revision=7,
            current_source_revision_refs=c["sources"],
        )


# D2: actual original IntentCommitment owner, no secondary Goal state database.

def owner_goal_view(c, *, incumbent=None, intensity=None, changed=None,
                    revision=4):
    return OwnerGoalReadout(
        scope=c["scope"], revision=revision, incumbent_goal_ref=incumbent,
        incumbent_intensity=intensity, last_goal_transition_ns=changed,
        provenance=OWNER,
    )


def goal_review(c, r, *, directive=GoalDisposition.ADOPT, incumbent=None,
                intensity=None, changed=None, revision=4, now=100,
                policy=None, goal_ref="EXPLORE_WORLD"):
    return review_exploration_goal(
        r, goal_ref=goal_ref, disposition=directive,
        owner=owner_goal_view(
            c, incumbent=incumbent, intensity=intensity,
            changed=changed, revision=revision,
        ),
        intent_owner=c["owner"], policy=policy or GoalReviewPolicy(),
        current_present_revision=c["present"].frame_revision,
        current_schema_revision=c["snapshot"].revision,
        current_source_revision_refs=c["sources"], now_ns=now,
    )


def project_owner_goal(c, goal_refs, *, frame_revision=3):
    c["present"] = project_present_frame(
        three_self=c["present"].three_self, snapshot=c["snapshot"],
        current_registry_revision=c["snapshot"].revision,
        current_source_revision_refs=c["sources"],
        frame_revision=frame_revision,
        signals=(c["need"].signal,),
        active_question_refs=c["present"].active_question_refs,
        active_goal_refs=goal_refs,
        attention_refs=c["present"].attention_refs,
        need_refs=c["present"].need_refs,
    )
    return c


def chosen_l1_result(round_, choice="MOVE"):
    selection = next(
        number for number, option in round_.l1.numbered
        if option == choice or (hasattr(option, "skill_id")
                                and option.skill_id == choice)
    )
    return RelayEngine(
        lambda req, *, mode: ProviderDecision.resolved(selection),
    )(round_.l1.request)


def test_d2_explicit_goal_review_is_proposal_not_intent_commit():
    c = setup()
    r = build(c)
    old = c["owner"].events
    reviewed = goal_review(c, r)
    assert reviewed.status is GoalReviewStatus.ADOPTION_PROPOSED
    assert reviewed.goal_ref == "EXPLORE_WORLD"
    assert reviewed.question_refs == ("question:ridge",)
    assert c["owner"].events == old
    assert c["present"].active_goal_refs == ()
    assert c["retained"].memories == ()


def test_d2_explicit_hold_and_continue_do_not_start_or_end_intent():
    c = setup(live_intent=True)
    r = build(c)
    held = goal_review(c, r, directive=GoalDisposition.HOLD)
    assert held.status is GoalReviewStatus.HELD
    assert held.reason == "OWNER_HELD"
    project_owner_goal(c, ("EXPLORE_WORLD",))
    r = build(c)
    continued = goal_review(
        c, r, directive=GoalDisposition.CONTINUE,
        incumbent="EXPLORE_WORLD", intensity=0.5,
    )
    assert continued.status is GoalReviewStatus.CONTINUED
    assert c["owner"].current_intent.intent_id == "intent:ongoing"
    assert len(c["owner"].events) == 1


def test_d2_busy_different_intent_requires_original_owner_reconsideration():
    c = setup(live_intent=True)
    r = build(c)
    held = goal_review(c, r)
    assert held.reason == "INCUMBENT_INTENT_MUST_BE_RECONSIDERED"
    assert c["owner"].current_intent.objective == "BUILD_SHELTER"
    assert len(c["owner"].events) == 1
    from relay_self.intent import ReconsiderationDecision

    c["owner"].request_reconsideration(
        "intent:ongoing", reason="new goal evaluation",
        at_ns=101, provenance=OWNER,
    )
    c["owner"].reconsider(
        "intent:ongoing", decision=ReconsiderationDecision.RELEASE,
        reason="Self chooses to release incumbent",
        at_ns=102, provenance=OWNER,
    )
    assert c["owner"].current_intent is None
    r = build(c, owner_revision=5)
    assert goal_review(c, r, revision=5, now=103).status is (
        GoalReviewStatus.ADOPTION_PROPOSED
    )


def test_d2_hysteresis_min_duration_holds_even_with_strong_goal():
    c = setup()
    project_owner_goal(c, ("BUILD_SHELTER",))
    r = build(c)
    held = goal_review(
        c, r, incumbent="BUILD_SHELTER", intensity=0.0,
        changed=99, now=100,
        policy=GoalReviewPolicy(min_hold_ns=10, switch_margin=0.0),
    )
    assert held.status is GoalReviewStatus.HELD
    assert held.reason == "GOAL_HYSTERESIS_HOLD"
    assert c["present"].active_goal_refs == ("BUILD_SHELTER",)


def test_d2_small_intensity_delta_does_not_flip_goal_every_epoch():
    c = setup()
    project_owner_goal(c, ("BUILD_SHELTER",))
    r = build(c)
    held = goal_review(
        c, r, incumbent="BUILD_SHELTER", intensity=0.62,
        changed=1, now=100,
        policy=GoalReviewPolicy(min_hold_ns=10, switch_margin=0.10),
    )
    assert held.status is GoalReviewStatus.HELD
    assert held.reason == "GOAL_MARGIN_HOLD"
    admitted = goal_review(
        c, r, incumbent="BUILD_SHELTER", intensity=0.3,
        changed=1, now=100,
        policy=GoalReviewPolicy(min_hold_ns=10, switch_margin=0.10),
    )
    assert admitted.status is GoalReviewStatus.ADOPTION_PROPOSED
    assert c["owner"].events == ()


def test_d2_goal_owner_must_publish_before_start_and_new_l1_must_choose():
    c = setup()
    first = build(c, owner_revision=4)
    admission = goal_review(c, first)
    assert c["owner"].current_intent is None
    with pytest.raises(ExplorationOwnerError, match="owner-published"):
        begin_adopted_exploration_intent(
            admission=admission, refreshed=first,
            l1_result=chosen_l1_result(first), intent_owner=c["owner"],
            intent_id="explore-A", current_owner_revision=4,
            current_source_revision_refs=c["sources"],
            available_skills=ALLOWED, at_ns=120, provenance=OWNER,
        )
    assert c["owner"].events == ()

    project_owner_goal(c, ("EXPLORE_WORLD",))
    refreshed = build(c, owner_revision=5)
    with pytest.raises(ExplorationOwnerError, match="new L1"):
        begin_adopted_exploration_intent(
            admission=admission, refreshed=refreshed,
            l1_result=chosen_l1_result(refreshed, "DEFER"),
            intent_owner=c["owner"], intent_id="explore-A",
            current_owner_revision=5, current_source_revision_refs=c["sources"],
            available_skills=ALLOWED, at_ns=120, provenance=OWNER,
        )
    selected = begin_adopted_exploration_intent(
        admission=admission, refreshed=refreshed,
        l1_result=chosen_l1_result(refreshed), intent_owner=c["owner"],
        intent_id="explore-A", current_owner_revision=5,
        current_source_revision_refs=c["sources"],
        available_skills=ALLOWED, at_ns=120, provenance=OWNER,
    )
    assert selected.intent_id == "explore-A"
    assert selected.objective == "EXPLORE_WORLD"
    assert c["owner"].current_intent == selected
    assert len(c["owner"].events) == 1
    assert c["retained"].memories == ()
    assert not hasattr(selected, "action")
    assert not hasattr(selected, "world_outcome")


def test_d2_no_target_allows_goal_review_but_not_physical_intent_start():
    c = setup(with_target=False)
    admission = goal_review(c, build(c))
    assert admission.status is GoalReviewStatus.ADOPTION_PROPOSED
    project_owner_goal(c, ("EXPLORE_WORLD",))
    r = build(c, owner_revision=5)
    with pytest.raises(ExplorationOwnerError, match="new L1"):
        begin_adopted_exploration_intent(
            admission=admission, refreshed=r,
            l1_result=chosen_l1_result(r, "ESCALATE_L2"),
            intent_owner=c["owner"], intent_id="invented-move",
            current_owner_revision=5, current_source_revision_refs=c["sources"],
            available_skills=ALLOWED, at_ns=120, provenance=OWNER,
        )
    assert c["owner"].events == ()
    assert c["present"].active_question_refs == ("question:ridge",)


def test_d2_stale_original_intent_history_fences_replay_after_release():
    c = setup()
    admission = goal_review(c, build(c))
    project_owner_goal(c, ("EXPLORE_WORLD",))
    r = build(c, owner_revision=5)
    result = chosen_l1_result(r)
    begin_adopted_exploration_intent(
        admission=admission, refreshed=r, l1_result=result,
        intent_owner=c["owner"], intent_id="intent-A",
        current_owner_revision=5, current_source_revision_refs=c["sources"],
        available_skills=ALLOWED, at_ns=110, provenance=OWNER,
    )
    c["owner"].complete(
        "intent-A", reason="closed without physical effect",
        at_ns=111, provenance=OWNER,
    )
    with pytest.raises(ExplorationOwnerError, match="owner"):
        begin_adopted_exploration_intent(
            admission=admission, refreshed=r, l1_result=result,
            intent_owner=c["owner"], intent_id="replayed-B",
            current_owner_revision=5, current_source_revision_refs=c["sources"],
            available_skills=ALLOWED, at_ns=112, provenance=OWNER,
        )
    assert c["owner"].current_intent is None


def test_d2_foreign_self_and_stale_revision_cannot_adopt_goal():
    a = setup("self-A")
    b = setup("self-B")
    ra = build(a)
    with pytest.raises(ExplorationOwnerError, match="stale/foreign"):
        review_exploration_goal(
            ra, goal_ref="EXPLORE_WORLD",
            disposition=GoalDisposition.ADOPT,
            owner=owner_goal_view(b), intent_owner=a["owner"],
            policy=GoalReviewPolicy(),
            current_present_revision=a["present"].frame_revision,
            current_schema_revision=7,
            current_source_revision_refs=a["sources"],
            now_ns=100,
        )
    with pytest.raises(ExplorationOwnerError, match="stale/foreign"):
        goal_review(a, ra, revision=5)
    with pytest.raises(ExplorationOwnerError, match="stale/foreign"):
        review_exploration_goal(
            ra, goal_ref="EXPLORE_WORLD",
            disposition=GoalDisposition.ADOPT,
            owner=owner_goal_view(a), intent_owner=a["owner"],
            policy=GoalReviewPolicy(),
            current_present_revision=a["present"].frame_revision + 1,
            current_schema_revision=7,
            current_source_revision_refs=a["sources"],
            now_ns=100,
        )


def test_d2_original_owner_revision_and_question_cannot_be_skipped():
    c = setup()
    admission = goal_review(c, build(c))
    project_owner_goal(c, ("EXPLORE_WORLD",))
    r = build(c, owner_revision=6)
    with pytest.raises(ExplorationOwnerError, match="owner"):
        begin_adopted_exploration_intent(
            admission=admission, refreshed=r,
            l1_result=chosen_l1_result(r),
            intent_owner=c["owner"], intent_id="wrong-revision",
            current_owner_revision=6, current_source_revision_refs=c["sources"],
            available_skills=ALLOWED, at_ns=120, provenance=OWNER,
        )
    c["present"] = project_present_frame(
        three_self=c["present"].three_self, snapshot=c["snapshot"],
        current_registry_revision=7,
        current_source_revision_refs=c["sources"], frame_revision=4,
        signals=(c["need"].signal,),
        active_goal_refs=("EXPLORE_WORLD",),
        active_question_refs=("different-question",),
    )
    r = build(c, owner_revision=5)
    with pytest.raises(ExplorationOwnerError, match="owner"):
        begin_adopted_exploration_intent(
            admission=admission, refreshed=r,
            l1_result=chosen_l1_result(r),
            intent_owner=c["owner"], intent_id="wrong-question",
            current_owner_revision=5, current_source_revision_refs=c["sources"],
            available_skills=ALLOWED, at_ns=120, provenance=OWNER,
        )
    assert c["owner"].events == ()


@pytest.mark.parametrize("incumbent,changed,policy,reason", [
    (None, 1, GoalReviewPolicy(min_hold_ns=0, switch_margin=0.1),
     "INCUMBENT_STRENGTH_UNKNOWN"),
    (0.1, None, GoalReviewPolicy(min_hold_ns=10, switch_margin=0.1),
     "GOAL_TENURE_UNKNOWN"),
])
def test_d2_unknown_owner_goal_strength_or_tenure_never_means_zero(
    incumbent, changed, policy, reason,
):
    c = setup()
    project_owner_goal(c, ("BUILD_SHELTER",))
    r = build(c)
    review = goal_review(
        c, r, incumbent="BUILD_SHELTER", intensity=incumbent,
        changed=changed, policy=policy,
    )
    assert review.status is GoalReviewStatus.HELD
    assert review.reason == reason
    assert c["owner"].events == ()
