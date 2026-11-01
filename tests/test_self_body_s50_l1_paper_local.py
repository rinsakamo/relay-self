"""MP5: synthetic Paper prearm contract only; no Minecraft or physical claims."""
from __future__ import annotations

import hashlib

import pytest

from adapters.mineflayer.self_body_s50_l1_paper_dispatch import ForecastDispatchRejected
from adapters.mineflayer.self_body_s50_l1_paper_local import (
    check_local_paper_config,
    confirm_original_local_arm,
    local_model_command,
)

MARKER = "s49-action-uuid"
WORLD = "0dcf8a5d-b8da-4863-bc0d-641d0abc1260"
SUBJECT = "eea169cf-a0d7-3c89-ae20-3d11ecc29d8e"
SHA = "a" * 64
SLOPE = 0.20331885786720635


def test_model_arm_is_single_console_command_no_per_tick_channel():
    assert local_model_command(MARKER, SLOPE, SHA) == (
        f"relaydevlocalmodel {MARKER} 0.20331885786720635 {SHA}"
    )


@pytest.mark.parametrize("change", [
    ("bad\nstop", SLOPE, SHA),
    ("", SLOPE, SHA),
    (MARKER, float("nan"), SHA),
    (MARKER, float("inf"), SHA),
    (MARKER, -1., SHA),
    (MARKER, 65., SHA),
    (MARKER, True, SHA),
    (MARKER, SLOPE, "b"),
])
def test_injection_and_malformed_model_refused(change):
    with pytest.raises(ForecastDispatchRejected):
        local_model_command(*change)


def test_unique_sha_pinned_config_prior_to_any_world(tmp_path):
    config = tmp_path / "config.yml"
    original = (
        "dev-enabled: true\ns50-tick-meter-dev: true\n"
        "s50-input-witness-dev: true\ns50-forecast-gate-dev: false\n"
        "s50-paper-local-forecast-dev: true\n"
    )

    def write_verify(source: str, allowed: bool):
        config.write_text(source)
        digest = hashlib.sha256(config.read_bytes()).hexdigest()
        if allowed:
            check_local_paper_config(config, digest)
        else:
            with pytest.raises(ForecastDispatchRejected):
                check_local_paper_config(config, digest)

    write_verify(original, True)
    with pytest.raises(ForecastDispatchRejected):
        check_local_paper_config(config, "f" * 64)
    for key, value in (
        ("dev-enabled", "false"),
        ("s50-tick-meter-dev", "false"),
        ("s50-input-witness-dev", "false"),
        ("s50-paper-local-forecast-dev", "false"),
        ("s50-forecast-gate-dev", "true"),
    ):
        modified = original.replace(f"{key}: {'false' if key == 's50-forecast-gate-dev' else 'true'}",
                                    f"{key}: {value}")
        write_verify(modified, False)
    write_verify(original + "s50-paper-local-forecast-dev: true\n", False)
    write_verify(original.replace("s50-paper-local-forecast-dev: true\n", ""), False)


def original_arm(*, world=WORLD, subject=SUBJECT, slope=SLOPE,
                 digest=SHA, status="FROZEN_PRE_S49_ACTION") -> bytes:
    return (
        f"[12:00 INFO] [RelayMetabolismDev] S50_DEV_LOCAL_MODEL_ARM "
        f"marker_id={MARKER} world={world} subject_uuid={subject} "
        f"world_full_time=400 slope={slope!r} "
        f"ticket_sha256={digest} status={status}\n"
    ).encode()


def confirm(raw):
    return confirm_original_local_arm(
        raw, marker=MARKER, paper_world_uuid=WORLD,
        subject_uuid=SUBJECT, ticket_sha256=SHA, slope=SLOPE,
    )


def test_paper_original_arms_before_native_action():
    assert confirm(original_arm()) is None
    assert confirm(b"paper starting\n" + original_arm()) is None


@pytest.mark.parametrize("invalid", [
    b"",
    original_arm(world="foreign"),
    original_arm(subject="foreign"),
    original_arm(slope=0.1),
    original_arm(digest="b" * 64),
    original_arm(status="REJECTED"),
    original_arm() + original_arm(),
    b"relaydevlocalmodel s49-action-uuid 0.2\n",
])
def test_false_identity_duplicate_or_command_echo_never_authorizes_action(invalid):
    with pytest.raises(ForecastDispatchRejected):
        confirm(invalid)
