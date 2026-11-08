"""D8 independent audit must never promote one cycle or second zero into two."""
from __future__ import annotations

import pytest

from tools.bug0_d8_two_natural_food_post import (
    D8TwoCycleAuditRejected,
    audit_two_natural_food_cycles,
)


@pytest.mark.parametrize("mutant", [
    {},
    {"status": "PASS_DEV"},
    {"status": "PASS_DEV", "d8_two_generation_optin": True},
    {"status": "PASS_DEV", "d8_two_generation_optin": True,
     "d8_second_generation_food_proven": True},
    {"status": "PASS_DEV", "d8_two_generation_optin": True,
     "d8_second_generation_food_proven": True, "self_eat": True},
])
def test_one_original_world_report_cannot_claim_two_natural_food_cycles(
    mutant, tmp_path,
):
    with pytest.raises(D8TwoCycleAuditRejected):
        audit_two_natural_food_cycles(
            mutant, "",
            nonmotion_path=tmp_path/"absent-original-nonmotion.json",
            motion_path=tmp_path/"absent-original-motion.json",
        )


def test_operator_staged_item_never_qualifies_second_natural_food(tmp_path):
    with pytest.raises(D8TwoCycleAuditRejected):
        audit_two_natural_food_cycles(
            {
                "status": "PASS_DEV", "real_world_started": True,
                "d8_two_generation_optin": True,
                "node_exit": 0, "java_exit": 0, "cleanup_done": True,
                "original_action_issuer": "S49", "real_model_calls": 0,
                "learning_updated": False, "self_eat": True,
            },
            "RSELF_LOOT_STAGED world=forged",
            nonmotion_path=tmp_path/"missing-eat-ledger",
            motion_path=tmp_path/"missing-move-ledger",
        )


@pytest.mark.parametrize("spoof", [
    {}, {"status": "PASS_DEV"},
    {
        "status": "PASS_DEV",
        "d8_first_true_zero_food_not_exercised": True,
        "d8_two_generation_optin": True,
        "real_rotten_flesh_count": 0,
    },
])
def test_fake_first_zero_requires_original_real_paper_and_attack_ledger(
    spoof, tmp_path,
):
    bogus = {**spoof, "d8_first_true_zero_food_not_exercised": True}
    with pytest.raises(D8TwoCycleAuditRejected):
        audit_two_natural_food_cycles(
            bogus,
            "RSELF_NATURAL_DROP_DEATH source=fabricated rotten_count=0",
            nonmotion_path=tmp_path/"no-S49-original-attack.json",
            motion_path=tmp_path/"no-C1-original-move.json",
        )


def test_original_c1_fence_readback_counts_both_s49_intent_epochs():
    from tools.bug0_d4_oneworld import require_d8_original_motion_history

    expected = [
        {"action_id": f"gen1-move-{i}", "terminal": "outcome",
         "intent_id": "old-intent", "s15_clear_seq": i * 11}
        for i in (1, 2)
    ] + [
        {"action_id": "gen2-move-1", "terminal": "outcome",
         "intent_id": "new-intent", "s15_clear_seq": 33}
    ]
    actual = [
        {"action_id": row["action_id"], "status": "S16_OUTCOME",
         "action_ref": "MOVE_BACKWARD", "intent_id": row["intent_id"],
         "cleanup_seq": row["s15_clear_seq"]}
        for row in expected
    ]
    # OriginalS49PhysicalFence.actions is an immutable tuple, not a list.
    # Exercise the real API shape rather than merely a mutable test list.
    require_d8_original_motion_history(tuple(actual), expected)
    require_d8_original_motion_history(actual, expected)
    # R9 original regression: the old D6-only final count would compare
    # len(actual)==3 to len(gen1)==2 and reject a true second EAT.
    assert len(actual) == 3 and len(expected[:2]) == 2
    require_d8_original_motion_history([], [])


@pytest.mark.parametrize("mutant", [
    "missing_gen2", "reordered", "duplicate_id", "wrong_s16",
    "wrong_second_intent", "forged_s15_clear", "invalid_source_type",
    "invalid_journal_container",
])
def test_d8_final_c1_two_epoch_negative_controls(mutant):
    from tools.bug0_d4_oneworld import (
        S49D3Rejected,
        require_d8_original_motion_history,
    )

    expected = [
        {"action_id": "d6-gen1-move-1", "terminal": "outcome",
         "intent_id": "old", "s15_clear_seq": 11},
        {"action_id": "d8-gen2-move-1", "terminal": "outcome",
         "intent_id": "new", "s15_clear_seq": 31},
    ]
    actual = [
        {"action_id": row["action_id"], "status": "S16_OUTCOME",
         "action_ref": "MOVE_BACKWARD", "intent_id": row["intent_id"],
         "cleanup_seq": row["s15_clear_seq"]}
        for row in expected
    ]
    if mutant == "missing_gen2":
        expected = expected[:1]
    elif mutant == "reordered":
        actual.reverse()
    elif mutant == "duplicate_id":
        expected[1]["action_id"] = expected[0]["action_id"]
    elif mutant == "wrong_s16":
        actual[-1]["status"] = "PREPARED_UNRESOLVED"
    elif mutant == "wrong_second_intent":
        actual[-1]["intent_id"] = "old"
    elif mutant == "forged_s15_clear":
        actual[-1]["cleanup_seq"] = 999
    elif mutant == "invalid_source_type":
        expected = {"not": "two-epoch-list"}
    elif mutant == "invalid_journal_container":
        actual = {"forged": "physical journal"}
    with pytest.raises(S49D3Rejected):
        require_d8_original_motion_history(actual, expected)


def test_d8_first_genuine_zero_natural_drop_needs_no_move_history():
    from tools.bug0_d4_oneworld import (
        d8_reported_original_move_records,
        require_d8_original_motion_history,
    )
    first_zero = {
        "d8_first_true_zero_food_not_exercised": True,
        "real_rotten_flesh_count": 0,
        "d8_second_generation_food_proven": False,
        "self_eat": False,
    }
    # Actual R14 report omits both generation MOVE lists because no
    # item existed. The physically empty C1 file is the correct evidence.
    assert d8_reported_original_move_records(first_zero) == []
    require_d8_original_motion_history((), [])
    assert d8_reported_original_move_records({
        **first_zero, "d6_original_s49_move_actions": [],
    }) == []


@pytest.mark.parametrize("mutant", [
    {"real_rotten_flesh_count": 1},
    {"d8_second_generation_food_proven": True},
    {"self_eat": True},
    {"d6_original_s49_move_actions": [{"action_id": "forged"}]},
    {"d6_original_s49_move_actions": ()},
    {"d8_second_generation": {"d6_original_s49_move_actions": []}},
])
def test_d8_first_zero_rejects_spoofed_action_or_second_generation(mutant):
    from tools.bug0_d4_oneworld import (
        S49D3Rejected,
        d8_reported_original_move_records,
    )
    report = {
        "d8_first_true_zero_food_not_exercised": True,
        "real_rotten_flesh_count": 0,
        "d8_second_generation_food_proven": False,
        "self_eat": False,
        **mutant,
    }
    with pytest.raises(S49D3Rejected):
        d8_reported_original_move_records(report)


def test_d8_positive_drop_requires_both_explicit_generation_sources():
    from tools.bug0_d4_oneworld import (
        S49D3Rejected, d8_reported_original_move_records,
    )
    first = [{"action_id": "gen1", "terminal": "outcome"}]
    second = [{"action_id": "gen2", "terminal": "outcome"}]
    report = {
        "real_rotten_flesh_count": 1,
        "d8_first_true_zero_food_not_exercised": False,
        "d8_second_generation": {"d6_original_s49_move_actions": second},
    }
    with pytest.raises(S49D3Rejected):
        d8_reported_original_move_records(report)
    report["d6_original_s49_move_actions"] = first
    assert d8_reported_original_move_records(report) == first + second
    report["d8_second_generation"]["d6_original_s49_move_actions"] = ()
    with pytest.raises(S49D3Rejected):
        d8_reported_original_move_records(report)
