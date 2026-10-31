"""Isolated S50 packet-observer overlay retains the exact L23 owner files.

This test is *offline* only: it neither uses nor qualifies Minecraft runtime.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ORIGINAL_L23_OWNER_BLOBS = {
    "adapters/mineflayer/s49_normal_session_real_ci.py":
        "938c3b9361075191a99feb56a8e3467eaf15e872",
    "adapters/mineflayer/s34_native_world_cognition_ci.py":
        "e21f0daedd8a326b35adcdc5b340fb546199f291",
    "adapters/mineflayer/process_session.py":
        "9d19fb8bd902cb53806106c97f40b48951959601",
    "adapters/mineflayer/normal_action.py":
        "28f231bdacb933679dad7a9720b10fffa179d6fb",
}


def _git_blob(path: Path) -> str:
    original = path.read_bytes()
    return hashlib.sha1(
        f"blob {len(original)}\0".encode() + original
    ).hexdigest()


def test_s49_l23_original_authority_sources_still_exact_frozen_bytes():
    for path, sha in ORIGINAL_L23_OWNER_BLOBS.items():
        assert _git_blob(BASE / path) == sha, path


def test_bridge_has_only_one_original_control_and_action_writer():
    original = (BASE / "adapters/mineflayer/bridge.mjs").read_text()
    assert original.count("bot.setControlState(command.control, command.state)") == 1
    assert original.count("bot.clearControlStates()") == 2
    assert original.count("emitEffectResult(command, 'applied')") >= 2
    assert "await bot.look(command.yaw, command.pitch)" in original
    assert "The RSEE product may explicitly select" in original
    assert "RELAYSELF_S50_PACKET_WITNESS_DEV" in original
    assert "s50PacketWitness?.effect('set_control', command.state)" in original
    assert "s50PacketWitness?.effect('clear_controls')" in original
    assert "s50PacketSidecar?.close()" in original
    assert "bot._client.write(" not in original
    assert "bot._client.write =" not in original


def test_s50_witness_remains_opt_in_diagnostic_without_packet_injection():
    source = (
        BASE / "adapters/mineflayer/s50_client_packet_witness_dev.mjs"
    ).read_text()
    assert "PACKETS = new Set([" in source
    assert "'player_input'" in source
    assert "client.write = function (name, ...args)" in source
    assert "Reflect.apply(nativeWrite, this, [name, ...args])" in source
    assert "new_packet_writes: 0" in source
    assert "server_world_tick: 'NOT_OBSERVED'" in source
    assert "client_server_clock_aligned: false" in source
    assert "paper_received: false" in source
    assert "effective_s15_clear_tick: 'NOT_ATTESTED'" in source
