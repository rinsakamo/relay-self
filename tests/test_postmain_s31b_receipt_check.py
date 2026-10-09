"""Negative receipt checks only; no fake World, network or process launch."""
import copy
import json
from pathlib import Path

import pytest

from adapters.mineflayer.s31b_receipt_check import check_receipt

ROOT = Path(__file__).resolve().parents[1]


def receipt():
    return json.loads((ROOT / "docs/s31b-evidence/local-001/s31a-report.json").read_text())


def test_original_local_receipt_consistency():
    check_receipt(receipt())


@pytest.mark.parametrize("field,value", [
    ("status", "BLOCKED"), ("server_exit_code", -9), ("bridge_exit_code", None),
    ("node_test_shim", True), ("real_mineflayer_package", False),
    ("server_sha1", "0" * 40), ("server_size_bytes", 1),
    ("server_port", 25566), ("mineflayer_version", "4.38.0"),
    ("bridge_exit_code", False), ("duplicate_rejected_seq", 1),
    ("session_id", "wrong-session"), ("last_world_probe_id", "other"),
])
def test_invalid_receipt_cannot_pass(field, value):
    report = receipt()
    report[field] = value
    with pytest.raises(ValueError):
        check_receipt(report)


@pytest.mark.parametrize("field,value", [
    ("coverage_truncated", True), ("coverage_candidates", 17),
    ("request_id", "s31a-target:999"), ("distance_m", 3),
    ("entity_position", [float("nan"), -60, 2.5]),
    ("entity_position", [20, -60, 2.5]), ("observation_seq", 2),
    ("provenance", "fabricated"),
])
def test_inconsistent_native_evidence_cannot_pass(field, value):
    report = copy.deepcopy(receipt())
    report["target"][field] = value
    with pytest.raises(ValueError):
        check_receipt(report)


def test_missing_measurement_cannot_pass():
    report = receipt()
    del report["target"]
    with pytest.raises(KeyError):
        check_receipt(report)
