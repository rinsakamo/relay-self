"""R11: genuine 24000 Paper tick natural day, passive loot, no free Action."""
from __future__ import annotations

import hashlib
import json

import pytest

from test_d14_local_oneworld import _fixture_paths, _validate
from test_d14_natural_active_s49 import _active_fixture, _audit
from test_d14_natural_world import INITIAL, WORLD, Z1
from tools import bug0_d14_local_oneworld as local
from tools.bug0_d14_natural_world import (
    R10_PLUGIN_CONFIG,
    R11_DAY_GRANT,
    R11_PLUGIN_CONFIG,
    NaturalPaperTimeline,
    marker_kind,
)
from tools.bug0_d14_r11_day_foraging_post import (
    R11SourceRejected,
    inspect_r11_natural_day,
)

SELF = "88888888-8888-4888-8888-888888888888"
EQUIP = (
    f"RSELF_R10_INITIAL_STONE_SWORD world={WORLD} player={SELF} tick=15"
    " item=STONE_SWORD count=1 hand=MAIN_HAND"
    " source=PAPER_OPERATOR_INITIAL_ONLY physics=VANILLA no_auto_attack=true"
)
SOURCE_READY = (
    "RSELF_R10_SOURCE_READY"
    " source=PAPER_MAIN_THREAD_INITIAL_EQUIPMENT_AND_DAMAGE"
    " sword_count=1 stage=BEFORE_INITIAL_ZOMBIE"
    " original_S49_authority=UNCHANGED"
)
LOOT_READY = (
    "RSELF_R11_LOOT_SOURCE_READY"
    " source=PAPER_PASSIVE_MANAGED_DEATH_AND_ITEM_EVENTS"
    " world_mutation=NONE pickup_action=NONE"
)


def _r11(tmp_path, *, early=False):
    report, _, _, fence = _active_fixture(tmp_path)
    start = 15
    full = 1000
    start_row = (
        f"RSELF_ENDURANCE_START world={WORLD} start_tick={start}"
        " stop_tick=24015 horizon_ticks=24000"
        " natural_600tick_respawns_unchanged=true"
        " world_time=1000 world_full_time=1000 daylight_cycle=true"
    )
    values = [INITIAL, start_row]
    limit = 119 if not early else 2
    for i in range(1, limit + 1):
        elapsed = i * 200
        values.append(
            f"RSELF_ENDURANCE_SAMPLE world={WORLD} tick={start+elapsed}"
            f" elapsed_ticks={elapsed} generation=1"
            f" living={Z1} pending_due_tick=-1"
            f" world_time={(full+elapsed)%24000}"
            f" world_full_time={full+elapsed} daylight_cycle=true"
        )
    if early:
        values.append(
            f"RSELF_ENDURANCE_TERMINAL world={WORLD}"
            " start_tick=15 scheduled_stop_tick=24015"
            " observed_tick=650 elapsed_ticks=635"
            " reason=SELF_DIED horizon_reached=false"
            " native_actions_inferred=none"
        )
    else:
        values.append(
            f"RSELF_ENDURANCE_LIMIT world={WORLD}"
            " start_tick=15 end_tick=24015 observed_tick=24015"
            " elapsed_ticks=24000 generation=1"
            f" living={Z1} stop_new_spawns=true no_forced_death=true"
            " world_time=1000 world_full_time=25000 daylight_cycle=true"
        )
    timeline = NaturalPaperTimeline(horizon_ticks=24000)
    for value in values:
        timeline.admit(marker_kind(value), value)
    paper = "\n".join([SOURCE_READY, LOOT_READY, EQUIP, *values]) + "\n"
    derived = "".join(
        json.dumps({
            "record_type": "D14_R3_DERIVATIVE_SOURCE_REFERENCE",
            "kind": marker_kind(row), "original_paper_line": row,
            "native_observation": None,
        }) + "\n"
        for row in values
    )
    report.update({
        "plugin_config": R11_PLUGIN_CONFIG,
        "r10_initial_sword_opt_in": True,
        "r10_operator_initial_equipment":
            "VANILLA_STONE_SWORD_MAIN_HAND_ONE_PAPER_INITIAL_GRANT",
        "r11_natural_day_opt_in": True,
        "requested_paper_horizon_ticks": 24000,
        "result": timeline.finish(),
        "paper_source": timeline.source_summary(),
        "paper_original_sha256": hashlib.sha256(paper.encode()).hexdigest(),
        "derivative_journal_sha256": hashlib.sha256(derived.encode()).hexdigest(),
    })
    return report, paper, derived, fence


def test_full_24000_tick_paper_day_is_independently_qualified(tmp_path):
    report, paper, derived, fence = _r11(tmp_path)
    active = _audit(report, paper, derived, fence)
    assert active["status"] == "PASS_DEV"
    assert active["observed_world_ticks"] == 24000
    assert active["r11_full_day_survival_observed"] is True
    assert active["original_s49_actions"] == 0
    day = inspect_r11_natural_day(paper, report, active)
    assert day["status"] == "PAPER_SOURCE_ONLY"
    assert day["start_world_time"] == day["end_world_time"] == 1000
    assert day["sample_count"] == 119
    assert day["full_day_horizon_survived"] is True
    assert day["paper_managed_rotten_death_count"] == 0
    assert day["original_s49_item_approach_authorized"] is False
    assert R11_PLUGIN_CONFIG != R10_PLUGIN_CONFIG
    assert "dev-tick-endurance-ticks: 24000\n" in R11_PLUGIN_CONFIG
    assert "dev-r11-natural-day: true\n" in R11_PLUGIN_CONFIG
    assert "NoAI" not in R11_PLUGIN_CONFIG
    assert "Hunger" not in R11_PLUGIN_CONFIG


def test_early_death_is_not_one_day_survival(tmp_path):
    report, paper, derived, fence = _r11(tmp_path, early=True)
    active = _audit(report, paper, derived, fence)
    assert active["observed_world_ticks"] == 635
    assert active["self_died_before_limit"] is True
    assert active["r11_full_day_survival_observed"] is False
    readout = inspect_r11_natural_day(paper, report, active)
    assert readout["full_day_horizon_survived"] is False
    assert readout["end_world_time"] is None


@pytest.mark.parametrize("tamper", [
    "skip_200", "frozen_full_time", "invalid_modulo", "duplicate_ready",
])
def test_daylight_clock_tampering_is_not_qualified(tmp_path, tamper):
    report, paper, derived, fence = _r11(tmp_path)
    active = _audit(report, paper, derived, fence)
    if tamper == "skip_200":
        paper = paper.replace("world_full_time=1200", "world_full_time=1201", 1)
    elif tamper == "frozen_full_time":
        paper = paper.replace("world_full_time=25000", "world_full_time=1000", 1)
    elif tamper == "invalid_modulo":
        paper = paper.replace("world_time=1200 world_full_time=1200",
                              "world_time=1199 world_full_time=1200", 1)
    else:
        paper = paper.replace(LOOT_READY, LOOT_READY + "\n" + LOOT_READY, 1)
    with pytest.raises(R11SourceRejected):
        inspect_r11_natural_day(paper, report, active)


def test_natural_item_spawn_without_actual_death_source_rejected(tmp_path):
    report, paper, derived, fence = _r11(tmp_path)
    active = _audit(report, paper, derived, fence)
    paper += (
        f"RSELF_R11_ROTTEN_ITEM_SPAWN source=PAPER_ITEM_SPAWN world={WORLD}"
        f" zombie={Z1} item=aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
        " tick=600 count=1 death_link=PROXIMITY_AND_TICK_ONLY"
        " inventory_delta=NOT_ATTESTED\n"
    )
    with pytest.raises(R11SourceRejected, match="ITEM_SPAWN"):
        inspect_r11_natural_day(paper, report, active)


def test_r11_local_preflight_requires_full_prior_grant_chain(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths[4][R11_DAY_GRANT] = "1"
    with pytest.raises(local.D14LocalRejected, match="R11_DAY_REQUIRES"):
        _validate(paths)
    assert not paths[1].exists()
    for key in (
        local.R10_SWORD_GRANT, local.R9_COMBAT_GRANT,
        local.R7_EVIDENCE_GRANT, local.R6_GRANT,
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
    ):
        paths[4][key] = "1"
    valid = _validate(paths)
    assert valid["r11_natural_day_opt_in"]
    assert valid["requested_paper_horizon_ticks"] == 24000
    assert not paths[1].exists()
