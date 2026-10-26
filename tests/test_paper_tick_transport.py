"""#150 wire delivery matches Paper logger, never proves L0 or Action authority."""
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.paper_tick_probe import PaperTickProbeRejected
from adapters.mineflayer.m02_paper_dev.paper_tick_transport import (
    join_paper_l0_shadow,
    join_paper_tick_transport,
)
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerPaperTickSample,
    MineflayerPaperL0Shadow,
    MineflayerStreamDecoder,
    parse_mineflayer_line,
)

WORLD = "11111111-1111-4111-8111-111111111111"
PLAYER = "22222222-2222-4222-8222-222222222222"
SESSION = "session-source-1"


def tick_data(i):
    return {
        "index": i, "server_tick": str(100 + i),
        "world_full_time": str(400 + i),
        "wall_nanos": str(10000 + 100 * i),
        "world": WORLD, "player": PLAYER,
        "source": "PAPER_SCHEDULER_CALLBACK_ONLY",
        "l0_checked": False, "action_bound": False,
    }


def log(n=4):
    return "\n".join(
        "PAPER_DEV_TIME_SAMPLE " +
        " ".join(f"{k}={str(v).lower() if type(v) is bool else v}"
                 for k, v in tick_data(i).items())
        for i in range(1, n + 1)
    )


def packet(i, **changes):
    data = tick_data(i)
    data.update(changes)
    return {
        "type": "paper_tick_sample",
        "session_id": SESSION,
        "seq": i,
        "source": data["source"],
        "observation_precision": "PAPER_PLUGIN_MESSAGE_RECEIVED_LATER",
        "index": data["index"],
        "server_tick": data["server_tick"],
        "world_full_time": data["world_full_time"],
        "wall_nanos": data["wall_nanos"],
        "world": data["world"], "player": data["player"],
        "bridge_recv_monotonic_ns": str(100000 + 1000 * i),
        "l0_checked": data["l0_checked"], "action_bound": data["action_bound"],
        "paper_native_source_authenticated": False,
    }


def message(i, **changes):
    return parse_mineflayer_line(json.dumps(packet(i, **changes)))


def matched(messages=None, paper=None):
    return join_paper_tick_transport(
        paper if paper is not None else log(),
        tuple(message(i) for i in range(1, 5)) if messages is None else messages,
        expected_world=WORLD,
        expected_player=PLAYER,
        expected_session=SESSION,
    )


def test_valid_single_receiver_transport_is_not_a_real_l0_check():
    receipt = matched()
    assert receipt.server_ticks == (101, 102, 103, 104)
    assert receipt.session_id == SESSION
    assert receipt.paper_wire_delivery_matched
    assert receipt.l0_checked_ticks == ()
    assert not receipt.action_bound
    assert not receipt.native_source_authenticated
    assert not receipt.tps_change_admitted


@pytest.mark.parametrize("field,bad", [
    ("l0_checked", True), ("action_bound", True),
    ("paper_native_source_authenticated", True),
    ("source", "fake"), ("server_tick", "-1"),
    ("world_full_time", 400), ("wall_nanos", "x"),
    ("bridge_recv_monotonic_ns", "0"), ("world", "bad"), ("index", True),
])
def test_invalid_wire_authority_and_types_reject_before_join(field, bad):
    with pytest.raises(MineflayerAdapterProtocolError):
        message(1, **{field: bad})


@pytest.mark.parametrize("changed", [
    lambda ms: (replace(ms[0], session_id="other"), *ms[1:]),
    lambda ms: (ms[0], replace(ms[1], seq=ms[0].seq), *ms[2:]),
    lambda ms: (ms[0], replace(ms[1], server_tick="109"), *ms[2:]),
    lambda ms: (ms[0], replace(ms[1], world_full_time="409"), *ms[2:]),
    lambda ms: (ms[0], replace(ms[1], wall_nanos="99999"), *ms[2:]),
    lambda ms: (ms[0], replace(ms[1], bridge_recv_monotonic_ns="1"), *ms[2:]),
    lambda ms: (*ms[:-1],),
])
def test_missing_changed_reordered_wire_event_fails_closed(changed):
    messages = tuple(message(i) for i in range(1, 5))
    with pytest.raises(PaperTickProbeRejected):
        matched(tuple(changed(messages)))


def test_stream_decoder_retains_only_one_native_receiver_session():
    d = MineflayerStreamDecoder()
    started = {
        "type": "adapter_started", "session_id": SESSION, "seq": 0,
        "mineflayer_version": "4.39.0",
        "config": {"host": "127.0.0.1", "port": 25565,
                   "username": "RelaySelf", "version": "1.21.8"},
    }
    d.decode(json.dumps(started))
    first = d.decode(json.dumps(packet(1)))
    assert isinstance(first, MineflayerPaperTickSample)
    with pytest.raises(MineflayerAdapterProtocolError):
        d.decode(json.dumps({**packet(2), "session_id": "foreign"}))
    assert d.next_seq == 2
    with pytest.raises(MineflayerAdapterProtocolError):
        d.decode(json.dumps({**packet(3), "seq": 3}))
    assert isinstance(d.decode(json.dumps(packet(2))), MineflayerPaperTickSample)


def test_extra_protocol_key_or_wrong_expected_scope_rejected():
    with pytest.raises(MineflayerAdapterProtocolError):
        parse_mineflayer_line(json.dumps({**packet(1), "permission": "ACTION"}))
    with pytest.raises(PaperTickProbeRejected):
        join_paper_tick_transport(
            log(), tuple(message(i) for i in range(1, 5)),
            expected_world=WORLD, expected_player=PLAYER,
            expected_session="wrong",
        )


def shadow(i, *, assessment="NO_KNOWN_URGENT_SIGNAL", **changes):
    body = {
        "type": "paper_l0_shadow", "session_id": SESSION, "seq": 2 * i,
        "source": "MINEFLAYER_CACHE_SHADOW_L0_DEV",
        "observation_precision": "CLIENT_CACHE_POST_PAPER_MESSAGE_NOT_EPOCH_FRESH",
        "paper_sample_index": i, "paper_server_tick": str(100 + i),
        "paper_world": WORLD, "paper_player": PLAYER,
        "evaluation_duration_ns": "1234", "assessment": assessment,
        "cached_body_observed": assessment != "UNKNOWN",
        "l0_shadow_evaluated": True,
        "l0_fresh_world_tick_attested": False,
        "authorized_action_issued": False, "tps_admission_granted": False,
    }
    body.update(changes)
    return parse_mineflayer_line(json.dumps(body))


def shadow_match(*, delivered=None, shadows=None):
    delivered = (tuple(replace(message(i), seq=2 * i - 1) for i in range(1, 5))
                 if delivered is None else delivered)
    shadows = (tuple(shadow(i) for i in range(1, 5))
               if shadows is None else shadows)
    return join_paper_l0_shadow(
        log(), delivered, shadows,
        expected_world=WORLD, expected_player=PLAYER,
        expected_session=SESSION,
    )


def test_one_cache_l0_evaluation_per_paper_message_still_no_tps_permission():
    receipt = shadow_match()
    assert receipt.paired_server_ticks == (101, 102, 103, 104)
    assert receipt.shadow_cache_evaluated_ticks == (101, 102, 103, 104)
    assert receipt.unknown_or_uncovered_ticks == ()
    assert receipt.l0_fresh_world_tick_attested is False
    assert receipt.tps_change_admitted is False
    assert isinstance(shadow(1), MineflayerPaperL0Shadow)


def test_unknown_cached_body_is_not_counted_as_fresh_world_l0():
    shadows = tuple(shadow(i, assessment="UNKNOWN") if i == 3 else shadow(i)
                    for i in range(1, 5))
    r = shadow_match(shadows=shadows)
    assert r.unknown_or_uncovered_ticks == (103,)
    assert not r.l0_fresh_world_tick_attested


@pytest.mark.parametrize("bad", [
    {"l0_shadow_evaluated": False},
    {"l0_fresh_world_tick_attested": True},
    {"authorized_action_issued": True},
    {"tps_admission_granted": True},
    {"paper_sample_index": True},
    {"assessment": "SAFETY_GRANTED"},
    {"assessment": ["UNKNOWN"]},
    {"evaluation_duration_ns": "-5"},
    {"observation_precision": "FRESH_WORLD"},
    {"cached_body_observed": False},
])
def test_shadow_forged_permission_or_invalid_state_is_rejected(bad):
    with pytest.raises(MineflayerAdapterProtocolError):
        shadow(1, **bad)


@pytest.mark.parametrize("change", [
    lambda ms: (replace(ms[0], session_id="other"), *ms[1:]),
    lambda ms: (*ms[:1], replace(ms[1], seq=9), *ms[2:]),
    lambda ms: (*ms[:1], replace(ms[1], paper_server_tick="999"), *ms[2:]),
    lambda ms: (*ms[:1], replace(ms[1], paper_world=PLAYER), *ms[2:]),
    lambda ms: (*ms[:1], replace(ms[1], paper_player=WORLD), *ms[2:]),
    lambda ms: (ms[0], ms[2], ms[1], ms[3]),
    lambda ms: ms[:-1],
])
def test_shadow_missing_reordered_unbound_receipts_reject(change):
    shards = tuple(shadow(i) for i in range(1, 5))
    with pytest.raises(PaperTickProbeRejected):
        shadow_match(shadows=tuple(change(shards)))
