"""Write-once original S1 evidence and independent S2 prefix audit.

All World/model/native actions in these fixtures are synthetic DEV only.
"""
import hashlib
import json
from dataclasses import replace

import pytest

from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    capture_live_wal_history_anchor,
)
from relay_self.i_lane_i4a_s1_source_capture_dev import (
    I4AS1SourceHold,
    audit_s1_prefix_after_s2,
    freeze_original_s1_wal,
)
from relay_self.i_lane_i4a_s2_first_physical_reservation_dev import (
    reserve_s2_first_original_move_synthetic_dev,
)
from test_c_lane_stage27hi_multi_action_review_dev import _fixture, _run_multi
from test_i4a_live_wal_anchor_dev import _close_original_s1
from test_i4a_s2_first_move_proposal_dev import _first_s2, _propose
from test_i4a_s2_first_physical_reservation_dev import _prepare


def test_original_owner_freezes_s1_bytes_once_and_rejects_recomputed_forgery(tmp_path):
    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        peer = f.owners[f.names[1]]
        peer_before = peer.files.physical_wal_file.read_bytes()
        _close_original_s1(loop)
        anchor = capture_live_wal_history_anchor(loop, lane=lane)
        directory = tmp_path / "original-s1"
        directory.mkdir()
        initial = loop.owner.files.physical_wal_file.read_bytes()
        receipt = freeze_original_s1_wal(
            loop.owner, physical=f.physical, lane=lane,
            anchor=anchor, evidence_dir=directory,
        )
        assert receipt.action_ids == anchor.action_ids
        assert len(receipt.action_ids) == 3
        assert receipt.restart_authenticated is False
        assert not receipt.physical_authorized
        assert (directory / "i4a-original-s1-wal.json").read_bytes() == initial
        with pytest.raises(I4AS1SourceHold, match="already used"):
            freeze_original_s1_wal(
                loop.owner, physical=f.physical, lane=lane,
                anchor=anchor, evidence_dir=directory,
            )
        assert loop.owner.files.physical_wal_file.read_bytes() == initial
        assert peer.files.physical_wal_file.read_bytes() == peer_before
    _fixture(tmp_path, scenario)


def test_s1_s2_prefix_readback_accepts_unresolved_but_never_reissues(tmp_path):
    async def scenario(f, lane, server):
        loop, witness, boundary, observed = await _first_s2(f, lane, server)
        directory = tmp_path / "original"
        directory.mkdir()
        receipt = freeze_original_s1_wal(
            loop.owner, physical=f.physical, lane=lane,
            anchor=boundary.anchor, evidence_dir=directory,
        )
        candidate = _propose(f, lane, witness, boundary, observed)
        scripted, args = _prepare(f, lane, candidate, witness)
        prepared = reserve_s2_first_original_move_synthetic_dev(
            scripted, candidate, **args,
        )
        assert prepared.status == "PREPARED_UNRESOLVED"
        current = loop.owner.files.physical_wal_file
        before = current.read_bytes()
        readback = audit_s1_prefix_after_s2(
            receipt, current_wal=current,
            new_action_id=candidate.action_id,
            new_skill_id=boundary.new_skill_id,
            new_intent_id=boundary.new_intent_id,
        )
        assert readback.classification == "I4A_S1_S2_WAL_PREFIX_READBACK_ONLY"
        assert readback.s2_status == "PREPARED_UNRESOLVED"
        assert not readback.physical_authorized
        assert not readback.restart_authenticated
        assert current.read_bytes() == before
        assert scripted.sent_commands == []

        with pytest.raises(I4AS1SourceHold):
            audit_s1_prefix_after_s2(
                receipt, current_wal=current, new_action_id=candidate.action_id,
                new_skill_id=boundary.old_skill_id,
                new_intent_id=boundary.new_intent_id,
            )
        with pytest.raises(I4AS1SourceHold):
            audit_s1_prefix_after_s2(
                replace(receipt, raw_sha256="0" * 64),
                current_wal=current, new_action_id=candidate.action_id,
                new_skill_id=boundary.new_skill_id,
                new_intent_id=boundary.new_intent_id,
            )
        assert current.read_bytes() == before

        # An attacker can recompute the WAL checksum, not the earlier
        # independently retained Owner-issued S1 capture/prefix bytes.
        payload = json.loads(before)
        payload["body"]["actions"][0]["action_id"] = "forged-old-action"
        canonical = json.dumps(
            payload["body"], sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        payload["sha256"] = hashlib.sha256(canonical).hexdigest()
        current.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(I4AS1SourceHold, match="S1 history differs"):
            audit_s1_prefix_after_s2(
                receipt, current_wal=current, new_action_id=candidate.action_id,
                new_skill_id=boundary.new_skill_id,
                new_intent_id=boundary.new_intent_id,
            )
    _fixture(tmp_path, scenario)


def test_s1_source_refuses_symlinked_archive_and_competing_lease(tmp_path):
    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        _close_original_s1(loop)
        anchor = capture_live_wal_history_anchor(loop, lane=lane)
        directory = tmp_path / "real"
        directory.mkdir()
        alias = tmp_path / "alias"
        alias.symlink_to(directory, target_is_directory=True)
        with pytest.raises(I4AS1SourceHold, match="non-symlink"):
            freeze_original_s1_wal(
                loop.owner, physical=f.physical, lane=lane,
                anchor=anchor, evidence_dir=alias,
            )
        assert not list(directory.iterdir())
        with f.physical.lease(
            self_id=loop.owner.self_id, native_session_id=anchor.native_session_id,
            action_id="competing-raw-evidence", effect_family="NONE",
        ):
            with pytest.raises(I4AS1SourceHold, match="not quiescent"):
                freeze_original_s1_wal(
                    loop.owner, physical=f.physical, lane=lane,
                    anchor=anchor, evidence_dir=directory,
                )
        assert not list(directory.iterdir())
    _fixture(tmp_path, scenario)
