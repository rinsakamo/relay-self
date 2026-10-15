"""Independent R read-only M0.2 Paper one-shot QUALIFICATION evidence gate.

Consumes neither permits nor physical resources; never launches Java/Node.
The older physical DEV reviewer is reused only for native SOURCE SHAPE, after
new qualification identity, start/STOP, host witness and byte ownership gates.
No scientific, ecological, autonomous food-acquisition or production verdict.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from experiments.standard_env import m02_paper_dev_audit as source
from experiments.standard_env import m02_paper_preworld as profile

QUAL_GRANT = "USER_M02_PAPER_QUALIFICATION_20261015_SECOND_ONCE"
SEED = "2026101502"
NATIVE_NAMES = ("paper_server.log", "original_native.jsonl",
                "owner_commands.jsonl", "qualification_producer.json",
                "initial_world_level.dat")
CLASSIFIED = "S_M02_PAPER_QUALIFICATION_SOURCE_CLOSED_R_REVIEW_REQUIRED"
PASS = "M02_RSEE_PAPER_CANDIDATE_ENGINEERING_QUALIFIED"


class NotQualified(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise NotQualified(message)


def parsed(path: Path) -> dict[str, Any]:
    try:
        value = source.decode(source.read_original(path))
    except (OSError, ValueError) as exc:
        raise NotQualified("bad source JSON: " + str(exc)) from exc
    require(type(value) is dict, "not an object")
    return value


def _check_host_witness(witness: dict[str, Any], report: dict[str, Any],
                        expected_run: str) -> None:
    require(type(witness) is dict
            and set(witness) == {"github_run_id", "github_run_attempt",
                                 "java_pid", "node_pid", "java_absent",
                                 "node_absent", "loopback_port_released"}
            and witness.get("github_run_id") == expected_run
            and witness.get("github_run_attempt") == 1
            and witness.get("java_pid") == report.get("java_pid")
            and witness.get("node_pid") == report.get("node_pid")
            and type(witness.get("java_pid")) is int
            and type(witness.get("node_pid")) is int
            and witness["java_pid"] > 0 and witness["node_pid"] > 0
            and witness["java_pid"] != witness["node_pid"]
            and witness.get("java_absent") is True
            and witness.get("node_absent") is True
            and witness.get("loopback_port_released") is True,
            "current runner's independent process/port witness unavailable")


def review(root: Path, *, expected_workflow_run: str,
           witness_path: Path, admitted_assets: Path) -> dict[str, Any]:
    require(type(expected_workflow_run) is str
            and bool(re.fullmatch(r"[0-9]{6,16}", expected_workflow_run)),
            "expected real workflow identity absent")
    require(root.is_dir() and not root.is_symlink()
            and all(not parent.is_symlink() for parent in root.parents),
            "not an absolute direct owned originals root")
    require(admitted_assets != root and witness_path.is_file(),
            "independent host receipt missing")
    asset = profile.inspect(admitted_assets)
    require(asset["classification"] == "M02_PAPER_ASSETS_PINNED_PREWORLD_REVIEW_ONLY"
            and asset["physical_world_launches_by_review"] == 0,
            "input binary/config source did not pass prior offline gate")
    manifest = source.read_original(root / "SHA256SUMS")
    lines = manifest.decode("ascii").splitlines()
    indexes = {}
    for line in lines:
        m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        require(m is not None, "invalid original evidence hash index")
        digest, name = m.groups()
        require(name not in indexes, "duplicate source hash entry")
        indexes[name] = digest
    require(set(indexes) == set(NATIVE_NAMES), "incomplete/extra source index")
    originals = {name: source.read_original(root / name) for name in NATIVE_NAMES}
    require(all(hashlib.sha256(originals[k]).hexdigest() == v
                for k, v in indexes.items()), "source original changed")
    raw_qual = source.decode(originals["qualification_producer.json"])
    require(type(raw_qual) is dict, "qualification source record absent")
    q = raw_qual
    require(
        q.get("owner") == "S" and q.get("mode") == "QUALIFICATION"
        and q.get("grant_id") == QUAL_GRANT
        and q.get("authorization_consumed") is True
        and q.get("classification") == CLASSIFIED
        and q.get("source_mode") == "PAPER_CANDIDATE"
        and q.get("qual_engineering") is False
        and q.get("science_success") is False
        and q.get("production_go") is False
        and q.get("v_trials") == 0
        and q.get("virtual_m0_ledger_used") is False
        and q.get("retry_count") == 0
        and q.get("java_launch_count") == 1
        and q.get("node_session_count") == 1
        and q.get("new_world") == "NEW_ISOLATED_PAPER"
        and q.get("seed") == SEED
        and q.get("paper_version") == "1.21.8"
        and q.get("owned_world_cleaned") is True
        and q.get("port_released") is True
        and q.get("owned_java_pid_absent") is True
        and q.get("owned_node_pid_absent") is True
        and q.get("java_exit") == 0 and q.get("node_exit") == 0
        and type(q.get("run_id")) is str
        and bool(re.fullmatch(r"[0-9a-f]{32}", q["run_id"]))
        and type(q.get("source_session_id")) is str,
        "S source cannot be admitted as new independent engineering QUALIFICATION")
    require(
        type(q.get("world_seeded_properties_sha256")) is str
        and bool(re.fullmatch(r"[0-9a-f]{64}",
                              q["world_seeded_properties_sha256"]))
        and type(q.get("initial_level_dat_sha256")) is str
        and bool(re.fullmatch(r"[0-9a-f]{64}", q["initial_level_dat_sha256"])),
        "fixed new seed and original initial level.dat evidence absent")
    require(q.get("source_asset_hashes") == profile.load_manifest()[
            "expected_assets_sha256"], "foreign candidate source bytes")
    expected_world_properties = (
        source.read_original(admitted_assets / "server.properties") +
        f"level-seed={SEED}\n".encode("ascii")
    )
    require(q.get("world_seeded_properties_sha256") ==
            hashlib.sha256(expected_world_properties).hexdigest(),
            "new World seed/properties hash not reproducible")
    snapshot = q.get("initial_world_receipt")
    blob = originals["initial_world_level.dat"]
    require(type(snapshot) is dict and
            snapshot.get("snapshot_phase") ==
            "AFTER_SERVER_READY_SAVE_FLUSH_BEFORE_ACTION" and
            snapshot.get("source_world_path") == "s31a-ephemeral/level.dat" and
            snapshot.get("size_bytes") == len(blob) and
            snapshot.get("sha256") == indexes["initial_world_level.dat"] and
            q.get("initial_level_dat_sha256") == indexes["initial_world_level.dat"],
            "initial World source bytes not matched to pre-Action checkpoint")
    try:
        decompressed = gzip.decompress(blob)
    except (OSError, EOFError) as exc:
        raise NotQualified("invalid initial World level.dat gzip bytes") from exc
    require(len(decompressed) <= 16 * 1024 * 1024 and
            len(decompressed) >= 4 and decompressed[0] == 10,
            "initial World NBT compound source invalid")
    # Never treat the S "producer SOURCE_CLOSED" as an independent verdict.
    witness = parsed(witness_path)
    _check_host_witness(witness, q, expected_workflow_run)
    require(not list((root / "owned-worlds").iterdir()),
            "owned Paper World not deleted")
    # Source-shape normalization only. NOT an actual DEV invocation or a
    # mutation/reclassification of the producer's QUALIFICATION receipt.
    adapted = {
        "milestone": "M0.2_PAPER_DEV",
        "classification": "M02_PAPER_DEV_ONLY_PHYSICS_OBSERVED",
        "status": "PASS", "owner_status": "PASS",
        "physical_world": "STARTED_NEW_DEV_PAPER",
        "minecraft_version": q["paper_version"],
        "steak": "cooked_beef", "m0_virtual_ledger_used": False,
        "qualified": False, "science_go": False, "production_go": False,
        "node_exit": q["node_exit"], "java_exit": q["java_exit"],
        "port_released_after_shutdown": q["port_released"],
        "source_session_id": q["source_session_id"],
        "movement": q.get("movement"), "eating": q.get("eating"),
    }
    s = source.inspect(originals["paper_server.log"],
                       originals["original_native.jsonl"],
                       originals["owner_commands.jsonl"], adapted)
    require(s["native_stop_ack_seq"] == q.get("native_stop_ack_seq")
            and s["native_connection_end_seq"] ==
            q.get("native_connection_end_seq")
            and s["native_rows"] == q.get("native_rows")
            and s["observed_native_steak_eat"] is True
            and s["paper_walk_events"] > 0
            and s["observed_motion_blocks"] > 0.5
            and abs(s["recomputed_walk_exhaustion"] -
                    s["observed_motion_blocks"] * 0.01) < 1e-7,
            "R independent raw World/Action effects differ from S qualifier")
    # Post-audit immutable-byte readback.
    require(all(hashlib.sha256(source.read_original(root / k)).hexdigest() == v
                for k, v in indexes.items())
            and source.read_original(root / "SHA256SUMS") == manifest,
            "original evidence modified during R review")
    return {
        "classification": PASS,
        "scope": "PAPER_1_21_8_CANDIDATE_M02_BASAL_WALK_S50_MOVE_S51_STEAK_EAT_ONLY",
        "run_id": q["run_id"], "source_session": q["source_session_id"],
        "github_run_id": expected_workflow_run,
        "source_seed": SEED, "evidence_sha256": indexes,
        "java_launches": 1, "node_sessions": 1, "grant_consumed": True,
        "native_rows": s["native_rows"],
        "motion_packets": s["observed_motion_packets"],
        "motion_blocks": s["observed_motion_blocks"],
        "recomputed_walk_exhaustion": s["recomputed_walk_exhaustion"],
        "native_stop_ack_seq": s["native_stop_ack_seq"],
        "native_connection_end_seq": s["native_connection_end_seq"],
        "independent_process_port_exit": True,
        "candidate_physics_qualified": True,
        "strict_pickup_causality": "NOT_TESTED",
        "learning_qualified": False,
        "ecological_calibration": "NOT_RUN",
        "b0_vanilla_golden_mutated": False,
        "v_science_trials": 0, "science_go": False, "production_go": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--witness", type=Path, required=True)
    parser.add_argument("--workflow-run-id", required=True)
    args = parser.parse_args(argv)
    try:
        result = review(args.original_root,
                        expected_workflow_run=args.workflow_run_id,
                        witness_path=args.witness, admitted_assets=args.asset_root)
        code = 0
    except (ValueError, TypeError, OSError, KeyError, AttributeError) as exc:
        result = {
            "classification": "M02_PAPER_R_QUALIFICATION_FAILED_OR_UNDETERMINED",
            "failure": f"{type(exc).__name__}: {exc}",
            "candidate_physics_qualified": False,
            "science_go": False, "production_go": False,
            "requires_fresh_grant_for_new_java": True,
        }
        code = 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
