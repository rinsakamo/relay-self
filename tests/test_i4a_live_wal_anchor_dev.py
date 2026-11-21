"""I4a: independent live Owner anchor; no new physical issue authority."""
import hashlib
import json

import pytest

from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    I4ALiveAnchorHold,
    capture_live_wal_history_anchor,
    verify_live_wal_history_anchor,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.skill import SkillState
from test_c_lane_stage27hi_multi_action_review_dev import _fixture, _run_multi


def _close_original_s1(loop):
    owner = loop.owner
    provenance = Provenance("i4a-test", "explicit-synthetic-cancel")
    owner.finish_reviewed_skill(
        loop.handoff.skill_execution_id, outcome=SkillState.CANCELLED,
        reason="synthetic explicit cancellation", at_ns=100000,
        provenance=provenance,
    )
    owner.complete_intent(
        loop.handoff.intent_id, reason="synthetic release",
        at_ns=100001, provenance=provenance,
    )


def _rewrite_with_valid_checksum(path):
    envelope = json.loads(path.read_bytes())
    envelope["body"]["actions"][0]["action_id"] = "forged-action-id"
    canonical = json.dumps(
        envelope["body"], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    envelope["sha256"] = hashlib.sha256(canonical).hexdigest()
    path.write_text(json.dumps(envelope), encoding="utf-8")


def test_live_owner_anchor_captures_unmodified_s1_and_rejects_rechecksum_tamper(tmp_path):
    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        owner = loop.owner
        peer = f.owners[f.names[1]]
        peer_before = (dict(peer.skills), peer.intent.events,
                       peer.files.physical_wal_file.read_bytes())
        _close_original_s1(loop)
        with pytest.raises(I4ALiveAnchorHold, match="anchor required"):
            verify_live_wal_history_anchor(
                owner, physical=f.physical, lane=lane, anchor=None)
        anchor = capture_live_wal_history_anchor(loop, lane=lane)
        assert len(anchor.action_ids) == 3
        verify_live_wal_history_anchor(
            owner, physical=f.physical, lane=lane, anchor=anchor)
        with pytest.raises(I4ALiveAnchorHold, match="unanchored"):
            capture_live_wal_history_anchor(loop, lane=lane)
        with pytest.raises(I4ALiveAnchorHold, match="foreign"):
            verify_live_wal_history_anchor(
                peer, physical=f.physical, lane=lane, anchor=anchor)
        path = owner.files.physical_wal_file
        original_digest = anchor.wal_sha256
        _rewrite_with_valid_checksum(path)
        assert PhysicalActionJournal.restore(
            path, self_id=owner.self_id).digest != original_digest
        with pytest.raises(I4ALiveAnchorHold, match="history differs"):
            verify_live_wal_history_anchor(
                owner, physical=f.physical, lane=lane, anchor=anchor)
        assert (dict(peer.skills), peer.intent.events,
                peer.files.physical_wal_file.read_bytes()) == peer_before
    _fixture(tmp_path, scenario)


def test_live_owner_anchor_rejects_pre_capture_tamper(tmp_path):
    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        _close_original_s1(loop)
        _rewrite_with_valid_checksum(loop.owner.files.physical_wal_file)
        with pytest.raises(I4ALiveAnchorHold, match="lineage changed"):
            capture_live_wal_history_anchor(loop, lane=lane)
        assert getattr(loop.owner, "_i4a_live_wal_anchor", None) is None
    _fixture(tmp_path, scenario)


def test_live_owner_anchor_requires_quiescent_original_issuer(tmp_path):
    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        _close_original_s1(loop)
        with f.physical.lease(
            self_id=loop.owner.self_id,
            native_session_id=loop.owner.native_session_id,
            action_id="i4a-test-competing-lease", effect_family="NONE",
        ):
            with pytest.raises(I4ALiveAnchorHold, match="physical issuer"):
                capture_live_wal_history_anchor(loop, lane=lane)
        anchor = capture_live_wal_history_anchor(loop, lane=lane)
        with f.physical.lease(
            self_id=loop.owner.self_id,
            native_session_id=loop.owner.native_session_id,
            action_id="i4a-test-second-lease", effect_family="NONE",
        ):
            with pytest.raises(I4ALiveAnchorHold, match="physical issuer"):
                verify_live_wal_history_anchor(
                    loop.owner, physical=f.physical, lane=lane, anchor=anchor)
        verify_live_wal_history_anchor(
            loop.owner, physical=f.physical, lane=lane, anchor=anchor)
    _fixture(tmp_path, scenario)


def test_live_owner_anchor_no_authority_after_session_change(tmp_path):
    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        _close_original_s1(loop)
        anchor = capture_live_wal_history_anchor(loop, lane=lane)
        loop.owner.native_session_id = "retired-synthetic-session"
        with pytest.raises(I4ALiveAnchorHold, match="scope"):
            verify_live_wal_history_anchor(
                loop.owner, physical=f.physical, lane=lane, anchor=anchor)
    _fixture(tmp_path, scenario)
