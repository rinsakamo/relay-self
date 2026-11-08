"""D14 tick horizon negative controls. All Paper/native sources here are synthetic."""

from __future__ import annotations

from copy import deepcopy

import pytest

from tools.bug0_d14_tick_horizon_post import (
    D14TickHorizonAuditRejected,
    audit_closed_original_action_failure,
    audit_horizon,
)
from tools.bug0_d14_tick_horizon_world import (
    D14HorizonRejected,
    _field,
    parse_endurance_marker,
    qualified_early_terminal,
)

WORLD = "11111111-1111-4111-8111-111111111111"
ZOMBIE = "22222222-2222-4222-8222-222222222222"


def make_sources():
    start_tick = 500
    start = (
        f"RSELF_ENDURANCE_START world={WORLD} start_tick={start_tick} "
        "stop_tick=10500 horizon_ticks=10000 "
        "natural_600tick_respawns_unchanged=true"
    )
    samples = [
        f"RSELF_ENDURANCE_SAMPLE world={WORLD} tick={start_tick + 200*i} "
        f"elapsed_ticks={200*i} generation=3 living={ZOMBIE} pending_due_tick=-1"
        for i in range(1, 50)
    ]
    end = (
        f"RSELF_ENDURANCE_LIMIT world={WORLD} start_tick=500 "
        "end_tick=10500 observed_tick=10500 elapsed_ticks=10000 "
        f"generation=3 living={ZOMBIE} "
        "stop_new_spawns=true no_forced_death=true"
    )
    report = {
        "status": "PASS_DEV", "node_exit": 0, "java_exit": 0,
        "cleanup_done": True, "real_model_calls": 0, "learning_updated": False,
        "session_id": "same-original-native-session",
        "d12_third_rearm": {"session_id": "same-original-native-session"},
        "d14_tick_horizon_proven": True,
        "d14_tick_horizon_optin": True,
        "d14_tick_horizon_requested": 10000,
        "d14_self_continuous_action_policy_enabled": False,
        "d14_additional_native_actions": 0,
        "d14_l2_calls": 0, "d14_learning_updates": 0,
        "d14_start_action_count": 7,
        "d14_heartbeat_observations": [],
        "d14_tick_horizon": {
            "world_uuid": WORLD, "world_ticks": 10000, "end_tick": 10500,
            "original_s49_action_count": 7,
            "native_new_actions_issued_by_horizon": 0,
            "source_original_start": start, "source_original_end": end,
        },
    }
    parent = {
        "status": "PASS_DEV",
        "classification": "D12_TWO_TRUE_MEALS_THIRD_REAL_WORLD_INTENT_REARM_PASS",
    }
    return report, "\n".join([start, *samples, end]), parent


def test_paper_world_limit_is_not_skill_or_survival_claim():
    r, log, parent = make_sources()
    original = deepcopy(r)
    out = audit_horizon(r, log, parent)
    assert out["status"] == "PASS_DEV"
    assert out["world_ticks"] == 10000
    assert out["paper_heartbeat_count"] == 49
    assert out["parent_d12_status"] == "PASS_DEV"
    assert out["third_and_later_S49_action_loop"] == "NOT_IMPLEMENTED"
    assert out["Self_autonomous_long_survival"] is False
    assert out["learning_updates"] == 0
    assert r == original


def test_previous_natural_zero_is_valid_world_observation():
    r, log, _ = make_sources()
    out = audit_horizon(r, log, {
        "status": "NOT_EXERCISED",
        "classification": "D12_THIRD_REARM_NOT_EXERCISED_TRUE_ZERO_FOOD",
    })
    assert out["status"] == "PASS_DEV"
    assert out["parent_d12_status"] == "NOT_EXERCISED"


@pytest.mark.parametrize(("key", "bad"), [
    ("d14_tick_horizon_proven", False),
    ("d14_self_continuous_action_policy_enabled", True),
    ("d14_additional_native_actions", 1),
    ("d14_start_action_count", 8),
    ("d14_l2_calls", 1),
    ("d14_learning_updates", 1),
    ("node_exit", 1),
    ("learning_updated", True),
])
def test_reject_forged_stopping_or_claims(key, bad):
    r, log, parent = make_sources()
    r[key] = bad
    with pytest.raises(D14TickHorizonAuditRejected):
        audit_horizon(r, log, parent)


@pytest.mark.parametrize(("needle", "replacement"), [
    ("stop_tick=10500", "stop_tick=10501"),
    ("observed_tick=10500", "observed_tick=10499"),
    ("elapsed_ticks=10000", "elapsed_ticks=9999"),
    ("stop_new_spawns=true", "stop_new_spawns=false"),
    ("tick=2500", "tick=2501"),
    ("world=" + WORLD, "world=66666666-6666-4666-8666-666666666666"),
])
def test_bad_world_markers_rejected(needle, replacement):
    r, log, parent = make_sources()
    if "stop_tick" in needle or "observed_tick" in needle or "stop_new_spawns" in needle:
        if "stop_tick" in needle:
            log = log.replace(needle, replacement)
        else:
            log = log.replace(needle, replacement)
    else:
        log = log.replace(needle, replacement, 1)
    with pytest.raises(D14TickHorizonAuditRejected):
        audit_horizon(r, log, parent)


def test_duplicate_world_limit_or_missing_heartbeat_rejected():
    r, log, parent = make_sources()
    lines = log.splitlines()
    with pytest.raises(D14TickHorizonAuditRejected):
        audit_horizon(r, log + "\n" + lines[-1], parent)
    with pytest.raises(D14TickHorizonAuditRejected):
        audit_horizon(r, "\n".join([lines[0], *lines[2:]]), parent)


def test_no_post_limit_respawn_allowed():
    r, log, parent = make_sources()
    spawn = f"RSELF_RESPAWN_SPAWN world={WORLD} generation=4 entity={ZOMBIE} tick=10500"
    with pytest.raises(D14TickHorizonAuditRejected, match="SPAWN_AFTER_WORLD_LIMIT"):
        audit_horizon(r, log + "\n" + spawn, parent)


def test_duplicate_single_marker_and_missing_fields():
    r, log, _ = make_sources()
    start = log.splitlines()[0]
    assert parse_endurance_marker(log, "RSELF_ENDURANCE_START world=") == start
    with pytest.raises(D14HorizonRejected, match="DUPLICATED"):
        parse_endurance_marker(log + "\n" + start, "RSELF_ENDURANCE_START world=")
    with pytest.raises(D14HorizonRejected, match="MISSING_PAPER_FIELD"):
        _field("RSELF_ENDURANCE_SAMPLE world=" + WORLD, "elapsed_ticks")



def test_closed_prior_action_failure_does_not_forge_food_success():
    report, paper, _ = make_sources()
    report["status"] = "FAIL"
    report["failure"] = "D6StagedMoveRejected: original D6 native item approach declined"
    report["d14_prior_owner_action_failure"] = report["failure"]
    report["d14_action_failure_does_not_end_world"] = True
    independent = {
        "status": "SOURCE_INCOMPLETE",
        "classification": "D14_D8_FOOD_ROUTE_REJECTED_ALL_ORIGINAL_ACTIONS_S16_CLOSED",
    }
    result = audit_horizon(report, paper, independent)
    assert result["status"] == "PASS_DEV"
    assert result["parent_d12_status"] == "SOURCE_INCOMPLETE"
    assert result["legacy_original_action_path_complete"] is False
    assert result["Self_autonomous_long_survival"] is False


def test_reject_claim_that_failed_owner_source_is_complete():
    report, paper, independent = make_sources()
    report["status"] = "FAIL"
    with pytest.raises(D14TickHorizonAuditRejected):
        audit_horizon(report, paper, independent)
    report["status"] = "PASS_DEV"
    independent["status"] = "SOURCE_INCOMPLETE"
    with pytest.raises(D14TickHorizonAuditRejected):
        audit_horizon(report, paper, independent)


def test_partial_owner_independent_audit_never_accepts_without_closed_fences(tmp_path):
    report, _paper, _ = make_sources()
    report["status"] = "FAIL"
    report["failure"] = "Original native Action declined"
    report["d14_prior_owner_action_failure"] = report["failure"]
    report["d14_action_failure_does_not_end_world"] = True
    report["real_world_started"] = True
    report["original_action_issuer"] = "S49"
    report["s49_actions"] = [{"action_id": "attack-real"}]
    with pytest.raises((D14TickHorizonAuditRejected, ValueError, OSError)):
        audit_closed_original_action_failure(
            report,
            nonmotion_path=tmp_path / "missing-nonmotion.json",
            motion_path=tmp_path / "missing-motion.json",
        )



def test_paper_self_death_terminates_without_horizon_pass():
    r, log, _ = make_sources()
    start = log.splitlines()[0]
    terminal = (
        f"RSELF_ENDURANCE_TERMINAL world={WORLD} start_tick=500 "
        "scheduled_stop_tick=10500 observed_tick=1822 elapsed_ticks=1322 "
        "reason=SELF_DIED horizon_reached=false native_actions_inferred=none"
    )
    result = qualified_early_terminal(start, terminal)
    assert result["reason"] == "SELF_DIED"
    assert result["elapsed_ticks"] == 1322
    assert not result["world_horizon_reached"]
    assert not result["self_survived_to_horizon"]
    assert result["terminal_tick"] < 10500


@pytest.mark.parametrize("altered", [
    "scheduled_stop_tick=10501",
    "observed_tick=1823",
    "elapsed_ticks=1323",
    "reason=FAKE_SUCCESS",
    "horizon_reached=true",
])
def test_false_early_terminal_rejected(altered):
    _, log, _ = make_sources()
    first = log.splitlines()[0]
    original = (
        f"RSELF_ENDURANCE_TERMINAL world={WORLD} start_tick=500 "
        "scheduled_stop_tick=10500 observed_tick=1822 elapsed_ticks=1322 "
        "reason=SELF_DIED horizon_reached=false native_actions_inferred=none"
    )
    replacement = altered.split("=", 1)[0] + "="
    new = original.replace(
        next(token for token in original.split() if token.startswith(replacement)),
        altered,
    )
    with pytest.raises(D14HorizonRejected, match="INVALID_PAPER_EARLY_TERMINAL"):
        qualified_early_terminal(first, new)
