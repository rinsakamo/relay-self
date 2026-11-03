"""Bug-0: the one original S49 issuer delegates its scoped EAT to original S51.

Offline fixture only. A test-only delegate intentionally aborts BEFORE native IO
and lets S49 mark the Action UNKNOWN. No fake World success or learning claim.
"""
import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_feature_s46_eat as s46
import test_mineflayer_execution_qualification as s15
from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.eat_execution import (
    EatingExecutionRejected,
    IssuedEatingExecutor,
    validate_issued_eating_binding,
)
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalActionStage,
    NormalEatingAuthorization,
    NormalEatingObservationStatus,
    NormalActionReceipt,
    NormalSessionActionExecutor,
    assess_normal_eating_observation,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MineflayerEffectResult, MineflayerInventoryItem
from relay_self.action import ActionLifecycle, ActionState
from relay_self.eat_hunger import EatCursor, EatRejected
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


class OfflineNoNativeIO(RuntimeError):
    pass


def source(tag):
    return Provenance("bug0-offline-independent-grant", tag)


def fixture(*, current_name="eat-when-hungry"):
    before = s46.case()
    # Synthetic positive case: only a bounded, empty native registry,
    # never a claim of globally safe surroundings.
    before = replace(before, snapshot=replace(
        before.snapshot,
        nearby_entities=(),
        nearby_entities_coverage=replace(
            before.snapshot.nearby_entities_coverage, candidate_count=0,
        ),
    ))
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


def prior_probe(current):
    """Previous synthetic native probe: same session, separate request and seq."""
    return replace(
        current, seq=current.seq - 1,
        request_id="bug0-earlier-native-food-window",
    )


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
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue, previous_probe=prior_probe(before)))
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
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue, previous_probe=prior_probe(before)))
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
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue, previous_probe=prior_probe(before)))
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
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue, previous_probe=prior_probe(before)))
    assert len(owner.supervisor.open_actions) == 1
    assert propose.action_id not in owner._dispatched


def test_reused_native_source_is_fenced_after_failed_non_idempotent_handoff(monkeypatch):
    before, choice, owner, session = fixture()
    propose, issue = grants(before, choice, owner.intent.current_intent.intent_id)
    monkeypatch.setattr(IssuedEatingExecutor, "execute", forbid_native_io)
    with pytest.raises(OfflineNoNativeIO):
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue, previous_probe=prior_probe(before)))
    new_propose, new_issue = grants(
        before, choice, owner.intent.current_intent.intent_id, action_id="new-eat",
    )
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(session, choice, before, new_propose, new_issue, previous_probe=prior_probe(before)))
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
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue, previous_probe=prior_probe(before)))
    assert owner.supervisor.get(propose.action_id).intent_id == "eat-when-hungry"
    assert owner.intent.current_intent.intent_id == "eat-when-hungry"


class ScriptedNativeSession(MineflayerProcessSession):
    """Same S51 transport API, but no Node/world/socket; receipt source is fixture."""

    def __init__(self, before, action_id, *, consume_applied=True):
        self._started = SimpleNamespace(session_id=before.session_id)
        self._process = SimpleNamespace(returncode=None)
        self.commands = []
        after = replace(
            before, seq=before.seq + 3,
            request_id=f"{action_id}-after-eating-00",
            snapshot=replace(
                before.snapshot, food=12.0,
                inventory=(MineflayerInventoryItem("bread", 1, 4),),
            ),
        )
        self._frames = [
            MineflayerEffectResult(
                before.session_id, before.seq + 1,
                f"{action_id}-equip", "equip_item", "applied", None,
            ),
            MineflayerEffectResult(
                before.session_id, before.seq + 2,
                f"{action_id}-consume", "consume_held",
                "applied" if consume_applied else "rejected",
                None if consume_applied else "native-denied",
            ),
            after,
        ]

    async def receive(self):
        assert self._frames, "unexpected extra native read"
        return self._frames.pop(0)

    async def send_equip_item(self, action_id, *, item_name):
        self.commands.append(("equip", action_id, item_name))

    async def send_consume_held(self, action_id):
        self.commands.append(("consume", action_id))

    async def send_observe(self, request_id):
        self.commands.append(("observe", request_id))


def test_original_s49_supervisor_and_actual_s51_verifier_with_scripted_native_frames():
    before, choice, owner, _ = fixture()
    propose, issue = grants(before, choice, owner.intent.current_intent.intent_id)
    session = ScriptedNativeSession(before, propose.action_id)
    receipt = asyncio.run(owner.execute_eat(session, choice, before, propose, issue, previous_probe=prior_probe(before)))
    assert receipt.terminal is owner.supervisor.get(propose.action_id)
    assert receipt.terminal.state is ActionState.OUTCOME
    assert receipt.outcome.action_id == propose.action_id
    assert receipt.outcome.food_before == 7.0
    assert receipt.outcome.food_after == 12.0
    assert receipt.outcome.count_before == 2
    assert receipt.outcome.count_after == 1
    assert session.commands == [
        ("equip", propose.action_id + "-equip", "bread"),
        ("consume", propose.action_id + "-consume"),
        ("observe", propose.action_id + "-after-eating-00"),
    ]
    assert owner.supervisor.open_actions == ()


def test_original_s49_marks_unknown_if_scripted_native_consume_is_rejected():
    before, choice, owner, _ = fixture()
    propose, issue = grants(before, choice, owner.intent.current_intent.intent_id)
    session = ScriptedNativeSession(before, propose.action_id, consume_applied=False)
    with pytest.raises(EatingExecutionRejected, match="native consume_held rejected"):
        asyncio.run(owner.execute_eat(session, choice, before, propose, issue, previous_probe=prior_probe(before)))
    assert owner.supervisor.get(propose.action_id).state is ActionState.UNKNOWN
    assert session.commands == [
        ("equip", propose.action_id + "-equip", "bread"),
        ("consume", propose.action_id + "-consume"),
    ]
    assert owner.supervisor.open_actions == ()


def test_empty_native_registry_is_only_a_bounded_eat_eligibility_not_safety():
    before, choice, owner, _ = fixture()
    assert assess_normal_eating_observation(before) is (
        NormalEatingObservationStatus.NO_NEARBY_ENTITY_OBSERVED
    )
    assert choice.item_name == "bread"
    assert owner.supervisor.open_actions == ()


@pytest.mark.parametrize("variant", ("zombie", "unknown-entity", "no-health", "no-oxygen"))
def test_observed_threat_or_nonviable_body_fences_s49_eat(variant):
    before, choice, owner, session = fixture()
    if variant in ("zombie", "unknown-entity"):
        entity = s46.case().snapshot.nearby_entities[0]
        if variant == "unknown-entity":
            entity = replace(entity, name=None, entity_type=None)
        unsafe = replace(before, snapshot=replace(
            before.snapshot,
            nearby_entities=(entity,),
            nearby_entities_coverage=replace(
                before.snapshot.nearby_entities_coverage, candidate_count=1,
            ),
        ))
    elif variant == "no-health":
        unsafe = replace(before, snapshot=replace(before.snapshot, health=0))
    else:
        unsafe = replace(before, snapshot=replace(before.snapshot, oxygen_level=0))
    status = assess_normal_eating_observation(unsafe)
    assert status is not NormalEatingObservationStatus.NO_NEARBY_ENTITY_OBSERVED
    propose, issue = grants(unsafe, choice, owner.intent.current_intent.intent_id)
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(session, choice, unsafe, propose, issue, previous_probe=prior_probe(unsafe)))
    assert owner._dispatched == set()
    assert owner.supervisor.open_actions == ()


def test_truncated_native_entity_registry_cannot_admit_eat():
    before, choice, owner, session = fixture()
    coverage = before.snapshot.nearby_entities_coverage
    sample = s46.case().snapshot.nearby_entities[0]
    full = tuple(
        replace(sample, entity_id=sample.entity_id + i)
        for i in range(coverage.max_entities)
    )
    unsafe = replace(before, snapshot=replace(
        before.snapshot, nearby_entities=full,
        nearby_entities_coverage=replace(
            coverage, candidate_count=coverage.max_entities + 1, truncated=True,
        ),
    ))
    assert assess_normal_eating_observation(unsafe) is (
        NormalEatingObservationStatus.TRUNCATED_COVERAGE
    )
    propose, issue = grants(unsafe, choice, owner.intent.current_intent.intent_id)
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(session, choice, unsafe, propose, issue, previous_probe=prior_probe(unsafe)))
    assert owner.supervisor.open_actions == ()


def test_unverified_event_cannot_be_treated_as_current_food_probe():
    before, _, _, _ = fixture()
    with pytest.raises(NormalActionRejected):
        assess_normal_eating_observation(replace(before, kind="health", request_id=None))


def test_original_s49_read_only_eat_shadow_preserves_cue_vs_action_separation():
    from adapters.mineflayer.s49_normal_session_real_ci import read_only_bug0_eat_window

    safe, _, owner, _ = fixture()
    row = read_only_bug0_eat_window(EatCursor(safe.session_id), safe)
    assert row["food_status"] == "CANDIDATE"
    assert row["candidate_item"] == "bread"
    assert row["risk_status"] == "NO_NEARBY_ENTITY_OBSERVED"
    assert row["action_issued"] is False
    assert row["grant_requested"] is False
    assert row["learning_written"] is False
    assert owner.supervisor.open_actions == ()
    assert owner._dispatched == set()

    near = s46.case()
    row_near = read_only_bug0_eat_window(EatCursor(near.session_id), near)
    assert row_near["food_status"] == "CANDIDATE"
    assert row_near["risk_status"] == "OBSERVED_ENTITY_NEARBY"
    assert row_near["action_issued"] is False
    cursor = EatCursor(near.session_id)
    cursor.choose(near)
    with pytest.raises(EatRejected):
        read_only_bug0_eat_window(cursor, near)


def test_s49_eat_shadow_flag_cannot_start_world_without_independent_dev_gate(
    monkeypatch, tmp_path,
):
    import json

    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("S49_BUG0_EAT_SHADOW_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    path = tmp_path / "s49-shadow-gate.json"
    rc = asyncio.run(qualify(
        path, tmp_path / "server.log", bug0_eat_shadow=True,
    ))
    report = json.loads(path.read_text(encoding="utf-8"))
    assert rc == 2
    assert report["status"] == "BLOCKED"
    assert "read-only EAT shadow needs explicit DEV gate" in report["error"]
    assert report["actual_native_actions"] == []
    assert "session_id" not in report


@pytest.mark.parametrize("variant", (
    "same-sequence", "foreign-session", "same-request", "too-old",
    "unstable-position", "prior-threat", "non-probe",
))
def test_eat_requires_two_stable_same_session_native_probes(variant):
    before, choice, owner, session = fixture()
    propose, issue = grants(before, choice, owner.intent.current_intent.intent_id)
    previous = prior_probe(before)
    if variant == "same-sequence":
        previous = replace(previous, seq=before.seq)
    elif variant == "foreign-session":
        previous = replace(previous, session_id="forged-previous-world")
    elif variant == "same-request":
        previous = replace(previous, request_id=before.request_id)
    elif variant == "too-old":
        # Construct a later valid current probe; native seqs cannot be < 0.
        before = replace(before, seq=before.seq + 40)
        choice = EatCursor(before.session_id).choose(before)
        propose, issue = grants(
            before, choice, owner.intent.current_intent.intent_id,
        )
    elif variant == "unstable-position":
        moved = replace(
            previous.snapshot.position,
            x=previous.snapshot.position.x + 0.2,
        )
        previous = replace(
            previous, snapshot=replace(previous.snapshot, position=moved),
        )
    elif variant == "prior-threat":
        entity = s46.case().snapshot.nearby_entities[0]
        previous = replace(
            previous, snapshot=replace(
                previous.snapshot, nearby_entities=(entity,),
                nearby_entities_coverage=replace(
                    previous.snapshot.nearby_entities_coverage,
                    candidate_count=1,
                ),
            ),
        )
    else:
        previous = replace(previous, kind="health", request_id=None)
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(
            session, choice, before, propose, issue, previous_probe=previous,
        ))
    assert owner.supervisor.open_actions == ()
    assert owner._dispatched == set()


def test_prior_move_with_unqualified_postclear_settling_blocks_eat():
    # Owner state reflecting a previously dispatched MOVE: S16 terminal and
    # two nearly identical positions are NOT evidence of native STOP settling.
    before, choice, owner, session = fixture()
    propose, issue = grants(before, choice, owner.intent.current_intent.intent_id)
    owner._post_move_settling_unqualified = True
    with pytest.raises(NormalActionRejected):
        asyncio.run(owner.execute_eat(
            session, choice, before, propose, issue,
            previous_probe=prior_probe(before),
        ))
    assert owner._dispatched == set()
    assert owner.supervisor.open_actions == ()


def original_s15_closure_in_s49_owner():
    """Typed S15/S16 original-like fixture: not independent live World truth."""
    owner_intent = s15.intent_owner()
    owner = NormalSessionActionExecutor("s15-session", owner_intent)
    *_, supervisor, issued = s15.issued_chain()
    assert issued.state is ActionState.ISSUED
    owner.supervisor = supervisor
    owner._dispatched.add(issued.action_id)
    owner._post_move_settling_unqualified = True
    original = WorldConsequence(
        action_id=issued.action_id,
        binding_id="binding-move-away-1",
        action_ref="MOVE_BACKWARD",
        status=WorldConsequenceStatus.EXECUTED,
        session_id="s15-session",
        before_observation=s15.observation(1, 0.0, 0.0),
        dispatch_receipt=s15.effect(2, issued.action_id, "set_control"),
        cleanup_receipt=s15.effect(3, issued.action_id + "-s15-clear", "clear_controls"),
        after_observation=s15.observation(4, 0.0, 0.20),
        movement_distance=0.20,
        cleanup_attempted=True,
        error=None,
        provenance=s15.provenance("original-execution"),
    )
    terminal = supervisor.record_outcome(
        issued.action_id, at_ns=14, provenance=s15.provenance("terminal"),
    )
    return owner, NormalActionReceipt(terminal, original, s15.provenance("source"))


def test_original_s15_s16_source_readback_never_promotes_stop_to_eat():
    owner, receipt = original_s15_closure_in_s49_owner()
    row = owner.read_only_post_move_eat_boundary(receipt)
    assert row.session_id == owner.session_id
    assert row.action_id == receipt.terminal.action_id
    assert row.s15_clear_ack_applied
    assert row.s16_terminal == "OUTCOME"
    assert row.clear_ack_seq == 3 and row.after_probe_seq == 4
    assert row.readback_source == receipt.consequence.after_observation.provenance
    assert row.settling_status == "WORLD_TICK_IDLE_NOT_ATTESTED"
    assert row.physically_stopped_proven is False
    assert row.eat_issuance_authorized is False
    assert owner._post_move_settling_unqualified is True


@pytest.mark.parametrize("variant", (
    "wrong-session", "bad-clear-effect", "bad-clear-result",
    "foreign-after", "not-dispatched", "not-owner", "not-closed",
    "future-clear", "settling-lie",
))
def test_original_s15_readback_rejects_corrupt_or_foreign_boundary(variant):
    owner, receipt = original_s15_closure_in_s49_owner()
    consequence = receipt.consequence
    if variant == "wrong-session":
        consequence = replace(consequence, session_id="foreign-world")
    elif variant == "bad-clear-effect":
        consequence = replace(
            consequence, cleanup_receipt=replace(
                consequence.cleanup_receipt, effect="set_control",
            ),
        )
    elif variant == "bad-clear-result":
        # Must be a valid typed WorldConsequence. Downgrade the consequence to
        # FAILED with an error to carry a rejected clear receipt.
        consequence = replace(
            consequence, status=WorldConsequenceStatus.FAILED,
            cleanup_receipt=replace(
                consequence.cleanup_receipt,
                result="rejected", error="not-applied",
            ),
            error="clear_failed",
        )
    elif variant == "foreign-after":
        consequence = replace(
            consequence, after_observation=replace(
                consequence.after_observation, session_id="foreign-world",
            ),
        )
    elif variant == "not-dispatched":
        owner._dispatched.clear()
    elif variant == "not-owner":
        owner.supervisor = ActionSupervisor()
    elif variant == "not-closed":
        owner.supervisor = ActionSupervisor()
    elif variant == "future-clear":
        consequence = replace(
            consequence, cleanup_receipt=replace(
                consequence.cleanup_receipt, seq=8,
            ),
        )
    elif variant == "settling-lie":
        owner._post_move_settling_unqualified = False
    if variant in {
        "wrong-session", "bad-clear-effect", "bad-clear-result",
        "foreign-after", "future-clear",
    }:
        receipt = replace(receipt, consequence=consequence)
    with pytest.raises((NormalActionRejected, ValueError, TypeError)):
        owner.read_only_post_move_eat_boundary(receipt)
