"""#633 SelfWorld v0 synthetic/offline negative controls; no external World runs."""
from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, replace

import pytest

from adapters.mineflayer.present_projection import MinecraftEntityPresent, MinecraftPresent
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.belief import (
    BeliefCriterion,
    BeliefEvidence,
    EvidenceRelation,
    PropositionKey,
    assess_belief,
)
from relay_self.persistent_cognition import IdentitySpecification, Memory, PersistentCognition
from relay_self.prediction import PredictionState, StateVariable, TransitionRule, predict_transition
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import ReactiveL0
from relay_self.self_body import compose_self_body_view
from relay_self.self_world import (
    InvalidSelfWorldData,
    WorldForecast,
    WorldOrigin,
    WorldScenario,
    compose_self_world_view,
)


def prov(ref: str, source: str = "synthetic") -> Provenance:
    return Provenance(source, ref)


def present(
    *, session: str = "s-A", seq: int = 8, entity_id: int | None = 42,
    truncated: bool = False,
) -> MinecraftPresent:
    entities = () if entity_id is None else (
        MinecraftEntityPresent(entity_id, "zombie", 3.0, (4.0, 64.0, 2.0)),
    )
    return MinecraftPresent(
        session_id=session, seq=seq, request_id=f"probe-{seq}",
        body_position=(1.0, 64.0, 2.0), health=10.0, food=6.0,
        food_saturation=3.0, inventory=(), observed_entities=entities,
        coverage_scope="bounded-native-nearby", coverage_radius_m=16.0,
        coverage_cap=16, coverage_candidates=len(entities),
        coverage_truncated=truncated,
        provenance=prov(f"{session}:{seq}", "mineflayer"),
    )


def view(self_id="A", *, present_value=None, **kwargs):
    obs = None if present_value is None else project_self_world_present(
        present_value, observer_id=self_id, observed_at_ns=100,
    )
    return compose_self_world_view(
        self_id=self_id, session_id=f"s-{self_id}", epoch_id="e1",
        observation=obs, **kwargs,
    )


def owned(self_id: str, *memory_ids: str) -> PersistentCognition:
    return PersistentCognition(
        identity=IdentitySpecification(
            self_id, ("keep-private-context-local",), prov(f"identity:{self_id}"),
        ),
        memories=tuple(
            Memory(m, f"{self_id}:personal-experience:{m}", prov(f"source:{m}"),
                   prov(f"commit:{m}"))
            for m in memory_ids
        ),
    )


def scenario() -> tuple[WorldScenario, WorldForecast]:
    state = PredictionState(
        "imagine-world-without-monster",
        (StateVariable("monster_present", False), StateVariable("distance_band", "near")),
        prov("imagined"),
    )
    hyp = WorldScenario("h1", "A", "entity-42", state)
    result = predict_transition(
        state, TransitionRule(
            "monster-away", (StateVariable("distance_band", "near"),),
            (StateVariable("distance_band", "far"),), prov("rule"),
        ),
    )
    return hyp, WorldForecast("h1", result)


def test_observed_entity_is_bounded_and_missing_is_unknown_not_safe():
    a = view(present_value=present())
    reading = a.observed_entity("entity-42")
    assert reading.origin is WorldOrigin.OBSERVED
    assert reading.value.position == (4.0, 64.0, 2.0)
    assert reading.source_refs == ("present:s-A:8:probe-8",)
    assert a.observed_entity("entity-99").origin is WorldOrigin.UNKNOWN
    empty = view(present_value=present(entity_id=None, truncated=False))
    assert empty.observation.coverage_candidates == 0
    assert empty.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    truncated = view(present_value=present(entity_id=None, truncated=True))
    assert truncated.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    assert truncated.observation.coverage_truncated
    assert not hasattr(a, "world_truth")
    assert not hasattr(a, "authorize_action")


def test_two_selves_same_world_are_information_asymmetric_and_have_no_shared_state():
    # One synthetic World with one monster; only Self A gets source visibility.
    a = view(present_value=present())
    b = view("B", present_value=present(session="s-B", entity_id=None))
    assert a.observed_entity("entity-42").origin is WorldOrigin.OBSERVED
    assert b.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    # A's refreshed observation is immutable and does not magically update B.
    a2 = view(present_value=present(seq=9, entity_id=None))
    assert a2.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    assert a.observed_entity("entity-42").origin is WorldOrigin.OBSERVED
    assert b.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    with pytest.raises(FrozenInstanceError):
        a.self_id = "B"


def test_other_self_external_location_is_not_private_body_or_memory():
    other_visible = replace(
        present(), observed_entities=(
            MinecraftEntityPresent(7, "B", 2.0, (3.0, 64.0, 2.0)),
        ),
    )
    a = view(present_value=other_visible)
    b_public = a.observed_entity("entity-7").value
    assert b_public.label == "B" and b_public.position == (3.0, 64.0, 2.0)
    assert not hasattr(b_public, "memory")
    assert not hasattr(b_public, "intent")
    assert not hasattr(b_public, "energy")
    assert not hasattr(b_public, "self_body")
    b_private = owned("B", "private-b")
    with pytest.raises(InvalidSelfWorldData, match="foreign Self private memory"):
        view(retained=b_private, memory_ids=("private-b",))
    assert a.remembered("private-b").origin is WorldOrigin.UNKNOWN


def test_explicit_own_retained_memory_is_not_current_observation_or_shareable():
    a = view(retained=owned("A", "seen-monster-yesterday"), memory_ids=("seen-monster-yesterday",))
    recalled = a.remembered("seen-monster-yesterday")
    assert recalled.origin is WorldOrigin.REMEMBERED
    assert recalled.value.content.startswith("A:personal-experience")
    assert a.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    with pytest.raises(InvalidSelfWorldData, match="retained snapshot"):
        view(memory_ids=("seen-monster-yesterday",))
    with pytest.raises(InvalidSelfWorldData, match="unknown or foreign"):
        view(retained=owned("A"), memory_ids=("seen-monster-yesterday",))
    with pytest.raises(InvalidSelfWorldData, match="duplicate"):
        view(retained=owned("A", "m"), memory_ids=("m", "m"))


def test_existing_belief_is_inferred_never_measured_and_not_mutated():
    proposition = PropositionKey("entity", "entity-42", "dangerous")
    b = assess_belief(
        (BeliefEvidence("ev1", proposition, EvidenceRelation.SUPPORT, prov("source")),),
        BeliefCriterion("danger-belief", proposition),
    )
    a = view(beliefs=(b,))
    assert a.inferred("entity-42", "dangerous").origin is WorldOrigin.INFERRED
    assert a.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    no_evidence = assess_belief((), BeliefCriterion("undetermined", proposition))
    assert view(beliefs=(no_evidence,)).inferred(
        "entity-42", "dangerous"
    ).origin is WorldOrigin.UNKNOWN
    wrong_domain = assess_belief(
        (), BeliefCriterion("private", PropositionKey("body", "self", "healthy")),
    )
    with pytest.raises(InvalidSelfWorldData, match="not World belief"):
        view(beliefs=(wrong_domain,))


def test_hypothetical_and_predicted_world_never_override_observation():
    hyp, forecast = scenario()
    a = view(present_value=present(), scenarios=(hyp,), forecasts=(forecast,))
    assert a.observed_entity("entity-42").origin is WorldOrigin.OBSERVED
    assert a.hypothetical("h1", "monster_present").value is False
    assert a.hypothetical("h1", "monster_present").origin is WorldOrigin.HYPOTHETICAL
    assert a.predicted("h1", "distance_band").value == "far"
    assert a.predicted("h1", "distance_band").origin is WorldOrigin.PREDICTED
    assert a.observed_entity("entity-42").value.label == "zombie"
    assert not hasattr(a, "commit_memory") and not hasattr(a, "execute_action")
    with pytest.raises(InvalidSelfWorldData, match="foreign Self counterfactual"):
        view(scenarios=(replace(hyp, owner_id="B"),))
    with pytest.raises(InvalidSelfWorldData, match="exact scenario"):
        view(forecasts=(forecast,))


def test_stale_foreign_duplicate_future_time_and_source_provenance_fail_closed():
    obs = project_self_world_present(present(), observer_id="A", observed_at_ns=100)
    with pytest.raises(InvalidSelfWorldData, match="foreign observer or session"):
        compose_self_world_view(self_id="B", session_id="s-A", epoch_id="e1", observation=obs)
    with pytest.raises(InvalidSelfWorldData, match="stale native"):
        view(present_value=present(), minimum_native_seq=9)
    with pytest.raises(InvalidSelfWorldData, match="duplicate native"):
        view(present_value=present(), seen_observation_refs=(obs.source_ref,))
    with pytest.raises(InvalidSelfWorldData, match="stale, future"):
        view(present_value=present(), inspected_at_ns=200, max_age_ns=10)
    with pytest.raises(InvalidSelfWorldData, match="stale, future"):
        view(present_value=present(), inspected_at_ns=99, max_age_ns=10)
    with pytest.raises(InvalidSelfWorldData, match="time check"):
        view(present_value=present(), inspected_at_ns=101)
    forged = replace(present(), provenance=prov("foreign:s", "mineflayer"))
    with pytest.raises(InvalidSelfWorldData, match="source provenance"):
        project_self_world_present(forged, observer_id="A")


def test_selfbody_requires_exact_self_id_session_epoch_and_native_source():
    present_a = present()
    world_obs = project_self_world_present(present_a, observer_id="A")
    body = compose_self_body_view(
        self_id="A", session_id="s-A", epoch_id="e1",
        observation=project_body_present(present_a),
    )
    combined = view(present_value=present_a, self_body=body)
    assert combined.self_body is body
    assert combined.observed_entity("entity-42").origin is WorldOrigin.OBSERVED
    with pytest.raises(InvalidSelfWorldData, match="SelfBody owner"):
        view(present_value=present_a, self_body=replace(body, self_id="B"))
    with pytest.raises(InvalidSelfWorldData, match="SelfBody owner"):
        view(present_value=present_a, self_body=replace(body, epoch_id="e2"))
    with pytest.raises(InvalidSelfWorldData, match="source mismatch"):
        view(present_value=present_a, self_body=replace(
            body, observation=project_body_present(present(seq=9)),
        ))
    with pytest.raises(InvalidSelfWorldData, match="SelfBody owner"):
        view(present_value=present_a, self_body=compose_self_body_view(
            session_id="s-A", epoch_id="e1",
        ))
    assert world_obs.provenance == body.observation.source_provenance


def test_action_memory_ownership_and_initial_l0_are_unchanged():
    initial = compose_self_world_view(self_id="A", session_id="s-A", epoch_id="initial")
    assert initial.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    assert "self_world" not in inspect.signature(ReactiveL0.decide).parameters
    assert "self_world" not in inspect.signature(ReactiveL0.__init__).parameters
    import relay_self.self_world as module
    assert not any(name in module.__dict__ for name in (
        "ActionSupervisor", "WorldConsequence", "MineflayerCommand",
        "save_persistent_cognition",
    ))


# #633 follow-up: existing ATT consumer, without L0 motor/BLF/MEM ownership.


def test_attention_reads_only_observed_source_and_never_broadcasts():
    from relay_self.attention import AttentionCriterion
    from relay_self.self_world import (
        resolve_self_world_attention,
        select_self_world_attention,
    )

    criterion = AttentionCriterion("look-zombie", focus_key="name:zombie", top_k=1)
    a = view(present_value=present())
    b = view("B", present_value=present(session="s-B", entity_id=None))
    selected_a = select_self_world_attention(a, criterion)
    selected_b = select_self_world_attention(b, criterion)
    assert selected_a.considered_count == 1 and len(selected_a.selected) == 1
    assert selected_b.considered_count == 0 and not selected_b.selected
    assert resolve_self_world_attention(a, selected_a)[0].origin is WorldOrigin.OBSERVED
    assert resolve_self_world_attention(b, selected_b) == ()
    assert b.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    with pytest.raises(InvalidSelfWorldData, match="count mismatch"):
        resolve_self_world_attention(b, selected_a)


def test_attention_selection_cannot_be_replayed_across_epoch_session_or_self():
    from relay_self.attention import AttentionCriterion
    from relay_self.self_world import (
        resolve_self_world_attention,
        select_self_world_attention,
    )

    a = view(present_value=present())
    sel = select_self_world_attention(a, AttentionCriterion("choose-visible"))
    assert len(resolve_self_world_attention(a, sel)) == 1

    # Same observer but newer native source: old attention snapshot is invalid.
    new_a = view(present_value=present(seq=9))
    with pytest.raises(InvalidSelfWorldData, match="foreign, stale"):
        resolve_self_world_attention(new_a, sel)
    new_epoch = compose_self_world_view(
        self_id="A", session_id="s-A", epoch_id="e2",
        observation=a.observation,
    )
    with pytest.raises(InvalidSelfWorldData, match="foreign, stale"):
        resolve_self_world_attention(new_epoch, sel)
    foreign = view("B", present_value=present(session="s-B"))
    with pytest.raises(InvalidSelfWorldData, match="foreign, stale"):
        resolve_self_world_attention(foreign, sel)


def test_attention_rejects_counterfeit_payload_or_candidate_and_empty_hypothesis():
    from relay_self.attention import AttentionCriterion
    from relay_self.self_world import (
        resolve_self_world_attention,
        select_self_world_attention,
    )

    a = view(present_value=present())
    selected = select_self_world_attention(a, AttentionCriterion("visible"))
    forged = replace(
        selected, selected=(
            replace(selected.selected[0], payload_ref="entity-999"),
        ),
    )
    with pytest.raises(InvalidSelfWorldData, match="invented"):
        resolve_self_world_attention(a, forged)
    forged_count = replace(selected, considered_count=8)
    with pytest.raises(InvalidSelfWorldData, match="count mismatch"):
        resolve_self_world_attention(a, forged_count)
    repeated = replace(
        selected, selected=(selected.selected[0], selected.selected[0]),
        considered_count=2,
    )
    # ATT selection's count is inconsistent with this single-entity view.
    with pytest.raises(InvalidSelfWorldData, match="count mismatch"):
        resolve_self_world_attention(a, repeated)

    hyp, forecast = scenario()
    imaginary = view(scenarios=(hyp,), forecasts=(forecast,))
    assert imaginary.hypothetical("h1", "monster_present").origin is WorldOrigin.HYPOTHETICAL
    assert select_self_world_attention(
        imaginary, AttentionCriterion("visible-only")
    ).selected == ()


def test_attention_can_read_public_other_self_position_without_private_mind():
    from relay_self.attention import AttentionCriterion
    from relay_self.self_world import (
        resolve_self_world_attention,
        select_self_world_attention,
    )

    other = MinecraftEntityPresent(7, "B", 2.0, (3.0, 64.0, 2.0))
    src = replace(present(), observed_entities=(other,))
    a = view(present_value=src)
    selected = select_self_world_attention(
        a, AttentionCriterion("visible-B", focus_key="entity-7"),
    )
    observed_b = resolve_self_world_attention(a, selected)
    assert len(observed_b) == 1
    assert observed_b[0].origin is WorldOrigin.OBSERVED
    assert observed_b[0].value.position == (3.0, 64.0, 2.0)
    assert not hasattr(observed_b[0].value, "memory")
    assert not hasattr(observed_b[0].value, "intent")

    # A's estimate of B's subjective field is not B's own observation.
    imagined = PredictionState(
        "a-guess-about-b",
        (StateVariable("B_sees_zombie", True),), prov("a-private-guess"),
    )
    guess = WorldScenario("guess-b-world", "A", "entity-7", imagined)
    a_guess = view(present_value=src, scenarios=(guess,))
    assert a_guess.hypothetical(
        "guess-b-world", "B_sees_zombie",
    ).origin is WorldOrigin.HYPOTHETICAL
    assert a_guess.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    b = view("B", present_value=present(session="s-B", entity_id=None))
    assert b.observed_entity("entity-42").origin is WorldOrigin.UNKNOWN
    with pytest.raises(InvalidSelfWorldData, match="foreign Self counterfactual"):
        view(present_value=src, scenarios=(replace(guess, owner_id="B"),))


def test_att_selects_only_bounded_observed_subset_without_salience_or_action():
    from relay_self.attention import AttentionCriterion
    from relay_self.self_world import (
        resolve_self_world_attention,
        select_self_world_attention,
    )

    p = replace(
        present(),
        observed_entities=(
            MinecraftEntityPresent(42, "zombie", 3.0, (4.0, 64.0, 2.0)),
            MinecraftEntityPresent(7, "B", 2.0, (3.0, 64.0, 2.0)),
        ),
        coverage_candidates=2, coverage_truncated=True,
    )
    a = view(present_value=p)
    picked = select_self_world_attention(
        a, AttentionCriterion("one-visible", top_k=1),
    )
    assert picked.considered_count == 2
    assert len(picked.selected) == 1
    assert picked.selected[0].priority == 0  # no invented danger ranking
    assert resolve_self_world_attention(a, picked)[0].value.entity_ref == "entity-42"
    assert a.observed_entity("entity-999").origin is WorldOrigin.UNKNOWN
    assert a.observation.coverage_truncated
    assert not hasattr(picked, "execute_action")
    assert not hasattr(picked, "grant_action")


# #633 Stage F: a discrepancy is read-only evidence, never a learning grant.


def anchored_forecast(
    old_view,
    predicted_label: str,
    *,
    action_id: str | None = None,
    target: str = "entity-42",
):
    refs = (old_view.observation.source_ref, f"target:{target}")
    if action_id is not None:
        refs += (f"action:{action_id}",)
    state = PredictionState(
        "anchored-entity-label",
        (StateVariable("entity_label", "zombie"),), prov("owner-A-assumption"),
        source_refs=refs,
        source_provenance=(old_view.observation.provenance,),
    )
    hyp = WorldScenario("source-bound-future", old_view.self_id, target, state)
    forecast = WorldForecast(
        hyp.scenario_id,
        predict_transition(
            state,
            TransitionRule(
                "one-step-change",
                (StateVariable("entity_label", "zombie"),),
                (StateVariable("entity_label", predicted_label),),
                prov("owner-A-rule"),
            ),
        ),
    )
    return hyp, forecast


def review_fixture(
    *,
    predicted_label: str = "creeper",
    later_present=None,
    max_gap: int = 10,
):
    from relay_self.self_world import review_self_world_prediction

    before = view(present_value=present(seq=8))
    hypothesis, forecast = anchored_forecast(before, predicted_label)
    prior = view(
        present_value=present(seq=8),
        scenarios=(hypothesis,), forecasts=(forecast,),
    )
    after = replace(view(present_value=(
        later_present if later_present is not None else present(seq=9)
    )), epoch_id="e2")
    result = review_self_world_prediction(
        prior, after, scenario_id=hypothesis.scenario_id,
        variable_key="entity_label", max_native_seq_gap=max_gap,
    )
    return prior, after, result


def test_cross_epoch_prediction_mismatch_is_not_learning():
    from relay_self.self_world import WorldPredictionReviewStatus

    prior, after, result = review_fixture(predicted_label="creeper")
    assert result.status is WorldPredictionReviewStatus.MISMATCH
    assert result.predicted_value == "creeper"
    assert result.observed_value == "zombie"
    assert result.reason_code == "observed_prediction_mismatch"
    assert result.prior_observation_ref == prior.observation.source_ref
    assert result.later_observation_ref == after.observation.source_ref
    assert result.observation_provenance == after.observation.provenance
    assert result.prediction_source_provenance
    assert not hasattr(result, "feedback")
    assert not hasattr(result, "commit_learning_update")
    assert prior.observed_entity("entity-42").value.label == "zombie"


def test_match_never_grants_feedback_and_missing_is_unknown():
    from relay_self.self_world import WorldPredictionReviewStatus

    _, _, match = review_fixture(predicted_label="zombie")
    assert match.status is WorldPredictionReviewStatus.MATCH
    _, _, absent = review_fixture(
        later_present=present(seq=9, entity_id=None, truncated=False),
    )
    assert absent.status is WorldPredictionReviewStatus.UNDETERMINED
    assert absent.observed_value is None
    assert absent.reason_code == "target_or_property_unobserved"
    _, _, truncated = review_fixture(
        later_present=present(seq=9, entity_id=None, truncated=True),
    )
    assert truncated.status is WorldPredictionReviewStatus.UNDETERMINED
    _, _, expired = review_fixture(later_present=present(seq=99), max_gap=4)
    assert expired.status is WorldPredictionReviewStatus.UNDETERMINED
    assert expired.reason_code == "source_gap_beyond_explicit_bound"


def test_cross_epoch_review_rejects_foreign_replay_and_bad_limits():
    from relay_self.self_world import review_self_world_prediction

    prior, after, _ = review_fixture()
    arg = dict(
        scenario_id="source-bound-future",
        variable_key="entity_label", max_native_seq_gap=10,
    )
    with pytest.raises(InvalidSelfWorldData, match="foreign observer"):
        review_self_world_prediction(
            prior, view("B", present_value=present(session="s-B", seq=9)), **arg,
        )
    with pytest.raises(InvalidSelfWorldData, match="stale or replayed"):
        review_self_world_prediction(
            prior, replace(view(present_value=present(seq=8)), epoch_id="e2"),
            **arg,
        )
    with pytest.raises(InvalidSelfWorldData, match="distinct decision"):
        review_self_world_prediction(prior, prior, **arg)
    with pytest.raises(InvalidSelfWorldData, match="positive integer"):
        review_self_world_prediction(
            prior, after, **{**arg, "max_native_seq_gap": False},
        )
    with pytest.raises(InvalidSelfWorldData, match="observable exterior"):
        review_self_world_prediction(
            prior, after, **{**arg, "variable_key": "energy"},
        )
    forged = replace(after.observation, provenance=prov("s-A:999", "mineflayer"))
    with pytest.raises(InvalidSelfWorldData, match="source lineage"):
        review_self_world_prediction(
            prior, replace(after, observation=forged), **arg,
        )
    with pytest.raises(InvalidSelfWorldData, match="nonmonotonic"):
        review_self_world_prediction(
            prior,
            replace(
                after, observation=replace(after.observation, observed_at_ns=90),
            ),
            **arg,
        )


def test_unbound_forged_or_unavailable_forecast_cannot_mint_mismatch():
    from relay_self.self_world import review_self_world_prediction

    before, after, _ = review_fixture()
    kwargs = dict(
        scenario_id="source-bound-future", variable_key="entity_label",
        max_native_seq_gap=10,
    )
    scenario0 = before.scenarios[0]
    no_ancestor = replace(
        scenario0.state, source_refs=("target:entity-42",),
    )
    fake_scenario = replace(scenario0, state=no_ancestor)
    fake_forecast = WorldForecast(
        "source-bound-future",
        predict_transition(no_ancestor, before.forecasts[0].prediction.rule),
    )
    tampered = replace(
        before, scenarios=(fake_scenario,), forecasts=(fake_forecast,),
    )
    with pytest.raises(InvalidSelfWorldData, match="unbound"):
        review_self_world_prediction(tampered, after, **kwargs)
    with pytest.raises(InvalidSelfWorldData, match="one explicit matching"):
        review_self_world_prediction(
            replace(before, forecasts=()), after, **kwargs,
        )
    with pytest.raises(InvalidSelfWorldData, match="unbound"):
        review_self_world_prediction(
            replace(before, scenarios=(replace(scenario0, owner_id="B"),)),
            after, **kwargs,
        )
    # No invented predicted external property from unavailable PRD variable.
    missing_key = review_self_world_prediction(
        before, after,
        scenario_id="source-bound-future",
        variable_key="entity_visible", max_native_seq_gap=10,
    )
    from relay_self.self_world import WorldPredictionReviewStatus

    assert missing_key.status is WorldPredictionReviewStatus.UNDETERMINED


def test_positive_visibility_does_not_imply_global_absence():
    from relay_self.self_world import (
        WorldPredictionReviewStatus,
        review_self_world_prediction,
    )

    before = view(present_value=present(seq=8))
    state = PredictionState(
        "possible-monster-presence",
        (StateVariable("entity_visible", False),), prov("counterfactual"),
        source_refs=(before.observation.source_ref, "target:entity-42"),
    )
    rule = TransitionRule(
        "remain-unobserved", (StateVariable("entity_visible", False),),
        (StateVariable("entity_visible", False),), prov("possible"),
    )
    hyp = WorldScenario("visible-claim", "A", "entity-42", state)
    forecast = WorldForecast("visible-claim", predict_transition(state, rule))
    prior = replace(before, scenarios=(hyp,), forecasts=(forecast,))
    observed_after = replace(view(present_value=present(seq=9)), epoch_id="e2")
    seen = review_self_world_prediction(
        prior, observed_after, scenario_id="visible-claim",
        variable_key="entity_visible", max_native_seq_gap=10,
    )
    assert seen.status is WorldPredictionReviewStatus.MISMATCH
    assert seen.observed_value is True
    unobserved_after = replace(
        view(present_value=present(seq=9, entity_id=None)), epoch_id="e2",
    )
    unseen = review_self_world_prediction(
        prior, unobserved_after, scenario_id="visible-claim",
        variable_key="entity_visible", max_native_seq_gap=10,
    )
    assert unseen.status is WorldPredictionReviewStatus.UNDETERMINED
    assert unseen.observed_value is None


def synthetic_s17_world_review_chain():
    """Re-use the qualified S17 offline Action fixture; no Java/Node I/O."""
    import asyncio

    import test_action_feedback_qualification as s17
    from adapters.mineflayer.action_outcome import interpret_world_consequence
    from adapters.mineflayer.execution import (
        build_mineflayer_command,
        execute_mineflayer_command,
    )
    from adapters.mineflayer.present_projection import project_mineflayer_present
    from adapters.mineflayer.python_protocol import (
        MineflayerEntityFact,
        MineflayerPosition,
    )
    from adapters.mineflayer.self_world_projection import project_self_world_present

    # Use a CURRENT ISSUED snapshot to perform S15/S16, then obtain
    # the existing Action owner's terminal OUTCOME. Old ISSUED is stale
    # immediately after terminal transition and cannot be replayed.
    chain = s17.issued_chain()
    binding, supervisor, issued = chain[-4], chain[-2], chain[-1]
    command = build_mineflayer_command(issued, binding)
    consequence = asyncio.run(execute_mineflayer_command(
        s17.successful_session(command), command,
        provenance=s17.provenance("selfworld-synthetic-world-consequence"),
    ))
    # Supply a complete synthetic native after-probe that actually observes
    # the target. Re-run existing S16 interpretation, not a free-form result.
    native_after = consequence.after_observation
    fact = MineflayerEntityFact(
        42, "zombie", "mob", 3.0,
        MineflayerPosition(x=3.0, y=64.0, z=0.2),
    )
    snapshot = replace(
        native_after.snapshot,
        nearby_entities=(fact,),
        nearby_entities_coverage=replace(
            native_after.snapshot.nearby_entities_coverage,
            candidate_count=1,
        ),
    )
    native_after = replace(native_after, snapshot=snapshot)
    consequence = replace(consequence, after_observation=native_after)
    outcome = interpret_world_consequence(
        issued, binding, consequence,
        provenance=prov("S16-source-bound-interpretation"),
    )
    action = s17.record_interpreted_action_outcome(
        supervisor, outcome, at_ns=20,
    )

    old_present = present(session="s15-session", seq=0)
    old_observation = project_self_world_present(
        old_present, observer_id="A", observed_at_ns=100,
    )
    old_view = compose_self_world_view(
        self_id="A", session_id="s15-session", epoch_id="e1",
        observation=old_observation,
    )
    hyp, forecast = anchored_forecast(
        old_view, "creeper", action_id=action.action_id,
    )
    prior = replace(old_view, scenarios=(hyp,), forecasts=(forecast,))
    after_present = project_mineflayer_present(native_after)
    current = compose_self_world_view(
        self_id="A", session_id="s15-session", epoch_id="e2",
        observation=project_self_world_present(
            after_present, observer_id="A", observed_at_ns=120,
        ),
    )
    return s17, prior, current, action, outcome, consequence


def test_s17_explicit_feedback_from_mismatch_cannot_commit_learning():
    from adapters.mineflayer.self_world_projection import (
        interpret_self_world_mismatch_as_s17_feedback,
    )
    from relay_self.action_feedback import LearningFeedbackInterpretationStatus
    from relay_self.learning import (
        FeedbackDirection,
        MissingLearningAuthority,
        commit_learning_update,
        propose_learning_update,
    )
    from relay_self.self_world import WorldPredictionReviewStatus

    s17, prior, current, action, outcome, consequence = synthetic_s17_world_review_chain()
    original = s17.learning_state()
    criterion = s17.feedback_criterion(direction=FeedbackDirection.HOLD)
    review, feedback = interpret_self_world_mismatch_as_s17_feedback(
        prior, current, scenario_id="source-bound-future",
        variable_key="entity_label", max_native_seq_gap=10,
        action=action, outcome=outcome, consequence=consequence,
        criterion=criterion, provenance=prov("S17-selfworld-interpretation"),
    )
    assert review.status is WorldPredictionReviewStatus.MISMATCH
    assert feedback.status is LearningFeedbackInterpretationStatus.PRODUCED
    assert feedback.feedback.direction is FeedbackDirection.HOLD
    assert feedback.feedback.target_id == original.target_id
    assert original.value == 3 and original.revision == 0
    assert not hasattr(review, "learning_authority")
    # Even with actual feedback, existing S10 proposal/commit remain explicit.
    proposed = propose_learning_update(
        original, feedback.feedback, s17.learning_rule(),
    )
    with pytest.raises(MissingLearningAuthority):
        commit_learning_update(
            original, proposed, None, provenance=prov("cannot-bypass-LRN"),
        )


def test_s17_mismatch_bridge_fails_closed_without_exact_native_lineage():
    from adapters.mineflayer.self_world_projection import (
        interpret_self_world_mismatch_as_s17_feedback,
    )
    from relay_self.action_outcome import ActionOutcomeDisposition

    s17, prior, current, action, outcome, consequence = synthetic_s17_world_review_chain()
    args = dict(
        scenario_id="source-bound-future", variable_key="entity_label",
        max_native_seq_gap=10, action=action, outcome=outcome,
        consequence=consequence, criterion=s17.feedback_criterion(),
        provenance=prov("S17-exact-gate"),
    )

    matched = replace(prior, forecasts=(
        WorldForecast(
            "source-bound-future",
            predict_transition(
                prior.scenarios[0].state,
                replace(
                    prior.forecasts[0].prediction.rule,
                    assignments=(StateVariable("entity_label", "zombie"),),
                ),
            ),
        ),
    ))
    with pytest.raises(InvalidSelfWorldData, match="only observed mismatch"):
        interpret_self_world_mismatch_as_s17_feedback(matched, current, **args)

    with pytest.raises(InvalidSelfWorldData, match="unqualified executed"):
        interpret_self_world_mismatch_as_s17_feedback(
            prior, current,
            **{**args, "outcome": replace(
                outcome, disposition=ActionOutcomeDisposition.UNKNOWN,
            )},
        )
    with pytest.raises(InvalidSelfWorldData, match="lineage mismatch"):
        interpret_self_world_mismatch_as_s17_feedback(
            prior, current,
            **{**args, "outcome": replace(outcome, session_id="other-session")},
        )
    with pytest.raises(InvalidSelfWorldData, match="exact Action readback"):
        interpret_self_world_mismatch_as_s17_feedback(
            prior,
            replace(
                current,
                observation=replace(
                    current.observation, coverage_radius_m=12.0,
                ),
            ),
            **args,
        )
    with pytest.raises(InvalidSelfWorldData, match="not bound to this Action"):
        unbound_state = replace(
            prior.scenarios[0].state,
            source_refs=(
                prior.observation.source_ref,
                "target:entity-42",
            ),
        )
        unbound_scenario = replace(prior.scenarios[0], state=unbound_state)
        unbound_forecast = WorldForecast(
            "source-bound-future",
            predict_transition(
                unbound_state, prior.forecasts[0].prediction.rule,
            ),
        )
        interpret_self_world_mismatch_as_s17_feedback(
            replace(
                prior, scenarios=(unbound_scenario,), forecasts=(unbound_forecast,),
            ),
            current, **args,
        )


def test_s17_criterion_not_matched_stays_not_applicable_no_reward_defaults():
    from adapters.mineflayer.self_world_projection import (
        interpret_self_world_mismatch_as_s17_feedback,
    )
    from relay_self.action_feedback import LearningFeedbackInterpretationStatus

    s17, prior, current, action, outcome, consequence = synthetic_s17_world_review_chain()
    review, result = interpret_self_world_mismatch_as_s17_feedback(
        prior, current, scenario_id="source-bound-future",
        variable_key="entity_label", max_native_seq_gap=10,
        action=action, outcome=outcome, consequence=consequence,
        criterion=s17.feedback_criterion(action_ref="DIFFERENT_ACTION"),
        provenance=prov("S17-unmatched-criterion"),
    )
    assert review.reason_code == "observed_prediction_mismatch"
    assert result.status is LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    assert result.feedback is None
