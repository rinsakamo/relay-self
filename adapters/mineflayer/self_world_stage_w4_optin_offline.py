"""W4 Phase-A: immutable DEV readback of one original-component composition.

Only verifies already produced local fixtures and original single-session
read audit. No session launch, Java/Node server, World command, Action grant,
or S10 path. Producer-provided evidence never becomes physical authority.
"""
from __future__ import annotations

from pathlib import Path

from adapters.mineflayer.normal_action import NormalActionClosedReadback
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_world_stage_w3_capture import (
    W3CaptureRejected,
    audit_w3_sealed_stdout,
)
from adapters.mineflayer.self_world_stage_w4_lease import W4DevLeasedSession
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from adapters.mineflayer.self_world_stage_w4_prehost import (
    W4PrehostLedger,
    join_w4_prehost_s16_offline,
)
from adapters.mineflayer.self_world_stage_w4_window import (
    W4WindowEvent,
    reconcile_w4_window_offline,
)
from relay_self.reactive_l0 import L0Step


def reconcile_w4_s49_optin_offline(
    *, session: W4DevLeasedSession, ledger: W4PrehostLedger,
    before: MineflayerObservation, after: MineflayerObservation,
    host_trace: tuple[L0Step, ...],
    events: tuple[W4WindowEvent, ...],
    expected_session: str, before_request_id: str, after_request_id: str,
    slot: int, one_time_token: str,
    original_closed: NormalActionClosedReadback | None,
) -> dict:
    """Check *one* local lease + ledger + server marker + S49 host + S16.

    The port deliberately accepts no server, process, callback, command or
    token that could initiate new World/Action execution. Even a successful
    cross-reference is not external source or lease qualification.
    """
    if (
        type(session) is not W4DevLeasedSession
        or session.phase != "HOST"
        or session._pending is not None
        or session._active or session._delegated
        or session._handoff_pending is not None
        or session._ledger is not ledger
        or not session._marker
        or session._bridge is None
        or session._bridge._handoff._marker is None
        or type(ledger) is not W4PrehostLedger
        or ledger.delivery_scope != "PREWORLD_EVIDENCE_ONLY_NOT_L0_STIMULUS"
        or ledger.original_reader_lease_attested
        or ledger.external_source_qualified
        or ledger.physical_run_permitted
        or not ledger.captured_frames
        or ledger.captured_frames[-1] != before
        or ledger.probe_reference != before.provenance.reference
        or type(before) is not MineflayerObservation
        or type(after) is not MineflayerObservation
        or before.session_id != expected_session
        or after.session_id != expected_session
        or before.request_id != before_request_id
        or after.request_id != after_request_id
        or not isinstance(host_trace, tuple)
        or len(host_trace) != 1
        or type(host_trace[0]) is not L0Step
        or host_trace[0].choice.probe_seq != after.seq
    ):
        raise W4PreworldBlocked("W4 opt-in offline original-owner witness not complete")

    # Actual *inherited* decoder and single receive call history on one
    # in-process session, no synthesis of timestamps or source identifiers.
    audit = session.audit
    decoded = [a for a in audit if a.event == "DECODED"]
    delivered = [a for a in audit if a.event == "DELIVER"]
    if (
        not audit or any(a.event in {"DENY", "ABORT"} for a in audit)
        or len(delivered) != len(decoded)
        or len({a.seq for a in delivered}) != len(delivered)
        or [a.seq for a in delivered] != sorted(a.seq for a in delivered)
        or not any(a.phase == "PREWORLD" and a.seq == before.seq for a in delivered)
        or not any(a.phase == "HOST" and a.seq == after.seq for a in delivered)
        or any(a.phase == "WORLD_WINDOW" for a in delivered)
        or any(a.phase != "PREWORLD" for a in delivered if a.seq in {
            f.seq for f in ledger.captured_frames
        } if a.seq >= ledger.first_seq)
        or any(a.phase == "HOST" and a.seq <= before.seq for a in delivered)
        or not all(f.session_id == expected_session for f in ledger.captured_frames)
        or tuple(f.seq for f in ledger.captured_frames)
           != tuple(range(ledger.first_seq, ledger.last_seq + 1))
        or ledger.last_seq != before.seq
    ):
        raise W4PreworldBlocked("preworld/host native receiver accounting mismatch")

    window = reconcile_w4_window_offline(
        before, after, expected_session=expected_session,
        before_request_id=before_request_id,
        after_request_id=after_request_id,
        minimum_seq=before.seq, slot=slot,
        one_time_token=one_time_token,
        events=events, seen_tokens=frozenset(),
    )
    if (
        window["before_source"] != ledger.probe_reference
        or window["after_source"] != after.provenance.reference
        or session._bridge._handoff._marker.log_line != events[5].content
        or not session._bridge._handoff._marker.producer_content_only
        or session._bridge._handoff._marker.external_source_qualified
    ):
        raise W4PreworldBlocked("collector readback does not bind owner")
    step = host_trace[0]
    if (
        step.choice.entity_id != window["observed_zombie_id"]
        or step.choice.request_id != after.request_id
        or step.choice.provenance != after.provenance
    ):
        raise W4PreworldBlocked("original host L0 target/source does not bind window")

    joined = None
    if original_closed is None:
        if step.asks_for_action:
            raise W4PreworldBlocked("issued Action has no original S16 closure")
    else:
        if (
            type(original_closed) is not NormalActionClosedReadback
            or not step.asks_for_action
            or original_closed.original_probe != after
            or original_closed.terminal.action_id != step.action_request_id
            or original_closed.consequence.session_id != expected_session
        ):
            raise W4PreworldBlocked("original S16 owner/Action does not bind host")
        joined = join_w4_prehost_s16_offline(
            before, original_closed,
            expected_session=expected_session,
            before_request_id=before_request_id,
            minimum_seq=before.seq, slot=slot,
            one_time_token=one_time_token, events=events,
            seen_tokens=frozenset(),
        )

    return {
        "schema": "W4_S49_OPTIN_COMPOSITION_OFFLINE_V0",
        "session_id": expected_session,
        "native_decoded_frames": len(decoded),
        "native_delivered_frames": len(delivered),
        "preworld_captured_sequences": [f.seq for f in ledger.captured_frames],
        "preworld_unsolicited_sequences": [f.seq for f in ledger.buffered_frames],
        "host_decisions": len(host_trace),
        "original_s16_closed": joined is not None,
        "window": window,
        "original_s16_stage_s_join": joined,
        "evidence_scope": "SYNTHETIC_DEV_ONLY",
        "live_owner_attested": False,
        "external_custody_qualified": False,
        "physical_run_permitted": False,
        "s10_permission": False,
        "science_qualified": False,
    }


def seal_w4_s49_optin_offline(
    *, session: W4DevLeasedSession, composition: dict,
) -> dict:
    """Recheck a local Phase-A result *after* original session shutdown.

    This is a read-only, synthetic close-out check, not an external receipt
    signature. It cannot make Java/Node execution or S49 qualification legal.
    """
    if (
        type(session) is not W4DevLeasedSession
        or type(composition) is not dict
        or composition.get("schema") != "W4_S49_OPTIN_COMPOSITION_OFFLINE_V0"
        or composition.get("session_id") != session.started.session_id
        or composition.get("evidence_scope") != "SYNTHETIC_DEV_ONLY"
        or any(composition.get(field) is not False for field in (
            "live_owner_attested", "external_custody_qualified",
            "physical_run_permitted", "s10_permission", "science_qualified",
        ))
        or session.phase != "CLOSED"
        or not session._shutdown_completed
        or session.process_returncode != 0
        or session._pending is not None
        or session._active
        or session._delegated
        or session._handoff_pending is not None
        or session._actor is not session._controller
        or session._ledger is None
        or not session._marker
    ):
        raise W4PreworldBlocked("W4 synthetic original-session shutdown not sealed")

    audit = session.audit
    decoded = [a for a in audit if a.event == "DECODED"]
    delivered = [a for a in audit if a.event == "DELIVER"]
    if (
        not audit
        or any(a.event in {"DENY", "ABORT"} for a in audit)
        or len(decoded) != len(delivered)
        or len({a.seq for a in delivered}) != len(delivered)
        or composition.get("native_decoded_frames") != len(decoded)
        or composition.get("native_delivered_frames") != len(delivered)
        or not any(a.event == "OPEN" and a.phase == "SHUTDOWN" for a in audit)
        or audit[-1].event != "OPEN"
        or audit[-1].phase != "CLOSED"
        or any(a.phase == "SHUTDOWN" and a.event == "DELIVER" for a in audit)
    ):
        raise W4PreworldBlocked("W4 synthetic shutdown audit or receipt inconsistent")

    return {
        **composition,
        "schema": "W4_S49_OPTIN_COMPOSITION_OFFLINE_CLOSED_V0",
        "local_shutdown_completed": True,
        "node_exit_code": 0,
        # Reassert the ceiling explicitly: software-only closure.
        "live_owner_attested": False,
        "external_custody_qualified": False,
        "physical_run_permitted": False,
        "s10_permission": False,
        "science_qualified": False,
    }


def audit_original_s49_cleanup_claim_offline(*, report: dict) -> dict:
    """Fail-closed readback of the *reported* S49 Node/Java cleanup.

    Neither S49's earlier Action PASS nor an unverified W3 receipt can
    authorize W4. This examines producer-supplied claims only: it is not
    independent raw evidence, OS custody, or a replacement for original
    S49 finalization. No subprocess, World or action can be launched here.
    """
    if type(report) is not dict:
        raise W4PreworldBlocked("S49 cleanup claim must be a report object")
    if (
        report.get("milestone") != "S49"
        or report.get("stage") != "CLOSED"
        or report.get("status") != "PASS"
        or type(report.get("node_exit")) is not int
        or report["node_exit"] != 0
        or type(report.get("server_exit")) is not int
        or report["server_exit"] != 0
        or any(key in report for key in (
            "node_cleanup_error", "server_cleanup_error", "error",
        ))
        or not isinstance(report.get("session_id"), str)
        or not report["session_id"]
    ):
        raise W4PreworldBlocked("S49 Action PASS does not attest clean Node/Java exit")

    # Do not consume stale qualified labels or extra cleanup failure keys.
    # A report-only candidate PASS is NOT a physically trusted PASS.
    prospective = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=0,
    )
    if (
        prospective["candidate_final_status"] != "PASS"
        or prospective["candidate_final_classification"]
           != report.get("classification")
    ):
        raise W4PreworldBlocked("S49 producer status or class was not finalized")

    # Baseline original S49 need not capture Node shutdown ACK at all.
    # Consequently an old baseline PASS is NEVER sufficient for a W4
    # source/STOP gate. Even a well-formed W3 local receipt is not external.
    capture = report.get("w3_node_stdout_capture")
    if (
        type(capture) is not dict
        or capture.get("schema") != "relay-self-w3-node-stdout-v0"
        or capture.get("scope") != "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP"
        or capture.get("session_id") != report["session_id"]
        or capture.get("status") != "COMPLETE_NODE_STDOUT"
        or capture.get("eof_observed") is not True
        or type(capture.get("shutdown_ack_count")) is not int
        or capture["shutdown_ack_count"] != 1
        or type(capture.get("process_exit_code")) is not int
        or capture["process_exit_code"] != 0
        or capture.get("seal_reason") != "clean_shutdown"
        or capture.get("capture_fault") is not None
        or any(capture.get(key) is not False for key in (
            "minecraft_tcp_packets_attested",
            "external_source_independence_attested",
            "s10_commit_permitted", "physical_wait_permitted",
            "science_qualified",
        ))
    ):
        raise W4PreworldBlocked("S49 producer STOP/EOF claim is missing or incomplete")

    return {
        "schema": "W4_S49_CLEANUP_CLAIM_OFFLINE_V0",
        "session_id": report["session_id"],
        "node_exit_code": 0,
        "server_exit_code": 0,
        "producer_claimed_stop_ack": 1,
        "evidence_scope": "UNTRUSTED_REPORT_CONTENT_ONLY",
        "raw_stdout_independently_replayed": False,
        "live_owner_attested": False,
        "external_custody_qualified": False,
        "physical_run_permitted": False,
        "s10_permission": False,
        "science_qualified": False,
    }



def replay_original_s49_cleanup_stdout_offline(
    *, report: dict, archive_root: Path,
) -> dict:
    """Replay local W3 raw frames, binding source files to the S49 report.

    Existing independent decoder replay validates W3 raw bytes and receipt.
    The producer and its local archive are NOT an independent external source.
    No live Node, Java, TCP, Action, grant, or S10 API is accessible here.
    """
    claim = audit_original_s49_cleanup_claim_offline(report=report)
    if (
        not isinstance(archive_root, Path)
        or not archive_root.is_absolute()
        or not archive_root.is_dir()
        or archive_root.is_symlink()
        or any(parent.is_symlink() for parent in archive_root.parents)
    ):
        raise W4PreworldBlocked("W3 local replay requires an existing real directory")
    try:
        replayed = audit_w3_sealed_stdout(archive_root)
    except (W3CaptureRejected, OSError, ValueError) as exc:
        raise W4PreworldBlocked("W3 local raw receipt replay rejected") from exc
    if (
        replayed != report["w3_node_stdout_capture"]
        or replayed["session_id"] != claim["session_id"]
        or replayed["process_exit_code"] != claim["node_exit_code"]
    ):
        raise W4PreworldBlocked("W3 replay and original S49 report diverged")
    return {
        **claim,
        "schema": "W4_S49_CLEANUP_RAW_REPLAY_OFFLINE_V0",
        "raw_stdout_independently_replayed": True,
        "evidence_scope": "LOCAL_W3_RAW_REPLAY_NOT_EXTERNAL_CUSTODY",
        "node_stdout_sha256": replayed["stdout_sha256"],
        "node_stdout_frame_count": replayed["frame_count"],
        "live_owner_attested": False,
        "external_custody_qualified": False,
        "physical_run_permitted": False,
        "s10_permission": False,
        "science_qualified": False,
    }


def review_w4_s49_phase_b_optin_offline(
    *, selected_mode: str, explicit_opt_in: bool, closed_composition: dict,
    report: dict, archive_root: Path,
) -> dict:
    """Review an explicit W4 *offline* branch; never select a live owner.

    Deliberately accepts no session factory, shell command, native stream,
    actual W4 grant, or callback. Physical opt-in is not wired or authorized.
    """
    if (
        selected_mode != "W4_S49_SYNTHETIC_OFFLINE_REVIEW"
        or explicit_opt_in is not True
        or type(closed_composition) is not dict
        or closed_composition.get("schema")
           != "W4_S49_OPTIN_COMPOSITION_OFFLINE_CLOSED_V0"
        or closed_composition.get("local_shutdown_completed") is not True
        or type(closed_composition.get("node_exit_code")) is not int
        or closed_composition["node_exit_code"] != 0
        or closed_composition.get("evidence_scope") != "SYNTHETIC_DEV_ONLY"
        or any(closed_composition.get(key) is not False for key in (
            "live_owner_attested", "external_custody_qualified",
            "physical_run_permitted", "s10_permission", "science_qualified",
        ))
    ):
        raise W4PreworldBlocked("W4 Phase B live opt-in is not authorized")

    # The S49 producer's provisional success CLASSIFICATION cannot be
    # consumed without the same closeout decision as status and exit code.
    # This is still producer report consistency, not external attestation.
    classification = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=0,
    )
    if (
        classification["candidate_final_status"] != "PASS"
        or classification["candidate_final_classification"]
           != report.get("classification")
        or classification["reported_cleanup_consistent"] is not True
    ):
        raise W4PreworldBlocked("S49 cleanup or classification does not permit review")

    # Re-run the actual on-disk decoder/replay at the review boundary:
    # passing a caller-constructed "replayed" dict is insufficient.
    cleanup_claim = replay_original_s49_cleanup_stdout_offline(
        report=report, archive_root=archive_root,
    )
    if (
        closed_composition["session_id"] != cleanup_claim["session_id"]
        or cleanup_claim["raw_stdout_independently_replayed"] is not True
    ):
        raise W4PreworldBlocked("W4 offline review source identity mismatch")

    return {
        "schema": "W4_S49_PHASE_B_OPTIN_OFFLINE_REVIEW_V0",
        "selected_mode": selected_mode,
        "scope": "SYNTHETIC_LOCAL_W3_RAW_REPLAY_NO_EXTERNAL_CUSTODY",
        "original_s49_qualify_wired": False,
        "live_original_owner_permitted": False,
        "physical_run_permitted": False,
        "external_custody_qualified": False,
        "s10_permission": False,
        "science_qualified": False,
        "next_gate": "W4_EXTERNAL_TRUST_NO_GO_PREWORLD_BLOCKED",
    }


def review_s49_cleanup_finalization_candidate(
    *, report: dict, provisional_rc: int,
) -> dict:
    """Prospective S49 final-status policy, WITHOUT changing protected S49.

    Pure offline evaluation of an existing producer report. This does NOT
    rewrite the report or an archived S49 outcome and gives no W4 authority.
    """
    if (
        type(report) is not dict
        or report.get("milestone") != "S49"
        or type(report.get("status")) is not str
        or report["status"] not in {"PASS", "FAIL", "BLOCKED"}
        or (
            "stage_r_dev_enabled" in report
            and type(report["stage_r_dev_enabled"]) is not bool
        )
        or type(provisional_rc) is not int
        or provisional_rc not in {0, 1, 2}
    ):
        raise W4PreworldBlocked("invalid prospective S49 finalization input")

    previous_status = report["status"]
    # Never turn a previously failed or blocked run into PASS.
    if previous_status != "PASS":
        expected_rc = 1 if previous_status == "FAIL" else 2
        if provisional_rc != expected_rc:
            raise W4PreworldBlocked("inconsistent provisional failure status/exit")
        return {
            "schema": "W4_S49_CLEANUP_FINALIZATION_CANDIDATE_OFFLINE_V0",
            "previous_status": previous_status,
            "candidate_final_status": previous_status,
            "candidate_rc": expected_rc,
            "candidate_final_classification": "S49_SESSION_NOT_QUALIFIED",
            "candidate_classification_scope": "UNTRUSTED_PRODUCER_REPORT_ONLY",
            "reported_cleanup_consistent": False,
            "veto_reasons": ["PRIOR_NONPASS"],
            "original_report_mutated": False,
            "original_qualify_modified": False,
            "raw_stdout_independently_replayed": False,
            "external_custody_qualified": False,
            "physical_run_permitted": False,
            "science_qualified": False,
        }

    vetoes: list[str] = []
    classification = report.get("classification")
    expected_class = (
        "DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2"
        if report.get("stage_r_dev_enabled") is True
        else "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED"
    )
    if classification != expected_class:
        vetoes.append("PROVISIONAL_CLASSIFICATION_INVALID")
    if report.get("stage") != "CLOSED" or provisional_rc != 0:
        vetoes.append("PREMATURE_PASS")
    if type(report.get("node_exit")) is not int or report["node_exit"] != 0:
        vetoes.append("NODE_EXIT_NOT_ZERO")
    for key, reason in (
        ("node_cleanup_error", "NODE_CLEANUP_ERROR"),
        ("node_terminate_error", "NODE_TERMINATE_ERROR"),
        ("stage_r_cleanup_error", "STAGE_R_CLEANUP_ERROR"),
        ("stage_world_cleanup_error", "STAGE_WORLD_CLEANUP_ERROR"),
        ("temp_cleanup_error", "TEMP_CLEANUP_ERROR"),
        ("error", "PREEXISTING_PRODUCER_ERROR"),
    ):
        if key in report:
            vetoes.append(reason)
    if type(report.get("server_exit")) is not int or report["server_exit"] != 0:
        vetoes.append("JAVA_EXIT_NOT_ZERO")
    if "server_cleanup_error" in report:
        vetoes.append("JAVA_CLEANUP_ERROR")

    # Normal historical S49 does not capture shutdown ACK. Its process
    # exit can be checked, but do not manufacture an ACK it did not collect.
    # When W3 capture is explicitly present, require its genuine local
    # producer completeness claim; independent raw replay remains separate.
    if "w3_node_stdout_capture" in report:
        capture = report["w3_node_stdout_capture"]
        if (
            type(capture) is not dict
            or capture.get("schema") != "relay-self-w3-node-stdout-v0"
            or capture.get("scope") != "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP"
            or capture.get("status") != "COMPLETE_NODE_STDOUT"
            or capture.get("session_id") != report.get("session_id")
            or capture.get("eof_observed") is not True
            or type(capture.get("shutdown_ack_count")) is not int
            or capture["shutdown_ack_count"] != 1
            or type(capture.get("process_exit_code")) is not int
            or capture["process_exit_code"] != 0
            or capture.get("capture_fault") is not None
            or capture.get("seal_reason") != "clean_shutdown"
            or any(capture.get(key) is not False for key in (
                "minecraft_tcp_packets_attested",
                "external_source_independence_attested",
                "s10_commit_permitted", "physical_wait_permitted",
                "science_qualified",
            ))
        ):
            vetoes.append("W3_CAPTURE_INCOMPLETE")

    return {
        "schema": "W4_S49_CLEANUP_FINALIZATION_CANDIDATE_OFFLINE_V0",
        "previous_status": previous_status,
        "candidate_final_status": "FAIL" if vetoes else "PASS",
        "candidate_rc": 1 if vetoes else 0,
        "candidate_final_classification": (
            "S49_SESSION_NOT_QUALIFIED" if vetoes else expected_class
        ),
        "candidate_classification_scope": "UNTRUSTED_PRODUCER_REPORT_ONLY",
        "reported_cleanup_consistent": not vetoes,
        "veto_reasons": vetoes,
        "original_report_mutated": False,
        "original_qualify_modified": False,
        "raw_stdout_independently_replayed": False,
        "external_custody_qualified": False,
        "physical_run_permitted": False,
        "science_qualified": False,
    }
