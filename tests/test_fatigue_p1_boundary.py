"""P1-B strict evaluator seam tests, not a World source-authentication claim."""

from dataclasses import replace

import pytest

from experiments.fatigue_p1 import FatigueProfile, FatigueRejected, FatigueSensor, initial_state
from experiments.fatigue_p1_boundary import (
    BodyPreflight,
    P1BoundaryRejected,
    SActivityRequest,
    SourceBoundTick,
    preflight,
    reconcile,
    sensed_for_self,
)


def request(state, activity, **kwargs):
    return SActivityRequest(state.session_id, state.world_tick, activity, **kwargs)


def source(prepared, **overrides):
    q = prepared.request
    values = dict(
        session_id=q.session_id, world_tick=prepared.admitted_world_tick,
        activity=q.activity, world_source_ref=f"world:{prepared.admitted_world_tick}",
    )
    if q.activity in ("MOVE", "FIGHT"):
        values.update(action_ref=q.action_ref, action_effect_ref=f"effect:{q.action_ref}")
    if q.activity == "REST":
        values.update(rest_choice_ref=q.rest_choice_ref, rest_interval_ref=f"idle:{q.rest_choice_ref}")
    values.update(overrides)
    return SourceBoundTick(**values)


def test_off_reuses_existing_unmodified_one_block_action():
    p = FatigueProfile()
    s = initial_state(p, "run")
    b = preflight(p, s, request(s, "MOVE", requested_blocks=1, action_ref="a1"))
    assert b.allowed_blocks == 1 and not b.constrained
    result = reconcile(p, s, b, source(b, observed_blocks=1))
    assert result.transition.after.fatigue == 0
    assert result.transition.capacity_after.max_move_blocks_per_world_tick == 1


def test_fatigue_cap_is_prospective_and_does_not_authorize_action():
    p = FatigueProfile(enabled=True, initial=1)
    s = initial_state(p, "run")
    b = preflight(p, s, request(s, "MOVE", requested_blocks=1, action_ref="S49-a"))
    assert b.allowed_blocks == pytest.approx(.3) and b.constrained
    assert not hasattr(b, "authorized") and not hasattr(b, "issued")
    done = reconcile(p, s, b, source(b, observed_blocks=.24, blocked=True))
    assert done.transition.after.fatigue == 1
    with pytest.raises(P1BoundaryRejected, match="exceeded"):
        reconcile(p, s, b, source(b, observed_blocks=1))
    # Original overrun must be preserved by S/R and classified invalid, never clipped.


def test_partial_blocked_movement_billed_only_actual_motion():
    p = FatigueProfile(enabled=True)
    s = initial_state(p, "run")
    b = preflight(p, s, request(s, "MOVE", requested_blocks=1, action_ref="step"))
    hit = reconcile(p, s, b, source(b, observed_blocks=.2, blocked=True))
    assert hit.transition.accumulated == pytest.approx(.008)
    b2 = preflight(p, hit.transition.after,
                   request(hit.transition.after, "MOVE", requested_blocks=.5, action_ref="step2"))
    zero = reconcile(p, hit.transition.after, b2,
                     source(b2, observed_blocks=0, blocked=True))
    assert zero.transition.accumulated == 0
    assert zero.transition.after.fatigue == hit.transition.after.fatigue


def test_rest_and_wait_are_distinct_source_observed_world_ticks():
    p = FatigueProfile(enabled=True, initial=.8)
    s = initial_state(p, "solo")
    w = preflight(p, s, request(s, "WAIT"))
    waited = reconcile(p, s, w, source(w))
    assert waited.transition.after.fatigue == .8
    s2 = waited.transition.after
    b = preflight(p, s2, request(s2, "REST", rest_choice_ref="S-rest-decision"))
    rest = reconcile(p, s2, b, source(b))
    assert rest.transition.after.fatigue == pytest.approx(.7)
    assert rest.transition.after.world_tick == s.world_tick + 2
    assert rest.transition.recovered == pytest.approx(.1)
    assert not hasattr(rest.transition.after, "energy")


def test_fight_impossible_at_high_fatigue_but_rest_not_selected_for_agent():
    p = FatigueProfile(enabled=True, initial=1)
    s = initial_state(p, "solo")
    with pytest.raises(P1BoundaryRejected, match="unavailable"):
        preflight(p, s, request(s, "FIGHT", action_ref="strike"))
    assert preflight(p, s, request(s, "WAIT")).request.activity == "WAIT"
    assert preflight(p, s, request(s, "REST", rest_choice_ref="choice")).request.activity == "REST"


def test_evaluator_projection_never_releases_true_fatigue_or_capability():
    p = FatigueProfile(enabled=True, initial=.87)
    s = initial_state(p, "solo")
    view = sensed_for_self(p, s, FatigueSensor(gain=0, bias=2))
    assert vars(view) == {"world_tick": 0, "reading": 2.0}
    assert view.reading != s.fatigue


@pytest.mark.parametrize("bad", [
    {"action_ref": "fake"},
    {"rest_choice_ref": "fake"},
    {"requested_blocks": 0.1},
])
def test_wait_rejects_stealth_action_or_rest(bad):
    p = FatigueProfile(enabled=True)
    s = initial_state(p, "solo")
    with pytest.raises(P1BoundaryRejected):
        preflight(p, s, request(s, "WAIT", **bad))


@pytest.mark.parametrize("bad", [
    {"action_ref": "stealth"},
    {"requested_blocks": .1},
    {"rest_choice_ref": ""},
])
def test_rest_rejects_stealth_action_and_missing_decision(bad):
    p = FatigueProfile(enabled=True)
    s = initial_state(p, "solo")
    with pytest.raises(P1BoundaryRejected):
        preflight(p, s, request(s, "REST", **bad))


@pytest.mark.parametrize("kind,kw", [
    ("MOVE", {"requested_blocks": 0, "action_ref": "a"}),
    ("MOVE", {"requested_blocks": 1.1, "action_ref": "a"}),
    ("MOVE", {"requested_blocks": float("nan"), "action_ref": "a"}),
    ("MOVE", {"requested_blocks": True, "action_ref": "a"}),
    ("MOVE", {"requested_blocks": .2}),
    ("FIGHT", {"action_ref": "a", "requested_blocks": 1}),
    ("FIGHT", {}),
])
def test_invalid_proposals_reject(kind, kw):
    p = FatigueProfile(enabled=True)
    s = initial_state(p, "solo")
    with pytest.raises(P1BoundaryRejected):
        preflight(p, s, request(s, kind, **kw))


@pytest.mark.parametrize("bad", [
    {"session_id": "other"},
    {"world_tick": 2},
    {"activity": "WAIT"},
    {"world_source_ref": ""},
    {"action_ref": "other"},
    {"action_effect_ref": None},
    {"rest_interval_ref": "forged-rest"},
    {"observed_fight_events": 1},
    {"observed_blocks": -1},
    {"observed_blocks": 2},
    {"observed_blocks": float("nan")},
])
def test_reconcile_movement_source_is_strict(bad):
    p = FatigueProfile(enabled=True)
    s = initial_state(p, "solo")
    b = preflight(p, s, request(s, "MOVE", requested_blocks=1, action_ref="a"))
    with pytest.raises(P1BoundaryRejected):
        reconcile(p, s, b, source(b, observed_blocks=.5, **bad) if "observed_blocks" not in bad else source(b, **bad))


@pytest.mark.parametrize("bad", [
    {"rest_interval_ref": None},
    {"rest_choice_ref": "other"},
    {"action_ref": "sneaky"},
    {"action_effect_ref": "fake"},
    {"action_outcome_ref": "fake"},
    {"observed_blocks": .01},
    {"blocked": True},
])
def test_rest_source_requires_choice_and_no_world_action(bad):
    p = FatigueProfile(enabled=True)
    s = initial_state(p, "solo")
    b = preflight(p, s, request(s, "REST", rest_choice_ref="rest1"))
    with pytest.raises(P1BoundaryRejected):
        reconcile(p, s, b, source(b, **bad))


def test_previous_preflight_cannot_be_reused_or_edited():
    p = FatigueProfile(enabled=True, initial=.5)
    s = initial_state(p, "solo")
    b = preflight(p, s, request(s, "REST", rest_choice_ref="r"))
    after = reconcile(p, s, b, source(b)).transition.after
    with pytest.raises(P1BoundaryRejected):
        reconcile(p, after, b, source(b))
    with pytest.raises(P1BoundaryRejected):
        reconcile(p, s, replace(b, allowed_blocks=1), source(b))
    with pytest.raises(FatigueRejected):
        reconcile(replace(p, initial=.4), s, b, source(b))


def test_explicit_movement_tolerance_is_zero_by_default_and_bounded():
    p = FatigueProfile(enabled=True)
    s = initial_state(p, "solo")
    b = preflight(p, s, request(s, "MOVE", requested_blocks=1, action_ref="a"))
    with pytest.raises(P1BoundaryRejected):
        reconcile(p, s, b, source(b, observed_blocks=1.02))
    # Only an explicitly fixed tolerance allows an overrun, still billed as actual.
    x = reconcile(p, s, b, source(b, observed_blocks=1.02),
                  movement_tolerance_blocks=.03)
    assert x.transition.accumulated == pytest.approx(1.02 * .04)
    with pytest.raises(P1BoundaryRejected):
        reconcile(p, s, b, source(b), movement_tolerance_blocks=float("inf"))


def test_same_issued_action_multiple_world_ticks_not_fake_terminal_outcome():
    p = FatigueProfile(enabled=True)
    s = initial_state(p, "solo", world_tick=100)
    b1 = preflight(p, s, request(s, "MOVE", requested_blocks=1, action_ref="issued-1"))
    first = reconcile(p, s, b1, source(b1, observed_blocks=.2, action_effect_ref="native-101"))
    assert first.source.action_outcome_ref is None
    s2 = first.transition.after
    b2 = preflight(p, s2, request(s2, "MOVE", requested_blocks=.8, action_ref="issued-1"))
    second = reconcile(p, s2, b2, source(b2, observed_blocks=.6,
                        action_effect_ref="native-102", action_outcome_ref="closed-S16-102"))
    assert second.transition.after.world_tick == 102
    assert second.transition.after.fatigue == pytest.approx(.8 * .04)
    assert second.source.action_outcome_ref == "closed-S16-102"
    # This is just a synthetic correlation; only S can attest Action state.


def test_invalid_terminal_reference_and_tolerance_above_fixed_ceiling_reject():
    p = FatigueProfile(enabled=True)
    s = initial_state(p, "solo")
    b = preflight(p, s, request(s, "MOVE", requested_blocks=1, action_ref="issued"))
    with pytest.raises(P1BoundaryRejected):
        reconcile(p, s, b, source(b, action_outcome_ref=""))
    with pytest.raises(P1BoundaryRejected):
        reconcile(p, s, b, source(b, observed_blocks=1.07),
                  movement_tolerance_blocks=.07)