"""MP7 real Paper packed-ice input and original receipt negative controls."""
from __future__ import annotations

import hashlib

import pytest

from adapters.mineflayer.self_body_s50_l1_ice_floor import (
    attest_ice_original,
    ice_command,
    verify_ice_config,
)
from adapters.mineflayer.self_body_s50_l1_paper_dispatch import ForecastDispatchRejected

M = "s49-action"
W = "source-world"
S = "source-subject"


def test_ice_control_has_one_concrete_5x5_mode():
    assert ice_command(M, "PACKED_ICE_5X5") == (
        "relaydevicefloor s49-action PACKED_ICE_5X5"
    )
    for marker, mode in ((M, "BLUE_ICE"), (M, "SLOWNESS_II"), ("bad\nstop", "PACKED_ICE_5X5")):
        with pytest.raises(ForecastDispatchRejected):
            ice_command(marker, mode)


def test_config_pinned_exclusive_and_default_off(tmp_path):
    p = tmp_path / "active.yml"
    text = (
        "dev-enabled: true\ns50-tick-meter-dev: true\n"
        "s50-input-witness-dev: true\ns50-paper-local-forecast-dev: true\n"
        "s50-forecast-gate-dev: false\ns50-changed-body-condition-dev: false\n"
        "s50-ice-floor-dev: true\n"
    )

    def require(v, expected):
        p.write_text(v)
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if expected:
            verify_ice_config(p, sha)
        else:
            with pytest.raises(ForecastDispatchRejected):
                verify_ice_config(p, sha)

    require(text, True)
    with pytest.raises(ForecastDispatchRejected):
        verify_ice_config(p, "0"*64)
    for invalid in (
        text.replace("s50-ice-floor-dev: true", "s50-ice-floor-dev: false"),
        text.replace("s50-changed-body-condition-dev: false",
                     "s50-changed-body-condition-dev: true"),
        text.replace("s50-paper-local-forecast-dev: true",
                     "s50-paper-local-forecast-dev: false"),
        text + "s50-ice-floor-dev: true\n",
    ):
        require(invalid, False)


def original(*, mode="PACKED_ICE_5X5", material="PACKED_ICE", count="25",
             world=W, subject=S, status="REAL_PAPER_WORLD_BLOCK_INTERVENTION_PRE_S49_ACTION"):
    return (
        f"[INFO] S50_DEV_ICE_FLOOR_APPLIED marker_id={M} world={world} "
        f"subject_uuid={subject} before_action_world_tick=243 "
        f"mode={mode} original_material=GRASS_BLOCK target_material={material} "
        f"blocks_verified={count} center_x=3 floor_y=-61 center_z=3 "
        f"status={status}\n"
    ).encode()


def audit(raw):
    return attest_ice_original(raw, marker=M, world=W, subject_uuid=S)


def test_physical_original_authenticated():
    d = audit(original())
    assert d["blocks_verified"] == "25" and d["original_material"] == "GRASS_BLOCK"


@pytest.mark.parametrize("raw", [
    b"relaydevicefloor s49-action PACKED_ICE_5X5\n",
    original(world="wrong"),
    original(subject="wrong"),
    original(mode="BLUE_ICE"),
    original(material="STONE"),
    original(count="24"),
    original(status="FAKE"),
    original()+original(),
    b"",
])
def test_fake_receipt_rejected(raw):
    with pytest.raises(ForecastDispatchRejected):
        audit(raw)
