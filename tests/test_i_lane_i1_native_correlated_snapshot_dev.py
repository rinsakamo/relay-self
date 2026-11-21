"""I1 original Native correlated-probe snapshot vs passive E SENSE (CPU/offline).

The original Mineflayer process has one decoder/owner. A matched read-only
observe reply must remain the source of the I1 CPU record even when the
original passive observer receives a newer move/entities message with no
request ID before B Present and CPU evaluate it. No World/GPU/Action here.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import replace

import pytest

from adapters.mineflayer.sense_projection import sense_from_native
from relay_self.common_io import ScopeRef
from relay_self.i_lane_i1_normal_runtime_dev import (
    I1NormalRuntimeHold,
    read_i1_original_cpu_epoch,
    sample_i1_original_cpu_epochs,
)
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_i_lane_e2c_original_present_dev import _inject


def _setup(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, _, world, _, _ = case
    for sid in ("A", "B"):
        _inject(bridge, world, sid)
    bridge._i1_correlated_sense = {}
    bridge._i1_correlated_received_at = {}
    return case


def _matched_with_passive_after(bridge, world, sid, round_number: int):
    prev = bridge._sense[sid]
    req = f"i1-original-sense-{round_number:031x}{int(sid == 'B'):x}"
    seq = 2 * round_number + 2
    matched = sense_from_native(
        replace(
            prev.observation, seq=seq, kind="probe", request_id=req,
            snapshot=replace(prev.observation.snapshot, food=float(8 + round_number)),
        ),
        scope=ScopeRef(sid, world.paper_session_id),
        expected_native_session=prev.observation.session_id,
        previous_seq=prev.observation.seq,
        expected_request_id=req,
    )
    bridge._i1_correlated_sense[sid] = matched
    bridge._i1_correlated_received_at[sid] = time.monotonic()
    # A passive unsolicited update with LATER seq is concurrently received
    # by the SAME original adapter; it has request_id=None.
    passive = sense_from_native(
        replace(matched.observation, seq=seq + 1, kind="move", request_id=None),
        scope=matched.scope, expected_native_session=matched.observation.session_id,
        previous_seq=matched.observation.seq,
    )
    bridge._sense[sid] = passive
    bridge._sense_received_at[sid] = time.monotonic()
    return matched, passive


def test_i1_cpu_two_matched_probes_each_survive_interleaved_passive_updates(
    tmp_path, monkeypatch,
):
    case = _setup(tmp_path, monkeypatch)
    _, bridge, boot, world, links, _ = case
    old_files = _files(bridge)
    owners_before = {
        sid: (bridge.owners[sid].retained, bridge.owners[sid].intent,
              bridge.owners[sid].pattern_registry)
        for sid in ("A", "B")
    }
    rounds = 0

    async def refresh_native():
        nonlocal rounds
        rounds += 1
        matched = {}
        for sid in ("A", "B"):
            observed, passive = _matched_with_passive_after(
                bridge, world, sid, rounds,
            )
            assert passive.observation.seq > observed.observation.seq
            assert passive.observation.request_id is None
            assert bridge.current_sense(sid) is passive
            assert bridge.current_i1_correlated_sense(sid) is observed
            matched[sid] = observed
        return matched

    result = asyncio.run(sample_i1_original_cpu_epochs(
        bridge=bridge, boot=boot, world=world, links=links,
        refresh_native_source=refresh_native,
        refresh_paper_source=lambda: (world, links),
        timeout_s=1.0, poll_s=0.01,
    ))
    assert result.per_self_counts == (("A", 2), ("B", 2))
    assert result.continuous_native_updates_observed
    for sid in ("A", "B"):
        rows = [row for row in result.epochs if row.self_id == sid]
        assert [row.native_seq for row in rows] == [4, 6]
        assert [row.native_request_id for row in rows] == [
            f"i1-original-sense-{round_number:031x}{int(sid == 'B'):x}"
            for round_number in (1, 2)
        ]
        assert all(row.source_revision_refs[-1] == row.sense_revision for row in rows)
        assert all(row.native_seq < bridge.current_sense(sid).observation.seq
                   for row in rows)
        assert owners_before[sid] == (
            bridge.owners[sid].retained, bridge.owners[sid].intent,
            bridge.owners[sid].pattern_registry,
        )
    assert _files(bridge) == old_files
    assert all(not row.model_invoked and not row.action_issue_authorized
               for row in result.epochs)


def test_i1_correlated_reader_does_not_adopt_passive_only_native_event(
    tmp_path, monkeypatch,
):
    case = _setup(tmp_path, monkeypatch)
    _, bridge, boot, world, links, _ = case
    assert bridge.current_sense("A") is not None
    assert bridge.current_i1_correlated_sense("A") is None
    with pytest.raises(I1NormalRuntimeHold, match="fresh original native SENSE"):
        read_i1_original_cpu_epoch(
            bridge=bridge, boot=boot, world=world,
            links=links, self_id="A", require_correlated_i1=True,
        )


@pytest.mark.parametrize("reason", [
    "expired", "foreign-session", "wrong-request", "foreign-scope",
    "future-seq", "owner-fenced",
])
def test_i1_correlated_reply_fences_stale_or_foreign_native(
    tmp_path, monkeypatch, reason,
):
    case = _setup(tmp_path, monkeypatch)
    _, bridge, boot, world, links, _ = case
    matched, _ = _matched_with_passive_after(bridge, world, "A", 1)
    assert bridge.current_i1_correlated_sense("A") is matched
    if reason == "expired":
        bridge._i1_correlated_received_at["A"] = time.monotonic() - 10
    elif reason == "foreign-session":
        bridge._i1_correlated_sense["A"] = replace(
            matched, observation=replace(matched.observation, session_id="foreign"),
        )
    elif reason == "wrong-request":
        bridge._i1_correlated_sense["A"] = replace(
            matched, observation=replace(matched.observation, request_id=None),
        )
    elif reason == "foreign-scope":
        bridge._i1_correlated_sense["A"] = replace(
            matched, scope=ScopeRef("B", world.paper_session_id),
        )
    elif reason == "future-seq":
        bridge._i1_correlated_sense["A"] = replace(
            matched,
            observation=replace(matched.observation, seq=matched.observation.seq + 50),
            source_revision_ref=(
                f"mineflayer:{matched.observation.session_id}:"
                f"{matched.observation.seq + 50}"
            ),
        )
    else:
        bridge.cognitive_work.fence_self("A")
    assert bridge.current_i1_correlated_sense("A") is None
    with pytest.raises((I1NormalRuntimeHold, RuntimeError, ValueError)):
        read_i1_original_cpu_epoch(
            bridge=bridge, boot=boot, world=world,
            links=links, self_id="A", require_correlated_i1=True,
        )
