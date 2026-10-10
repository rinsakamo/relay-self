"""One deterministic World double; real E3/S24 and S14-S16 owners."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace

import pytest

import test_postmain_correlated_probe as s29
import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer.execution import build_mineflayer_command
from experiments import epistemic_e5_prospective_gate as e5
from experiments import epistemic_e6_feasibility_interlock as e6
from experiments import epistemic_e10_action_world as e10
from relay_self.action import ActionState
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.correlated_probe import CorrelatedProbeGrant
from relay_self.execution_binding import ExecutionBinding
from relay_self.provenance import Provenance

P = Provenance("e10.offline", "separate-caller-authority")


class Clock:
    def __init__(self, *, unavailable=False, late=False):
        self.now = 70
        self.calls = 0
        self.unavailable = unavailable
        self.late = late

    def __call__(self):
        self.calls += 1
        self.now += 10
        if (self.unavailable and self.calls == 7) or (self.late and self.calls == 5):
            self.now = 1000
        return self.now


class World:
    def __init__(self, old, observation, *, mode="executed", fault=None, health=18):
        self.started = old.started
        self.template = observation
        self.seq = observation.seq
        self.mode = mode
        self.fault = fault
        self.health = health
        self.frames = deque()
        self.commands = []
        self.observes = []
        self.reads = []
        self.pre = 0

    def queue(self, message):
        message = replace(message, session_id=self.started.session_id, seq=self.seq)
        self.seq += 1
        if self.fault == "session":
            message = replace(message, session_id="alien")
        if self.fault == "seq":
            message = replace(message, seq=999)
        self.frames.append(message)

    async def send_observe(self, request_id=None):
        self.observes.append(request_id)
        message = replace(self.template, request_id=request_id)
        if request_id == "e10:evaluator":
            if self.fault == "evaluator-missing":
                return
            if self.fault == "evaluator-id":
                message = replace(message, request_id="policy-leak")
            message = replace(message, snapshot=replace(message.snapshot, health=self.health))
        elif request_id == s29.REQUEST1:
            entity = message.snapshot.nearby_entities[0]
            origin = message.snapshot.position
            entity = replace(entity, distance=1.8, position=replace(entity.position, x=origin.x + 1.8))
            message = replace(message, snapshot=replace(message.snapshot, nearby_entities=(entity,)))
        elif request_id is None:
            self.pre += 1
            z = 0.0 if self.pre == 1 or self.mode == "unavailable" else 0.2
            message = replace(message, snapshot=replace(
                message.snapshot, position=replace(message.snapshot.position, z=z),
            ))
        self.queue(message)

    async def receive(self):
        if not self.frames:
            raise EOFError("offline unavailable stream")
        message = self.frames.popleft()
        self.reads.append(message)
        return message

    async def send_set_control(self, action_id, *, control, state):
        assert control == "back" and state is True
        self.commands.append(("set_control", action_id))
        if self.mode == "unknown":
            return
        effect = s19.effect(1, action_id, "set_control")
        if self.mode == "rejected":
            effect = replace(effect, result="rejected", error="controlled rejection")
        if self.fault == "action-id":
            effect = replace(effect, action_id="foreign-action")
        self.queue(effect)

    async def send_clear_controls(self, action_id):
        self.commands.append(("clear_controls", action_id))
        if self.mode not in ("unknown", "rejected"):
            self.queue(s19.effect(1, action_id, "clear_controls"))


def prepare(distance=0.2, *, arm="OBSERVE", price=1, mode="executed", fault=None,
            health=18):
    data, _, inputs, _, kwargs = s29._subject(distance=distance)
    world = World(kwargs["adapter"], kwargs["adapter"].frames[0],
                  mode=mode, fault=fault, health=health)
    action_world = World(kwargs["adapter"], kwargs["adapter"].frames[0],
                         mode=mode, fault=fault, health=health)
    action_world.started = replace(action_world.started, session_id="e10:action-session4")
    action_world.seq = 1
    binding = ExecutionBinding(
        "e10:binding4", "MOVE_AWAY", data["intent"].current_intent.intent_id,
        "e10:skill4", "alternate-escape-path", "e10:action4", "MOVE_BACKWARD", P,
    )

    def authorize(proposed):
        return proposed.authorize(at_ns=101, provenance=P, authority="e10:action4-only")

    args = dict(
        arm=arm, price_quarters=price, prior_ref="uniform-nearfar-v1",
        recovery_skill=inputs["recovery_skill"], intent=data["intent"],
        retained=data["commit"].new_state, at_ns=70, provenance=P,
        binding4=binding, authorize4=authorize, deadline_ns=1000,
        action_adapter=action_world,
        second_grant=CorrelatedProbeGrant(kwargs["grant"].authority, s29.REQUEST2),
        second_observed_at_ns=68, second_inspected_at_ns=69,
        evaluator_request_id="e10:evaluator", reset_id="e10:reset1",
        used_sessions=set(), used_resets=set(),
        clock=Clock(unavailable=mode == "unavailable"), evaluator_horizon_ns=1,
        **{k: v for k, v in kwargs.items() if k not in ("max_frames", "max_age_ns")},
    )
    args["adapter"] = world
    return data, world, args


@pytest.fixture(autouse=True)
def no_duration_sleep(monkeypatch):
    async def no_sleep(_seconds):
        pass
    monkeypatch.setattr("adapters.mineflayer.execution.asyncio.sleep", no_sleep)


def run(args):
    return asyncio.run(e10.run_episode(**args))


@pytest.mark.parametrize("distance", [0.2, 1.8])
@pytest.mark.parametrize("price", [1, 4])
@pytest.mark.parametrize("arm", ["NO_OBSERVE", "CHEAP_EXACT", "OBSERVE"])
def test_twelve_frozen_policy_conditions_through_real_owners(distance, price, arm):
    data, world, args = prepare(distance, arm=arm, price=price)
    result = run(args)
    observes = arm == "OBSERVE" or (arm == "CHEAP_EXACT" and price == 1)
    moves = observes and distance == 0.2
    assert result.decision.observation_count == int(observes)
    assert (result.first_probe is not None) is observes
    if observes:
        assert result.first_probe.probe_seq < result.decision.receipt.probe_seq
        assert world.observes[:2] == [s29.REQUEST1, s29.REQUEST2]
    assert result.decision.issued_actions == 0  # E3 is still admission only
    assert result.physically_authenticated is False
    assert result.parent_action is args["action"]
    assert result.parent_action.state is ActionState.OUTCOME
    assert data["supervisor"].get(args["action"].action_id) is args["action"]
    assert result.evaluation.requested_at_ns > result.decision_at_ns
    assert result.evaluation.observation.snapshot.health == 18
    assert result.elapsed_ms > 0 and result.evaluator_ms > 0
    assert bool(result.probe_ms) is observes
    if moves:
        assert result.action4.state is ActionState.OUTCOME
        assert result.action4.action_id != result.parent_action.action_id
        assert result.binding4.binding_id != result.parent_consequence.binding_id
        assert result.consequence4.session_id != result.parent_consequence.session_id
        assert result.consequence4.dispatch_receipt.action_id == result.action4.action_id
        assert tuple(x.state for x in result.action4.events) == (
            ActionState.PROPOSED, ActionState.AUTHORIZED, ActionState.ISSUED, ActionState.OUTCOME,
        )
        assert result.interpretation4.disposition is ActionOutcomeDisposition.OUTCOME
        assert result.evaluation.requested_at_ns > result.action4.events[-1].at_ns
        assert args["action_adapter"].commands == [
            ("set_control", "e10:action4"), ("clear_controls", "e10:action4-s15-clear"),
        ]
    else:
        assert result.action4 is result.binding4 is result.consequence4 is None
        assert args["action_adapter"].commands == []
        assert world.observes == ([s29.REQUEST1, s29.REQUEST2] if observes else []) + ["e10:evaluator"]
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize("mode,disposition,state", [
    ("executed", ActionOutcomeDisposition.OUTCOME, ActionState.OUTCOME),
    ("rejected", ActionOutcomeDisposition.OUTCOME, ActionState.OUTCOME),
    ("unknown", ActionOutcomeDisposition.UNKNOWN, ActionState.UNKNOWN),
    ("unavailable", ActionOutcomeDisposition.UNAVAILABLE, ActionState.TIMEOUT),
])
def test_world_statuses_keep_s16_meaning_and_denominator(mode, disposition, state):
    data, _, args = prepare(mode=mode)
    result = run(args)
    assert result.interpretation4.disposition is disposition
    assert result.action4.state is state
    assert data["supervisor"].open_actions == ()
    assert result.evaluation.requested_at_ns > result.action4.events[-1].at_ns
    if mode == "rejected":
        assert result.interpretation4.reason_code == "known_adapter_rejection"
    if mode == "unavailable":
        assert result.consequence4.status.value == "undetermined"
        assert result.action4.events[-1].at_ns >= 1000


@pytest.mark.parametrize("arm,price", [("NO_OBSERVE", 1), ("CHEAP_EXACT", 4)])
def test_wait_never_reads_policy_source_or_calls_action_authority(arm, price):
    _, world, args = prepare(arm=arm, price=price)
    args["authorize4"] = lambda _: pytest.fail("WAIT authorized an Action")
    result = run(args)
    assert world.observes == ["e10:evaluator"]
    assert result.decision.receipt is None and not args["cursor"].consumed
    assert result.probe_ms == 0


@pytest.mark.parametrize("health", [0, 20])
def test_evaluator_world_truth_never_reenters_policy(health):
    _, _, args = prepare(health=health)
    result = run(args)
    assert result.decision.selected == "MOVE_AWAY"
    assert result.decision.epoch.wait_score == 8
    assert result.evaluation.damage_points == result.parent_consequence.after_observation.snapshot.health - health
    assert result.decision.epoch.world_evidence.provenance != result.evaluation.observation.provenance


@pytest.mark.parametrize("field", ["action_id", "binding_id", "skill_execution_id"])
def test_parent_ids_cannot_be_reused(field):
    _, world, args = prepare()
    value = dict(action_id=args["action"].action_id,
                 binding_id=args["consequence"].binding_id,
                 skill_execution_id=args["recovery_skill"].execution_id)[field]
    args["binding4"] = replace(args["binding4"], **{field: value})
    with pytest.raises(e10.E10Rejected, match="distinct"):
        run(args)
    assert args["action_adapter"].commands == []


@pytest.mark.parametrize("fault", ["session", "seq", "action-id", "evaluator-id"])
def test_native_contamination_is_rejected_without_false_outcome(fault):
    data, _, args = prepare(fault=fault)
    with pytest.raises(ValueError):
        run(args)
    if fault == "action-id":
        assert data["supervisor"].get("e10:action4").state is ActionState.ISSUED


@pytest.mark.parametrize("denied", [False, True])
def test_admission_cannot_substitute_for_separate_authority(denied):
    _, world, args = prepare()
    args["authorize4"] = (lambda p: p.deny(at_ns=101, provenance=P, authority="denied")) if denied else (lambda p: p)
    with pytest.raises(e10.E10Rejected, match="authoriz|denied"):
        run(args)
    assert args["action_adapter"].commands == []


def test_e9_read_only_bridge_cannot_issue():
    _, world, args = prepare()
    args["action_adapter"].send_set_control = None
    with pytest.raises(e10.E10Rejected, match="read-only"):
        run(args)
    assert args["action_adapter"].commands == []


@pytest.mark.parametrize("identity", ["session", "reset"])
def test_cross_arm_reuse_is_consumed_even_after_wait(identity):
    _, world, args = prepare(arm="NO_OBSERVE")
    run(args)
    if identity == "session":
        args["reset_id"] = "new-reset"
    else:
        args["used_sessions"] = set()
    with pytest.raises(e10.E10Rejected, match="cross-arm"):
        run(args)
    assert world.observes == ["e10:evaluator"]


def test_late_world_result_does_not_become_outcome():
    data, _, args = prepare()
    args["clock"] = Clock(late=True)
    with pytest.raises(e10.E10Rejected, match="late"):
        run(args)
    assert data["supervisor"].get("e10:action4").state is ActionState.TIMEOUT


def test_missing_evaluator_is_not_zero_damage_or_safety():
    _, _, args = prepare(fault="evaluator-missing")
    result = run(args)
    assert result.evaluation.observation is None
    assert result.evaluation.damage_points is result.evaluation.movement_m is None
    assert result.evaluation.error.startswith("EOFError")


def test_admitted_output_is_exact_s14_input_and_cannot_execute_yet():
    _, _, args = prepare()
    result = run(args)
    trace = result.decision.epoch
    assert trace.control.candidate_ref == trace.admission.candidate_ref == "MOVE_AWAY"
    assert trace.admission.status is trace.admission_status
    with pytest.raises(ValueError, match="ISSUED"):
        build_mineflayer_command(result.action4, result.binding4)


def test_frozen_e5_e6_are_not_promoted_by_e10():
    assert e5.digest() == "2ede0bd82ab6c8ada2557a5477f9c6d6084e6cbae50a5e1a6b8ffc6d1626e2f3"
    assert len(e5.planned_trials()) == 36
    assert e6.digest() == e6.MANIFEST_SHA256
    assert e6.plan()["classification"] == "E6_PHYSICAL_START_BLOCKED"
    assert e6.plan()["world_launched"] is False


@pytest.mark.parametrize("field", ["prior", "grant-session", "parent-dispatch", "parent-owner"])
def test_false_parent_or_hidden_prior_fails_before_any_read(field):
    data, world, args = prepare(arm="NO_OBSERVE")
    if field == "prior":
        args["prior_ref"] = "evaluator-known-safe"
    elif field == "grant-session":
        args["grant"] = replace(args["grant"], authority=replace(
            args["grant"].authority, session_id="foreign",
        ))
    elif field == "parent-dispatch":
        args["consequence"] = replace(args["consequence"], dispatch_receipt=replace(
            args["consequence"].dispatch_receipt, action_id="another-action",
        ))
    else:
        args["action"] = data["closed1"]
    with pytest.raises(ValueError):
        run(args)
    assert world.observes == [] and args["action_adapter"].commands == []


@pytest.mark.parametrize("fault", ["same-session", "different-world", "consumed-session"])
def test_frozen_e5_action_session_scope_cannot_be_collapsed(fault):
    _, _, args = prepare()
    other = args["action_adapter"]
    if fault == "same-session":
        other.started = replace(other.started, session_id=args["consequence"].session_id)
    elif fault == "different-world":
        other.started = replace(other.started, config=replace(other.started.config, port=25566))
    else:
        args["used_sessions"].add(other.started.session_id)
    with pytest.raises(e10.E10Rejected, match="distinct Action4 session"):
        run(args)
    assert other.commands == []


def test_two_source_reads_do_not_allow_evaluator_id_as_second_policy_read():
    _, world, args = prepare()
    args["second_grant"] = replace(args["second_grant"], request_id="e10:evaluator")
    with pytest.raises(e10.E10Rejected, match="distinct evaluator"):
        run(args)
    assert world.observes == []


def test_evaluation_cannot_be_smuggled_into_decision_api():
    _, world, args = prepare()
    with pytest.raises(TypeError, match="unexpected keyword"):
        run({**args, "evaluator_world_info": {"health": 20, "distance": 180}})
    assert world.observes == []


def test_source_frames_keep_original_objects_and_independent_native_sequences():
    _, world, args = prepare()
    result = run(args)
    assert result.native_frames == tuple(world.reads + args["action_adapter"].reads)
    assert all(a is b for a, b in zip(result.native_frames, world.reads + args["action_adapter"].reads))
    assert result.first_probe.probe_seq == 5
    assert result.decision.receipt.probe_seq == 6
    assert result.evaluation.observation.session_id == "e10:action-session4"
    assert result.evaluation.observation.seq > result.consequence4.after_observation.seq
