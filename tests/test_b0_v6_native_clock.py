"""Typed receipt for candidate raw V6 native packet (not an Action event)."""
import json

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerNativeClockPacket,
    MineflayerStreamDecoder,
    parse_mineflayer_line,
)


def row(**kwargs):
    x = {
        "type": "native_clock_packet",
        "session_id": "s-v6", "seq": 1,
        "source": "minecraft_1_21_8_clientbound_update_time",
        "observation_precision": "SERVER_UPDATE_TIME_PACKET_SAMPLE_ONLY",
        "world_age_ticks": "151", "world_day_time_raw_ticks": "-12",
        "tick_day_time": False, "host_monotonic_ns": "1234567",
        "command_effect_tick_attested": False,
    }
    x.update(kwargs)
    return json.dumps(x)


def test_packet_is_typed_but_never_authenticates_command_effect():
    msg = parse_mineflayer_line(row())
    assert isinstance(msg, MineflayerNativeClockPacket)
    assert msg.world_age_ticks == "151"
    assert msg.world_day_time_raw_ticks == "-12"
    assert msg.command_effect_tick_attested is False


@pytest.mark.parametrize("change", [
    {"world_age_ticks": 151}, {"world_age_ticks": "-1"},
    {"world_age_ticks": "0151"}, {"world_age_ticks": str(2**63)},
    {"world_day_time_raw_ticks": None}, {"tick_day_time": 1},
    {"host_monotonic_ns": "-1"}, {"host_monotonic_ns": "0"},
    {"command_effect_tick_attested": True}, {"source": "synthetic"},
    {"observation_precision": "EXACT_COMMAND_TICK"}, {"unexpected": 1},
])
def test_unqualified_source_or_fake_attestation_rejected(change):
    with pytest.raises(MineflayerAdapterProtocolError):
        parse_mineflayer_line(row(**change))


def test_same_session_contiguous_original_seq_required():
    d = MineflayerStreamDecoder()
    start = {
        "type": "adapter_started", "session_id": "s-v6", "seq": 0,
        "mineflayer_version": "4.39.0",
        "config": {
            "host": "127.0.0.1", "port": 25565,
            "username": "RelaySelf", "version": "1.21.8",
        },
    }
    d.decode(json.dumps(start))
    d.decode(row())
    with pytest.raises(MineflayerAdapterProtocolError):
        d.decode(row(seq=1))
    with pytest.raises(MineflayerAdapterProtocolError):
        d.decode(row(seq=2, session_id="foreign"))
