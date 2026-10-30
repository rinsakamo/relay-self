"""G4.13: original G1 witness placement, no motor qualification."""
from copy import deepcopy
from dataclasses import asdict

import pytest

from adapters.mineflayer.g412_original_control_boundary_dwell_dev import (
    join_g412_original_control_boundary_dwell_dev,
)
from adapters.mineflayer.g413_original_g1_generation_witness_dev import (
    _classify,
    join_g413_original_g1_generation_witness_dev,
)
from test_s49_g412_original_control_boundary_dwell_dev import _args as g412_args


def _args():
    prior = g412_args()
    rows = [asdict(row) for row in join_g412_original_control_boundary_dwell_dev(
        **prior,
    )]
    return {**prior, "g412_rows": rows}


def test_g413_original_paper_g1_and_challenge_witnesses_preserved():
    args = _args()
    snapshot = deepcopy(args)
    out = join_g413_original_g1_generation_witness_dev(**args)
    assert args == snapshot
    assert [item.source_seq for item in out] == [12, 20]
    assert len(out) == len(args["g412_rows"])
    for current, earlier in zip(out, args["g412_rows"]):
        assert current.source_seq == earlier["source_seq"]
        assert current.original_generation_paper_worldticks == earlier[
            "observed_generation_worldtick_count"
        ]
        assert current.stable_candidate_worldticks == earlier[
            "observed_same_generation_stable_g1_frames"
        ]
        assert current.post_control_challenge_worldticks == earlier[
            "observed_same_generation_post_control_frames"
        ]
        assert len(current.original_g412_row_sha256) == 64
        assert all(len(x) == 64
                   for x in current.original_generation_paper_frame_sha256)
        assert current.original_unknown_unchanged
        assert current.original_g1_classification_unchanged
        assert current.original_t2_p1_m0_untouched
        assert not current.physics_tick_packet_acceptance_attested
        assert not current.real_motor_latency_inferred
        assert not current.physical_wait_inferred
        assert not current.extra_motor_or_reader
    assert [row.stable_candidate_worldticks for row in out] == [1, 1]
    assert [row.original_generation_paper_worldticks for row in out] == [2, 2]


@pytest.mark.parametrize(("count", "stable", "after", "both", "expected"), [
    (1, 0, 0, 0, "ONLY_ONE_ORIGINAL_PAPER_GENERATION_FRAME"),
    (2, 0, 0, 0, "MULTIPLE_FRAMES_NO_STABLE_G1_OR_POST_CONTROL_CHALLENGE"),
    (3, 0, 2, 0, "MULTIPLE_FRAMES_WITH_CHALLENGE_G1_REMAINS_NONSTABLE"),
    (2, 1, 0, 0, "ORIGINAL_G1_STABLE_KIND_BUT_NO_POST_CONTROL_CHALLENGE"),
    (3, 1, 1, 0, "ORIGINAL_G1_STABLE_AND_CHALLENGE_ON_SEPARATE_FRAMES"),
    (4, 2, 2, 1, "ORIGINAL_G1_STABLE_KIND_AND_POST_CONTROL_PRESENT_NOT_CAUSAL_GAIT"),
    (0, 0, 0, 0, "NO_BOUNDED_ORIGINAL_PAPER_GENERATION"),
])
def test_g413_observational_categories(count, stable, after, both, expected):
    assert _classify(count=count, stable=stable, after=after,
                     both=both) == expected


@pytest.mark.parametrize("mutation", [
    "g412_class", "g412_kind_count", "g412_tick", "g412_sha",
    "g411_rewrite", "g410_rewrite", "g49_rewrite", "original_t2_p1",
    "g44_effect_id", "foreign_paper", "duplicate_paper",
    "paper_g1_kind", "post_control_challenge",
])
def test_g413_fail_closed_on_relabelled_or_cross_session_sources(mutation):
    args = _args()
    if mutation == "g412_class":
        args["g412_rows"][0]["original_effect_evidence_class"] = "FORGED"
    elif mutation == "g412_kind_count":
        args["g412_rows"][0]["observed_same_generation_stable_g1_frames"] = 999
    elif mutation == "g412_tick":
        args["g412_rows"][0]["observed_generation_last_tick"] += 1
    elif mutation == "g412_sha":
        args["g412_rows"][0]["original_g411_row_sha256"] = "0" * 64
    elif mutation == "g411_rewrite":
        args["g411_rows"][0]["evidence_class"] = "FORGED"
    elif mutation == "g410_rewrite":
        args["g410_rows"][0]["original_g1_kind"] = "FORGED"
    elif mutation == "g49_rewrite":
        args["g49_rows"][0]["source_gap_class"] = "FORGED"
    elif mutation == "original_t2_p1":
        args["t2_rows"][0]["p1"] = {"forged": True}
    elif mutation == "g44_effect_id":
        args["original_transition_acks"][0]["transition_effect_id"] = "FORGED"
    elif mutation == "foreign_paper":
        args["paper_rows"][0]["session_id"] = "FORGED"
    elif mutation == "duplicate_paper":
        args["paper_rows"].append(dict(args["paper_rows"][-1]))
    elif mutation == "paper_g1_kind":
        args["paper_rows"][1]["kind"] = "FORGED"
    else:
        args["paper_rows"][1]["g46_challenge_after_control_dev"] = "FORGED"
    with pytest.raises(ValueError, match=r"G4\.(9|10|11|12|13)"):
        join_g413_original_g1_generation_witness_dev(**args)


def test_g413_does_not_promote_stable_kind_without_original_challenge():
    args = _args()
    out = join_g413_original_g1_generation_witness_dev(**args)
    assert all(item.original_unknown_unchanged for item in out)
    assert all(item.original_g1_classification_unchanged for item in out)
    assert sum(item.stable_candidate_worldticks for item in out) == 2
