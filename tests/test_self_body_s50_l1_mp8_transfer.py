"""MP8 offline tests: frozen MP7 prior, matched setup, no source promotion."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_l1_mp8_transfer import (
    DEFAULT_ARCHIVE,
    MP5_SLOPE,
    MP8Rejected,
    TargetSetup,
    freeze_matched_pair,
    score_pair,
    train_from_mp7,
)


def setup(condition: str, world: str, *, seed: str = "fixed-seed") -> TargetSetup:
    return TargetSetup(
        world_uuid=world, subject_uuid="same-body-uuid", seed=seed,
        condition=condition, matched_state_sha256="a" * 64,
        native_action_spec_sha256="b" * 64,
    )


def pair():
    prior = train_from_mp7()
    return freeze_matched_pair(
        prior, setup("NORMAL", "new-normal-world"),
        setup("PACKED_ICE", "new-ice-world"),
    )


def test_pinned_mp7_prior_only_training_not_transfer():
    model = train_from_mp7()
    assert model.previous_normal_slope == MP5_SLOPE
    assert model.sample_pairs == 7
    assert model.fitted_ice_slope == pytest.approx(0.4348785598, abs=1e-9)
    assert model.claim == "TRAINING_FIT_ONLY_NO_TRANSFER"
    assert model.source_world_uuid != "new-ice-world"


def test_mp7_tampering_or_symlink_refused(tmp_path):
    source = tmp_path / "source.json"
    source.write_bytes(DEFAULT_ARCHIVE.read_bytes() + b" ")
    with pytest.raises(MP8Rejected, match="bytes"):
        train_from_mp7(source)
    alias = tmp_path / "alias.json"
    alias.symlink_to(DEFAULT_ARCHIVE)
    with pytest.raises(MP8Rejected, match="missing"):
        train_from_mp7(alias)


def test_matched_pair_frozen_before_future_observation():
    ticket = pair()
    assert ticket.normal.seed == ticket.ice.seed
    assert ticket.training.surface == "PACKED_ICE"
    assert len(ticket.ticket_sha256) == 64
    assert ticket.claim == "OFFLINE_TICKET_ONLY"
    assert pair().ticket_sha256 == ticket.ticket_sha256


@pytest.mark.parametrize("change", [
    lambda p,n,i: (replace(n, seed="different"), i),
    lambda p,n,i: (n, replace(i, matched_state_sha256="c"*64)),
    lambda p,n,i: (n, replace(i, native_action_spec_sha256="d"*64)),
    lambda p,n,i: (n, replace(i, condition="NORMAL")),
    lambda p,n,i: (n, replace(i, world_uuid=n.world_uuid)),
    lambda p,n,i: (replace(n, world_uuid=p.source_world_uuid), i),
    lambda p,n,i: (n, replace(i, original_surface="STONE")),
    lambda p,n,i: (replace(n, matched_state_sha256="invalid"), i),
])
def test_unmatched_or_reused_world_denied(change):
    prior = train_from_mp7()
    normal, ice = change(prior, setup("NORMAL", "normal"), setup("PACKED_ICE", "ice"))
    with pytest.raises(MP8Rejected):
        freeze_matched_pair(prior, normal, ice)


def test_holdout_scoring_is_diagnostic_not_automatic_learning():
    t = pair()
    normal = [0.1, 0.02, 0.004, 0.0008, 0, 0, 0, 0]
    ice = [0.12, 0.06, 0.03, 0.015, 0.0075, 0.003, 0.002, 0.001]
    scored = score_pair(t, normal_motions=normal, ice_motions=ice)
    s = scored["score"]
    assert s["ice_updated_model_mae_m"] < s["ice_old_model_mae_m"]
    assert s["normal_old_model_mae_m"] < s["normal_wrong_ice_model_mae_m"]
    assert scored["same_information_cheap_linear"] == "MATHEMATICALLY_EQUIVALENT"
    assert scored["source_authenticity"] == "NOT_AUDITED_FROM_ORIGINAL_PAPER"
    assert scored["paired_physical_control"] == "NOT_ATTESTED"
    assert scored["transfer_claim"] == "UNDETERMINED"
    assert scored["qualification"] == "NO_GO"
    assert scored["science"] == "NOT_RUN"


@pytest.mark.parametrize("field", ["normal_motions", "ice_motions"])
def test_invalid_target_samples_rejected(field):
    sample = {
        "normal_motions": [0.1] * 8,
        "ice_motions": [0.1] * 8,
    }
    for invalid in ([0] * 7, [0] * 7 + [-1], [0] * 7 + [float("nan")], "fake"):
        with pytest.raises(MP8Rejected):
            score_pair(pair(), **{**sample, field: invalid})


def test_forged_frozen_ticket_denied():
    t = pair()
    with pytest.raises(MP8Rejected, match="mutation"):
        score_pair(replace(t, ticket_sha256="0" * 64),
                   normal_motions=[0.1]*8, ice_motions=[0.1]*8)
