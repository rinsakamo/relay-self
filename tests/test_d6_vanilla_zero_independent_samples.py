"""D6-D6 source-only target adjudication: multiple NEW Worlds, never replay.

Pure synthetic test input stands only for post-audit outputs; this is NOT a
real Paper World qualification. The physical workflow runs all originals.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from tools.bug0_d6_vanilla_zero_samples import (
    NaturalZeroSampleRejected,
    _assert_grant,
    _sha_manifest,
    judge_independent_sample,
)


def _source(*, natural: tuple[int, ...]) -> tuple[dict, dict]:
    assert natural and (len(natural) == 1 or natural[0] == 0)
    generations = []
    for i, amount in enumerate(natural):
        generations.append({
            "generation": i+1,
            "real_rotten_count": amount,
            "native_zombie_id": i+17,
            "paper_zombie_uuid": f"real-world-zombie-uuid-{i+1}",
            "death_tick": 70 + 630*i,
            "respawn_tick": 670+630*i if i < len(natural)-1 else None,
            "action_ids": [f"new-original-s49-attack-id-{i+1}"],
        })
    report = {
        "status": "PASS_DEV",
        "node_exit": 0,
        "java_exit": 0,
        "cleanup_done": True,
        "d6_multigen_source_natural_drop_rng_unchanged": True,
        "d6_multigen_operator_forced_zero": False,
        "d6_multigen_generations": generations,
    }
    audited = {
        "status": "PASS_DEV",
        "operator_forced_zero_not_vanilla_rng": False,
        "same_supervisor_retained": True,
        "all_real_respawns_world_600_ticks": True,
        "unresolved_nonmotion": False,
        "unresolved_motion": False,
        "no_eat_after_move": True,
        "completed_original_s49_kill_generations": len(generations),
        "original_attack_count": len(generations),
        "original_move_count": 0 if natural[0] == 0 else 1,
        "natural_counts": list(natural),
        "paper_world_uuid": "new-paper-world-uuid",
        "session_id": "fresh-native-self-session",
        "natural_item_uuid": "actual-Paper-item-uuid" if natural[0] else None,
        "classification": (
            "D6_MULTIGEN_FIRST_REAL_NATURAL_MOVE_PICKUP_EAT_FENCED_PASS"
            if natural[0] > 0 else
            "D6_MULTIGEN_ZERO_DROP_CONTINUE_THEN_REAL_MOVE_PICKUP_PASS"
        ),
    }
    return report, audited


def test_positive_first_world_fully_closes_but_must_sample_another_new_world():
    report, audited = _source(natural=(1,))
    answer = judge_independent_sample(report, audited)
    assert answer["natural_counts"] == [1]
    assert answer["original_s49_attack_count"] == 1
    assert answer["original_s49_move_count"] == 1
    assert not answer["genuine_natural_zero_to_new_s49_attack_proven"]
    assert answer["classification"].endswith("ZERO_NOT_SEEN")
    assert answer["previous_world_clean_independently_attested"] is True


def test_real_zero_to_next_real_original_s49_attack_is_qualified():
    report, audited = _source(natural=(0, 2))
    audited["original_move_count"] = 2
    x = judge_independent_sample(report, audited)
    assert x["natural_counts"] == [0, 2]
    assert x["completed_generations"] == 2
    assert x["genuine_natural_zero_to_new_s49_attack_proven"]
    assert x["classification"].endswith("ORIGINAL_S49_ATTACK_PASS")
    assert not x["self_eat_after_move"]


def test_four_real_zero_generations_also_qualify_continuation():
    report, audited = _source(natural=(0, 0, 0, 0))
    audited["classification"] = "D6_MULTIGEN_BOUNDED_FOUR_TRUE_ZERO_DROPS_PASS"
    x = judge_independent_sample(report, audited)
    assert x["genuine_natural_zero_to_new_s49_attack_proven"]
    assert x["original_s49_attack_count"] == 4


@pytest.mark.parametrize("alter", [
    ("report", "d6_multigen_operator_forced_zero", True),
    ("report", "d6_multigen_source_natural_drop_rng_unchanged", False),
    ("report", "cleanup_done", False),
    ("report", "node_exit", None),
    ("audit", "operator_forced_zero_not_vanilla_rng", True),
    ("audit", "all_real_respawns_world_600_ticks", False),
    ("audit", "unresolved_nonmotion", True),
    ("audit", "unresolved_motion", True),
    ("audit", "original_attack_count", 0),
    ("audit", "natural_counts", [0]),
])
def test_uncertain_physical_source_never_allows_next_world(alter):
    report, audited = _source(natural=(1,))
    source, key, value = alter
    obj = report if source == "report" else audited
    obj[key] = value
    with pytest.raises(NaturalZeroSampleRejected):
        judge_independent_sample(report, audited)


def test_no_new_world_when_same_positive_first_lacks_genuine_pickup():
    report, audited = _source(natural=(1,))
    audited["natural_item_uuid"] = None
    with pytest.raises(NaturalZeroSampleRejected, match="neither verified"):
        judge_independent_sample(report, audited)


@pytest.mark.parametrize("mutation", [
    ("respawn_tick", 671),
    ("paper_zombie_uuid", "real-world-zombie-uuid-1"),
    ("native_zombie_id", 17),
    ("action_ids", []),
    ("death_tick", 660),
])
def test_real_zero_requires_new_generation_tick_entity_and_real_attack(mutation):
    report, audited = _source(natural=(0, 1))
    audited["original_move_count"] = 1
    key, value = mutation
    if key == "respawn_tick":
        report["d6_multigen_generations"][0][key] = value
    else:
        report["d6_multigen_generations"][1][key] = value
    with pytest.raises(NaturalZeroSampleRejected):
        judge_independent_sample(report, audited)


def test_preflight_rejects_new_world_without_separate_source_scope(monkeypatch, tmp_path):
    for key in (
        "S49_REAL_SERVER_CI", "BUG0_S49_D4_ONE_WORLD_ONLY",
        "S49_D5_NONMOTION_FENCE_DEV_ONLY",
        "D6_NATURAL_DROP_MOVE_WORLD_ONLY",
        "D6_NATURAL_MULTIGEN_WORLD_ONLY",
        "D6_VANILLA_REPLICATES_WORLD_ONLY",
    ):
        monkeypatch.delenv(key, raising=False)
    root=tmp_path/"would-be-minecraft"
    with pytest.raises(NaturalZeroSampleRejected):
        _assert_grant(4, root)
    assert not root.exists()


def test_manifest_is_deterministic_and_does_not_hash_itself(tmp_path):
    (tmp_path/"z-original.json").write_text("test",encoding="utf8")
    (tmp_path/"a-paper.log").write_text("original",encoding="utf8")
    _sha_manifest(tmp_path)
    a=(tmp_path/"SHA256SUMS.txt").read_text()
    _sha_manifest(tmp_path)
    assert a==(tmp_path/"SHA256SUMS.txt").read_text()
    assert "SHA256SUMS.txt" not in a
    assert "a-paper.log" in a and "z-original.json" in a


def test_audit_requires_verifiable_real_native_counts():
    report, audited = _source(natural=(0, 1))
    altered=deepcopy(audited)
    altered["natural_counts"]=[1, 0]
    with pytest.raises(NaturalZeroSampleRejected):
        judge_independent_sample(report, altered)
