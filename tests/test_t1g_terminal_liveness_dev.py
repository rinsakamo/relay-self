"""Pure DEV terminal receiver audit; independent of Minecraft process."""
import pytest

from adapters.mineflayer.t1g_terminal_liveness_dev import (
    TerminalLivenessRejected,
    audit_bridge_terminal,
)

SID = "session-A"


def e(i, typ, session=SID):
    return {"type": typ, "session_id": session, "seq": i}


def test_normal_shutdown_ack_and_connection_end_not_high_level_stop():
    v = audit_bridge_terminal([e(0, "adapter_started"), e(1,"effect_result"),
                               e(2,"shutdown_ack"), e(3,"connection_end")],session_id=SID)
    assert v.bridge_transport_closed
    assert v.bridge_shutdown_ack_seen and v.connection_end_seen
    assert not v.high_level_stop_ack_attested
    assert not v.paper_world_stopped_attested
    assert not v.native_source_authenticated


def test_unexpected_disconnect_never_becomes_clean_stop():
    v = audit_bridge_terminal([e(0,"adapter_started"),e(5,"connection_end")],session_id=SID)
    assert v.classification == "UNEXPECTED_DISCONNECT_NO_SHUTDOWN_ACK"
    assert not v.bridge_transport_closed


def test_missing_end_or_missing_shutdown_ack_not_successful():
    for seq in ([e(0,"adapter_started"),e(1,"shutdown_ack")],
                [e(0,"adapter_started")]):
        assert not audit_bridge_terminal(seq,session_id=SID).bridge_transport_closed


@pytest.mark.parametrize("events",[
    [e(0,"adapter_started"),e(1,"shutdown_ack"),e(2,"shutdown_ack"),e(3,"connection_end")],
    [e(0,"adapter_started"),e(1,"connection_end"),e(2,"shutdown_ack")],
    [e(0,"adapter_started"),e(2,"shutdown_ack"),e(3,"effect_result"),e(4,"connection_end")],
    [e(0,"adapter_started"),e(3,"shutdown_ack"),e(3,"connection_end")],
    [e(0,"adapter_started"),e(2,"shutdown_ack",session="foreign"),e(3,"connection_end")],
])
def test_dup_order_foreign_and_post_shutdown_effect_reject(events):
    with pytest.raises(TerminalLivenessRejected):
        audit_bridge_terminal(events,session_id=SID)


def test_unbounded_or_bad_scope_rejects():
    for events, session in (([],SID),([e(0,"adapter_started")],""),
                            ([e(True,"adapter_started")],SID),
                            ([{"type":"shutdown_ack","session_id":SID,"seq":0.0}],SID)):
        with pytest.raises(TerminalLivenessRejected):
            audit_bridge_terminal(events,session_id=session)
