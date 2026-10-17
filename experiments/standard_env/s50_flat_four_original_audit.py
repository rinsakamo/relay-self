"""Independent R offline reader of the four S FLAT DEV original archives.

No S imports or Java/Node execution. A successful audit can preserve behavioral
FAIL; sparse native observations do not attest a continuous physical path.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from experiments.standard_env.s50_flat_base_original_audit import (
    PLUGIN_SHA,
    SOURCE_LEVEL_SHA,
    digest,
    independent_index,
    parse_json,
    read_bytes,
    require,
    validate_manifest,
)
from experiments.standard_env.v7_m02_world_nbt_audit import review_level_dat

ARMS = ("SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")
PROFILES = dict(zip(ARMS, ((1, 1), (0, 1), (1, 0), (0, 0)), strict=True))
PAPER_SHA = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
BASE_CONFIG_SHA = "e9361faa7eac2e3c63bf2f6760765f7f8ae5a4b3631c6819f7ad8ac5c04a540e"


def archive_hashes(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): digest(read_bytes(p, 100 * 1024 * 1024))
            for p in sorted(root.rglob("*")) if p.is_file()}


def safe_root(root: Path) -> None:
    require(root.is_absolute() and ".." not in root.parts and root.is_dir()
            and not root.is_symlink() and not any(p.is_symlink() for p in root.parents),
            "absolute non-aliased original archive root required")
    require(not any(p.is_symlink() for p in root.rglob("*")), "archive symlink forbidden")


def frames(path: Path) -> list[dict]:
    data = [json.loads(x) for x in read_bytes(path).splitlines() if x.strip()]
    require(bool(data), "native original empty")
    session = data[0]["session_id"]
    require(all(x.get("session_id") == session for x in data), "foreign native session")
    require([x.get("seq") for x in data] == list(range(len(data))),
            "native sequence discontinuity")
    return data


def beef(snapshot: dict) -> int:
    return sum(x["count"] for x in snapshot["inventory"] if x["name"] == "cooked_beef")


def rows(log: str, prefix: str) -> list[dict]:
    return [dict(x.split("=", 1) for x in line.split(prefix, 1)[1].split())
            for line in log.splitlines() if prefix in line]


def validate_config(raw: bytes, arm: str) -> str:
    text = raw.decode()
    baseline = text
    for kind, mult in zip(("BASAL", "WALK"), PROFILES[arm], strict=True):
        pattern = rf"(?m)^  {kind}: \{{[^\n]+\}}$"
        matches = re.findall(pattern, text)
        require(len(matches) == 1 and f"multiplier: {mult:.1f}" in matches[0],
                "wrong native config multiplier")
        baseline = baseline.replace(matches[0], matches[0].replace(
            f"multiplier: {mult:.1f}", "multiplier: 1.0"))
    require(digest(baseline.encode()) == BASE_CONFIG_SHA, "foreign M0.2 config bytes")
    return digest(raw)


def audit_arm(root: Path, arm: str, source_index: list[dict]) -> dict:
    report = parse_json(root / "report.json")
    require(report["arm"] == arm and report["mode"] == "FLAT_DEV_ONLY"
            and report["science_trials"] == 0 and not report["engineering_qualified"],
            "wrong arm/mode/science ceiling")
    require(report["status"] in ("PASS", "FAIL"), "nonterminal DEV arm")
    count, missing, changed = validate_manifest(root, parse_json(root / "sha256.json"))
    require(not missing and not changed, "missing or altered archived original files")
    require(parse_json(root / "initial_world_index.json") == source_index,
            "initial World bytes differ from fixed original")
    saved = independent_index(root / "server/world")
    require(parse_json(root / "saved_world_index.json") == saved,
            "saved World index does not match actual original bytes")
    plugin = root / "server/plugins/relay-metabolism-paper-dev.jar"
    require(digest(read_bytes(plugin)) == PLUGIN_SHA, "installed DEV plugin differs")
    paper = root / "server/paper-1.21.8.jar"
    paper_present = paper.is_file()
    require(paper_present, "actual installed Paper JAR missing from originals")
    if paper_present:
        require(digest(read_bytes(paper, 100 * 1024 * 1024)) == PAPER_SHA,
                "installed actual Paper JAR differs")
    config = validate_config(read_bytes(root / "server/plugins/RelayMetabolismDev/config.yml"), arm)
    require(config == report["config_sha256"], "reported config SHA mismatch")
    log = read_bytes(root / "paper_server.log").decode()
    native = frames(root / "original_native.jsonl")
    require(native[0]["type"] == "adapter_started"
            and native[0]["config"] == {"host": "127.0.0.1", "port": 25565,
                                        "username": "RelaySelf", "version": "1.21.8"},
            "wrong native adapter connection")
    require(report["session_id"] == native[0]["session_id"], "report/native session mismatch")
    obs = [f for f in native if f["type"] == "observation"]
    require(bool(obs), "native observation absent")
    kinds = [f["type"] for f in native]
    cleanup_native = (kinds.count("shutdown_ack") == kinds.count("connection_end") == 1
                      and "Done (" in log and "All dimensions are saved" in log)
    claimed_cleanup = all(report.get(k) is True for k in (
        "cleanup_complete", "java_pid_absent", "node_pid_absent", "port_released",
        "port_rebind_witness", "original_unchanged"))
    if report["cleanup_complete"]:
        require(cleanup_native and claimed_cleanup
                and report["java_exit"] == report["node_exit"] == 0,
                "cleanup claim lacks archived native/host witness")
    markers = rows(log, "S_V8_DEV_SNAPSHOT ")
    initial = [x for x in markers if x.get("marker_id") == "INITIAL_" + arm]
    require(len(initial) == 1 and initial[0] == report["initial_server_marker"],
            "initial marker not identical to original Paper log")
    start = initial[0]
    require(start["seed"] == "63101" and [float(start[k]) for k in ("x", "y", "z")]
            == [0.5, -60.0, 0.5], "wrong original native seed/spawn")
    by_seq = {f["seq"]: f for f in native}
    trace = report.get("foraging") or {}
    moves = trace.get("movement_outcomes", [])
    issued = [json.loads(x) for x in read_bytes(root / "issued_actions.jsonl").splitlines()
              if x.strip()] if (root / "issued_actions.jsonl").exists() else []
    ids = {x["action_id"] for x in issued}
    distances = []
    for move in moves:
        require(move["action_id"] in ids and move["terminal"] == "outcome",
                "MOVE missing formal issued Action/OUTCOME")
        before, after = (by_seq[move[k]] for k in ("before_seq", "after_seq"))
        require(before["type"] == after["type"] == "observation", "MOVE non-observation")
        for key, effect, suffix in (("look_seq", "look", "-look"),
                                    ("forward_seq", "set_control", ""),
                                    ("clear_seq", "clear_controls", "-clear")):
            f = by_seq[move[key]]
            require(f["type"] == "effect_result" and f["effect"] == effect
                    and f["action_id"] == move["action_id"] + suffix
                    and f["result"] == "applied", "MOVE original ACK linkage mismatch")
        a, b = before["snapshot"]["position"], after["snapshot"]["position"]
        distance = math.dist([a[k] for k in ("x", "y", "z")],
                             [b[k] for k in ("x", "y", "z")])
        require(move["progress_blocks"] >= 0 or move["kind"] == "BLOCKED",
                "invalid formal MOVE progress")
        distances.append(distance)
    fixture_native = {}
    for key in ("food_initial_native", "food_after_fall_native"):
        value = trace.get(key)
        if value is not None:
            frame = by_seq[value["seq"]]
            require(frame["type"] == "observation"
                    and frame["snapshot"]["position"] == value["snapshot"]["position"],
                    "food fixture foot pose differs from raw native observation")
            fixture_native[key] = frame
    decisions = trace.get("l0_decisions", [])
    for decision in decisions:
        snapshot = by_seq[decision["seq"]]["snapshot"]
        require(decision["food"] == snapshot["food"], "L0 food differs from raw observation")
        if decision["kind"] == "SEEK":
            require(snapshot["food"] < 14 and not snapshot["nearby_entities_coverage"]["truncated"]
                    and sum(e["name"] == "item" for e in snapshot["nearby_entities"]) == 1,
                    "L0 SEEK lacks hungry single native item source")
    item = trace.get("item_entity_id")
    pickup_pairs = []
    if item is not None:
        for a in obs:
            if not any(e["id"] == item for e in a["snapshot"]["nearby_entities"]):
                continue
            for b in obs:
                if (b["seq"] > a["seq"] and beef(b["snapshot"]) - beef(a["snapshot"]) == 1
                        and not b["snapshot"]["nearby_entities_coverage"]["truncated"]
                        and not any(e["id"] == item
                                    for e in b["snapshot"]["nearby_entities"])):
                    pickup_pairs.append([a["seq"], b["seq"]])
                    break
            if pickup_pairs:
                break
    consume = [f for f in native if f["type"] == "effect_result"
               and f.get("effect") == "consume_held" and f.get("result") == "applied"]
    eat_native = False
    for f in consume:
        before = [o for o in obs if o["seq"] < f["seq"] and beef(o["snapshot"]) >= 1]
        after = [o for o in obs if o["seq"] > f["seq"] and beef(o["snapshot"]) == 0]
        if before and after and f["action_id"].removesuffix("-consume") in ids:
            eat_native = any(o["snapshot"]["food"] > min(p["snapshot"]["food"] for p in before)
                             for o in after)
    if report["status"] == "PASS":
        require(bool(moves) and bool(pickup_pairs) and eat_native,
                "behavioral PASS lacks original native MOVE/pickup/EAT contrast")
    basal, motion = rows(log, "M02_DEV_BASAL_WRITE "), rows(log, "M02_DEV_MOTION ")
    for b in basal:
        require(math.isclose(float(b["requested"]), 0.001 * PROFILES[arm][0], abs_tol=1e-9),
                "native BASAL requested amount contradicts arm")
    for m in motion:
        require(m["reason"] == "WALK" and math.isclose(
            float(m["billed"]), float(m["blocks"]) * 0.01 * PROFILES[arm][1],
            abs_tol=1e-8), "native WALK billed amount contradicts arm")
    source = {"basal_logged_rows": len(basal),
              "basal_logged_requested": sum(float(x["requested"]) for x in basal),
              "motion_logged_rows": len(motion),
              "motion_blocks": sum(float(x["blocks"]) for x in motion),
              "motion_billed": sum(float(x["billed"]) for x in motion)}
    for key, value in source.items():
        require(math.isclose(value, report["metabolism_source"][key], abs_tol=1e-8),
                "reported metabolism totals differ from original Paper rows")
    terminal = [x for x in markers if x.get("marker_id") == "TERMINAL_" + arm]
    return {"arm": arm, "behavioral_status": report["status"], "S_error": report.get("error"),
            "native_session_id": native[0]["session_id"], "original_files_checked": count,
            "saved_world_files_checked": len(saved), "config_sha256": config,
            "actual_paper_jar_archived": paper_present, "initial_native_marker": start,
            "terminal_native_marker": terminal[0] if len(terminal) == 1 else None,
            "native_frames": len(native), "move_outcomes": len(moves),
            "food_fixture_original_native": fixture_native, "L0_decisions": decisions,
            "move_endpoint_displacements": distances, "continuous_path_attested": False,
            "pickup_native_source_seq_pairs": pickup_pairs, "strict_playerCollect": "UNKNOWN",
            "S51_eat_native_contrast": eat_native, "metabolism_original_log_totals": source,
            "basal_log_cap_reached": len(basal) >= 500,
            "motion_log_cap_reached": len(motion) >= 300,
            "native_stop_and_save": cleanup_native, "host_cleanup_archived_witness": claimed_cleanup,
            "R_independent_live_host_cleanup_witness": False}


def audit(source: Path, run: Path) -> dict:
    safe_root(source)
    safe_root(run)
    before_source, before_run = archive_hashes(source), archive_hashes(run)
    original = source / "flat-source/server/world"
    before = independent_index(original)
    nbt = review_level_dat(read_bytes(original / "level.dat"), expected_seed=63101)
    require(nbt["original_level_dat_sha256"] == SOURCE_LEVEL_SHA,
            "wrong frozen FLAT level.dat")
    receipt = parse_json(source / "flat-source/flat_dev_receipt.json")
    source_log = read_bytes(source / "flat-source/paper_console.log").decode()
    ground = set(re.findall(r"\[Server\] (S50_FLAT_DEV_GROUND_X-?\d+_Z-?\d+)", source_log))
    require(len(ground) == 25, "original native grass/air witness markers absent")
    require(receipt["stopped_world_index"] == before
            and receipt["native_surface_witnesses"] == 25, "wrong source index/witness count")
    results = run / "flat-four-results"
    summary = parse_json(results / "summary.json")
    whole = parse_json(results / "saved_files_sha256.json")
    require(type(whole) is dict and bool(whole), "whole saved file manifest absent")
    for name, expected in whole.items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts
                and digest(read_bytes(results / name, 100 * 1024 * 1024)) == expected,
                "whole saved file manifest mismatch")
    actual_saved = {p.relative_to(results).as_posix() for p in results.rglob("*") if p.is_file()}
    require(actual_saved == set(whole) | {"saved_files_sha256.json"},
            "whole saved manifest does not cover exact archive files")
    require(summary["arm_order"] == list(ARMS) and summary["science_trials"] == 0
            and not summary["engineering_qualified"] and not summary["science_go"],
            "wrong arm roster or DEV ceiling")
    reviews = []
    for arm in ARMS:
        if arm in summary["not_run"]:
            require(not (results / arm).exists(), "NOT_RUN hides existing physical arm")
            reviews.append({"arm": arm, "behavioral_status": "NOT_RUN"})
            continue
        reviews.append(audit_arm(results / arm, arm, before))
    sessions = [x["native_session_id"] for x in reviews if "native_session_id" in x]
    require(len(sessions) == len(set(sessions)), "cross-arm native session reuse")
    require(independent_index(original) == before, "R review changed source originals")
    require(archive_hashes(source) == before_source and archive_hashes(run) == before_run,
            "original archive bytes changed during independent review")
    return {"classification": "R_FLAT_FOUR_ORIGINAL_READBACK_DEV_ONLY",
            "entire_source_archive_files_checked": len(before_source),
            "entire_run_archive_files_checked": len(before_run),
            "entire_run_archive_sha256": before_run,
            "arms": reviews, "source_world_files_checked": len(before),
            "source_world_level_sha256": SOURCE_LEVEL_SHA,
            "R_java_node_starts": 0, "science_trials": 0,
            "engineering_qualified": False, "science_go": False, "production_go": False,
            "limits": ["host PID/port cleanup is archived producer witness, not live R observation",
                       "formal Action OUTCOME journal cross-checked with native ACK/endpoints",
                       "native sparse endpoint distance is not continuous physical path",
                       "operator hunger and food fixtures; no natural discovery/adaptation credit"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.source, args.run)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
