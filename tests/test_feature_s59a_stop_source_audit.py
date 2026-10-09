"""S59-A static admission tests. Never execute or cancel a real provider."""
from __future__ import annotations

import json

import pytest

from adapters.mineflayer.s59a_backend_stop_audit import (
    BINARY_SHA256_S57,
    SOURCE_HEAD_S57,
    StopAuditRejected,
    audit,
    inspect_pinned_source_text,
    main,
)


README = """
### POST `/slots/{id_slot}?action=erase`: Erase the prompt cache.
### POST `/v1/chat/completions/control`
`action`: only `reasoning_end`; reasoning control, not generation stop.
"""
CONTEXT = """
case SERVER_TASK_TYPE_CANCEL:
{
    for (auto & slot : slots) {
        if (slot.task) { slot.release(); }
    }
}
case SERVER_TASK_TYPE_SLOT_ERASE:
{
    if (slot->is_processing()) {
        queue_tasks.defer(std::move(task));
    }
}
this->post_control = [this](const server_http_req & req) {
    const std::string action = json_value(body, "action", std::string());
    if (action != "reasoning_end") {
        res->error(format_error_response("unknown control action",
                                        ERROR_TYPE_INVALID_REQUEST));
        return res;
    }
};
"""
HTTP = "request.is_connection_closed = req.is_connection_closed;"


def inspect(*, readme=README, context=CONTEXT, http=HTTP):
    return inspect_pinned_source_text(
        readme, context, http,
        source_head=SOURCE_HEAD_S57, binary_digest=BINARY_SHA256_S57,
    )


def test_pinned_source_cannot_claim_independently_acknowledged_stop():
    facts = inspect()
    assert facts.internal_cancel_task_exists
    assert facts.control_reasoning_end_only
    assert facts.slot_erase_deferred_when_busy
    assert not facts.source_reader_sees_disconnect_predicate
    assert facts.documented_request_stop_ack is False
    assert facts.request_stop_admissible is False
    receipt = facts.public_report()
    assert receipt["status"] == "BLOCKED"
    assert receipt["backend_stop_command_sent"] is False
    assert receipt["gpu_preemption_claimed"] is False
    assert receipt["runtime_model_call_attempted"] is False


def test_client_disconnect_capture_is_not_a_stop_ack():
    assert inspect().request_stop_admissible is False
    with pytest.raises(StopAuditRejected):
        inspect(http="")  # no pinned HTTP source predicate


def test_reasoning_end_cannot_qualify_as_request_stop():
    with pytest.raises(StopAuditRejected):
        inspect(context=CONTEXT.replace(
            'action != "reasoning_end"', 'action != "stop"',
        ))


def test_busy_slot_erase_must_be_deferred_not_cancelled():
    with pytest.raises(StopAuditRejected):
        inspect(context=CONTEXT.replace(
            "queue_tasks.defer(std::move(task));", "slot.release();",
        ))


def test_internal_cancel_task_is_not_public_request_ack():
    with pytest.raises(StopAuditRejected):
        inspect(context=CONTEXT.replace("slot.release();", "slot.flag_idle();"))


def test_unknown_source_head_or_binary_identity_cannot_enter():
    with pytest.raises(StopAuditRejected):
        inspect_pinned_source_text(
            README, CONTEXT, HTTP,
            source_head="1" * 40, binary_digest=BINARY_SHA256_S57,
        )
    with pytest.raises(StopAuditRejected):
        inspect_pinned_source_text(
            README, CONTEXT, HTTP,
            source_head=SOURCE_HEAD_S57, binary_digest="f" * 64,
        )


def test_absent_binary_is_not_replaced_by_fixture_response(tmp_path):
    with pytest.raises(StopAuditRejected):
        audit(
            tmp_path / "nonexistent-llama-server",
            tmp_path / "repo",
            BINARY_SHA256_S57,
        )


def test_no_stop_command_even_if_cli_is_invoked(tmp_path, monkeypatch, capsys):
    report = tmp_path / "audit.json"
    monkeypatch.setattr("sys.argv", [
        "s59a_backend_stop_audit",
        "--llama-server", str(tmp_path / "fake-nonexistent"),
        "--expected-binary-sha256", BINARY_SHA256_S57,
        "--source-checkout", str(tmp_path),
        "--report", str(report),
    ])
    code = main()
    receipt = json.loads(report.read_text())
    assert code == 2
    assert receipt["status"] == "BLOCKED"
    assert receipt["classification"] == "PINNED_STOP_SOURCE_AUDIT_UNQUALIFIED"
    assert receipt["backend_stop_command_sent"] is False
    assert receipt["gpu_preemption_claimed"] is False
    assert "S59_AUDIT=" in capsys.readouterr().out
