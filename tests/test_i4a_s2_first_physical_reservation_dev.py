"""I4a synthetic: S1 settled WAL prefix + S2 original issuer PREPARED (no IO)."""
import hashlib
import json

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_physical_executor_dev import PhysicalGrantStage
from relay_self.action import ActionState
from relay_self.i_lane_i4a_s2_first_physical_reservation_dev import (
    I4AS2FirstReservationHold,
    reserve_s2_first_original_move_synthetic_dev,
)
from relay_self.i_lane_i4a_s2_run_boundary_dev import I4AS2RunBoundaryHold
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalUnresolved,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueFenceError
from test_c_lane_stage27hi_multi_action_review_dev import _fixture
from test_i4a_s2_first_move_proposal_dev import _first_s2, _propose
from test_i4a_s2_owner_handoff_dev import P
from test_p0d_stage27c_place_move_wal_issuer_dev import ScriptedPlaceNative, _grant


def _prepare(f, lane, candidate, witness, **overrides):
    binding = candidate.proposal.binding
    native = ScriptedPlaceNative(candidate.boundary.native_session_id)
    source = {
        "physical": f.physical, "lane": lane,
        "previous_probe": witness.prepared.first_probe,
        "propose_grant": _grant(PhysicalGrantStage.PROPOSE, binding),
        "issue_grant": _grant(PhysicalGrantStage.ISSUE, binding),
        "at_ns": 200020, "provenance": P,
        "grant_real_world": True, "acknowledge_dev_unverified_principal": True,
    }
    source.update(overrides)
    return native, source


def test_s2_original_issuer_appends_prepared_only_and_fences_any_native_io(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, observed = await _first_s2(f, lane, server)
        candidate = _propose(f, lane, witness, boundary, observed)
        peer = f.owners[f.names[1]]
        peer_before = (
            peer.retained, peer.intent.events, dict(peer.skills),
            peer.files.physical_wal_file.read_bytes(),
        )
        owner = loop.owner
        original = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        old_rows = original.records
        native, args = _prepare(f, lane, candidate, witness)
        receipt = reserve_s2_first_original_move_synthetic_dev(
            native, candidate, **args,
        )
        assert receipt.old_prefix_count == 3
        assert receipt.prepared_row_count == 4
        assert receipt.old_prefix_sha256 == original.digest
        assert not receipt.native_effect_issued
        assert not receipt.issue_lease_active
        assert not receipt.resumption_authorized
        assert native.sent_commands == []
        saved = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        assert saved.records[:3] == old_rows
        assert saved.records[-1]["action_id"] == candidate.action_id
        assert saved.records[-1]["status"] == "PREPARED_UNRESOLVED"
        assert saved.digest == receipt.prepared_wal_sha256
        assert owner.supervisor.get(candidate.action_id).state is ActionState.ISSUED
        assert f.physical.active_action_ids == ()
        with pytest.raises(PhysicalIssueFenceError):
            with f.physical.lease(
                self_id=owner.self_id, native_session_id=owner.native_session_id,
                action_id=candidate.action_id, effect_family="MOVE_PLACE",
            ):
                raise AssertionError("duplicate original S2 native lease granted")
        with pytest.raises(PhysicalJournalUnresolved):
            saved.require_clear()
        with pytest.raises(PhysicalIssueFenceError):
            f.physical.require_native_effect(
                self_id=owner.self_id, native_session_id=owner.native_session_id,
                effect="look", action_id=candidate.action_id+"-look",
            )
        with pytest.raises((
            I4AS2FirstReservationHold, I4AS2RunBoundaryHold,
            PhysicalIssueFenceError, PhysicalJournalUnresolved,
        )):
            reserve_s2_first_original_move_synthetic_dev(
                native, candidate, **args,
            )
        assert (peer.retained, peer.intent.events, dict(peer.skills),
                peer.files.physical_wal_file.read_bytes()) == peer_before
    _fixture(tmp_path, scenario)


def test_s2_first_issue_rejects_missing_grant_and_competing_physical_lease(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, observed = await _first_s2(f, lane, server)
        candidate = _propose(f, lane, witness, boundary, observed)
        native, args = _prepare(
            f, lane, candidate, witness, acknowledge_dev_unverified_principal=False,
        )
        path = loop.owner.files.physical_wal_file
        previous = path.read_bytes()
        with pytest.raises(I4AS2FirstReservationHold):
            reserve_s2_first_original_move_synthetic_dev(
                native, candidate, **args,
            )
        assert path.read_bytes() == previous
        args["acknowledge_dev_unverified_principal"] = True
        with f.physical.lease(
            self_id=loop.owner.self_id,
            native_session_id=boundary.native_session_id,
            action_id="conflicting-i4a", effect_family="NONE",
        ):
            with pytest.raises(PhysicalIssueFenceError):
                reserve_s2_first_original_move_synthetic_dev(
                    native, candidate, **args,
                )
        assert path.read_bytes() == previous
        assert candidate.action_id not in {
            action.action_id for action in loop.owner.supervisor.recorded_actions
        }
    _fixture(tmp_path, scenario)


def test_s2_original_issuer_rejects_modified_historic_sha_after_rechecksum(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, observed = await _first_s2(f, lane, server)
        candidate = _propose(f, lane, witness, boundary, observed)
        native, args = _prepare(f, lane, candidate, witness)
        path = loop.owner.files.physical_wal_file
        body = json.loads(path.read_bytes())
        body["body"]["actions"][0]["action_id"] = "rewritten-s1"
        canonical = json.dumps(
            body["body"], ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        body["sha256"] = hashlib.sha256(canonical).hexdigest()
        path.write_text(json.dumps(body), encoding="utf-8")
        with pytest.raises((
            PhysicalIssueFenceError, I4AS2FirstReservationHold, I4AS2RunBoundaryHold,
        )):
            reserve_s2_first_original_move_synthetic_dev(
                native, candidate, **args,
            )
        assert candidate.action_id not in {
            action.action_id for action in loop.owner.supervisor.recorded_actions
        }
    _fixture(tmp_path, scenario)


def test_i4a_synthetic_s2_rejects_live_native_before_wal_or_lease(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, observed = await _first_s2(f, lane, server)
        candidate = _propose(f, lane, witness, boundary, observed)
        scripted, args = _prepare(f, lane, candidate, witness)
        prior = loop.owner.files.physical_wal_file.read_bytes()
        actions = loop.owner.supervisor.recorded_actions

        # A real MineflayerProcessSession is process-backed and does not
        # become a synthetic source just because the same DEV grants exist.
        process_session = object.__new__(MineflayerProcessSession)
        with pytest.raises(I4AS2FirstReservationHold, match="process-backed"):
            reserve_s2_first_original_move_synthetic_dev(
                process_session, candidate, **args,
            )
        # A subclass of MineflayerProcessSession that carries real process
        # resources is likewise not accepted, even with scripted methods.
        scripted._process = object()
        with pytest.raises(I4AS2FirstReservationHold, match="process-backed"):
            reserve_s2_first_original_move_synthetic_dev(
                scripted, candidate, **args,
            )
        assert loop.owner.files.physical_wal_file.read_bytes() == prior
        assert loop.owner.supervisor.recorded_actions == actions
        assert f.physical.active_action_ids == ()
        assert candidate.action_id not in {
            action.action_id for action in loop.owner.supervisor.recorded_actions
        }
    _fixture(tmp_path, scenario)


@pytest.mark.parametrize("resource", ["_process", "_decoder"])
def test_s2_rejects_slot_resource_before_original_wal_or_lease(tmp_path, resource):
    """A real resource in __slots__ was invisible to the old __dict__ fence."""
    class SlottedNative(ScriptedPlaceNative):
        __slots__ = ("_process", "_decoder")

    async def scenario(f, lane, server):
        loop, witness, boundary, observed = await _first_s2(f, lane, server)
        candidate = _propose(f, lane, witness, boundary, observed)
        _, args = _prepare(f, lane, candidate, witness)
        native = SlottedNative(boundary.native_session_id)
        setattr(native, resource, object())
        assert resource not in vars(native)
        owner = loop.owner
        previous_wal = owner.files.physical_wal_file.read_bytes()
        previous_actions = owner.supervisor.recorded_actions
        with pytest.raises(I4AS2FirstReservationHold, match="process-backed"):
            reserve_s2_first_original_move_synthetic_dev(
                native, candidate, **args,
            )
        assert owner.files.physical_wal_file.read_bytes() == previous_wal
        assert owner.supervisor.recorded_actions == previous_actions
        assert f.physical.active_action_ids == ()
        assert candidate.action_id not in {
            action.action_id for action in owner.supervisor.recorded_actions
        }
    _fixture(tmp_path, scenario)


def test_s2_rejects_class_resource_and_failing_descriptor():
    from relay_self.i_lane_i4a_s2_first_physical_reservation_dev import (
        require_i4a_offline_scripted_native,
    )

    class ClassResource(MineflayerProcessSession):
        _process = object()

    class UninspectableNative(MineflayerProcessSession):
        @property
        def _decoder(self):
            raise RuntimeError("decoder inspection unavailable")

    for cls in (ClassResource, UninspectableNative):
        with pytest.raises(I4AS2FirstReservationHold, match="process-backed"):
            require_i4a_offline_scripted_native(object.__new__(cls))
