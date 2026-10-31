"""Same-process S #634 B0 owner × L8 L1 × M shadow on ONE probe.

RUN ONLY inside CI's combined exact immutable S/L8 source checkouts.
Unlike separate lane contracts, the B0 readout here is produced by the
*actual S B0 owner* and SelfBody, not a manually constructed B0 model fact.
The original probe and L6 training fixtures are synthetic; this is NOT a
real physical Minecraft run, an S49 move receipt or SCIENCE qualification.
"""
import json
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
from experiments.metabolism_s_l_m_post_epoch import (
    SLMPostEpochRejected,
    read_s_l_m_after_owner_epoch,
)
from experiments.metabolism_slm_dev_host_tap import (
    SLMDevTapResult,
    bounded_s_l_m_audit_row,
    observe_optional_s_l_m_dev,
)
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


def passive_tap(data, *, b0_decision=None, probe=None, native=None,
                learning=None, retention_enabled=True, noise_bound=0):
    (joined, owner, original, original_probe, s_epoch, _supervisor,
     _views, _resource, retained_learning, original_native,
     retained, *_rest) = data
    return read_s_l_m_after_owner_epoch(
        probe=original_probe if probe is None else probe,
        native=original_native if native is None else native,
        ledger=owner,
        original_b0_decision=original if b0_decision is None else b0_decision,
        original_s_epoch=s_epoch,
        retained=retained,
        self_id=retained_learning.cognition.identity.self_id,
        epoch_id=f"same-s-epoch-{original_probe.seq}",
        learning=retained_learning if learning is None else learning,
        retention_enabled=retention_enabled,
        noise_bound=noise_bound,
    )


def test_one_call_read_only_s_l_m_owner_post_epoch_tap_matches_manual_join():
    data = common_epoch(energy=0.6)
    owner, supervisor = data[1], data[5]
    before = (owner.body, owner.credit_count, owner._last_decision_seq,
              owner._last_eat_seq, supervisor.open_actions)
    readout = passive_tap(data)
    assert readout.m == data[12]
    assert readout.l8_m == data[0]
    assert readout.l8_m.s_epoch is data[4]
    assert readout.session_id == data[3].session_id
    assert readout.probe_seq == data[3].seq
    assert readout.b0_original_l0_kind == data[2].kind
    assert not readout.action_authority
    assert (
        readout.action_issues, readout.new_native_reads,
        readout.new_cognition_calls, readout.learning_updates,
        readout.habit_grants, readout.food_credits,
    ) == (0, 0, 0, 0, 0, 0)
    assert before == (owner.body, owner.credit_count, owner._last_decision_seq,
                      owner._last_eat_seq, supervisor.open_actions)
    assert not hasattr(readout, "authorize") and not hasattr(readout, "issue")


def test_no_learning_snapshot_is_an_explicit_m_only_passive_mode():
    data = common_epoch(energy=0.6)
    _, owner, original, probe, s_epoch, _, _, _, _learned, native, retained, *_ = data
    result = read_s_l_m_after_owner_epoch(
        probe=probe, native=native, ledger=owner,
        original_b0_decision=original,
        original_s_epoch=s_epoch, retained=retained,
        self_id="post-only", epoch_id="one", noise_bound=0,
    )
    assert result.m.choice.value == "MOVE_AWAY"
    assert result.l8_m is None
    assert result.new_cognition_calls == result.action_issues == 0


def test_no_sensor_noise_calibration_gives_unknown_not_false_safety():
    data = common_epoch(energy=0.6)
    result = passive_tap(data, noise_bound=None)
    assert result.m.modeled_tension == "MOVE_MODEL_UNKNOWN"
    assert result.l8_m.l1_candidate_model_status == "UNKNOWN"


@pytest.mark.parametrize("attack", (
    "copied_probe", "stale_decision", "advance_ledger", "wrong_l8_flag",
))
def test_passive_tap_rejects_stale_or_foreign_original_owner_source(attack):
    data = common_epoch()
    owner, original, probe = data[1], data[2], data[3]
    kw = {}
    if attack == "copied_probe":
        kw["probe"] = replace(probe)
    elif attack == "stale_decision":
        kw["b0_decision"] = replace(original, body_tick=original.body_tick + 1)
    elif attack == "advance_ledger":
        owner.step("WAIT")
    else:
        kw["retention_enabled"] = None
    with pytest.raises(SLMPostEpochRejected):
        passive_tap(data, **kw)


def host_tap(data, *, enabled=True, learning_on=True, **changes):
    (_, owner, decision, probe, s_epoch, _supervisor,
     _views, _resource, learned, native, retained, *_rest) = data
    arguments = dict(
        enabled=enabled, original_s_epoch=s_epoch,
        probe=probe, native=native, ledger=owner,
        original_b0_decision=decision,
        retained=retained,
        self_id=learned.cognition.identity.self_id,
        epoch_id=f"same-s-epoch-{probe.seq}",
        learning=learned if learning_on else None,
        retention_enabled=True if learning_on else None,
        noise_bound=0,
    )
    arguments.update(changes)
    return observe_optional_s_l_m_dev(**arguments)


def test_optional_host_tap_disabled_is_truly_inert_with_missing_source():
    class MustNotRead:
        def __getattribute__(self, name):
            raise AssertionError("optional tap must not inspect World when disabled")

    original = object()
    result = observe_optional_s_l_m_dev(
        original_s_epoch=original, enabled=False,
        probe=MustNotRead(), ledger=MustNotRead(), native=MustNotRead(),
    )
    assert result.original_s_epoch is original
    assert result.status == "DISABLED"
    audit = bounded_s_l_m_audit_row(result)
    assert audit["status"] == "DISABLED"
    assert audit["session_id"] is None and audit["m_model_tension"] is None
    assert "MustNotRead" not in json.dumps(audit)
    assert "original_s_epoch" not in audit


def test_original_s_owner_host_tap_produces_bounded_no_action_audit():
    data = common_epoch(energy=0.6)
    owner = data[1]
    before = (owner.body, owner.credit_count, data[5].last_at_ns)
    tap = host_tap(data)
    assert tap.status == "RECORDED", tap.reason
    assert tap.original_s_epoch is data[4]
    assert tap.s_choice == "MOVE_AWAY"
    assert tap.l1_candidate == "WAIT"
    assert tap.m_model_tension == "MOVE_MODEL_INSUFFICIENT"
    assert tap.l1_model_status == "MODEL_AFFORDABLE"
    row = bounded_s_l_m_audit_row(tap)
    assert row["schema"] == "SLM_PASSIVE_DEV_AUDIT_V1"
    assert row["request_id"] == data[3].request_id
    assert not row["native_source_attested"] and not row["action_authority"]
    assert row["new_cognition_calls"] == row["action_issues"] == 0
    assert row["learning_updates"] == row["food_credits"] == 0
    assert "energy" not in json.dumps(row).lower()
    assert "body" not in json.dumps(row).lower()
    assert before == (owner.body, owner.credit_count, data[5].last_at_ns)
    assert data[5].open_actions == ()


def test_host_tap_missing_learning_has_no_unearned_candidate():
    data = common_epoch()
    tap = host_tap(data, learning_on=False)
    assert tap.status == "RECORDED"
    assert tap.s_choice == "MOVE_AWAY"
    assert tap.l1_candidate is tap.l1_status is tap.l1_model_status is None


def test_host_tap_missing_sensor_bound_does_not_infer_true_energy():
    data = common_epoch(energy=0.6)
    tap = host_tap(data, noise_bound=None)
    assert tap.status == "RECORDED"
    assert tap.m_model_tension == "MOVE_MODEL_UNKNOWN"
    assert tap.l1_model_status == "UNKNOWN"


@pytest.mark.parametrize("attack", (
    "stale", "copied_probe", "foreign_learning", "no_true_enable",
))
def test_failed_observer_cannot_abort_original_s_epoch_or_change_owner(attack):
    data = common_epoch()
    original_s, owner, probe, learned = data[4], data[1], data[3], data[8]
    before = (owner.body, owner.credit_count, owner._last_decision_seq,
              data[5].last_at_ns, data[5].open_actions, learned.cognition)
    changed = {}
    if attack == "stale":
        changed["original_b0_decision"] = replace(
            data[2], body_tick=data[2].body_tick + 1,
        )
    elif attack == "copied_probe":
        changed["probe"] = replace(probe)
    elif attack == "foreign_learning":
        changed["learning"] = replace(
            learned, current=replace(learned.current, session_id="foreign"),
        )
    else:
        changed["enabled"] = "yes"
    result = host_tap(data, **changed)
    if attack == "no_true_enable":
        assert result.status == "DISABLED" and result.reason == "invalid_flag"
    else:
        assert result.status == "DEFERRED"
        assert result.reason == "owner_source_or_scope_rejected"
    assert result.original_s_epoch is original_s
    row = bounded_s_l_m_audit_row(result)
    assert row["request_id"] is None and row["l1_candidate"] is None
    assert row["action_issues"] == row["new_native_reads"] == 0
    assert before == (owner.body, owner.credit_count, owner._last_decision_seq,
                      data[5].last_at_ns, data[5].open_actions, learned.cognition)


def test_unexpected_optional_observer_exception_is_sanitized_and_nonblocking(monkeypatch):
    data = common_epoch()
    from experiments import metabolism_slm_dev_host_tap as tap_module

    def broken(**_kwargs):
        raise RuntimeError("SENSITIVE_HIDDEN_ENERGY_AND_RAW_BYTES")

    monkeypatch.setattr(tap_module, "read_s_l_m_after_owner_epoch", broken)
    result = host_tap(data)
    assert result.status == "OBSERVER_ERROR"
    assert result.original_s_epoch is data[4]
    row = bounded_s_l_m_audit_row(result)
    assert "SENSITIVE" not in json.dumps(row)
    assert all(v == 0 for k, v in row.items() if k in (
        "action_issues", "new_cognition_calls", "food_credits",
    ))


def test_interrupt_is_not_swallowed_by_optional_dev_telemetry(monkeypatch):
    data = common_epoch()
    from experiments import metabolism_slm_dev_host_tap as tap_module

    def interrupt(**_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(tap_module, "read_s_l_m_after_owner_epoch", interrupt)
    with pytest.raises(KeyboardInterrupt):
        host_tap(data)


def test_audit_row_rejects_forged_authority_or_unadmitted_source():
    data = common_epoch()
    good = host_tap(data)
    with pytest.raises(ValueError):
        bounded_s_l_m_audit_row(replace(good, action_authority=True))
    with pytest.raises(ValueError):
        bounded_s_l_m_audit_row(replace(good, food_credits=1))
    with pytest.raises(ValueError):
        bounded_s_l_m_audit_row(replace(good, session_id="bad\nraw"))
    with pytest.raises(ValueError):
        bounded_s_l_m_audit_row(replace(good, request_id="x" * 300))
    bad = SLMDevTapResult(data[4], "DEFERRED",
                          "owner_source_or_scope_rejected", s_choice="WAIT")
    with pytest.raises(ValueError):
        bounded_s_l_m_audit_row(bad)
