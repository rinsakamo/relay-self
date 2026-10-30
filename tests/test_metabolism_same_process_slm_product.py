"""Same-process S #634 B0 owner × L8 L1 × M shadow on ONE probe.

RUN ONLY inside CI's combined exact immutable S/L8 source checkouts.
Unlike separate lane contracts, the B0 readout here is produced by the
*actual S B0 owner* and SelfBody, not a manually constructed B0 model fact.
The original probe and L6 training fixtures are synthetic; this is NOT a
real physical Minecraft run, an S49 move receipt or SCIENCE qualification.
"""
from dataclasses import replace

import pytest
import test_l1_epoch_observer as l8
import test_l1_s_choice_shadow as l7
from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.self_body_m0_projection import compose_b0_cognition_views
from relay_self.l1_epoch_observer import observe_s_epoch_l1
from relay_self.l1_s_choice_shadow import SChoiceContrastStatus

from experiments.metabolism_b0_cognition import read_b0_resource_context
from experiments.metabolism_l8_resource_shadow import contrast_l8_with_m_resource
from experiments.metabolism_s_epoch_resource import observe_completed_s_resource_epoch
from experiments.metabolism_viability import Interoception


def common_epoch(*, energy=0.6, near=True, retention=True, gain=1.0,
                 cheap=False):
    kw = {"near": near, "enabled": retention}
    if not near:
        kw["tags"] = ("alpha", "novel_cue")
    if cheap:
        kw["constant_winner"] = "OPTION_B"
    initial, retained, native, choice, learned = l7.scenario(**kw)
    probe = native.observation  # SINGLE original-shaped source and request
    assert choice.probe_seq == probe.seq
    owner = B0EnergyLedger(probe.session_id, sensor=Interoception(gain=gain, quantum=0.1))
    owner.body = replace(owner.body, energy=energy)
    decision = owner.decide(probe)
    b0_views = compose_b0_cognition_views(
        probe, owner, decision, self_id=initial.identity.self_id,
        epoch_id=f"same-s-epoch-{probe.seq}",
    )
    assert b0_views.body.observation.native_seq == probe.seq
    assert b0_views.world.self_body is b0_views.body
    resource = read_b0_resource_context(
        b0_views, owner_decision=decision, config=owner.config,
        sensor=owner.sensor, noise_bound=0,
    )
    supervisor, s_epoch = l8.run_s_epoch(native, retained)
    assert s_epoch.cognition_result is not None
    assert s_epoch.cognition_result == choice
    m_epoch = observe_completed_s_resource_epoch(
        s_epoch, native=native, retained=retained, body=resource,
    )
    l_epoch = observe_s_epoch_l1(
        s_epoch, native=native, retained=retained, learning=learned,
        retention_enabled=retention,
    )
    joined = contrast_l8_with_m_resource(
        l_epoch, m_epoch, native=native, retained=retained,
        learning=learned, retention_enabled=retention,
    )
    return (
        joined, owner, decision, probe, s_epoch, supervisor,
        b0_views, resource, learned, native, retained, l_epoch, m_epoch,
    )


def test_actual_s_b0_producer_and_actual_l8_shadow_same_probe_low_energy():
    (result, owner, decision, probe, s, supervisor, views,
     resource, learning, native, retained, l8_obs, m_obs) = common_epoch()
    assert result.s_epoch is s is l8_obs.s_epoch is m_obs.s_epoch
    assert resource.native_seq == decision.probe_seq == probe.seq
    assert resource.native_source_ref == (
        f"native-probe:{probe.session_id}:{probe.seq}:{probe.request_id}"
    )
    assert views.body.sensed("m0_energy_sensor").value == decision.sensor_reading
    assert result.original_probe_sha256 in learning.admitted_current_probe_sha256
    assert result.s_choice_ref == "MOVE_AWAY"
    assert result.l1_shadow_ref == "WAIT"
    assert result.l1_status == SChoiceContrastStatus.L1_DIFFERS.value
    assert result.s_model_tension == "MOVE_MODEL_INSUFFICIENT"
    assert result.l1_candidate_model_status == "MODEL_AFFORDABLE"
    assert result.action_issues == result.learning_updates == result.habit_grants == 0
    assert result.action_authority is False
    assert owner.body.energy == 0.6
    assert owner.credit_count == 0
    assert supervisor.open_actions == ()
    assert not hasattr(result, "issue_action")


def test_same_original_s_and_l8_choices_model_energy_contrast():
    lo, hi = common_epoch(energy=0.6), common_epoch(energy=12.0)
    assert lo[0].s_choice_ref == hi[0].s_choice_ref == "MOVE_AWAY"
    assert lo[0].l1_shadow_ref == hi[0].l1_shadow_ref == "WAIT"
    assert lo[0].s_model_tension == "MOVE_MODEL_INSUFFICIENT"
    assert hi[0].s_model_tension == "NO_MODEL_TENSION"
    assert lo[0].l1_candidate_model_status == hi[0].l1_candidate_model_status


def test_far_s_wait_l8_move_is_model_insufficient_on_same_probe():
    joined, owner, _, probe, s, *_ = common_epoch(
        energy=0.6, near=False,
    )
    assert joined.s_epoch is s
    assert joined.s_choice_ref == "WAIT"
    assert joined.l1_shadow_ref == "MOVE_AWAY"
    assert joined.l1_candidate_model_status == "MODEL_INSUFFICIENT"
    assert joined.s_model_tension == "NO_MODEL_TENSION"
    assert owner.session_id == probe.session_id


def test_retention_off_is_no_l1_candidate_even_with_real_b0_sensor():
    joined, *_ = common_epoch(energy=0.6, retention=False)
    assert joined.l1_status == SChoiceContrastStatus.WITHHELD.value
    assert joined.l1_shadow_ref is None
    assert joined.l1_candidate_model_status == "NO_ADMISSIBLE_L1_CANDIDATE"


def test_gainless_b0_sensor_does_not_access_hidden_energy():
    low, high = common_epoch(energy=0.6, gain=0), common_epoch(
        energy=12.0, gain=0,
    )
    assert low[2].sensor_reading == high[2].sensor_reading
    assert low[0].s_model_tension == high[0].s_model_tension == "MOVE_MODEL_UNKNOWN"
    assert low[0].l1_candidate_model_status == "UNKNOWN"


def test_cheap_candidate_remains_cheap_not_learned_with_actual_b0_owner():
    joined, *_ = common_epoch(energy=0.6, cheap=True)
    assert joined.l1_status == SChoiceContrastStatus.CHEAP_DIFFERS.value
    assert joined.l1_shadow_ref == "WAIT"


@pytest.mark.parametrize("attack", (
    "b0_other_probe", "b0_tampered_decision", "foreign_learning",
    "foreign_epoch", "foreign_b0_owner_ref", "tampered_l8_candidate",
))
def test_original_owner_and_l8_admission_fail_closed(attack):
    data = common_epoch()
    (joined, owner, decision, probe, s, supervisor, views,
     resource, learning, native, retained, l8_obs, m_obs) = data
    if attack == "b0_other_probe":
        probe = replace(probe, seq=probe.seq + 1)
        with pytest.raises(ValueError):
            read_b0_resource_context(
                views, owner_decision=replace(decision, probe_seq=probe.seq),
                config=owner.config, sensor=owner.sensor, noise_bound=0,
            )
        return
    if attack == "b0_tampered_decision":
        with pytest.raises(ValueError):
            read_b0_resource_context(
                views, owner_decision=replace(
                    decision, sensor_reading=decision.sensor_reading + 1,
                ), config=owner.config, sensor=owner.sensor, noise_bound=0,
            )
        return
    if attack == "foreign_learning":
        learning = replace(learning, current=replace(
            learning.current, session_id="foreign",
        ))
    elif attack == "foreign_epoch":
        l8_obs = replace(l8_obs, s_epoch=replace(s))
    elif attack == "foreign_b0_owner_ref":
        m_obs = replace(m_obs, body=replace(
            resource, owner_sensor_ref="forged",
        ))
    else:
        l8_obs = replace(l8_obs, comparison=replace(
            l8_obs.comparison, l1_shadow_ref="MOVE_AWAY",
        ))
    with pytest.raises(ValueError):
        contrast_l8_with_m_resource(
            l8_obs, m_obs, native=native, retained=retained,
            learning=learning, retention_enabled=True,
        )
