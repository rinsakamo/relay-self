"""Independent D14 R3 natural World audit: source-clock OR actual early Self end.

No D4/D8 food-success authority is used. No third kill/Skill/learning claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.bug0_d14_natural_world import (
    NATURAL_PLUGIN_CONFIG,
    NaturalPaperTimeline,
    marker_kind,
    natural_properties,
)


class D14NaturalAuditRejected(ValueError):
    """Original Paper/event-journal pair or natural World contract invalid."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_natural(
    report: dict[str, Any], original: str, derivative: str,
    *, original_sha: str, derivative_sha: str,
) -> dict[str, Any]:
    if (
        report.get("status") != "PASS_DEV"
        or report.get("cleanup_done") is not True
        or report.get("java_exit") != 0
        or report.get("node_exit") != 0
        or report.get("paper_original_sha256") != original_sha
        or report.get("derivative_journal_sha256") != derivative_sha
        or report.get("world_config") != "NATURAL_SURVIVAL"
        or report.get("plugin_config") != NATURAL_PLUGIN_CONFIG
        or report.get("s49_physical_issuer") != "NOT_CONNECTED_IN_R3_OBSERVER"
        or report.get("operator_commands") != []
        or any(report.get(k) is not False for k in (
            "staged_zombie_no_ai", "staged_zombie_low_health",
            "staged_hunger_effect", "staged_enemy_teleport",
        ))
        or report.get("natural_mob_spawning_unchanged") is not True
        or report.get("world_daylight_behavior") != "VANILLA"
        or report.get("managed_respawn_after_real_death_ticks") != 600
        or any(report.get(k) != 0 for k in (
            "new_s49_actions", "model_posts", "learning_updates",
            "skill_installs",
        ))
    ):
        raise D14NaturalAuditRejected("NATURAL_WORLD_SOURCE_OR_AUTHORITY_MISMATCH")
    expected = natural_properties(report.get("server_properties", ""))
    if (
        report["server_properties"] != expected
        or "level-type=minecraft:normal\n" not in expected
        or "gamemode=survival\n" not in expected
        or "difficulty=normal\n" not in expected
    ):
        raise D14NaturalAuditRejected("NONNATURAL_SERVER_CONFIGURATION")

    # Independently reconstruct the World and original 600-tick rule from
    # Paper, not from the Python report or derivative assertions.
    timeline = NaturalPaperTimeline()
    originals: list[tuple[str, str]] = []
    for line in original.splitlines():
        kind = marker_kind(line)
        if kind is not None:
            try:
                timeline.admit(kind, line)
            except (ValueError, RuntimeError) as exc:
                raise D14NaturalAuditRejected("PAPER_ORIGINAL_WORLD_INCONSISTENT") from exc
            originals.append((kind, line))
    try:
        observed = timeline.finish()
    except (ValueError, RuntimeError) as exc:
        raise D14NaturalAuditRejected("PAPER_END_NOT_ATTESTED") from exc
    if (
        report.get("result") != observed
        or report.get("paper_source") != timeline.source_summary()
        or report.get("classification") != (
            "DEV_D14_R3_NATURAL_10000_PAPER_TICKS_OBSERVED"
            if observed["outcome"] == "WORLD_TICK_LIMIT_REACHED"
            else "DEV_D14_R3_NATURAL_EARLY_SELF_TERMINAL_OBSERVED"
        )
    ):
        raise D14NaturalAuditRejected("REPORT_RETROSPECTIVE_OUTCOME_NOT_SOURCE")

    # Derivative may contain native snapshots, but every Paper marker must
    # have exactly one identical original source line and ordering.
    journal_lines: list[tuple[str, str]] = []
    native_events = 0
    native_ids: set[str] = set()
    for line in derivative.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise D14NaturalAuditRejected("DERIVATIVE_CORRUPT") from exc
        if record.get("record_type") != "D14_R3_DERIVATIVE_SOURCE_REFERENCE":
            raise D14NaturalAuditRejected("DERIVATIVE_SOURCE_TYPE_INVALID")
        kind = record.get("kind")
        if kind in ("NATIVE_OBSERVATION", "NATIVE_OBSERVATION_FAILED"):
            if kind == "NATIVE_OBSERVATION":
                native_events += 1
                obs = record.get("native_observation")
                if (
                    not isinstance(obs, dict)
                    or obs.get("native_session_id") != report.get("native_session_id")
                    or not isinstance(obs.get("native_request_id"), str)
                    or obs.get("native_request_id") in native_ids
                    or obs.get("correlation") != "AFTER_PAPER_SAMPLE_NOT_SAME_TICK"
                ):
                    raise D14NaturalAuditRejected("NATIVE_READBACK_SOURCE_INVALID")
                native_ids.add(obs["native_request_id"])
            continue
        if kind is None or marker_kind(record.get("original_paper_line", "")) != kind:
            raise D14NaturalAuditRejected("DERIVATIVE_PAPER_SOURCE_KIND_INVALID")
        journal_lines.append((kind, record["original_paper_line"]))
    if originals != journal_lines:
        raise D14NaturalAuditRejected("DERIVATIVE_LOST_OR_REWROTE_PAPER_ORIGINAL")
    if native_events != len(report.get("native_snapshots", [])):
        raise D14NaturalAuditRejected("NATIVE_SNAPSHOT_COUNT_NOT_CONSISTENT")
    return {
        "status": "PASS_DEV",
        "classification": "D14_R3_NATURAL_WORLD_SOURCE_AUDIT_PASS",
        "world_uuid": timeline.source_summary()["world_uuid"],
        "observed_world_ticks": observed["elapsed_ticks"],
        "eventual_reason": observed["terminal_reason"],
        "reached_10000_ticks": observed["outcome"] == "WORLD_TICK_LIMIT_REACHED",
        "self_died_before_limit": observed["self_died_before_limit"],
        "managed_zombie_deaths": len(timeline.deaths),
        "managed_zombie_respawns": len(timeline.respawns),
        "original_paper_checkpoints": len(timeline.samples),
        "new_original_s49_actions": 0,
        "l2_calls": 0, "learning_updates": 0,
        "long_run_autonomous_self": False,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("report", "server-log", "event-journal", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    args = ap.parse_args()
    result = audit_natural(
        json.loads(args.report.read_text(encoding="utf8")),
        args.server_log.read_text(encoding="utf8"),
        args.event_journal.read_text(encoding="utf8"),
        original_sha=sha256(args.server_log),
        derivative_sha=sha256(args.event_journal),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(result["classification"], result["eventual_reason"])


if __name__ == "__main__":
    main()
