"""Only one post-WAIT native probe produces matched SelfWorld/SelfBody DEV."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_postwait_native_dev import (
    compose_postwait_native_self_world_dev,
)
from adapters.mineflayer.s49_p1_self_body_dev import (
    MODEL,
    compose_s49_p1_postwait_native_dev,
)
from relay_self.self_body import BodyOrigin
from test_s49_p1_self_body_dev import correlated_next_native


def test_same_next_cognition_epoch_preserves_real_native_vs_p1_model(monkeypatch):
    handoff, reviewed, last, native, request = correlated_next_native(monkeypatch)
    body, next_readback = compose_s49_p1_postwait_native_dev(
        handoff, reviewed, last, native, expected_request_id=request,
    )
    world_readback = compose_postwait_native_self_world_dev(body, native)
    assert world_readback["status"] == "DEV_NEXT_COGNITION_WORLD_BODY_SOURCE_JOINED"
    assert world_readback["native_seq"] == next_readback["native_seq"]
    assert world_readback["native_request_id"] == next_readback["native_request_id"]
    assert world_readback["native_source_ref"] == next_readback["native_source_ref"]
    assert world_readback["world_body_same_epoch"] is True
    assert world_readback["world_body_same_object"] is True
    assert world_readback["p1_model_sensor_pct"] == next_readback[
        "p1_dev_hypothesis_sensor_pct"
    ]
    assert body.observed("food").origin is BodyOrigin.OBSERVATION
    assert body.observed("p1_fatigue").origin is BodyOrigin.UNKNOWN
    assert body.sensed("p1_fatigue_sensor").origin is BodyOrigin.UNKNOWN
    assert body.hypothetical(MODEL, "p1_phase").value == "after-wait"
    assert world_readback["p1_source_kind"] == (
        "SELF_BODY_HYPOTHESIS_NOT_NATIVE_OBSERVATION"
    )
    assert world_readback["native_paper_exact_tick_joined"] is False
    assert world_readback["extra_protocol_receivers"] == 0
    assert world_readback["extra_action_issuers"] == 0
    assert world_readback["next_l0_consumed"] is False


@pytest.mark.parametrize("bad", [
    "wrong_session", "wrong_request", "wrong_seq", "altered_food",
    "lost_observation", "lost_hypothesis", "foreign_selfid",
])
def test_cannot_join_foreign_or_fabricated_native_world(monkeypatch, bad):
    handoff, reviewed, last, native, request = correlated_next_native(monkeypatch)
    body, _ = compose_s49_p1_postwait_native_dev(
        handoff, reviewed, last, native, expected_request_id=request,
    )
    if bad == "wrong_session":
        native = replace(native, session_id="foreign-session")
    elif bad == "wrong_request":
        native = replace(native, request_id="some-other-probe")
    elif bad == "wrong_seq":
        native = replace(native, seq=native.seq + 1)
    elif bad == "altered_food":
        native = replace(native, snapshot=replace(
            native.snapshot, food=native.snapshot.food - 1,
        ))
    elif bad == "lost_observation":
        body = replace(body, observation=None)
    elif bad == "lost_hypothesis":
        body = replace(body, hypotheses=())
    elif bad == "foreign_selfid":
        body = replace(body, self_id=None)
    with pytest.raises(BoundaryRejected):
        compose_postwait_native_self_world_dev(body, native)
