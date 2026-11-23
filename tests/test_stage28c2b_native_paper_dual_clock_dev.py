"""Stage28c2b: distinct Minecraft native World-time / Bukkit process clocks.

These fixtures exercise original owners with synthetic Paper/native evidence.
They do NOT start Minecraft, qualify a live PID or prove a real rejoin.
"""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
from relay_self.owned_resident_physical_bridge_dev import OwnedResidentPhysicalBridge
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28RecoveryHold,
    stage28_require_fresh_l1_eligibility,
)
from relay_self.stage28c2b_native_paper_body_link_dev import (
    Stage28NativePaperLinkHold,
    link_recovered_a_b_native_paper_body,
)
from relay_self.world_resident_lifecycle_dev import (
    NativeLoginEvidence,
    Presence,
    ResidentLifecycleError,
    WorldLifetime,
    WorldResidentLifecycle,
)
from test_p0d_resident_move_issuer_dev import _probe
from test_stage28c2b_fork_paper_epoch_dev import (
    _boot,
    _owned_paper_from_synthetic_log,
    _source,
)


def test_original_online_owner_receives_only_matching_native_probe(tmp_path, monkeypatch):
    from relay_self.checkpointed_cognitive_runtime_dev import LiveCognitionCheckpointError

    copy, _, _, _, _ = _clock_context(tmp_path, monkeypatch, native_time=123)
    owner = copy.recovered.owners["A"]
    probe = _probe("new-session-A", 12, "request-A", 123, 4.5)
    owner.accept_rejoined_worldbody(probe, request_id="request-A")
    assert owner.current_worldbody_observation is probe
    assert owner.current_worldbody_observation.snapshot.position.x == 4.5
    for invalid, request in (
        (_probe("new-session-B", 12, "request-A", 123, 4.5), "request-A"),
        (probe, "wrong-request"),
        (_probe("new-session-A", 12, "request-A", 124, 4.5), "request-A"),
    ):
        with pytest.raises(LiveCognitionCheckpointError):
            owner.accept_rejoined_worldbody(invalid, request_id=request)
        assert owner.current_worldbody_observation is probe


def _clock_context(tmp_path, monkeypatch, *, native_time=0, two=True):
    copy = _source(tmp_path, monkeypatch)
    paper = _owned_paper_from_synthetic_log(copy, tick=10)
    # The original new Paper-boot witness was at tick3. The helper's fake
    # Paper log/tick is synthetic; actual code demands the owned Popen.
    # Build a real typed boot dataclass first with a sample tick3.
    from relay_self.owned_paper_world_dev import PaperTickReceipt

    initial_ref = (
        "paper-main-thread:p0d:new-boot-id:new-nonce:sha256:" + "a" * 64
    )
    paper.tick_readback = lambda sid: PaperTickReceipt(sid, 3, initial_ref)
    paper._log_path.write_text(
        "P0D_TICK_READY boot=new-boot-id source=PAPER_MAIN_THREAD\n"
        f"P0D_TICK_ACK nonce=new-nonce boot=new-boot-id "
        f"session={paper.owned_session_id} world={paper.world_id} "
        "tick=3 source=PAPER_MAIN_THREAD\n"
    )
    world, boot = _boot(copy, paper)
    assert world.world_tick == 3
    paper.tick_readback = lambda sid: PaperTickReceipt(
        sid, 10, "paper-main-thread:p0d:new-boot-id:next-nonce:sha256:"
        + "b" * 64,
    )
    paper._log_path.write_text(
        "P0D_TICK_READY boot=new-boot-id source=PAPER_MAIN_THREAD\n"
        f"P0D_TICK_ACK nonce=next-nonce boot=new-boot-id "
        f"session={paper.owned_session_id} world={paper.world_id} "
        "tick=10 source=PAPER_MAIN_THREAD\n"
    )
    life = WorldResidentLifecycle(
        world=world,
        persisted_self_refs={"A": "original-cut-A", "B": "original-cut-B"},
        independent_native_world_clock=True,
    )
    recovered = copy.recovered
    bridge = object.__new__(OwnedResidentPhysicalBridge)
    bridge.paper = paper
    bridge.lifecycle = life
    bridge.physical = recovered.physical
    bridge.owners = recovered.owners
    bridge.cognitive_work = recovered.cognitive_work
    bridge.inference_lane = None
    bridge.sessions = {}
    bridge.last_login_evidence = {}
    bridge.configs = {
        sid: MineflayerLaunchConfig(
            host="127.0.0.1", port=25565,
            username="Relay" + sid, version="1.21.8",
        ) for sid in ("A", "B")
    }
    bridge.forbidden_native_sessions = frozenset(
        (*boot.historical_native_sessions, "other-old-A"),
    )
    for sid in (("A", "B") if two else ("A",)):
        native = "new-session-" + sid
        ticket = life.begin_login(sid)
        proof = NativeLoginEvidence(
            sid, ticket.login_seq, world.world_id, world.branch_id,
            world.paper_session_id, world.epoch, native, native_time,
            "native-probe:" + sid, True, True, True, True, True,
        )
        life.complete_login(ticket, proof)
        recovered.physical.admit_resident_login(
            self_id=sid, former_native_session_id="native-retired-" + sid,
            fresh_native_session_id=native,
            physical_wal_file=recovered.owners[sid].files.physical_wal_file,
            source_world_epoch_validated=True,
        )
        recovered.cognitive_work.bind_login(
            self_id=sid, native_session_id=native, world_epoch=1,
            world_tick=native_time,
        )
        bridge.last_login_evidence[sid] = proof
        bridge.sessions[sid] = SimpleNamespace(
            started=SimpleNamespace(session_id=native),
            process_returncode=None, owned_child_pid=7000 + (sid == "B"),
        )
    return copy, paper, world, boot, bridge


def _fake_trace(boot, **kwargs):
    def e(sid, event, line, tick):
        return SimpleNamespace(
            name="Relay" + sid, event=event,
            line=line, tick=tick, actor_uuid="actor-" + sid,
        )
    events = [e("A", "JOIN", 1, 4), e("B", "JOIN", 2, 5),
              e("A", "PRESENT", 3, 6), e("B", "PRESENT", 4, 7)]
    if kwargs.get("missing_b"):
        events.pop()
    if kwargs.get("foreign_actor"):
        events[3] = SimpleNamespace(**{
            **vars(events[3]), "actor_uuid": "other-actor",
        })
    return SimpleNamespace(
        boot_id="different-resident-plugin-boot",
        paper_session_id=boot.paper_session_id, events=tuple(events),
    )


def _link(copy, paper, boot, bridge, monkeypatch, **trace_opts):
    from relay_self import stage28c2b_native_paper_body_link_dev as linkmodule
    monkeypatch.setattr(
        linkmodule, "parse_owned_paper_resident_trace",
        lambda **_params: _fake_trace(boot, **trace_opts),
    )
    return link_recovered_a_b_native_paper_body(
        bridge=bridge, paper=paper, boot=boot,
        forbidden_native_sessions=bridge.forbidden_native_sessions,
    )


def test_stage28_native_day_time_zero_with_paper_tick_ten_is_valid(
    tmp_path, monkeypatch,
):
    copy, paper, world, boot, bridge = _clock_context(
        tmp_path, monkeypatch, native_time=0,
    )
    updated, links = _link(copy, paper, boot, bridge, monkeypatch)
    assert updated.world_tick == 10
    assert all(p.observed_world_tick == 0 for p in bridge.last_login_evidence.values())
    assert [link.native_world_time_tick for link in links] == [0, 0]
    assert [link.paper_observed_tick for link in links] == [6, 7]
    assert all(not link.clocks_numerically_comparable for link in links)
    assert all(not link.physical_action_issue_authorized for link in links)
    assert links[0].tick_boot_id != links[0].presence_boot_id
    for sid in ("A", "B"):
        assert bridge.lifecycle.view(sid).status is Presence.ONLINE
        # The owner Native memory clock must not be reported as Paper tick.
        assert bridge.owners[sid].last_observed_tick == 0
        assert bridge.lifecycle.view(sid).last_observed_world.world_tick == 3
    from relay_self.resident_llama_inference_lane_dev import LlamaSlotIdleReceipt

    allowed = stage28_require_fresh_l1_eligibility(
        copy.recovered.plan, world=updated,
        logins=tuple(bridge.last_login_evidence[s] for s in ("A", "B")),
        links=links, boot=boot,
        idle=LlamaSlotIdleReceipt("simulated-GPU-idle", 0, 1, False, "sim-only"),
    )
    assert allowed.l1_reevaluation_eligible
    assert allowed.physical_action_issue_authorized is False


@pytest.mark.parametrize("failure", [
    "missing-b", "missing-b-paper-present", "altered-actor",
    "foreign-native-session", "wrong-original-Paper-session",
    "recycled-native", "stale-pid",
])
def test_stage28_native_paper_link_holds_on_missing_independent_source(
    tmp_path, monkeypatch, failure,
):
    copy, paper, world, boot, bridge = _clock_context(
        tmp_path, monkeypatch, two=failure != "missing-b",
    )
    opts = {}
    if failure == "missing-b-paper-present":
        opts["missing_b"] = True
    elif failure == "altered-actor":
        opts["foreign_actor"] = True
    elif failure == "foreign-native-session":
        bridge.sessions["A"].started.session_id = "foreign"
    elif failure == "wrong-original-Paper-session":
        bridge.last_login_evidence["A"] = replace(
            bridge.last_login_evidence["A"], paper_session_id="paper-owned-old",
        )
    elif failure == "recycled-native":
        bridge.forbidden_native_sessions = frozenset((
            *bridge.forbidden_native_sessions, "new-session-A",
        ))
    elif failure == "stale-pid":
        bridge.sessions["B"].owned_child_pid = None
    with pytest.raises(Stage28NativePaperLinkHold):
        _link(copy, paper, boot, bridge, monkeypatch, **opts)


def test_stage28_legacy_lifecycle_still_comparatively_fences_native_tick(
    tmp_path, monkeypatch,
):
    world = WorldLifetime("world", "source", "old-paper", 0, 50)
    life = WorldResidentLifecycle(
        world=world, persisted_self_refs={"A": "retained-A"},
    )
    ticket = life.begin_login("A")
    native = NativeLoginEvidence(
        "A", ticket.login_seq, "world", "source", "old-paper", 0,
        "native-new", 2, "probe-A", True, True, True, True, True,
    )
    with pytest.raises(ResidentLifecycleError, match="source/epoch"):
        life.complete_login(ticket, native)


def test_stage28_independent_clock_mode_requires_fresh_owned_paper():
    with pytest.raises(ResidentLifecycleError):
        WorldResidentLifecycle(
            world=WorldLifetime("world", "branch", "old-paper", 0, 100),
            persisted_self_refs={"A": "retained"},
            independent_native_world_clock=True,
        )


@pytest.mark.parametrize("kind", [
    "missing-a", "wrong-native-ref", "other-Paper-boot",
    "Paper-tick-before-event", "wrong-native-time",
])
def test_stage28_linked_l1_gate_rejects_tampered_clock_evidence(
    tmp_path, monkeypatch, kind,
):
    copy, paper, world, boot, bridge = _clock_context(tmp_path, monkeypatch)
    updated, links = _link(copy, paper, boot, bridge, monkeypatch)
    native = tuple(bridge.last_login_evidence[s] for s in ("A", "B"))
    if kind == "missing-a":
        links = (links[1],)
    elif kind == "wrong-native-ref":
        links = (replace(links[0], native_probe_ref="foreign-probe"), links[1])
    elif kind == "other-Paper-boot":
        links = (replace(links[0], tick_boot_id="other-boot"), links[1])
    elif kind == "Paper-tick-before-event":
        links = (replace(links[0], paper_observed_tick=0), links[1])
    else:
        links = (replace(links[0], native_world_time_tick=100), links[1])
    from relay_self.resident_llama_inference_lane_dev import LlamaSlotIdleReceipt

    with pytest.raises(Stage28RecoveryHold):
        stage28_require_fresh_l1_eligibility(
            copy.recovered.plan, world=updated, logins=native, links=links,
            boot=boot,
            idle=LlamaSlotIdleReceipt("sim-idle", 0, 1, False, "source"),
        )
