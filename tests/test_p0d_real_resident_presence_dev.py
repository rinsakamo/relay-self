"""#860 Stage22: real Paper native-presence runner preflight and source fakes.

No Paper, Node, Java, Minecraft EULA or real World is started by these tests.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from experiments.p0d_real_resident_presence_dev import (
    RealResidentPresenceRefusal,
    _bounded_b_probe,
    run_real_resident_presence,
)
from test_p0d_resident_physical_issuer_dev import FakeNativeResident


def test_real_world_requires_separate_explicit_grant_before_any_io(tmp_path: Path):
    parent = tmp_path / "not-even-created"

    with pytest.raises(RealResidentPresenceRefusal, match="HOLD_REAL_WORLD_GRANT"):
        asyncio.run(run_real_resident_presence(
            paper_jar=tmp_path / "missing-paper",
            paper_sha256="0" * 64,
            plugin_jar=tmp_path / "missing-plugin",
            plugin_sha256="1" * 64,
            scratch_parent=parent, accepted_eula=False,
            real_world_dev_grant=False,
        ))
    assert not parent.exists()


@pytest.mark.parametrize("value", [1.0, 13.0, True])
def test_real_world_rejects_invalid_heartbeat_without_launch(tmp_path: Path, value):
    parent = tmp_path / "missing-parent"

    with pytest.raises(RealResidentPresenceRefusal, match="heartbeat"):
        asyncio.run(run_real_resident_presence(
            paper_jar=tmp_path / "missing-paper",
            paper_sha256="0" * 64,
            plugin_jar=tmp_path / "missing-plugin",
            plugin_sha256="1" * 64,
            scratch_parent=parent,
            accepted_eula=True, real_world_dev_grant=True,
            b_heartbeat_s=value,
        ))
    assert not parent.exists()


def test_surviving_native_b_correlated_probe_is_read_only():
    native = FakeNativeResident(
        MineflayerLaunchConfig(
            host="127.0.0.1", port=25565,
            username="RelayB", version="1.21.8",
        ),
        "native-B-live",
    )

    async def scenario():
        got = await _bounded_b_probe(native, timeout_s=1.0)
        assert got.kind == "probe"
        assert got.request_id is not None
        assert got.request_id.startswith("p0d-b-online-")
        assert got.session_id == "native-B-live"
        assert got.snapshot.health > 0
        assert got.provenance.reference == "native-B-live:" + str(got.seq)
        assert native.effect_gate is None
        assert native.process_returncode is None

    asyncio.run(scenario())


def test_surviving_b_native_probe_wrong_request_refuses():
    native = FakeNativeResident(
        MineflayerLaunchConfig(
            host="127.0.0.1", port=25565,
            username="RelayB", version="1.21.8",
        ),
        "native-B-live",
        bad_probe=True,
    )

    async def scenario():
        with pytest.raises(RealResidentPresenceRefusal, match="mismatched"):
            await _bounded_b_probe(native, timeout_s=1.0)

    asyncio.run(scenario())
