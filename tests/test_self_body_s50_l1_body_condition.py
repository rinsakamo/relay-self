"""MP6: separate experimenter-created real body change, source-bound DEV-only."""
from __future__ import annotations

import hashlib

import pytest

from adapters.mineflayer.self_body_s50_l1_body_condition import (
    attest_condition_original,
    condition_command,
    verify_condition_config,
)
from adapters.mineflayer.self_body_s50_l1_paper_dispatch import ForecastDispatchRejected

MARKER = "s49-action-uuid"
WORLD = "0dcf8a5d-b8da-4863-bc0d-641d0abc1260"
SUBJECT = "eea169cf-a0d7-3c89-ae20-3d11ecc29d8e"


def test_only_one_explicit_physical_effect_allowed():
    assert condition_command(MARKER, "SLOWNESS_II") == (
        "relaydevcondition s49-action-uuid SLOWNESS_II"
    )
    for marker, mode in (
        (MARKER, "SLOWNESS_I"),
        (MARKER, "SPEED_II"),
        (MARKER, ""),
        ("bad\nstop", "SLOWNESS_II"),
        ("", "SLOWNESS_II"),
    ):
        with pytest.raises(ForecastDispatchRejected):
            condition_command(marker, mode)


def test_pin_and_unique_physical_config(tmp_path):
    path = tmp_path / "config.yml"
    raw = (
        "dev-enabled: true\ns50-tick-meter-dev: true\n"
        "s50-input-witness-dev: true\ns50-paper-local-forecast-dev: true\n"
        "s50-forecast-gate-dev: false\ns50-changed-body-condition-dev: true\n"
    )

    def verify(data, should_pass):
        path.write_text(data)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if should_pass:
            verify_condition_config(path, digest)
        else:
            with pytest.raises(ForecastDispatchRejected):
                verify_condition_config(path, digest)

    verify(raw, True)
    with pytest.raises(ForecastDispatchRejected):
        verify_condition_config(path, "b" * 64)
    verify(raw.replace("s50-changed-body-condition-dev: true",
                       "s50-changed-body-condition-dev: false"), False)
    verify(raw + "s50-changed-body-condition-dev: true\n", False)
    verify(raw.replace("s50-paper-local-forecast-dev: true",
                       "s50-paper-local-forecast-dev: false"), False)
    verify(raw.replace("s50-forecast-gate-dev: false",
                       "s50-forecast-gate-dev: true"), False)


def receipt(*, world=WORLD, subject=SUBJECT,
            mode="SLOWNESS_II", amplifier="1",
            status="EXPERIMENTER_PHYSICAL_INTERVENTION_PRE_S49_ACTION",
            ticks="400"):
    return (
        f"[12:00 INFO] S50_DEV_BODY_CONDITION_APPLIED marker_id={MARKER} "
        f"world={world} subject_uuid={subject} before_action_world_tick=245 "
        f"condition={mode} paper_effect=SLOWNESS amplifier={amplifier} "
        f"effect_ticks={ticks} status={status}\n"
    ).encode()


def verify_receipt(raw):
    return attest_condition_original(
        raw, marker=MARKER,
        paper_world_uuid=WORLD, subject_uuid=SUBJECT,
    )


def test_only_genuine_paper_body_effect_source_permitted():
    result = verify_receipt(receipt())
    assert result["condition"] == "SLOWNESS_II"
    assert result["amplifier"] == "1"


@pytest.mark.parametrize("raw", [
    b"",
    b"relaydevcondition s49-action-uuid SLOWNESS_II\n",
    receipt(world="different"),
    receipt(subject="different"),
    receipt(mode="SLOWNESS_I"),
    receipt(amplifier="0"),
    receipt(ticks="100"),
    receipt(status="FAKE_APPLIED"),
    receipt() + receipt(),
])
def test_fake_or_ambiguous_world_body_rejected(raw):
    with pytest.raises(ForecastDispatchRejected):
        verify_receipt(raw)
