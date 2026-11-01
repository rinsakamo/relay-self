"""MP9 exact-source material routing; offline synthetic fixtures NEVER World evidence."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_l1_mp9_selector import (
    SOURCE_PATH,
    MP9Rejected,
    compare_pair,
    evaluate_frozen_shadow,
    freeze_from_paper_lock,
    train_mp8_only,
)


def lock(mode="NORMAL", world="new-target-world"):
    return {
        "status": "REAL_PAPER_PRE_ACTION_SURFACE_LOCK",
        "mode": "GRASS_BLOCK_5X5_READONLY" if mode == "NORMAL" else "PACKED_ICE_5X5",
        "target_material": "GRASS_BLOCK" if mode == "NORMAL" else "PACKED_ICE",
        "original_material": "GRASS_BLOCK", "blocks_verified": "25",
        "on_ground": "true", "world": world, "subject_uuid": "actual-target-subject",
    }


def test_source_mp8_exact_provenance_and_no_mp9_in_sample_fit():
    prior = train_mp8_only()
    assert prior.normal_slope == pytest.approx(0.5701332477105613)
    assert prior.ice_slope == pytest.approx(0.6052193469653747)
    assert prior.pairs_per_surface == 7
    assert len(prior.source_worlds) == 2
    assert prior.status == "DEV_ARCHIVAL_TRAINING_FIT_ONLY"


def test_mutation_and_symlink_source_fail_closed(tmp_path):
    raw = SOURCE_PATH.read_bytes()
    changed = tmp_path / "modified.json"
    changed.write_bytes(raw + b" ")
    with pytest.raises(MP9Rejected, match="blob"):
        train_mp8_only(changed)
    alias = tmp_path / "alias.json"
    alias.symlink_to(SOURCE_PATH)
    with pytest.raises(MP9Rejected):
        train_mp8_only(alias)
    edited = tmp_path / "edited.json"
    data = json.loads(raw)
    data["motion"]["normal_wait_m"][0] = 42.0
    edited.write_text(json.dumps(data))
    with pytest.raises(MP9Rejected):
        train_mp8_only(edited)


def test_preaction_surface_routes_to_different_frozen_prior():
    p = train_mp8_only()
    n = freeze_from_paper_lock(p, lock("NORMAL"), mode="NORMAL")
    i = freeze_from_paper_lock(p, lock("ICE"), mode="ICE")
    assert n.selected_slope == p.normal_slope
    assert i.selected_slope == p.ice_slope
    assert n.selected_slope != i.selected_slope
    assert n.ticket_sha256 != i.ticket_sha256
    assert n.decision == "PAPER_SOURCE_CONDITIONED_READONLY_SHADOW"


@pytest.mark.parametrize("tamper", [
    lambda x: {**x, "mode": "PACKED_ICE_5X5"},
    lambda x: {**x, "target_material": "PACKED_ICE"},
    lambda x: {**x, "blocks_verified": "24"},
    lambda x: {**x, "on_ground": "false"},
    lambda x: {**x, "status": "CLAIM_ONLY"},
    lambda x: {**x, "world": ""},
    lambda x: {**x, "world": train_mp8_only().source_worlds[0]},
])
def test_wrong_or_reused_paper_source_rejected(tamper):
    with pytest.raises(MP9Rejected):
        freeze_from_paper_lock(train_mp8_only(), tamper(lock()), mode="NORMAL")


def test_foreign_prior_and_future_observation_rejected():
    p = train_mp8_only()
    ticket = freeze_from_paper_lock(p, lock(), mode="NORMAL")
    samples = [0.1] * 8
    with pytest.raises(MP9Rejected):
        freeze_from_paper_lock(replace(p, normal_slope=0.5), lock(), mode="NORMAL")
    with pytest.raises(MP9Rejected):
        evaluate_frozen_shadow(p, replace(ticket, ticket_sha256="0"*64),
                               motions=samples, verified_surface="GRASS_BLOCK")
    with pytest.raises(MP9Rejected):
        evaluate_frozen_shadow(p, ticket, motions=samples,
                               verified_surface="PACKED_ICE")
    with pytest.raises(MP9Rejected):
        evaluate_frozen_shadow(p, ticket, motions=[0.1]*7,
                               verified_surface="GRASS_BLOCK")


def test_scoring_not_claimed_as_qualified_learning():
    p = train_mp8_only()
    a = freeze_from_paper_lock(p, lock(), mode="NORMAL")
    b = freeze_from_paper_lock(p, lock("ICE", world="fresh-ice"), mode="ICE")
    normal = evaluate_frozen_shadow(
        p, a, motions=[0.1, 0.055, 0.03, 0.017, 0.01, 0.005, 0.003, 0.001],
        verified_surface="GRASS_BLOCK",
    )
    ice = evaluate_frozen_shadow(
        p, b, motions=[0.15, 0.09, 0.05, 0.03, 0.017, 0.01, 0.006, 0.003],
        verified_surface="PACKED_ICE",
    )
    contrast = compare_pair(normal, ice)
    assert contrast["cheap_material_rule_equivalent"]
    assert contrast["l1_unique_advantage"] is False
    assert normal["learning_admissions"] == ice["learning_admissions"] == 0
    assert contrast["qualification"] == "NO_GO"
    assert contrast["science"] == "NOT_RUN"


def test_pair_without_both_materials_is_refused():
    p = train_mp8_only()
    ticket = freeze_from_paper_lock(p, lock(), mode="NORMAL")
    sample = evaluate_frozen_shadow(
        p, ticket, motions=[0.1]*8, verified_surface="GRASS_BLOCK",
    )
    with pytest.raises(MP9Rejected):
        compare_pair(sample, sample)
