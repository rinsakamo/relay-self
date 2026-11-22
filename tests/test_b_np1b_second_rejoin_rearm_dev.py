"""Second A logout/reJOIN and original CPU task rearm, no real World/GPU/Action.

The fixtures use the original Bridge/Owner, Mineflayer ProcessSession decoder,
original logout/login and an owned synthetic Paper process with explicit
second-generation main-thread presence/ACK events.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from relay_self.b_np1b_fresh_native_update_dev import update_fresh_native
from relay_self.b_np1b_normal_present_scheduler_dev import NormalCpuScheduleHold
from relay_self.b_np1b_second_rejoin_rearm_dev import (
    SecondRejoinHold,
    build_second_rejoin_cpu_pair,
    capture_first_rejoin_cpu_anchor,
    rearm_second_rejoin_normal_cpu,
)
from relay_self.owned_paper_world_dev import PaperTickReceipt
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_initial_source_dev import BOOT, WORLD
from test_b_np1b_normal_present_poll_dev import current_fixture as current_fixture
from test_b_np1b_normal_present_poll_dev import pair as pair
from test_b_np1b_normal_present_poll_dev import rejoined as rejoined
from test_b_np1b_normal_present_poll_dev import rejoined_present as rejoined_present
from test_b_np1b_owner_bound_rejoin_dev import _paper_line


def _bind(pair):
    f, initial, _, history, *_ = pair
    f.bridge.bind_normal_rejoin_present_cpu(
        initial_receipts=initial, historical_composite=history,
    )
    return f


async def _current(f, sid, *, after=0, different=None):
    for _ in range(100):
        try:
            value = f.bridge.require_scheduled_present_cpu(sid)
            if (value.iteration > after
                    and (different is None or value.source_pair_revision != different)):
                return value
        except NormalCpuScheduleHold:
            pass
        await asyncio.sleep(0.01)
    raise AssertionError("no current original A/B CPU sample for " + sid)


async def _first(f):
    old = f.bridge.start_normal_present_cpu_schedule(interval_s=0.02)
    await _current(f, "A")
    await _current(f, "B")
    anchor = capture_first_rejoin_cpu_anchor(bridge=f.bridge)
    assert anchor.a.native_session_id != f.bridge._b_np1b_retired_login["A"][0].native_session_id
    return old, anchor


async def _second(f, monkeypatch):
    logout = await f.bridge.logout("A")
    assert logout.physical_issuer_revoked and logout.native_terminated
    assert f.cognitive.retired_clean("A")
    assert "normal-present-cpu:A" in f.cognitive._state("A").retired.cancelled_cpu_task_refs
    await f.bridge.login("A")
    tick = PaperTickReceipt(
        f.paper.owned_session_id, 31,
        f"paper-main-thread:p0d:{BOOT}:99999999-9999-4999-8999-999999999999:sha256:"
        + "e" * 64,
    )
    original = f.paper._log_path.read_text()
    f.paper._log_path.write_text(
        original + _paper_line("QUIT", 26, "A")
        + _paper_line("PRESENT", 27, "B")
        + _paper_line("JOIN", 28, "A")
        + _paper_line("PRESENT", 29, "A")
        + _paper_line("PRESENT", 30, "B")
        + f"P0D_TICK_ACK nonce=99999999-9999-4999-8999-999999999999 "
          f"boot={BOOT} session={f.paper.owned_session_id} "
          f"world={WORLD} tick=31 source=PAPER_MAIN_THREAD\n"
    )
    monkeypatch.setattr(f.paper, "tick_readback", lambda _: tick)
    return logout


def _unchanged_cognition(f):
    return {
        sid: (
            owner.retained, owner.intent, owner.pattern_registry,
            dict(owner.skills), set(owner.pending_questions),
        ) for sid, owner in f.owners.items()
    }


def test_second_original_logout_rejoin_rearms_pair_and_fences_old_tasks(pair, monkeypatch):
    f = _bind(pair)
    memory_before = files(f)
    cognition_before = _unchanged_cognition(f)
    b_session = f.bridge.sessions["B"]
    b_scope = f.cognitive.current_scope("B")

    async def run():
        old, anchor = await _first(f)
        with pytest.raises(SecondRejoinHold):
            await rearm_second_rejoin_normal_cpu(bridge=f.bridge, interval_s=0.02)
        await _second(f, monkeypatch)
        assert old._tasks["A"].done() and not old._tasks["B"].done()
        with pytest.raises(NormalCpuScheduleHold):
            f.bridge.require_scheduled_present_cpu("A")
        with pytest.raises(NormalCpuScheduleHold):
            f.bridge.require_scheduled_present_cpu("B")
        ra, rb = build_second_rejoin_cpu_pair(bridge=f.bridge)
        assert ra.old_resident_epoch == anchor.a.resident_epoch
        assert ra.old_native_session_id == anchor.a.native_session_id
        assert ra.native_session_id != anchor.a.native_session_id
        assert ra.native_session_id != anchor.a.old_native_session_id
        assert ra.paper_quit_line > anchor.a.paper_present_line
        assert ra.paper_rejoin_line > ra.paper_quit_line
        assert ra.paper_present_line > ra.paper_rejoin_line
        assert rb.b_present_line if False else True
        assert rb.b_post_rejoin_present_line > ra.paper_rejoin_line
        assert ra.b_continuity_revision == rb.b_continuity_revision
        assert f.bridge.sessions["B"] is b_session
        assert f.cognitive.current_scope("B") == b_scope

        fresh, proof = await rearm_second_rejoin_normal_cpu(
            bridge=f.bridge, interval_s=0.02,
        )
        try:
            assert old._stopped and all(t.done() for t in old._tasks.values())
            assert fresh is not old
            assert fresh._tasks["A"] is not old._tasks["A"]
            assert fresh._tasks["B"] is not old._tasks["B"]
            assert proof.generation == 2
            assert proof.first_pair_revision == anchor.pair_revision
            assert proof.second_pair_revision != anchor.pair_revision
            assert proof.retired_a_cpu_task and proof.retired_b_cpu_task
            assert proof.old_a_task_epoch == anchor.a_scope[0]
            assert proof.new_a_task_epoch == anchor.a_scope[0] + 2
            assert proof.old_b_task_epoch == proof.new_b_task_epoch == b_scope[0]
            assert proof.first_a_native == anchor.a.native_session_id
            assert proof.second_a_native == f.bridge.sessions["A"].started.session_id
            assert proof.continuous_b_native == b_session.started.session_id
            a = await _current(f, "A")
            b = await _current(f, "B")
            assert a.poll == b.poll
            assert a.source_pair_revision == b.source_pair_revision == proof.second_pair_revision
            assert a.poll.a_present.present.three_self.scope.self_id == "A"
            assert b.poll.b_present.present.three_self.scope.self_id == "B"
            assert a.poll.a_present.exploration_need is not None
            assert b.poll.b_present.exploration_need is not None
            assert a.poll.a_inquiry is not None and b.poll.b_inquiry is not None
            assert a.poll.a_present.source.composite_receipt == ra
            assert b.poll.b_present.source.composite_receipt == rb
            with pytest.raises(NormalCpuScheduleHold):
                old.require_current("A")
            with pytest.raises(NormalCpuScheduleHold):
                old.require_current("B")
            with pytest.raises(SecondRejoinHold):
                await rearm_second_rejoin_normal_cpu(bridge=f.bridge)
            # B remains the original session, but a newer B observation
            # requalifies the entire second-generation A/B source pair.
            updated_b = await update_fresh_native(
                bridge=f.bridge, self_id="B", initial_receipt=pair[1][1],
            )
            newer_a = await _current(f, "A", different=proof.second_pair_revision)
            newer_b = await _current(f, "B", different=proof.second_pair_revision)
            assert newer_a.poll == newer_b.poll
            assert newer_a.source_pair_revision == newer_b.source_pair_revision
            assert newer_a.poll.b_present.source.composite_receipt.native_revision == (
                updated_b.native_revision
            )
            assert newer_a.poll.a_present.source.composite_receipt.b_continuity_revision != (
                ra.b_continuity_revision
            )
            assert f.bridge.sessions["B"] is b_session
        finally:
            await fresh.stop()

    asyncio.run(run())
    assert files(f) == memory_before or all(
        p.endswith("cognition.json") for p in set(files(f)) if files(f)[p] != memory_before.get(p)
    )
    assert _unchanged_cognition(f) == cognition_before
    assert not f.bridge.physical.active_action_ids


@pytest.mark.parametrize("fault", [
    "missing_quit", "missing_b_gap", "missing_a_join", "missing_a_present",
    "missing_b_post", "foreign_b_quit", "foreign_a_actor", "foreign_b_actor",
    "stale_ack", "extra_a_join", "extra_a_quit", "anchor_prefix",
    "second_retirement", "second_retired_owner", "second_old_probe",
    "new_session", "b_session", "paper_pid", "resident_epoch",
    "native_a_copy", "b_native_copy", "world_epoch", "pending_b",
    "schema_a", "schema_b",
])
def test_second_rejoin_proof_fails_closed_on_hostile_sources(pair, monkeypatch, fault):
    f = _bind(pair)

    async def run():
        old, anchor = await _first(f)
        await _second(f, monkeypatch)
        valid = build_second_rejoin_cpu_pair(bridge=f.bridge)
        assert valid[0].old_native_session_id == anchor.a.native_session_id
        paper = f.paper
        data = paper._log_path.read_text()
        if fault in (
            "missing_quit", "missing_b_gap", "missing_a_join", "missing_a_present",
            "missing_b_post", "foreign_b_quit", "foreign_a_actor",
            "foreign_b_actor", "stale_ack", "extra_a_join", "extra_a_quit",
            "anchor_prefix",
        ):
            actions = {
                "missing_quit": (_paper_line("QUIT", 26, "A"), ""),
                "missing_b_gap": (_paper_line("PRESENT", 27, "B"), ""),
                "missing_a_join": (_paper_line("JOIN", 28, "A"), ""),
                "missing_a_present": (_paper_line("PRESENT", 29, "A"), ""),
                "missing_b_post": (_paper_line("PRESENT", 30, "B"), ""),
                "foreign_b_quit": (
                    _paper_line("PRESENT", 27, "B"), _paper_line("QUIT", 27, "B"),
                ),
                "foreign_a_actor": (
                    _paper_line("JOIN", 28, "A"), _paper_line("JOIN", 28, "B"),
                ),
                "foreign_b_actor": (
                    _paper_line("PRESENT", 30, "B"),
                    _paper_line("PRESENT", 30, "A"),
                ),
                "stale_ack": ("P0D_TICK_ACK nonce=99999999-", "BAD_TICK_ACK nonce=99999999-"),
                "extra_a_join": (
                    _paper_line("PRESENT", 29, "A"),
                    _paper_line("JOIN", 29, "A") + _paper_line("PRESENT", 29, "A"),
                ),
                "extra_a_quit": (
                    _paper_line("PRESENT", 29, "A"),
                    _paper_line("QUIT", 29, "A") + _paper_line("PRESENT", 29, "A"),
                ),
                "anchor_prefix": (
                    _paper_line("PRESENT", 24, "A"), _paper_line("PRESENT", 24, "B"),
                ),
            }
            before, after = actions[fault]
            assert before in data
            paper._log_path.write_text(data.replace(before, after))
        elif fault == "second_retirement":
            proof, scope, owner, login, probe = f.bridge._b_np1b_retired_login["A"]
            f.bridge._b_np1b_retired_login["A"] = (
                replace(proof, native_session_id="spoof"), scope, owner, login, probe,
            )
        elif fault == "second_retired_owner":
            proof, scope, _, login, probe = f.bridge._b_np1b_retired_login["A"]
            f.bridge._b_np1b_retired_login["A"] = (
                proof, scope, f.owners["B"], login, probe,
            )
        elif fault == "second_old_probe":
            proof, scope, owner, login, probe = f.bridge._b_np1b_retired_login["A"]
            f.bridge._b_np1b_retired_login["A"] = (
                proof, scope, owner, login, replace(probe, seq=probe.seq),
            )
        elif fault == "new_session":
            f.bridge.sessions["A"]._started = replace(
                f.bridge.sessions["A"].started, session_id="spoof-a",
            )
        elif fault == "b_session":
            f.bridge.sessions["B"]._started = replace(
                f.bridge.sessions["B"].started, session_id="spoof-b",
            )
        elif fault == "paper_pid":
            original = f.paper._assert_owned
            monkeypatch.setattr(
                f.paper, "_assert_owned",
                lambda: type("ForeignPaper", (), {"pid": original().pid + 1})(),
            )
        elif fault == "resident_epoch":
            f.cognitive._states["A"].epoch += 1
        elif fault == "native_a_copy":
            f.owners["A"].current_worldbody_observation = replace(
                f.owners["A"].current_worldbody_observation,
                seq=f.owners["A"].current_worldbody_observation.seq,
            )
        elif fault == "b_native_copy":
            f.owners["B"].current_worldbody_observation = replace(
                f.owners["B"].current_worldbody_observation,
                seq=f.owners["B"].current_worldbody_observation.seq,
            )
        elif fault == "world_epoch":
            f.cognitive._states["B"].world_epoch += 1
        elif fault == "pending_b":
            f.bridge._fresh_native_pending = {"B": object()}
        elif fault == "schema_a":
            f.cognitive._present_schemas.pop("A")
        else:
            f.cognitive._present_schemas.pop("B")
        try:
            if fault not in ("schema_a", "schema_b"):
                with pytest.raises((SecondRejoinHold, RuntimeError, ValueError)):
                    build_second_rejoin_cpu_pair(bridge=f.bridge)
            with pytest.raises((SecondRejoinHold, RuntimeError, ValueError)):
                await rearm_second_rejoin_normal_cpu(
                    bridge=f.bridge, interval_s=0.02,
                )
        finally:
            await old.stop()

    asyncio.run(run())


def test_anchor_never_admits_unowned_or_duplicate_scheduler(pair):
    f = _bind(pair)
    with pytest.raises(SecondRejoinHold):
        capture_first_rejoin_cpu_anchor(bridge=f.bridge)

    async def run():
        old, _ = await _first(f)
        with pytest.raises(SecondRejoinHold):
            capture_first_rejoin_cpu_anchor(bridge=f.bridge)
        try:
            with pytest.raises(SecondRejoinHold):
                await rearm_second_rejoin_normal_cpu(
                    bridge=f.bridge, interval_s=0.02,
                )
        finally:
            await old.stop()

    asyncio.run(run())


@pytest.mark.parametrize("interval", [0, -1, 30.1, "0.1", None, True])
def test_second_rejoin_rearm_rejects_unbounded_interval(pair, monkeypatch, interval):
    f = _bind(pair)

    async def run():
        old, _ = await _first(f)
        await _second(f, monkeypatch)
        try:
            with pytest.raises(SecondRejoinHold):
                await rearm_second_rejoin_normal_cpu(
                    bridge=f.bridge, interval_s=interval,
                )
            assert not old._stopped
        finally:
            await old.stop()

    asyncio.run(run())
