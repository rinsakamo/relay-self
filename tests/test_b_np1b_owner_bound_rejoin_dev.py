"""Original Bridge logout/reJOIN to Paper verifier, synthetic CPU/offline only."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace

import pytest

from relay_self.b_np1b_current_composite_source_dev import build_current_composite_source
from relay_self.b_np1b_initial_source_dev import _revision
from relay_self.b_np1b_owner_bound_rejoin_dev import (
    OwnerBoundRejoinHold,
    build_owner_bound_rejoin_paper,
)
from relay_self.owned_paper_world_dev import PaperTickReceipt
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_initial_source_dev import ACTORS, BOOT, PRESENCE, WORLD


def _paper_line(event, tick, sid):
    actor = ACTORS[0] if sid == "A" else ACTORS[1]
    return (
        f"P0D_RESIDENT event={event} boot={PRESENCE} tick={tick} "
        f"world={WORLD} actor={actor} name=Relay{sid} "
        "x=0 y=64 z=0 source=PAPER_MAIN_THREAD\n"
    )


@pytest.fixture
def rejoined(request, monkeypatch):
    # Import the existing fixture by alias, without redefining its Python name.
    assert current_fixture is not None
    f, initial, native, _ = request.getfixturevalue("current_fixture")
    old_composite = build_current_composite_source(
        bridge=f.bridge, self_id="A", native_revision=native, initial_receipts=initial,
    )
    old_a_session = f.bridge.sessions["A"].started.session_id
    other = (
        f.bridge.sessions["B"],
        f.owners["B"].current_worldbody_observation,
        f.cognitive.current_scope("B"),
    )
    async def cycle():
        logout = await f.bridge.logout("A")
        await f.bridge.login("A")
        return logout
    logout = asyncio.run(cycle())
    session = f.paper.owned_session_id
    nonce = "88888888-8888-4888-8888-888888888888"
    with f.paper._log_path.open("a") as out:
        out.write(_paper_line("QUIT", 21, "A"))
        out.write(_paper_line("PRESENT", 22, "B"))
        out.write(_paper_line("JOIN", 23, "A"))
        out.write(_paper_line("PRESENT", 24, "A"))
        out.write(
            f"P0D_TICK_ACK nonce={nonce} boot={BOOT} session={session} "
            f"world={WORLD} tick=25 source=PAPER_MAIN_THREAD\n"
        )
    tick = PaperTickReceipt(
        session, 25, f"paper-main-thread:p0d:{BOOT}:{nonce}:sha256:" + "c" * 64,
    )
    monkeypatch.setattr(f.paper, "tick_readback", lambda _: tick)
    return f, initial, native, old_composite, old_a_session, logout, other


def test_original_bridge_rejoin_is_bound_to_owned_paper(rejoined):
    f, initial, _, old_composite, old_a_session, logout, other = rejoined
    before_file = {
        str(p): p.read_bytes()
        for o in f.owners.values()
        for p in o.files.self_root.rglob("*") if p.is_file()
    }
    evidence = build_owner_bound_rejoin_paper(
        bridge=f.bridge, initial_receipts=initial,
    )
    assert evidence == build_owner_bound_rejoin_paper(
        bridge=f.bridge, initial_receipts=initial,
    )
    assert evidence.old_native_session_id == old_a_session
    assert evidence.old_logout_source_ref == logout.source_ref
    assert evidence.native_session_id == f.bridge.sessions["A"].started.session_id
    assert evidence.native_session_id != old_a_session
    assert evidence.resident_epoch > evidence.old_resident_epoch
    assert evidence.paper_actor_uuid == ACTORS[0]
    assert evidence.paper_tick == 25
    assert (
        evidence.paper_evidence.a_quit_line
        < evidence.paper_evidence.b_present_line
        < evidence.paper_evidence.a_join_line
        < evidence.paper_evidence.a_present_line
    )
    assert (initial[0].native_session_id, old_composite.native_session_id) == (
        old_a_session, old_a_session,
    )
    assert (
        f.bridge.sessions["B"],
        f.owners["B"].current_worldbody_observation,
        f.cognitive.current_scope("B"),
    ) == other
    assert {
        str(p): p.read_bytes()
        for o in f.owners.values()
        for p in o.files.self_root.rglob("*") if p.is_file()
    } == before_file


@pytest.mark.parametrize("fault", [
    "old_logout", "old_owner", "new_login", "native_probe", "b_session",
    "paper_quit", "a_present", "b_quit", "actor", "tick_ack", "paper_session",
    "old_receipt", "forged_old_request", "log_growth", "native_during_paper", "paper_pid",
])
def test_owner_bound_rejoin_rejects_foreign_and_changing_sources(rejoined, monkeypatch, fault):
    f, initial, _, _, old_a_session, logout, _ = rejoined
    bridge = f.bridge
    paper = f.paper
    if fault == "old_logout":
        proof, scope, owner, prior_login, prior_probe = bridge._b_np1b_retired_login["A"]
        bridge._b_np1b_retired_login["A"] = (
            replace(proof, native_session_id="foreign-native"), scope, owner,
            prior_login, prior_probe,
        )
    elif fault == "old_owner":
        proof, scope, owner, prior_login, prior_probe = bridge._b_np1b_retired_login["A"]
        bridge._b_np1b_retired_login["A"] = (
            proof, scope, bridge.owners["B"], prior_login, prior_probe,
        )
    elif fault == "new_login":
        bridge.last_login_evidence["A"] = replace(
            bridge.last_login_evidence["A"], native_session_id=old_a_session,
        )
    elif fault == "native_probe":
        bridge.last_login_observations["A"] = replace(
            bridge.last_login_observations["A"], request_id=initial[0].native_request_id,
        )
    elif fault == "b_session":
        session_b = bridge.sessions["B"]
        session_b._started = replace(session_b.started, session_id="foreign-b")
    elif fault in ("paper_quit", "a_present", "b_quit", "actor", "tick_ack"):
        data = paper._log_path.read_text()
        if fault == "paper_quit":
            data = data.replace(_paper_line("QUIT", 21, "A"), "")
        elif fault == "a_present":
            data = data.replace(_paper_line("PRESENT", 24, "A"), "")
        elif fault == "b_quit":
            data = data.replace(_paper_line("PRESENT", 22, "B"), _paper_line("QUIT", 22, "B"))
        elif fault == "actor":
            data = data.replace(_paper_line("JOIN", 23, "A"), _paper_line("JOIN", 23, "B"))
        else:
            data = data.replace("P0D_TICK_ACK nonce=88888888-", "BAD_TICK_ACK nonce=88888888-")
        paper._log_path.write_text(data)
    elif fault == "paper_session":
        paper._session_id = "foreign-paper"
    elif fault == "old_receipt":
        initial = (replace(initial[0], native_session_id="foreign"), initial[1])
    elif fault == "forged_old_request":
        forged = replace(initial[0], native_request_id="forged-original-request")
        values = asdict(forged)
        keys = (
            "self_id", "owner_identity", "resident_epoch", "world_id", "branch_id",
            "world_epoch", "native_session_id", "native_request_id", "native_sequence",
            "native_source_ref", "native_world_time",
        )
        forged = replace(forged, native_revision=_revision({k: values[k] for k in keys}))
        initial = (forged, initial[1])
    elif fault == "log_growth":
        read = paper.read_owned_log
        reads = [0]
        def changing(session):
            reads[0] += 1
            value = read(session)
            return value + b"foreign-growth\n" if reads[0] > 1 else value
        monkeypatch.setattr(paper, "read_owned_log", changing)
    elif fault == "native_during_paper":
        read = paper.read_owned_log
        def changing_native(session):
            result = read(session)
            bridge.last_login_evidence["A"] = replace(
                bridge.last_login_evidence["A"], observation_ref="stale-request",
            )
            return result
        monkeypatch.setattr(paper, "read_owned_log", changing_native)
    else:
        owned = paper._assert_owned
        def foreign_process():
            from types import SimpleNamespace
            return SimpleNamespace(pid=owned().pid + 1)
        monkeypatch.setattr(paper, "_assert_owned", foreign_process)
    with pytest.raises(OwnerBoundRejoinHold):
        build_owner_bound_rejoin_paper(bridge=bridge, initial_receipts=initial)
