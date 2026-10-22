"""W4: same owner observes/stops in memory, never starts Minecraft."""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer.self_world_observation_only_entry import (
    ObservationOnlyEntryInventory,
)
from adapters.mineflayer.self_world_observation_only_owner_offline import (
    rehearse_observation_only_owner_offline,
)
from adapters.mineflayer.self_world_observation_only_dev import ObservationOnlyDevBlocked
from adapters.mineflayer.self_world_observation_only_lifetime import (
    ObservationOnlyLifetimeBlocked,
)
from test_self_world_stage_w4_prehost import _offline_lines

MARKER = b"[21:00:00] [Server thread/INFO]: The time is 1234\n"


def _args(tmp_path):
    before, after, raw = _offline_lines()
    return {
        "inventory": ObservationOnlyEntryInventory(
            schema="W4_OBSERVATION_ONLY_PREWORLD_INVENTORY_V1",
            exact_head="a" * 40, jar_sha256="b" * 64,
            bridge_sha256="c" * 64,
        ),
        "raw_frames": tuple(raw),
        "before_request": before.request_id,
        "after_request": after.request_id,
        "marker_line": MARKER,
        "evidence_root": tmp_path,
    }


def test_synthetic_owner_closes_full_raw_lifetime_with_no_action(tmp_path, monkeypatch):
    async def no_process(*args, **kwargs):
        raise AssertionError("no Java/Node process or World can launch")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", no_process)
    result = asyncio.run(rehearse_observation_only_owner_offline(**_args(tmp_path)))
    assert result["schema"] == "W4_OBSERVATION_ONLY_OWNER_REHEARSAL_OFFLINE_V1"
    assert result["scope"] == "FAKE_PROCESSES_LOCAL_CONTENT_ONLY"
    assert result["node_commands"] == ["observe", "observe", "shutdown"]
    assert result["java_commands"] == ["stop"]
    assert result["node_frame_reads_including_eof"] == 9
    assert result["node_raw_audit"]["status"] == "COMPLETE_NODE_STDOUT"
    assert result["node_raw_audit"]["shutdown_ack_count"] == 1
    assert result["local_lifetime"]["classification"] == "LOCAL_PRODUCER_LIFETIME_ONLY"
    assert result["local_lifetime"]["before_seq"] == 3
    assert result["local_lifetime"]["after_seq"] == 5
    assert all(result[k] is False for k in (
        "physical_run_permitted", "external_grant_verified",
        "external_owner_attested", "actual_pid_port_disposal_attested",
        "science_qualified",
    ))
    assert result["action_count"] == result["outcome_count"] == 0
    assert result["s10_update_count"] == 0
    assert (tmp_path / "w3-node-stdout.raw.jsonl").is_file()
    assert (tmp_path / "w3-node-stdout-receipt.json").is_file()
    assert (tmp_path / "sole-java-collector.raw").is_file()


@pytest.mark.parametrize("fault", (
    "bad_marker", "foreign_probe", "wrong_request", "duplicate_sequence",
    "bad_inventory", "fake_grant", "missing_frame", "occupied_root",
))
def test_offline_owner_fail_closed_and_never_world(tmp_path, fault):
    kwargs = _args(tmp_path)
    if fault == "bad_marker":
        kwargs["marker_line"] = b"World truth! time=1234\n"
    elif fault == "foreign_probe":
        frames = list(kwargs["raw_frames"])
        obj = json.loads(frames[5])
        obj["session_id"] = "foreign"
        frames[5] = (json.dumps(obj) + "\n").encode()
        kwargs["raw_frames"] = tuple(frames)
    elif fault == "wrong_request":
        kwargs["after_request"] = "different-correlated-id"
    elif fault == "duplicate_sequence":
        frames = list(kwargs["raw_frames"])
        obj = json.loads(frames[4])
        obj["seq"] = 3
        frames[4] = (json.dumps(obj) + "\n").encode()
        kwargs["raw_frames"] = tuple(frames)
    elif fault == "bad_inventory":
        kwargs["inventory"] = {"disposition": "PREWORLD_BLOCKED"}
    elif fault == "fake_grant":
        kwargs["grant"] = "self-issued"
    elif fault == "missing_frame":
        kwargs["raw_frames"] = kwargs["raw_frames"][:-1]
    elif fault == "occupied_root":
        (tmp_path / "existing").touch()
    with pytest.raises((
        TypeError, ObservationOnlyDevBlocked, ObservationOnlyLifetimeBlocked,
        RuntimeError, ValueError,
    )):
        asyncio.run(rehearse_observation_only_owner_offline(**kwargs))


def test_offline_owner_has_no_runtime_or_authority_ports(tmp_path):
    with pytest.raises(TypeError):
        asyncio.run(rehearse_observation_only_owner_offline(
            **_args(tmp_path), confirm=True,
        ))
