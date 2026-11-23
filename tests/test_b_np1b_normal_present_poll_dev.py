"""Original Bridge normal CPU caller after A reJOIN and continuous B.

All tests use the original Mineflayer decoder, original Bridge logout/login and
the owned Paper subprocess with synthetic events; no real World/GPU/Action.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace

import pytest

from relay_self.b_np1b_continuing_b_composite_dev import (
    ContinuingCompositeHold,
    ContinuingCompositeSourceReceipt,
    build_continuing_b_composite_source,
)
from relay_self.b_np1b_normal_present_poll_dev import NormalPresentCpuPoll, NormalPresentPollHold
from relay_self.b_np1b_rejoin_present_dev import RejoinedOwnerSource
from relay_self.owned_paper_world_dev import PaperTickReceipt
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_initial_source_dev import ACTORS, BOOT, WORLD
from test_b_np1b_owner_bound_rejoin_dev import _paper_line
from test_b_np1b_owner_bound_rejoin_dev import rejoined as rejoined
from test_b_np1b_rejoin_present_dev import rejoined_present as rejoined_present


@pytest.fixture
def pair(request):
    assert rejoined_present is not None and rejoined is not None and current_fixture is not None
    f, initial, old_native, historical, old_session, logout, b_before = (
        request.getfixturevalue("rejoined_present")
    )
    # This is *new* independent Paper B presence AFTER A's second JOIN.
    # The earlier B presence between A QUIT and A JOIN remains untouched.
    ack_prefix = "P0D_TICK_ACK nonce=88888888"
    data = f.paper._log_path.read_text()
    assert data.count(ack_prefix) == 1
    f.paper._log_path.write_text(
        data.replace(ack_prefix, _paper_line("PRESENT", 24, "B") + ack_prefix)
    )
    return f, initial, old_native, historical, old_session, logout, b_before


def _history(pair):
    f, initial, _, historical, _, _, _ = pair
    return dict(bridge=f.bridge, initial_receipts=initial, historical_composite=historical)


def _owner_state(f):
    return {
        sid: (owner.retained, owner.intent, owner.pattern_registry,
              dict(owner.skills), set(owner.pending_questions))
        for sid, owner in f.owners.items()
    }


def test_bridge_normal_cpu_pair_uses_current_independent_a_b_sources(pair):
    f, initial, _, historical, old_session, _, b_before = pair
    before_files = files(f)
    before_state = _owner_state(f)
    with pytest.raises(NormalPresentPollHold):
        f.bridge.poll_normal_present_cpu()
    f.bridge.bind_normal_rejoin_present_cpu(
        initial_receipts=initial, historical_composite=historical,
    )
    result = f.bridge.poll_normal_present_cpu()
    assert type(result) is NormalPresentCpuPoll
    assert result == f.bridge.poll_normal_present_cpu()
    a, b = result.a_present, result.b_present
    ca, cb = a.source.composite_receipt, b.source.composite_receipt
    assert type(b.source) is RejoinedOwnerSource
    assert type(cb) is ContinuingCompositeSourceReceipt
    assert ca.self_id == "A" and cb.self_id == "B"
    assert ca.native_session_id != old_session
    assert cb.native_session_id == initial[1].native_session_id
    assert cb.native_session_id == b_before[2][1]
    assert cb.native_request_id == initial[1].native_request_id
    assert cb.native_sequence == initial[1].native_sequence
    assert cb.native_revision == initial[1].native_revision
    assert cb.paper_tick == ca.paper_tick == 25
    assert cb.paper_tick_ref == ca.paper_tick_ref
    assert cb.paper_actor_uuid == ACTORS[1]
    assert ca.paper_actor_uuid == ACTORS[0]
    assert ca.paper_log_sha256 == cb.paper_log_sha256
    assert ca.paper_revision != cb.paper_revision
    assert ca.composite_revision != cb.composite_revision
    assert cb.b_post_rejoin_present_tick == 24
    assert cb.b_post_rejoin_present_line > ca.paper_rejoin_line
    assert cb.b_continuity_revision == ca.b_continuity_revision
    assert b.source.native_probe_source_ref == initial[1].native_source_ref
    assert b.source.native_world_time_tick == initial[1].native_world_time
    assert b.source.native_session_id == f.bridge.sessions["B"].started.session_id
    assert a.source.resident_epoch > b.source.resident_epoch
    for sid, frame, inquiry in (("A", a, result.a_inquiry), ("B", b, result.b_inquiry)):
        assert frame.present.three_self.scope.self_id == sid
        refs = frame.present.three_self.source_revision_refs
        assert len(refs) == 3
        assert refs[0].startswith("native:")
        assert refs[1].startswith("paper:")
        assert refs[2] == "composite:rejoin:" + frame.source.composite_receipt.composite_revision
        assert frame.exploration_need is not None
        assert inquiry is not None
        assert inquiry.self_id == sid
        assert inquiry.source_revision_refs == refs
        assert inquiry.coverage_claim_ref == frame.exploration_need.basis[0].present_ref
    assert result.source_pair_revision.startswith("sha256:")
    assert f.bridge.sessions["B"] is b_before[0]
    assert f.owners["B"].current_worldbody_observation is b_before[1]
    assert f.cognitive.current_scope("B") == b_before[2]
    assert historical.native_session_id == old_session
    assert files(f) == before_files
    assert _owner_state(f) == before_state


def test_new_b_paper_source_refreshes_pair_without_stale_receipt_reuse(pair, monkeypatch):
    f = pair[0]
    f.bridge.bind_normal_rejoin_present_cpu(**{
        k: v for k, v in _history(pair).items() if k != "bridge"
    })
    original = f.bridge.poll_normal_present_cpu()
    prior_a, prior_b = original.a_present.source.composite_receipt, original.b_present.source.composite_receipt
    original_bytes = f.paper._log_path.read_text()
    new_nonce = "99999999-9999-4999-8999-999999999999"
    session_id = f.paper.owned_session_id
    f.paper._log_path.write_text(
        original_bytes
        + _paper_line("PRESENT", 26, "B")
        + f"P0D_TICK_ACK nonce={new_nonce} boot={BOOT} session={session_id} "
          f"world={WORLD} tick=27 source=PAPER_MAIN_THREAD\n"
    )
    tick = PaperTickReceipt(
        session_id, 27, f"paper-main-thread:p0d:{BOOT}:{new_nonce}:sha256:" + "d" * 64,
    )
    monkeypatch.setattr(f.paper, "tick_readback", lambda _: tick)
    newer = f.bridge.poll_normal_present_cpu()
    assert newer == f.bridge.poll_normal_present_cpu()
    assert newer.source_pair_revision != original.source_pair_revision
    assert newer.a_present.source.composite_receipt.native_revision == prior_a.native_revision
    assert newer.b_present.source.composite_receipt.native_revision == prior_b.native_revision
    assert newer.a_present.source.composite_receipt.paper_revision != prior_a.paper_revision
    assert newer.b_present.source.composite_receipt.paper_revision != prior_b.paper_revision
    assert newer.b_present.source.composite_receipt.b_post_rejoin_present_tick == 26
    assert (prior_a.paper_tick, prior_b.paper_tick) == (25, 25)


def test_missing_b_post_rejoin_present_never_qualifies_normal_cpu(rejoined_present):
    f, initial, _, historical, _, _, _ = rejoined_present
    with pytest.raises(ContinuingCompositeHold):
        build_continuing_b_composite_source(
            bridge=f.bridge, initial_receipts=initial,
            historical_composite=historical,
        )
    # The original Bridge caller normalizes a lower-level B HOLD.
    with pytest.raises(NormalPresentPollHold):
        f.bridge.bind_normal_rejoin_present_cpu(
            initial_receipts=initial, historical_composite=historical,
        )
    with pytest.raises(NormalPresentPollHold):
        f.bridge.poll_normal_present_cpu()


@pytest.mark.parametrize("fault", [
    "a_logout", "b_logout", "a_session", "b_session", "a_request",
    "b_request", "a_epoch", "b_epoch", "b_owner", "b_probe",
    "paper_pid", "paper_session", "paper_boot", "paper_nonce",
    "b_post_present", "b_quit", "b_actor", "a_new_join",
    "native_update_pending", "foreign_paper_log",
    "a_schema", "b_schema", "forbidden_old",
])
def test_original_paired_poll_rejects_changed_sources(pair, monkeypatch, fault):
    f, initial, _, historical, old_session, _, _ = pair
    f.bridge.bind_normal_rejoin_present_cpu(
        initial_receipts=initial, historical_composite=historical,
    )
    old = f.bridge.poll_normal_present_cpu()
    bridge = f.bridge
    paper = f.paper
    if fault in ("a_logout", "b_logout"):
        asyncio.run(bridge.logout("A" if fault == "a_logout" else "B"))
    elif fault in ("a_session", "b_session"):
        sid = "A" if fault == "a_session" else "B"
        bridge.sessions[sid]._started = replace(
            bridge.sessions[sid].started, session_id="forged-session",
        )
    elif fault in ("a_request", "b_request"):
        sid = "A" if fault == "a_request" else "B"
        bridge.last_login_evidence[sid] = replace(
            bridge.last_login_evidence[sid], observation_ref="foreign-request",
        )
    elif fault in ("a_epoch", "b_epoch"):
        sid = "A" if fault == "a_epoch" else "B"
        f.cognitive._states[sid].epoch += 1
    elif fault == "b_owner":
        bridge.owners["B"] = bridge.owners["A"]
    elif fault == "b_probe":
        bridge.owners["B"].current_worldbody_observation = replace(
            bridge.owners["B"].current_worldbody_observation, seq=88,
        )
    elif fault == "paper_pid":
        original = paper._assert_owned
        monkeypatch.setattr(
            paper, "_assert_owned",
            lambda: type("OtherProcess", (), {"pid": original().pid + 1})(),
        )
    elif fault == "paper_session":
        paper._session_id = "foreign-paper"
    elif fault in ("paper_boot", "paper_nonce"):
        tick = paper.tick_readback(paper.owned_session_id)
        source = BOOT if fault == "paper_boot" else "88888888"
        monkeypatch.setattr(
            paper, "tick_readback",
            lambda _: replace(tick, source_ref=tick.source_ref.replace(source, "forged")),
        )
    elif fault in ("b_post_present", "b_quit", "b_actor", "a_new_join", "foreign_paper_log"):
        original = paper._log_path.read_text()
        if fault == "b_post_present":
            original = original.replace(_paper_line("PRESENT", 24, "B"), "")
        elif fault == "b_quit":
            original = original.replace(
                _paper_line("PRESENT", 24, "B"), _paper_line("QUIT", 24, "B"),
            )
        elif fault == "b_actor":
            original = original.replace(
                _paper_line("PRESENT", 24, "B"),
                _paper_line("PRESENT", 24, "B").replace(ACTORS[1], ACTORS[0]),
            )
        elif fault == "a_new_join":
            original = original.replace(
                _paper_line("JOIN", 23, "A"), _paper_line("MOVE", 23, "A"),
            )
        else:
            original += "appended unverified raw log\n"
        paper._log_path.write_text(original)
    elif fault == "native_update_pending":
        bridge._fresh_native_pending = {"B": object()}
    elif fault in ("a_schema", "b_schema"):
        del f.cognitive._present_schemas["A" if fault == "a_schema" else "B"]
    else:
        assert fault == "forbidden_old"
        bridge.forbidden_native_sessions = frozenset()
    with pytest.raises((NormalPresentPollHold, RuntimeError, ValueError)):
        bridge.poll_normal_present_cpu()
    assert old.source_pair_revision.startswith("sha256:")
    assert old.a_present.source.composite_receipt.old_native_session_id == old_session


def test_no_stale_external_history_rebinding_or_foreign_bridge(pair):
    f = pair[0]
    args = _history(pair)
    with pytest.raises(NormalPresentPollHold):
        f.bridge.bind_normal_rejoin_present_cpu(
            initial_receipts=args["initial_receipts"],
            historical_composite=replace(args["historical_composite"], native_request_id="forged"),
        )
    with pytest.raises(NormalPresentPollHold):
        f.bridge.poll_normal_present_cpu()
    f.bridge.bind_normal_rejoin_present_cpu(
        initial_receipts=args["initial_receipts"],
        historical_composite=args["historical_composite"],
    )
    with pytest.raises(NormalPresentPollHold):
        f.bridge.bind_normal_rejoin_present_cpu(
            initial_receipts=args["initial_receipts"],
            historical_composite=args["historical_composite"],
        )
    with pytest.raises(NormalPresentPollHold):
        f.cognitive.poll_normal_present_cpu(bridge=object())
    result = f.bridge.poll_normal_present_cpu()
    assert result.source_pair_revision
    assert asdict(args["historical_composite"])["native_session_id"] == pair[4]


def test_paired_poll_rechecks_external_log_during_projection(pair, monkeypatch):
    f = pair[0]
    f.bridge.bind_normal_rejoin_present_cpu(
        initial_receipts=pair[1], historical_composite=pair[3],
    )
    read = f.paper.read_owned_log
    calls = [0]

    def changed_log(session):
        calls[0] += 1
        data = read(session)
        return data + b"unverified append\n" if calls[0] > 6 else data

    monkeypatch.setattr(f.paper, "read_owned_log", changed_log)
    with pytest.raises((NormalPresentPollHold, RuntimeError, ValueError)):
        f.bridge.poll_normal_present_cpu()
