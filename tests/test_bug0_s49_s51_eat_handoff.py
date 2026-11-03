"""Bug-0: the one original S49 issuer delegates its scoped EAT to original S51.

Offline fixture only. A test-only delegate intentionally aborts BEFORE native IO
and lets S49 mark the Action UNKNOWN. No fake World success or learning claim.
"""
import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_feature_s46_eat as s46
from adapters.mineflayer.eat_execution import (
    IssuedEatingExecutor,
    validate_issued_eating_binding,
)
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalActionStage,
    NormalEatingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from relay_self.action import ActionLifecycle, ActionState
from relay_self.eat_hunger import EatCursor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


class OfflineNoNativeIO(RuntimeError):
    pass


def source(tag):
    return Provenance("bug0-offline-independent-grant", tag)


def fixture(*, current_name="eat-when-hungry"):
    before = s46.case()
    choice = EatCursor(before.session_id).choose(before)
    commitment = IntentCommitment()
    commitment.commit(
        current_name, objective="eat observed bread",
        at_ns=1, provenance=source("intent"),
    )
    owner = NormalSessionActionExecutor(before.session_id, commitment)
    # Must be an actual MineflayerProcessSession instance for S49's type guard,
    # but no OS process, socket, bridge, network or source observation is opened.
    session = object.__new__(MineflayerProcessSession)
    session._started = SimpleNamespace(session_id=before.session_id)
    session._process = SimpleNamespace(returncode=None)
    return before, choice, owner, session


def grants(before, choice, intent_id, action_id="bug0-s49-issued-eat"):
    base = dict(
        intent_id=intent_id, session_id=before.session_id,
        action_id=action_id, probe_seq=before.seq,
        probe_request_id=before.request_id, food_item=choice.item_name,
        food_slot=choice.item_slot, granted=True,
    )
    return (
        NormalEatingAuthorization(
            stage=NormalActionStage.PROPOSE,
            authority_id="operator-proposal", provenance=source("propose"), **base,
        ),
        NormalEatingAuthorization(
            stage=NormalActionStage.ISSUE,
            authority_id="operator-issue", provenance=source("issue"), **base,
        ),
    )


async def forbid_native_io(
    self, session, supervisor, issued, choice, before, *,
    skill_execution=None, intent_commitment=None,
):
    # This must be the SAME ActionSupervisor owned by S49, not an S51 duplicate.
    assert issued.state is ActionState.ISSUED
    validate_issued_eating_binding(
        supervisor, issued, skill_execution, intent_commitment, choice, before,
    )
    raise OfflineNoNativeIO("S49 -> S51 typed handoff verified; no physical IO")


def test_original_s49_owner_reaches_s51_and_marks_unexecuted_action_unknown(monkeypatch):
    before, choice, owner, session = fixture()
    propose, issue = grants(
        before, choice, owner.intent.current_intent.intent_id,
    )
    monkeypatch.setattr(IssuedEatingExecutor, "execute", forbid_native_io)
    with pytest.raises(OfflineNoNativeIO):
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue))
    issued = owner.supervisor.get(propose.action_id)
    assert issued.state is ActionState.UNKNOWN
    assert issued.intent_id == owner.intent.current_intent.intent_id
    assert issued.events[-3].authority == propose.authority_id
    assert issued.events[-2].state is ActionState.ISSUED
    assert owner.supervisor.open_actions == ()
    assert owner._last_issued_probe_seq == before.seq


@pytest.mark.parametrize("bad", (
    "not-granted", "same-authority", "same-provenance", "wrong-stage",
    "wrong-action", "wrong-intent", "wrong-session", "wrong-seq",
    "wrong-request", "wrong-food", "wrong-slot", "wrong-probe",
))
def test_bad_eat_authorizations_or_source_never_issue(bad, monkeypatch):
    before, choice, owner, session = fixture()
    propose, issue = grants(before, choice, owner.intent.current_intent.intent_id)
    if bad == "not-granted":
        issue = replace(issue, granted=False)
    elif bad == "same-authority":
        issue = replace(issue, authority_id=propose.authority_id)
    elif bad == "same-provenance":
        issue = replace(issue, provenance=propose.provenance)
    elif bad == "wrong-stage":
        issue = replace(issue, stage=NormalActionStage.PROPOSE)
    elif bad == "wrong-action":
        issue = replace(issue, action_id="other-action")
    elif bad == "wrong-intent":
        propose = replace(propose, intent_id="other-intent")
    elif bad == "wrong-session":
        issue = replace(issue, session_id="other-session")
    elif bad == "wrong-seq":
        propose = replace(propose, probe_seq=before.seq + 1)
    elif bad == "wrong-request":
        issue = replace(issue, probe_request_id="other-probe")
    elif bad == "wrong-food":
        propose = replace(propose, food_item="rotten_flesh")
    elif bad == "wrong-slot":
        issue = replace(issue, food_slot=choice.item_slot + 1)
    elif bad == "wrong-probe":
        before = replace(before, seq=before.seq + 1)

    async def unexpected(*args, **kwargs):
        pytest.fail("S51 delegate must not run after failed S49 admission")

    monkeypatch.setattr(IssuedEatingExecutor, "execute", unexpected)
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue))
    assert owner.supervisor.open_actions == ()
    assert owner._dispatched == set()


def test_reconsideration_fences_unsafe_eat_before_issue():
    before, choice, owner, session = fixture()
    propose, issue = grants(before, choice, owner.intent.current_intent.intent_id)
    owner.intent.request_reconsideration(
        owner.intent.current_intent.intent_id, reason="enemy approaching",
        at_ns=2, provenance=source("urgent"),
    )
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue))
    assert not owner.supervisor.open_actions and not owner._dispatched


def test_concurrent_move_action_blocks_eat():
    before, choice, owner, session = fixture()
    propose, issue = grants(before, choice, owner.intent.current_intent.intent_id)
    existing_skill = SkillExecution.start(
        "already-moving", skill_id="MOVE_BACKWARD",
        intent_commitment=owner.intent, at_ns=2, provenance=source("skill"),
    )
    existing_action = ActionLifecycle.propose(
        "existing-move", skill_execution=existing_skill,
        intent_commitment=owner.intent, at_ns=3, provenance=source("proposed"),
    )
    authorized = existing_action.authorize(
        at_ns=4, provenance=source("authorized"), authority="operator-existing",
    )
    owner.supervisor.issue(
        authorized, at_ns=5, deadline_ns=80, provenance=source("issued"),
    )
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue))
    assert len(owner.supervisor.open_actions) == 1
    assert propose.action_id not in owner._dispatched


def test_reused_native_source_is_fenced_after_failed_non_idempotent_handoff(monkeypatch):
    before, choice, owner, session = fixture()
    propose, issue = grants(before, choice, owner.intent.current_intent.intent_id)
    monkeypatch.setattr(IssuedEatingExecutor, "execute", forbid_native_io)
    with pytest.raises(OfflineNoNativeIO):
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue))
    new_propose, new_issue = grants(
        before, choice, owner.intent.current_intent.intent_id, action_id="new-eat",
    )
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(session, choice, before, new_propose, new_issue))
    assert "new-eat" not in owner._dispatched


def test_same_s49_owner_can_admit_new_eat_intent_after_prior_release(monkeypatch):
    before, choice, owner, session = fixture(current_name="escape-threat")
    owner.intent.complete(
        "escape-threat", reason="threat went away",
        at_ns=2, provenance=source("completed"),
    )
    owner.intent.commit(
        "eat-when-hungry", objective="eat observed bread",
        at_ns=3, provenance=source("new-intent"),
    )
    propose, issue = grants(before, choice, "eat-when-hungry")
    monkeypatch.setattr(IssuedEatingExecutor, "execute", forbid_native_io)
    with pytest.raises(OfflineNoNativeIO):
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue))
    assert owner.supervisor.get(propose.action_id).intent_id == "eat-when-hungry"
    assert owner.intent.current_intent.intent_id == "eat-when-hungry"
