"""Observation-only admission must remain closed even for online residents."""
import pytest

from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)


@pytest.mark.parametrize("family", ["NONE", "MOVE", "EAT", "ATTACK", "REST", "PEER"])
def test_online_observation_only_rejects_every_issue_lease(family):
    admission = PhysicalIssueAdmission(
        {"A": "new-session"}, resident_mode=True,
        allow_resident_move=True, observation_only=True,
    )
    with pytest.raises(PhysicalIssueFenceError, match="observation-only"):
        with admission.lease(
            self_id="A", native_session_id="new-session", action_id="action",
            effect_family=family,
        ):
            pytest.fail("must not enter physical lease")
    assert admission.active_action_ids == ()


@pytest.mark.parametrize("effect", [
    "set_control", "clear_controls", "equip_item", "consume_held",
    "attack_entity", "look", "unknown",
])
def test_online_observation_only_rejects_final_native_effect(effect):
    admission = PhysicalIssueAdmission(
        {"A": "new-session"}, resident_mode=True, observation_only=True,
    )
    with pytest.raises(PhysicalIssueFenceError, match="observation-only"):
        admission.require_native_effect(
            self_id="A", native_session_id="new-session", effect=effect,
            action_id="action",
        )
    with pytest.raises(PhysicalIssueFenceError, match="observation-only"):
        admission.begin_neutralization()


def test_observation_only_requires_explicit_resident_mode():
    with pytest.raises(PhysicalIssueFenceError):
        PhysicalIssueAdmission({"A": "session"}, observation_only=True)
