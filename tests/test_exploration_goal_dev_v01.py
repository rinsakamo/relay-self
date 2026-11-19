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
from relay_self.exploration_checkpoint_bridge_dev import (
    D4OwnerHold,
    ResidentD4Scope,
    inspect_d4_inert_recovery,
    record_resident_l2_result,
    reserve_resident_l2,
    retain_resident_question,
)
from relay_self.exploration_continuity_dev import (
    AttemptPhase,
    ExplorationContinuity,
    ExplorationContinuityError,
    L2Reservation,
    QuestionRecord,
    decode_exploration_continuity,
    encode_exploration_continuity,
    open_question_refs,
    record_l2_attempt_result,
    reserve_exploration_l2,
    retain_open_question,
    validate_persisted_l2_reservation,
)
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
from relay_self.persistent_cognition import (
    IdentitySpecification,
    InvalidPersistentCognitionData,
    PersistentCognition,
    UnsupportedPersistentCognitionVersion,
    load_persistent_cognition,
    save_persistent_cognition,
)
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


# D3: the same owner cognition path is the only persistence, including Stage28
# generation copies. No L2/GPU call, no WorldBody Action and no restored Target.


def d3_question(c):
    changed = retain_open_question(
        c["retained"], question_ref=c["present"].active_question_refs[0],
        origin=OWNER, expected_revision=0,
        current_present_question_refs=c["present"].active_question_refs,
    )
    c["retained"] = changed
    return changed


def d3_reserved(c, *, owner_revision=4, native_session_ref="native-A"):
    r = build(c, owner_revision=owner_revision)
    selection = choose(c, r, "ESCALATE_L2")
    return reserve_exploration_l2(
        c["retained"], round_=r, selection=selection,
        expected_revision=c["retained"].exploration_continuity.revision,
        current_intent_owner_revision=owner_revision,
        native_session_ref=native_session_ref, owner_provenance=OWNER,
    )


def test_d3_legacy_cognition_v3_unchanged_and_question_explicitly_owned(tmp_path):
    c = setup(with_target=False)
    path = tmp_path / "self-A.json"
    save_persistent_cognition(path, c["retained"])
    import json
    legacy = json.loads(path.read_text())
    assert legacy["schema_version"] == 3
    assert "exploration_continuity" not in legacy
    assert open_question_refs(load_persistent_cognition(path), expected_self_id="self-A") == ()
    d3_question(c)
    assert c["retained"].exploration_continuity.revision == 1
    assert c["retained"].memories == ()
    assert c["retained"].exploration_continuity.questions[0].question_ref == "question:ridge"
    assert c["present"].active_question_refs == ("question:ridge",)
    save_persistent_cognition(path, c["retained"])
    obj = json.loads(path.read_text())
    assert obj["schema_version"] == 4
    assert set(obj) == {"schema_version", "identity", "memories",
                        "appraisal_dispositions", "pattern_registry",
                        "exploration_continuity"}
    assert load_persistent_cognition(path) == c["retained"]


def test_d3_original_owner_cas_and_present_question_checks():
    c = setup(with_target=False)
    with pytest.raises(ExplorationContinuityError, match="stale/unprojected"):
        retain_open_question(
            c["retained"], question_ref="invented", origin=OWNER,
            expected_revision=0,
            current_present_question_refs=c["present"].active_question_refs,
        )
    d3_question(c)
    with pytest.raises(ExplorationContinuityError, match="already registered"):
        retain_open_question(
            c["retained"], question_ref="question:ridge", origin=OWNER,
            expected_revision=1,
            current_present_question_refs=c["present"].active_question_refs,
        )
    with pytest.raises(ExplorationContinuityError, match="stale/unprojected"):
        retain_open_question(
            c["retained"], question_ref="other", origin=OWNER,
            expected_revision=0,
            current_present_question_refs=("other",),
        )
    with pytest.raises(InvalidPersistentCognitionData, match="owner revision"):
        c["retained"].retain_exploration_continuity(
            ExplorationContinuity("self-A", 1), expected_revision=1,
        )
    with pytest.raises(InvalidPersistentCognitionData, match="foreign"):
        c["retained"].retain_exploration_continuity(
            ExplorationContinuity("self-B", 2), expected_revision=1,
        )


def test_d3_reservation_is_inert_until_original_file_saved_and_read_back(tmp_path):
    c = setup(with_target=False)
    d3_question(c)
    path = tmp_path / "original-cognition.json"
    save_persistent_cognition(path, c["retained"])
    new, reservation = d3_reserved(c)
    assert isinstance(reservation, L2Reservation)
    assert new.exploration_continuity.revision == 2
    assert new.exploration_continuity.attempts[0].phase is AttemptPhase.RESERVED
    assert new.memories == ()
    assert c["owner"].events == ()
    with pytest.raises(ExplorationContinuityError, match="not durably committed"):
        validate_persisted_l2_reservation(
            path, reservation=reservation, current_scope=c["scope"],
            current_native_session_ref="native-A", current_intent_owner_revision=4,
            current_source_revision_refs=c["sources"],
        )
    # The EXISTING original cognition writer, not D, commits the whole snapshot.
    save_persistent_cognition(path, new)
    request = validate_persisted_l2_reservation(
        path, reservation=reservation, current_scope=c["scope"],
        current_native_session_ref="native-A", current_intent_owner_revision=4,
        current_source_revision_refs=c["sources"],
    )
    assert request is reservation.task.request
    assert request.focus == "EXPLORATION_TARGET_DISCOVERY"
    assert request.intent_id is None
    assert c["owner"].events == ()


def test_d3_crash_after_reserved_rejoin_never_auto_retries_same_evidence(tmp_path):
    c = setup(with_target=False)
    d3_question(c)
    new, reservation = d3_reserved(c)
    path = tmp_path / "owner.json"
    save_persistent_cognition(path, new)
    c["retained"] = load_persistent_cognition(path)
    assert open_question_refs(c["retained"], expected_self_id="self-A") == ("question:ridge",)
    r = build(c, owner_revision=5)
    selection = choose(c, r, "ESCALATE_L2")
    same, second = reserve_exploration_l2(
        c["retained"], round_=r, selection=selection,
        expected_revision=2, current_intent_owner_revision=5,
        native_session_ref="native-REJOIN", owner_provenance=OWNER,
    )
    assert same is c["retained"] and second is None
    assert c["retained"].exploration_continuity.attempts[0].phase is AttemptPhase.RESERVED
    with pytest.raises(ExplorationContinuityError, match="stale L2 session"):
        validate_persisted_l2_reservation(
            path, reservation=reservation, current_scope=c["scope"],
            current_native_session_ref="native-REJOIN",
            current_intent_owner_revision=5,
            current_source_revision_refs=c["sources"],
        )
    assert not hasattr(c["retained"].exploration_continuity, "worldbody_position")
    assert not hasattr(c["retained"].exploration_continuity, "action_issue_grant")


@pytest.mark.parametrize("outcome", [
    AttemptPhase.CANCELLED, AttemptPhase.TIMEOUT, AttemptPhase.UNRESOLVED,
])
def test_d3_cancel_timeout_unresolved_preserves_question_without_duplicate(outcome):
    c = setup(with_target=False)
    d3_question(c)
    updated, reservation = d3_reserved(c)
    c["retained"] = record_l2_attempt_result(
        updated, reservation=reservation,
        phase=outcome, expected_revision=2,
    )
    assert c["retained"].exploration_continuity.revision == 3
    assert open_question_refs(c["retained"], expected_self_id="self-A") == ("question:ridge",)
    repeated, task = d3_reserved(c, owner_revision=23, native_session_ref="new-native")
    assert repeated is c["retained"] and task is None
    with pytest.raises(ExplorationContinuityError, match="duplicate"):
        record_l2_attempt_result(
            c["retained"], reservation=reservation,
            phase=outcome, expected_revision=3,
        )


def test_d3_evidence_change_not_owner_revision_can_enable_one_new_attempt():
    c = setup(with_target=False)
    d3_question(c)
    c["retained"], first = d3_reserved(c)
    assert d3_reserved(c, owner_revision=5)[1] is None
    original_basis = c["need"].basis
    c["need"] = replace(c["need"], basis=original_basis + (
        ExplorationEvidence(
            ExplorationBasis.PREDICTION_MISMATCH,
            "attention:unexpected-outcome",
            EpistemicStatus.INFERRED,
        ),
    ))
    changed, second = d3_reserved(c, owner_revision=6, native_session_ref="new-native")
    assert second is not None
    assert first.attempt_ref != second.attempt_ref
    assert len(changed.exploration_continuity.attempts) == 2
    c["retained"] = changed
    assert d3_reserved(c, owner_revision=7)[1] is None
    assert c["owner"].events == ()


def test_d3_two_self_question_and_attempt_records_stay_separate(tmp_path):
    a = setup("self-A", with_target=False)
    b = setup("self-B", with_target=False)
    d3_question(a)
    d3_question(b)
    a["retained"], ar = d3_reserved(a)
    b["retained"], br = d3_reserved(b)
    assert ar.attempt_ref != br.attempt_ref
    assert open_question_refs(b["retained"], expected_self_id="self-B") == (
        "question:forest",
    )
    with pytest.raises(ExplorationContinuityError, match="foreign restored Self"):
        open_question_refs(a["retained"], expected_self_id="self-B")
    apath = tmp_path / "A.json"
    save_persistent_cognition(apath, a["retained"])
    with pytest.raises(ExplorationContinuityError, match="not durably committed"):
        validate_persisted_l2_reservation(
            apath, reservation=br, current_scope=b["scope"],
            current_native_session_ref="native-A",
            current_intent_owner_revision=4,
            current_source_revision_refs=b["sources"],
        )


@pytest.mark.parametrize("mutate", [
    lambda p: p["exploration_continuity"].update(self_id="self-foreign"),
    lambda p: p["exploration_continuity"]["attempts"][0].update(
        evidence_digest="not-a-digest"),
    lambda p: p["exploration_continuity"]["attempts"][0].update(
        attempt_ref="forged"),
    lambda p: p["exploration_continuity"]["attempts"].append(
        dict(p["exploration_continuity"]["attempts"][0])),
    lambda p: p["exploration_continuity"].update(extra_field="silent"),
    lambda p: p["exploration_continuity"].update(schema_version=999),
    lambda p: p["exploration_continuity"].update(questions=[]),
    lambda p: p.update(schema_version=5),
])
def test_d3_checkpoint_malformed_or_forged_attempt_fails_closed(tmp_path, mutate):
    c = setup(with_target=False)
    d3_question(c)
    new, _ = d3_reserved(c)
    path = tmp_path / "corrupt.json"
    save_persistent_cognition(path, new)
    import json
    payload = json.loads(path.read_text())
    mutate(payload)
    path.write_text(json.dumps(payload))
    error = (UnsupportedPersistentCognitionVersion
             if payload["schema_version"] == 5
             else InvalidPersistentCognitionData)
    with pytest.raises(error):
        load_persistent_cognition(path)


def test_d3_question_history_has_no_native_target_or_l2_output_replay(tmp_path):
    c = setup(with_target=False)
    d3_question(c)
    updated, reservation = d3_reserved(c)
    path = tmp_path / "owner.json"
    save_persistent_cognition(path, updated)
    recovered = load_persistent_cognition(path)
    assert recovered.exploration_continuity.attempts[0].phase is AttemptPhase.RESERVED
    assert recovered.exploration_continuity.questions[0].open is True
    assert recovered.memories == ()
    assert open_question_refs(recovered, expected_self_id="self-A") == ("question:ridge",)
    assert "observed" not in str(encode_exploration_continuity(
        recovered.exploration_continuity,
    )).lower()
    with pytest.raises(ExplorationContinuityError, match="stale L2 session"):
        validate_persisted_l2_reservation(
            path, reservation=reservation, current_scope=ScopeRef("self-A", "fork"),
            current_native_session_ref="native-A",
            current_intent_owner_revision=4,
            current_source_revision_refs=c["sources"],
        )


def test_d3_schema_codec_exact_fields_and_readonly_decoding():
    q = QuestionRecord("question:small", OWNER)
    state = ExplorationContinuity("self-A", 1, (q,), ())
    obj = encode_exploration_continuity(state)
    assert decode_exploration_continuity(obj, expected_self_id="self-A") == state
    obj["questions"][0]["origin"]["reference"] = "owner-mutated"
    assert state.questions[0].origin == OWNER
    with pytest.raises(ExplorationContinuityError, match="foreign"):
        decode_exploration_continuity(obj, expected_self_id="self-B")


def test_d3_positive_l2_target_audit_rechecks_current_world_and_does_not_close_question():
    c = setup(with_target=False)
    d3_question(c)
    updated, reservation = d3_reserved(c)
    actual = Target("destination:ridge", "DESTINATION", SOURCE, "world-A", 13)
    live = replace(c["percept"], targets=(actual,))
    typed = review_l2_target_reference(
        task=reservation.task,
        result_status="RESOLVED",
        result_text=json.dumps({
            "kind": "TARGET_REFERENCE",
            "question_ref": "question:ridge",
            "target_ref": "destination:ridge",
            "target_kind": "DESTINATION",
        }),
        result_provenance=OWNER, percept=live,
        current_source_revision_refs=c["sources"],
    )
    assert typed.target == actual
    with pytest.raises(ExplorationContinuityError, match="current World review"):
        record_l2_attempt_result(
            updated, reservation=reservation,
            phase=AttemptPhase.REFERENCED_OBSERVED_TARGET,
            reviewed_target=typed, expected_revision=2,
        )
    with pytest.raises(ExplorationContinuityError, match="current World review"):
        record_l2_attempt_result(
            updated, reservation=reservation,
            phase=AttemptPhase.REFERENCED_OBSERVED_TARGET,
            reviewed_target=typed, current_percept=replace(live, targets=()),
            current_source_revision_refs=c["sources"], expected_revision=2,
        )
    with pytest.raises(ExplorationContinuityError, match="current World review"):
        record_l2_attempt_result(
            updated, reservation=reservation,
            phase=AttemptPhase.REFERENCED_OBSERVED_TARGET,
            reviewed_target=typed, current_percept=live,
            current_source_revision_refs=("later-source",), expected_revision=2,
        )
    accepted = record_l2_attempt_result(
        updated, reservation=reservation,
        phase=AttemptPhase.REFERENCED_OBSERVED_TARGET,
        reviewed_target=typed, current_percept=live,
        current_source_revision_refs=c["sources"], expected_revision=2,
    )
    assert accepted.exploration_continuity.attempts[0].phase is (
        AttemptPhase.REFERENCED_OBSERVED_TARGET
    )
    assert open_question_refs(accepted, expected_self_id="self-A") == (
        "question:ridge",
    )
    assert c["owner"].events == ()


# D4 local Stage28-compatible contract harness. These fake classes mirror the
# documented B-Lane shape but DO NOT attest the unmerged real B resident/runtime.
# In an actual merged tree the D4 adapter requires the REAL B classes.

def d4_owner_harness(c, tmp_path, monkeypatch):
    import sys
    import threading
    import types
    from types import SimpleNamespace

    class Stage28OriginalCognitiveOwner:
        def __init__(self, cognition, parent):
            self.retained = cognition
            self.intent = c["owner"]
            self.pending_questions = set()
            self.files = SimpleNamespace(
                self_root=parent, cognition_file=parent / "cognition.json",
            )
            self.native_session_id = "native-D4"
            self.current_worldbody_observation = object()
            self.fresh_native_observation_required = False
            self.cohort = None

        @property
        def self_id(self):
            return self.retained.identity.self_id

        def _eligible(self):
            if self.cohort is None:
                raise RuntimeError("no original owner")
            self.cohort._mutating(self.self_id)
            if self.fresh_native_observation_required:
                raise RuntimeError("fresh native observation absent")

    class Stage28OriginalResidentWorkOwner:
        def __init__(self, owner):
            self.lock = threading.RLock()
            self.owners = {owner.self_id: owner}
            self.mode = "ONLINE"
            self.epoch = 1
            self.native = owner.native_session_id
            self.world_epoch = 2
            owner.cohort = self

        def _mutating(self, self_id):
            if self.mode != "ONLINE" or self_id not in self.owners:
                raise RuntimeError("original resident not online")

        def current_scope(self, self_id):
            self._mutating(self_id)
            return self.epoch, self.native, self.world_epoch

        def fence_self(self, self_id):
            if self_id not in self.owners:
                raise RuntimeError("foreign Self")
            self.mode = "QUARANTINED"
            self.epoch += 1

    modules = (
        ("relay_self.checkpointed_cognitive_runtime_dev",
         "CheckpointedCognitiveOwner", Stage28OriginalCognitiveOwner),
        ("relay_self.resident_cognitive_work_owner_dev",
         "ResidentCognitiveWorkOwner", Stage28OriginalResidentWorkOwner),
    )
    for module_name, attr, obj in modules:
        module = types.ModuleType(module_name)
        setattr(module, attr, obj)
        monkeypatch.setitem(sys.modules, module_name, module)
    root = tmp_path / c["scope"].self_id
    root.mkdir()
    owner = Stage28OriginalCognitiveOwner(c["retained"], root)
    save_persistent_cognition(owner.files.cognition_file, owner.retained)
    resident = Stage28OriginalResidentWorkOwner(owner)
    scope = ResidentD4Scope(
        owner.self_id, c["scope"].world_session_id, 1, "native-D4", 2,
        len(owner.intent.events), owner.intent.last_at_ns,
    )
    return owner, resident, scope


def test_d4_resident_original_owner_mutations_are_one_atomic_path(tmp_path, monkeypatch):
    c = setup(with_target=False)
    owner, resident, lease = d4_owner_harness(c, tmp_path, monkeypatch)
    original = owner.retained
    retain_resident_question(
        owner, resident, scope=lease, present=c["present"],
        question_ref="question:ridge", owner_provenance=OWNER,
    )
    assert owner.retained != original
    assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
    assert owner.pending_questions == {"question:ridge"}
    assert owner.retained.exploration_continuity.revision == 1

    r = build(c)
    selection = choose(c, r, "ESCALATE_L2")
    task = reserve_resident_l2(
        owner, resident, scope=lease, round_=r,
        selection=selection, owner_provenance=OWNER,
    )
    assert task is not None
    assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
    assert len(owner.retained.exploration_continuity.attempts) == 1
    again = reserve_resident_l2(
        owner, resident, scope=lease, round_=r,
        selection=selection, owner_provenance=OWNER,
    )
    assert again is None
    assert owner.retained.exploration_continuity.revision == 2
    record_resident_l2_result(
        owner, resident, scope=lease, reservation=task,
        phase=AttemptPhase.TIMEOUT,
        current_source_revision_refs=c["sources"],
    )
    assert owner.retained.exploration_continuity.attempts[0].phase is (
        AttemptPhase.TIMEOUT
    )
    assert owner.pending_questions == {"question:ridge"}
    assert c["owner"].events == ()
    assert resident.mode == "ONLINE"


def test_d4_quarantined_or_rebound_resident_does_not_mutate(tmp_path, monkeypatch):
    c = setup(with_target=False)
    owner, resident, lease = d4_owner_harness(c, tmp_path, monkeypatch)
    before = owner.retained
    resident.fence_self(owner.self_id)
    with pytest.raises(D4OwnerHold, match="not currently admitted"):
        retain_resident_question(
            owner, resident, scope=lease, present=c["present"],
            question_ref="question:ridge", owner_provenance=OWNER,
        )
    assert owner.retained == before
    assert load_persistent_cognition(owner.files.cognition_file) == before


def test_d4_wrong_owner_native_epoch_and_unobserved_body_hold(tmp_path, monkeypatch):
    c = setup(with_target=False)
    owner, resident, lease = d4_owner_harness(c, tmp_path, monkeypatch)
    wrong = replace(lease, cognition_epoch=lease.cognition_epoch + 1)
    with pytest.raises(D4OwnerHold, match="(stale|not currently admitted)"):
        retain_resident_question(
            owner, resident, scope=wrong, present=c["present"],
            question_ref="question:ridge", owner_provenance=OWNER,
        )
    with pytest.raises(D4OwnerHold, match="foreign/unprojected"):
        retain_resident_question(
            owner, resident, scope=replace(lease, world_session_id="world-fork"),
            present=c["present"], question_ref="question:ridge",
            owner_provenance=OWNER,
        )
    owner.current_worldbody_observation = None
    with pytest.raises(D4OwnerHold, match="(stale|not currently admitted)"):
        retain_resident_question(
            owner, resident, scope=lease, present=c["present"],
            question_ref="question:ridge", owner_provenance=OWNER,
        )
    assert owner.pending_questions == set()


def test_d4_original_disk_mismatch_fences_resident_without_overwrite(
    tmp_path, monkeypatch,
):
    c = setup(with_target=False)
    owner, resident, lease = d4_owner_harness(c, tmp_path, monkeypatch)
    from relay_self.persistent_cognition import Memory
    divergent = owner.retained.retain_memory(
        Memory("foreign-entry", "unadopted", OWNER, OWNER),
    )
    save_persistent_cognition(owner.files.cognition_file, divergent)
    with pytest.raises(D4OwnerHold, match="disk/current owner disagreement"):
        retain_resident_question(
            owner, resident, scope=lease, present=c["present"],
            question_ref="question:ridge", owner_provenance=OWNER,
        )
    assert resident.mode == "QUARANTINED"
    assert owner.retained != divergent
    assert load_persistent_cognition(owner.files.cognition_file) == divergent


def test_d4_cognition_write_failure_quarantines_original_owner(
    tmp_path, monkeypatch,
):
    c = setup(with_target=False)
    owner, resident, lease = d4_owner_harness(c, tmp_path, monkeypatch)
    before = owner.retained
    def fail_save(path, cognition):
        raise OSError("simulated disk full")
    monkeypatch.setattr(
        "relay_self.exploration_checkpoint_bridge_dev.save_persistent_cognition",
        fail_save,
    )
    with pytest.raises(OSError, match="disk full"):
        retain_resident_question(
            owner, resident, scope=lease, present=c["present"],
            question_ref="question:ridge", owner_provenance=OWNER,
        )
    assert owner.retained == before
    assert owner.pending_questions == set()
    assert resident.mode == "QUARANTINED"
    assert load_persistent_cognition(owner.files.cognition_file) == before


def test_d4_l2_completion_after_native_fork_rejected(tmp_path, monkeypatch):
    c = setup(with_target=False)
    owner, resident, lease = d4_owner_harness(c, tmp_path, monkeypatch)
    retain_resident_question(
        owner, resident, scope=lease, present=c["present"],
        question_ref="question:ridge", owner_provenance=OWNER,
    )
    r = build(c)
    task = reserve_resident_l2(
        owner, resident, scope=lease, round_=r,
        selection=choose(c, r, "ESCALATE_L2"), owner_provenance=OWNER,
    )
    assert task is not None
    retained = owner.retained
    resident.fence_self(owner.self_id)
    resident.mode = "ONLINE"
    resident.native = "native-NEW"
    resident.epoch += 1
    owner.native_session_id = "native-NEW"
    next_scope = replace(
        lease, native_session_id="native-NEW", cognition_epoch=resident.epoch,
    )
    with pytest.raises(D4OwnerHold, match="stale/foreign"):
        record_resident_l2_result(
            owner, resident, scope=next_scope, reservation=task,
            phase=AttemptPhase.UNRESOLVED,
            current_source_revision_refs=c["sources"],
        )
    assert owner.retained == retained
    assert owner.retained.exploration_continuity.attempts[0].phase is (
        AttemptPhase.RESERVED
    )


def test_d4_checkpoint_requires_actual_stage28_not_an_untyped_manifest(
    tmp_path, monkeypatch,
):
    import sys
    # No Stage28 implementation on D/#917 stack: never silently downgrade to
    # owner-state-only verification or the same timestamp without World/WAL.
    monkeypatch.delitem(
        sys.modules, "relay_self.stage28_cognitive_recovery_gate_dev",
        raising=False,
    )
    with pytest.raises(D4OwnerHold, match="real Stage28 typed recovery"):
        inspect_d4_inert_recovery(
            tmp_path, tmp_path,
            expected_self_ids=("self-A", "self-B"),
            expected_source_world_id="world-A",
            expected_committed_sha256="0" * 64,
        )


def test_d4_stub_stage28_plan_requires_same_commit_roster_and_pending_refs(
    tmp_path, monkeypatch,
):
    """Contract simulation of B's exact StagedRecoveredCognition fields only."""
    import hashlib
    import sys
    import types
    from types import SimpleNamespace
    a = setup("self-A", with_target=False)
    b = setup("self-B", with_target=False)
    d3_question(a)
    d3_question(b)
    a["retained"], _ = d3_reserved(a)
    b["retained"], _ = d3_reserved(b)
    marker = tmp_path / "COMMITTED.json"
    marker.write_bytes(b'{"generation_id":"g-000000000001"}')
    digest = hashlib.sha256(marker.read_bytes()).hexdigest()

    def staged(c, pending):
        sid = c["scope"].self_id
        cut = SimpleNamespace(
            self_id=sid, generation_id=tmp_path.name,
            world_id="world-A", branch_id="branch-SOURCE",
            former_native_session_id="native-old-" + sid,
            pending_question_refs=pending,
        )
        return SimpleNamespace(
            self_id=sid, retained=c["retained"],
            semantic=SimpleNamespace(cut=cut),
            native_session_bound=False,
            issue_authorized=False,
            fresh_worldbody_required=True,
        )
    plan = SimpleNamespace(
        generation_id=tmp_path.name,
        source_world_id="world-A", source_branch_id="branch-SOURCE",
        fork_branch_id="branch-FORK",
        roster=("self-A", "self-B"),
        candidates=(staged(a, ("question:ridge",)),
                    staged(b, ("question:forest",))),
        source_committed_sha256=digest,
        physical_action_issue_authorized=False,
        old_l1_decision_reusable=False,
        old_skill_resume_authorized=False,
        l1_reevaluation_eligible=False,
    )
    module = types.ModuleType("relay_self.stage28_cognitive_recovery_gate_dev")
    module.stage28_inert_cognitive_recovery = lambda *args, **kwargs: plan
    monkeypatch.setitem(sys.modules, module.__name__, module)
    result = inspect_d4_inert_recovery(
        tmp_path, tmp_path,
        expected_self_ids=("self-A", "self-B"),
        expected_source_world_id="world-A",
        expected_committed_sha256=digest,
    )
    assert result.generation_id == tmp_path.name
    assert result.l2_dispatch_authorized is False
    assert result.physical_action_issue_authorized is False
    assert result.current_native_session_attested is False
    assert result.restored[0].question_refs == ("question:ridge",)
    assert result.restored[1].question_refs == ("question:forest",)
    assert len(result.restored[0].attempt_refs) == 1
    plan.candidates = (staged(a, ()), staged(b, ("question:forest",)))
    with pytest.raises(D4OwnerHold, match="open D Question absent"):
        inspect_d4_inert_recovery(
            tmp_path, tmp_path,
            expected_self_ids=("self-A", "self-B"),
            expected_source_world_id="world-A",
            expected_committed_sha256=digest,
        )
    plan.candidates = (staged(a, ("question:ridge",)),
                       staged(b, ("question:forest",)))
    plan.physical_action_issue_authorized = True
    with pytest.raises(D4OwnerHold, match="wrong committed"):
        inspect_d4_inert_recovery(
            tmp_path, tmp_path,
            expected_self_ids=("self-A", "self-B"),
            expected_source_world_id="world-A",
            expected_committed_sha256=digest,
        )
    plan.physical_action_issue_authorized = False
    with pytest.raises(D4OwnerHold, match="wrong committed"):
        inspect_d4_inert_recovery(
            tmp_path, tmp_path,
            expected_self_ids=("self-A", "self-B"),
            expected_source_world_id="world-A",
            expected_committed_sha256="0" * 64,
        )
