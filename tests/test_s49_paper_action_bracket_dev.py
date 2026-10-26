"""Paper DEV-only world/player bounded arm-to-release proof and corruptions."""
import pytest

from adapters.mineflayer.s49_paper_forward_dash_dev import (
    ForwardDashDevRejected,
    review_paper_action_bracket_dev,
)

ACTION = "s49-native-move-19"
SESSION = "s49-dev"
WORLD = "11111111-1111-1111-1111-111111111111"
PLAYER = "22222222-2222-2222-2222-222222222222"


def rows():
    data = [
        f"S49_DASH_DEV_ARM action_id={ACTION} session_id={SESSION}"
        f" tick=100 world={WORLD} player_uuid={PLAYER}",
    ]
    for k in range(1, 14):
        yes = "true" if k >= 3 else "false"
        data.append(
            f"S49_DASH_DEV_TICK action_id={ACTION} session_id={SESSION}"
            f" tick={100+k} index={k} world={WORLD}"
            f" player_uuid={PLAYER} modifier_applied={yes}"
        )
    data.append(
        f"S49_DASH_DEV_COMPLETE action_id={ACTION} session_id={SESSION}"
        f" reason=OWNER_RELEASE tick=114 world={WORLD} player_uuid={PLAYER}"
        " forward_boost_ticks=11 modifier_applied=false"
    )
    return data


def test_paper_same_world_action_bracket_cannot_claim_cross_host_time():
    record = review_paper_action_bracket_dev(
        "\n".join(rows()), action_id=ACTION, session_id=SESSION,
    )
    assert record["elapsed_callbacks"] == 13
    assert record["boosted_callbacks"] == 11
    assert record["arm_tick"] == 100
    assert record["last_tick"] == 113 and record["release_tick"] == 114
    assert record["original_owner_release"]
    assert record["mineflayer_paper_tick_synchronized"] is False
    assert record["independent_source_attested"] is False


@pytest.mark.parametrize("broken", [
    "missing", "duplicate", "world", "player", "release", "delay",
    "session", "overlap", "negative",
])
def test_paper_gaps_foreign_world_or_bad_owner_release_fail_closed(broken):
    data = rows()
    if broken == "missing":
        data.pop(6)
    elif broken == "duplicate":
        data.insert(6, data[5])
    elif broken == "world":
        data[6] = data[6].replace(WORLD, PLAYER)
    elif broken == "player":
        data[6] = data[6].replace(PLAYER, WORLD)
    elif broken == "release":
        data[-1] = data[-1].replace("OWNER_RELEASE", "TIMEOUT")
    elif broken == "delay":
        data[-1] = data[-1].replace("tick=114", "tick=137")
    elif broken == "session":
        data[6] = data[6].replace("session_id=" + SESSION, "session_id=other")
    elif broken == "overlap":
        data.append(data[0])
    else:
        data[1] = data[1].replace("tick=101", "tick=-1")
    with pytest.raises(ForwardDashDevRejected):
        review_paper_action_bracket_dev(
            "\n".join(data), action_id=ACTION, session_id=SESSION,
        )
