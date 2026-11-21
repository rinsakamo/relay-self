"""I4a: synthetic S1 closed prefix -> S2 native original MOVE -> closed."""
import pytest

from relay_self.action import ActionState
from relay_self.i_lane_i4a_s2_first_native_move_dev import (
    issue_s2_first_original_place_move_synthetic_dev,
)
from relay_self.physical_action_journal import PhysicalActionJournal, PhysicalJournalUnresolved
from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from test_c_lane_stage27hi_multi_action_review_dev import _fixture
from test_i4a_s2_first_move_proposal_dev import _first_s2, _propose
from test_i4a_s2_first_physical_reservation_dev import _prepare
from test_p0d_stage27c_place_move_wal_issuer_dev import ScriptedPlaceNative


def _prepare_native(f, candidate, native):
    native.seq = candidate.source_probe.seq
    native.tick = 1213 + native.seq * 9
    native.x = candidate.source_probe.snapshot.position.x
    native.gate = lambda session, effect, action: f.physical.require_native_effect(
        self_id=candidate.boundary.self_id,
        native_session_id=session, effect=effect, action_id=action,
    )


def test_original_s2_native_parent_look_start_stop_settles_after_s1(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, observed = await _first_s2(f, lane, server)
        candidate = _propose(f, lane, witness, boundary, observed)
        native, args = _prepare(f, lane, candidate, witness)
        _prepare_native(f, candidate, native)
        owner, peer = loop.owner, f.owners[f.names[1]]
        peer_before = (peer.retained, peer.intent.events, dict(peer.skills),
                       peer.files.physical_wal_file.read_bytes())
        old = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        ).records
        receipt = await issue_s2_first_original_place_move_synthetic_dev(
            native, candidate, **args,
        )
        assert receipt.journal_status == "NATIVE_PLACE_MOVE_SETTLED"
        assert receipt.native_effect_issued and not receipt.skill_success_attested
        assert not receipt.l0_goal_succeeded
        assert len(native.sent_commands) == 3
        wal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        assert len(wal.records) == 4
        assert wal.records[:3] == old
        assert wal.records[-1]["action_id"] == candidate.action_id
        assert wal.records[-1]["skill_execution_id"] == boundary.new_skill_id
        assert wal.records[-1]["status"] == "NATIVE_PLACE_MOVE_SETTLED"
        assert owner.supervisor.get(candidate.action_id).state is ActionState.OUTCOME
        assert f.physical.active_action_ids == ()
        with pytest.raises(PhysicalIssueFenceError):
            with f.physical.lease(
                self_id=owner.self_id, native_session_id=owner.native_session_id,
                action_id=candidate.action_id, effect_family="MOVE_PLACE",
            ):
                raise AssertionError("replayed original S2 parent")
        assert (peer.retained, peer.intent.events, dict(peer.skills),
                peer.files.physical_wal_file.read_bytes()) == peer_before
    _fixture(tmp_path, scenario)


def test_original_s2_bad_stop_leaves_prepared_and_denies_replay(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, observed = await _first_s2(f, lane, server)
        candidate = _propose(f, lane, witness, boundary, observed)
        _, args = _prepare(f, lane, candidate, witness)
        native = ScriptedPlaceNative(boundary.native_session_id, bad_stop=True)
        _prepare_native(f, candidate, native)
        with pytest.raises(Exception):
            await issue_s2_first_original_place_move_synthetic_dev(
                native, candidate, **args,
            )
        wal = PhysicalActionJournal.restore(
            loop.owner.files.physical_wal_file, self_id=loop.owner.self_id,
        )
        assert len(wal.records) == 4
        assert wal.records[-1]["status"] == "PREPARED_UNRESOLVED"
        with pytest.raises(PhysicalJournalUnresolved):
            wal.require_clear()
        assert f.physical.active_action_ids == ()
        with pytest.raises(PhysicalIssueFenceError):
            with f.physical.lease(
                self_id=boundary.self_id, native_session_id=boundary.native_session_id,
                action_id=candidate.action_id, effect_family="MOVE_PLACE",
            ):
                raise AssertionError("reopened original S2 parent")
    _fixture(tmp_path, scenario)
