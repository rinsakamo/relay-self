"""Zombie L prediction v0: synthetic typed source, no Paper/Gemma/model calls."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace

import pytest

from adapters.mineflayer.l_zombie_20tick_shadow import (
    HORIZON_TICKS,
    SOURCE_KIND,
    ZombieSourceRejected,
    baseline_forecasts,
    parse_zombie_source,
    report_json,
    review_forecast,
    shadow_forecast,
)

WORLD = "095288da-4414-441b-9cbe-1b35a3a5d1bc"
ZOMBIE = "baf12c70-c261-49f4-a309-ccf0f91c5ae1"
OTHER = "d0755a89-b852-40ed-88c4-07e17255aab7"


def source(*, tick=100, seq=10, x=1.0, y=64, z=2.0, **overrides):
    row = {
        "source_kind": SOURCE_KIND,
        "world_uuid": WORLD, "session_id": "session-demo",
        "entity_uuid": ZOMBIE, "entity_id": 41, "spawn_instance": 1,
        "native_seq": seq, "server_tick": tick,
        "x_m": x, "y_m": y, "z_m": z, "complete_coverage": True,
    }
    row.update(overrides)
    return (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()


def observed(**kwargs):
    raw = source(**kwargs)
    return parse_zombie_source(raw, claimed_sha256=hashlib.sha256(raw).hexdigest())


def trio():
    return (
        observed(tick=100, seq=10, x=0, z=0),
        observed(tick=110, seq=13, x=1, z=0),
        observed(tick=130, seq=15, x=3, z=0),
    )


def test_bounded_source_is_parsed_exact_without_claiming_paper_authenticity():
    p = observed()
    assert p.source_kind == SOURCE_KIND
    assert p.entity_uuid == ZOMBIE
    assert p.entity_id == 41 and p.spawn_instance == 1
    assert p.server_tick == 100 and p.native_seq == 10
    assert not p.externally_authenticated


def test_stationary_vs_velocity_forecast_and_true_horizontal_error():
    a, b, c = trio()
    stationary, velocity = baseline_forecasts(a, b)
    assert stationary.issued_server_tick == 110
    assert stationary.target_server_tick == 130
    assert velocity.target_server_tick-stationary.issued_server_tick == HORIZON_TICKS == 20
    assert (velocity.predicted_x_m, velocity.predicted_z_m) == (3, 0)
    assert (stationary.predicted_x_m, stationary.predicted_z_m) == (1, 0)
    assert review_forecast(velocity, c).horizontal_error_m == 0
    assert review_forecast(stationary, c).horizontal_error_m == 2
    assert not review_forecast(velocity, c).source_authenticated
    assert not review_forecast(velocity, c).learning_admitted
    assert not review_forecast(velocity, c).action_authority
    assert velocity.proposal_sha256 != stationary.proposal_sha256


def test_l2_readonly_point_or_honest_abstention():
    a, b, c = trio()
    model = shadow_forecast(a, b, predicted_x_m=2.5, predicted_z_m=0.5)
    assert model.model_label == "L2_UNADMITTED_SHADOW"
    assert not model.action_authority and not model.learning_authority
    score = review_forecast(model, c)
    assert score.horizontal_error_m == pytest.approx(math.sqrt(0.5))
    assert score.result == "SCORED_OFFLINE_ONLY"
    assert json.loads(report_json(score))["source_authenticated"] is False
    abstain = shadow_forecast(a, b, predicted_x_m=None, predicted_z_m=None)
    assert abstain.forecast_status == "ABSTAIN_UNQUALIFIED"
    assert review_forecast(abstain, c).result == "ABSTAIN_NO_NUMERIC_ERROR"
    assert review_forecast(abstain, c).horizontal_error_m is None
    with pytest.raises(ZombieSourceRejected):
        shadow_forecast(a, b, predicted_x_m=3.0, predicted_z_m=None)


@pytest.mark.parametrize("update", [
    {"entity_id": 42},
    {"entity_uuid": OTHER},
    {"spawn_instance": 2},
    {"world_uuid": "db24b0bc-457a-47d1-9d79-4884fe300d67"},
    {"session_id": "other-session"},
])
def test_no_cross_entity_or_newly_spawned_zombie_identity(update):
    a, b, c = trio()
    changed_before = observed(tick=110, seq=13, x=1, z=0, **update)
    with pytest.raises(ZombieSourceRejected, match="replaced"):
        baseline_forecasts(a, changed_before)
    candidate = shadow_forecast(a, b, predicted_x_m=3, predicted_z_m=0)
    changed_after = observed(tick=130, seq=15, x=3, z=0, **update)
    with pytest.raises(ZombieSourceRejected, match="replaced"):
        review_forecast(candidate, changed_after)


@pytest.mark.parametrize("tick,seq", [
    (110, 14),  # same server tick as last reading
    (109, 14),  # negative World tick order
    (151, 14),  # >40 tick prior gap
    (111, 13),  # native seq not advancing, even if tick does
])
def test_source_native_seq_is_not_world_tick_and_prior_order_must_match(tick, seq):
    a = observed(tick=110, seq=13)
    b = observed(tick=tick, seq=seq, x=1)
    with pytest.raises(ZombieSourceRejected):
        baseline_forecasts(a, b)


@pytest.mark.parametrize("target_tick,source_seq", [
    (129, 15), (131, 15), (130, 11),
])
def test_outcome_must_be_exact_world_tick_not_nearest_packet(target_tick, source_seq):
    a, b, _ = trio()
    candidate = shadow_forecast(a, b, predicted_x_m=3, predicted_z_m=0)
    c = observed(tick=target_tick, seq=source_seq, x=3, z=0)
    with pytest.raises(ZombieSourceRejected, match="not exact"):
        review_forecast(candidate, c)


@pytest.mark.parametrize("field,value", [
    ("complete_coverage", False),
    ("complete_coverage", 1),
    ("source_kind", "MINEFLAYER_SEEN_ENTITY_ONLY"),
    ("entity_uuid", "not-a-uuid"),
    ("world_uuid", "bad-world"),
    ("entity_id", True),
    ("entity_id", -1),
    ("spawn_instance", 0),
    ("server_tick", 1.5),
    ("server_tick", -1),
    ("native_seq", True),
    ("x_m", float("inf")),
    ("y_m", True),
    ("z_m", float("nan")),
    ("session_id", "contains space"),
])
def test_source_invalid_or_missing_authoritative_fields_fail_closed(field, value):
    raw = source(**{field: value})
    with pytest.raises(ZombieSourceRejected):
        parse_zombie_source(raw, claimed_sha256=hashlib.sha256(raw).hexdigest())


def test_original_sha_wrong_spoof_and_extra_fields_fail_closed():
    raw = source()
    with pytest.raises(ZombieSourceRejected, match="SHA"):
        parse_zombie_source(raw, claimed_sha256="0"*64)
    with pytest.raises(ZombieSourceRejected, match="SHA"):
        parse_zombie_source(raw.rstrip(b"\n"), claimed_sha256=hashlib.sha256(raw.rstrip(b"\n")).hexdigest())
    raw_extra = source(unapproved_future_outcome={"x": 42})
    with pytest.raises(ZombieSourceRejected, match="keys"):
        parse_zombie_source(raw_extra, claimed_sha256=hashlib.sha256(raw_extra).hexdigest())
    with pytest.raises(ZombieSourceRejected):
        parse_zombie_source(b"a"*5000+b"\n", claimed_sha256=hashlib.sha256(b"a"*5000+b"\n").hexdigest())


def test_not_tracking_after_teleport_or_stale_double_frame():
    a = observed(tick=100, seq=10, x=0)
    teleport = observed(tick=101, seq=11, x=50)
    with pytest.raises(ZombieSourceRejected, match="teleport"):
        baseline_forecasts(a, teleport)
    with pytest.raises(ZombieSourceRejected):
        baseline_forecasts(a, a)


def test_no_future_inference_if_same_original_prior_as_future():
    a, b, _ = trio()
    f = shadow_forecast(a, b, predicted_x_m=3, predicted_z_m=0)
    fake_future = replace(b, server_tick=130)
    with pytest.raises(ZombieSourceRejected, match="not exact"):
        review_forecast(f, fake_future)


def test_reject_nan_unbounded_or_partial_shadow_forecast():
    a, b, _ = trio()
    for x, z in (
        (float("nan"), 0), (float("inf"), 0), (10000, 1),
        (True, 1), (None, 1), (1, None),
    ):
        with pytest.raises(ZombieSourceRejected):
            shadow_forecast(a, b, predicted_x_m=x, predicted_z_m=z)


def test_world_tick_must_be_explicit_and_not_host_sequence():
    raw = source()
    modified = json.loads(raw)
    modified.pop("server_tick")
    fake = (json.dumps(modified) + "\n").encode()
    with pytest.raises(ZombieSourceRejected, match="keys"):
        parse_zombie_source(fake, claimed_sha256=hashlib.sha256(fake).hexdigest())


def test_source_uuid_cannot_be_replaced_by_mineflayer_entity_integer():
    raw = source(entity_uuid="41")
    with pytest.raises(ZombieSourceRejected):
        parse_zombie_source(raw, claimed_sha256=hashlib.sha256(raw).hexdigest())
