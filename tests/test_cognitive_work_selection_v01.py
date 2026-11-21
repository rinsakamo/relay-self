"""#841 offline Present+Schema -> L1 work-choice seam tests, no live LLM."""

from dataclasses import replace

import pytest

from relay_self.cognitive_profile_contract import (
    OriginKind,
    TaskOrigin,
    bind_present_task,
)
from relay_self.cognitive_work_selection import (
    NO_NEW_WORK,
    CognitiveWorkCandidate,
    WorkSelectionError,
    accept_selected_work,
    propose_work_selection,
)
from relay_self.common_io import (
    Clock,
    ClockStamp,
    CognitionResultReceipt,
    CommonEnvelope,
    Profile,
    ScopeRef,
    TaskRequirement,
    select_profile,
)
from relay_self.innate_schema import (
    CognitiveSignal,
    ExplorationQuestion,
    SchemaActivation,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.relay_engine import DecisionStatus
from relay_self.three_self_present import project_present_frame, project_three_self

SCOPE = ScopeRef("self-A", "world-A")
SOURCE = ("native-71", "present-5")
NATIVE = Provenance("world-observation", "native-71")
OWNER = Provenance("self-owner", "revision-4")
SCHEMA = Provenance("schema-spec", "schema-v1")


def envelope(kind="COGNITIVE_TASK", scope=SCOPE, received=100):
    return CommonEnvelope(
        event_id=f"{kind}-event", kind=kind, scope=scope,
        occurred_at=ClockStamp(Clock.WORLD_TICK, 71),
        received_at=ClockStamp(Clock.HOST_MONOTONIC_NS, received),
        provenance=OWNER, source_refs=(NATIVE,),
    )


def present(*, include_signal=False, source=SOURCE):
    identity = PersistentCognition(
        IdentitySpecification("self-A", ("Act with provenance.",), OWNER)
    )
    lenses = project_three_self(
        retained=identity, scope=SCOPE,
        epoch_ref="epoch-5", source_revision_refs=source,
    )
    spec = SchemaModuleSpec(
        schema_id="explore", version=1,
        supported_modes=frozenset({SchemaMode.FULL}),
        signal_kinds=("QUESTION_CANDIDATE",), dependencies=(),
        provenance=SCHEMA,
    )
    snapshot = SchemaSnapshot(
        "self-A", 9, (SchemaActivation(spec, SchemaMode.FULL),)
    )
    signals = ()
    if include_signal:
        signals = (
            CognitiveSignal(
                envelope=envelope("COGNITIVE_SIGNAL"),
                schema_id="explore", module_version=1, registry_revision=9,
                source_revision_refs=source, signal_kind="QUESTION_CANDIDATE",
                execution_mode=SchemaMode.FULL, epistemic_status="HYPOTHETICAL",
                question_candidate=ExplorationQuestion(
                    unknown_target_ref="observed-unknown-1",
                    reference_action_refs=("move", "inspect"),
                ),
            ),
        )
    return project_present_frame(
        three_self=lenses, snapshot=snapshot,
        current_registry_revision=9, current_source_revision_refs=source,
        frame_revision=5, signals=signals,
        active_question_refs=("question-1",),
        active_goal_refs=("goal-explore", "goal-survive"),
        active_intent_refs=("intent-1",), need_refs=("need-1",),
    )


def candidate(
    ident="work-goal",
    *,
    origin_ref="goal-survive",
    origin_kind=OriginKind.GOAL,
    requirement=TaskRequirement.SELECT_FINITE,
):
    return CognitiveWorkCandidate(
        candidate_ref=ident, description="Review known need and goals",
        origin_ref=origin_ref, origin_kind=origin_kind,
        requirement=requirement, provenance=OWNER,
    )


def build(options=None, *, frame=None, generation=1):
    if options is None:
        options = (candidate(),)
    return propose_work_selection(
        present=frame if frame is not None else present(),
        envelope=envelope(), candidates=options,
        owner_revision=4, task_ref="meta-select-1",
        generation=generation, deadline_ns=200, context_provenance=OWNER,
    )


def resolve(round_, choice_id="work-goal", **overrides):
    decision = select_profile(
        round_.task, scope=SCOPE,
        current_source_revision_refs=SOURCE,
        now_ns=110, l1_available=True,
    )
    receipt = CognitionResultReceipt(
        task_ref="meta-select-1", scope=SCOPE,
        generation=round_.task.generation, profile=Profile.L1,
        source_revision_refs=SOURCE, status="SELECTED",
        provenance=OWNER, choice_id=choice_id,
    )
    values = dict(
        result=receipt, route=decision, present=present(),
        current_source_revision_refs=SOURCE,
        current_present_revision=5, current_registry_revision=9,
        current_owner_revision=4, current_generation=round_.task.generation,
        now_ns=120, compute_admitted=True,
    )
    values.update(overrides)
    return accept_selected_work(round_, **values)


def test_cpu_meta_task_l1_no_recursive_goal_and_stable_context() -> None:
    round_ = build(
        (candidate("z-goal", origin_ref="goal-survive"),
         candidate("a-question", origin_kind=OriginKind.QUESTION,
                   origin_ref="question-1")),
    )
    assert round_ is not None
    assert round_.task.requirement is TaskRequirement.SELECT_FINITE
    assert round_.task.question_ref is None and round_.task.intent_ref is None
    assert tuple(c.choice_id for c in round_.task.choices) == (
        "a-question", "z-goal", NO_NEW_WORK,
    )
    assert round_.request.think_allowed is False
    assert round_.request.context[0].key == "present_projection"
    assert round_.request.context[1].key == "schema_signals"
    assert build(
        (candidate("a-question", origin_kind=OriginKind.QUESTION,
                   origin_ref="question-1"),
         candidate("z-goal", origin_ref="goal-survive")),
    ).request.context == round_.request.context


def test_zero_candidate_skips_model_one_candidate_preserves_no_work() -> None:
    assert build(()) is None
    one = build()
    assert one is not None
    assert tuple(c.choice_id for c in one.task.choices) == (
        "work-goal", NO_NEW_WORK,
    )


def test_selected_known_goal_is_a_proposal_then_existing_task_can_be_bound() -> None:
    owner = IntentCommitment()
    owner.commit("intent-1", objective="explore", at_ns=1, provenance=OWNER)
    old = owner.events
    round_ = build((candidate(requirement=TaskRequirement.OPEN_REASONING),))
    proposal = resolve(round_)
    assert proposal.choice_id == "work-goal"
    assert proposal.candidate.requirement is TaskRequirement.OPEN_REASONING
    assert not proposal.requires_owner_adoption
    assert owner.events == old
    # Explicit separate caller choice can now use pre-existing #835 binding.
    bound = bind_present_task(
        present=present(), envelope=envelope(),
        origin=TaskOrigin(OriginKind.GOAL, "goal-survive", 4),
        task_ref="future-work", requirement=TaskRequirement.OPEN_REASONING,
        generation=1, deadline_ns=200,
    )
    assert bound.origin.ref == "goal-survive"
    assert bound.task.requirement is TaskRequirement.OPEN_REASONING


def test_schema_signal_work_proposal_does_not_adopt_question_or_goal() -> None:
    frame = present(include_signal=True)
    option = candidate(
        "work-schema", origin_ref="COGNITIVE_SIGNAL-event", origin_kind=None,
        requirement=TaskRequirement.OPEN_REASONING,
    )
    round_ = build((option,), frame=frame)
    assert round_ is not None
    proposal = resolve(
        round_, choice_id="work-schema", present=frame,
    )
    assert proposal.requires_owner_adoption
    assert proposal.candidate.origin_ref == "COGNITIVE_SIGNAL-event"
    assert frame.active_question_refs == ("question-1",)
    with pytest.raises(ValueError, match="not active"):
        bind_present_task(
            present=frame, envelope=envelope(),
            origin=TaskOrigin(OriginKind.QUESTION, "COGNITIVE_SIGNAL-event", 4),
            task_ref="not-adopted", requirement=TaskRequirement.OPEN_REASONING,
            generation=1, deadline_ns=200,
        )


def test_explicit_no_new_work_and_unresolved_no_auto_l2() -> None:
    round_ = build()
    proposal = resolve(round_, choice_id=NO_NEW_WORK)
    assert proposal.candidate is None
    assert not proposal.requires_owner_adoption
    assert not hasattr(proposal, "action_id")
    with pytest.raises(WorkSelectionError, match="not admitted or unresolved"):
        resolve(
            round_,
            result=CognitionResultReceipt(
                task_ref="meta-select-1", scope=SCOPE, generation=1,
                profile=Profile.L1, source_revision_refs=SOURCE,
                status=DecisionStatus.UNRESOLVED.value,
                provenance=OWNER, choice_id=None,
            ),
        )


@pytest.mark.parametrize("override", [
    {"current_source_revision_refs": ("native-72",)},
    {"current_present_revision": 6},
    {"current_registry_revision": 10},
    {"current_owner_revision": 5},
    {"current_generation": 2},
    {"now_ns": 200},
    {"compute_admitted": False},
])
def test_stale_or_unadmitted_l1_result_rejected(override) -> None:
    with pytest.raises(WorkSelectionError):
        resolve(build(), **override)


def test_unknown_or_forged_choice_rejected() -> None:
    with pytest.raises(WorkSelectionError):
        resolve(build(), choice_id="fictional-work")
    with pytest.raises(WorkSelectionError):
        resolve(
            build(),
            result=CognitionResultReceipt(
                task_ref="meta-select-1", scope=SCOPE, generation=1,
                profile=Profile.L2, source_revision_refs=SOURCE,
                status="SELECTED", provenance=OWNER, choice_id="work-goal",
            ),
        )


def test_revised_present_fences_earlier_choice() -> None:
    old = build()
    new_frame = replace(present(), frame_revision=6)
    with pytest.raises(WorkSelectionError, match="stale"):
        resolve(old, present=new_frame)
    with pytest.raises(WorkSelectionError, match="stale"):
        resolve(old, present=present(source=("native-72", "present-6")))


def test_invalid_candidate_origin_and_duplicate_rejected() -> None:
    with pytest.raises(WorkSelectionError, match="not live"):
        build((candidate(origin_ref="goal-not-adopted"),))
    with pytest.raises(WorkSelectionError, match="duplicate"):
        build((candidate(), candidate()))
    with pytest.raises(WorkSelectionError, match="not live"):
        build((candidate("fake-signal", origin_ref="signal-not-issued", origin_kind=None),))
    with pytest.raises(WorkSelectionError, match="foreign"):
        propose_work_selection(
            present=present(), envelope=envelope(scope=ScopeRef("self-B", "world-A")),
            candidates=(candidate(),), owner_revision=4, task_ref="meta",
            generation=1, deadline_ns=200, context_provenance=OWNER,
        )


def test_native_fast_cue_not_a_meta_task_and_no_l1_think_escalation() -> None:
    with pytest.raises(WorkSelectionError, match="native L0"):
        candidate(requirement=TaskRequirement.FAST_REACTION)
    with pytest.raises(WorkSelectionError, match="reserved"):
        candidate(ident=NO_NEW_WORK)
    assert build().request.think_allowed is False


def test_selector_does_not_issue_actions_or_write_memory() -> None:
    round_ = build()
    proposal = resolve(round_)
    assert not hasattr(round_, "issue_action")
    assert not hasattr(proposal, "commit")
    assert not hasattr(proposal, "memory_revision")
    assert round_.request.intent_id is None
