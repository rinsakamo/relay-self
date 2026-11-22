"""Stage27c2 experimental source-shaped LOOK / MOVE / STOP original WAL tests.

The Mineflayer subclass is scripted, never a real native process. Real Paper,
real Gemma, real checkpoint and native physical causality are NOT attested.
"""
from __future__ import annotations

import asyncio
import math

import pytest

from adapters.mineflayer.python_protocol import MineflayerEffectResult
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    PhysicalGrantStage,
)
from relay_self.p0d_stage27c_l0_place_proposal_dev import Stage27L0PlaceProposal
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from test_p0d_real_preset_checkpoint_dev import native_probe
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _SyntheticLlamaServer,
)
from test_p0d_resident_move_issuer_dev import ScriptedNative
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit
from test_p0d_stage27b_place_motion_dev import _resolve, qualified_a
from test_p0d_stage27c_l0_place_proposal_dev import prepare


class ScriptedPlaceNative(ScriptedNative):
    def __init__(self, native, *, blocked=False, overshoot=False,
                 bad_stop=False, bad_look=False):
        super().__init__(native, bad_stop=bad_stop)
        self.blocked = blocked
        self.overshoot = overshoot
        self.bad_look = bad_look
        self.look_received = asyncio.Event()

    async def send_look(self, action_id, *, yaw, pitch):
        self.gate(self.started.session_id, "look", action_id)
        assert math.isfinite(yaw) and yaw == pytest.approx(-math.pi / 2)
        assert pitch == 0.0
        self.sent_commands.append((action_id, "look", yaw, pitch))
        self.seq += 1
        self.events.append(MineflayerEffectResult(
            self.started.session_id, self.seq,
            "forged-look" if self.bad_look else action_id,
            "look", "applied", None,
        ))
        self.look_received.set()

    async def send_set_control(self, action_id, *, control, state):
        self.gate(self.started.session_id, "set_control", action_id)
        assert control == "forward" and state is True
        self.sent_commands.append((action_id, control, state))
        self.seq += 1
        self.events.append(MineflayerEffectResult(
            self.started.session_id, self.seq, action_id, "set_control",
            "applied", None,
        ))
        self.x += 2.5 if self.overshoot else 0.0 if self.blocked else 0.8
        self.start_received.set()


def _grant(stage, binding):
    return PhysicalDevGrant(
        stage=stage, authority_id="operator-stage27c-" + stage.value,
        provenance=Provenance(
            "operator-stage27c-" + stage.value, binding.native_source.reference,
        ),
        intent_id=binding.intent_id,
        action_id=binding.action_id,
        session_id=binding.scope.world_session_id,
        probe_seq=binding.native_seq,
        probe_request_id=binding.native_request_id,
        selected_target_ref=binding.target_ref,
        granted=True,
    )


async def selected_original(f, lane):
    prepared, handoff, former = await qualified_a(f, lane)
    new = native_probe(f.names[0], former.seq + 1,
                       session=handoff.native_session_id)
    plan = _resolve(f, prepared, handoff, new)
    l0 = prepare(f, prepared, handoff, plan, new)
    assert isinstance(l0, Stage27L0PlaceProposal)
    return prepared, handoff, plan, l0, former, new


def _args(f, prepared, handoff, plan, l0, previous, current):
    binding = l0.proposal.binding
    owner = f.owners[f.names[0]]
    return dict(
        proposal=l0.proposal, l0=l0, prepared=prepared,
        handoff=handoff, motion=plan,
        previous_probe=previous, current_probe=current,
        owner=owner, physical=f.physical,
        propose_grant=_grant(PhysicalGrantStage.PROPOSE, binding),
        issue_grant=_grant(PhysicalGrantStage.ISSUE, binding),
        journal=PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        ),
        at_ns=1000,
        provenance=Provenance("stage27c-physical", "original-owner"),
        grant_real_world=True,
        acknowledge_dev_unverified_principal=True,
        evidence_timeout_s=1.5,
        pulse_seconds=0.15,
    )


@pytest.mark.parametrize(
    ("mode", "expected_status", "expected_distance"),
    [
        ("moved", "NATIVE_PLACE_MOVE_SETTLED", 0.8),
        ("blocked", "NATIVE_PLACE_MOVE_NO_PROGRESS", 0.0),
        ("overshoot", "NATIVE_PLACE_MOVE_OVERSHOOT", 2.5),
    ],
)
def test_one_original_a_place_parent_look_forward_stop_and_b_is_unchanged(
    tmp_path, mode, expected_status, expected_distance,
):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True,
                        allow_resident_move=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        pre, handoff, motion, l0, former, current = await selected_original(f, lane)
        a = f.names[0]
        b = f.names[1]
        owner_b = f.owners[b]
        before_b = (
            owner_b.intent.events, tuple(owner_b.skills),
            PhysicalActionJournal.restore(
                owner_b.files.physical_wal_file, self_id=b,
            ).digest,
        )
        script = ScriptedPlaceNative(
            l0.native_session_id, blocked=mode == "blocked",
            overshoot=mode == "overshoot",
        )
        script.seq = current.seq
        script.tick = 1213
        script.gate = lambda native, effect, action: f.physical.require_native_effect(
            self_id=a, native_session_id=native,
            effect=effect, action_id=action,
        )
        args = _args(f, pre, handoff, motion, l0, former, current)
        receipt = await f.physical.issue_place_move(script, **args)
        assert receipt.journal_status == expected_status
        assert receipt.displacement_m == pytest.approx(expected_distance)
        assert receipt.look_ack.action_id == l0.action_id + "-look"
        assert receipt.start_ack.action_id == l0.action_id + "-start"
        assert receipt.stop_ack.action_id == l0.action_id + "-stop"
        assert script.look_received.is_set()
        assert script.start_received.is_set()
        assert script.stop_received.is_set()
        assert receipt.native_effect_issued
        assert receipt.l0_step_status == "YIELD_EVALUATION"
        assert not receipt.l0_goal_succeeded
        assert f.owners[a].supervisor.get(l0.action_id).state.value == "outcome"
        assert not receipt.skill_success_attested
        assert not receipt.paper_causal_attribution
        assert len(script.sent_commands) == 3
        journal = PhysicalActionJournal.restore(
            f.owners[a].files.physical_wal_file, self_id=a,
        )
        journal.require_clear()
        assert journal._body["schema"] == 2
        assert journal.records[-1]["capability"] == "MOVE_PLACE"
        assert journal.records[-1]["invocation_ref"] == handoff.invocation_ref
        assert journal.records[-1]["preset_ref"] == handoff.preset_ref
        assert journal.records[-1]["target_contract_ref"] == motion.target_contract_ref
        assert journal.records[-1]["target_ref"] == handoff.target_ref
        assert journal.records[-1]["status"] == expected_status
        assert (
            owner_b.intent.events, tuple(owner_b.skills),
            PhysicalActionJournal.restore(
                owner_b.files.physical_wal_file, self_id=b,
            ).digest,
        ) == before_b
        assert f.physical.active_action_ids == ()
        assert len(http.calls) == 1
        for name in f.names:
            await f.bridge.logout(name)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


@pytest.mark.parametrize("fault", ["bad-look", "bad-stop"])
def test_original_place_native_uncertainty_keeps_prepared_wal_and_no_retry(
    tmp_path, fault,
):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True,
                        allow_resident_move=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        pre, handoff, motion, l0, former, current = await selected_original(f, lane)
        a = f.names[0]
        script = ScriptedPlaceNative(
            l0.native_session_id, bad_stop=fault == "bad-stop",
            bad_look=fault == "bad-look",
        )
        script.seq = current.seq
        script.tick = 1213
        script.gate = lambda native, effect, action: f.physical.require_native_effect(
            self_id=a, native_session_id=native,
            effect=effect, action_id=action,
        )
        args = _args(f, pre, handoff, motion, l0, former, current)
        with pytest.raises(Exception):
            await f.physical.issue_place_move(script, **args)
        journal = PhysicalActionJournal.restore(
            f.owners[a].files.physical_wal_file, self_id=a,
        )
        assert journal.unresolved
        assert journal.records[-1]["capability"] == "MOVE_PLACE"
        assert journal.records[-1]["invocation_ref"] == handoff.invocation_ref
        assert journal.records[-1]["status"] == "PREPARED_UNRESOLVED"
        assert len(http.calls) == 1
        # Keep physical uncertainty: no cleanup, no retry or fabricated result.
        await f.bridge.logout(f.names[1])
        f.physical.hold_for_operator()
        assert not f.physical.active_action_ids

    try:
        asyncio.run(scenario())
    finally:
        # The synthetic Paper process is disposable; no fake successful
        # retirement of A after an unresolved physical Action.
        f.stop_paper()
        http.stop()
