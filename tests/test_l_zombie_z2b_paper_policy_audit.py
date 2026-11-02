"""Z2b original Paper policy projection tests, SYNTHETIC only."""
from __future__ import annotations

import hashlib

import pytest

from test_l_zombie_z2a_prospective_audit import fixture as cheap_fixture
from test_l_zombie_z2b_policy_contract import frozen
from tools.l_zombie_paper_original_audit import PaperZombieSourceRejected
from tools.l_zombie_z2b_paper_policy_audit import audit_prepared_l2_world
from tools.l_zombie_z2b_prepare_gemma import render_activated_plugin_config

WORLD = "095288da-4414-441b-9cbe-1b35a3a5d1bc"
ZOMBIE = "baf12c70-c261-49f4-a309-ccf0f91c5ae1"


def packet_line(prepared=None, **changes):
    prepared = prepared or frozen()
    entries = {
        "marker": "z1-1", "session": "s1",
        "world": WORLD, "entity_uuid": ZOMBIE,
        "entity_id": "42", "issued_tick": "1010", "target_tick": "1030",
        "policy_sha256": prepared.policy_sha256, "strategy": prepared.strategy,
        "speed": ("0.110000000000" if prepared.strategy == "TARGET_APPROACH" else "none"),
        "player_x": "6.000000000000", "player_z": "0.000000000000",
        "predicted_x": ("3.200000000000" if prepared.strategy == "TARGET_APPROACH" else "null"),
        "predicted_z": ("0.000000000000" if prepared.strategy == "TARGET_APPROACH" else "null"),
    }
    entries.update(changes)
    return (
        "[12:00:00 INFO]: L_ZOMBIE_PREPARED_L2_FREEZE_V3 "
        + " ".join(f"{key}={val}" for key, val in entries.items())
    )


def original(prepared=None, *, at=13, double=False, **changes):
    lines = cheap_fixture().decode().splitlines()
    row = packet_line(prepared, **changes)
    lines.insert(at, row)
    if double:
        lines.insert(at + 1, row)
    return ("\n".join(lines) + "\n").encode()


def audit(raw, prepared=None):
    prepared = prepared or frozen()
    return audit_prepared_l2_world(
        raw, sha256=hashlib.sha256(raw).hexdigest(),
        marker="z1-1", session="s1", prepared=prepared,
    )


def test_prepared_paper_freeze_is_before_outcome_and_scored_against_same_cheap():
    p = frozen()
    result = audit(original(p), p)
    assert result["issued_tick"] == 1010
    assert result["target_tick"] == 1030
    assert result["frozen_before_next_tick"]
    assert result["prepared_policy_error_m"] == pytest.approx(.2)
    assert result["cheap_stationary_error_m"] == pytest.approx(2)
    assert result["cheap_velocity_error_m"] == 0
    assert result["prepared_policy_owner"] == "EARLIER_EPOCH_MODEL_PREPARED_SHADOW"
    assert result["model_live_in_world_calls"] == 0
    assert result["model_original_wire_cryptographically_joined_by_this_parser"] is False
    assert result["actual_real_gguf_mapping_verified_by_this_parser"] is False
    assert not result["l0_promotion"]


@pytest.mark.parametrize("params", [
    {"at": 11},
    {"at": 14},
    {"at": 33},
    {"double": True},
    {"policy_sha256": "f"*64},
    {"strategy": "STATIONARY"},
    {"speed": "0.120000000000"},
    {"predicted_x": "3.500000000000"},
    {"predicted_x": "null"},
    {"player_x": "NaN"},
    {"issued_tick": "1011"},
    {"target_tick": "1031"},
    {"entity_uuid": "d0755a89-b852-40ed-88c4-07e17255aab7"},
])
def test_late_duplicate_or_wrong_prepared_policy_never_scores(params):
    at = params.pop("at", 13)
    double = params.pop("double", False)
    with pytest.raises(PaperZombieSourceRejected):
        audit(original(at=at, double=double, **params))


def test_missing_prepared_line_is_not_retrospectively_invented():
    with pytest.raises(PaperZombieSourceRejected):
        audit(cheap_fixture())


def test_paper_abstain_has_no_invented_error():
    policy = frozen(strategy="ABSTAIN", speed_m_per_tick=None)
    data = original(
        policy, speed="none", predicted_x="null", predicted_z="null",
    )
    result = audit(data, policy)
    assert result["prepared_policy_error_m"] is None
    assert result["model_prepared_xz_m"] is None
    assert result["classification"] == "Z2B_PAPER_PREPARED_L2_POLICY_ABSTAIN_SOURCE_ONLY"


def test_prepared_plugin_config_requires_prior_cheap_and_exact_model_packet():
    disabled = (
        "dev-enabled: true\n"
        "zombie-tick-readonly-dev: true\n"
        "zombie-prospective-cheap-dev: true\n"
        'zombie-prepared-l2-shadow-dev: false\n'
        'zombie-prepared-l2-strategy: "ABSTAIN"\n'
        'zombie-prepared-l2-speed-m-per-tick: "none"\n'
        'zombie-prepared-l2-policy-sha256: "none"\n'
    )
    p = frozen()
    enabled = render_activated_plugin_config(
        disabled_plugin_config=disabled, prepared_policy=p,
    )
    assert "zombie-prepared-l2-shadow-dev: true" in enabled
    assert f'zombie-prepared-l2-policy-sha256: "{p.policy_sha256}"' in enabled
    assert 'zombie-prepared-l2-strategy: "TARGET_APPROACH"' in enabled
    assert 'zombie-prepared-l2-speed-m-per-tick: "0.110000000000"' in enabled
    assert "zombie-prospective-cheap-dev: true" in enabled
    with pytest.raises(ValueError):
        render_activated_plugin_config(
            disabled_plugin_config=disabled.replace("zombie-prospective-cheap-dev: true",""),
            prepared_policy=p,
        )
    assert p.no_action_authority and p.no_learning_admission
