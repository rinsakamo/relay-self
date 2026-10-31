"""L11: inspect saved G4.13 real-Paper originals, NEVER mint L10 Goal labels.

The caller supplies an existing GitHub Actions artifact ZIP. This read-only
audit checks pinned exact original *file bytes*, joined native S16 summaries
and T2 rows. It cannot independently authenticate Minecraft packets, infer
per-Action goal rewards, or turn a world terminal into L3 ExternalGoalLabel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import stat
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA = "L11_G413_ORIGINAL_GOAL_BOUNDARY_V1"
ARTIFACT_ID = 12952335343
PRODUCER_RUN_ID = 40997098497
PRODUCER_HEAD = "55f5f7c6f2e483ceb6bcb9d692c02b1dcf751e24"
# Hashes of the *unmodified real source file contents* inside the artifact,
# verified from the downloaded artifact, not copied from GitHub summaries.
PINNED = {
    "WORLD-G4/goal_report.json":
        "5cc9d5c2bf262dcf241ba3ce715c2347fd075db96de5fda16352c1b84ab17757",
    "WORLD-G4/l1_t2_ledger_dev.json":
        "017eabbc2fdfc963160eabf72e549b6550c133a00a3958cc3104e04f7f66163e",
    "WORLD-G413/goal_report.json":
        "a2139d5edb7fae955470306ddc8f83535c3995666236562f3727d9d308a4cec6",
    "WORLD-G413/l1_t2_ledger_dev.json":
        "0f21851ab06377532b46514534d49df6db5b39fa7ede65a1c2919553be20f75d",
}
MAX_ARCHIVE_BYTES = 2_000_000
MAX_TOTAL_UNCOMPRESSED_BYTES = 3_500_000
MAX_ENTRIES = 32
MAX_ONE_FILE_BYTES = 650_000


class L11OriginalRejected(ValueError):
    """A saved original is missing, altered, unsafe, or incoherent."""


@dataclass(frozen=True, slots=True)
class L11SavedWorld:
    source: str
    session_id: str
    original_report_sha256: str
    original_t2_sha256: str
    original_s49_outcomes: int
    original_t2_world_ticks: int
    tolerance_m: float
    final_goal_error_m: float
    last_s16_goal_error_m: float
    last_s16_within_tolerance: bool
    final_goal_within_tolerance: bool
    last_s16_seq: int
    final_probe_seq: int
    last_action_not_final_probe: bool
    independent_native_source_authenticated: bool = False
    independent_per_action_goal_attested: bool = False


@dataclass(frozen=True, slots=True)
class L11OriginalBoundaryAudit:
    schema: str
    artifact_id: int
    producer_run_id: int
    producer_head: str
    worlds: tuple[L11SavedWorld, ...]
    original_s49_outcomes: int
    original_t2_world_ticks: int
    source_file_hashes_match: bool = True
    world_goal_observed: bool = True
    action_goal_labels_admitted: int = 0
    l10_qualified_episode_pairs: int = 0
    l10_current_world_body_cues_admitted: bool = False
    s10_learning_updates: int = 0
    s11_habit_grants: int = 0
    action_issues: int = 0
    replayed_worlds: int = 0
    physical_learning_attested: bool = False
    science_go: bool = False
    classification: str = "L11_REAL_ORIGINAL_WORLD_GOAL_ONLY_NO_ACTION_LABELS"


def _exact_json(raw: bytes, name: str) -> dict:
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise L11OriginalRejected(f"{name} not original valid UTF-8 JSON") from exc
    if not isinstance(result, dict):
        raise L11OriginalRejected(f"{name} not a JSON object")
    return result


def _finite(value: object) -> bool:
    return type(value) in (float, int) and math.isfinite(value)


def _world(name: str, report: dict, t2: dict) -> L11SavedWorld:
    session = report.get("session_id")
    actions = report.get("native_actions")
    goal = report.get("goal_l2")
    precision = report.get("goal_l1")
    last = report.get("final_native_xz")
    ledger_ref = report.get("l1_t2_ledger_dev")
    if (
        not isinstance(session, str) or not session
        or report.get("status") != "PASS"
        or report.get("stage") != "GOAL_REACHED"
        or report.get("real_world") is not True
        or report.get("learned_L1_attested") is not False
        or report.get("qualification_go") is not False
        or report.get("science_go") is not False
        or report.get("experience_requested_dev") is not False
        or report.get("goal_S14_dev_admission") is not True
        or report.get("existing_S49_action_supervisor_reused") is not True
        or not isinstance(actions, list) or not actions
        or type(report.get("action_count")) is not int
        or len(actions) != report["action_count"]
        or not isinstance(goal, dict) or goal.get("session_id") != session
        or not isinstance(precision, dict)
        or not isinstance(last, dict) or not isinstance(ledger_ref, dict)
    ):
        raise L11OriginalRejected(f"{name} missing real S49 original Goal boundaries")
    tolerance = precision.get("tolerance_m")
    tx, tz = goal.get("target_x"), goal.get("target_z")
    fx, fz = last.get("x"), last.get("z")
    error = last.get("euclidean_error_m")
    if not all(map(_finite, (tolerance, tx, tz, fx, fz, error))):
        raise L11OriginalRejected("nonfinite original goal geometry")
    if not (0.0 < tolerance <= 1.0 and error >= 0
            and math.isclose(math.hypot(fx-tx, fz-tz), error, abs_tol=1e-9)):
        raise L11OriginalRejected("original final goal geometry drift")
    if error > tolerance:
        raise L11OriginalRejected("reported goal passed without final spatial tolerance")

    ids: set[str] = set()
    last_seq = -1
    for a in actions:
        if not isinstance(a, dict):
            raise L11OriginalRejected("untyped original S49 Action row")
        aid = a.get("action_id")
        before, after = a.get("before_seq"), a.get("after_seq")
        ax, az, ae = a.get("end_x"), a.get("end_z"), a.get("goal_error_at_S16_end_m")
        if (not isinstance(aid, str) or not aid or aid in ids
                or type(before) is not int or type(after) is not int
                or not (0 <= before < after and last_seq < before)
                or a.get("s16_status") != "executed"
                or a.get("s16_terminal") != "outcome"
                or not all(map(_finite, (ax, az, ae)))
                or ae < 0 or not math.isclose(math.hypot(ax-tx, az-tz), ae, abs_tol=1e-9)):
            raise L11OriginalRejected("S16 terminal/Action identity or geometry mismatch")
        ids.add(aid)
        last_seq = after
    last_action_error = actions[-1]["goal_error_at_S16_end_m"]
    final_seq = last.get("seq")
    if type(final_seq) is not int or final_seq <= last_seq:
        raise L11OriginalRejected("separate later final probe required")
    rows = t2.get("rows")
    ticks = ledger_ref.get("rows")
    if (not isinstance(rows, list) or not rows
            or type(ticks) is not int or len(rows) != ticks
            or t2.get("independent_native_source_authenticated") is not False
            or t2.get("exact_gait_attested") is not False
            or ledger_ref.get("session_id") != session
            or ledger_ref.get("rows") != ticks
            or ledger_ref.get("original_action_boundary_receipts") != len(actions)
            or ledger_ref.get("one_native_reader") is not True
            or ledger_ref.get("owner_failed") is not False
            or ledger_ref.get("source_admitted") is not True
            or ledger_ref.get("qualified_wait_attested") is not False):
        raise L11OriginalRejected("T2 source owner/receipt mismatch")
    world_ticks = [x.get("world_tick") if isinstance(x, dict) else None for x in rows]
    if any(type(x) is not int or x <= 0 for x in world_ticks) or any(
        b != a + 1 for a, b in zip(world_ticks, world_ticks[1:], strict=False)
    ) or any(x.get("session_id") != session for x in rows):
        raise L11OriginalRejected("T2 original contiguous WorldTick/source session drift")
    return L11SavedWorld(
        source=name,
        session_id=session,
        original_report_sha256=PINNED[f"{name}/goal_report.json"],
        original_t2_sha256=PINNED[f"{name}/l1_t2_ledger_dev.json"],
        original_s49_outcomes=len(actions), original_t2_world_ticks=ticks,
        tolerance_m=tolerance, final_goal_error_m=error,
        last_s16_goal_error_m=last_action_error,
        last_s16_within_tolerance=last_action_error <= tolerance,
        final_goal_within_tolerance=True,
        last_s16_seq=last_seq, final_probe_seq=final_seq,
        last_action_not_final_probe=True,
    )


def audit_l11_g413_saved_originals(archive: Path) -> L11OriginalBoundaryAudit:
    """Read a saved **real** G413 artifact; never run World or issue Action.

    File SHA pins are to the original report/T2 bytes. The container ZIP itself
    may be repackaged: zip-level metadata is not an Action/World source.
    """
    if (not isinstance(archive, Path) or not archive.is_absolute()
            or archive.is_symlink() or not archive.is_file()
            or not stat.S_ISREG(archive.lstat().st_mode)
            or archive.stat().st_size > MAX_ARCHIVE_BYTES):
        raise L11OriginalRejected("read-only existing regular bounded artifact required")
    try:
        with zipfile.ZipFile(archive) as z:
            items = z.infolist()
            if (len(items) > MAX_ENTRIES or
                    sum(i.file_size for i in items) > MAX_TOTAL_UNCOMPRESSED_BYTES):
                raise L11OriginalRejected("artifact expanded size/count exceeds bound")
            names = set()
            for item in items:
                name = item.filename
                parts = name.split("/")
                if (item.is_dir() or name.startswith("/") or ".." in parts
                        or name in names or item.file_size > MAX_ONE_FILE_BYTES
                        or (item.external_attr >> 16) & 0o170000 == 0o120000):
                    raise L11OriginalRejected("unsafe or duplicate ZIP member")
                names.add(name)
            if not set(PINNED).issubset(names):
                raise L11OriginalRejected("saved G413 report/T2 originals missing")
            verified = {}
            for name, expected in PINNED.items():
                data = z.read(name)
                if hashlib.sha256(data).hexdigest() != expected:
                    raise L11OriginalRejected("historical original SHA drift: " + name)
                verified[name] = _exact_json(data, name)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise L11OriginalRejected("unreadable or corrupted original ZIP") from exc

    for folder in ("WORLD-G4", "WORLD-G413"):
        report = verified[f"{folder}/goal_report.json"]
        receipt = report.get("l1_t2_ledger_dev")
        if (not isinstance(receipt, dict)
                or receipt.get("derived_file") != "l1_t2_ledger_dev.json"
                or receipt.get("derived_file_sha256") !=
                   PINNED[f"{folder}/l1_t2_ledger_dev.json"]):
            raise L11OriginalRejected("original report-derived T2 SHA binding failed")
    worlds = tuple(
        _world(name, verified[f"{name}/goal_report.json"],
               verified[f"{name}/l1_t2_ledger_dev.json"])
        for name in ("WORLD-G4", "WORLD-G413")
    )
    if worlds[0].session_id == worlds[1].session_id:
        raise L11OriginalRejected("two real Worlds cannot share a session identity")
    return L11OriginalBoundaryAudit(
        schema=SCHEMA, artifact_id=ARTIFACT_ID,
        producer_run_id=PRODUCER_RUN_ID, producer_head=PRODUCER_HEAD,
        worlds=worlds,
        original_s49_outcomes=sum(x.original_s49_outcomes for x in worlds),
        original_t2_world_ticks=sum(x.original_t2_world_ticks for x in worlds),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact-zip", type=Path)
    args = ap.parse_args(argv)
    if args.artifact_zip is None:
        print(json.dumps({
            "schema": SCHEMA,
            "classification": "L11_ORIGINAL_BYTES_NOT_SUPPLIED",
            "verified_originals": 0,
            "action_goal_labels_admitted": 0,
            "worlds_started": 0,
        }, sort_keys=True))
        return 0
    try:
        outcome = audit_l11_g413_saved_originals(args.artifact_zip)
    except (L11OriginalRejected, OSError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "classification": "L11_ORIGINAL_AUDIT_BLOCKED",
            "reason": str(exc),
            "action_goal_labels_admitted": 0, "worlds_started": 0,
        }, sort_keys=True))
        return 2
    print(json.dumps(asdict(outcome), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
