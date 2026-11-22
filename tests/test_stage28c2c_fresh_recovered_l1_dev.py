"""Stage28c2c: original recovered A/B, current native Body, fresh L1 numbers.

All synthetic here. Even an accepted numbered choice does NOT issue a
Physical Action, start a Skill, commit an Intent, or claim a real Gemma POST.
"""
from __future__ import annotations

import asyncio
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer.python_protocol import MineflayerInventoryItem
from relay_self.cognitive_minimal_dev import PatternRegistry
from relay_self.owned_resident_physical_bridge_dev import (
    OwnedResidentBridgeError,
)
from relay_self.relay_engine import (
    BoundedChoice,
    CognitionMode,
    ProviderDecision,
)
from relay_self.resident_llama_inference_lane_dev import (
    LlamaSlotIdleReceipt,
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)
from relay_self.stage28c2c_fresh_recovered_l1_dev import (
    Stage28c2cL1Hold,
    prepare_fresh_original_l1_turn,
    run_one_fresh_original_bounded_choice,
    validate_fresh_original_l1_result,
)
from test_p0d_resident_move_issuer_dev import _probe
from test_stage28c2b_native_paper_dual_clock_dev import (
    _clock_context,
    _link,
)


def _ready(tmp_path, monkeypatch, *, bread=False, omega=0):
    copy, paper, _, boot, bridge = _clock_context(
        tmp_path, monkeypatch, native_time=0,
    )
    world, links = _link(copy, paper, boot, bridge, monkeypatch)
    bridge.last_login_observations = {}
    for sid in ("A", "B"):
        native = bridge.last_login_evidence[sid]
        actual = _probe(
            native.native_session_id, 2, native.observation_ref,
            native.observed_world_tick, 230.5 if sid == "A" else 243.5,
        )
        if bread and sid == "A":
            actual = replace(
                actual,
                snapshot=replace(
                    actual.snapshot,
                    inventory=(MineflayerInventoryItem("bread", 1, 36),),
                ),
            )
        if omega and sid == "A":
            actual = replace(
                actual,
                snapshot=replace(actual.snapshot, oxygen_level=None),
            )
        bridge.last_login_observations[sid] = actual
        bridge.owners[sid].accept_rejoined_worldbody(
            actual, request_id=native.observation_ref,
        )
    idle = LlamaSlotIdleReceipt(
        "synthetic-exclusive-backend", 0, 1, False, "synthetic-idle",
    )
    return copy, bridge, boot, world, links, idle


def _prepare(case, *, self_id="A", skills=frozenset(), presets=()):
    copy, bridge, boot, world, links, idle = case
    return prepare_fresh_original_l1_turn(
        plan=copy.recovered.plan, bridge=bridge,
        boot=boot, world=world, links=links, idle=idle,
        self_id=self_id, allowed_skills=skills,
        preset_by_skill=presets,
    )


def _fake_l1(case, turn, choice):
    _, bridge, _, _, _, _ = case
    lane = object.__new__(ResidentLlamaInferenceLane)
    lane.cognitive_work = bridge.cognitive_work
    lane.backend_ref = "synthetic-exclusive-backend"
    lane.result = lambda ticket: ProviderDecision.resolved(choice)
    bridge.inference_lane = lane
    token = ResidentInferenceTicket(
        turn.self_id, "new-work-"+turn.request.request_id,
        turn.request.request_id, CognitionMode.BOUNDED,
        turn.owner_scope[0], turn.owner_scope[1], turn.owner_scope[2],
        lane.backend_ref,
    )
    return lane, token


def test_both_original_owners_use_retained_registry_not_fresh_bootstrap(
    tmp_path, monkeypatch,
):
    case = _ready(tmp_path, monkeypatch, omega=1)
    original = case[0].recovered.owners
    for sid in ("A", "B"):
        before = original[sid].retained
        registry = original[sid].pattern_registry
        turn = _prepare(case, self_id=sid)
        assert turn.request_source_verified
        assert turn.round.frame.registry_revision == registry.revision
        assert turn.round.frame.pattern_checks == len(registry.patterns)
        assert turn.round.frame.options == ()
        assert [c.description for c in turn.request.choices] == [
            "ESCALATE_L2", "DEFER",
        ]
        assert turn.request.identity_context.value_json
        assert turn.request.think_allowed is False
        assert turn.original_probe is original[sid].current_worldbody_observation
        assert turn.original_probe.session_id == turn.owner_scope[1]
        assert turn.old_decision_reusable is False
        assert turn.physical_action_issue_authorized is False
        assert original[sid].retained is before
    assert _prepare(case, self_id="A").request.request_id != (
        _prepare(case, self_id="A").request.request_id
    )


def test_food_target_only_when_present_and_presetted_from_original(
    tmp_path, monkeypatch,
):
    case = _ready(tmp_path, monkeypatch, bread=True)
    turn = _prepare(
        case, skills=frozenset({("EAT", 1)}),
        presets=(("EAT@1", "synthetic-existing-eat-preset"),),
    )
    assert len(turn.round.frame.options) == 1
    choice = turn.round.frame.options[0]
    assert choice.goal_id == "HUNGER_RELIEF"
    assert choice.skill_id == "EAT"
    assert choice.target_ref == "inventory:bread:slot:36"
    assert [x.description for x in turn.request.choices][-2:] == [
        "ESCALATE_L2", "DEFER",
    ]
    assert "synthetic-existing-eat-preset" in turn.request.choices[0].description
    assert turn.round.frame.registry_revision == case[1].owners["A"].pattern_registry.revision


@pytest.mark.parametrize("failure", [
    "missing-A-Body", "other-native-Body", "altered-probe-request",
    "changed-Paper-session", "GPU-busy", "missing-B-Body",
    "mutated-registry", "physical-open", "wrong-preset",
    "unregistered-skill", "old-native-session",
])
def test_preflight_refuses_stale_or_unowned_original_source(
    tmp_path, monkeypatch, failure,
):
    case = _ready(tmp_path, monkeypatch)
    copy, bridge, boot, world, links, idle = case
    if failure == "missing-A-Body":
        bridge.owners["A"].current_worldbody_observation = None
    elif failure == "other-native-Body":
        bridge.owners["A"].current_worldbody_observation = (
            bridge.last_login_observations["B"]
        )
    elif failure == "altered-probe-request":
        bridge.last_login_observations["A"] = replace(
            bridge.last_login_observations["A"], request_id="forged",
        )
    elif failure == "changed-Paper-session":
        bridge.paper._session_id = "paper-owned-foreign"
    elif failure == "GPU-busy":
        idle = replace(idle, is_processing=True)
    elif failure == "missing-B-Body":
        bridge.last_login_observations.pop("B")
    elif failure == "mutated-registry":
        bridge.owners["A"].pattern_registry = PatternRegistry(123, ())
        bridge.owners["A"].current_worldbody_observation = None
    elif failure == "physical-open":
        bridge.physical._observation_only = False
    elif failure == "wrong-preset":
        with pytest.raises(Stage28c2cL1Hold):
            _prepare(case, skills=frozenset({("EAT", 1)}))
        return
    elif failure == "unregistered-skill":
        with pytest.raises(Stage28c2cL1Hold):
            _prepare(
                case,
                skills=frozenset({("FLY", 1)}),
                presets=(("FLY@1", "forged-fly"),),
            )
        return
    else:
        bridge.last_login_evidence["A"] = replace(
            bridge.last_login_evidence["A"],
            native_session_id=boot.historical_native_sessions[0],
        )
    with pytest.raises((Stage28c2cL1Hold, RuntimeError, ValueError)):
        prepare_fresh_original_l1_turn(
            plan=copy.recovered.plan, bridge=bridge,
            boot=boot, world=world, links=links, idle=idle,
            self_id="A",
        )


def test_only_real_owned_lane_result_may_select_no_Action(
    tmp_path, monkeypatch,
):
    case = _ready(tmp_path, monkeypatch)
    before = case[1].owners["A"].retained
    intent = case[1].owners["A"].intent
    turn = _prepare(case)
    lane, token = _fake_l1(case, turn, choice="1")
    result = validate_fresh_original_l1_result(
        bridge=case[1], boot=case[2], turn=turn,
        lane=lane, ticket=token,
    )
    assert result.selection_status == "ESCALATE_L2"
    assert result.choice_id == "1"
    assert result.selected_skill_id is None
    assert result.selected_target_ref is None
    assert result.action_issued is False
    assert result.skill_started is False
    assert result.intent_committed is False
    assert result.peer_sent is False
    assert case[1].owners["A"].retained is before
    assert case[1].owners["A"].intent is intent


def test_actual_provider_unknown_number_does_not_create_target(
    tmp_path, monkeypatch,
):
    case = _ready(tmp_path, monkeypatch)
    turn = _prepare(case)
    lane, token = _fake_l1(case, turn, choice="99")
    result = validate_fresh_original_l1_result(
        bridge=case[1], boot=case[2], turn=turn,
        lane=lane, ticket=token,
    )
    assert result.selection_status == "RECONSIDER"
    assert result.selected_skill_id is None
    assert result.action_issued is False


@pytest.mark.parametrize("failure", [
    "old-native", "new-Paper", "wrong-request",
    "foreign-self", "stale-Body", "tampered-choices",
    "tampered-Preset", "physical-gate", "backend-foreign",
])
def test_model_readback_refuses_foreign_or_replayed_result(
    tmp_path, monkeypatch, failure,
):
    case = _ready(tmp_path, monkeypatch)
    turn = _prepare(case)
    lane, token = _fake_l1(case, turn, choice="2")
    bridge, boot = case[1], case[2]
    if failure == "old-native":
        token = replace(token, native_session_id="retired-A")
    elif failure == "new-Paper":
        bridge.paper._session_id = "paper-owned-other"
    elif failure == "wrong-request":
        token = replace(token, request_id="prior-decision")
    elif failure == "foreign-self":
        token = replace(token, self_id="B")
    elif failure == "stale-Body":
        bridge.owners["A"].current_worldbody_observation = None
    elif failure == "tampered-choices":
        turn = replace(
            turn, request=replace(
                turn.request, choices=(
                    BoundedChoice("1", "MOVE to nowhere"),
                    turn.request.choices[1],
                ),
            ),
        )
    elif failure == "tampered-Preset":
        turn = replace(turn, presets=(("MOVE@1", "fake"),))
    elif failure == "physical-gate":
        bridge.physical._observation_only = False
    else:
        token = replace(token, backend_ref="different-backend")
    with pytest.raises(Stage28c2cL1Hold):
        validate_fresh_original_l1_result(
            bridge=bridge, boot=boot, turn=turn,
            lane=lane, ticket=token,
        )


def test_attach_owned_gpu_lane_requires_original_active_body_then_fences_on_logout(
    tmp_path, monkeypatch,
):
    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, _, _ = case
    lane = object.__new__(ResidentLlamaInferenceLane)
    lane.cognitive_work = bridge.cognitive_work
    lane._uncertain = False
    lane._lock = threading.RLock()
    lane.witness = SimpleNamespace(require_idle=lambda: None)
    bound = []
    lane.bind_login = bound.append
    bridge.attach_observation_only_bounded_l1(lane)
    assert bridge.inference_lane is lane
    assert bound == ["A", "B"]
    with pytest.raises(OwnedResidentBridgeError):
        bridge.attach_observation_only_bounded_l1(lane)


def test_attach_gpu_lane_fails_if_original_body_missing(tmp_path, monkeypatch):
    case = _ready(tmp_path, monkeypatch)
    _, bridge, _, _, _, _ = case
    bridge.owners["B"].current_worldbody_observation = None
    lane = object.__new__(ResidentLlamaInferenceLane)
    lane.cognitive_work = bridge.cognitive_work
    lane._uncertain = False
    lane._lock = threading.RLock()
    lane.witness = SimpleNamespace(require_idle=lambda: None)
    lane.bind_login = lambda _sid: pytest.fail("missing B Body admitted GPU")
    with pytest.raises(OwnedResidentBridgeError):
        bridge.attach_observation_only_bounded_l1(lane)


def test_actual_lane_one_bounded_submit_only_returns_nonmotor_choice(
    tmp_path, monkeypatch,
):
    case = _ready(tmp_path, monkeypatch)
    turn = _prepare(case)
    lane, token = _fake_l1(case, turn, choice="2")
    calls = []
    def submit(sid, *, work_ref, request, mode):
        calls.append((sid, work_ref, request, mode))
        return token
    async def await_result(ticket, *, timeout_s):
        assert ticket is token
        assert timeout_s == 10
        return ProviderDecision.resolved("2")
    lane.submit = submit
    lane.await_result = await_result
    original = case[1].owners["A"].retained
    receipt = asyncio.run(run_one_fresh_original_bounded_choice(
        bridge=case[1], boot=case[2], turn=turn,
        lane=lane, timeout_s=10,
    ))
    assert len(calls) == 1
    assert calls[0][0] == "A"
    assert calls[0][1].startswith("stage28c2c:")
    assert calls[0][2] is turn.request
    assert calls[0][3] is CognitionMode.BOUNDED
    assert receipt.selection_status == "DEFER"
    assert not receipt.action_issued
    assert not receipt.skill_started
    assert not receipt.intent_committed
    assert case[1].owners["A"].retained is original


def test_late_provider_result_cannot_cross_original_owner_body_epoch(
    tmp_path, monkeypatch,
):
    case = _ready(tmp_path, monkeypatch)
    turn = _prepare(case)
    lane, token = _fake_l1(case, turn, choice="1")
    lane.submit = lambda sid, *, work_ref, request, mode: token
    async def await_stale(ticket, *, timeout_s):
        case[1].owners["A"].current_worldbody_observation = None
        return ProviderDecision.resolved("1")
    lane.await_result = await_stale
    with pytest.raises(Stage28c2cL1Hold, match="stale"):
        asyncio.run(run_one_fresh_original_bounded_choice(
            bridge=case[1], boot=case[2], turn=turn,
            lane=lane,
        ))
