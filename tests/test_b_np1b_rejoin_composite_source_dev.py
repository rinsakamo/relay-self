"""Post-reJOIN composite: original Bridge process/decoder and owned Paper stream."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from relay_self.b_np1b_current_composite_source_dev import (
    CompositeSourceHold,
    build_current_composite_source,
)
from relay_self.b_np1b_fresh_native_update_dev import read_rejoined_native_revision
from relay_self.b_np1b_initial_source_dev import _revision
from relay_self.b_np1b_rejoin_composite_source_dev import (
    RejoinCompositeHold,
    RejoinedCompositeSourceReceipt,
    build_rejoined_composite_source,
)
from relay_self.owned_paper_world_dev import PaperTickReceipt
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_initial_source_dev import ACTORS, BOOT, PRESENCE
from test_b_np1b_owner_bound_rejoin_dev import rejoined as rejoined


def build(rejoined):
    f, initial, _, old, _, _, _ = rejoined
    return build_rejoined_composite_source(
        bridge=f.bridge, initial_receipts=initial, historical_composite=old,
    )


def test_full_original_bridge_cycle_creates_current_immutable_receipt(rejoined):
    assert current_fixture is not None
    f, initial, native_old, historical, old_session, logout, b_before = rejoined
    files_before = files(f)
    cognition_before = {
        sid: (owner.retained, owner.intent, owner.pattern_registry,
              dict(owner.skills), set(owner.pending_questions))
        for sid, owner in f.owners.items()
    }
    new = build(rejoined)
    again = build(rejoined)
    expected_native = read_rejoined_native_revision(bridge=f.bridge, self_id="A")
    assert isinstance(new, RejoinedCompositeSourceReceipt)
    assert isinstance(f.bridge.sessions["A"], MineflayerProcessSession)
    assert new == again
    assert new.self_id == "A"
    assert new.owner_identity == str(f.owners["A"].files.self_root)
    assert new.resident_epoch == f.cognitive.current_scope("A")[0]
    assert new.resident_epoch > initial[0].resident_epoch
    assert new.native_session_id == f.bridge.sessions["A"].started.session_id != old_session
    assert new.native_request_id == expected_native.native_request_id
    assert new.native_sequence == expected_native.native_sequence
    assert new.native_source_ref == expected_native.native_source_ref
    assert new.native_world_time == expected_native.native_world_time
    assert new.native_revision == expected_native.native_revision != native_old.native_revision
    assert new.old_resident_epoch == initial[0].resident_epoch
    assert new.old_native_session_id == old_session
    assert new.old_logout_source_ref == logout.source_ref
    assert new.initial_receipt_ref == _revision(asdict(initial[0]))
    assert new.historical_composite_ref == _revision(asdict(historical))
    assert new.paper_revision != historical.paper_revision
    assert new.paper_revision != new.native_revision
    assert new.composite_revision not in (
        historical.composite_revision, new.paper_revision, new.native_revision,
    )
    assert new.paper_actor_uuid == ACTORS[0]
    assert new.paper_tick == 25
    assert new.paper_tick > historical.paper_tick
    assert new.paper_log_sha256 != historical.paper_log_sha256
    assert new.paper_quit_line < new.b_present_line < new.paper_rejoin_line < new.paper_present_line
    assert new.rejoin_paper_revision.startswith("sha256:")
    assert new.b_continuity_revision.startswith("sha256:")
    assert (f.bridge.sessions["B"], f.owners["B"].current_worldbody_observation,
            f.cognitive.current_scope("B")) == b_before
    assert (initial[0].native_session_id, historical.native_session_id) == (
        old_session, old_session,
    )
    assert initial[0].paper_tick == 10
    assert historical.paper_tick == 20
    assert files(f) == files_before
    assert all(
        (o.retained, o.intent, o.pattern_registry, o.skills, o.pending_questions)
        == cognition_before[sid]
        for sid, o in f.owners.items()
    )


def test_old_receipts_remain_history_not_current_source(rejoined):
    f, initial, old_native, old, _, _, _ = rejoined
    new = build(rejoined)
    with pytest.raises(CompositeSourceHold):
        build_current_composite_source(
            bridge=f.bridge, self_id="A", native_revision=old_native,
            initial_receipts=initial,
        )
    with pytest.raises(RejoinCompositeHold):
        build_rejoined_composite_source(
            bridge=f.bridge, initial_receipts=initial,
            historical_composite=replace(old, self_id="B"),
        )
    assert old.composite_revision != new.composite_revision


@pytest.mark.parametrize("fault", [
    "old_native_session", "old_native_request", "old_native_sequence",
    "old_paper_tick", "old_paper_digest", "old_paper_boot", "old_composite_revision",
    "old_initial_ref", "old_paper_actor", "old_paper_session", "old_paper_pid",
    "old_paper_log_prefix",
])
def test_historical_tampering_never_issues_current(rejoined, fault):
    f, initial, _, old, _, _, _ = rejoined
    change = {
        "old_native_session": {"native_session_id": "foreign"},
        "old_native_request": {"native_request_id": "forged"},
        "old_native_sequence": {"native_sequence": old.native_sequence + 1},
        "old_paper_tick": {"paper_tick": old.paper_tick + 1},
        "old_paper_digest": {"paper_log_sha256": "f" * 64},
        "old_paper_boot": {"paper_boot_id": "wrong-boot"},
        "old_composite_revision": {"composite_revision": "sha256:" + "f" * 64},
        "old_initial_ref": {"initial_receipt_ref": "sha256:" + "f" * 64},
        "old_paper_actor": {"paper_actor_uuid": ACTORS[1]},
        "old_paper_session": {"paper_session_id": "foreign-paper"},
        "old_paper_pid": {"paper_pid": old.paper_pid + 1},
        "old_paper_log_prefix": {"paper_tick_ref": old.paper_tick_ref.replace(BOOT, "foreign")},
    }[fault]
    with pytest.raises(RejoinCompositeHold):
        build_rejoined_composite_source(
            bridge=f.bridge, initial_receipts=initial,
            historical_composite=replace(old, **change),
        )


@pytest.mark.parametrize("fault", [
    "pending", "owner", "world_epoch", "resident_epoch", "native_session",
    "native_request", "native_sequence", "native_provenance", "b_native_session",
    "paper_pid", "paper_session", "paper_boot", "paper_nonce", "paper_actor",
    "paper_quit", "paper_rejoin", "paper_present", "b_present", "b_quit",
    "owner_logout", "forbidden_session",
])
def test_rejoined_composite_fails_closed_on_current_source_changes(
    rejoined, monkeypatch, fault,
):
    f, initial, _, old, old_session, _, _ = rejoined
    bridge, paper = f.bridge, f.paper
    if fault == "pending":
        bridge._fresh_native_pending = {"A": object()}
    elif fault == "owner":
        bridge.owners["A"] = f.owners["B"]
    elif fault in ("world_epoch", "resident_epoch"):
        state = f.cognitive._states["A"]
        if fault == "world_epoch":
            state.world_epoch += 1
        else:
            state.epoch += 1
    elif fault == "native_session":
        bridge.sessions["A"]._started = replace(
            bridge.sessions["A"].started, session_id=old_session,
        )
    elif fault in ("native_request", "native_sequence", "native_provenance"):
        probe = bridge.last_login_observations["A"]
        if fault == "native_request":
            altered = replace(probe, request_id="foreign-request")
        elif fault == "native_sequence":
            altered = replace(probe, seq=probe.seq + 1)
        else:
            # Provenance is derived from session_id/seq, not a dataclass field.
            altered = replace(probe, session_id="foreign-source-session")
        bridge.last_login_observations["A"] = altered
    elif fault == "b_native_session":
        bridge.sessions["B"]._started = replace(
            bridge.sessions["B"].started, session_id="foreign-b",
        )
    elif fault == "paper_pid":
        original = paper._assert_owned
        monkeypatch.setattr(
            paper, "_assert_owned", lambda: SimpleNamespace(pid=original().pid + 1),
        )
    elif fault == "paper_session":
        paper._session_id = "different-paper"
    elif fault in ("paper_boot", "paper_nonce"):
        tick = paper.tick_readback(paper.owned_session_id)
        name = BOOT if fault == "paper_boot" else "88888888"
        monkeypatch.setattr(
            paper, "tick_readback", lambda _: replace(
                tick, source_ref=tick.source_ref.replace(name, "foreign"),
            ),
        )
    elif fault == "owner_logout":
        proof, scope, owner, login, probe = bridge._b_np1b_retired_login["A"]
        bridge._b_np1b_retired_login["A"] = (
            replace(proof, native_session_id="other-session"),
            scope, owner, login, probe,
        )
    elif fault == "forbidden_session":
        bridge.forbidden_native_sessions = frozenset()
    else:
        contents = paper._log_path.read_text()
        if fault == "paper_actor":
            contents = contents.replace(
                f"actor={ACTORS[0]} name=RelayA",
                f"actor={ACTORS[1]} name=RelayA",
            )
        elif fault == "paper_quit":
            contents = contents.replace(
                f"P0D_RESIDENT event=QUIT boot={PRESENCE} tick=21", "P0D_RESIDENT event=MOVE boot="
                + PRESENCE + " tick=21",
            )
        elif fault == "paper_rejoin":
            contents = contents.replace(
                f"P0D_RESIDENT event=JOIN boot={PRESENCE} tick=23",
                f"P0D_RESIDENT event=MOVE boot={PRESENCE} tick=23",
            )
        elif fault == "paper_present":
            contents = contents.replace(
                f"P0D_RESIDENT event=PRESENT boot={PRESENCE} tick=24",
                f"P0D_RESIDENT event=QUIT boot={PRESENCE} tick=24",
            )
        elif fault == "b_present":
            contents = contents.replace(
                f"P0D_RESIDENT event=PRESENT boot={PRESENCE} tick=22",
                f"P0D_RESIDENT event=QUIT boot={PRESENCE} tick=22",
            )
        else:
            contents = contents.replace(
                f"P0D_RESIDENT event=PRESENT boot={PRESENCE} tick=22",
                f"P0D_RESIDENT event=QUIT boot={PRESENCE} tick=22",
            )
        paper._log_path.write_text(contents)
    with pytest.raises(RejoinCompositeHold):
        build_rejoined_composite_source(
            bridge=bridge, initial_receipts=initial, historical_composite=old,
        )


@pytest.mark.parametrize("fault", [
    "owned_log_after_provisional", "owner_scope_during_paper",
    "native_probe_during_paper", "paper_process_during_paper",
])
def test_final_lock_revalidates_original_sources(rejoined, monkeypatch, fault):
    f, initial, _, old, _, _, _ = rejoined
    paper = f.paper
    bridge = f.bridge
    read = paper.read_owned_log
    count = [0]

    def changing(session):
        count[0] += 1
        data = read(session)
        if count[0] >= 4:
            if fault == "owned_log_after_provisional":
                return data + b"post-check growth\n"
            if fault == "owner_scope_during_paper":
                f.cognitive._states["A"].epoch += 1
            if fault == "native_probe_during_paper":
                bridge.last_login_evidence["A"] = replace(
                    bridge.last_login_evidence["A"], observation_ref="foreign",
                )
            if fault == "paper_process_during_paper":
                old_assert = paper._assert_owned
                monkeypatch.setattr(paper, "_assert_owned", lambda: SimpleNamespace(pid=old_assert().pid + 1))
        return data

    monkeypatch.setattr(paper, "read_owned_log", changing)
    with pytest.raises(RejoinCompositeHold):
        build_rejoined_composite_source(
            bridge=bridge, initial_receipts=initial, historical_composite=old,
        )


def test_logout_fence_never_reissues_current_receipt(rejoined):
    f, initial, _, historical, _, _, _ = rejoined
    new = build(rejoined)
    asyncio.run(f.bridge.logout("A"))
    with pytest.raises(RejoinCompositeHold):
        build_rejoined_composite_source(
            bridge=f.bridge, initial_receipts=initial,
            historical_composite=historical,
        )
    assert new.old_native_session_id == historical.native_session_id


def test_paper_source_must_be_new_ack_after_rejoin(rejoined, monkeypatch):
    f, initial, _, old, _, _, _ = rejoined
    tick = f.paper.tick_readback(f.paper.owned_session_id)
    stale = PaperTickReceipt(
        tick.server_session_id, old.paper_tick, tick.source_ref,
    )
    monkeypatch.setattr(f.paper, "tick_readback", lambda _: stale)
    with pytest.raises(RejoinCompositeHold):
        build(rejoined)
