"""M1 sensed-resource interface is an OFFLINE model, never an action policy."""
from dataclasses import replace

import pytest

from experiments.metabolism_m01_minecraft import M01Profile, WorldTickSample, begin
from experiments.metabolism_resource_projection import (
    Candidate,
    VisibleResourceQuote,
    quote_candidate,
    visible_costs,
)
from experiments.metabolism_sensed_viability import assess_sensed_costs
from experiments.metabolism_viability import (
    BodyState,
    EnergyObservation,
    Interoception,
    observe_energy,
)


@pytest.fixture
def context():
    profile = M01Profile(
        profile_id="m-sensed-test",
        capacity=20,
        initial_energy=8,
        basal_per_world_tick=0.1,
        movement_per_block=0.3,
        food_energy=(("cooked_beef", 5.0),),
    )
    body = begin(profile, WorldTickSample("session", 100, (0.0, 64.0, 0.0)))
    candidate = Candidate(
        "goal", "MOVE", distance_blocks=5, nominal_blocks_per_tick=0.5
    )
    return profile, body, candidate


def _view(profile, body, candidate, sensor, true_energy):
    quote = quote_candidate(profile, replace(body, energy=true_energy), candidate)
    reading = observe_energy(BodyState(true_energy, tick=100), sensor)
    return visible_costs("session", reading, (quote,))


def test_same_world_high_vs_low_sensed_energy_changes_model_affordability(context):
    profile, body, candidate = context
    sensor = Interoception(gain=1.0, quantum=1)
    high_view = _view(profile, body, candidate, sensor, 8.0)
    low_view = _view(profile, body, candidate, sensor, 1.0)
    high = assess_sensed_costs(profile, high_view, sensor, noise_bound=0)
    low = assess_sensed_costs(profile, low_view, sensor, noise_bound=0)
    assert high.assessments[0].estimated_energy_cost == pytest.approx(2.5)
    assert low.assessments[0].estimated_energy_cost == pytest.approx(2.5)
    assert high.assessments[0].affordability == "MODEL_AFFORDABLE"
    assert low.assessments[0].affordability == "MODEL_INSUFFICIENT"
    assert high.model_energy_lower > 2.5
    assert low.model_energy_upper < 2.5


def test_blind_interoception_is_cheap_null_for_both_body_states(context):
    profile, body, candidate = context
    sensor = Interoception(gain=0.0, bias=3.0)
    high = _view(profile, body, candidate, sensor, 8)
    low = _view(profile, body, candidate, sensor, 1)
    assert high == low
    for value in (high, low):
        result = assess_sensed_costs(profile, value, sensor, noise_bound=0)
        assert result.assessments[0].affordability == "UNKNOWN"
        assert result.model_energy_lower is None


def test_even_perfectly_known_cost_is_unknown_without_noise_bound(context):
    profile, body, candidate = context
    sensor = Interoception()
    view = _view(profile, body, candidate, sensor, 8)
    result = assess_sensed_costs(profile, view, sensor)
    assert result.assessments[0].affordability == "UNKNOWN"
    assert result.assessments[0].estimated_energy_cost == pytest.approx(2.5)
    assert result.source_scope == "OFFLINE_MODEL_CONDITIONAL_NOT_WORLD_ATTESTED"


def test_boundary_of_quantized_sensor_is_ambiguous(context):
    profile, body, candidate = context
    sensor = Interoception(quantum=2)
    read = visible_costs(
        "session", EnergyObservation(100, 2.0),
        (quote_candidate(profile, body, candidate),),
    )
    assessment = assess_sensed_costs(profile, read, sensor, noise_bound=0)
    assert assessment.assessments[0].affordability == "MODEL_AMBIGUOUS"
    assert assessment.model_energy_lower < 2.5 < assessment.model_energy_upper


def test_bounded_sensor_noise_changes_certainty_without_utility(context):
    profile, body, candidate = context
    sensor = Interoception(quantum=1)
    view = _view(profile, body, candidate, sensor, 4.0)
    certain = assess_sensed_costs(profile, view, sensor, noise_bound=0)
    noisy = assess_sensed_costs(profile, view, sensor, noise_bound=1.5)
    assert certain.assessments[0].affordability == "MODEL_AFFORDABLE"
    assert noisy.assessments[0].affordability == "MODEL_AMBIGUOUS"


def test_out_of_capacity_sensor_value_is_not_an_energy_certificate(context):
    profile, body, candidate = context
    sensor = Interoception()
    view = visible_costs("session", EnergyObservation(100, 1000),
                         (quote_candidate(profile, body, candidate),))
    result = assess_sensed_costs(profile, view, sensor, noise_bound=0)
    assert result.model_energy_upper is None
    assert result.assessments[0].affordability == "UNKNOWN"


def test_unknown_route_cannot_become_cheap_zero_cost(context):
    profile, body, _ = context
    sensor = Interoception()
    quote = quote_candidate(profile, body, Candidate("unknown", "MOVE"))
    view = visible_costs("session", EnergyObservation(100, 8), (quote,))
    result = assess_sensed_costs(profile, view, sensor, noise_bound=0)
    assert result.assessments[0].affordability == "UNKNOWN"
    assert result.assessments[0].estimated_energy_cost is None


def test_truth_never_enters_sensed_function_when_reading_is_same(context):
    profile, body, candidate = context
    sensor = Interoception(quantum=20)
    view8 = _view(profile, body, candidate, sensor, 8)
    view6 = _view(profile, body, candidate, sensor, 6)
    assert view8 == view6
    r8 = assess_sensed_costs(profile, view8, sensor, noise_bound=0)
    r6 = assess_sensed_costs(profile, view6, sensor, noise_bound=0)
    assert r8 == r6
    assert not hasattr(r8, "true_energy")


def test_wait_cost_remains_nonzero_and_no_future_meal_credit(context):
    profile, body, _ = context
    sensor = Interoception()
    wait = quote_candidate(profile, body, Candidate("wait", "WAIT", wait_ticks=40))
    view = visible_costs("session", EnergyObservation(100, 2), (wait,))
    result = assess_sensed_costs(profile, view, sensor, noise_bound=0)
    assert result.assessments[0].estimated_energy_cost == pytest.approx(4.0)
    assert result.assessments[0].affordability == "MODEL_INSUFFICIENT"


@pytest.mark.parametrize("invalid", [
    lambda v: replace(v, owner_world_tick=True),
    lambda v: replace(v, source_scope="NATIVE_AUTHORITATIVE"),
    lambda v: replace(v, quotes=(VisibleResourceQuote("x", 2, float("nan"), "x"),)),
    lambda v: replace(v, quotes=(VisibleResourceQuote("x", 2, -1, "x"),)),
    lambda v: replace(v, quotes=(VisibleResourceQuote("x", 2, None, "x"),)),
    lambda v: replace(v, quotes=(VisibleResourceQuote("x", None, 0, "x"),)),
    lambda v: replace(v, quotes=(VisibleResourceQuote("x", 2, 1, "x"),
                                 VisibleResourceQuote("x", 3, 2, "x"))),
    lambda v: replace(v, session_id=""),
    lambda v: replace(v, observed_energy_reading=float("inf")),
])
def test_foreign_or_invalid_public_inputs_fail_closed(context, invalid):
    profile, body, candidate = context
    view = _view(profile, body, candidate, Interoception(), 8)
    with pytest.raises(ValueError):
        assess_sensed_costs(profile, invalid(view), Interoception(), noise_bound=0)


@pytest.mark.parametrize("bad", [-1, True, float("nan"), float("inf")])
def test_invalid_noise_bounds_reject(context, bad):
    profile, body, candidate = context
    view = _view(profile, body, candidate, Interoception(), 8)
    with pytest.raises(ValueError):
        assess_sensed_costs(profile, view, Interoception(), noise_bound=bad)


def test_no_automatic_gait_or_action_selection_api(context):
    profile, body, candidate = context
    view = _view(profile, body, candidate, Interoception(), 8)
    result = assess_sensed_costs(profile, view, Interoception(), noise_bound=0)
    assert not hasattr(result, "selected_action")
    assert not hasattr(result, "gait")
    assert not hasattr(result, "goal")
    assert not hasattr(result, "reward")
    assert not hasattr(result.assessments[0], "survival_value")
