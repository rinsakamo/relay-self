"""Quantization sensitivity: never equate rounded fatigue with certain fatigue."""
from __future__ import annotations

import math

import pytest

from adapters.mineflayer.s49_p1_paper_dev import (
    S49P1SourceRejected,
    inspect_paper_tick_source,
)
from test_bug0_s49_p1_paper_dev import NONCE, native, sample_log
from tools.bug0_p1_sensor_threshold import (
    P1SensorThresholdRejected,
    sensitivity,
)
from tools.bug0_s49_p1_prospective_sensor import _prefix


def test_previous_real_world_near_threshold_is_not_robust_rest():
    # Parent real #41844805744 predecision original P1 experimental state
    # .045999... quantizes to .05. Exact raw state is *not* used by S49.
    measured = 0.045999999999999874
    observed = round(measured / 0.01) * 0.01
    assert math.isclose(observed, 0.05)
    choice = sensitivity(float(observed))
    assert choice.nominal_rest is True
    assert choice.uncertainty_guard_rest is False
    assert choice.safety_margin_rest is False
    assert choice.abstain_due_to_quantization is True
    assert choice.safety_margin_suppressed_rest is True
    assert math.isclose(choice.admissible_lower, 0.045)


@pytest.mark.parametrize(("reading", "nominal", "guard", "margin"), (
    (0.0, False, False, False),
    (0.04, False, False, False),
    (0.05, True, False, False),
    (0.06, True, True, False),
    (0.07, True, True, False),
    (0.08, True, True, True),
    (0.12, True, True, True),
))
def test_quantization_interval_and_three_policy_sensitivity(
    reading, nominal, guard, margin,
):
    c = sensitivity(float(reading))
    assert (c.nominal_rest, c.uncertainty_guard_rest, c.safety_margin_rest) == (
        nominal, guard, margin,
    )
    assert c.admissible_lower >= 0
    assert c.admissible_upper <= 1
    assert c.admissible_lower <= c.reading <= c.admissible_upper


@pytest.mark.parametrize("kwargs", (
    {"reading": float("nan")},
    {"reading": float("inf")},
    {"reading": -0.01},
    {"reading": 1.1},
    {"reading": 0.05, "quantum": 0.0},
    {"reading": 0.05, "quantum": float("nan")},
    {"reading": 0.05, "threshold": -1.0},
    {"reading": 0.05, "margin": -0.1},
    {"reading": 0.05, "margin": float("inf")},
    {"reading": True},
))
def test_invalid_sensor_never_produces_qualified_choice(kwargs):
    with pytest.raises(P1SensorThresholdRejected):
        sensitivity(**kwargs)


def _wait_source():
    source = sample_log()
    source = source.replace(
        f"S49P1_REST nonce={NONCE} world=",
        f"S49P1_CHOICE nonce={NONCE} selected=WAIT world=",
    )
    return source


def _wait_native():
    scope = native()
    scope["rest_intent_selected"] = False
    scope["rest_choice"] = {
        "selected": "WAIT", "preferred": None, "action_issued": False,
    }
    return scope


def test_original_wait_intent_and_stillness_have_separate_native_label():
    result = inspect_paper_tick_source(
        _wait_source(), nonce=NONCE, native_report=_wait_native(),
        expected_choice="WAIT", marker_style="choice",
    )
    assert result["paper_rest_marker_tick"] is None
    assert result["paper_choice_marker_tick"] == 115
    assert result["paper_selected_intent"] == "WAIT"
    assert result["rest_candidate_quiet_source_ticks"] == list(range(117, 125))
    assert result["source_full_tick_activity_independently_attested"] is False


@pytest.mark.parametrize("change", (
    "legacy-rest", "wrong-choice", "stale-native", "extra-rest",
    "extra-choice", "source-gap", "foreign-session",
))
def test_wait_cannot_relabel_rest_or_unauthorized_native_action(change):
    source = _wait_source()
    scope = _wait_native()
    if change == "legacy-rest":
        source = sample_log()
    elif change == "wrong-choice":
        source = source.replace("selected=WAIT", "selected=REST")
    elif change == "stale-native":
        scope["rest_intent_selected"] = True
    elif change == "extra-rest":
        source += "\n" + next(
            x for x in sample_log().splitlines() if "S49P1_REST " in x
        )
    elif change == "extra-choice":
        source += "\n" + next(
            x for x in source.splitlines() if "S49P1_CHOICE " in x
        )
    elif change == "source-gap":
        source = "\n".join(
            x for x in source.splitlines()
            if "S49P1_TICK " not in x or "tick=120 " not in x
        )
    else:
        scope["rest_choice"]["selected"] = "REST"
    with pytest.raises(S49P1SourceRejected):
        inspect_paper_tick_source(
            source, nonce=NONCE, native_report=scope,
            expected_choice="WAIT", marker_style="choice",
        )


def test_predecision_reader_rejects_future_choice_marker():
    source = _wait_source()
    source = "\n".join(
        x for x in source.splitlines() if "S49P1_STOP " not in x
    )
    with pytest.raises(S49P1SourceRejected):
        _prefix(source, nonce=NONCE)
