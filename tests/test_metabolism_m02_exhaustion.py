"""M0.2 opt-in offline checks: no physical Minecraft starts or energy rewards."""
from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from experiments.metabolism_m02_exhaustion import (
    EVENT_REASONS,
    NATIVE_REQUIRED,
    UNITS,
    M02Rejected,
    bill_event,
    bill_world_tick,
    cost,
    load_profile,
    paper_event_cost,
    parse_profile,
    start_audit,
)

PROFILE_FILE = (
    Path(__file__).resolve().parents[1] / "experiments/config/m02_relay_ecology_v1.json"
)


@pytest.fixture
def profile():
    return load_profile(PROFILE_FILE)


def mutate(profile, name, **overrides):
    rows = dict(profile.rates)
    rows[name] = replace(rows[name], **overrides)
    return replace(profile, rates=tuple(sorted(rows.items())))


def test_profile_explicit_complete_standards_and_identity(profile):
    assert set(dict(profile.rates)) == set(UNITS)
    assert "BASAL" not in EVENT_REASONS
    assert "COGNITION" not in EVENT_REASONS
    assert len(EVENT_REASONS) == 14
    assert profile.minecraft_version == "1.21.8"
    assert profile.calibration_status == "candidate_uncalibrated"
    assert profile.standard_food == "cooked_beef"
    assert profile.rule("BASAL").standard == 0.001
    assert profile.rule("WALK").standard == 0.01
    assert profile.rule("SPRINT").standard == 0.1
    assert profile.rule("REGEN").standard == "native"
    assert profile.rule("COGNITION").enabled is False
    assert len(profile.sha256) == 64
    assert profile.sha256 == parse_profile(profile.canonical_dict()).sha256


def test_same_formula_applies_to_basal_walk_sprint_and_attack(profile):
    assert cost(profile, "BASAL", 10) == pytest.approx(0.01)
    assert cost(profile, "WALK", 2.0) == pytest.approx(0.02)
    assert cost(profile, "SPRINT", 2.0) == pytest.approx(0.2)
    assert cost(profile, "ATTACK", 2) == pytest.approx(0.2)
    changed = mutate(profile, "WALK", multiplier=1.5, additional=0.002)
    assert cost(changed, "WALK", 2.0) == pytest.approx(0.034)
    assert changed.sha256 != profile.sha256
    basal = mutate(profile, "BASAL", multiplier=2, additional=0.002)
    assert cost(basal, "BASAL", 10) == pytest.approx(0.04)


def test_walking_sprinting_and_swimming_events_are_one_centimeter(profile):
    assert paper_event_cost(
        profile, "WALK", native_event_exhaustion=0, distance_centimeters=1
    ) == pytest.approx(0.0001)
    assert paper_event_cost(
        profile, "SPRINT", native_event_exhaustion=0.001, distance_centimeters=1
    ) == pytest.approx(0.001)
    assert paper_event_cost(
        profile, "SWIM", native_event_exhaustion=0.0001, distance_centimeters=1
    ) == pytest.approx(0.0001)
    assert paper_event_cost(
        profile, "CROUCH", native_event_exhaustion=0, distance_centimeters=1
    ) == 0.0


def test_non_movement_events_use_native_exhaustion_as_replacement_not_addition(profile):
    assert paper_event_cost(
        profile, "ATTACK", native_event_exhaustion=0.1
    ) == pytest.approx(0.1)
    assert paper_event_cost(
        profile, "JUMP_SPRINT", native_event_exhaustion=0.2
    ) == pytest.approx(0.2)
    assert paper_event_cost(
        profile, "BLOCK_MINED", native_event_exhaustion=0.005
    ) == pytest.approx(0.005)
    assert paper_event_cost(
        profile, "REGEN", native_event_exhaustion=6.0
    ) == pytest.approx(6.0)


@pytest.mark.parametrize("kind", sorted(NATIVE_REQUIRED))
def test_variable_native_standard_is_explicit_passthrough(profile, kind):
    rule = profile.rule(kind)
    assert rule.standard == "native"
    assert rule.multiplier == 1
    assert rule.additional == 0
    move = kind in ("WALK_ON_WATER", "WALK_UNDERWATER")
    args = {"distance_centimeters": 1} if move else {}
    assert paper_event_cost(
        profile, kind, native_event_exhaustion=0.037, **args
    ) == pytest.approx(0.037)
    raised = mutate(profile, kind, multiplier=2, additional=0.02)
    assert paper_event_cost(
        raised, kind, native_event_exhaustion=0.037, **args
    ) == pytest.approx(0.0742 if move else 0.094)


def test_cognition_is_off_and_can_be_explicitly_enabled(profile):
    assert cost(profile, "COGNITION", 100000) == 0.0
    assert cost(profile, "BASAL", 10) == pytest.approx(0.01)
    enabled = mutate(profile, "COGNITION", enabled=True, additional=0.0001)
    assert cost(enabled, "COGNITION", 10) == pytest.approx(0.001)
    with pytest.raises(M02Rejected, match="requires a real"):
        mutate(profile, "COGNITION", enabled=True)


def test_audit_world_time_not_number_of_decisions(profile):
    s = start_audit(profile, "session-a", 99)
    first = bill_world_tick(profile, s, 100)
    assert first.total_exhaustion == pytest.approx(0.001)
    second = bill_world_tick(profile, first, 101)
    assert second.total_exhaustion == pytest.approx(0.002)
    assert second.total_exhaustion == bill_world_tick(profile, first, 101).total_exhaustion
    with pytest.raises(M02Rejected):
        bill_world_tick(profile, first, 100)
    with pytest.raises(M02Rejected):
        bill_world_tick(profile, first, 102)


def test_event_idempotency_and_session_fences(profile):
    s = bill_world_tick(profile, start_audit(profile, "own", 9), 10)
    evt = bill_event(
        profile, s, session_id="own", world_tick=10, event_id="move-1",
        reason="WALK", native_event_exhaustion=0, distance_centimeters=100,
    )
    assert evt.total_exhaustion == pytest.approx(0.011)
    with pytest.raises(M02Rejected, match="duplicate"):
        bill_event(
            profile, evt, session_id="own", world_tick=10, event_id="move-1",
            reason="WALK", native_event_exhaustion=0, distance_centimeters=100,
        )
    with pytest.raises(M02Rejected, match="session"):
        bill_event(
            profile, evt, session_id="foreign", world_tick=10, event_id="move-2",
            reason="JUMP", native_event_exhaustion=0.05,
        )
    with pytest.raises(M02Rejected, match="World tick"):
        bill_event(
            profile, evt, session_id="own", world_tick=11, event_id="jump",
            reason="JUMP", native_event_exhaustion=0.05,
        )
    different_profile = mutate(profile, "BASAL", multiplier=2)
    with pytest.raises(M02Rejected, match="profile"):
        bill_world_tick(different_profile, evt, 11)


@pytest.mark.parametrize("kind,quantity", [
    ("BASAL", 1.5), ("JUMP", 0.5), ("BASAL", True),
    ("WALK", -1), ("WALK", math.nan), ("WALK", math.inf),
])
def test_illegal_units_and_numeric_input_reject(profile, kind, quantity):
    with pytest.raises(M02Rejected):
        cost(profile, kind, quantity)


@pytest.mark.parametrize("reason,extra", [
    ("WALK", {}), ("REGEN", {"healed_hp": 1}), ("JUMP", {"distance_centimeters": 1}),
    ("ATTACK", {"healed_hp": 1}), ("REGEN", {"healed_hp": 0}),
    ("BASAL", {}), ("NOT_AN_EVENT", {}),
])
def test_paper_source_requires_unambiguous_units(profile, reason, extra):
    with pytest.raises(M02Rejected):
        paper_event_cost(profile, reason, native_event_exhaustion=0, **extra)


def test_native_event_cannot_be_called_without_source(profile):
    with pytest.raises(M02Rejected):
        cost(profile, "HUNGER_EFFECT", 1)
    with pytest.raises(M02Rejected):
        cost(profile, "HUNGER_EFFECT", 2, native_event_exhaustion=0.1)
    with pytest.raises(M02Rejected):
        paper_event_cost(profile, "UNKNOWN", native_event_exhaustion=float("nan"))


def test_missing_or_invalid_profile_refused_without_silent_fallback(profile):
    data = profile.canonical_dict()
    del data["actions"]["WALK"]
    with pytest.raises(M02Rejected):
        parse_profile(data)
    data = profile.canonical_dict()
    data["actions"]["WALK"]["unit"] = "event"
    with pytest.raises(M02Rejected):
        parse_profile(data)
    data = profile.canonical_dict()
    data["actions"]["BASAL"]["standard"] = "native"
    with pytest.raises(M02Rejected):
        parse_profile(data)
    data = profile.canonical_dict()
    data["actions"]["ATTACK"]["enabled"] = False
    with pytest.raises(M02Rejected):
        parse_profile(data)
    data = profile.canonical_dict()
    data["actions"]["WALK"]["additional"] = -1
    with pytest.raises(M02Rejected):
        parse_profile(data)
    data = profile.canonical_dict()
    data["actions"]["WALK"]["multiplier"] = float("inf")
    with pytest.raises(M02Rejected):
        parse_profile(data)


def test_profile_loader_denies_duplicate_json_keys_and_nan(tmp_path):
    duplicate = tmp_path / "bad.json"
    duplicate.write_text('{"version":"M0.2","version":"M0.2"}', encoding="utf-8")
    with pytest.raises(M02Rejected, match="duplicate"):
        load_profile(duplicate)
    duplicate.write_text('{"version":NaN}', encoding="utf-8")
    with pytest.raises(M02Rejected):
        load_profile(duplicate)
    with pytest.raises(M02Rejected):
        load_profile(tmp_path / "missing.json")


def test_canonical_standard_values_and_full_configuration_roundtrip(profile, tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(profile.canonical_dict()), encoding="utf-8")
    assert load_profile(path).sha256 == profile.sha256
    after = profile.canonical_dict()
    after["actions"]["WALK"]["additional"] = 0.01
    with pytest.raises(M02Rejected):
        parse_profile({**after, "version": "M0.3"})
