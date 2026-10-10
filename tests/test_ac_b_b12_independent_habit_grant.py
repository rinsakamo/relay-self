"""Prospective B12 falsification on actual frozen APIs; no physical execution."""
from __future__ import annotations

import json
import secrets
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path

import pytest

from experiments.ac_b_b11_governed_habit import (
    CurrentWorld,
    QualifiedLedger,
    UnqualifiedHabitAcquisition,
    commit_experiment_habit,
    empty_repertoire,
    grant_test_authority,
    observe_training,
    propose_habit,
)
from experiments.ac_b_b12_independent_habit_grant import (
    IndependentS11Admission,
    InvalidHabitGrant,
    OfflineS11Issuer,
    SignedHabitGrant,
    digest,
    inspect_s10_nontransfer,
    qualify_fixture,
)
from relay_self.action_feedback import (
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.habit import CueFeature, HabitRule
from relay_self.learning import commit_learning_update, propose_learning_update
from relay_self.provenance import Provenance
from test_action_feedback_qualification import (
    executed_closed_chain,
    feedback_criterion,
    learning_authority,
    learning_rule,
    learning_state,
)


def fixture(owner=None):
    world = CurrentWorld()
    observations = observe_training(world)
    ledger = QualifiedLedger(world, observations)
    owner = empty_repertoire("b12-owner") if owner is None else owner
    key = secrets.token_bytes(32)
    issuer = OfflineS11Issuer(key, "trusted-s11")
    gate = IndependentS11Admission(trusted_key=key, trusted_issuer="trusted-s11",
                                  live_world=world, admitted_owner=owner)
    draft = propose_habit(owner, ledger, 0, 0)
    grant = issuer.grant(owner, draft, ledger, grant_id="grant:one")
    return world, observations, ledger, owner, key, issuer, gate, draft, grant


def real_commit():
    chain = executed_closed_chain()  # frozen FakeSession; never starts Minecraft
    outcome, closed = chain[-2:]
    repertoire = chain[6]
    criterion = feedback_criterion()
    feedback = interpret_action_outcome_as_learning_feedback(
        closed, outcome, criterion, provenance=Provenance("b12", "s17-feedback"))
    assert feedback.status is LearningFeedbackInterpretationStatus.PRODUCED
    state = learning_state()
    proposal = propose_learning_update(state, feedback.feedback, learning_rule())
    commit = commit_learning_update(state, proposal, learning_authority(),
                                   provenance=Provenance("b12", "s10-commit"))
    return commit, criterion, repertoire, outcome, closed


def test_actual_s17_s10_authorized_transition_cannot_mutate_or_grant_s11():
    commit, criterion, repertoire, outcome, closed = real_commit()
    assert (commit.previous_state.value, commit.previous_state.revision) == (3, 0)
    assert (commit.new_state.value, commit.new_state.revision) == (4, 1)
    before = asdict(repertoire)
    decision = inspect_s10_nontransfer(commit, criterion)
    assert decision.status == "NO_SHARED_WORLD_CUE_WITNESSES"
    assert decision.authorizes_s11 is False
    assert asdict(repertoire) == before
    assert outcome.action_ref == "MOVE_BACKWARD"
    wrong = interpret_action_outcome_as_learning_feedback(
        closed, outcome, replace(criterion, required_outcome_reason="different"),
        provenance=Provenance("b12", "criterion-mismatch"))
    assert wrong.status is LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    assert wrong.feedback is None
    *_, ledger, owner, key, issuer, gate, draft, grant = fixture()
    for token in (commit, commit.record, criterion, learning_authority(),
                  grant_test_authority(draft), {"granted": True, "b7": "schema"},
                  "provider says acquire", None):
        with pytest.raises(InvalidHabitGrant, match="signed S11"):
            gate.commit(owner, draft, ledger, token)
    assert gate.owner is owner and owner.rules == ()


def test_four_independent_commits_same_training_same_holdout_grand_null():
    result = qualify_fixture(secrets.token_bytes(32))
    assert result["classification"] == "INDEPENDENT_EXPERIMENTAL_S11_GRANT_CHECK_QUALIFIED"
    assert result["training_offline_actions"] == 8
    assert result["owner_revision"] == result["new_rules"] == 4
    assert result["original_owner_revision"] == result["original_rules"] == 0
    assert result["habit_correct"] == result["cheap_tag_correct"] == result["holdout"] == 12
    assert result["grand_null_retained"] is True
    assert result["novel_relevant_cues"] is False
    assert result["cheap_lookups"] == 12 and result["habit_feature_check_upper_bound"] == 96


def test_snapshot_binding_cannot_replace_admitted_owner_even_same_id_revision():
    _, _, ledger, owner, _, issuer, gate, draft, grant = fixture()
    other = replace(owner, provenance=Provenance("foreign-owner", "same-id-rev"))
    assert other.repertoire_id == owner.repertoire_id and other.revision == owner.revision
    forged = issuer.grant(other, draft, ledger, grant_id="other")
    for candidate, signed in ((other, forged), (replace(owner), grant), (owner, forged)):
        with pytest.raises(InvalidHabitGrant):
            gate.commit(candidate, draft, ledger, signed)
    assert gate.owner is owner
    updated = gate.commit(owner, draft, ledger, grant)
    assert updated is not owner and owner.rules == () and updated.revision == 1
    with pytest.raises(FrozenInstanceError):
        updated.revision = 42


@pytest.mark.parametrize("field,value", [
    ("domain", "S10"), ("issuer", "different-authority"),
    ("repertoire_id", "other"), ("expected_revision", 1),
    ("expected_revision", False), ("owner_snapshot_digest", "0" * 64),
    ("source_session", "foreign"), ("source_revision", 1),
    ("source_revision", False), ("observed_action_ids", ["fake:1", "fake:2"]),
    ("cue", [1, 0]), ("candidate_action", "action:1"),
    ("proposal_id", "other-proposal"), ("evidence_digest", "0" * 64),
    ("granted", False), ("granted", 1), ("proposal", {}),
])
@pytest.mark.parametrize("resign", [False, True])
def test_all_scope_tampering_fails_even_correctly_signed_wrong_evidence(field, value, resign):
    _, _, ledger, owner, _, issuer, gate, draft, grant = fixture()
    body = json.loads(grant.body)
    body[field] = value
    bad = issuer.sign_body(body) if resign else replace(grant, body=json.dumps(body))
    with pytest.raises(InvalidHabitGrant):
        gate.commit(owner, draft, ledger, bad)
    assert gate.owner is owner and owner.rules == ()
    assert gate.commit(owner, draft, ledger, grant).revision == 1  # rejection did not consume


def test_wrong_key_forgery_and_plain_b11_grant_not_signature():
    _, _, ledger, owner, _, _, gate, draft, grant = fixture()
    wrong = OfflineS11Issuer(secrets.token_bytes(32), "trusted-s11").grant(
        owner, draft, ledger, grant_id="foreign-key")
    for signed in (wrong, replace(grant, mac="0" * 64), replace(grant, mac="é" * 64),
                   replace(grant, mac=3), replace(grant, body=None)):
        with pytest.raises(InvalidHabitGrant):
            gate.commit(owner, draft, ledger, signed)
    assert gate.owner is owner


def test_replay_old_new_owner_and_reissued_proposal_rejected():
    _, _, ledger, owner, _, issuer, gate, draft, grant = fixture()
    newer = gate.commit(owner, draft, ledger, grant)
    again = issuer.grant(owner, draft, ledger, grant_id="another-valid-signature")
    for snapshot in (owner, newer):
        for signed in (grant, again):
            with pytest.raises(InvalidHabitGrant):
                gate.commit(snapshot, draft, ledger, signed)
    # Grant IDs are independently consumed even across distinct proposals.
    draft2 = propose_habit(newer, ledger, 0, 1)
    recycled = issuer.grant(newer, draft2, ledger, grant_id="grant:one")
    with pytest.raises(InvalidHabitGrant, match="replayed"):
        gate.commit(newer, draft2, ledger, recycled)
    good = issuer.grant(newer, draft2, ledger, grant_id="grant:two")
    assert gate.commit(newer, draft2, ledger, good).revision == 2


@pytest.mark.parametrize("change", ["revision", "session", "lost-witness", "different-world"])
def test_live_source_recomputed_from_independent_world(change):
    world, observations, ledger, owner, _, _, gate, draft, grant = fixture()
    if change == "revision":
        world.change_rule(announce=True)
    elif change == "session":
        world.session = "foreign-session"
    elif change == "lost-witness":
        world._issued.pop(observations[0].event_id)
    else:
        another = CurrentWorld()  # same declared scope; different source identity
        ledger = QualifiedLedger(another, observe_training(another))
    with pytest.raises(InvalidHabitGrant):
        gate.commit(owner, draft, ledger, grant)
    assert gate.owner is owner


def test_fabricated_copy_and_changed_proposal_witness_fail_closed():
    world, rows, ledger, owner, _, _, gate, draft, grant = fixture()
    with pytest.raises(UnqualifiedHabitAcquisition):
        QualifiedLedger(world, (replace(rows[0]),) + rows[1:])
    for changed in (replace(draft, observed_ids=("fake:1", "fake:2")),
                    replace(draft, rule=replace(draft.rule, candidate_ref="action:1")),
                    replace(draft, source_session="fake")):
        with pytest.raises(InvalidHabitGrant):
            gate.commit(owner, changed, ledger, grant)


def test_conflicting_rule_cannot_be_overwritten_by_valid_signed_grant():
    rule = HabitRule("prior", (CueFeature("a", 0),), "action:1", 100,
                     Provenance("b12", "prior-rule"))
    owner = replace(empty_repertoire("b12-owner"), revision=5, rules=(rule,))
    _, _, ledger, _, _, issuer, gate, draft, grant = fixture(owner)
    with pytest.raises(InvalidHabitGrant, match="conflict"):
        gate.commit(owner, draft, ledger, grant)
    assert gate.owner is owner and owner.rules == (rule,)
    other = propose_habit(owner, ledger, 1, 0)
    signed = issuer.grant(owner, other, ledger, grant_id="grant:one")
    assert gate.commit(owner, other, ledger, signed).revision == 6


@pytest.mark.parametrize("transform", [
    lambda s: s.replace('"grant_id":', '"grant_id":"duplicate","grant_id":', 1),
    lambda s: json.dumps(json.loads(s), indent=2),
    lambda s: s[:-1] + ',"key":"receipt-key"}',
    lambda s: "[]", lambda s: "null", lambda s: "{", lambda s: "3",
])
def test_noncanonical_duplicate_extra_or_invalid_json_rejected(transform):
    _, _, ledger, owner, _, _, gate, draft, grant = fixture()
    with pytest.raises(InvalidHabitGrant):
        gate.commit(owner, draft, ledger, SignedHabitGrant(transform(grant.body), grant.mac))
    assert gate.owner is owner


def test_test_key_and_b11_direct_bypass_limits_are_explicit():
    _, _, ledger, owner, _, issuer, _, draft, grant = fixture()
    # Anyone entrusted with the test key can sign arbitrary payloads.
    assert isinstance(issuer.sign_body({"malicious": "arbitrary"}), SignedHabitGrant)
    # B11 remains directly callable; wrapper cannot enforce production exclusivity.
    updated = commit_experiment_habit(owner, draft, grant_test_authority(draft), ledger)
    assert updated.revision == 1
    assert "key" not in json.loads(grant.body)
    pair = ledger.rows[0, 0]
    assert json.loads(grant.body)["evidence_digest"] == digest([asdict(pair[a]) for a in (0, 1)])


def test_prospective_manifest_stays_frozen():
    from hashlib import sha256

    path = Path(__file__).parents[1] / "experiments/ac_b_b12_manifest.json"
    assert sha256(path.read_bytes()).hexdigest() == (
        "036ff6d284bad7631c3f11fff08b47f5dd1e940221ddd0aebbb2c50c9ebb55aa")
