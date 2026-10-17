"""Source-only V6 Minecraft server gametime / summon atomic function gates."""
import hashlib
import json

import pytest

from adapters.mineflayer.v6_atomic_fixture import (
    ATOMIC_LINES,
    INSTALL_LINES,
    MAX_SCORE,
    OBJECTIVE,
    READBACK_LINES,
    AtomicV6Rejected,
    plan,
    proposed_datapack_files,
    review_reported_scores,
)

FUNCTION_PATH = "data/relayself_v6/function/atomic_food.mcfunction"


def _sha():
    return hashlib.sha256(proposed_datapack_files()[FUNCTION_PATH]).hexdigest()


def test_v6_atomic_pack_is_fixed_1_21_8_and_does_not_write_to_world(tmp_path):
    before = list(tmp_path.iterdir())
    files = proposed_datapack_files()
    assert set(files) == {
        "pack.mcmeta",
        "data/relayself_v6/function/install.mcfunction",
        FUNCTION_PATH,
    }
    assert all(type(b) is bytes and b.endswith(b"\n") for b in files.values())
    metadata = json.loads(files["pack.mcmeta"])
    assert metadata["pack"]["pack_format"] == 81
    assert b"scoreboard objectives add rs_v6_tick dummy" in files[
        "data/relayself_v6/function/install.mcfunction"
    ]
    assert all(not command.startswith("/") for command in INSTALL_LINES + ATOMIC_LINES)
    assert all("time set" not in command for command in INSTALL_LINES + ATOMIC_LINES)
    assert all("minecraft:" not in command for command in READBACK_LINES)
    assert OBJECTIVE == "rs_v6_tick"
    assert INSTALL_LINES[1] == "scoreboard players add #attempt rs_v6_tick 0"
    assert not any("players set #attempt" in row for row in INSTALL_LINES)
    assert ATOMIC_LINES[0] == "scoreboard players add #attempt rs_v6_tick 1"
    assert all("matches 1 run " in line for line in ATOMIC_LINES[1:8])
    assert ATOMIC_LINES[4].endswith(
        "execute store result score #before rs_v6_tick run time query gametime"
    )
    assert "run summon minecraft:item" in ATOMIC_LINES[5]
    assert ATOMIC_LINES[6].endswith(
        "execute store result score #after rs_v6_tick run time query gametime"
    )
    assert "matches 2.. run say RELAYSELF_V6_REPEAT_BLOCKED" in ATOMIC_LINES[-1]
    assert len(READBACK_LINES) == 4
    assert READBACK_LINES[0] == "scoreboard players get #attempt rs_v6_tick"
    assert list(tmp_path.iterdir()) == before


def test_v6_atomic_plan_is_separate_from_golden_and_never_grants_world():
    data = plan()
    assert data["classification"] == "S_V6_ATOMIC_FOOD_SOURCE_DESIGN_ONLY"
    assert data["schema"] == "S_V6_ATOMIC_FOOD_FUNCTION_SOURCE_V2_SINGLE_ATTEMPT"
    assert data["single_use_guard"] == "PERSISTENT_NONRESETTING_ATTEMPT_SCORE_ONE"
    assert data["repeated_attempt_invalidates_source"] is True
    assert data["repeated_invocation_can_resummon"] is False
    assert data["target_minecraft_version"] == "1.21.8"
    assert data["datapack_format"] == 81
    assert data["datapack_files_sha256"][FUNCTION_PATH] == _sha()
    assert data["preregistered_operator_command"] == (
        "execute at RelaySelf run function relayself_v6:atomic_food"
    )
    assert data["datapack_files_installed"] is False
    assert data["server_command_originals_attested"] is False
    assert data["exact_command_effect_tick_originals_attested"] is False
    assert data["matched_world_start_attested"] is False
    assert data["physical_execution_authorized"] is False
    assert data["science_g3"] == "NO_GO"


def test_v6_good_claim_still_is_never_original_proof():
    sha = _sha()
    result = review_reported_scores(
        before=601, after=601, summon_succeeded=1, attempt_count=1,
        source_function_sha256=sha, expected_function_sha256=sha,
    )
    assert result["claimed_server_gametime"] == 601
    assert result["claimed_summon_success"] == 1
    assert result["claimed_atomic_function_attempt_count"] == 1
    assert result["replay_originals_independently_attested"] is False
    assert result["classification"] == "S_V6_ATOMIC_SERVER_SCORE_CLAIM_REVIEW_ONLY"
    for k in (
        "original_server_console_bytes_attested",
        "real_server_function_loaded_attested",
        "server_effect_age_authenticity_attested",
        "world_start_matched_attested",
        "native_packet_time_correlated",
        "m0_tick_matched",
        "physical_execution_authorized",
    ):
        assert result[k] is False
    assert result["science_g3"] == "NO_GO"


@pytest.mark.parametrize(("before", "after", "success", "sha"), [
    (601, 602, 1, "same"),  # Different real game ticks: no silent alignment.
    (601, 601, 0, "same"),  # Summon failure not a food opportunity.
    (601, 601, True, "same"),  # Python bool is NOT valid scoreboard int.
    (601, 601, 2, "same"),
    (True, 601, 1, "same"),
    (-1, -1, 1, "same"),
    (MAX_SCORE + 1, MAX_SCORE + 1, 1, "same"),
    (1.0, 1.0, 1, "same"),
    (601, 601, 1, "foreign"),
])
def test_v6_claims_fail_closed(before, after, success, sha):
    expected = _sha()
    with pytest.raises(AtomicV6Rejected):
        review_reported_scores(
            before=before, after=after, summon_succeeded=success,
            attempt_count=1,
            source_function_sha256=expected if sha == "same" else "0" * 64,
            expected_function_sha256=expected,
        )


def test_v6_no_implicit_host_or_world_action_on_module_plan(capsys):
    from adapters.mineflayer import v6_atomic_fixture

    assert v6_atomic_fixture.plan() == plan()
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("attempt_count", [0, 2, 3, True, 1.0, -1, "1"])
def test_v6_reexecution_or_forged_attempt_count_rejected(attempt_count):
    checksum = _sha()
    with pytest.raises(AtomicV6Rejected, match="exactly one"):
        review_reported_scores(
            before=601, after=601, summon_succeeded=1,
            attempt_count=attempt_count,
            source_function_sha256=checksum,
            expected_function_sha256=checksum,
        )


def test_v6_attempt_lock_controls_all_effects_and_keeps_prior_original_scores():
    # Pure *source* review; real Minecraft scoreboard effect unqualified.
    assert ATOMIC_LINES[0] == "scoreboard players add #attempt rs_v6_tick 1"
    for line in ATOMIC_LINES[1:8]:
        assert line.startswith("execute if score #attempt rs_v6_tick matches 1 run ")
    assert sum("run summon minecraft:item" in line for line in ATOMIC_LINES) == 1
    assert not any("players set #attempt" in line for line in INSTALL_LINES)
    assert not any("players set #attempt" in line for line in ATOMIC_LINES)
    assert not any("time set" in line for line in ATOMIC_LINES)
