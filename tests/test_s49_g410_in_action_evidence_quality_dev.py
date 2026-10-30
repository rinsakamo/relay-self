"""G4.10 inspect G4.9 UNKNOWN evidence without touching original accounting."""
from copy import deepcopy
from dataclasses import asdict

import pytest

from adapters.mineflayer.g410_in_action_evidence_quality_dev import (
    join_g410_in_action_evidence_dev,
)
from adapters.mineflayer.g49_original_action_gap_census_dev import (
    join_g49_original_action_gap_census_dev,
)
from test_s49_g49_original_action_gap_census_dev import _args


def _source():
    original = _args()
    g49 = [asdict(row) for row in join_g49_original_action_gap_census_dev(
        **original,
    )]
    return {
        "session_id": original["session_id"],
        "g49_rows": g49,
        "g48_rows": original["g48_rows"],
        "paper_rows": original["paper_rows"],
        "t2_rows": original["t2_rows"],
    }


def test_g410_only_inspects_original_in_action_unknown_preserving_all_sources():
    source = _source()
    snapshot = deepcopy(source)
    rows = join_g410_in_action_evidence_dev(**source)
    assert source == snapshot
    assert len(rows) == 4
    assert [r.original_s49_mode for r in rows] == [
        "RUN", "RUN", "JOG", "WALK",
    ]
    assert [r.source_seq for r in rows] == [12, 20, 26, 32]
    assert all(r.remains_unknown and not r.full_physics_tick_gait_attested
               and not r.physical_wait_or_idle_inferred
               and not r.new_p1_or_m0_posting
               and r.additional_native_readers_or_t2_owners == 0
               for r in rows)
    assert all(len(r.original_g49_row_sha256) == 64
               and len(r.original_g48_row_sha256) == 64
               and len(r.original_t2_row_sha256) == 64 for r in rows)
    assert all("POST_CONTROL_CHALLENGE" in r.missing_evidence_axes
               for r in rows)
    assert rows[2].original_g48_status == "UNKNOWN_DIRECT_PRECHANGE_CHALLENGE"


def test_g410_g1_stable_kind_does_not_override_absent_after_control():
    a = _source()
    target_seq = 26
    row = next(row for row in a["paper_rows"] if row["source_seq"] == target_seq)
    row["kind"] = "STABLE_ORDINARY_FORWARD_CANDIDATE"
    idx = next(i for i, row in enumerate(a["g49_rows"])
               if row["source_seq"] == target_seq)
    a["g49_rows"][idx]["original_paper_g1_kind"] = row["kind"]
    a["g48_rows"][idx]["original_g1_kind"] = row["kind"]
    import hashlib
    import json
    a["g49_rows"][idx]["original_g48_row_sha256"] = hashlib.sha256(
        json.dumps(a["g48_rows"][idx], sort_keys=True,
                   separators=(",", ":")).encode(),
    ).hexdigest()
    out = join_g410_in_action_evidence_dev(**a)
    matched = next(r for r in out if r.source_seq == target_seq)
    assert matched.g1_two_sample_stable_kind == "G1_RECORDED_STABLE_KIND"
    assert "POST_CONTROL_CHALLENGE" in matched.missing_evidence_axes
    assert matched.remains_unknown


@pytest.mark.parametrize("mutation", [
    "t2_p1", "g48_status", "g49_sha", "paper_tick", "paper_duplicate",
    "foreign_session", "not_in_action", "out_of_bracket", "bad_g3_debit",
])
def test_g410_refuses_forged_mixed_or_rewritten_sources(mutation):
    a = _source()
    target = next(i for i, row in enumerate(a["g49_rows"])
                  if row["source_gap_class"].startswith("UNKNOWN_INSIDE_APPLIED"))
    if mutation == "t2_p1":
        a["t2_rows"][target]["p1"] = {"forged": True}
    elif mutation == "g48_status":
        a["g48_rows"][target]["status"] = "DIRECT_SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV"
    elif mutation == "g49_sha":
        a["g49_rows"][target]["original_g48_row_sha256"] = "0" * 64
    elif mutation == "paper_tick":
        seq = a["t2_rows"][target]["source_seq"]
        next(r for r in a["paper_rows"] if r["source_seq"] == seq)["world_tick"] += 1
    elif mutation == "paper_duplicate":
        a["paper_rows"].append(dict(a["paper_rows"][-1]))
    elif mutation == "foreign_session":
        a["g49_rows"][target]["session_id"] = "wrong"
    elif mutation == "not_in_action":
        a["g49_rows"][target]["original_s49_requested_mode"] = "DASH"
    elif mutation == "out_of_bracket":
        a["g49_rows"][target]["original_s15_clear_ack_seq"] = 1
    else:
        a["t2_rows"][target]["g3_extra_m0_paid_dev"] = 0.01
        import hashlib
        import json
        updated = hashlib.sha256(json.dumps(
            a["t2_rows"][target], sort_keys=True,
            separators=(",", ":"),
        ).encode()).hexdigest()
        a["g48_rows"][target]["original_t2_row_sha256"] = updated
        a["g49_rows"][target]["original_t2_row_sha256"] = updated
        a["g49_rows"][target]["original_g48_row_sha256"] = hashlib.sha256(
            json.dumps(a["g48_rows"][target], sort_keys=True,
                       separators=(",", ":")).encode(),
        ).hexdigest()
    with pytest.raises(ValueError, match="G4.10"):
        join_g410_in_action_evidence_dev(**a)


def test_g410_no_active_action_is_not_a_wait_or_gait_qualification():
    a = _source()
    # The original census may be dominated by non-Action passive/tail ticks.
    # They are checked but never turned into G4.10 physical evidence rows.
    all_g49 = a["g49_rows"]
    rows = join_g410_in_action_evidence_dev(**a)
    assert len(rows) == sum(
        row["source_gap_class"].startswith("UNKNOWN_INSIDE_APPLIED_")
        for row in all_g49
    )
    assert all(row.remains_unknown for row in rows)
