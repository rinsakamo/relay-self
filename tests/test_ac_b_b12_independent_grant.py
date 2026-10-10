"""B12: actual S17/S10 outcome is NOT an S11 Habit authority or source."""
from __future__ import annotations

import json
import secrets
from dataclasses import replace

import pytest

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    QualifiedHabitView,
    QualifiedLedger,
    cheap_flat_tags,
    cue_for,
    empty_repertoire,
    grant_test_authority,
    observe_training,
    propose_habit,
)
from experiments.ac_b_b12_independent_grant import (
    NO_SHARED_SOURCE,
    GRANT_KIND,
    IndependentS11Admission,
    InvalidIndependentHabitGrant,
    OfflineIndependentS11Issuer,
    SignedHabitGrant,
    inspect_real_s10_nontransfer,
    parse_grant,
    serialize_grant,
)
from relay_self.action_feedback import (
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.habit import HabitRule, HabitRepertoire, CueFeature, select_habit
from relay_self.learning import (
    LearningCommitResult,
    LearningUpdateAuthority,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance
from test_action_feedback_qualification import (
    executed_closed_chain,
    feedback_criterion,
    learning_authority,
    learning_rule,
    learning_state,
)


def prov(text: str) -> Provenance:
    return Provenance("b12-explicit-gate-test", text)


def world_evidence():
    world = CurrentWorld()
    ledger = QualifiedLedger(world, observe_training(world))
    return world, ledger


def existing_s10_commit():
    *_, actual_outcome, closed_action = executed_closed_chain()
    interpretation = interpret_action_outcome_as_learning_feedback(
        closed_action, actual_outcome, feedback_criterion(),
        provenance=prov("explicit-s17"),
    )
    assert interpretation.status is LearningFeedbackInterpretationStatus.PRODUCED
    state = learning_state()
    proposal = propose_learning_update(state, interpretation.feedback, learning_rule())
    assert state.value == 3 and proposal.proposed_value == 4
    commit = commit_learning_update(
        state, proposal, learning_authority(),
        provenance=prov("explicit-existing-s10-owner"),
    )
    assert isinstance(commit, LearningCommitResult)
    return interpretation, commit


def test_real_s17_to_s10_commit_is_not_s11_habit_acquisition():
    s17, commit = existing_s10_commit()
    world, ledger = world_evidence()
    owner = empty_repertoire()
    unrelated = propose_habit(owner, ledger, 0, 0)
    decision = inspect_real_s10_nontransfer(commit, unrelated)
    assert decision.status == NO_SHARED_SOURCE
    assert decision.authorizes_s11 is False
    assert decision.source_feedback_id == s17.feedback.feedback_id
    assert commit.new_state.revision == 1 and commit.new_state.value == 4
    assert commit.previous_state.value == 3 and commit.previous_state.revision == 0
    assert owner.rules == () and owner.revision == 0
    assert world.actions_executed == 8


def test_habit_gate_rejects_s10_b11_plain_and_generic_grants():
    _, commit = existing_s10_commit()
    _, ledger = world_evidence()
    owner = empty_repertoire()
    proposal = propose_habit(owner, ledger, 0, 0)
    real_s10_grant = LearningUpdateAuthority(
        "only-s10", "risk_weight", prov("lrn-not-habit"),
    )
    b12 = IndependentS11Admission(secrets.token_bytes(32))
    for not_s11_grant in (
        commit, commit.record, real_s10_grant,
        grant_test_authority(proposal),
        {"granted": True, "target": owner.repertoire_id},
        "S17 determined Habit",
        None,
    ):
        with pytest.raises(InvalidIndependentHabitGrant, match="signed S11"):
            b12.commit(owner, proposal, ledger, not_s11_grant)
    assert owner.rules == ()


def test_independent_signed_grants_produce_four_s11_snapshots_and_no_action():
    world, ledger = world_evidence()
    first = empty_repertoire()
    owner = first
    key = secrets.token_bytes(32)
    issuer = OfflineIndependentS11Issuer(key)
    gate = IndependentS11Admission(key)
    accepted = []
    for index, (a, b) in enumerate(CONTEXTS):
        draft = propose_habit(owner, ledger, a, b)
        supplied = issuer.grant(draft)
        copied = parse_grant(serialize_grant(supplied))
        assert copied is not supplied and copied == supplied
        previous = owner
        owner = gate.commit(owner, draft, ledger, copied)
        accepted.append(copied.grant_id)
        assert previous.revision == index
        assert owner.revision == index + 1
        assert len(previous.rules) == index
        assert len(owner.rules) == index + 1
    assert len(set(accepted)) == 4
    assert first.rules == () and first.revision == 0
    assert owner.revision == 4
    assert world.actions_executed == 8
    view = QualifiedHabitView(owner, world.session, world.revision)
    flat = cheap_flat_tags(ledger)
    choices = []
    correct = 0
    for trial in range(3):
        for a, b in CONTEXTS:
            cue = cue_for(a, b, trial=f"new-nuisance-{trial}")
            state, candidate = view.select(cue, world)
            chosen = select_habit(owner, cue)
            assert state == "selected"
            assert candidate == chosen.selected_candidate_ref
            assert candidate == f"action:{flat[a, b]}"
            correct += int(world.heldout_score(a, b, int(candidate.split(":")[1])))
            choices.append(candidate)
    assert len(choices) == 12
    assert correct == 12
    assert world.actions_executed == 8  # all heldout selection read-only


def test_wrong_signed_key_rejected_without_retention():
    _, ledger = world_evidence()
    owner = empty_repertoire()
    draft = propose_habit(owner, ledger, 0, 0)
    foreign = OfflineIndependentS11Issuer(secrets.token_bytes(32)).grant(draft)
    with pytest.raises(InvalidIndependentHabitGrant, match="MAC"):
        IndependentS11Admission(secrets.token_bytes(32)).commit(
            owner, draft, ledger, foreign,
        )
    assert owner.revision == 0


@pytest.mark.parametrize("field,replacement", [
    ("kind", "S10_LEARNING"),
    ("grant_id", "unrelated-grant"),
    ("owner_id", "wrong-repertoire"),
    ("expected_revision", 8),
    ("proposal_id", "wrong-proposal"),
    ("source_session", "other-world"),
    ("source_revision", 9),
    ("observed_ids", ("fake-source:1", "fake-source:2")),
    ("a", 1),
    ("b", 1),
    ("candidate_ref", "action:1"),
    ("proposal_digest", "0" * 64),
    ("granted", False),
    ("granted", 1),
    ("expected_revision", True),
    ("mac", "0" * 64),
])
def test_changing_any_signed_scope_or_mac_rejected(field, replacement):
    _, ledger = world_evidence()
    owner = empty_repertoire()
    draft = propose_habit(owner, ledger, 0, 0)
    key = secrets.token_bytes(32)
    signed = OfflineIndependentS11Issuer(key).grant(draft)
    tampered = replace(signed, **{field: replacement})
    with pytest.raises(InvalidIndependentHabitGrant):
        IndependentS11Admission(key).commit(owner, draft, ledger, tampered)
    assert owner.rules == ()


def test_signed_denial_cannot_update_habit():
    _, ledger = world_evidence()
    owner = empty_repertoire()
    draft = propose_habit(owner, ledger, 0, 0)
    key = secrets.token_bytes(32)
    denied = OfflineIndependentS11Issuer(key).grant(draft, granted=False)
    with pytest.raises(InvalidIndependentHabitGrant, match="denied"):
        IndependentS11Admission(key).commit(owner, draft, ledger, denied)


def test_signed_replay_fails_even_after_exact_revision_change():
    _, ledger = world_evidence()
    owner = empty_repertoire()
    draft = propose_habit(owner, ledger, 0, 0)
    key = secrets.token_bytes(32)
    signed = OfflineIndependentS11Issuer(key).grant(draft)
    gate = IndependentS11Admission(key)
    newer = gate.commit(owner, draft, ledger, signed)
    with pytest.raises(InvalidIndependentHabitGrant):
        gate.commit(newer, draft, ledger, signed)
    with pytest.raises(InvalidIndependentHabitGrant, match="spent"):
        gate.commit(owner, draft, ledger, signed)
    assert owner.revision == 0 and newer.revision == 1


def test_world_revision_change_invalidates_signed_grant_and_source():
    world, ledger = world_evidence()
    owner = empty_repertoire()
    draft = propose_habit(owner, ledger, 0, 0)
    key = secrets.token_bytes(32)
    signed = OfflineIndependentS11Issuer(key).grant(draft)
    world.change_rule(announce=True)
    with pytest.raises(InvalidIndependentHabitGrant, match="World"):
        IndependentS11Admission(key).commit(owner, draft, ledger, signed)
    assert owner.rules == ()


def test_owner_conflict_is_not_silently_overwritten_by_signed_grant():
    _, ledger = world_evidence()
    existing = HabitRule(
        "prior-safety", (CueFeature("a", 0),), "action:1", 100,
        Provenance("b12-existing", "safety"),
    )
    owner = HabitRepertoire("b11-retained-habit", 5, (existing,),
                            Provenance("b12-existing", "owner"))
    draft = propose_habit(owner, ledger, 0, 0)
    key = secrets.token_bytes(32)
    signed = OfflineIndependentS11Issuer(key).grant(draft)
    with pytest.raises(InvalidIndependentHabitGrant, match="conflict"):
        IndependentS11Admission(key).commit(owner, draft, ledger, signed)
    assert owner.rules == (existing,) and owner.revision == 5


def test_old_proposal_edited_to_new_rule_fails_even_with_old_signed_grant():
    _, ledger = world_evidence()
    owner = empty_repertoire()
    draft = propose_habit(owner, ledger, 0, 0)
    key = secrets.token_bytes(32)
    signed = OfflineIndependentS11Issuer(key).grant(draft)
    altered = replace(draft, rule=replace(draft.rule, candidate_ref="action:1"))
    with pytest.raises(InvalidIndependentHabitGrant, match="mismatch"):
        IndependentS11Admission(key).commit(owner, altered, ledger, signed)
    assert owner.rules == ()


def test_signed_grant_serialization_rejects_duplicate_missing_extra_keys():
    _, ledger = world_evidence()
    draft = propose_habit(empty_repertoire(), ledger, 0, 0)
    signed = OfflineIndependentS11Issuer(secrets.token_bytes(32)).grant(draft)
    assert signed.kind == GRANT_KIND
    raw = serialize_grant(signed)
    info = json.loads(raw)
    for malformed in (
        raw.replace('"grant_id":', '"grant_id":"forged","grant_id":', 1),
        json.dumps({**info, "untrusted": "extra"}),
        json.dumps({k: v for k, v in info.items() if k != "mac"}),
        json.dumps({**info, "observed_ids": "not-a-pair"}),
    ):
        with pytest.raises(InvalidIndependentHabitGrant):
            parse_grant(malformed)


def test_s17_outcome_without_explicit_matching_criterion_no_s10_feedback():
    *_, outcome, closed = executed_closed_chain()
    interpretation = interpret_action_outcome_as_learning_feedback(
        closed, outcome, feedback_criterion(reason="wrong_world_reason"),
        provenance=prov("not-matched"),
    )
    assert interpretation.status is LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    assert interpretation.feedback is None
    assert inspect_real_s10_nontransfer is not None


def test_s10_pure_proposal_or_unrelated_object_not_promotion_basis():
    _, ledger = world_evidence()
    owner = empty_repertoire()
    draft = propose_habit(owner, ledger, 0, 0)
    for untrusted in ("S10 output says reflex", grant_test_authority(draft), draft):
        with pytest.raises(InvalidIndependentHabitGrant, match="S10 commit"):
            inspect_real_s10_nontransfer(untrusted, draft)
    assert owner.revision == 0
