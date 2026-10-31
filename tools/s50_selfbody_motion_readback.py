"""CLI: project sealed S50/L23 paper + Node originals into a diagnostic view.

Produces no relay_self.self_body.BodyObservation. The SelfBody owner decides
later whether/how to use this supplemental source; no actor/ledger writes.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_selfbody_motion_source import (
    project_s50_body_motion_source,
)


def review_originals(
    *, report_original: bytes, paper_original: bytes,
    client_original: bytes, subject_uuid: str,
) -> dict[str, object]:
    report = json.loads(report_original)
    l23 = report.get("l23_paper", {})
    readback = l23.get("readback", {})
    actions = report.get("actual_native_actions", [])
    if (
        report.get("status") != "PASS"
        or report.get("node_exit") != 0
        or report.get("server_exit") != 0
        or l23.get("status") != "PAPER_SOURCE_SHAPE_REVIEWED_ONLY"
        or not isinstance(actions, list) or len(actions) != 1
        or not isinstance(readback, dict)
        or readback.get("session_id") != report.get("session_id")
        or actions[0].get("terminal") != "outcome"
    ):
        raise ValueError("S49/L23 source not a closed single-Action DEV result")
    action = actions[0].get("action")
    if not isinstance(action, str):
        raise ValueError("S49 Action source identity missing")
    view = project_s50_body_motion_source(
        paper_original=paper_original,
        client_original=client_original,
        l23_source_readback=readback,
        session_id=report["session_id"], action_id=action,
        world=readback["paper_world"], subject_uuid=subject_uuid,
        first_tick=readback["paper_first_tick"],
    )
    return {
        "source_classification": "S50_TO_SELFBODY_CANDIDATE_READ_ONLY",
        "physical_body_diagnostic": asdict(view),
        "selfbody_native_present_admitted": False,
        "physical_wait_admitted": False,
        "world_time_alignment_attested": False,
        "goal_admitted": False,
        "learning_updates": 0,
        "qualification": "DEV_ONLY",
        "science": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--s49-report", type=Path, required=True)
    parser.add_argument("--paper-original", type=Path, required=True)
    parser.add_argument("--client-original", type=Path, required=True)
    parser.add_argument("--subject-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    result = review_originals(
        report_original=a.s49_report.read_bytes(),
        paper_original=a.paper_original.read_bytes(),
        client_original=a.client_original.read_bytes(),
        subject_uuid=a.subject_uuid,
    )
    a.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "source_classification": result["source_classification"],
        "motion_with_reported_input_off_ticks": result[
            "physical_body_diagnostic"
        ]["observed_motion_while_reported_input_off_ticks"],
        "selfbody_native_present_admitted": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
