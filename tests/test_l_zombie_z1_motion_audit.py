"""Pure synthetic 31-tick Paper motion audit (NOT a physical proof)."""
from __future__ import annotations

import hashlib
import json

import pytest

from test_l_zombie_paper_original_audit import raw_lines
from tools.l_zombie_paper_original_audit import PaperZombieSourceRejected
from tools.l_zombie_z1_motion_audit import audit_z1b_movement, main


def audited(raw):
    return audit_z1b_movement(
        raw, sha256=hashlib.sha256(raw).hexdigest(),
        marker="z1-1", session="s1",
    )


def test_synthetic_moving_zombie_source_and_exact_future():
    raw = raw_lines()
    result = audited(raw)
    assert result["movement_observed"] is True
    assert result["net_horizontal_displacement_m"] == pytest.approx(3)
    assert result["total_path_length_m"] == pytest.approx(3)
    assert result["target_tick"] - result["freeze_reference_tick"] == 20
    assert result["sample_count"] == 31
    assert result["causal_pursuit_attested"] is False
    assert result["client_paper_tick_join_attested"] is False
    assert result["real_gemma_hypothesis"] is False


def test_stationary_paper_is_real_source_but_not_moving():
    raw = raw_lines()
    for i in range(31):
        raw = raw.replace(
            f"x={i / 10:.12f}".encode(), b"x=0.000000000000",
        )
    result = audited(raw)
    assert result["movement_observed"] is False
    assert result["classification"] == "Z1B_PAPER_SOURCE_VALID_BUT_MOTION_NOT_ESTABLISHED"
    assert result["net_horizontal_displacement_m"] == 0


def test_teleport_in_valid_shape_is_rejected():
    raw = raw_lines().replace(b"x=1.000000000000", b"x=8.000000000000", 1)
    with pytest.raises(PaperZombieSourceRejected, match="teleport"):
        audited(raw)


@pytest.mark.parametrize("mutation", [
    {"gap": 13}, {"missing": 10}, {"changed": True},
    {"end": "ENTITY_REMOVED"}, {"duplicate": 20},
])
def test_gap_loss_replacement_or_duplicate_not_scored(mutation):
    with pytest.raises(PaperZombieSourceRejected):
        audited(raw_lines(**mutation))


def test_cli_exclusive_create_original_sha_and_unqualified_cause(tmp_path):
    original = tmp_path / "paper.raw"
    report = tmp_path / "review.json"
    raw = raw_lines()
    original.write_bytes(raw)
    args = [
        "--paper-original", str(original),
        "--sha256", hashlib.sha256(raw).hexdigest(),
        "--marker", "z1-1", "--session", "s1",
        "--report", str(report),
    ]
    assert main(args) == 0
    value = json.loads(report.read_text())
    assert value["movement_observed"] is True
    assert value["causal_pursuit_attested"] is False
    assert main(args) == 2
    assert original.read_bytes() == raw


def test_cli_failure_does_not_issue_false_movement(tmp_path):
    original = tmp_path / "paper.raw"
    report = tmp_path / "review.json"
    raw = raw_lines()
    original.write_bytes(raw)
    args = [
        "--paper-original", str(original),
        "--sha256", "0"*64,
        "--marker", "z1-1", "--session", "s1",
        "--report", str(report),
    ]
    assert main(args) == 2
    assert not report.exists()
