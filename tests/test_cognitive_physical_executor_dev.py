"""Common physical issuer DEV envelope contracts, no real native/LLM calls."""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.cognitive_physical_eat_issue_dev import (
    PhysicalEatGrant,
    PhysicalGrantStage,
)
from experiments.cognitive_physical_executor_dev import (
    PhysicalDevGrant,
    begin_physical_issue_dev,
    check_dev_issuer_preflight,
    check_physical_grants,
    check_physical_source_window,
    finish_physical_issue_dev,
    mark_ambiguous_physical_dev,
)
from relay_self.action import ActionState
from relay_self.physical_action_journal import (
    PhysicalActionJournal,
    PhysicalJournalUnresolved,
)
from test_cognitive_physical_eat_issue_dev import setup


def _begin(kw, session, *, capability="EAT"):
    return begin_physical_issue_dev(
        session, capability=capability, proposal=kw["proposal"],
        current_probe=kw["current_probe"],
        propose_grant=kw["propose_grant"],
        issue_grant=kw["issue_grant"],
        intent_owner=kw["intent_owner"],
        skill_execution=kw["skill_execution"],
        supervisor=kw["supervisor"], journal=kw["journal"],
        at_ns=kw["at_ns"],
    )


def test_legacy_eat_grant_is_exact_shared_dev_envelope(tmp_path):
    kw, session, grants, _ = setup(tmp_path)
    assert PhysicalEatGrant is PhysicalDevGrant
    assert grants[0].stage is PhysicalGrantStage.PROPOSE
    check_physical_grants(kw["proposal"].binding, *grants)
    check_physical_source_window(
        kw["proposal"], kw["previous_probe"], kw["current_probe"],
        capability="EAT", target_kind="FOOD",
    )
    check_dev_issuer_preflight(
        session, kw["proposal"],
        intent_owner=kw["intent_owner"],
        skill_execution=kw["skill_execution"],
        supervisor=kw["supervisor"], journal=kw["journal"],
        at_ns=kw["at_ns"], provenance=kw["provenance"],
        grant_real_world=True, acknowledge_dev_unverified_principal=True,
        evidence_timeout_s=9,
    )
    assert kw["journal"].records == ()


@pytest.mark.parametrize("invalid", [
    "foreign_target", "same_authority", "ungranted", "same_stage",
])
def test_shared_grant_checks_fail_without_wal_or_native(tmp_path, invalid):
    kw, session, grants, _ = setup(tmp_path)
    proposal, issue = grants
    if invalid == "foreign_target":
        issue = replace(issue, selected_target_ref="inventory:other")
    elif invalid == "same_authority":
        issue = replace(issue, authority_id=proposal.authority_id)
    elif invalid == "ungranted":
        issue = replace(issue, granted=False)
    else:
        issue = replace(issue, stage=PhysicalGrantStage.PROPOSE)
    with pytest.raises(ValueError):
        check_physical_grants(kw["proposal"].binding, proposal, issue)
    kw["issue_grant"] = issue
    with pytest.raises(ValueError):
        _begin(kw, session)
    assert kw["journal"].records == ()
    assert kw["supervisor"].recorded_actions == ()
    assert session.sent == []


@pytest.mark.parametrize("invalid", [
    "wrong_capability", "wrong_source", "wrong_request", "stale_sequence",
])
def test_shared_native_window_currentness_is_capability_agnostic(
    tmp_path, invalid,
):
    kw, session, _, _ = setup(tmp_path)
    current = kw["current_probe"]
    capability = "EAT"
    if invalid == "wrong_capability":
        capability = "ATTACK"
    elif invalid == "wrong_source":
        current = replace(current, session_id="another-world")
    elif invalid == "wrong_request":
        current = replace(current, request_id="different-request")
    else:
        current = replace(current, seq=11)
    with pytest.raises(ValueError):
        check_physical_source_window(
            kw["proposal"], kw["previous_probe"], current,
            capability=capability, target_kind="FOOD",
        )
    assert kw["journal"].records == ()
    assert session.sent == []


def test_shared_issue_cannot_switch_selected_eat_to_attack(tmp_path):
    kw, session, _, _ = setup(tmp_path)
    with pytest.raises(ValueError, match="cannot change selected capability"):
        _begin(kw, session, capability="ATTACK")
    assert kw["journal"].records == ()
    assert kw["supervisor"].recorded_actions == ()
    assert session.sent == []


def test_shared_begin_fsync_prepared_before_supervisor_issue_and_no_native_io(
    tmp_path,
):
    kw, session, _, _ = setup(tmp_path)
    _begin(kw, session)
    b = kw["proposal"].binding
    assert kw["supervisor"].get(b.action_id).state is ActionState.ISSUED
    assert kw["journal"].unresolved is True
    assert kw["journal"].records[-1]["status"] == "PREPARED_UNRESOLVED"
    assert session.sent == []
    with pytest.raises(PhysicalJournalUnresolved):
        _begin(kw, session)
    assert len(kw["journal"].records) == 1
    restored = PhysicalActionJournal.restore(
        kw["journal"].path, self_id=b.scope.self_id,
    )
    with pytest.raises(PhysicalJournalUnresolved):
        restored.require_clear()


def test_shared_unknown_after_issued_action_keeps_durable_stop(tmp_path):
    kw, session, _, _ = setup(tmp_path)
    _begin(kw, session)
    action_id = kw["proposal"].binding.action_id
    mark_ambiguous_physical_dev(
        action_id=action_id, supervisor=kw["supervisor"],
        probe=kw["current_probe"], at_ns=kw["at_ns"],
    )
    assert kw["supervisor"].get(action_id).state is ActionState.UNKNOWN
    assert kw["journal"].unresolved is True
    assert session.sent == []


def test_shared_finish_uses_capability_eat_evidence_and_durable_close(tmp_path):
    kw, session, _, native = setup(tmp_path)
    _begin(kw, session)
    equip, consume, after = native
    b = kw["proposal"].binding
    terminal = finish_physical_issue_dev(
        action_id=b.action_id, after=after,
        supervisor=kw["supervisor"], journal=kw["journal"],
        at_ns=kw["at_ns"],
        close=lambda outcome: kw["journal"].close_eat(
            b, kw["current_probe"], equip, consume, after, outcome,
            kw["supervisor"],
        ),
    )
    assert terminal.state is ActionState.OUTCOME
    assert kw["journal"].unresolved is False
    assert kw["journal"].records[-1]["status"] == "NATIVE_EAT_OUTCOME"
    assert session.sent == []
