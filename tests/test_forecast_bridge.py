"""L2 forecast-vs-observation offline tests; no model, Minecraft or S10 updates."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_experience_bridge as l1
from relay_self.experience_bridge import retain_observation
from relay_self.forecast_bridge import (
    ActionForecast,
    AdmittedObservation,
    ContrastStatus,
    ForecastRejected,
    cheap_rule_comparator,
    compare_forecast,
    read_surprise_candidates,
    retain_comparison,
    retain_forecast,
)
from relay_self.persistent_cognition import Memory, load_persistent_cognition, save_persistent_cognition
from relay_self.prediction import (
    PredictionState,
    PredictionStatus,
    StateVariable,
    TransitionRule,
    predict_transition,
)
from relay_self.provenance import Provenance


def p(source: str = "fixture", ref: str = "l2") -> Provenance:
    return Provenance(source, ref)


def forecast(
    *,
    action: str = "MOVE_BACKWARD",
    revision: int = 1,
    digest: str = l1.DIGEST_A,
    forecast_id: str = "f1",
    has_condition: bool = True,
    source_band: str = "near",
) -> ActionForecast:
    state = PredictionState(
        "state-one",
        (StateVariable("action_ref", action),
         StateVariable("distance_band", source_band),
         StateVariable("hazard_after", "unknown")),
        p("s49-source-projection", "observation-1"),
    )
    preconditions = (StateVariable("distance_band", "near"),)
    if has_condition:
        preconditions = (StateVariable("action_ref", action), *preconditions)
    rule = TransitionRule(
        "deterministic-near-escape",
        preconditions, (StateVariable("hazard_after", "far"),),
        p("cheap-deterministic-rule", "v1"),
    )
    return ActionForecast(
        forecast_id, "session-1", revision, digest, action, l1.TAGS,
        predict_transition(state, rule), p("s49-source", "session-1:1"),
    )


def observation(*, result: str = "far", unknown: bool = False,
                revision: int = 2, digest: str = l1.DIGEST_B):
    q = l1.qualified(
        action_id="action-1", session="session-1", unknown=unknown,
        revision=revision, digest=digest,
    )
    return AdmittedObservation(
        q, (StateVariable("hazard_after", result),),
        p("independent-s16-projection", "native-after-snapshot"),
    )


ADMITTED = frozenset({l1.DIGEST_A, l1.DIGEST_B})


def original_owner(f: ActionForecast, o: AdmittedObservation):
    owner = retain_forecast(
        l1.identity(), f, integration_provenance=p("L2", "forecast"),
    )
    owner = retain_observation(
        owner, o.qualified, integration_provenance=p("S", "observed"),
    )
    return owner


def test_retained_hypothesis_plus_independent_observation_match_cheap(tmp_path):
    f = forecast()
    o = observation()
    assert f.prediction.status is PredictionStatus.PREDICTED
    assert cheap_rule_comparator(f) == f.prediction
    owner = original_owner(f, o)
    assert len(owner.memories) == 2
    assert '"observed_world_fact":false' in owner.memories[0].content
    assert '"executed_alternative":false' in owner.memories[0].content
    updated, result = retain_comparison(
        owner, f, o, admitted_source_sha256=ADMITTED,
        integration_provenance=p("L2", "review"),
    )
    assert result.status is ContrastStatus.MATCH
    assert result.comparison_keys == ("hazard_after",)
    assert result.mismatched_keys == ()
    assert len(updated.memories) == 3
    assert updated.appraisal_dispositions == ()
    assert read_surprise_candidates(
        updated, session_id="session-1", cue_tags=l1.TAGS,
        world_revision=3, admitted_evidence_sha256=ADMITTED,
    ) == ()
    dest = tmp_path / "existing-memory-owner.json"
    save_persistent_cognition(dest, updated)
    assert load_persistent_cognition(dest) == updated
    with pytest.raises(ValueError, match="duplicate memory identity"):
        retain_comparison(
            updated, f, o, admitted_source_sha256=ADMITTED,
            integration_provenance=p("L2", "review"),
        )


def test_surprise_is_review_hint_not_new_learning_or_action_authority():
    f = forecast()
    o = observation(result="near")
    owner = original_owner(f, o)
    updated, result = retain_comparison(
        owner, f, o, admitted_source_sha256=ADMITTED,
        integration_provenance=p("L2", "surprise"),
    )
    assert result.status is ContrastStatus.SURPRISE
    assert result.mismatched_keys == ("hazard_after",)
    hints = read_surprise_candidates(
        updated, session_id="session-1", cue_tags=l1.TAGS,
        world_revision=3, admitted_evidence_sha256=ADMITTED,
    )
    assert len(hints) == 1 and hints[0].startswith("l2:comparison:")
    assert updated.appraisal_dispositions == ()
    for memory in updated.memories:
        assert '"learning_authorized":true' not in memory.content
        assert '"goal_success_attested":true' not in memory.content
    assert read_surprise_candidates(
        updated, session_id="wrong-session", cue_tags=l1.TAGS,
        world_revision=3, admitted_evidence_sha256=ADMITTED,
    ) == ()
    assert read_surprise_candidates(
        updated, session_id="session-1", cue_tags=l1.TAGS,
        world_revision=100, admitted_evidence_sha256=ADMITTED,
    ) == ()


def test_non_executed_counterfactual_remains_unobserved_even_when_other_action_works():
    f = forecast(action="WAIT", forecast_id="wait")
    o = observation(result="far")
    result = compare_forecast(f, o, admitted_source_sha256=ADMITTED)
    assert result.status is ContrastStatus.NOT_OBSERVED
    assert result.observation_memory_id is None
    owner = original_owner(f, o)
    unchanged, result = retain_comparison(
        owner, f, o, admitted_source_sha256=ADMITTED,
        integration_provenance=p("L2", "counterfactual"),
    )
    assert unchanged == owner
    assert result.status is ContrastStatus.NOT_OBSERVED
    assert compare_forecast(f, None, admitted_source_sha256=ADMITTED).status is (
        ContrastStatus.NOT_OBSERVED
    )


@pytest.mark.parametrize(("which", "expected"), [
    ("unknown", ContrastStatus.UNKNOWN),
    ("source_future", ContrastStatus.STALE),
    ("too_old", ContrastStatus.STALE),
    ("unverified_initial", ContrastStatus.UNVERIFIED),
    ("unverified_observed", ContrastStatus.UNVERIFIED),
    ("unresolved_prd", ContrastStatus.UNKNOWN),
    ("missing_key", ContrastStatus.UNKNOWN),
])
def test_qualification_and_absence_do_not_produce_fake_result(which, expected):
    f = forecast(source_band="missing" if which == "unresolved_prd" else "near")
    o = observation(
        unknown=which == "unknown",
        revision=1 if which == "source_future" else
                 150 if which == "too_old" else 2,
    )
    if which == "missing_key":
        o = replace(o, variables=(StateVariable("unrelated", True),))
    admitted = ADMITTED
    if which == "unverified_initial":
        admitted = frozenset({l1.DIGEST_B})
    if which == "unverified_observed":
        admitted = frozenset({l1.DIGEST_A})
    assert compare_forecast(
        f, o, admitted_source_sha256=admitted,
    ).status is expected
    owner = original_owner(f, o)
    new, result = retain_comparison(
        owner, f, o, admitted_source_sha256=admitted,
        integration_provenance=p("L2", "negative"),
    )
    assert new == owner and result.status is expected


def test_strict_value_comparison_does_not_confuse_boolean_with_integer():
    f = forecast()
    o = replace(observation(), variables=(StateVariable("hazard_after", True),))
    assert compare_forecast(
        f, o, admitted_source_sha256=ADMITTED,
    ).status is ContrastStatus.SURPRISE


def test_forecast_requires_existing_action_condition_and_real_prd_result():
    with pytest.raises(ForecastRejected, match="action_ref"):
        forecast(has_condition=False)
    f = forecast()
    forged = replace(f.prediction, status=PredictionStatus.UNDETERMINED)
    with pytest.raises(ForecastRejected, match="forged"):
        replace(f, prediction=forged)
    with pytest.raises(ForecastRejected, match="source SHA256"):
        replace(f, source_sha256="not-a-digest")
    with pytest.raises(ForecastRejected, match="sorted"):
        replace(f, cue_tags=("zombie", "near"))


def test_foreign_session_or_projection_owner_fails_closed():
    f = forecast()
    o = observation()
    with pytest.raises(ForecastRejected, match="foreign World"):
        compare_forecast(
            f, replace(o, qualified=l1.qualified(session="foreign", revision=2)),
            admitted_source_sha256=ADMITTED,
        )
    with pytest.raises(ForecastRejected, match="independent S"):
        replace(
            o, projection_provenance=p(
                "relay_self.prediction.predict_transition", "synthetic-future",
            ),
        )


def test_comparison_rejects_missing_or_tampered_original_memory():
    f = forecast()
    o = observation(result="near")
    only_forecast = retain_forecast(
        l1.identity(), f, integration_provenance=p("L2", "forecast"),
    )
    with pytest.raises(ForecastRejected, match="observed Memory"):
        retain_comparison(
            only_forecast, f, o, admitted_source_sha256=ADMITTED,
            integration_provenance=p("L2", "review"),
        )
    only_observation = retain_observation(
        l1.identity(), o.qualified, integration_provenance=p("S", "obs"),
    )
    with pytest.raises(ForecastRejected, match="prospective forecast"):
        retain_comparison(
            only_observation, f, o, admitted_source_sha256=ADMITTED,
            integration_provenance=p("L2", "review"),
        )
    tampered = l1.identity().retain_memory(
        Memory(f.memory_id, '{"forged":true}', f.source_provenance,
               p("forged", "integrated")),
    )
    tampered = retain_observation(
        tampered, o.qualified, integration_provenance=p("S", "obs"),
    )
    with pytest.raises(ForecastRejected, match="absent or altered"):
        retain_comparison(
            tampered, f, o, admitted_source_sha256=ADMITTED,
            integration_provenance=p("L2", "review"),
        )


def test_untrusted_review_memory_cannot_silently_be_a_successful_hint():
    owner = l1.identity().retain_memory(
        Memory(
            "l2:comparison:forged", '{"schema":"L2_OBSERVED_COMPARISON_V1"}',
            p("bad", "source"), p("bad", "integration"),
        )
    )
    with pytest.raises(ForecastRejected, match="untrusted comparison"):
        read_surprise_candidates(
            owner, session_id="session-1", cue_tags=l1.TAGS,
            world_revision=2, admitted_evidence_sha256=ADMITTED,
        )
