"""Observation-only W4 DEV interface: no Java/Node/World launched."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerStreamDecoder,
    encode_observe,
    encode_shutdown,
)
from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyDevBlocked,
    ObservationOnlyDevSession,
    review_observation_only_dev_offline,
)
from test_mineflayer_process_session import FakeProcess
from test_self_world_stage_w4_prehost import _offline_lines


def _valid_review():
    _pre, _post, raws = _offline_lines()
    decoder = MineflayerStreamDecoder()
    decoded = [decoder.decode(raw.decode("utf-8")) for raw in raws]
    marker = b"[21:00:00] [Server thread/INFO]: The time is 1234\n"
    return dict(
        started=decoded[0], spawn=decoded[1],
        before=decoded[3], after=decoded[5],
        before_request=decoded[3].request_id,
        after_request=decoded[5].request_id,
        raw_marker_line=marker, marker_sha256=hashlib.sha256(marker).hexdigest(),
        marker_after_before=True, after_marker=True,
    )


def test_read_only_review_accepts_source_lineage_but_never_promotes_dev():
    result = review_observation_only_dev_offline(**_valid_review())
    assert result.spawn_seq == 1
    assert result.before_seq == 3 and result.after_seq == 5
    assert result.marker_local_game_time == 1234
    assert result.scope == "SYNTHETIC_OR_LOCAL_CONSOLE_NOT_EXTERNAL_CUSTODY"
    assert result.action_count == result.outcome_count == result.s10_update_count == 0
    assert not result.physical_run_permitted
    assert not result.qualification_approved and not result.science_qualified


@pytest.mark.parametrize("attack", (
    "foreign_session", "replay_seq", "wrong_spawn_kind",
    "wrong_before_request", "same_requests", "wrong_after_kind",
    "same_source", "wrong_marker_hash", "forged_marker", "partial_marker",
    "before_marker_unverified", "after_marker_unverified",
))
def test_read_only_review_rejects_unbound_source_or_marker(attack):
    params = _valid_review()
    if attack == "foreign_session":
        params["after"] = replace(params["after"], session_id="foreign")
    elif attack == "replay_seq":
        params["after"] = replace(params["after"], seq=params["before"].seq)
    elif attack == "wrong_spawn_kind":
        params["spawn"] = replace(params["spawn"], kind="probe")
    elif attack == "wrong_before_request":
        params["before_request"] = "another-request"
    elif attack == "same_requests":
        params["after_request"] = params["before_request"]
    elif attack == "wrong_after_kind":
        params["after"] = replace(params["after"], kind="entities", request_id=None)
    elif attack == "same_source":
        params["after"] = replace(params["after"], provenance=params["before"].provenance)
    elif attack == "wrong_marker_hash":
        params["marker_sha256"] = "0" * 64
    elif attack == "forged_marker":
        params["raw_marker_line"] = b"[21:00:00] [Server thread/INFO]: fake 1234\n"
        params["marker_sha256"] = hashlib.sha256(params["raw_marker_line"]).hexdigest()
    elif attack == "partial_marker":
        params["raw_marker_line"] = params["raw_marker_line"].rstrip(b"\n")
        params["marker_sha256"] = hashlib.sha256(params["raw_marker_line"]).hexdigest()
    elif attack == "before_marker_unverified":
        params["marker_after_before"] = False
    elif attack == "after_marker_unverified":
        params["after_marker"] = False
    with pytest.raises(ObservationOnlyDevBlocked):
        review_observation_only_dev_offline(**params)


def test_observation_only_process_session_blocks_inherited_action_commands():
    async def run():
        process = FakeProcess([])
        session = ObservationOnlyDevSession(process)
        for attempt in (
            lambda: session.send_set_control("action-1", control="back", state=True),
            lambda: session.send_clear_controls("action-1"),
            lambda: session.send_look("action-1", yaw=0, pitch=0),
            lambda: session.send_attack_entity("action-1", entity_id=1),
            lambda: session.send_consume_held("action-1"),
            lambda: session.send_equip_item("action-1", item_name="bread"),
            lambda: session._send('{"type":"effect","effect":"clear_controls"}\n'),
            lambda: session._send('{"type":"observe"}\n'),
            lambda: session._send('{"type":"observe","request_id":"r1","extra":true}\n'),
        ):
            with pytest.raises(ObservationOnlyDevBlocked):
                await attempt()
        assert process.stdin.writes == []
        await session.send_observe("probe-one")
        assert process.stdin.writes == [encode_observe("probe-one").encode()]
        rc = await session.shutdown()
        assert rc == 0 and process.stdin.writes[-1] == encode_shutdown().encode()
        assert len(process.stdin.writes) == 2
    asyncio.run(run())


def test_observation_only_dev_does_not_spawn_any_process_in_offline_review(monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("observation-only review must never start Java/Node")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    result = review_observation_only_dev_offline(**_valid_review())
    assert not result.physical_run_permitted
