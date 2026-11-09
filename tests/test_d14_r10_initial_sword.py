"""R10: one real Paper sword + health observer, no changed S49 authority."""
from __future__ import annotations

import hashlib

import pytest

from test_d14_local_oneworld import _fixture_paths, _validate
from test_d14_natural_active_s49 import _active_fixture, _audit
from test_d14_natural_world import WORLD, Z1
from tools import bug0_d14_local_oneworld as local
from tools.bug0_d14_natural_active_post import D14NaturalActiveAuditRejected
from tools.bug0_d14_natural_world import (
    NATURAL_PLUGIN_CONFIG,
    R10_PLUGIN_CONFIG,
    R10_SWORD_GRANT,
)
from tools.bug0_d14_r10_combat_post import (
    R10PaperCombatRejected,
    inspect_r10_paper_combat,
)

PLAYER = "88888888-8888-4888-8888-888888888888"
READY = (
    "RSELF_R10_SOURCE_READY"
    " source=PAPER_MAIN_THREAD_INITIAL_EQUIPMENT_AND_DAMAGE"
    " sword_count=1 stage=BEFORE_INITIAL_ZOMBIE"
    " original_S49_authority=UNCHANGED"
)
EQUIP = (
    f"RSELF_R10_INITIAL_STONE_SWORD world={WORLD} player={PLAYER} tick=15"
    " item=STONE_SWORD count=1 hand=MAIN_HAND"
    " source=PAPER_OPERATOR_INITIAL_ONLY physics=VANILLA no_auto_attack=true"
)


def _r10(tmp_path):
    report, original, derivative, fence = _active_fixture(tmp_path, early=True)
    original = READY + "\n" + EQUIP + "\n" + original
    report.update({
        "plugin_config": R10_PLUGIN_CONFIG,
        "r10_initial_sword_opt_in": True,
        "r10_operator_initial_equipment":
            "VANILLA_STONE_SWORD_MAIN_HAND_ONE_PAPER_INITIAL_GRANT",
        "paper_original_sha256": hashlib.sha256(original.encode()).hexdigest(),
    })
    return report, original, derivative, fence


def test_r10_equip_strictly_one_and_preserves_vanilla_natural_world(tmp_path):
    report, original, derivative, fence = _r10(tmp_path)
    result = _audit(report, original, derivative, fence)
    assert result["status"] == "PASS_DEV"
    assert result["r10_operator_initial_stone_sword_attested"]
    assert not result["r10_damage_caused_by_specific_s49_action_attested"]
    assert result["original_s49_actions"] == 0
    assert "NoAI" not in R10_PLUGIN_CONFIG
    assert "Health:" not in R10_PLUGIN_CONFIG
    assert "Hunger" not in R10_PLUGIN_CONFIG
    assert R10_PLUGIN_CONFIG == (
        NATURAL_PLUGIN_CONFIG + "dev-r10-initial-stone-sword: true\n"
    )


@pytest.mark.parametrize("tamper", [
    "duplicate", "wrong_sword", "late", "no_grant", "missing",
])
def test_r10_wrong_operator_equipment_fails_independent_source(
    tmp_path, tamper,
):
    report, original, derivative, fence = _r10(tmp_path)
    if tamper == "duplicate":
        original = original.replace(EQUIP + "\n", EQUIP + "\n" + EQUIP + "\n")
    elif tamper == "wrong_sword":
        original = original.replace("item=STONE_SWORD", "item=WOODEN_SWORD")
    elif tamper == "late":
        original = original.replace(EQUIP + "\n", "")
        original = original + EQUIP + "\n"
    elif tamper == "no_grant":
        report["r10_initial_sword_opt_in"] = False
    else:
        original = original.replace(EQUIP + "\n", "")
    report["paper_original_sha256"] = hashlib.sha256(original.encode()).hexdigest()
    with pytest.raises(D14NaturalActiveAuditRejected):
        _audit(report, original, derivative, fence)


def test_r10_preflight_requires_combat_and_readback_grants(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths[4][R10_SWORD_GRANT] = "1"
    with pytest.raises(local.D14LocalRejected, match="R10_STONE_SWORD_REQUIRES"):
        _validate(paths)
    assert not paths[1].exists()
    for grant in (
        local.R9_COMBAT_GRANT,
        local.R6_GRANT,
        local.R7_EVIDENCE_GRANT,
        "D7_PASSIVE_CONTROLS_WORLD_ONLY",
    ):
        paths[4][grant] = "1"
    qualified = _validate(paths)
    assert qualified["r10_stone_sword_initial_opt_in"]
    assert not paths[1].exists()


def _paper_damage():
    return "\n".join([
        "RSELF_R10_ZOMBIE_DAMAGE"
        " source=PAPER_ENTITY_DAMAGE_MONITOR"
        f" ordinal=1 world={WORLD} player={PLAYER}"
        f" victim={Z1} attacker={PLAYER} tick=20"
        " cause=ENTITY_ATTACK main_hand=STONE_SWORD"
        " health_before=20.0 final_damage=5.0"
        " cancelled=false s49_action_id=NOT_ATTESTED",
        "RSELF_R10_DAMAGE_AFTER source=PAPER_NEXT_MAIN_THREAD_TICK"
        f" ordinal=1 world={WORLD} victim={Z1}"
        " event_tick=20 observed_tick=21 health_after=15.0"
        " s49_action_id=NOT_ATTESTED",
        "RSELF_R10_SELF_DAMAGE source=PAPER_ENTITY_DAMAGE_MONITOR"
        f" ordinal=2 world={WORLD} player={PLAYER}"
        f" victim={PLAYER} attacker={Z1} tick=22"
        " cause=ENTITY_ATTACK main_hand=STONE_SWORD"
        " health_before=20.0 final_damage=3.0"
        " cancelled=false s49_action_id=NOT_ATTESTED",
        "RSELF_R10_DAMAGE_AFTER source=PAPER_NEXT_MAIN_THREAD_TICK"
        f" ordinal=2 world={WORLD} victim={PLAYER}"
        " event_tick=22 observed_tick=23 health_after=17.0"
        " s49_action_id=NOT_ATTESTED",
    ]) + "\n"


def test_r10_real_paper_health_deltas_never_forge_s49_attribution(tmp_path):
    report, original, derivative, fence = _r10(tmp_path)
    original = original + _paper_damage()
    report["paper_original_sha256"] = hashlib.sha256(original.encode()).hexdigest()
    checked = _audit(report, original, derivative, fence)
    result = inspect_r10_paper_combat(original, report, checked)
    assert result["paper_zombie_melee_damage_event_count"] == 1
    assert result["paper_self_melee_damage_event_count"] == 1
    assert result["paper_next_tick_positive_zombie_health_delta_count"] == 1
    assert result["paper_damage_events"][0]["paper_next_tick_health_delta"] == 5.0
    assert result["paper_damage_events"][1]["paper_next_tick_health_delta"] == 3.0
    assert not result["s49_action_to_paper_damage_causal_link_attested"]
    assert not result["food_or_loot_staged"]
    assert not result["physical_stop_attested"]


@pytest.mark.parametrize("changed", [
    "main_hand=WOODEN_SWORD",
    "world=77777777-7777-4777-8777-777777777777",
    "ordinal=3",
    "s49_action_id=FAKE",
])
def test_r10_paper_damage_forgery_rejected(tmp_path, changed):
    report, original, derivative, fence = _r10(tmp_path)
    original += _paper_damage()
    report["paper_original_sha256"] = hashlib.sha256(original.encode()).hexdigest()
    checked = _audit(report, original, derivative, fence)
    changed_log = original
    old = (
        "main_hand=STONE_SWORD" if changed.startswith("main_hand") else
        f"world={WORLD}" if changed.startswith("world") else
        "ordinal=1" if changed.startswith("ordinal") else
        "s49_action_id=NOT_ATTESTED"
    )
    mark = "RSELF_R10_ZOMBIE_DAMAGE"
    prefix, suffix = changed_log.split(mark, 1)
    suffix = suffix.replace(old, changed, 1)
    changed_log = prefix + mark + suffix
    with pytest.raises(R10PaperCombatRejected):
        inspect_r10_paper_combat(changed_log, report, checked)


def test_r10_no_damage_is_not_reported_as_combat_success(tmp_path):
    report, original, derivative, fence = _r10(tmp_path)
    audited = _audit(report, original, derivative, fence)
    result = inspect_r10_paper_combat(original, report, audited)
    assert result["paper_zombie_melee_damage_event_count"] == 0
    assert result["paper_next_tick_positive_zombie_health_delta_count"] == 0
    assert result["paper_managed_zombie_death_count"] == 1  # historical fixture
    assert result["paper_killer_is_self_death_count"] == 0
