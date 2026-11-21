"""I1 original B readback on a real owned-log byte prefix; CPU/offline only.

A live Paper console prompt may be present after a completed ACK line.
The default original B consumer must still demand its full raw log digest.
Only the explicit I1 path accepts exactly the latest complete original line,
and must refuse subsequent completed line growth / mismatched source.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from relay_self.bd1b_owner_source_dev import (
    BD1bSourceHold,
    build_bd1b_owner_source,
)
from test_stage28c2c_fresh_recovered_l1_dev import _ready


def _read(case, sid="A", *, links=None, i1=False):
    _, bridge, boot, world, original_links, _ = case
    return build_bd1b_owner_source(
        bridge=bridge, boot=boot, world=world,
        links=original_links if links is None else links,
        self_id=sid, i1_complete_paper_prefix=i1,
    )


def test_i1_paper_prompt_does_not_invalidate_exact_completed_ack_source(tmp_path, monkeypatch):
    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, links, _ = case
    path = bridge.paper._log_path
    original = path.read_bytes()
    assert original.endswith(b"\n")
    assert links[0].paper_log_sha256 == hashlib.sha256(original).hexdigest()
    path.write_bytes(original + b"> ")
    for sid in ("A", "B"):
        # Non-I1 B must keep its prior exact full-stream rule.
        with pytest.raises(BD1bSourceHold, match="original A/B native or Paper link mismatch"):
            _read(case, sid)
        # I1 explicitly recomputes the same completed source from the real
        # owned Paper file, not from a caller-submitted unhashed shortcut.
        source = _read(case, sid, i1=True)
        assert source.paper_log_sha256 == hashlib.sha256(original).hexdigest()
        assert source.paper_tick_source_ref == links[0].paper_tick_source_ref
    assert path.read_bytes() == original + b"> "


@pytest.mark.parametrize("tamper", [
    "new-complete-line", "extra-ack", "source-sha", "nonce",
    "foreign-session", "incomplete-ack", "foreign-actor",
])
def test_i1_current_complete_source_rejects_growth_or_tampering(
    tmp_path, monkeypatch, tamper,
):
    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, links, _ = case
    path = bridge.paper._log_path
    original = path.read_bytes()
    path.write_bytes(original + b"> ")
    bad_links = links
    if tamper == "new-complete-line":
        path.write_bytes(original + b"> new log line\n")
    elif tamper == "extra-ack":
        path.write_bytes(original + b"> P0D_TICK_ACK nonce=forged\n")
    elif tamper == "source-sha":
        bad_links = (
            replace(links[0], paper_log_sha256="f" * 64), links[1],
        )
    elif tamper == "nonce":
        bad_links = (
            replace(links[0], paper_tick_source_ref=links[0].paper_tick_source_ref.replace(
                "next-nonce", "other-nonce"
            )), replace(
                links[1], paper_tick_source_ref=links[1].paper_tick_source_ref.replace(
                    "next-nonce", "other-nonce"
                ),
            ),
        )
    elif tamper == "foreign-session":
        bridge.paper._session_id = "paper-owned-foreign"
    elif tamper == "incomplete-ack":
        path.write_bytes(original.split(b"\n", 1)[0] + b"\n" + original.split(b"\n", 1)[1].rstrip(b"\n"))
    else:
        bad_links = (replace(links[0], paper_actor_uuid="forged-actor"), links[1])
    with pytest.raises(BD1bSourceHold):
        _read(case, links=bad_links, i1=True)


def test_i1_current_readback_does_not_promote_observation_or_action(tmp_path, monkeypatch):
    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, links, _ = case
    before_owner = {
        sid: (bridge.owners[sid].retained, bridge.owners[sid].intent,
              bridge.owners[sid].pattern_registry)
        for sid in ("A", "B")
    }
    original = bridge.paper._log_path.read_bytes()
    bridge.paper._log_path.write_bytes(original + b"> ")
    for sid in ("A", "B"):
        source = _read(case, sid, i1=True)
        assert source.native_session_id == bridge.last_login_observations[sid].session_id
        assert source.paper_log_sha256 == links[0].paper_log_sha256
    assert all(
        before_owner[sid] == (
            bridge.owners[sid].retained, bridge.owners[sid].intent,
            bridge.owners[sid].pattern_registry,
        ) for sid in ("A", "B")
    )
    assert bridge.physical.active_action_ids == frozenset()
