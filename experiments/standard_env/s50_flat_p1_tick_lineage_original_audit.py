"""R-independent S FLAT → P1 tick-lineage original-byte audit (offline only).

R reads original Paper callback rows and S derived preview from separate
archived artifacts. Does not import any S code, nor accept absence of movement
callbacks as proof of a full-tick WAIT. Never admits Body fatigue transitions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ARMS = ("SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")
ORIGINAL_RUN = 38994504183
ORIGINAL_HEAD = "9cb7a009b392ea8127528c310171d804251c90ec"
ORIGINAL_DIGEST = "6bd9d446eefb0a27a7599cdc4d1b79837bff3ef14d6c12ef6361435a9ea69ca6"
P1_OWNER_HEAD = "0ab76b4e46efd914877e543a65de58b6cfc71326"
EXPECTED_DERIVED_CLASS = "S_FLAT_P1_CROSS_BRANCH_REAL_ORIGINAL_TICK_PREVIEW_DEV_ONLY"


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def load_original(path: Path, limit: int = 30_000_000) -> bytes:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= limit, "bad/oversized original file")
    return path.read_bytes()


def parse_json(path: Path) -> dict:
    value = json.loads(load_original(path))
    require(isinstance(value, dict), "original JSON is not a record")
    return value


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def native_rows(content: str) -> list[dict]:
    result = []
    for line in content.splitlines():
        if "M02_DEV_MOTION " not in line:
            continue
        part = line.split("M02_DEV_MOTION ", 1)[1]
        kv = [t.split("=", 1) for t in part.split()]
        require(all(len(pair) == 2 for pair in kv)
                and len(set(x[0] for x in kv)) == len(kv),
                "native original duplicate/malformed field")
        result.append(dict(kv))
    return result


def finite(row: dict, field: str) -> float:
    require(field in row, "missing original native number")
    try:
        number = float(row[field])
    except (ValueError, TypeError) as exc:
        raise ValueError("native original invalid number") from exc
    require(math.isfinite(number), "nonfinite original native number")
    return number


def check_arm(root: Path, original: dict) -> dict:
    """Re-decode original source separately from S/P1 screens."""
    require(isinstance(original, dict) and set(original) ==
            {"source", "tick_lineage", "P1_preview"},
            "missing R-bound derived per-arm records")
    report_raw = load_original(root / "report.json", limit=2_000_000)
    console_raw = load_original(root / "paper_server.log")
    manifest = parse_json(root / "sha256.json")
    source = original["source"]
    ledger = original["tick_lineage"]
    preview = original["P1_preview"]
    arm = source.get("arm")
    require(arm in ARMS and isinstance(ledger, dict) and isinstance(preview, dict),
            "unknown arm or malformed readback")
    require(manifest.get("report.json") == digest(report_raw)
            == source.get("original_report_sha256")
            and manifest.get("paper_server.log") == digest(console_raw)
            == source.get("original_console_sha256"), "source manifest or readback digest drift")
    report = json.loads(report_raw)
    native = native_rows(console_raw.decode("utf-8"))
    begin = report["initial_server_marker"]
    terminal = report["terminal_server_marker"]
    world = begin["world"]
    require(report.get("arm") == arm and report.get("status") == "PASS"
            and report.get("mode") == "FLAT_DEV_ONLY"
            and report.get("cleanup_complete") is True
            and begin["seed"] == terminal["seed"] == "63101"
            and terminal["world"] == world
            and ledger["world"] == preview["world"] == source["world"] == world
            and ledger["arm"] == preview["arm"] == arm,
            "foreign FLAT source, World, or terminal S Action")
    first_tick, last_tick = int(begin["full_time"]), int(terminal["full_time"])
    require(1 <= last_tick-first_tick <= 2400
            and source["start_full_time"] == ledger["start_full_time"] == first_tick
            and source["terminal_full_time"] == ledger["terminal_full_time"] == last_tick,
            "World full_time discrepancy")
    require(len(native) == source["native_motion_events"] <= 300,
            "source native MOVE log count drift")
    cursor_tick = first_tick
    aggregate = 0.0
    charged = 0.0
    groups: dict[int, tuple[int, float]] = {}
    for sequence, line in enumerate(native, 1):
        stamp = int(finite(line, "world_full_time"))
        require(finite(line, "id") == sequence
                and stamp >= cursor_tick and stamp <= last_tick
                and line.get("world") == world
                and line.get("reason") == "WALK"
                and line.get("marker_id"),
                "native event id, time, World or reason mismatch")
        delta = math.hypot(finite(line, "to_x")-finite(line, "from_x"),
                           finite(line, "to_z")-finite(line, "from_z"))
        blocks = finite(line, "blocks")
        bill = finite(line, "billed")
        factor = 0 if arm in ("WALK_ZERO", "BOTH_ZERO") else 1
        require(0 < blocks <= 1.0
                and math.isclose(delta, blocks, abs_tol=1e-9, rel_tol=1e-8)
                and math.isclose(bill, blocks*0.01*factor, abs_tol=1e-9, rel_tol=1e-8),
                "real event delta/M0.2 WALK mismatch")
        aggregate += blocks
        charged += bill
        require(math.isclose(aggregate, finite(line, "cumulative_blocks"),
                             abs_tol=1e-9, rel_tol=1e-8)
                and math.isclose(charged, finite(line, "cumulative_billed"),
                                 abs_tol=1e-9, rel_tol=1e-8),
                "event cumulative sequence corrupted")
        n,b = groups.get(stamp, (0,0.0))
        groups[stamp] = n+1,b+blocks
        cursor_tick=stamp
    require(first_tick not in groups
            and math.isclose(aggregate, float(terminal["motion_blocks"]),
                             abs_tol=1e-9, rel_tol=1e-8)
            and math.isclose(aggregate, source["native_observed_horizontal_blocks"],
                             abs_tol=1e-9, rel_tol=1e-8), "missing/bad motion terminal")
    require(ledger["classification"] ==
            "S_FLAT_P1_WORLD_TICK_LINEAGE_CANDIDATE_DEV_ONLY"
            and source["classification"] ==
            "S_FLAT_P1_MOTION_SOURCE_CANDIDATE_DEV_ONLY"
            and preview["classification"] ==
            "S_P1_FLAT_CROSS_BRANCH_MOTION_ONLY_PREVIEW_NOT_ADMITTED",
            "an allegedly admitted P1 or unrelated readback")
    timeline = ledger["ticks"]
    require(isinstance(timeline, list) and len(timeline) == last_tick-first_tick,
            "dropped/extra Paper World tick")
    unknown = 0
    witnessed = 0
    intervals: list[list[tuple[int,float]]] = []
    current = []
    for i,row in enumerate(timeline,1):
        tick = first_tick + i
        require(row["world_full_time"] == tick
                and row.get("P1_frame_issued") is False, "forged P1 Body frame")
        if tick in groups:
            count, blocks = groups[tick]
            require(row.get("activity") == "MOVE_EVENT_OBSERVED_NOT_FULL_TICK_ADMITTED"
                    and row.get("event_count") == count
                    and math.isclose(row.get("native_horizontal_blocks"),
                                     blocks, abs_tol=1e-9, rel_tol=1e-8)
                    and math.isclose(row.get("P1_hypothetical_gain_not_admitted"),
                                     0.04*blocks, abs_tol=1e-9, rel_tol=1e-8),
                    "native MOVE row not replicated in derived lineage")
            witnessed += 1
            current.append((tick,blocks))
        else:
            require(row.get("activity") == "UNKNOWN_NOT_WAIT"
                    and row.get("event_count") == 0
                    and row.get("native_horizontal_blocks") is None
                    and row.get("P1_hypothetical_gain_not_admitted") is None,
                    "missing source smuggled as free WAIT")
            unknown += 1
            if current:
                intervals.append(current)
                current = []
    if current:
        intervals.append(current)
    require(witnessed == ledger["move_observed_ticks"]
            and unknown == ledger["unclassified_ticks"]
            and witnessed == preview["native_move_tick_candidates"]
            and unknown == preview["unknown_tick_count"]
            and len(preview["windows"]) == len(intervals),
            "tick count or contiguous interval disagreement")
    profile_sha = preview.get("P1_owner_profile_sha256")
    require(isinstance(profile_sha,str) and re.fullmatch(r"[0-9a-f]{64}",profile_sha),
            "missing prospective P1 profile")
    for series, candidate in zip(intervals, preview["windows"], strict=True):
        require(candidate["first_world_tick"] == series[0][0]
                and candidate["last_world_tick"] == series[-1][0]
                and len(candidate["transitions"]) == len(series)
                and candidate["candidate_ticks_replayed"] == len(series)
                and candidate["conflict"] is None
                and candidate["lineage_reset_at_unknown_gap"] is True
                and candidate["authoritative_body_state_updated"] is False,
                "P1 candidate continuity or capability conflict")
        fatigue = 0.0
        for (tick,blocks), transition in zip(series, candidate["transitions"], strict=True):
            before = fatigue
            fatigue += 0.04 * blocks
            require(transition["world_tick"] == tick
                    and math.isclose(transition["real_movement_candidate_blocks"],
                                     blocks, abs_tol=1e-9, rel_tol=1e-8)
                    and math.isclose(transition["hypothetical_fatigue_before"],
                                     before, abs_tol=1e-9, rel_tol=1e-8)
                    and math.isclose(transition["hypothetical_fatigue_after"],
                                     fatigue, abs_tol=1e-9, rel_tol=1e-8)
                    and transition["hypothetical_recovered"] == 0.0,
                    "P1 window state failed independent R arithmetic")
        require(math.isclose(fatigue, candidate["hypothetical_window_end_fatigue"],
                             abs_tol=1e-9, rel_tol=1e-8),
                "P1 end state corrupted")
    require(ledger["SourceBoundTick_MOVE_issued"] == 0
            and ledger["SourceBoundTick_WAIT_issued"] == 0
            and ledger["P1_wait_recovery"] == 0.0
            and ledger["P1_state_advanced"] is False
            and preview["P1_World_SourceBoundTick_issued"] == 0
            and preview["P1_authoritative_state_advanced"] is False
            and preview["P1_wait_recovery"] == 0.0
            and preview["cap_conflicts"] == 0
            and preview["M02_energy_ledger_writes"] == 0,
            "scientific/physical source admission smuggled in DEV receipt")
    return {"arm":arm,"original_motion_rows":len(native),
            "move_observed_ticks":witnessed,"unknown_ticks":unknown,
            "contiguous_motion_windows":len(intervals),
            "native_motion_blocks":aggregate,
            "P1_preview_gain_unadmitted":0.04*aggregate,
            "real_source_bound_wait_ticks":0,"original_hash_pass":True}


def audit(original_root: Path, preview_path: Path) -> dict:
    require(original_root.is_dir() and not original_root.is_symlink()
            and preview_path.is_file() and not preview_path.is_symlink()
            and not any(p.is_symlink() for p in original_root.rglob("*")),
            "unexpected source symlinks/locations")
    receipt = parse_json(preview_path)
    require(receipt.get("classification") == EXPECTED_DERIVED_CLASS
            and receipt.get("S_physical_original_run") == ORIGINAL_RUN
            and receipt.get("S_physical_original_head") == ORIGINAL_HEAD
            and receipt.get("S_artifact_zip_sha256") == ORIGINAL_DIGEST
            and receipt.get("P1_owner_commit") == P1_OWNER_HEAD
            and receipt.get("P1_actual_body_state_advanced") is False
            and receipt.get("P1_WAIT_recovery") == 0.0
            and receipt.get("source_activity_full_tick_qualified") is False
            and receipt.get("science_trials") == 0
            and receipt.get("R_independent_review") == "PENDING",
            "foreign preview/frozen original or fake R authority")
    arms = receipt.get("arms")
    require(isinstance(arms,dict) and set(arms)==set(ARMS),
            "missing or added native arm preview")
    result = [check_arm(original_root/arm, arms[arm]) for arm in ARMS]
    return {"classification":"R_FLAT_P1_TICK_LINEAGE_ORIGINAL_REVIEW_DEV_ONLY",
            "audit_status":"PASS","original_run":ORIGINAL_RUN,
            "P1_owner_head":P1_OWNER_HEAD,"arms":result,
            "real_World_tick_P1_Wait_attested":False,
            "P1_actual_fatigue_state_updated":False,
            "P1_recovered":0.0,
            "R_Java_Node_starts":0,"science_trials":0,
            "engineering_qualified":False,"production_go":False}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original",required=True,type=Path)
    parser.add_argument("--derived",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    result=audit(args.original,args.derived)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("R_FLAT_P1_TICK_LINEAGE_ORIGINAL_READBACK",json.dumps({
        k:v for k,v in result.items() if k!="arms"},sort_keys=True))
    print("R_FLAT_P1_ARMS",json.dumps(result["arms"],sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
