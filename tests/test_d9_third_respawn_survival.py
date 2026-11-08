"""D9-A offline read-only third-spawn and continued Self survival negatives."""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from tools import bug0_d9_third_respawn_post as auditor
from tools.bug0_d9_third_respawn_world import (
    D9SurvivalRejected,
    d9_body_sample,
    d9_qualify_third_spawn,
)

W = "11111111-1111-4111-8111-111111111111"
Z1 = "22222222-2222-4222-8222-222222222222"
Z2 = "33333333-3333-4333-8333-333333333333"
Z3 = "44444444-4444-4444-8444-444444444444"
K = "55555555-5555-4555-8555-555555555555"


def paper_data():
    first = f"RSELF_RESPAWN_INITIAL world={W} entity={Z1} generation=1 tick=1 "
    second = f"RSELF_RESPAWN_SPAWN world={W} entity={Z2} generation=2 tick=600 "
    death = (
        f"RSELF_RESPAWN_DEATH world={W} entity={Z2} generation=2 "
        f"tick=700 due_tick=1300 killer={K} "
    )
    third = f"RSELF_RESPAWN_SPAWN world={W} entity={Z3} generation=3 tick=1300 "
    return first, second, death, third


def idle_paper_lines(*, n=12, drift=0.0, input_on=False, skip=None):
    rows = []
    for idx in range(n):
        tick = 1288 + idx
        if tick == skip:
            continue
        rows.append(
            "RSELF_D7_PAPER_TICK source=PAPER_SERVER_MAIN_THREAD_V1 "
            f"ordinal={idx} tick={tick} player={K} world={W} "
            f"x={1+drift*idx} y=64 z=2 "
            f"forward={'true' if input_on and idx==4 else 'false'} "
            "back=false left=false right=false jump=false "
            "sprint=false sneak=false"
        )
    return "\n".join(rows)


def native_frame(*, food=16.0, health=20.0, truncated=False,
                 candidate_count=1, zombie_id=73):
    inventory = [SimpleNamespace(name="rotten_flesh", count=1)]
    entity = SimpleNamespace(name="zombie", entity_id=zombie_id)
    snapshot = SimpleNamespace(
        food=food, health=health, oxygen_level=20,
        inventory=inventory,
        nearby_entities=[entity],
        nearby_entities_coverage=SimpleNamespace(
            truncated=truncated, candidate_count=candidate_count,
        ),
    )
    return SimpleNamespace(
        kind="probe", request_id="d9-new-probe", seq=123,
        session_id="session", snapshot=snapshot,
    )


def test_d9_first_second_third_real_world_600tick_only():
    first, second, death, third = paper_data()
    actual = d9_qualify_third_spawn(first, second, death, third)
    assert actual["third_spawn_after_death_ticks"] == 600
    assert len({actual["first_zombie_uuid"],
                actual["second_zombie_uuid"],
                actual["third_zombie_uuid"]}) == 3


@pytest.mark.parametrize("mutation", [
    lambda a: a.__setitem__(3, a[3].replace("tick=1300", "tick=1299")),
    lambda a: a.__setitem__(3, a[3].replace(Z3, Z2)),
    lambda a: a.__setitem__(3, a[3].replace(W, Z1)),
    lambda a: a.__setitem__(2, a[2].replace(Z2, Z1)),
    lambda a: a.__setitem__(3, a[3].replace("generation=3", "generation=2")),
])
def test_d9_spawn_rejects_reused_old_or_wrong_tick(mutation):
    rows = list(paper_data())
    mutation(rows)
    with pytest.raises(D9SurvivalRejected):
        d9_qualify_third_spawn(*rows)


@pytest.mark.parametrize("mutant", [
    {"food": 0.0}, {"health": 0.0}, {"food": float("nan")},
    {"health": float("inf")}, {"truncated": True},
    {"candidate_count": 2},
])
def test_d9_body_failclosed_on_bad_native_source(mutant):
    with pytest.raises(D9SurvivalRejected):
        d9_body_sample(native_frame(**mutant))


def test_d9_body_records_read_only_native_food_health_item():
    sample = d9_body_sample(native_frame())
    assert sample["food"] == 16
    assert sample["health"] == 20
    assert sample["rotten_flesh"] == 1
    assert sample["zombie_ids"] == [73]


def test_d9_paper_consecutive_last_idle_not_autonomous_rest():
    result = auditor.audit_paper_idle_before_third(
        idle_paper_lines(), 1300,
    )
    assert result["paper_idle_tick_count"] == 12
    assert result["autonomous_rest_selected"] is False


@pytest.mark.parametrize("mutant", [
    {"n": 7},
    {"drift": .02},
    {"input_on": True},
    {"skip": 1293},
])
def test_d9_paper_rest_not_from_missing_motion_or_active_input(mutant):
    with pytest.raises(auditor.D9SurvivalAuditRejected):
        auditor.audit_paper_idle_before_third(
            idle_paper_lines(**mutant), 1300,
        )


def fake_report():
    first, second, death, third = paper_data()
    lineage = d9_qualify_third_spawn(first, second, death, third)
    one = {
        "session_id": "session", "native_seq": 200,
        "request_id": "d9-monitor-00", "food": 15.0, "health": 20.0,
        "rotten_flesh": 1, "zombie_ids": [],
    }
    two = {
        **one, "native_seq": 210, "request_id": "d9-monitor-01",
        "food": 14.0,
    }
    after = {
        **one, "native_seq": 220, "request_id": "d9-after",
        "zombie_ids": [73],
    }
    return {
        "status": "PASS_DEV", "real_model_calls": 0,
        "learning_updated": False, "cleanup_done": True,
        "node_exit": 0, "java_exit": 0,
        "initial_paper": first, "paper_respawn": second,
        "d8_second_generation": {"paper_respawn_death": death},
        "native_initial": {"zombie_entity_id": 30},
        "native_respawn": {"zombie_entity_id": 46},
        "d8_original_total_actions": 2,
        "d9_status": "PASS_DEV",
        "d9_classification":
            "D9_TWO_REAL_EATS_THIRD_RESPAWN_READ_ONLY_SURVIVAL_PASS",
        "d9_physical_action_issued_after_second_eat": False,
        "d9_physical_action_issued_after_second_generation": False,
        "d9_two_real_meals_proven": True,
        "d9_second_vanilla_zero_continued": False,
        "d9_autonomous_rest_selected": False,
        "d9_passive_wait_input_off_not_rest_authorized": True,
        "d9_third_paper_spawn": third,
        "d9_third_paper_lineage": lineage,
        "d9_third_native": {
            "session_id": "session", "seq": 219,
            "zombie_entity_id": 73,
        },
        "d9_final_native_body": after,
        "d9_body_monitor_samples": [one, two],
        "d9_read_only_l0": {
            "selected": "DEFER", "reason": "ZOMBIE",
            "provenance": "session:220", "actually_dispatched": False,
        },
        "d9_original_action_count": 2,
        "d9_original_action_ids": ["a", "b"],
        "d9_nonmotion_sha256": "sha-a",
        "d9_motion_sha256": "sha-b",
    }


def test_d9_full_read_only_path_with_d8_audit_dependency(monkeypatch, tmp_path):
    report = fake_report()
    third = report["d9_third_paper_spawn"]
    paper = "\n".join([third, idle_paper_lines()])
    monkeypatch.setattr(
        auditor, "audit_two_natural_food_cycles", lambda *a, **kw: {
            "status": "PASS_DEV", "two_real_natural_food_cycles": True,
            "same_native_session_id": "session",
            "second_inventory_after_eat": 1,
            "original_S49_action_ids": ["a", "b"],
            "original_nonmotion_ledger_sha256": "sha-a",
            "original_move_ledger_sha256": "sha-b",
        },
    )
    result = auditor.audit_d9(
        report, paper, nonmotion_path=tmp_path/"a",
        motion_path=tmp_path/"b", s50_jsonl="",
    )
    assert result["status"] == "PASS_DEV"
    assert result["third_real_natural_food_cycle"] is False
    assert result["native_continuous_survival_samples"] == 3
    assert result["autonomous_rest_or_long_run_proven"] is False


@pytest.mark.parametrize("mutant", [
    lambda r: r.update(d9_physical_action_issued_after_second_generation=True),
    lambda r: r.update(d9_two_real_meals_proven=False),
    lambda r: r.update(d9_second_vanilla_zero_continued=True),
    lambda r: r.update(d9_physical_action_issued_after_second_eat=True),
    lambda r: r.update(d9_autonomous_rest_selected=True),
    lambda r: r["d9_third_native"].update(zombie_entity_id=46),
    lambda r: r["d9_third_native"].update(seq=210),
    lambda r: r["d9_final_native_body"].update(rotten_flesh=3),
    lambda r: r["d9_body_monitor_samples"][1].update(native_seq=199),
    lambda r: r["d9_body_monitor_samples"][1].update(health=0),
    lambda r: r["d9_read_only_l0"].update(actually_dispatched=True),
    lambda r: r.update(d9_original_action_ids=["a"]),
])
def test_d9_independent_audit_rejects_artificial_survival_or_action(
    monkeypatch, tmp_path, mutant,
):
    report = fake_report()
    mutant(report)
    monkeypatch.setattr(
        auditor, "audit_two_natural_food_cycles", lambda *a, **kw: {
            "status": "PASS_DEV", "two_real_natural_food_cycles": True,
            "same_native_session_id": "session",
            "second_inventory_after_eat": 1,
            "original_S49_action_ids": ["a", "b"],
            "original_nonmotion_ledger_sha256": "sha-a",
            "original_move_ledger_sha256": "sha-b",
        },
    )
    with pytest.raises(auditor.D9SurvivalAuditRejected):
        auditor.audit_d9(
            report, "\n".join([
                report["d9_third_paper_spawn"], idle_paper_lines(),
            ]),
            nonmotion_path=tmp_path/"a",
            motion_path=tmp_path/"b", s50_jsonl="",
        )


def test_d9_no_first_two_meals_cannot_claim_survival(monkeypatch, tmp_path):
    monkeypatch.setattr(
        auditor, "audit_two_natural_food_cycles",
        lambda *a, **kw: {"status": "NOT_EXERCISED"},
    )
    report = {"d8_first_true_zero_food_not_exercised": True}
    out = auditor.audit_d9(
        report, "", nonmotion_path=tmp_path/"a",
        motion_path=tmp_path/"b", s50_jsonl="",
    )
    assert out["status"] == "NOT_EXERCISED"
    report = deepcopy(report)
    report["d9_status"] = "PASS_DEV"
    with pytest.raises(auditor.D9SurvivalAuditRejected):
        auditor.audit_d9(
            report, "", nonmotion_path=tmp_path/"a",
            motion_path=tmp_path/"b", s50_jsonl="",
        )


def test_d9_first_true_zero_no_callback_fields_is_genuine_not_exercised(
    monkeypatch, tmp_path,
):
    monkeypatch.setattr(
        auditor, "audit_two_natural_food_cycles",
        lambda *a, **kw: {"status": "NOT_EXERCISED"},
    )
    report = {"d8_first_true_zero_food_not_exercised": True}
    out = auditor.audit_d9(
        report, "", nonmotion_path=tmp_path/"a",
        motion_path=tmp_path/"b", s50_jsonl="",
    )
    assert out["status"] == "NOT_EXERCISED"
    report["d9_status"] = "PASS_DEV"
    with pytest.raises(auditor.D9SurvivalAuditRejected):
        auditor.audit_d9(
            report, "", nonmotion_path=tmp_path/"a",
            motion_path=tmp_path/"b", s50_jsonl="",
        )


def fake_second_zero():
    report = fake_report()
    sid = "session"
    attack1 = {"action_id": "a"}
    move1 = {"action_id": "b"}
    eat1 = {"action_id": "c", "session_id": sid}
    attack2 = "d"
    report.update(
        d8_second_generation_food_proven=False,
        d8_second_generation={
            **report["d8_second_generation"],
            "real_rotten_flesh_count": 0,
            "original_eat_issued": False,
        },
        self_eat=True,
        s49_actions=[attack1],
        d6_original_s49_move_actions=[move1],
        d7f_eat_outcome=eat1,
        d7f_native_after_eat={"rotten_flesh": 0},
        d8_original_second_attack_action_id=attack2,
        d8_prior_rotten_after_gen1_eat=0,
        nonmotion_fence={
            "sha256": "sha-a", "unresolved": False,
            "action_ids": ["a", "c", "d"],
        },
        motion_fence={
            "sha256": "sha-b", "unresolved": False,
            "action_ids": ["b"],
        },
        d9_status="PASS_DEV",
        d9_classification=(
            "D9_SECOND_ZERO_DROP_THIRD_RESPAWN_READ_ONLY_SURVIVAL_PASS"
        ),
        d9_physical_action_issued_after_second_eat=None,
        d9_two_real_meals_proven=False,
        d9_second_vanilla_zero_continued=True,
        d9_original_action_count=4,
        d9_original_action_ids=["a", "b", "c", "d"],
    )
    # A true zero adds no second item and leaves the original first EAT
    # inventory balance untouched through the same-World third respawn.
    for row in [*report["d9_body_monitor_samples"],
                report["d9_final_native_body"]]:
        row["rotten_flesh"] = 0
    return report


def zero_d8_verdict():
    return {
        "status": "NOT_EXERCISED",
        "classification": "D8_TWO_GENERATION_SECOND_TRUE_ZERO_DROP_NO_EAT",
        "two_real_zombie_kills": True,
        "two_real_food_cycles": False,
        "second_natural_count": 0,
    }


def test_d9_second_genuine_zero_still_survives_to_third_world(
    monkeypatch, tmp_path,
):
    report = fake_second_zero()
    monkeypatch.setattr(
        auditor, "audit_two_natural_food_cycles",
        lambda *a, **kw: zero_d8_verdict(),
    )
    result = auditor.audit_d9(
        report, "\n".join([
            report["d9_third_paper_spawn"], idle_paper_lines(),
        ]),
        nonmotion_path=tmp_path/"a", motion_path=tmp_path/"b",
        s50_jsonl="",
    )
    assert result["status"] == "PASS_DEV"
    assert result["second_natural_zero_drop"] is True
    assert result["two_real_natural_food_cycles"] is False
    assert result["first_real_natural_food_cycle"] is True
    assert result["third_real_natural_food_cycle"] is False
    assert result["same_original_s49_actions_before_after_third"] is True


@pytest.mark.parametrize("mutant", [
    lambda r: r.update(d9_two_real_meals_proven=True),
    lambda r: r.update(d9_second_vanilla_zero_continued=False),
    lambda r: r["d8_second_generation"].update(
        original_eat_issued=True
    ),
    lambda r: r["d8_second_generation"].update(
        real_rotten_flesh_count=1
    ),
    lambda r: r["d8_second_generation"].update(
        d7f_eat_outcome={"forged": True}
    ),
    lambda r: r.update(d9_original_action_ids=["a", "b", "c"]),
    lambda r: r["d9_final_native_body"].update(rotten_flesh=1),
    lambda r: r["nonmotion_fence"].update(action_ids=["a", "c"]),
    lambda r: r.update(d9_physical_action_issued_after_second_eat=False),
    lambda r: r.update(d9_physical_action_issued_after_second_generation=True),
])
def test_d9_second_zero_never_fakes_second_eat_or_third_actions(
    monkeypatch, tmp_path, mutant,
):
    report = fake_second_zero()
    mutant(report)
    monkeypatch.setattr(
        auditor, "audit_two_natural_food_cycles",
        lambda *a, **kw: zero_d8_verdict(),
    )
    with pytest.raises(auditor.D9SurvivalAuditRejected):
        auditor.audit_d9(
            report, "\n".join([
                report["d9_third_paper_spawn"], idle_paper_lines(),
            ]),
            nonmotion_path=tmp_path/"a", motion_path=tmp_path/"b",
            s50_jsonl="",
        )


def test_d9_zero_cannot_be_promoted_from_forged_d8_verdict(
    monkeypatch, tmp_path,
):
    report = fake_second_zero()
    verdict = zero_d8_verdict()
    verdict["two_real_zombie_kills"] = False
    monkeypatch.setattr(
        auditor, "audit_two_natural_food_cycles", lambda *a, **kw: verdict,
    )
    with pytest.raises(auditor.D9SurvivalAuditRejected):
        auditor.audit_d9(
            report, "\n".join([
                report["d9_third_paper_spawn"], idle_paper_lines(),
            ]),
            nonmotion_path=tmp_path/"a", motion_path=tmp_path/"b",
            s50_jsonl="",
        )
