"""L-BCG post-run HOST REPORT sanity only; not independent original attestation.

Use after a specifically granted disposable S49 route B World. This script
reads the existing host report and cannot establish actual Paper input clear,
source-byte authenticity, a Goal, training admission, or physical improvement.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


class BCGReportRejected(ValueError):
    """Incomplete, changed, or overclaimed source-bound host shadow."""


_REQUIRED = frozenset({
    "goal_remaining_m", "goal_tolerance_m", "selected_gait",
    "p1_fatigue_high", "m_energy_low", "verified_obstacle",
    "world_revision", "verified_post_clear_training",
})


def review_bcg_host_report(report: dict[str, object]) -> dict[str, object]:
    """Verify the report's own typed S49/readout/shadow cross references.

    This is a ONE-FILE diagnostic, NOT independent S7/S16/Paper original-byte
    checking. Reject missing fields rather than guessing physical World state.
    """
    if not isinstance(report, dict):
        raise BCGReportRejected("JSON object report required")
    try:
        session = report["session_id"]
        actions = report["actual_native_actions"]
        decisions = report["decisions"]
        shadow = report["l_bcg_shadow"]
        live = report["live_next_epoch"]
        body = live["current_body"]
        world = live["current_world"]
        bo = body["observation"]
        wo = world["observation"]
        inventory = shadow["cue_inventory"]
        observed = inventory["observed"]
    except (KeyError, TypeError) as exc:
        raise BCGReportRejected("missing S49/Body/World host report field") from exc
    if (
        type(session) is not str or not session
        or report.get("status") != "PASS" or report.get("stage") != "CLOSED"
        or report.get("learning_in_world") is not False
        or report.get("real_model_calls") != 0
        or not isinstance(actions, list) or len(actions) != 1
        or actions[0].get("terminal") != "outcome"
        or not isinstance(decisions, list) or len(decisions) != 3
        or [d.get("selected") for d in decisions]
           != ["WAIT", "MOVE_AWAY", "WAIT"]
        or [d.get("issued") for d in decisions] != [False, True, False]
    ):
        raise BCGReportRejected("real host Action/L0 control ceiling violated")
    last = decisions[-1]
    if not isinstance(bo, dict) or not isinstance(wo, dict):
        raise BCGReportRejected("typed original observation missing")
    seq = bo.get("native_seq")
    request = bo.get("request_id")
    if type(seq) is not int or seq < 1 or not isinstance(request, str) or not request:
        raise BCGReportRejected("invalid original native identity")
    native_ref = f"native-probe:{session}:{seq}:{request}"
    world_ref = f"present:{session}:{seq}:{request}"
    if (
        bo.get("session_id") != session
        or wo.get("session_id") != session
        or wo.get("native_seq") != seq
        or wo.get("request_id") != request
        or last.get("probe_seq") != seq
        or bo.get("source_provenance") != {
            "source": "mineflayer", "reference": f"{session}:{seq}"
        }
        or wo.get("provenance") != bo.get("source_provenance")
        or shadow.get("session_id") != session
        or shadow.get("original_native_ref") != native_ref
        or shadow.get("original_selection") != "WAIT"
        or inventory.get("native_source_ref") != native_ref
        or inventory.get("world_source_ref") != world_ref
    ):
        raise BCGReportRejected("S49 original native/World/source mismatch")
    if (
        shadow.get("advice") != "DEFER_UNKNOWN"
        or shadow.get("reason") != "CURRENT_GOAL_GAIT_P1_M_OBSTACLE_SOURCE_NOT_ADMITTED"
        or shadow.get("conditional") is not None
        or shadow.get("source_ceiling") != "ROUTE_B_PROVISIONAL_PAPER_NOT_POST_CLEAR_ATTESTED"
        or shadow.get("used_physical_training_worlds") != 0
        or shadow.get("original_l0_choice_kept") is not True
        or shadow.get("goal_success_attested") is not False
        or shadow.get("action_authority") is not False
        or any(shadow.get(k) != 0 for k in (
            "action_issues", "extra_native_reads", "learning_updates", "habit_grants"
        ))
        or inventory.get("full_conditional_context_available") is not False
        or inventory.get("paper_effective_input_clear_attested") is not False
        or inventory.get("post_clear_training_admitted") is not False
        or not isinstance(inventory.get("missing_required"), list)
        or not all(type(k) is str for k in inventory["missing_required"])
        or frozenset(inventory["missing_required"]) != _REQUIRED
    ):
        raise BCGReportRejected("unjustified L-BCG learning or source promotion")
    native_fields = {
        x["key"]: x["value"] for x in bo.get("fields", [])
        if isinstance(x, dict) and "key" in x and "value" in x
    }
    if not isinstance(observed, list):
        raise BCGReportRejected("observed inventory absent")
    names: set[str] = set()
    for row in observed:
        if not isinstance(row, dict) or type(row.get("name")) is not str:
            raise BCGReportRejected("invalid observed cue")
        name = row["name"]
        if name in names:
            raise BCGReportRejected("duplicate observed cue")
        names.add(name)
        if name in ("position_x", "position_y", "position_z",
                    "health", "food", "food_saturation"):
            if (
                name not in native_fields
                or row.get("value") != native_fields[name]
                or row.get("source_ref") != native_ref
            ):
                raise BCGReportRejected("native field differs from original")
        elif name == "s42_threat_distance_m":
            if row.get("value") != last.get("distance_m") or row.get("source_ref") != native_ref:
                raise BCGReportRejected("S42 distance is not original native")
        elif name == "world_observed_target_distance_m":
            entities = wo.get("entities", [])
            target_id = f"entity-{last.get('entity_id')}"
            if (
                not isinstance(entities, list)
                or not any(e.get("entity_ref") == target_id
                           and e.get("distance_m") == row.get("value") for e in entities)
                or row.get("source_ref") != world_ref
            ):
                raise BCGReportRejected("World entity distance not observed")
        else:
            raise BCGReportRejected("unrecognized/predicted cue masked as observed")

    expected_native = {
        key for key in (
            "position_x", "position_y", "position_z", "health",
            "food", "food_saturation"
        ) if key in native_fields and type(native_fields[key]) in (int, float)
    }
    if not expected_native <= names or "s42_threat_distance_m" not in names:
        raise BCGReportRejected("missing existing original native cues")
    entities = wo.get("entities")
    if not isinstance(entities, list) or not all(isinstance(e, dict) for e in entities):
        raise BCGReportRejected("invalid original World entity coverage")
    target_id = f"entity-{last.get('entity_id')}"
    present_target = next((e for e in entities if e.get("entity_ref") == target_id), None)
    expected_seen = present_target is not None
    if (
        inventory.get("coverage_scope") != wo.get("coverage_scope")
        or inventory.get("coverage_truncated") != wo.get("coverage_truncated")
        or inventory.get("target_seen_in_limited_coverage") is not expected_seen
        or (
            expected_seen and present_target.get("distance_m") is not None
            and "world_observed_target_distance_m" not in names
        )
    ):
        raise BCGReportRejected("World limited-coverage original mismatch")
    return {
        "classification": "DEV_BCG_HOST_REPORT_SELF_CONSISTENT_ONLY",
        "session_id": session,
        "native_seq": seq,
        "observed_cue_names": sorted(names),
        "required_condition_cues_missing": sorted(_REQUIRED),
        "l0_choice_modified": False,
        "action_issues": 0,
        "qualified_training_worlds": 0,
        "physical_originals_independently_attested": False,
        "goal": "UNDETERMINED",
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("host_report", type=Path)
    args = parser.parse_args()
    try:
        src = args.host_report
        if not src.is_file() or src.stat().st_size > 2_000_000:
            raise BCGReportRejected("missing or oversized original host report")
        report = json.loads(src.read_text(encoding="utf-8"))
        print(json.dumps(review_bcg_host_report(report), sort_keys=True))
        return 0
    except (OSError, ValueError, BCGReportRejected) as exc:
        parser.exit(2, f"L-BCG HOST REPORT REJECTED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
