"""I2: original B/E exploration handoff, strictly CPU/offline synthetic evidence."""
from __future__ import annotations

import time
from dataclasses import replace

import pytest

from adapters.mineflayer.sense_projection import sense_from_native
from relay_self.cognitive_minimal_dev import Predicate
from relay_self.common_io import ScopeRef
from relay_self.i_lane_i2_original_exploration_handoff_dev import (
    I2OriginalGoalHold,
    prepare_i2_original_goal_handoff,
    verify_i2_original_goal_handoff,
)
from relay_self.innate_schema import SchemaSnapshot
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_i_lane_e2c_original_present_dev import _inject
from test_stage28c2c_fresh_recovered_l1_dev import _ready


def _correlate(bridge, world, sid: str):
    """Synthetic same-session probe then later unrelated passive event."""
    frame = _inject(bridge, world, sid)
    native = frame.observation.session_id
    request_id = "i1-original-sense-" + ("a" if sid == "A" else "b") * 32
    matched = sense_from_native(
        replace(frame.observation, kind="probe", request_id=request_id, seq=4),
        scope=ScopeRef(sid, world.paper_session_id),
        expected_native_session=native, previous_seq=3,
        expected_request_id=request_id,
    )
    passive = sense_from_native(
        replace(frame.observation, kind="move", request_id=None, seq=5),
        scope=matched.scope, expected_native_session=native, previous_seq=4,
    )
    bridge._i1_correlated_sense = getattr(bridge, "_i1_correlated_sense", {})
    bridge._i1_correlated_received_at = getattr(
        bridge, "_i1_correlated_received_at", {},
    )
    bridge._i1_correlated_sense[sid] = matched
    bridge._i1_correlated_received_at[sid] = time.monotonic()
    bridge._sense[sid] = passive
    bridge._sense_received_at[sid] = time.monotonic()
    return matched


def _args(case, sid):
    return {
        "bridge": case[1], "boot": case[2], "world": case[3],
        "links": case[4], "self_id": sid,
    }


def _configured_both(tmp_path, monkeypatch, *, exploration=True):
    if exploration:
        case = _configured(tmp_path, monkeypatch, need=True)
    else:
        # Same old-generation registry as the real I1 restored A/B. No
        # exploration Pattern is auto-added to make a test pass.
        original_bind = ResidentCognitiveWorkOwner.bind_login

        def attach_original_empty(resident, *, self_id, **kwargs):
            registry = resident.owners[self_id].pattern_registry
            assert registry.revision == 0
            # Restored original Self keeps innate hunger/defense/oxygen
            # patterns; only the exploration Goal was never installed.
            assert registry.patterns
            assert not any(p.predicate is Predicate.EXPLORE
                           for p in registry.patterns)
            resident.register_present_schema(
                self_id, SchemaSnapshot(self_id, registry.revision, ()),
            )
            return original_bind(resident, self_id=self_id, **kwargs)

        monkeypatch.setattr(
            ResidentCognitiveWorkOwner, "bind_login", attach_original_empty,
        )
        case = _ready(tmp_path, monkeypatch)
    for sid in ("A", "B"):
        _correlate(case[1], case[3], sid)
    return case


def test_i2_both_original_accepted_exploration_patterns_form_only_candidates(
    tmp_path, monkeypatch,
):
    case = _configured_both(tmp_path, monkeypatch)
    owners = case[1].owners
    before = _files(case[1])
    before_intent = {
        sid: (owners[sid].retained, owners[sid].intent,
              owners[sid].pattern_registry, tuple(owners[sid].pending_questions))
        for sid in ("A", "B")
    }
    prepared = [prepare_i2_original_goal_handoff(**_args(case, sid))
                for sid in ("A", "B")]
    for sid, value in zip(("A", "B"), prepared, strict=True):
        assert value.status == "EXPLORATION_GOAL_UNRESOLVED_TARGET"
        assert value.need_signal_ref.startswith("exploration-need:")
        assert value.question_candidate_ref.startswith("coverage-inquiry:v1:")
        assert len(value.goal_candidates) == 1
        assert value.goal_candidates[0].goal_id == "EXPLORE_WORLD"
        assert value.goal_candidates[0].unresolved
        assert value.native_request_id == case[1]._i1_correlated_sense[sid].observation.request_id
        assert value.native_seq == 4
        assert value.source_revision_refs[-1] == value.sense_revision
        assert tuple(x.description for x in value.bounded_request.choices) == (
            "ESCALATE_L2", "DEFER",
        )
        assert not value.bounded_request.think_allowed
        assert value.bounded_request.identity_context is not None
        assert not value.model_invoked and not value.goal_adopted
        assert not value.question_adopted and not value.intent_committed
        assert not value.action_issue_authorized
        verify_i2_original_goal_handoff(
            **{k: v for k, v in _args(case, sid).items() if k != "self_id"},
            handoff=value,
        )
    assert prepared[0].question_candidate_ref != prepared[1].question_candidate_ref
    assert prepared[0].bounded_request.request_id != prepared[1].bounded_request.request_id
    assert _files(case[1]) == before
    for sid in ("A", "B"):
        assert before_intent[sid] == (
            owners[sid].retained, owners[sid].intent,
            owners[sid].pattern_registry, tuple(owners[sid].pending_questions),
        )


def test_i2_old_restored_registry_does_not_get_invented_exploration(
    tmp_path, monkeypatch,
):
    case = _configured_both(tmp_path, monkeypatch, exploration=False)
    before = _files(case[1])
    for sid in ("A", "B"):
        handoff = prepare_i2_original_goal_handoff(**_args(case, sid))
        assert handoff.status == "NO_QUALIFIED_EXPLORATION_GOAL"
        assert handoff.need_signal_ref is None
        assert handoff.question_candidate_ref is None
        assert handoff.goal_candidates == ()
        assert [x.description for x in handoff.bounded_request.choices] == [
            "ESCALATE_L2", "DEFER",
        ]
        verify_i2_original_goal_handoff(
            **{k: v for k, v in _args(case, sid).items() if k != "self_id"},
            handoff=handoff,
        )
    assert _files(case[1]) == before


@pytest.mark.parametrize("failure", [
    "foreign-self", "altered-question", "invented-goal",
    "request-swap", "request-nonhex", "request-content", "request-identity",
    "wrong-hash", "fake-selected", "foreign-need",
])
def test_i2_frozen_handoff_rejects_fabrication(
    tmp_path, monkeypatch, failure,
):
    case = _configured_both(tmp_path, monkeypatch)
    value = prepare_i2_original_goal_handoff(**_args(case, "A"))
    if failure == "foreign-self":
        value = replace(value, self_id="B")
    elif failure == "altered-question":
        value = replace(value, question_candidate_ref="coverage-inquiry:v1:" + "0" * 64)
    elif failure == "invented-goal":
        value = replace(value, goal_candidates=())
    elif failure == "request-swap":
        value = replace(value, bounded_request=replace(
            value.bounded_request, request_id="i2-original-B-" + "f" * 32,
        ))
    elif failure == "request-nonhex":
        value = replace(value, bounded_request=replace(
            value.bounded_request, request_id="i2-original-A-" + "Z" * 32,
        ))
    elif failure == "request-content":
        value = replace(value, bounded_request=replace(
            value.bounded_request, instruction="fabricated instruction",
        ))
    elif failure == "request-identity":
        value = replace(value, bounded_request=replace(
            value.bounded_request, identity_context=None,
        ))
    elif failure == "wrong-hash":
        value = replace(value, material_sha256="0" * 64)
    elif failure == "fake-selected":
        value = replace(value, model_invoked=True)
    else:
        value = replace(value, need_signal_ref="fake-need")
    with pytest.raises(I2OriginalGoalHold):
        verify_i2_original_goal_handoff(
            **{k: v for k, v in _args(case, "A").items() if k != "self_id"},
            handoff=value,
        )


@pytest.mark.parametrize("failure", [
    "next-native", "foreign-probe", "paper-growth",
    "registry-revision", "owner-fenced", "same-session-new-request",
    "source-expiry",
])
def test_i2_stale_original_source_never_adopts_previous_goal_or_question(
    tmp_path, monkeypatch, failure,
):
    case = _configured_both(tmp_path, monkeypatch)
    bridge = case[1]
    value = prepare_i2_original_goal_handoff(**_args(case, "A"))
    if failure == "next-native":
        old = bridge._i1_correlated_sense["A"]
        bridge._i1_correlated_sense["A"] = replace(
            old, observation=replace(
                old.observation, seq=5,
            ), source_revision_ref=f"mineflayer:{old.observation.session_id}:5",
        )
    elif failure == "foreign-probe":
        old = bridge._i1_correlated_sense["A"]
        bridge._i1_correlated_sense["A"] = replace(
            old, observation=replace(old.observation, session_id="foreign"),
        )
    elif failure == "paper-growth":
        with bridge.paper._log_path.open("ab") as handle:
            handle.write(b"new complete Paper log line\n")
    elif failure == "registry-revision":
        old_registry = bridge.owners["A"].pattern_registry
        bridge.owners["A"].pattern_registry = replace(
            old_registry, revision=old_registry.revision + 1,
        )
    elif failure == "owner-fenced":
        bridge.cognitive_work.fence_self("A")
    elif failure == "same-session-new-request":
        old = bridge._i1_correlated_sense["A"]
        bridge._i1_correlated_sense["A"] = replace(
            old, observation=replace(
                old.observation,
                request_id="i1-original-sense-" + "c" * 32,
            ),
        )
    else:
        bridge._i1_correlated_received_at["A"] = time.monotonic() - 30
    with pytest.raises(I2OriginalGoalHold):
        verify_i2_original_goal_handoff(
            **{k: v for k, v in _args(case, "A").items() if k != "self_id"},
            handoff=value,
        )


def test_i2_no_saved_pattern_rejects_injected_goal_without_current_need(
    tmp_path, monkeypatch,
):
    case = _configured_both(tmp_path, monkeypatch, exploration=False)
    val = prepare_i2_original_goal_handoff(**_args(case, "A"))
    from relay_self.cognitive_minimal_dev import Goal

    forged = replace(val, goal_candidates=(
        Goal("EXPLORE_WORLD", "exploration", "MOVE", 1, "ACTIVE", True),
    ))
    with pytest.raises(I2OriginalGoalHold):
        verify_i2_original_goal_handoff(
            **{k: v for k, v in _args(case, "A").items() if k != "self_id"},
            handoff=forged,
        )


def test_i2_source_only_from_original_owner_no_other_l1_ticket(
    tmp_path, monkeypatch,
):
    case = _configured_both(tmp_path, monkeypatch)
    value = prepare_i2_original_goal_handoff(**_args(case, "A"))
    assert case[1].inference_lane is None
    assert value.bounded_request.request_id.startswith("i2-original-A-")
    assert value.material_sha256 and len(value.material_sha256) == 64
    assert case[1].physical.active_action_ids == ()
