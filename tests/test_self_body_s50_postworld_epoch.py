"""Post-shutdown INTERNAL cognition epoch: previous real-type prior, no Present.

Fixture source is SYNTHETIC original-typed S16/native and S50, not a new
Minecraft World or an authentic later physical epoch.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_original_closure import (
    SelfBodyS50ClosedOwnerLease,
)
from adapters.mineflayer.self_body_s50_postworld_epoch import (
    PostWorldInternalEpochLease,
    PostWorldInternalEpochRejected,
)
from relay_self.self_body import BodyOrigin
from test_self_body_s50_motion_companion import s50
from test_self_body_s50_original_closure import synthetic_original_closed


def prior():
    lease = SelfBodyS50ClosedOwnerLease(self_id="self")
    try:
        lease.observe_original_closed(synthetic_original_closed())
        result = lease.consume_s50_once(s50())
        assert result.self_body.observation is not None
        return result
    finally:
        lease.close()


def test_postworld_internal_epoch_reads_old_experience_and_not_current_world_state():
    earlier = prior()
    epoch = PostWorldInternalEpochLease(earlier)
    assert epoch.status()["status"] == "AWAITING_ORIGINAL_WORLD_SHUTDOWN"
    result = epoch.enter_after_owner_shutdown(node_exit=0, java_exit=0)
    assert epoch.status()["status"] == "INTERNAL_EPOCH_PRIOR_EXPERIENCE_READ_ONCE"
    assert epoch.status()["internal_epoch_reads"] == 1
    assert result["previous_action_id"] == earlier.action_id
    assert result["previous_native_ref"] == earlier.self_body.observation.source_ref
    assert result["previous_paper_sha256"] == earlier.paper_source_sha256
    assert result["previous_input_off_sampled_motion_ticks"] == (251, 252)
    assert result["previous_paper_samples"] == 8
    assert result["current_position_x"] is None
    assert result["current_body_observation"] == "UNKNOWN_NO_NEW_NATIVE_PRESENT"
    assert result["current_world_observation"] == "UNKNOWN_NO_NEW_NATIVE_PRESENT"
    assert not result["native_present_acquired_in_this_epoch"]
    assert not result["new_world_or_client_session"]
    assert not result["goal_admitted"]
    assert result["learning_updates"] == 0
    assert result["actions_issued"] == 0
    assert result["p1_wait_granted"] == 0
    assert result["full_tick_input_idle"] == "NOT_ATTESTED"
    assert result["physical_stability_attested"] is False
    assert epoch.status()["original_native_probes_requested"] == 0
    assert epoch.status()["new_action_issuers"] == 0
    assert epoch.status()["memory_writes"] == 0
    with pytest.raises(PostWorldInternalEpochRejected):
        epoch.enter_after_owner_shutdown(node_exit=0, java_exit=0)


@pytest.mark.parametrize("exit_args", [
    {"node_exit": 1, "java_exit": 0},
    {"node_exit": 0, "java_exit": -1},
    {"node_exit": None, "java_exit": 0},
    {"node_exit": False, "java_exit": 0},
    {"node_exit": 0, "java_exit": 0, "cleanup_errors": True},
    {"node_exit": 0, "java_exit": 0, "cleanup_errors": 1},
])
def test_missing_or_failed_shutdown_never_admits_internal_epoch(exit_args):
    lease = PostWorldInternalEpochLease(prior())
    with pytest.raises(PostWorldInternalEpochRejected):
        lease.enter_after_owner_shutdown(**exit_args)
    assert lease.status()["internal_epoch_reads"] == 0
    assert lease.status()["status"] == "REJECTED_WORLD_NOT_CLOSED"
    with pytest.raises(PostWorldInternalEpochRejected):
        lease.enter_after_owner_shutdown(node_exit=0, java_exit=0)


def test_expiration_without_shutdown_cannot_be_used():
    lease = PostWorldInternalEpochLease(prior())
    lease.close()
    assert lease.status()["status"] == "EXPIRED_NO_WORLD_SHUTDOWN"
    with pytest.raises(PostWorldInternalEpochRejected):
        lease.enter_after_owner_shutdown(node_exit=0, java_exit=0)


@pytest.mark.parametrize("wrong", [
    "no_s16", "other_action", "new_native_claim", "false_stop",
    "p1_wait", "wrong_clock", "no_self_id", "not_a_typed_source",
])
def test_prior_action_source_fail_closed(wrong):
    old = prior()
    if wrong == "no_s16":
        body = replace(old.self_body, outcome=None)
        old = replace(old, self_body=body)
    elif wrong == "other_action":
        old = replace(old, action_id="foreign-action")
    elif wrong == "new_native_claim":
        old = replace(old, native_present_minted=True)
    elif wrong == "false_stop":
        old = replace(old, physically_stopped_attested=True)
    elif wrong == "p1_wait":
        old = replace(old, p1_wait_granted=True)
    elif wrong == "wrong_clock":
        old = replace(old, world_client_clock_alignment="CLAIMED_ALIGNED")
    elif wrong == "no_self_id":
        old = replace(old, self_body=replace(old.self_body, self_id=None))
    else:
        old = {"fake": "report-json"}
    with pytest.raises(PostWorldInternalEpochRejected):
        PostWorldInternalEpochLease(old)


def test_original_owner_core_no_physical_value_from_prior_paper():
    from relay_self.self_body import compose_self_body_view
    from relay_self.self_world import compose_self_world_view
    old = prior()
    epoch = "internal-after-closed-world-12-move1"
    current = compose_self_body_view(
        self_id=old.self_body.self_id, session_id=old.self_body.session_id,
        epoch_id=epoch,
    )
    world = compose_self_world_view(
        self_id=old.self_body.self_id, session_id=old.self_body.session_id,
        epoch_id=epoch, self_body=current,
    )
    assert world.observation is None
    assert world.self_body is current
    assert current.outcome is None
    assert current.observation is None
    assert current.observed("position_x").origin is BodyOrigin.UNKNOWN
    assert current.observed("paper_motion").origin is BodyOrigin.UNKNOWN


def test_world_runner_has_explicit_default_off_postworld_flag():
    import inspect

    from adapters.mineflayer import self_body_s50_world_dev as host
    signature = inspect.signature(host.qualify)
    assert signature.parameters["postworld_internal_epoch_dev"].default is False


def test_real_host_postworld_callsite_projects_one_prior_experience_with_no_present():
    from adapters.mineflayer.self_body_s50_world_dev import (
        review_postworld_internal_epoch,
    )
    old = prior()
    result = review_postworld_internal_epoch(
        old, node_exit=0, server_exit=0,
    )
    assert result["classification"] == (
        "DEV_POSTWORLD_INTERNAL_EPOCH_PRIOR_EXPERIENCE_READ_PASS"
    )
    assert result["source_lease"]["internal_epoch_reads"] == 1
    assert result["source_lease"]["new_action_issuers"] == 0
    assert result["readback"]["previous_native_ref"] == (
        old.self_body.observation.source_ref
    )
    assert result["readback"]["previous_input_off_sampled_motion_ticks"] == (251, 252)
    assert result["readback"]["current_position_x"] is None
    assert result["actual_new_native_present"] is False
    assert result["actual_new_l0_decision"] is False


def test_real_host_postworld_callsite_rejects_failed_shutdown_without_new_epoch():
    from adapters.mineflayer.self_body_s50_world_dev import (
        review_postworld_internal_epoch,
    )
    with pytest.raises(PostWorldInternalEpochRejected):
        review_postworld_internal_epoch(
            prior(), node_exit=0, server_exit=1,
        )
    with pytest.raises(PostWorldInternalEpochRejected):
        review_postworld_internal_epoch(
            prior(), node_exit=0, server_exit=0, cleanup_errors=True,
        )
