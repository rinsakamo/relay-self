"""Stage28c2b DEV: bounded original Paper A/B presence is event-driven.

All Paper/native sources in these tests are synthetic. In particular no
test's 40-tick timer is accepted as proof of an actual PRESENT.
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.owned_resident_physical_bridge_dev import (
    OwnedResidentPhysicalBridge,
)
from relay_self.stage28_cognitive_recovery_gate_dev import Stage28ForkPaperEpoch
from relay_self.stage28c2b_bounded_paper_presence_dev import (
    Stage28PresenceWaitHold,
    await_both_recovered_paper_present,
)
from relay_self.world_resident_lifecycle_dev import (
    NativeLoginEvidence,
    WorldLifetime,
    WorldResidentLifecycle,
)


def _booted(tmp_path: Path):
    world_id, fork_id = str(uuid.uuid4()), "fork-new"
    session_id = "paper-owned-" + str(uuid.uuid4())
    plugin_boot = str(uuid.uuid4())
    tick_boot = str(uuid.uuid4())
    actors = {"A": str(uuid.uuid4()), "B": str(uuid.uuid4())}
    paper = object.__new__(OwnedPaperWorld)
    paper.world_id, paper.branch_id = world_id, fork_id
    paper._session_id = session_id
    paper._process = SimpleNamespace(pid=9005, poll=lambda: None)
    paper._uncertain = False
    paper._log_path = tmp_path / "owned-paper.log"
    paper._log_path.write_text(
        f"P0D_RESIDENT_READY boot={plugin_boot} "
        "source=PAPER_MAIN_THREAD version=1\n",
        encoding="utf-8",
    )
    epoch = Stage28ForkPaperEpoch(
        "g-000000000000", world_id, "original-source", 221,
        fork_id, "c" * 64, session_id, tick_boot, 1, 2,
        f"paper-main-thread:p0d:{tick_boot}:nonce:sha256:" + "a" * 64,
        9005, ("retired-A", "retired-B"),
    )
    life = WorldResidentLifecycle(
        world=WorldLifetime(world_id, fork_id, session_id, 1, 2),
        persisted_self_refs={"A": "retained:A", "B": "retained:B"},
        independent_native_world_clock=True,
    )
    evidence = {}
    sessions = {}
    for sid in ("A", "B"):
        ticket = life.begin_login(sid)
        native = NativeLoginEvidence(
            sid, ticket.login_seq, world_id, fork_id, session_id, 1,
            "new-native-" + sid, 0, "probe:" + sid,
            True, True, True, True, True,
        )
        life.complete_login(ticket, native)
        evidence[sid] = native
        sessions[sid] = SimpleNamespace(
            process_returncode=None,
            started=SimpleNamespace(session_id=native.native_session_id),
        )
    bridge = object.__new__(OwnedResidentPhysicalBridge)
    bridge.paper = paper
    bridge.inference_lane = None
    bridge.lifecycle = life
    bridge.physical = SimpleNamespace(
        observation_only=True, active_action_ids=(),
    )
    bridge.sessions = sessions
    bridge.last_login_evidence = evidence
    bridge.configs = {
        sid: SimpleNamespace(username="Relay" + sid) for sid in ("A", "B")
    }

    def event(sid: str, action: str, tick: int, *, actor: str | None = None):
        player_id = actor or actors[sid]
        return (
            f"P0D_RESIDENT event={action} boot={plugin_boot} tick={tick} "
            f"world={world_id} actor={player_id} name=Relay{sid} "
            "x=200.5 y=111.0 z=421.5 source=PAPER_MAIN_THREAD\n"
        )

    def append(*rows):
        with paper._log_path.open("a", encoding="utf-8") as handle:
            handle.writelines(rows)

    return paper, bridge, epoch, event, append


def test_both_present_after_delayed_b_succeeds_from_actual_paper_events(tmp_path):
    paper, bridge, boot, event, append = _booted(tmp_path)
    append(event("A", "JOIN", 17), event("B", "JOIN", 30))
    async def trial():
        async def delayed_witness():
            await asyncio.sleep(0.06)
            append(event("A", "PRESENT", 60))
            await asyncio.sleep(0.06)
            append(event("B", "PRESENT", 70))
        witness = asyncio.create_task(delayed_witness())
        result = await await_both_recovered_paper_present(
            bridge=bridge, paper=paper, boot=boot,
            timeout_seconds=1.5, poll_seconds=0.02,
        )
        await witness
        return result
    receipt = asyncio.run(trial())
    assert receipt.b_join_tick == 30
    assert receipt.a_join_tick == 17
    assert receipt.a_presence_tick == 60
    assert receipt.b_presence_tick == 70
    assert receipt.polling_reads >= 3
    assert receipt.both_present_source_verified
    assert not receipt.owner_worldbody_accepted
    assert not receipt.physical_action_issue_authorized
    assert receipt.paper_pid == 9005


def test_missing_b_present_is_hold_not_inferred_from_elapsed_time(tmp_path):
    paper, bridge, boot, event, append = _booted(tmp_path)
    append(event("A", "JOIN", 17), event("B", "JOIN", 30),
           event("A", "PRESENT", 60))
    with pytest.raises(Stage28PresenceWaitHold, match="timed out"):
        asyncio.run(await_both_recovered_paper_present(
            bridge=bridge, paper=paper, boot=boot,
            timeout_seconds=1.0, poll_seconds=0.05,
        ))


@pytest.mark.parametrize("failure", [
    "b-quit", "duplicate-b-join", "duplicate-actor",
    "paper-source-change", "foreign-world", "untrusted-boot",
    "b-present-before-join", "stale-native", "physical-authority",
    "tick-budget", "malformed-event",
])
def test_presence_wait_rejects_missing_foreign_or_retired_paper_source(
    tmp_path, failure,
):
    paper, bridge, boot, event, append = _booted(tmp_path)
    append(event("A", "JOIN", 17), event("B", "JOIN", 30))
    if failure == "b-quit":
        append(event("B", "QUIT", 33), event("A", "PRESENT", 60))
    elif failure == "duplicate-b-join":
        append(event("B", "JOIN", 34), event("A", "PRESENT", 60))
    elif failure == "duplicate-actor":
        current_a = event("A", "JOIN", 17)
        actor_id = current_a.split(" actor=")[1].split()[0]
        # Rewrite with the same A actor UUID for B in a coherent stream.
        paper._log_path.write_text(
            paper._log_path.read_text().split("P0D_RESIDENT event=")[0]
            + event("A", "JOIN", 17, actor=actor_id)
            + event("B", "JOIN", 30, actor=actor_id)
            + event("A", "PRESENT", 60, actor=actor_id)
            + event("B", "PRESENT", 70, actor=actor_id)
        )
    elif failure == "paper-source-change":
        paper._session_id = "paper-owned-different"
    elif failure == "foreign-world":
        wrong = str(uuid.uuid4())
        paper._log_path.write_text(
            paper._log_path.read_text().replace(
                f"world={boot.source_world_id}", f"world={wrong}",
            )
        )
        append(event("A", "PRESENT", 60), event("B", "PRESENT", 70))
    elif failure == "untrusted-boot":
        paper._log_path.write_text(
            paper._log_path.read_text().replace(
                "P0D_RESIDENT_READY boot=",
                "P0D_RESIDENT_READY boot=" + str(uuid.uuid4()) + "-",
            )
        )
        append(event("A", "PRESENT", 60), event("B", "PRESENT", 70))
    elif failure == "b-present-before-join":
        ready = paper._log_path.read_text().split("P0D_RESIDENT event=")[0]
        paper._log_path.write_text(
            ready + event("A", "JOIN", 17)
            + event("B", "PRESENT", 29)
            + event("B", "JOIN", 30)
            + event("A", "PRESENT", 60)
        )
    elif failure == "stale-native":
        bridge.sessions["B"].process_returncode = 0
    elif failure == "physical-authority":
        bridge.physical.observation_only = False
    elif failure == "tick-budget":
        append(event("A", "PRESENT", 200), event("B", "PRESENT", 201))
    elif failure == "malformed-event":
        append(
            f"P0D_RESIDENT event=PRESENT boot={str(uuid.uuid4())} "
            "this-is-not-valid-fields\n"
        )
    else:
        raise AssertionError("unknown test case")

    with pytest.raises(Stage28PresenceWaitHold):
        asyncio.run(await_both_recovered_paper_present(
            bridge=bridge, paper=paper, boot=boot,
            timeout_seconds=1.0, poll_seconds=0.04,
        ))


@pytest.mark.parametrize("timeout,poll,ticks", [
    (0, 0.1, 120), (31, 0.1, 120), (12, 0, 120),
    (12, 1.0, 120), (12, 0.1, 0), (12, 0.1, 241),
    (12, 0.1, True),
])
def test_presence_wait_requires_finite_bounded_budget(
    tmp_path, timeout, poll, ticks,
):
    paper, bridge, boot, _, _ = _booted(tmp_path)
    with pytest.raises(Stage28PresenceWaitHold, match="finite bounded"):
        asyncio.run(await_both_recovered_paper_present(
            bridge=bridge, paper=paper, boot=boot,
            timeout_seconds=timeout, poll_seconds=poll,
            max_ticks_after_latest_join=ticks,
        ))
