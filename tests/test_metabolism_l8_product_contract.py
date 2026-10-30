"""M × L8 cross-branch original API test, source-shaped DEV-only.

Run with pinned L8 checkout and *original* L8 scenario and coordinator.
The B0 resource value is a deliberately synthetic model fact for the *same*
probe; separate pinned S #634 tests exercise the genuine B0 owner path.
There is no real L8+B0 producer deployed or native World attestation.
"""
from dataclasses import replace

import pytest
import test_l1_epoch_observer as l8
import test_l1_s_choice_shadow as l7

from experiments.metabolism_b0_cognition import B0CognitiveResourceView, B0TickResourceFact
from experiments.metabolism_l8_resource_shadow import contrast_l8_with_m_resource
from experiments.metabolism_s_epoch_resource import observe_completed_s_resource_epoch
from relay_self.l1_epoch_observer import observe_s_epoch_l1
from relay_self.l1_s_choice_shadow import SChoiceContrastStatus
from relay_self.world_conditioned_choice import WorldChoiceKind


def scenario(*, energy=0.6, near=True, enabled=True, tags=None, cheap=False):
    kw = {"near": near, "enabled": enabled}
    if tags is not None:
        kw["tags"] = tags
    if cheap:
        kw["constant_winner"] = "OPTION_B"
    _, retained, native, choice, learned = l7.scenario(**kw)
    _, original_s = l8.run_s_epoch(native, retained)
    assert original_s.cognition_result == choice
    sid = choice.session_id
    probe = choice.probe_seq
    request = choice.request_id
    # Synthetic B0 sensor *projection* constrained to exact L8 native source.
    # Only the B0 owner from separate S product CI may produce true handoffs.
    statuses = (
        "MODEL_AFFORDABLE" if energy > 0.5 else "MODEL_INSUFFICIENT",
        "MODEL_AFFORDABLE" if energy > 0.75 else "MODEL_INSUFFICIENT",
    )
    body = B0CognitiveResourceView(
        self_id="L8-synthetic-self",
        session_id=sid,
        epoch_id=f"l8-probe-{probe}",
        native_seq=probe,
        owner_tick=0,
        original_l0_kind="WAIT",
        native_source_ref=f"native-probe:{sid}:{probe}:{request}",
        owner_sensor_ref=f"{sid}:0:{probe}:{request}",
        energy_lower=energy,
        energy_upper=energy,
        facts=(
            B0TickResourceFact("WAIT", 0.5, statuses[0], "SYNTHETIC_B0_MODEL"),
            B0TickResourceFact("MOVE", 0.75, statuses[1], "SYNTHETIC_B0_MODEL"),
        ),
    )
    m = observe_completed_s_resource_epoch(
        original_s, native=native, retained=retained, body=body,
    )
    l = observe_s_epoch_l1(
        original_s, native=native, retained=retained,
        learning=learned, retention_enabled=enabled,
    )
    return original_s, native, retained, learned, m, l, enabled


def join(data, *, m=None, l=None, native=None, retained=None, learning=None,
         enabled=None):
    _, n, r, lr, mr, lo, flag = data
    return contrast_l8_with_m_resource(
        lo if l is None else l,
        mr if m is None else m,
        native=n if native is None else native,
        retained=r if retained is None else retained,
        learning=lr if learning is None else learning,
        retention_enabled=flag if enabled is None else enabled,
    )


def test_original_l8_l1_wait_vs_s_move_with_model_energy_tension():
    data = scenario(energy=0.6)
    result = join(data)
    assert result.s_epoch is data[0]
    assert result.l8 is data[5]
    assert result.m_resource is data[4]
    assert result.s_choice_ref == "MOVE_AWAY"
    assert result.l1_shadow_ref == "WAIT"
    assert result.l1_status == SChoiceContrastStatus.L1_DIFFERS.value
    assert result.l1_candidate_model_status == "MODEL_AFFORDABLE"
    assert result.s_model_tension == "MOVE_MODEL_INSUFFICIENT"
    assert result.s_choice_kept
    assert not result.action_authority
    assert result.action_issues == result.learning_updates == result.habit_grants == 0
    assert not hasattr(result, "choose_action")
    assert not hasattr(result, "utility")
    assert not hasattr(result, "reward")


def test_high_energy_changes_m_readout_but_neither_s_nor_l8_selection():
    low = join(scenario(energy=0.6))
    high = join(scenario(energy=12.0))
    assert low.s_choice_ref == high.s_choice_ref == "MOVE_AWAY"
    assert low.l1_shadow_ref == high.l1_shadow_ref == "WAIT"
    assert low.s_model_tension == "MOVE_MODEL_INSUFFICIENT"
    assert high.s_model_tension == "NO_MODEL_TENSION"
    assert high.l1_candidate_model_status == "MODEL_AFFORDABLE"


def test_far_s_wait_and_l1_move_candidate_model_may_be_insufficient():
    data = scenario(energy=0.6, near=False, tags=("alpha", "novel_cue"))
    result = join(data)
    assert result.s_choice_ref == "WAIT"
    assert result.l1_shadow_ref == "MOVE_AWAY"
    assert result.l1_candidate_model_status == "MODEL_INSUFFICIENT"
    assert result.s_model_tension == "NO_MODEL_TENSION"


def test_retention_off_does_not_promote_shadow_candidate():
    data = scenario(energy=0.6, enabled=False)
    result = join(data)
    assert result.l1_status == SChoiceContrastStatus.WITHHELD.value
    assert result.l1_shadow_ref is None
    assert result.l1_candidate_model_status == "NO_ADMISSIBLE_L1_CANDIDATE"
    assert result.s_choice_ref == "MOVE_AWAY"


def test_l1_cheap_equivalent_is_not_attributed_to_learning():
    data = scenario(cheap=True)
    result = join(data)
    assert result.l1_status == SChoiceContrastStatus.CHEAP_DIFFERS.value
    assert result.l1_shadow_ref == "WAIT"
    assert result.action_authority is False


def test_reread_does_not_change_source_memory_or_s_owner():
    data = scenario(energy=0.6)
    before = (data[0], data[3].cognition, data[4], data[5])
    a, b = join(data), join(data)
    assert a == b
    assert before == (data[0], data[3].cognition, data[4], data[5])
    assert a.s_epoch is data[0]


@pytest.mark.parametrize("attack", (
    "other_epoch", "foreign_session", "foreign_probe", "altered_s_choice",
    "altered_l8_choice", "altered_l8_status", "altered_l8_probe_sha",
    "lost_admission", "action_authority_l8", "action_authority_m",
    "bad_l8_work_ids", "bad_l8_digest", "retention_mismatch",
    "foreign_native", "fake_l1_candidate", "bad_m_scope",
    "fake_source_owner_tick",
))
def test_forged_cross_lane_context_or_proposal_rejected(attack):
    data = scenario()
    s, native, retained, learning, m, l, enabled = data
    if attack == "other_epoch":
        other = scenario()
        l = replace(l, s_epoch=replace(other[0]))
    elif attack == "foreign_session":
        m = replace(m, body=replace(m.body, session_id="foreign"))
    elif attack == "foreign_probe":
        m = replace(m, body=replace(m.body, native_seq=m.body.native_seq + 1))
    elif attack == "altered_s_choice":
        m = replace(m, choice=WorldChoiceKind.WAIT)
    elif attack == "altered_l8_choice":
        l = replace(l, comparison=replace(
            l.comparison, s_choice=WorldChoiceKind.WAIT,
        ))
    elif attack == "altered_l8_status":
        l = replace(l, comparison=replace(
            l.comparison, status=SChoiceContrastStatus.AGREES,
        ))
    elif attack == "altered_l8_probe_sha":
        l = replace(l, comparison=replace(
            l.comparison, original_probe_sha256="0" * 64,
        ))
    elif attack == "lost_admission":
        learning = replace(learning, admitted_current_probe_sha256=frozenset())
    elif attack == "action_authority_l8":
        l = replace(l, action_authority=True)
    elif attack == "action_authority_m":
        m = replace(m, action_authority=True)
    elif attack == "bad_l8_work_ids":
        l = replace(l, planned_work_ids=("foreign-work",))
    elif attack == "bad_l8_digest":
        l = replace(l, comparison=replace(
            l.comparison, candidate_differs=False,
        ))
    elif attack == "retention_mismatch":
        enabled = False
    elif attack == "foreign_native":
        native = replace(native, request_id="wrong-request")
    elif attack == "fake_l1_candidate":
        l = replace(l, comparison=replace(
            l.comparison, l1_shadow_ref="SOME_OTHER_ACTION",
        ))
    elif attack == "bad_m_scope":
        m = replace(m, source_scope="PHYSICAL_ATTESTED")
    else:
        m = replace(m, body=replace(m.body, owner_tick=99999))
    with pytest.raises(ValueError):
        join(data, m=m, l=l, native=native, retained=retained,
             learning=learning, enabled=enabled)
