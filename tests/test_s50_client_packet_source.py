"""S50 packet path DEV: never promote a write-return to Paper acceptance."""
import json

import pytest

from adapters.mineflayer.m02_paper_dev.s50_client_packet_source import (
    S50PacketSourceRejected,
    inspect_s50_client_packets,
)

SID = "3e63cfbc-1011-4dd1-b1ca-f3a6f596f5bf"
MARKER = "s49-native-move-19-" + SID
WORLD = "6993349a-b2c3-433f-b2c8-7f32b5fe64c8"


def source(*, input_write=False, lost=False):
    rows = []
    names = ["position", "flying"] + (["player_input"] if input_write else [])
    for index, name in enumerate(names, 1):
        rows.append({
            "revision": 1, "session_id": SID,
            "index": index, "node_ns": str(index * 1000),
            "clock_scope": "NODE_ONLY", "server_world_tick": "NOT_OBSERVED",
            "source": "CLIENT_WRITE_RETURNED_NOT_NETWORK_DELIVERY",
            "kind": "PACKET_WRITE_RETURNED", "packet_index": index,
            "packet_name": name, "paper_received": False,
            "network_delivered": False,
        })
    rows.append({
        "revision": 1, "kind": "TRACE_END", "complete": not lost,
        "lost": lost, "recorded_rows": len(names),
        "input_write_authority": False, "server_packet_received": False,
        "effective_s15_clear_tick": "NOT_ATTESTED",
    })
    return ("\n".join(json.dumps(x) for x in rows) + "\n").encode()


def paper(*, callbacks=0):
    lines = [
        (f"[INFO] S50_DEV_INPUT_TICK marker_id={MARKER} "
         f"world={WORLD} subject_uuid=subject tick={252 + i} index={i + 1}")
        for i in range(8)
    ]
    lines.extend(
        f"[INFO] S50_DEV_INPUT_EVENT marker_id={MARKER} "
        f"world={WORLD} subject_uuid=subject tick=252 index={i + 1}"
        for i in range(callbacks)
    )
    return ("\n".join(lines) + "\n").encode()


def review(native, server):
    return inspect_s50_client_packets(
        native, server, session_id=SID, marker_id=MARKER, world=WORLD,
    )["readback"]


def test_no_input_update_write_even_though_position_packets_returned():
    result = review(source(), paper())
    assert result["diagnostic"] == "NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH"
    assert result["client_motion_write_returns"] == 2
    assert result["client_player_input_write_returns"] == 0
    assert result["paper_player_input_callbacks"] == 0
    assert not result["native_write_is_network_delivery"]
    assert not result["paper_packet_identity_proven"]
    assert result["effective_s15_clear_tick"] == "NOT_ATTESTED"
    assert not result["full_tick_input_coverage"]
    assert result["p1_wait_ticks_admitted"] == result["l10_pairs_admitted"] == 0


@pytest.mark.parametrize(("input_write", "callbacks", "label"), [
    (True, 0, "PLAYER_INPUT_WRITE_SEEN_PAPER_CALLBACK_ABSENT"),
    (True, 1, "BOTH_WRITE_AND_CALLBACK_SEEN_IDENTITY_UNPROVEN"),
])
def test_input_write_does_not_prove_server_acceptance(input_write, callbacks, label):
    assert review(source(input_write=input_write), paper(callbacks=callbacks))[
        "diagnostic"
    ] == label


@pytest.mark.parametrize("fault", [
    "incomplete", "foreign_session", "reordered", "invalid_packet",
    "false_wire", "foreign_paper", "no_eight_ticks", "footer_missing",
])
def test_bad_sources_fail_closed(fault):
    raw, server = source(), paper()
    if fault == "incomplete":
        raw = source(lost=True)
    elif fault == "foreign_session":
        raw = raw.replace(SID.encode(), b"other", 1)
    elif fault == "reordered":
        lines = raw.splitlines()
        lines[0], lines[1] = lines[1], lines[0]
        raw = b"\n".join(lines) + b"\n"
    elif fault == "invalid_packet":
        raw = raw.replace(b'"packet_name": "position"',
                          b'"packet_name": "custom_payload"', 1)
    elif fault == "false_wire":
        raw = raw.replace(b'"network_delivered": false',
                          b'"network_delivered": true', 1)
    elif fault == "foreign_paper":
        server = server.replace(WORLD.encode(), b"other-world", 1)
    elif fault == "no_eight_ticks":
        server = b"\n".join(server.splitlines()[:-1]) + b"\n"
    elif fault == "footer_missing":
        raw = b"\n".join(raw.splitlines()[:-1]) + b"\n"
    with pytest.raises(S50PacketSourceRejected):
        review(raw, server)
