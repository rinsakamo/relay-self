"""Offline-only v0.1 3Self/Present/Memory boundary scenarios (Issue #833)."""

from dataclasses import replace

import pytest

from relay_self.common_io import (
    Clock,
    ClockStamp,
    CommonEnvelope,
    PreemptionEvent,
    PreemptionPhase,
    PreemptionTrace,
    ScopeRef,
)
from relay_self.innate_schema import (
    CognitiveSignal,
    SchemaActivation,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
    with_schema_mode,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import IdentitySpecification, Memory, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.three_self_present import (
    EpistemicStatus,
    Lens,
    LensClaim,
    PresentContractError,
    QuestionDisposition,
    project_present_frame,
    project_three_self,
    review_question_candidate,
)

SCOPE = ScopeRef("self-A", "world-A")
NATIVE = Provenance("native-receiver", "world-A:seq-42")
RETAINED = Provenance("retained-owner", "memory-integration-7")
OWNER = Provenance("self-owner", "question-decision-8")
SOURCE = ("native:seq-42", "present-5")


def cognition(self_id: str = "self-A") -> PersistentCognition:
    identity = IdentitySpecification(
        self_id=self_id, directives=("Continue informed agency.",),
        provenance=Provenance("identity-owner", f"{self_id}:identity"),
    )
    return PersistentCognition(identity=identity).retain_memory(Memory(
        memory_id="memory-previous-observation",
        content="I saw a different target in an earlier session.",
        source_provenance=NATIVE,
        integration_provenance=RETAINED,
    ))


def envelope(kind: str, scope: ScopeRef = SCOPE) -> CommonEnvelope:
    return CommonEnvelope(
        event_id=f"{kind}-event-7",
        kind=kind,
        scope=scope,
        occurred_at=ClockStamp(Clock.WORLD_TICK, 42),
        received_at=ClockStamp(Clock.HOST_MONOTONIC_NS, 110),
        provenance=NATIVE,
        source_refs=(NATIVE,),
    )


def schema_config() -> SchemaSnapshot:
    exploration = SchemaModuleSpec(
        schema_id="exploratory",
        version=1,
        supported_modes=frozenset({SchemaMode.FAST, SchemaMode.FULL}),
        signal_kinds=("QUESTION_CANDIDATE",),
        dependencies=(),
        provenance=Provenance("schema-owner", "explore-v1"),
    )
    motivation = SchemaModuleSpec(
        schema_id="homeostatic",
        version=1,
        supported_modes=frozenset({SchemaMode.FAST, SchemaMode.FULL}),
        signal_kinds=("NEED_CANDIDATE",),
        dependencies=(),
        provenance=Provenance("schema-owner", "need-v1"),
    )
    return SchemaSnapshot(
        self_id="self-A", revision=7,
        modules=(
            SchemaActivation(exploration, SchemaMode.FULL),
            SchemaActivation(motivation, SchemaMode.FAST),
        ),
    )


def signal(
    kind: str = "QUESTION_CANDIDATE", *, schema_id: str = "exploratory",
    mode: SchemaMode = SchemaMode.FULL,
) -> CognitiveSignal:
    from relay_self.innate_schema import ExplorationQuestion

    return CognitiveSignal(
        envelope=envelope("COGNITIVE_SIGNAL"),
        schema_id=schema_id,
        module_version=1,
        registry_revision=7,
        source_revision_refs=SOURCE,
        signal_kind=kind,
        execution_mode=mode,
        epistemic_status="HYPOTHETICAL",
        question_candidate=ExplorationQuestion("unknown-subject", ("action-ref",))
        if kind == "QUESTION_CANDIDATE" else None,
    )


def three_self(
    scope: ScopeRef = SCOPE, *,
    claims: tuple[LensClaim, ...] = (),
    memory_lens_refs: tuple[tuple[Lens, str], ...] = (),
):
    return project_three_self(
        retained=cognition(scope.self_id),
        scope=scope,
        epoch_ref="epoch-5",
        source_revision_refs=SOURCE,
        claims=claims,
        memory_lens_refs=memory_lens_refs,
    )


def present(*, signals: tuple[CognitiveSignal, ...] = ()):
    return project_present_frame(
        three_self=three_self(),
        snapshot=schema_config(),
        current_registry_revision=7,
        current_source_revision_refs=SOURCE,
        frame_revision=5,
        signals=signals,
        active_goal_refs=("goal-keep-alive",),
        active_question_refs=("question-before-l2",),
        active_intent_refs=("intent-1",),
    )


def test_three_lenses_exist_with_explicit_unknown_not_false_or_safe() -> None:
    views = three_self()
    assert views.my_self.read("ability").status is EpistemicStatus.UNKNOWN
    assert views.self_world.read("no_zombies").status is EpistemicStatus.UNKNOWN
    assert views.self_body.read("food").status is EpistemicStatus.UNKNOWN
    assert views.self_body.read("food").value_ref is None
    assert views.self_world.claims == ()


def test_memory_is_remembered_not_promoted_to_fresh_world_truth() -> None:
    views = three_self(memory_lens_refs=(
        (Lens.MYSELF, "memory-previous-observation"),
        (Lens.SELF_WORLD, "memory-previous-observation"),
    ))
    remembered = views.self_world.read("memory:memory-previous-observation")
    assert remembered.status is EpistemicStatus.REMEMBERED
    assert remembered.source_refs == (NATIVE, RETAINED)
    assert remembered.source_revision_refs == ()
    assert views.self_world.read("current-target").status is EpistemicStatus.UNKNOWN
    assert cognition().memories[0].content.startswith("I saw")


def test_native_world_and_body_observations_stay_separate_from_hypothesis() -> None:
    observed = LensClaim(
        scope=SCOPE, lens=Lens.SELF_WORLD,
        claim_key="observed-target", status=EpistemicStatus.OBSERVED,
        source_refs=(NATIVE,), source_revision_refs=SOURCE,
        value_ref="native-entity-7", coverage_ref="native-radius-covered",
    )
    hypothesis = LensClaim(
        scope=SCOPE, lens=Lens.SELF_WORLD,
        claim_key="possible-exit", status=EpistemicStatus.HYPOTHETICAL,
        source_refs=(Provenance("llm", "text-1"),),
        value_ref="llm-hypothesis-1",
    )
    body = LensClaim(
        scope=SCOPE, lens=Lens.SELF_BODY,
        claim_key="body-health", status=EpistemicStatus.OBSERVED,
        source_refs=(NATIVE,), source_revision_refs=SOURCE, value_ref="health-field",
    )
    views = three_self(claims=(observed, hypothesis, body))
    assert views.self_world.read("observed-target").status is EpistemicStatus.OBSERVED
    assert views.self_world.read("possible-exit").status is EpistemicStatus.HYPOTHETICAL
    assert views.self_body.read("body-health").value_ref == "health-field"
    assert views.my_self.read("possible-exit").status is EpistemicStatus.UNKNOWN


def test_foreign_self_session_or_stale_observed_source_is_rejected() -> None:
    original = LensClaim(
        scope=SCOPE, lens=Lens.SELF_WORLD, claim_key="target",
        status=EpistemicStatus.OBSERVED, source_refs=(NATIVE,),
        source_revision_refs=SOURCE, value_ref="entity-ref",
    )
    with pytest.raises(PresentContractError, match="foreign"):
        three_self(claims=(replace(original, scope=ScopeRef("self-B", "world-A")),))
    with pytest.raises(PresentContractError, match="foreign"):
        three_self(claims=(replace(original, scope=ScopeRef("self-A", "world-B")),))
    with pytest.raises(PresentContractError, match="stale observation"):
        three_self(claims=(replace(original, source_revision_refs=("old-native",)),))
    with pytest.raises(PresentContractError, match="foreign retained"):
        project_three_self(
            retained=cognition("self-B"), scope=SCOPE,
            epoch_ref="epoch-5", source_revision_refs=SOURCE,
        )


def test_unattested_world_fact_and_nonexistent_memory_cannot_be_projected() -> None:
    with pytest.raises(PresentContractError, match="qualified claim"):
        LensClaim(
            scope=SCOPE, lens=Lens.SELF_WORLD, claim_key="danger",
            status=EpistemicStatus.OBSERVED, value_ref="native-value",
            source_revision_refs=SOURCE,
        )
    with pytest.raises(PresentContractError, match="World session"):
        LensClaim(
            scope=ScopeRef("self-A"), lens=Lens.SELF_WORLD,
            claim_key="danger", status=EpistemicStatus.OBSERVED,
            source_refs=(NATIVE,), source_revision_refs=SOURCE, value_ref="evidence",
        )
    with pytest.raises(PresentContractError, match="memory not held"):
        three_self(memory_lens_refs=((Lens.SELF_BODY, "invented-memory"),))
    with pytest.raises(PresentContractError, match="duplicate lens claim"):
        claim = LensClaim(
            scope=SCOPE, lens=Lens.MYSELF, claim_key="skill-ability",
            status=EpistemicStatus.INFERRED,
            source_refs=(Provenance("inference", "bound-1"),),
            value_ref="hypothesis-1",
        )
        three_self(claims=(claim, claim))
    with pytest.raises(PresentContractError, match="UNKNOWN"):
        LensClaim(
            scope=SCOPE, lens=Lens.SELF_BODY, claim_key="food",
            status=EpistemicStatus.UNKNOWN, value_ref="imagined-full",
        )


def test_two_selves_in_one_world_do_not_share_internal_views() -> None:
    a = three_self()
    b = three_self(scope=ScopeRef("self-B", "world-A"))
    assert a.scope != b.scope
    assert a.identity_provenance != b.identity_provenance
    assert b.self_body.read("private-intent-A").status is EpistemicStatus.UNKNOWN
    assert b.self_world.read("A-secret-health").status is EpistemicStatus.UNKNOWN


def test_present_integrates_multiple_schema_signals_without_priority_winner() -> None:
    a = signal()
    b = signal("NEED_CANDIDATE", schema_id="homeostatic", mode=SchemaMode.FAST)
    other_env = replace(b.envelope, event_id="OTHER-SIGNAL-8")
    b = replace(b, envelope=other_env)
    frame = present(signals=(a, b))
    assert len(frame.signals) == 2
    assert frame.active_goal_refs == ("goal-keep-alive",)
    assert frame.active_question_refs == ("question-before-l2",)
    assert frame.active_intent_refs == ("intent-1",)
    assert not hasattr(frame, "winner")
    assert not hasattr(frame, "score")
    # #828 addendum: validity is not restricted by #831's narrow IDLE+LOW
    # exploratory candidate *generator*, nor by an absolute "free" trigger.
    assert a.signal_kind == "QUESTION_CANDIDATE"


def test_stale_or_foreign_schema_signal_not_admitted_to_present() -> None:
    valid = signal()
    config = schema_config()
    with pytest.raises(PresentContractError, match="stale schema registry"):
        project_present_frame(
            three_self=three_self(), snapshot=config,
            current_registry_revision=8, current_source_revision_refs=SOURCE,
            frame_revision=5, signals=(valid,),
        )
    with pytest.raises(PresentContractError, match="unqualified"):
        project_present_frame(
            three_self=three_self(), snapshot=config,
            current_registry_revision=7, current_source_revision_refs=SOURCE,
            frame_revision=5, signals=(replace(valid, registry_revision=6),),
        )
    with pytest.raises(PresentContractError, match="stale 3Self"):
        project_present_frame(
            three_self=three_self(), snapshot=config,
            current_registry_revision=7,
            current_source_revision_refs=("next-native",), frame_revision=5,
        )


@pytest.mark.parametrize("choice", list(QuestionDisposition))
def test_question_adopt_hold_decline_are_owner_receipts_not_goal_or_action(
    choice: QuestionDisposition,
) -> None:
    owner = IntentCommitment()
    owner.commit(
        "intent-1", objective="survive and remain active",
        at_ns=1, provenance=OWNER,
    )
    prior_events = owner.events
    retained = cognition()
    sig = signal()
    frame = present(signals=(sig,))
    receipt = review_question_candidate(
        present=frame, snapshot=schema_config(),
        signal_event_id=sig.envelope.event_id, disposition=choice,
        owner_self_id="self-A", expected_owner_revision=4,
        current_owner_revision=4, current_frame_revision=5,
        current_registry_revision=7, current_source_revision_refs=SOURCE,
        provenance=OWNER,
    )
    assert receipt.disposition is choice
    assert receipt.signal_event_id == sig.envelope.event_id
    assert owner.events == prior_events
    assert owner.current_intent.intent_id == "intent-1"
    assert retained.memories == cognition().memories
    assert not hasattr(receipt, "action_id")
    assert not hasattr(receipt, "goal_committed")


@pytest.mark.parametrize("failure,kwargs", [
    ("foreign Self", {"owner_self_id": "self-B"}),
    ("stale Self owner", {"current_owner_revision": 5}),
    ("stale Present frame", {"current_frame_revision": 6}),
    ("stale Present registry", {"current_registry_revision": 8}),
    ("stale Present source", {"current_source_revision_refs": ("old",)}),
    ("unknown", {"signal_event_id": "unknown-event"}),
])
def test_review_fail_closed_for_unsafe_or_stale_question(
    failure: str, kwargs: dict,
) -> None:
    sig = signal()
    args = dict(
        present=present(signals=(sig,)), snapshot=schema_config(),
        signal_event_id=sig.envelope.event_id,
        disposition=QuestionDisposition.ADOPT,
        owner_self_id="self-A", expected_owner_revision=4,
        current_owner_revision=4, current_frame_revision=5,
        current_registry_revision=7, current_source_revision_refs=SOURCE,
        provenance=OWNER,
    )
    with pytest.raises(PresentContractError, match=failure):
        review_question_candidate(**(args | kwargs))


def test_schema_off_on_roundtrip_fences_old_question_before_review() -> None:
    sig = signal()
    old_frame = present(signals=(sig,))
    config = schema_config()
    new_config = with_schema_mode(config, schema_id="exploratory", mode=SchemaMode.OFF)
    new_config = with_schema_mode(
        new_config, schema_id="exploratory", mode=SchemaMode.FULL
    )
    assert new_config.revision == 9
    with pytest.raises(PresentContractError, match="stale Present registry"):
        review_question_candidate(
            present=old_frame, snapshot=new_config,
            signal_event_id=sig.envelope.event_id,
            disposition=QuestionDisposition.ADOPT,
            owner_self_id="self-A", expected_owner_revision=4,
            current_owner_revision=4, current_frame_revision=5,
            current_registry_revision=9, current_source_revision_refs=SOURCE,
            provenance=OWNER,
        )


def test_l2_preemption_fences_result_without_dropping_question_goal_intent() -> None:
    frame = present()
    trace = PreemptionTrace(
        scope=SCOPE, l2_task_ref="task-l2", l2_generation=3,
        l1_task_ref="task-l1",
    ).append(PreemptionEvent(PreemptionPhase.CANCEL_REQUESTED, 118, OWNER))
    assert trace.output_fenced
    newer = project_present_frame(
        three_self=frame.three_self, snapshot=schema_config(),
        current_registry_revision=7, current_source_revision_refs=SOURCE,
        frame_revision=6,
        active_question_refs=frame.active_question_refs,
        active_goal_refs=frame.active_goal_refs,
        active_intent_refs=frame.active_intent_refs,
    )
    assert newer.active_question_refs == ("question-before-l2",)
    assert newer.active_goal_refs == ("goal-keep-alive",)
    assert newer.active_intent_refs == ("intent-1",)
    assert newer.signals == ()
    # No memory is written from cancelled L2 output, or by this pure projection.
    assert len(cognition().memories) == 1
