"""View completed Self S49/L0/L2/Memory together with Lane C C15 spatial evidence.

Offline/read-only: never imports a Minecraft runner, Node, llama.cpp, an Action
issuer, S17 feedback, S10 learning or S11 habit owner. Source-shaped C15 region
recognition is NOT an attestation of physical World/task success.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from adapters.mineflayer.self_timeline import (
    MAX_SOURCE_BYTES,
    SCHEMA,
    _read_json,
    timeline,
)

from adapters.mineflayer.goal_witness import InvalidSpatialContract, Region, SpatialContract
from adapters.mineflayer.self_lane_c_witness import qualify_self_action_spatial
from relay_self.persistent_cognition import load_persistent_cognition

SPATIAL_QUESTIONS_SCHEMA = "SELF_LANEC_C15_SPATIAL_QUESTIONS_V1"


class SpatialTimelineRejected(ValueError):
    """Non-complete, cross-session, unsigned or unbounded source question."""


def _file(path: Path, *, max_bytes: int = MAX_SOURCE_BYTES) -> str:
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size > max_bytes):
        raise SpatialTimelineRejected("bounded regular source file required")
    return path.read_text(encoding="utf-8")


def _region(value: object) -> Region:
    if (not isinstance(value, dict) or set(value) != {"low", "high"}
            or any(type(value.get(k)) is not list or len(value[k]) != 3
                   for k in ("low", "high"))):
        raise SpatialTimelineRejected("explicit bounded region required")
    return Region(tuple(value["low"]), tuple(value["high"]))


def spatial_questions(doc: object, *, session_id: str,
                      actions: set[str]) -> dict[str, SpatialContract]:
    """Caller-specified retrospective regions, NOT precommitted task goals."""
    if (not isinstance(doc, dict)
            or set(doc) != {"schema", "session_id", "questions"}
            or doc["schema"] != SPATIAL_QUESTIONS_SCHEMA
            or doc["session_id"] != session_id
            or type(doc["questions"]) is not list
            or len(doc["questions"]) != len(actions) or len(actions) != 2):
        raise SpatialTimelineRejected("questions do not cover exactly this S49 session")
    result: dict[str, SpatialContract] = {}
    for question in doc["questions"]:
        if (not isinstance(question, dict)
                or set(question) != {"action_id", "goal", "alternative"}
                or not isinstance(question["action_id"], str)
                or question["action_id"] not in actions
                or question["action_id"] in result):
            raise SpatialTimelineRejected("foreign, missing or duplicate Action question")
        aid = question["action_id"]
        try:
            result[aid] = SpatialContract(
                session_id, aid, f"{aid}-s15-clear",
                _region(question["goal"]), _region(question["alternative"]),
            )
        except (InvalidSpatialContract, ValueError, TypeError) as exc:
            raise SpatialTimelineRejected("invalid C15 spatial contract") from exc
    if set(result) != actions:
        raise SpatialTimelineRejected("two exact Action questions required")
    return result


def timeline_with_spatial(
    report: dict[str, Any], *,
    questions: object,
    original_bridge_lines: tuple[str, ...] | None = None,
    live_l2: dict[str, Any] | None = None,
    memory: Any | None = None,
) -> tuple[dict[str, Any], ...]:
    """Compose retained product timeline with two C15 observational events.

    The original action_outcome event always says spatial_goal_success=UNKNOWN.
    Returned spatial region labels never modify it or grant Action/Learning.
    """
    base = timeline(report, live_l2=live_l2, memory=memory)
    sid = base[0]["session"]
    actions = {row["action_id"] for row in base if row["kind"] == "action_outcome"}
    specs = spatial_questions(questions, session_id=sid, actions=actions)
    result: list[dict[str, Any]] = []
    statuses: list[str] = []
    for event in base:
        if event["kind"] == "summary":
            event = {
                **event,
                "lane_c_spatial_events": len(statuses),
                "lane_c_regions_observed": statuses,
                "lane_c_physical_goal_attested": False,
                "lane_c_s17_feedback_issued": False,
            }
        result.append(event)
        if event["kind"] != "action_outcome":
            continue
        aid = event["action_id"]
        observation = qualify_self_action_spatial(
            report, action_id=aid, spec=specs[aid],
            source_lines=original_bridge_lines,
        )
        statuses.append(observation.status)
        result.append({
            "schema": SCHEMA,
            "kind": "lane_c_spatial_observation",
            "session": sid,
            "epoch": event["epoch"],
            "action_id": aid,
            "source_owner": "LANE_C_C15_FROZEN_READ_ONLY",
            "question_origin": "CALLER_SUPPLIED_RETROSPECTIVE_NOT_PRECOMMITTED_GOAL",
            "region_status": observation.status,
            "region_reason": observation.reason,
            "source_references": list(observation.source_references),
            "source_sha256": observation.source_sha256,
            "source_matches_s16": observation.source_matches_s16,
            "physical_source_attested": observation.physical_source_attested,
            "goal_success_attested": observation.goal_success_attested,
            "signed_action_label": observation.signed_action_label,
            "s17_feedback_issued": observation.s17_feedback_issued,
            "s10_updates": observation.s10_updates,
            "s11_habit_promotions": observation.s11_habit_promotions,
        })
    if len(statuses) != 2:
        raise SpatialTimelineRejected("two original S49 Actions required")
    return tuple(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline Self/World/L0/L2/Memory + Lane C spatial read-only view"
    )
    parser.add_argument("--native-report", type=Path, required=True)
    parser.add_argument("--spatial-questions", type=Path, required=True)
    parser.add_argument("--bridge-jsonl", type=Path,
                        help="optional ORIGINAL full Mineflayer source, never invented")
    parser.add_argument("--live-l2", type=Path)
    parser.add_argument("--memory", type=Path)
    parser.add_argument("--format", choices=("jsonl", "text"), default="text")
    args = parser.parse_args(argv)
    try:
        report = _read_json(args.native_report)
        questions = json.loads(_file(args.spatial_questions))
        original_lines = (
            tuple(_file(args.bridge_jsonl).splitlines(keepends=True))
            if args.bridge_jsonl is not None else None
        )
        l2 = None
        if args.live_l2 is not None:
            l2_lines = _file(args.live_l2).splitlines()
            if len(l2_lines) != 1:
                raise SpatialTimelineRejected("one L2 sidecar is required")
            l2 = json.loads(l2_lines[0])
        mem = None
        if args.memory is not None:
            if not _file(args.memory):
                raise SpatialTimelineRejected("empty Memory source")
            mem = load_persistent_cognition(args.memory)
        rows = timeline_with_spatial(
            report, questions=questions, original_bridge_lines=original_lines,
            live_l2=l2, memory=mem,
        )
        if args.format == "jsonl":
            print("".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                for row in rows
            ), end="")
        else:
            for row in rows:
                if row["kind"] == "lane_c_spatial_observation":
                    print(
                        f"Action {row['action_id']}: Lane C spatial "
                        f"{row['region_status']} ({row['region_reason']}); "
                        "goal success UNKNOWN, no S17/S10/S11 authority"
                    )
                elif row["kind"] == "summary":
                    print(
                        f"Self {row['session']}: {row['decisions']} L0 decisions, "
                        f"{row['native_action_outcomes']} World outcomes, "
                        f"{row['lane_c_spatial_events']} Lane C read-only observations"
                    )
        return 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError,
            IndexError, OverflowError):
        print(json.dumps({
            "schema": SCHEMA, "status": "UNDETERMINED",
            "reason": "SPATIAL_VIEW_SOURCE_REJECTED",
            "world_actions_issued": 0, "model_requests_issued": 0,
            "s17_feedback_issued": False, "s10_updates": 0, "s11_promotions": 0,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
