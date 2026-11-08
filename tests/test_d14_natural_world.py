"""D14 R3 natural World: source-clock tests, no D4 staged World authority."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from adapters.mineflayer.s31a_real_server_ci import _write_config
from tools.bug0_d14_natural_post import D14NaturalAuditRejected, audit_natural
from tools.bug0_d14_natural_world import (
    NATURAL_PLUGIN_CONFIG,
    D14NaturalWorldRejected,
    NaturalPaperTimeline,
    marker_kind,
    natural_properties,
)

WORLD = "11111111-1111-4111-8111-111111111111"
Z1 = "22222222-2222-4222-8222-222222222222"
Z2 = "33333333-3333-4333-8333-333333333333"
START = (
    f"RSELF_ENDURANCE_START world={WORLD} start_tick=15 stop_tick=10015 "
    "horizon_ticks=10000 natural_600tick_respawns_unchanged=true"
)
INITIAL = f"RSELF_RESPAWN_INITIAL world={WORLD} entity={Z1} generation=1 tick=15"
DEATH = f"RSELF_RESPAWN_DEATH world={WORLD} entity={Z1} generation=1 tick=526"
RESPAWN = f"RSELF_RESPAWN_SPAWN world={WORLD} entity={Z2} generation=2 tick=1126"
LIMIT = (
    f"RSELF_ENDURANCE_LIMIT world={WORLD} start_tick=15 end_tick=10015 "
    f"observed_tick=10015 elapsed_ticks=10000 generation=2 living={Z2} "
    "stop_new_spawns=true no_forced_death=true"
)
TERMINAL = (
    f"RSELF_ENDURANCE_TERMINAL world={WORLD} start_tick=15 "
    "scheduled_stop_tick=10015 observed_tick=1337 elapsed_ticks=1322 "
    "reason=SELF_DIED horizon_reached=false native_actions_inferred=none"
)


def raw_lines(*, early=False):
    values = [INITIAL, START]
    count = 6 if early else 49
    for i in range(1, count + 1):
        elapsed = i * 200
        if elapsed > 526 and DEATH not in values:
            values.append(DEATH)
        if elapsed > 1126 and RESPAWN not in values:
            values.append(RESPAWN)
        living = Z1 if elapsed < 526 else ("NONE" if elapsed < 1126 else Z2)
        values.append(
            f"RSELF_ENDURANCE_SAMPLE world={WORLD} tick={15+elapsed} "
            f"elapsed_ticks={elapsed} generation={1 if elapsed < 1126 else 2} "
            f"living={living} pending_due_tick=-1"
        )
    values.append(TERMINAL if early else LIMIT)
    return values


def make_report(tmp_path, *, early=False):
    _write_config(tmp_path)
    original_props = (tmp_path / "server.properties").read_text(encoding="utf8")
    values = raw_lines(early=early)
    timeline = NaturalPaperTimeline()
    for value in values:
        timeline.admit(marker_kind(value), value)
    original = "\n".join(values) + "\n"
    derivative = "".join(
        json.dumps({
            "record_type": "D14_R3_DERIVATIVE_SOURCE_REFERENCE",
            "kind": marker_kind(x), "original_paper_line": x,
            "native_observation": None,
        }) + "\n" for x in values
    )
    report = {
        "status": "PASS_DEV",
        "classification": (
            "DEV_D14_R3_NATURAL_EARLY_SELF_TERMINAL_OBSERVED" if early
            else "DEV_D14_R3_NATURAL_10000_PAPER_TICKS_OBSERVED"
        ),
        "cleanup_done": True,
        "java_exit": 0, "node_exit": 0,
        "paper_original_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "derivative_journal_sha256": hashlib.sha256(derivative.encode()).hexdigest(),
        "world_config": "NATURAL_SURVIVAL",
        "plugin_config": NATURAL_PLUGIN_CONFIG,
        "server_properties": natural_properties(original_props),
        "s49_physical_issuer": "NOT_CONNECTED_IN_R3_OBSERVER",
        "operator_commands": [],
        "staged_zombie_no_ai": False,
        "staged_zombie_low_health": False,
        "staged_hunger_effect": False,
        "staged_enemy_teleport": False,
        "natural_mob_spawning_unchanged": True,
        "world_daylight_behavior": "VANILLA",
        "managed_respawn_after_real_death_ticks": 600,
        "new_s49_actions": 0, "model_posts": 0,
        "learning_updates": 0, "skill_installs": 0,
        "native_snapshots": [],
        "result": timeline.finish(),
        "paper_source": timeline.source_summary(),
    }
    return report, original, derivative


def do_audit(report, original, derivative):
    return audit_natural(
        report, original, derivative,
        original_sha=hashlib.sha256(original.encode()).hexdigest(),
        derivative_sha=hashlib.sha256(derivative.encode()).hexdigest(),
    )


def test_natural_survival_properties_without_staged_action(tmp_path):
    _write_config(tmp_path)
    before = (tmp_path / "server.properties").read_text()
    after = natural_properties(before)
    assert "level-type=minecraft:normal\n" in after
    assert "gamemode=survival\n" in after
    assert "difficulty=normal\n" in after
    assert "force-gamemode=true\n" in after
    assert "max-players=1\n" in after
    assert "gamemode=creative\n" not in after
    assert "level-type=minecraft:flat\n" not in after
    assert "doMobSpawning" not in after
    assert "NoAI" not in NATURAL_PLUGIN_CONFIG
    assert "Health:" not in NATURAL_PLUGIN_CONFIG
    assert "hunger" not in NATURAL_PLUGIN_CONFIG.lower()
    assert "dev-natural-world-mode: true" in NATURAL_PLUGIN_CONFIG
    assert natural_properties(after) == after


@pytest.mark.parametrize("bad", [
    "", "server-ip=127.0.0.1\n", "gamemode=survival\ngamemode=creative\n",
])
def test_missing_or_ambiguous_world_properties_refused(bad):
    with pytest.raises(D14NaturalWorldRejected):
        natural_properties(bad)


def test_realistic_unforced_death_respawn_and_10000tick_audit(tmp_path):
    report, original, derivative = make_report(tmp_path)
    result = do_audit(report, original, derivative)
    assert result["status"] == "PASS_DEV"
    assert result["reached_10000_ticks"] is True
    assert result["observed_world_ticks"] == 10000
    assert result["managed_zombie_deaths"] == 1
    assert result["managed_zombie_respawns"] == 1
    assert result["original_paper_checkpoints"] == 49
    assert result["new_original_s49_actions"] == 0
    assert result["long_run_autonomous_self"] is False


def test_early_zombie_kills_self_is_real_observation_not_horizon(tmp_path):
    report, original, derivative = make_report(tmp_path, early=True)
    result = do_audit(report, original, derivative)
    assert result["status"] == "PASS_DEV"
    assert result["eventual_reason"] == "SELF_DIED"
    assert result["observed_world_ticks"] == 1322
    assert result["managed_zombie_respawns"] == 1
    assert result["reached_10000_ticks"] is False
    assert result["self_died_before_limit"] is True
    assert report["result"]["self_died_before_limit"] is True


@pytest.mark.parametrize(("field", "bad"), [
    ("world_config", "DEV_STAGED_ARENA"),
    ("staged_hunger_effect", True),
    ("staged_zombie_no_ai", True),
    ("staged_zombie_low_health", True),
    ("staged_enemy_teleport", True),
    ("operator_commands", ["effect give RelaySelf minecraft:hunger 70 20 true"]),
    ("natural_mob_spawning_unchanged", False),
    ("model_posts", 1), ("learning_updates", 1), ("new_s49_actions", 1),
    ("managed_respawn_after_real_death_ticks", 30),
    ("paper_original_sha256", "forged"),
    ("derivative_journal_sha256", "forged"),
])
def test_artificial_conditions_or_unverified_hash_rejected(tmp_path, field, bad):
    report, original, derivative = make_report(tmp_path)
    report[field] = bad
    with pytest.raises(D14NaturalAuditRejected):
        do_audit(report, original, derivative)


def test_report_claim_cannot_override_paper_self_death(tmp_path):
    report, original, derivative = make_report(tmp_path, early=True)
    report["result"] = {
        "outcome": "WORLD_TICK_LIMIT_REACHED",
        "elapsed_ticks": 10000,
        "terminal_reason": "PAPER_WORLD_LIMIT",
        "self_died_before_limit": False,
    }
    with pytest.raises(D14NaturalAuditRejected, match="REPORT_RETROSPECTIVE"):
        do_audit(report, original, derivative)


def test_dropped_paper_marker_from_derivative_rejected(tmp_path):
    report, original, derivative = make_report(tmp_path)
    rows = derivative.splitlines()
    derivative = "\n".join(rows[:3] + rows[4:]) + "\n"
    # Change the derivative hash to show that a coherent but incomplete
    # derivative is still rejected against the immutable Paper original.
    report["derivative_journal_sha256"] = hashlib.sha256(derivative.encode()).hexdigest()
    with pytest.raises(D14NaturalAuditRejected, match="DERIVATIVE_LOST"):
        do_audit(report, original, derivative)


def test_off_by_one_respawn_world_clock_rejected(tmp_path):
    report, original, derivative = make_report(tmp_path)
    new = original.replace("tick=1126", "tick=1125")
    report["paper_original_sha256"] = hashlib.sha256(new.encode()).hexdigest()
    with pytest.raises(D14NaturalAuditRejected):
        do_audit(report, new, derivative)


def test_noncontiguous_paper_checkpoints_rejected():
    timeline = NaturalPaperTimeline()
    for row in raw_lines():
        if "elapsed_ticks=400 " in row:
            continue
        if "elapsed_ticks=600 " in row:
            with pytest.raises(
                D14NaturalWorldRejected, match="NONCONTIGUOUS_PAPER_TICK_SAMPLES"
            ):
                timeline.admit(marker_kind(row), row)
            return
        timeline.admit(marker_kind(row), row)
    pytest.fail("expected 600tick sample not observed")


def test_no_duplicate_terminal_and_no_fabricated_prediction():
    t = NaturalPaperTimeline()
    for line in raw_lines(early=True):
        t.admit(marker_kind(line), line)
    assert t.finish()["outcome"] == "SELF_EARLY_TERMINAL"
    with pytest.raises(D14NaturalWorldRejected):
        t.admit("TERMINAL", TERMINAL)
    assert not hasattr(t, "prediction")
