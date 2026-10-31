"""DEV-only cross-source S50 commanded-input / Action boundary reviewer.

This is NOT a native getControlState() readback or an authoritative Paper
server-effective command tick.  It verifies the recorded command/ACK, S15/S16
Action lifecycle, and Paper phase/WAIТ begin.  Other issuers are not covered.
"""
from __future__ import annotations

from adapters.mineflayer.m02_paper_dev.s50_boundary import (
    BoundaryRejected,
    integer,
    phases,
    rows,
    verify_native,
)


def review_control_action(
    original_paper: str, native: list[dict], commands: list[dict],
    journal: list[dict], movement: dict,
) -> dict:
    """Correlate three original S-owned streams without clock interpolation."""
    if not isinstance(movement, dict):
        raise BoundaryRejected("missing source-scoped movement")
    action = movement.get("action_id")
    session = movement.get("source_session")
    marker = movement.get("v7_phase_marker_id")
    if (not isinstance(action, str) or not action
            or not isinstance(session, str) or not session
            or marker != action + "-" + session
            or not isinstance(native, list) or not isinstance(commands, list)
            or not isinstance(journal, list)):
        raise BoundaryRejected("bad Action/session/marker provenance")
    if len(journal) != 2:
        raise BoundaryRejected("not exactly one original issued/outcome pair")
    issue, outcome = journal
    if any(not isinstance(row, dict) for row in journal):
        raise BoundaryRejected("invalid original Action journal row")
    if (issue.get("action_id") != action
            or outcome.get("action_id") != action
            or issue.get("session_id") != session
            or outcome.get("session_id") != session
            or issue.get("clock") != "SYNTHETIC_DEV_LOGICAL_ORDER_NOT_WORLD_TIME"
            or outcome.get("clock") != issue.get("clock")
            or issue.get("state") != "issued" or outcome.get("state") != "outcome"):
        raise BoundaryRejected("foreign/unclosed S15/S16 original Action")
    issued_events = issue.get("events")
    completed_events = outcome.get("events")
    if (not isinstance(issued_events, list)
            or not isinstance(completed_events, list)
            or len(issued_events) != 3
            or len(completed_events) != 4
            or completed_events[:3] != issued_events
            or [event.get("state") for event in issued_events
                if isinstance(event, dict)] != ["proposed", "authorized", "issued"]
            or not isinstance(completed_events[-1], dict)
            or completed_events[-1].get("state") != "outcome"):
        raise BoundaryRejected("invalid S15/S16 Action transition sequence")
    if outcome.get("physical_outcome") == "NOT_ATTESTED":
        raise BoundaryRejected("Action terminal outcome not physically established")

    # Requires exact original session + monotonically ordered bridge frames,
    # one applied look, forward and clear, one after-probe, one STOP ACK;
    # other recorded native effect requests or ACKs fail closed.
    verify_native(native, commands, movement)
    if any(not isinstance(row, dict) for row in commands + native):
        raise BoundaryRejected("malformed command/native row")
    issued_effects = [row for row in commands if row.get("type") == "effect"]
    if [(row.get("action_id"), row.get("effect")) for row in issued_effects] != [
            (action + "-look", "look"),
            (action, "set_control"),
            (action + "-clear", "clear_controls")]:
        raise BoundaryRejected("extraneous or reordered native motor request")
    if (issued_effects[1].get("control") != "forward"
            or issued_effects[1].get("state") is not True):
        raise BoundaryRejected("incorrect requested motor state")
    native_acks = [row for row in native if row.get("type") == "effect_result"]
    if [(row.get("action_id"), row.get("effect"), row.get("result"))
            for row in native_acks] != [
            (action + "-look", "look", "applied"),
            (action, "set_control", "applied"),
            (action + "-clear", "clear_controls", "applied")]:
        raise BoundaryRejected("missing/rejected/reordered native motor ACK")

    source_phases = phases(original_paper, marker)
    world = source_phases[0].get("world")
    if not world or any(row.get("world") != world for row in source_phases):
        raise BoundaryRejected("changed Paper World across motor brackets")
    if not all(integer(b, "world_full_time") >= integer(a, "world_full_time")
               for a, b in zip(source_phases, source_phases[1:])):
        raise BoundaryRejected("Paper phases regressed")
    begin = rows(original_paper, "S50_DEV_WAIT_BEGIN ")
    if (len(begin) != 1 or begin[0].get("marker_id") != marker
            or begin[0].get("world") != world
            or integer(begin[0], "tick") < integer(source_phases[-1], "world_full_time")):
        raise BoundaryRejected("no source-bound post-clear WAIT start")
    snapshot = rows(original_paper, "S50_DEV_WAIT_TICK ")
    if (len(snapshot) != 8
            or any(row.get("marker_id") != marker or row.get("world") != world
                   or integer(row, "index") != i
                   or integer(row, "tick") != integer(begin[0], "tick") + i
                   for i, row in enumerate(snapshot, 1))):
        raise BoundaryRejected("incomplete/foreign post-clear WAIT ticks")

    return {
        "classification": "S50_P1_RECORDED_COMMAND_AND_ACTION_BOUNDARY_ONLY",
        "action_id": action,
        "source_session": session,
        "marker_id": marker,
        "paper_world": world,
        "issued_terminal_sequence": ["issued", "outcome"],
        "native_commanded_control_after_clear": "CLEARED_BY_APPLIED_COMMAND_ACK",
        "native_held_controls_readback": "NOT_ATTESTED",
        "client_server_effective_tick_mapping": "NOT_ATTESTED",
        "all_other_action_issuers_absent": "NOT_ATTESTED",
        "physical_whole_tick_idle": "NOT_ATTESTED",
        "paper_post_clear_tick": integer(source_phases[-1], "world_full_time"),
        "paper_wait_begin_tick": integer(begin[0], "tick"),
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "independent_R_qualification": False,
        "science_go": False,
    }
