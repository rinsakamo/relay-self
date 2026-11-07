"""D7-B: Paper main-thread per-tick evidence, NOT a server-effective S49 STOP grant."""
from __future__ import annotations

import pytest

from tools.bug0_d7_paper_server_tick_post import (
    D7PaperSourceRejected,
    audit_paper_ticks,
)

WORLD = "deafbeef-0060-4eaf-8d15-123456789abc"
PLAYER = "faded00d-0001-4fce-9999-123456789abc"
SESSION = "original-one-world"
OFF = dict.fromkeys(
    ("forward", "back", "left", "right", "jump", "sprint", "sneak"), "false"
)


def original():
    report = {
        "session_id": SESSION,
        "self_eat": False,
        "d7_eat_grant_issued": False,
        "d6_original_s49_move_actions": [{"action_id": "original-move"}],
    }
    prior = {
        "status": "PASS_DEV", "session_id": SESSION,
        "paper_world_uuid": WORLD, "no_eat_after_move": True,
    }
    client = {
        "source_session": SESSION, "body_physically_stopped_proven": False,
        "original_EAT_issued": False,
        "source_scope": "S50_NATIVE_CLIENT_HELD_CONTROLS_ONLY",
    }
    return report, prior, client


def log_source():
    header = (
        "RSELF_D7_PAPER_READY source=PAPER_SERVER_MAIN_THREAD_V1"
        " interval_ticks=1 max_rows=8192 mode=read_only eat_authority=none"
    )
    rows = []
    for i in range(15):
        tokens = {
            "source": "PAPER_SERVER_MAIN_THREAD_V1",
            "ordinal": str(i + 1),
            "tick": str(100 + i),
            "player": PLAYER, "world": WORLD,
            "x": "1.0", "y": "64.0", "z": "2.0",
            "vx": "0.0", "vy": "0.0", "vz": "0.0",
            "ground": "true", **OFF,
        }
        rows.append("RSELF_D7_PAPER_TICK "
                    + " ".join(f"{k}={v}" for k, v in tokens.items()))
    footer = ("RSELF_D7_PAPER_STOP total_ticks=15 input_events=0"
              " truncated=false eat_authority=none")
    return [header, *rows, footer]


def test_even_contiguous_true_server_idle_is_not_stop_certificate():
    report, prior, client = original()
    result = audit_paper_ticks(
        "\n".join(log_source()), report, prior, client
    )
    assert result["gapfree_Paper_tick_rows"] == 15
    assert result["longest_sampled_quiet_Paper_tick_streak"] == 14
    assert result["body_physically_stopped_proven"] is False
    assert result["authenticated_S_owner_EAT_resume_grant"] is False
    assert result["original_EAT_issued"] is False
    assert result["server_effective_original_S49_clear_tick"] == (
        "NOT_CAUSALLY_ATTESTED"
    )


@pytest.mark.parametrize("mutation", [
    "gap", "wrong_world", "wrong_player", "duplicate_ordinal",
    "nonfinite", "bad_input", "truncated", "no_stop",
    "missing_ready", "false_count", "bad_source",
    "foreign_session", "paper_unqualified", "client_false_stop",
    "eat_grant", "eat_issued",
])
def test_invalid_source_or_authority_fails_closed(mutation):
    report, prior, client = original()
    rows = log_source()
    if mutation == "gap":
        rows[4] = rows[4].replace("tick=103", "tick=105")
    elif mutation == "wrong_world":
        rows[3] = rows[3].replace(WORLD, "another-world")
    elif mutation == "wrong_player":
        rows[3] = rows[3].replace(PLAYER, "foreign-player")
    elif mutation == "duplicate_ordinal":
        rows[4] = rows[4].replace("ordinal=4", "ordinal=3")
    elif mutation == "nonfinite":
        rows[4] = rows[4].replace("vx=0.0", "vx=NaN")
    elif mutation == "bad_input":
        rows[4] = rows[4].replace("sneak=false", "sneak=UNKNOWN")
    elif mutation == "truncated":
        rows.insert(-1, "RSELF_D7_PAPER_TRUNCATED limit=8192")
    elif mutation == "no_stop":
        rows.pop()
    elif mutation == "missing_ready":
        rows.pop(0)
    elif mutation == "false_count":
        rows[-1] = rows[-1].replace("total_ticks=15", "total_ticks=14")
    elif mutation == "bad_source":
        rows[4] = rows[4].replace(
            "source=PAPER_SERVER_MAIN_THREAD_V1", "source=FAKE"
        )
    elif mutation == "foreign_session":
        report["session_id"] = "another-session"
    elif mutation == "paper_unqualified":
        prior["status"] = "FAIL"
    elif mutation == "client_false_stop":
        client["body_physically_stopped_proven"] = True
    elif mutation == "eat_grant":
        report["d7_eat_grant_issued"] = True
    elif mutation == "eat_issued":
        report["self_eat"] = True
    with pytest.raises(D7PaperSourceRejected):
        audit_paper_ticks("\n".join(rows), report, prior, client)


def test_active_input_is_observed_not_relabelled_as_stop():
    report, prior, client = original()
    rows = log_source()
    rows[5] = rows[5].replace("back=false", "back=true")
    actual = audit_paper_ticks("\n".join(rows), report, prior, client)
    assert actual["server_input_active_ticks"] == 1
    assert actual["authenticated_S_owner_EAT_resume_grant"] is False


def test_nonzero_velocity_and_drift_reset_quiet_streak():
    report, prior, client = original()
    rows = log_source()
    rows[8] = rows[8].replace("x=1.0", "x=2.0")
    rows[8] = rows[8].replace("vx=0.0", "vx=0.25")
    actual = audit_paper_ticks("\n".join(rows), report, prior, client)
    assert actual["longest_sampled_quiet_Paper_tick_streak"] < 14
    assert actual["body_physically_stopped_proven"] is False
