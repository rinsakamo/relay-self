"""I4a: first new S2 MOVE uses original ActionPort only; no issuer authority."""
import hashlib
import json
from dataclasses import replace

import pytest

from relay_self.action import ActionState
from relay_self.i_lane_i4a_s2_first_move_proposal_dev import (
    I4AS2MotorProposalHold,
    propose_s2_first_original_place_move,
)
from relay_self.i_lane_i4a_s2_owner_handoff_dev import (
    begin_live_s2_owner_handoff,
    finish_live_s2_l1,
    submit_live_s2_l1,
)
from relay_self.i_lane_i4a_s2_run_boundary_dev import (
    attest_i4a_s2_empty_run_boundary,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability
from test_c_lane_stage27hi_multi_action_review_dev import _fixture
from test_i4a_s2_owner_handoff_dev import P, _adopt, _obs_new, _prepared, _return


async def _first_s2(f, lane, server):
    loop, prepared, first = await _prepared(f, lane, server)
    server.choice_id = "1"
    ticket = submit_live_s2_l1(prepared)
    after = _obs_new(first, 1, "i4a-new-move-first")
    witness = await finish_live_s2_l1(
        prepared, ticket=ticket, post_model_probe=lambda: _return(after),
    )
    _adopt(loop.owner, after)
    handoff = begin_live_s2_owner_handoff(
        witness, at_ns=200000, provenance=P,
    )
    boundary = attest_i4a_s2_empty_run_boundary(witness, handoff)
    return loop, witness, boundary, after


def _propose(f, lane, witness, boundary, native):
    return propose_s2_first_original_place_move(
        boundary, witness, physical=f.physical, lane=lane,
        native=native,
        capability=PhysicalCapability("MOVE", 1, "locomotion", "DESTINATION", True),
        at_ns=200010, provenance=P,
    )


def test_s2_original_actionport_proposed_without_wal_or_native_issue(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, native = await _first_s2(f, lane, server)
        owner = loop.owner
        peer = f.owners[f.names[1]]
        peer_before = (peer.retained, peer.intent.events, dict(peer.skills),
                       peer.files.physical_wal_file.read_bytes())
        source_wal = owner.files.physical_wal_file.read_bytes()
        actions = owner.supervisor.recorded_actions
        candidate = _propose(f, lane, witness, boundary, native)
        assert candidate.ir.invocation.invocation_ref == boundary.invocation_ref
        assert candidate.proposal.proposal.state is ActionState.PROPOSED
        assert not candidate.target_clearance_attested
        assert not candidate.physical_authorized
        assert not candidate.physical_issued
        assert not candidate.wal_modified
        assert candidate.proposal.proposal.action_id == candidate.action_id
        assert owner.files.physical_wal_file.read_bytes() == source_wal
        assert owner.supervisor.recorded_actions == actions
        assert len(PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        ).records) == boundary.prefix_count
        assert (peer.retained, peer.intent.events, dict(peer.skills),
                peer.files.physical_wal_file.read_bytes()) == peer_before
    _fixture(tmp_path, scenario)


def test_s2_first_action_rejects_forged_history_even_if_checksum_rebuilt(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, native = await _first_s2(f, lane, server)
        path = loop.owner.files.physical_wal_file
        body = json.loads(path.read_bytes())
        body["body"]["actions"][0]["action_id"] = "forged-s1-history"
        canonical = json.dumps(
            body["body"], ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        body["sha256"] = hashlib.sha256(canonical).hexdigest()
        path.write_text(json.dumps(body), encoding="utf-8")
        with pytest.raises(I4AS2MotorProposalHold, match="boundary stale"):
            _propose(f, lane, witness, boundary, native)
    _fixture(tmp_path, scenario)


def test_s2_first_action_rejects_competing_lease_and_stale_current(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, native = await _first_s2(f, lane, server)
        with f.physical.lease(
            self_id=loop.owner.self_id,
            native_session_id=loop.owner.native_session_id,
            action_id="i4a-fence-competitor",
            effect_family="NONE",
        ):
            with pytest.raises(I4AS2MotorProposalHold, match="boundary stale"):
                _propose(f, lane, witness, boundary, native)
        stale = replace(native, seq=native.seq+1, request_id="i4a-later-native")
        _adopt(loop.owner, stale)
        with pytest.raises(I4AS2MotorProposalHold, match="boundary stale"):
            _propose(f, lane, witness, boundary, native)
    _fixture(tmp_path, scenario)
