"""Read-only Self product bridge to unchanged Lane C C15 spatial witness.

Unlike S49 Action OUTCOME, a C15 spatial endpoint needs TWO source-owned
poststop probes. The existing Self S49 report alone has only one and MUST NOT
be turned into a goal label. This adapter never observes, issues, authorizes,
replays, stores LearningFeedback or changes a Habit.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from adapters.mineflayer.goal_witness import (
    EndpointReducer,
    Region,
    SpatialContract,
    manifest,
)
from adapters.mineflayer.python_protocol import MineflayerStreamDecoder
from adapters.mineflayer.self_action_evidence import (
    NativeEvidenceRejected,
    verify_native_action_evidence,
)
from adapters.mineflayer.self_demo import DemoRejected, project_native_report

MAX_SOURCE_BYTES = 2_000_000
MAX_SOURCE_LINES = 256
MAX_REPORT_BYTES = 2_000_000


@dataclass(frozen=True)
class SelfSpatialReview:
    classification: str
    reason: str
    action_id: str | None
    world_session: str | None
    source_references: tuple[str, ...] = ()
    # All of the following are ALWAYS false. C15 sees a reported spatial
    # endpoint, never a signed task-success criterion or physical identity.
    physical_source_attested: bool = False
    action_caused_goal: bool = False
    goal_success_signed: bool = False
    negative_reward_signed: bool = False
    learning_feedback_created: bool = False
    production_habit_granted: bool = False
    world_actions_issued: int = 0
    l2_calls: int = 0


def _deny(reason: str, action: str | None = None,
          session: str | None = None) -> SelfSpatialReview:
    return SelfSpatialReview("UNDETERMINED", reason, action, session)


def _json_frame(message: Any) -> dict[str, Any]:
    # Typed protocol decoder owns source/ref/seq validation.
    frame = json.loads(json.dumps(asdict(message), ensure_ascii=False, allow_nan=False))
    # Match the ORIGINAL S16 retained frame format: source provenance is a
    # derived Mineflayer protocol property, not a dataclass field.
    frame["provenance"] = asdict(message.provenance)
    return frame


def review_s49_spatial(
    native_report: object,
    original_source_lines: Iterable[str],
    *,
    goal: Region,
    alternative: Region,
    action_index: int,
) -> SelfSpatialReview:
    """Source-match all FOUR S16 frames; require extra original 2nd poststop.

    The caller is an offline reviewer of locally supplied evidence, NOT a
    privileged attester. No post-hoc synthetic probe or revision of seq.
    """
    action_id: str | None = None
    sid: str | None = None
    try:
        if type(action_index) is not int or action_index not in (0, 1):
            return _deny("INVALID_ACTION_INDEX")
        if not isinstance(native_report, dict):
            return _deny("MISSING_NATIVE_REPORT")
        sid = native_report.get("session_id")
        if not isinstance(sid, str) or not sid:
            return _deny("MISSING_NATIVE_SESSION")
        actions = native_report.get("actual_native_actions")
        if not isinstance(actions, list) or len(actions) != 2:
            return _deny("INCOMPLETE_S49_ACTIONS", session=sid)
        candidate = actions[action_index]
        if not isinstance(candidate, dict):
            return _deny("UNTYPED_NATIVE_ACTION", session=sid)
        action_id = candidate.get("action")
        if not isinstance(action_id, str) or not action_id:
            return _deny("MISSING_ACTION_ID", session=sid)

        # Verify all three epochs/two independent S16 OUTCOME owners first.
        product_trace = project_native_report(native_report)
        if not product_trace or not isinstance(goal, Region) or not isinstance(alternative, Region):
            return _deny("INVALID_SOURCE_OR_REGIONS", action_id, sid)
        evidence = candidate.get("execution_evidence")
        if evidence is None:
            # Older real run cannot be backfilled with invented frames.
            return _deny("LEGACY_S49_ACTION_FRAMES_ABSENT", action_id, sid)
        verify_native_action_evidence(
            evidence, action_id=action_id, session_id=sid,
            movement_m=candidate["movement_m"],
        )

        spec = SpatialContract(
            sid, action_id, f"{action_id}-s15-clear",
            goal, alternative,
        )
        decoder = MineflayerStreamDecoder()
        seen: dict[int, dict[str, Any]] = {}
        source: list[str] = []
        for line in original_source_lines:
            if type(line) is not str or len(line.encode("utf-8")) > MAX_SOURCE_BYTES:
                return _deny("INVALID_OR_OVERSIZED_SOURCE_LINE", action_id, sid)
            source.append(line)
            if len(source) > MAX_SOURCE_LINES:
                return _deny("EXCESS_SOURCE_LINES", action_id, sid)
            decoded = decoder.decode(line)
            if decoded.session_id != sid:
                return _deny("FOREIGN_SOURCE_SESSION", action_id, sid)
            seen[decoded.seq] = _json_frame(decoded)
        if len(seen) != len(source) or not source:
            return _deny("REPLAYED_OR_MISSING_ORIGINAL_FRAMES", action_id, sid)

        for name in (
            "before_observation", "dispatch_receipt",
            "cleanup_receipt", "after_observation",
        ):
            # Exact decoded frames from original S16 action receipt must be
            # independently re-observed in the caller's source transcript.
            expected = evidence[name]
            seq = expected["seq"]
            if seen.get(seq) != expected:
                return _deny("S16_SOURCE_FRAME_IDENTITY_MISMATCH", action_id, sid)

        witness = EndpointReducer().qualify(source, spec)
        return SelfSpatialReview(
            classification=witness.status,
            reason=witness.reason,
            action_id=action_id,
            world_session=sid,
            source_references=witness.evidence,
        )
    except (
        ValueError, TypeError, KeyError, OSError,
        NativeEvidenceRejected, DemoRejected,
    ) as exc:
        # Lossless class name only; never accept data merely because it decoded.
        return _deny(
            "INVALID_OR_UNQUALIFIED_SOURCE:" + type(exc).__name__,
            action_id, sid,
        )


def _load_regions(path: Path) -> tuple[Region, Region]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_768:
        raise ValueError("untrusted spatial region file")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or set(doc) != {"goal", "alternative"}:
        raise ValueError("explicit goal and alternative must both be supplied")
    def parse(v: object) -> Region:
        if not isinstance(v, dict) or set(v) != {"low", "high"}:
            raise ValueError("invalid region object")
        if (not isinstance(v["low"], list) or len(v["low"]) != 3
                or not isinstance(v["high"], list) or len(v["high"]) != 3):
            raise ValueError("three-dimensional region required")
        return Region(tuple(v["low"]), tuple(v["high"]))
    return parse(doc["goal"]), parse(doc["alternative"])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read existing S49+C15 original observations; never launch World")
    p.add_argument("--native-report", type=Path, required=True)
    p.add_argument("--source-transcript", type=Path, required=True)
    p.add_argument("--regions", type=Path, required=True)
    p.add_argument("--action-index", type=int, choices=[0, 1], required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        output = args.output_dir
        dest = output / "spatial_review.json"
        if (output.is_symlink() or not output.is_dir() or
                dest.exists() or dest.is_symlink()):
            raise ValueError("output location not an empty unique evidence destination")
        for path, limit in (
            (args.native_report, MAX_REPORT_BYTES),
            (args.source_transcript, MAX_SOURCE_BYTES),
        ):
            if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
                raise ValueError("source report/transcript missing or oversized")
        goal, alternative = _load_regions(args.regions)
        manifest()  # Re-check exact C15 frozen classification contract.
        native = json.loads(args.native_report.read_text(encoding="utf-8"))
        lines = args.source_transcript.read_text(encoding="utf-8").splitlines()
        result = review_s49_spatial(
            native, lines, goal=goal,
            alternative=alternative, action_index=args.action_index,
        )
        with dest.open("x", encoding="utf-8") as fp:
            json.dump(asdict(result), fp, ensure_ascii=False, sort_keys=True, indent=2)
            fp.write("\n")
        print(json.dumps(asdict(result), sort_keys=True))
        # A recognized spatial region is an observational result only.
        return 0 if result.classification != "UNDETERMINED" else 1
    except (OSError, ValueError, TypeError, UnicodeError):
        print(json.dumps(asdict(_deny("SOURCE_PREFLIGHT_BLOCKED")), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
