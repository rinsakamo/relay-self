"""R independent read-only original review: FLAT BASE_ON food/L0/Action/STOP.

Does not import any S producer code. S claims are independently bounded
against archived raw Mineflayer, Paper, Action and whole-source hashes.
This is DEV evidence review, not new Paper JAR engineering qualification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.standard_env.v7_m02_world_nbt_audit import review_level_dat

SOURCE_LEVEL_SHA = "1cd714e9607a8015ca37918f11717ab92f2e0d44718c439d7d83a9a36dac1845"
PLUGIN_SHA = "d620935f6f03f3239cebbef0b931ba97482f596e5457feec9b680fe2e14da486"
ARMS = {"BASE_ON"}
FILE_CAP = 512
BYTE_CAP = 512 * 1024 * 1024


class FlatBaseAuditRejected(ValueError):
    """Not a complete native source original, or claim beyond review scope."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise FlatBaseAuditRejected(reason)


def read_bytes(path: Path, cap: int = 64 * 1024 * 1024) -> bytes:
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= cap,
            f"missing/symlink/oversized original {path.name}")
    return path.read_bytes()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_json(path: Path) -> Any:
    return json.loads(read_bytes(path, 10 * 1024 * 1024))


def independent_index(root: Path) -> list[dict[str, Any]]:
    require(root.is_dir() and not root.is_symlink(), "missing source World root")
    rows: list[dict] = []
    total = 0
    for item in sorted(root.rglob("*")):
        require(not item.is_symlink(), "symlink in original World")
        if item.is_dir():
            continue
        require(item.is_file(), "foreign filesystem entry in World")
        raw = read_bytes(item)
        total += len(raw)
        require(len(rows) < FILE_CAP and total <= BYTE_CAP, "World too large")
        rows.append({"relative_path": item.relative_to(root).as_posix(),
                     "size": len(raw), "sha256": digest(raw)})
    paths = {r["relative_path"] for r in rows}
    require("level.dat" in paths
            and any(p.startswith("region/") and p.endswith(".mca") for p in paths),
            "no real level.dat/terrain")
    return rows


def validate_manifest(root: Path, manifest: Any) -> tuple[int, list[str], list[str]]:
    require(type(manifest) is dict and 10 <= len(manifest) <= FILE_CAP,
            "invalid archived S manifest")
    missing: list[str] = []
    mismatch: list[str] = []
    for name, expected in sorted(manifest.items()):
        require(type(name) is str and name and not name.startswith("/")
                and all(segment not in ("", ".", "..") for segment in name.split("/"))
                and type(expected) is str and len(expected) == 64
                and all(c in "0123456789abcdef" for c in expected),
                "invalid manifest path/digest")
        file = root / name
        if not file.is_file() or file.is_symlink():
            missing.append(name)
        elif digest(read_bytes(file)) != expected:
            mismatch.append(name)
    return len(manifest), missing, mismatch


def audit(source_archive: Path, run_archive: Path) -> dict[str, Any]:
    src = source_archive / "flat-source/server/world"
    run = run_archive / "flat-base-results/BASE_ON"
    old_idx = independent_index(src)
    require(len(old_idx) == 13, "source flat stopped World file count mismatch")
    old_nbt = review_level_dat(read_bytes(src / "level.dat"), expected_seed=63101)
    require(old_nbt["original_level_dat_sha256"] == SOURCE_LEVEL_SHA,
            "wrong historical flat World level.dat")
    original_receipt = parse_json(source_archive / "flat-source/flat_dev_receipt.json")
    require(original_receipt["stopped_world_index"] == old_idx
            and original_receipt["native_surface_witnesses"] == 25,
            "original ground/source mismatch")
    initial_idx = parse_json(run / "initial_world_index.json")
    require(initial_idx == old_idx, "new DEV arm not cloned from fixed flat World")
    report = parse_json(run / "report.json")
    summary = parse_json(run_archive / "flat-base-results/summary.json")
    require(report["arm"] == "BASE_ON" and report["mode"] == "FLAT_DEV_ONLY"
            and report["status"] == "PASS" and report["cleanup_complete"],
            "source positive native DEV report absent")
    require(summary["classification"] == "S50_FLAT_BASE_ON_L0_FORENSIC_DEV_ONLY"
            and summary["behavioral_status"] == "PASS"
            and summary["arm"] == "BASE_ON"
            and summary["initial_original_bytes_retained"]
            and summary["cleanup_complete"] and summary["retries"] == 0,
            "source summary inconsistent")
    require(report["java_launch_attempts"] == 1
            and report["node_launch_attempts"] == 1
            and report["java_exit"] == report["node_exit"] == 0
            and all(report.get(key) is True for key in (
                "shutdown_ack", "connection_end", "java_stop_saved",
                "port_released", "port_rebind_witness",
                "java_pid_absent", "node_pid_absent", "original_unchanged")),
            "native Java Node STOP and host lifecycle incomplete")
    need_files, missing, mismatched = validate_manifest(run, parse_json(run / "sha256.json"))
    require(not missing and not mismatched,
            "archived per-arm source hashes missing/mismatched")
    require(digest(read_bytes(run / "server/plugins/relay-metabolism-paper-dev.jar"))
            == PLUGIN_SHA, "actual installed new unqualified DEV plugin mismatch")
    native = [json.loads(line) for line in read_bytes(run / "original_native.jsonl").splitlines()
              if line.strip()]
    kinds = [x.get("type") for x in native]
    require(kinds.count("shutdown_ack") == kinds.count("connection_end") == 1
            and kinds.count("adapter_started") == 1
            and kinds.count("observation") >= 8,
            "original Mineflayer native lifecycle missing")
    trace = report.get("foraging", {})
    require(trace.get("status") == "PICKUP_SOURCE_CONSISTENT"
            and trace.get("fixture_food_source") == "OPERATOR_STAGED_COOKED_BEEF_NOT_AUTONOMOUS"
            and trace.get("virtual_energy_ledger_used") is False
            and trace["pickup"]["cooked_beef_inventory_delta"] == 1
            and trace["pickup"]["strict_player_collect_causality"] == "UNKNOWN"
            and trace["pickup"]["source_evidence"] == "ITEM_DISAPPEARED_AND_INVENTORY_ROSE_ONLY",
            "native item disappearance+inventory source contrast missing")
    moves = trace.get("movement_outcomes", [])
    require(len(moves) == 2 and [x["kind"] for x in moves] == ["PROGRESSED", "ARRIVED"]
            and all(x["terminal"] == "outcome" and x["progress_blocks"] > 0 for x in moves),
            "two governed native MOVE terminal outcomes missing")
    require("eating" in report and report["eating"] is not None
            and summary["s51_eat_completed"] is True,
            "no S51 native EAT original completion")
    mark = report["initial_server_marker"]
    require(mark["seed"] == "63101" and mark["x"] == "0.5"
            and mark["y"] == "-60.0" and mark["z"] == "0.5",
            "native FLAT spawn pose/seed not the actual original")
    console = read_bytes(run / "paper_server.log", cap=25 * 1024 * 1024)
    require(b"Done (" in console and b"All dimensions are saved" in console,
            "original native Paper startup/STOP source absent")
    own_actions = read_bytes(run / "issued_actions.jsonl", cap=5 * 1024 * 1024)
    actions = [json.loads(x) for x in own_actions.splitlines() if x.strip()]
    require(len(actions) >= 3 and all(x["action_id"] in own_actions.decode()
                                      for x in moves),
            "original S Action issuance missing")
    require(report["science_trials"] == summary["science_trials"] == 0
            and not report["engineering_qualified"] and not summary["science_go"],
            "DEV science or engineering escalation forbidden")
    return {
        "classification": "R_FLAT_BASE_ON_ORIGINAL_NATIVE_PICKUP_EAT_READBACK_DEV_ONLY",
        "flat_seed_nbt": old_nbt["world_seed_from_nbt"],
        "flat_ground_source_files": len(old_idx),
        "archived_arm_files_sha256_checked": need_files,
        "archived_arm_missing": missing, "archived_arm_changed": mismatched,
        "native_frames": len(native), "native_observations": kinds.count("observation"),
        "governed_move_outcomes": len(moves),
        "native_move_kinds": [x["kind"] for x in moves],
        "cooked_beef_inventory_delta": 1,
        "pickup_source_consistent_only": True,
        "strict_player_collect_causality": "UNKNOWN",
        "S51_EAT_reported": True,
        "native_start_x_y_z": [mark["x"], mark["y"], mark["z"]],
        "source_archive_world_level_sha256": SOURCE_LEVEL_SHA,
        "source_javaprocess_count": 1, "source_nodeprocess_count": 1,
        "separate_R_java_node_starts": 0,
        "source_stopped_world_unchanged": True,
        "source_food_staged_by_operator": True,
        "r_new_plugin_engineering_qualified": False,
        "science_trials": 0, "science_go": False, "production_go": False,
    }
