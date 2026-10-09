"""Offline consistency check of an existing receipt; never physical qualification."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def check_receipt(report: dict[str, Any]) -> None:
    """Reject incomplete or inconsistent PASS receipts, without starting processes."""
    expected = {
        "milestone": "S31-A",  # Original frozen runner identity is preserved.
        "status": "PASS",
        "stage": "SUCCESS",
        "minecraft_version": "1.21.8",
        "mineflayer_version": "4.39.0",
        "java_major_version": 21,
        "server_host": "127.0.0.1",
        "server_port": 25565,
        "server_sha1": "6bce4ef400e4efaa63a13d5e6f6b500be969ef81",
        "server_size_bytes": 57555044,
        "real_minecraft_server": True,
        "real_mineflayer_package": True,
        "node_test_shim": False,
        "bridge_exit_code": 0,
        "server_exit_code": 0,
        "action_issued": False,
        "autonomous_cognition": False,
        "world_evidence_projected_into_s27": False,
    }
    for key, value in expected.items():
        if type(report.get(key)) is not type(value) or report[key] != value:
            raise ValueError(f"invalid receipt field: {key}")
    target = report["target"]
    initial = report["initial_probe"]
    request_id = target["request_id"]
    if (
        initial["request_id"] != "s31a-initial:001"
        or request_id not in {f"s31a-target:{i:03d}" for i in range(5)}
        or request_id != report["last_world_probe_id"]
        or target["name"] != "zombie"
        or type(target["entity_id"]) is not int
        or target["coverage_scope"] != "mineflayer_entity_registry"
        or type(target["coverage_candidates"]) is not int
        or not 1 <= target["coverage_candidates"] <= 16
        or target["coverage_truncated"] is not False
    ):
        raise ValueError("invalid target/correlation/coverage")
    seqs = [report["spawn_seq"], initial["seq"], target["observation_seq"],
            report["duplicate_rejected_seq"]]
    if any(type(s) is not int or s < 1 for s in seqs) or seqs != sorted(set(seqs)):
        raise ValueError("invalid source sequence ordering")
    session = report["session_id"]
    if not isinstance(session, str) or not session or target["provenance"] != (
        f"{session}:{target['observation_seq']}"
    ):
        raise ValueError("invalid native session provenance")
    positions = [target["bot_position"], target["entity_position"]]
    for position in positions:
        if len(position) != 3 or any(
            type(v) not in (int, float) or not math.isfinite(v) for v in position
        ):
            raise ValueError("invalid native coordinates")
    distance = math.dist(*positions)
    if (
        type(target["distance_m"]) not in (int, float)
        or not 0 < distance <= 16
        or not math.isclose(distance, target["distance_m"], rel_tol=0, abs_tol=1e-6)
        or not math.isclose(distance, 2, rel_tol=0, abs_tol=0.1)
    ):
        raise ValueError("invalid controlled zombie geometry")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    check_receipt(json.loads(args.report.read_text(encoding="utf-8")))
    print("OFFLINE_RECEIPT_CONSISTENT; physical authority requires original run evidence")


if __name__ == "__main__":
    main()
