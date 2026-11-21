"""I4a: original Owner S1 certified prefix -> empty S2 authenticated boundary."""
import hashlib
import json
from dataclasses import replace

import pytest

from relay_self.i_lane_i4a_s2_owner_handoff_dev import (
    begin_live_s2_owner_handoff,
    finish_live_s2_l1,
    submit_live_s2_l1,
)
from relay_self.i_lane_i4a_s2_run_boundary_dev import (
    I4AS2RunBoundaryHold,
    attest_i4a_s2_empty_run_boundary,
    verify_i4a_s2_empty_run_boundary,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from test_c_lane_stage27hi_multi_action_review_dev import _fixture
from test_i4a_s2_owner_handoff_dev import (
    P,
    _adopt,
    _obs_new,
    _prepared,
    _return,
)


async def _s2_bound(f, lane, server):
    loop, prepared, first = await _prepared(f, lane, server)
    server.choice_id = "1"
    ticket = submit_live_s2_l1(prepared)
    after = _obs_new(first, 1, "i4a-runboundary-current")
    witness = await finish_live_s2_l1(
        prepared, ticket=ticket, post_model_probe=lambda: _return(after),
    )
    _adopt(loop.owner, after)
    handoff = begin_live_s2_owner_handoff(
        witness, at_ns=200000, provenance=P,
    )
    boundary = attest_i4a_s2_empty_run_boundary(witness, handoff)
    return loop, boundary


def test_s2_authenticated_empty_scope_retains_s1_history_and_peer(tmp_path):
    async def scenario(f, lane, server):
        loop, boundary = await _s2_bound(f, lane, server)
        # Existing Stage26 A/B restore legitimately changes peer during S1
        # setup. Only compare after the original S2 boundary is established.
        peer = f.owners[f.names[1]]
        before = (
            peer.retained, peer.intent.events, dict(peer.skills),
            peer.files.physical_wal_file.read_bytes(),
        )
        assert boundary.prefix_count == 3
        assert boundary.new_skill_id != boundary.old_skill_id
        assert boundary.new_intent_id != boundary.old_intent_id
        assert boundary.new_action_authorized is False
        verify_i4a_s2_empty_run_boundary(
            boundary, physical=f.physical, lane=lane,
        )
        with pytest.raises(I4AS2RunBoundaryHold, match="Owner/current"):
            verify_i4a_s2_empty_run_boundary(
                replace(boundary, new_skill_id="forged-s2-skill"),
                physical=f.physical, lane=lane,
            )
        assert (peer.retained, peer.intent.events, dict(peer.skills),
                peer.files.physical_wal_file.read_bytes()) == before
        assert len(PhysicalActionJournal.restore(
            loop.owner.files.physical_wal_file, self_id=loop.owner.self_id,
        ).records) == 3
    _fixture(tmp_path, scenario)


def test_s2_boundary_rejects_wal_forgery_with_recomputed_checksum(tmp_path):
    async def scenario(f, lane, server):
        loop, boundary = await _s2_bound(f, lane, server)
        path = loop.owner.files.physical_wal_file
        data = json.loads(path.read_bytes())
        data["body"]["actions"][0]["action_id"] = "forged-history"
        canonical = json.dumps(
            data["body"], ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        data["sha256"] = hashlib.sha256(canonical).hexdigest()
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(I4AS2RunBoundaryHold, match="no longer qualified"):
            verify_i4a_s2_empty_run_boundary(
                boundary, physical=f.physical, lane=lane,
            )
    _fixture(tmp_path, scenario)


def test_s2_boundary_rejects_competing_lease_and_changed_current(tmp_path):
    async def scenario(f, lane, server):
        loop, boundary = await _s2_bound(f, lane, server)
        with f.physical.lease(
            self_id=loop.owner.self_id,
            native_session_id=loop.owner.native_session_id,
            action_id="i4a-s2-competing", effect_family="NONE",
        ):
            with pytest.raises(I4AS2RunBoundaryHold, match="no longer qualified"):
                verify_i4a_s2_empty_run_boundary(
                    boundary, physical=f.physical, lane=lane,
                )
        verify_i4a_s2_empty_run_boundary(
            boundary, physical=f.physical, lane=lane,
        )
        stale = _obs_new(
            loop.owner.current_worldbody_observation, 1, "i4a-s2-stale",
        )
        _adopt(loop.owner, stale)
        with pytest.raises(I4AS2RunBoundaryHold, match="Owner/current"):
            verify_i4a_s2_empty_run_boundary(
                boundary, physical=f.physical, lane=lane,
            )
    _fixture(tmp_path, scenario)
