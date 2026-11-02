"""Z1 original Paper main-thread zombie witness auditor (NOT Mineflayer correlation).

This independently re-reads *captured* Paper stdout, not invented L0
outcomes. Correct format/hash alone does not prove real World provenance:
the actual runner must pin the owned Java PID/JAR and full original raw bytes.
No Action, model call, learned update or physical World launch here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

MAX_BYTES = 16_000_000
PREFIX_ARM = "L_ZOMBIE_ARM_V1 "
PREFIX_TICK = "L_ZOMBIE_TICK_V1 "
PREFIX_END = "L_ZOMBIE_END_V1 "
ALLOWED_PREFIXES = (PREFIX_ARM, PREFIX_TICK, PREFIX_END)
KEY_PATTERN = re.compile(r"^[a-z_]+=[^\s=]+$")
TOKEN = re.compile(r"[A-Za-z0-9._:-]{1,48}")
SHA = re.compile(r"[a-f0-9]{64}")


class PaperZombieSourceRejected(ValueError):
    """Original Paper witness is incomplete, stale, ambiguous or unqualified."""


@dataclass(frozen=True, slots=True)
class PaperZombieTick:
    tick: int
    offset: int
    x_m: float
    y_m: float
    z_m: float
    entity_uuid: str
    entity_id: int
    world_uuid: str


@dataclass(frozen=True, slots=True)
class PaperZombieWindow:
    marker: str
    session: str
    paper_log_sha256: str
    original_line_count: int
    world_uuid: str
    entity_uuid: str
    entity_id: int
    entity_spawn_instance: int
    pre_source_tick: int
    forecast_freeze_tick: int
    target_tick: int
    pre_source_xz_m: tuple[float, float]
    forecast_freeze_xz_m: tuple[float, float]
    target_xz_m: tuple[float, float]
    total_samples: int
    paper_only: bool = True
    mineflayer_client_join_attested: bool = False
    actor_action_issued: bool = False
    l2_model_called: bool = False
    learned_state_admitted: bool = False
    qualified_world_claim: bool = False


def _uuid(text: str) -> str:
    try:
        parsed = uuid.UUID(text)
    except (TypeError, ValueError, AttributeError) as exc:
        raise PaperZombieSourceRejected("bad Paper entity/world UUID") from exc
    if parsed.version not in (1, 2, 3, 4, 5) or str(parsed) != text:
        raise PaperZombieSourceRejected("noncanonical Paper entity/world UUID")
    return text


def _token(text: str) -> str:
    if not TOKEN.fullmatch(text):
        raise PaperZombieSourceRejected("invalid Paper marker/session token")
    return text


def _entry(line: str) -> tuple[str, dict[str, str]] | None:
    # The original logger always writes one marker within a Paper logger line.
    hits = [k for k in ALLOWED_PREFIXES if k in line]
    if not hits:
        return None
    if len(hits) != 1:
        raise PaperZombieSourceRejected("ambiguous Paper witness source marker")
    marker = hits[0]
    pos = line.index(marker)
    after = line[pos + len(marker):]
    parts = after.split(" ")
    if any(not KEY_PATTERN.fullmatch(part) for part in parts):
        raise PaperZombieSourceRejected("non-exact Paper witness key=value source")
    fields = dict(part.split("=", 1) for part in parts)
    if len(fields) != len(parts):
        raise PaperZombieSourceRejected("duplicate Paper source key")
    return marker, fields


def _number(fields: dict[str, str], key: str) -> float:
    try:
        value = float(fields[key])
    except (ValueError, TypeError, KeyError) as exc:
        raise PaperZombieSourceRejected("not a numeric Paper location") from exc
    if not math.isfinite(value) or abs(value) > 30_000_000:
        raise PaperZombieSourceRejected("non-finite/unbounded location")
    return value


def _integer(fields: dict[str, str], key: str, *, min_value: int = 0) -> int:
    value = fields.get(key, "")
    if re.fullmatch(r"(0|[1-9][0-9]*)", value) is None:
        raise PaperZombieSourceRejected("not an exact integer source")
    parsed = int(value)
    if not min_value <= parsed < 2**31:
        raise PaperZombieSourceRejected("integer original bound failed")
    return parsed


def audit_paper_zombie_window(
    original: bytes, *, original_sha256: str,
    expected_marker: str, expected_session: str,
) -> PaperZombieWindow:
    """Read back original log 31 rows; no nearest tick or client timestamp."""
    if (
        type(original) is not bytes
        or not 0 < len(original) <= MAX_BYTES
        or not original.endswith(b"\n")
        or not isinstance(original_sha256, str)
        or not SHA.fullmatch(original_sha256)
        or hashlib.sha256(original).hexdigest() != original_sha256
    ):
        raise PaperZombieSourceRejected("complete-line Paper original/SHA required")
    _token(expected_marker)
    _token(expected_session)
    try:
        lines = original.decode("utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise PaperZombieSourceRejected("not a UTF-8 original Paper logger") from exc
    relevant = []
    for line_no, line in enumerate(lines, start=1):
        item = _entry(line)
        if item is not None and item[1].get("marker") == expected_marker:
            relevant.append((line_no, *item))
    if len(relevant) != 33:
        raise PaperZombieSourceRejected("31 tick rows plus one arm and one end required")
    if relevant[0][1] != PREFIX_ARM or relevant[-1][1] != PREFIX_END:
        raise PaperZombieSourceRejected("Paper source order arm->31ticks->end missing")
    if any(kind != PREFIX_TICK for _, kind, _ in relevant[1:-1]):
        raise PaperZombieSourceRejected("non-sampled or duplicate Paper witness frame")
    arm = relevant[0][2]
    end = relevant[-1][2]
    arm_keys = {
        "marker", "session", "world", "entity_uuid", "entity_id",
        "expected_samples", "pre_offset", "future_offset",
    }
    end_keys = {"marker", "session", "result", "samples", "last_offset"}
    if set(arm) != arm_keys or set(end) != end_keys:
        raise PaperZombieSourceRejected("unknown original arm/close fields")
    if any(obj.get("session") != expected_session for _, _, obj in relevant):
        raise PaperZombieSourceRejected("foreign Paper session")
    if end.get("result") != "PAPER_WINDOW_COMPLETE":
        raise PaperZombieSourceRejected("zombie disappeared or source not completed")
    if (
        _integer(arm, "expected_samples") != 31
        or _integer(arm, "pre_offset") != 10
        or _integer(arm, "future_offset") != 30
        or _integer(end, "samples") != 31
        or _integer(end, "last_offset") != 30
    ):
        raise PaperZombieSourceRejected("wrong authoritative 20-tick observation window")
    world = _uuid(arm["world"])
    entity_uuid = _uuid(arm["entity_uuid"])
    entity_id = _integer(arm, "entity_id")
    rows = []
    row_keys = {
        "marker", "session", "world", "entity_uuid", "entity_id",
        "spawn_instance", "server_tick", "offset", "x", "y", "z",
    }
    for i, (_, _, fields) in enumerate(relevant[1:-1]):
        if set(fields) != row_keys or any(
            fields.get(k) != value for k, value in (
                ("world", world), ("entity_uuid", entity_uuid),
                ("entity_id", str(entity_id)), ("marker", expected_marker),
            )
        ):
            raise PaperZombieSourceRejected("entity/world/source identity changed during observation")
        if _integer(fields, "spawn_instance") != 1:
            raise PaperZombieSourceRejected("new zombie generation is a different trajectory")
        if _integer(fields, "offset") != i:
            raise PaperZombieSourceRejected("missing/duplicated/noncontiguous Paper tick")
        rows.append(PaperZombieTick(
            tick=_integer(fields, "server_tick"), offset=i,
            x_m=_number(fields, "x"), y_m=_number(fields, "y"),
            z_m=_number(fields, "z"), entity_uuid=entity_uuid,
            entity_id=entity_id, world_uuid=world,
        ))
        if i and rows[i].tick != rows[i-1].tick + 1:
            raise PaperZombieSourceRejected("Paper server tick gap/duplicate")
    if rows[30].tick != rows[10].tick + 20:
        raise PaperZombieSourceRejected("no exact future 20-tick original source")
    return PaperZombieWindow(
        marker=expected_marker, session=expected_session,
        paper_log_sha256=original_sha256, original_line_count=len(lines),
        world_uuid=world, entity_uuid=entity_uuid, entity_id=entity_id,
        entity_spawn_instance=1,
        pre_source_tick=rows[0].tick,
        forecast_freeze_tick=rows[10].tick,
        target_tick=rows[30].tick,
        pre_source_xz_m=(rows[0].x_m, rows[0].z_m),
        forecast_freeze_xz_m=(rows[10].x_m, rows[10].z_m),
        target_xz_m=(rows[30].x_m, rows[30].z_m),
        total_samples=31,
    )


def report_paper_only(original: bytes, *, sha256: str, marker: str, session: str) -> dict:
    report = asdict(audit_paper_zombie_window(
        original, original_sha256=sha256,
        expected_marker=marker, expected_session=session,
    ))
    report["classification"] = "PAPER_31_TICK_EXACT_SAME_ZOMBIE_SOURCE_ONLY"
    report["real_java_pid_and_jar_attested_here"] = False
    report["real_client_observation_attested_here"] = False
    report["physical_world_evidence_qualified_here"] = False
    return report



def main(argv: list[str] | None = None) -> int:
    """Offline readback of a separately captured original Paper log."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-original", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--marker", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if (
            not args.paper_original.is_absolute()
            or not args.report.is_absolute()
            or args.paper_original.is_symlink()
            or args.report.is_symlink()
            or args.paper_original == args.report
            or args.report.exists()
        ):
            raise PaperZombieSourceRejected(
                "absolute original, unused distinct report and no symlink required"
            )
        with args.paper_original.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        report = report_paper_only(
            raw, sha256=args.expected_sha256, marker=args.marker,
            session=args.session,
        )
        # The write is create-only; the raw original and prior reports stay intact.
        with args.report.open("x", encoding="utf-8") as output:
            json.dump(report, output, ensure_ascii=False, sort_keys=True, indent=2)
            output.write("\n")
    except (PaperZombieSourceRejected, OSError, ValueError) as exc:
        print(f"L_ZOMBIE_PAPER_AUDIT_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "classification": report["classification"],
        "original_sha256": report["paper_log_sha256"],
        "paper_only": True, "real_client_attested": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
