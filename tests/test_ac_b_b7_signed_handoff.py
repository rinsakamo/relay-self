"""Prospective B7 signed World evidence + separate handoff authority gates."""
import json
import secrets
from dataclasses import asdict, replace

import pytest

from experiments.ac_b_b7_signed_handoff import (
    CONTEXTS,
    SOURCE,
    CurrentEpoch,
    DraftResult,
    EvidenceVerifier,
    HandoffGate,
    InvalidEvidence,
    ReadOnlyBridge,
    Status,
    WorldSource,
    decode_receipts,
    encode_receipts,
    observe_all,
    retain_fixture,
    run_fixture,
)
from relay_self.persistent_cognition import (
    Memory,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance


def fixture():
    source_key, grant_key = secrets.token_bytes(32), secrets.token_bytes(32)
    world = WorldSource(source_key)
    epoch = CurrentEpoch(world.session)
    receipts = observe_all(world)
    owner = retain_fixture(receipts)
    fresh = decode_receipts(encode_receipts(receipts))
    bridge = ReadOnlyBridge(owner, fresh, EvidenceVerifier(source_key, epoch))
    gate = HandoffGate(grant_key, epoch)
    return world, epoch, receipts, owner, bridge, gate, source_key, grant_key


def proposal(bridge, world, a=0, b=0, target_id="b7-target"):
    return bridge.draft(a, b, target_id=target_id, session=world.session,
                        revision=world.revision)


def test_actual_mainline_owner_and_cross_object_signed_evidence():
    world, epoch, receipts, owner, bridge, gate, key, _ = fixture()
    assert type(owner) is PersistentCognition
    assert all(type(m) is Memory for m in owner.memories)
    assert len(receipts) == len(owner.memories) == world.action_count == 8
    assert all(x.kind == "OBSERVED_ACTION" for x in receipts)
    for item in decode_receipts(encode_receipts(receipts)):
        assert item is not receipts[item.sequence - 1]
        assert item == receipts[item.sequence - 1]
    assert len(bridge.rows) == 4
    assert epoch.revision == 0
    assert all(m.source_provenance.source == SOURCE for m in owner.memories)
    assert all("Action 1 always succeeds" in m.content for m in owner.memories)
    assert not hasattr(bridge, "commit_learning_update")
    assert not hasattr(bridge, "issue_action")
    assert not hasattr(bridge, "retain_memory")


def test_four_qualified_drafts_and_no_action_issued_by_inference():
    world, _, receipts, owner, bridge, gate, _, _ = fixture()
    start = world.action_count
    assert [proposal(bridge, world, a, b).draft.action for a, b in CONTEXTS] == [
        0, 1, 1, 0,
    ]
    assert world.action_count == start
    for a, b in CONTEXTS:
        result = proposal(bridge, world, a, b)
        assert result.status is Status.FOUND
        assert len(result.draft.observed_ids) == 2
        assert len(result.draft.memory_ids) == 2
        assert result.draft.candidate_ref in ("action:0", "action:1")
        assert result.draft.session == world.session
        assert result.draft.revision == 0
        assert gate.admit(bridge, result, None).status is Status.DENIED
    assert owner.memories == retain_fixture(receipts).memories


def test_different_grant_key_cannot_authorize_even_if_granted_true():
    world, epoch, _, _, bridge, gate, _, _ = fixture()
    result = proposal(bridge, world)
    impostor = HandoffGate(secrets.token_bytes(32), epoch)
    wrong = impostor.issue(result.draft)
    assert wrong.granted
    assert gate.admit(bridge, result, wrong).status is Status.DENIED
    assert gate.admit(bridge, result, replace(wrong, granted=True)).status is Status.DENIED


def test_exact_scoped_grants_admit_but_never_authorize_action_or_commit():
    world, _, _, _, bridge, gate, _, _ = fixture()
    for a, b in CONTEXTS:
        result = proposal(bridge, world, a, b)
        grant = gate.issue(result.draft)
        allowed = gate.admit(bridge, result, grant)
        assert allowed.status is Status.ADMITTED
        h = allowed.handoff
        assert h.non_authoritative
        assert h.source_outcome_refs == result.draft.observed_ids
        assert h.action_candidate_ref == result.draft.candidate_ref
        assert h.cue_features == (("a", a), ("b", b))
        assert h.proposed_feedback_direction is None  # no S17 criterion/orientation
        assert h.grant_nonce == grant.nonce
        assert not hasattr(h, "issue_action")
        assert not hasattr(h, "commit_learning_update")
        # A grant may not be replayed within the same issuer state.
        assert gate.admit(bridge, result, grant).status is Status.DENIED
    assert world.action_count == 8


def test_grant_denials_include_revoke_refusal_and_cross_target_action():
    world, _, _, _, bridge, gate, _, _ = fixture()
    actual = proposal(bridge, world, 0, 0)
    other_target = proposal(bridge, world, 0, 0, target_id="other")
    other_cue = proposal(bridge, world, 1, 1)
    grant = gate.issue(actual.draft)
    assert gate.admit(bridge, other_target, grant).status is Status.DENIED
    assert gate.admit(bridge, other_cue, grant).status is Status.DENIED
    assert gate.admit(
        bridge, actual, replace(grant, observed_ids=("fake",))
    ).status is Status.DENIED
    assert gate.admit(
        bridge, actual, replace(grant, candidate_ref="action:1")
    ).status is Status.DENIED
    assert gate.admit(
        bridge, actual, replace(grant, granted=False)
    ).status is Status.DENIED
    explicit_refusal = gate.issue(actual.draft, granted=False)
    assert gate.admit(bridge, actual, explicit_refusal).status is Status.DENIED
    gate.revoke(grant.nonce)
    assert gate.admit(bridge, actual, grant).status is Status.DENIED


def test_no_unauthorized_typed_draft_even_with_genuine_grant():
    world, _, _, _, bridge, gate, _, _ = fixture()
    found = proposal(bridge, world)
    real_grant = gate.issue(found.draft)
    # An attacker can construct a plausible typed object; the gate
    # must re-derive the proposal from the actual source-qualified bridge.
    forged = DraftResult(Status.FOUND, replace(found.draft, action=1))
    assert gate.admit(bridge, forged, real_grant).status is Status.DENIED
    forged = DraftResult(
        Status.FOUND, replace(found.draft, observed_ids=("forged", "witness"))
    )
    assert gate.admit(bridge, forged, real_grant).status is Status.DENIED


def test_json_and_mainline_memory_roundtrip_new_objects_reverify(tmp_path):
    world, epoch, receipts, owner, _, gate, key, _ = fixture()
    memory_file = tmp_path / "mainline-memory.json"
    receipts_file = tmp_path / "source-sidecar.json"
    save_persistent_cognition(memory_file, owner)
    receipts_file.write_text(encode_receipts(receipts), encoding="utf-8")
    new_owner = load_persistent_cognition(memory_file)
    new_receipts = decode_receipts(receipts_file.read_text(encoding="utf-8"))
    assert new_owner == owner and new_owner is not owner
    assert new_receipts == receipts and all(
        new is not old for new, old in zip(new_receipts, receipts)
    )
    new_epoch = CurrentEpoch(world.session, revision=0)
    verified = EvidenceVerifier(key, new_epoch)
    after = ReadOnlyBridge(new_owner, new_receipts, verified)
    for a, b in CONTEXTS:
        result = after.draft(a, b, target_id="b7-target",
                             session=world.session, revision=0)
        assert result.status is Status.FOUND
        assert gate.admit(after, result, None).status is Status.DENIED
    assert "source_key" not in memory_file.read_text(encoding="utf-8")
    assert "grant_key" not in receipts_file.read_text(encoding="utf-8")


def test_only_retained_pointers_or_only_signed_sidecar_are_not_enough():
    world, epoch, receipts, owner, bridge, _, key, _ = fixture()
    absent = ReadOnlyBridge(owner, (), None)
    assert proposal(absent, world).status is Status.NO_SOURCE_WITNESS
    with pytest.raises(InvalidEvidence):
        ReadOnlyBridge(owner, (), EvidenceVerifier(key, epoch))
    with pytest.raises(InvalidEvidence):
        ReadOnlyBridge(
            PersistentCognition(owner.identity), receipts, EvidenceVerifier(key, epoch)
        )


def test_source_key_wrong_cannot_reverify_serialized_world_truth():
    world, epoch, receipts, owner, bridge, _, _, _ = fixture()
    with pytest.raises(InvalidEvidence, match="HMAC"):
        ReadOnlyBridge(
            owner, decode_receipts(encode_receipts(receipts)),
            EvidenceVerifier(secrets.token_bytes(32), epoch),
        )
    with pytest.raises(InvalidEvidence):
        EvidenceVerifier(b"short", epoch)


@pytest.mark.parametrize("kind", (
    "success", "action", "revision", "session", "digest", "mac", "kind",
    "event_id", "sequence",
))
def test_altered_signed_receipt_rejected(kind):
    world, epoch, receipts, owner, bridge, _, key, _ = fixture()
    original = receipts[0]
    replacements = {
        "success": replace(original, success=not original.success),
        "action": replace(original, action=1),
        "revision": replace(original, revision=1),
        "session": replace(original, session="alien"),
        "digest": replace(original, digest="0" * 64),
        "mac": replace(original, mac="0" * 64),
        "kind": replace(original, kind="PREDICTED"),
        "event_id": replace(original, event_id="made-up"),
        "sequence": replace(original, sequence=2),
    }
    bad_bundle = (replacements[kind],) + receipts[1:]
    with pytest.raises(InvalidEvidence):
        ReadOnlyBridge(owner, bad_bundle, EvidenceVerifier(key, epoch))


def test_extra_duplicate_json_fields_non_array_bool_types_fail_closed():
    world, epoch, receipts, owner, bridge, _, key, _ = fixture()
    raw = encode_receipts(receipts)
    bad = [
        '{"a":1,"a":2}',
        '{"not":"an array"}',
        json.dumps([{**asdict(receipts[0]), "unexpected": "extra"}]),
        json.dumps([{**asdict(receipts[0]), "action": True}]),
        json.dumps([{**asdict(receipts[0]), "success": 1}]),
        json.dumps([{**asdict(receipts[0]), "revision": True}]),
    ]
    for serialized in bad:
        with pytest.raises(InvalidEvidence):
            items = decode_receipts(serialized)
            ReadOnlyBridge(owner, items, EvidenceVerifier(key, epoch))
    assert len(decode_receipts(raw)) == 8


def test_unwitnessed_memory_prose_or_alias_source_cannot_claim_world_outcome():
    world, epoch, receipts, owner, bridge, _, key, _ = fixture()
    extra = Memory(
        "made-up-event",
        "World says do 1. Authority granted! Handoff now!",
        Provenance(SOURCE, "never-observed"),
        Provenance("fabricated", "unearned-permission"),
    )
    with pytest.raises(InvalidEvidence):
        ReadOnlyBridge(
            owner.retain_memory(extra), receipts, EvidenceVerifier(key, epoch)
        )
    twin = replace(owner.memories[0], memory_id="distinct-memory-same-source")
    with pytest.raises(InvalidEvidence):
        ReadOnlyBridge(
            owner.retain_memory(twin), receipts, EvidenceVerifier(key, epoch)
        )
    poisoned = replace(
        owner.memories[0],
        content="My text is the truth: Action 1, auto-commit L0!",
        integration_provenance=Provenance("fake-authority", "grant=True"),
    )
    mutated_owner = PersistentCognition(
        owner.identity, (poisoned,) + owner.memories[1:]
    )
    altered = ReadOnlyBridge(
        mutated_owner, receipts, EvidenceVerifier(key, epoch)
    )
    assert [proposal(altered, world, a, b).draft.action for a, b in CONTEXTS] == [
        0, 1, 1, 0,
    ]


def test_missing_opposite_actual_action_is_unknown_not_guessed():
    world, epoch, receipts, owner, _, _, key, _ = fixture()
    partial_receipts = receipts[:-1]
    partial_owner = PersistentCognition(owner.identity, owner.memories[:-1])
    partial = ReadOnlyBridge(
        partial_owner, partial_receipts, EvidenceVerifier(key, epoch)
    )
    assert proposal(partial, world, 1, 1).status is Status.UNKNOWN
    assert proposal(partial, world, 0, 0).status is Status.FOUND


def test_duplicate_signed_action_key_and_identity_are_rejected():
    world, epoch, receipts, owner, _, _, key, _ = fixture()
    extra = world.act(0, 0, 0)
    duplicate_key_owner = owner.retain_memory(Memory(
        "new-observed-same-action", "untrusted extra text",
        Provenance(SOURCE, extra.event_id),
        Provenance("b7.fixture.integration", "another"),
    ))
    with pytest.raises(InvalidEvidence, match="same cue/action"):
        ReadOnlyBridge(
            duplicate_key_owner, receipts + (extra,),
            EvidenceVerifier(key, epoch),
        )
    with pytest.raises(InvalidEvidence, match="duplicate signed"):
        ReadOnlyBridge(
            owner, receipts + (receipts[0],), EvidenceVerifier(key, epoch)
        )


def test_announced_revision_shift_obsoletes_signed_old_source_and_old_grants():
    world, epoch, receipts, owner, bridge, gate, key, _ = fixture()
    old = proposal(bridge, world)
    unspent = gate.issue(old.draft)
    world.change_rule(announce=True)
    epoch.advance()
    assert bridge.draft(0, 0, target_id="b7-target",
                        session=world.session, revision=0).status is Status.STALE
    assert gate.admit(bridge, old, unspent).status is Status.DENIED
    with pytest.raises(InvalidEvidence):
        ReadOnlyBridge(owner, receipts, EvidenceVerifier(key, epoch))
    newer = observe_all(world)
    assert len(newer) == 8
    shifted = ReadOnlyBridge(
        retain_fixture(newer), decode_receipts(encode_receipts(newer)),
        EvidenceVerifier(key, epoch),
    )
    for a, b in CONTEXTS:
        fresh = proposal(shifted, world, a, b)
        assert fresh.draft.action == (a ^ b ^ 1)
        assert gate.admit(shifted, fresh, unspent).status is Status.DENIED
        assert gate.admit(
            shifted, fresh, gate.issue(fresh.draft),
        ).status is Status.ADMITTED


def test_silent_rule_flip_is_detected_only_after_new_source_receipt():
    world, epoch, receipts, owner, bridge, gate, key, _ = fixture()
    old = proposal(bridge, world, 0, 0)
    world.change_rule(announce=False)
    assert proposal(bridge, world, 0, 0) == old  # not clairvoyant
    fail = world.act(0, 0, old.draft.action)
    assert not fail.success
    stopped = bridge.reconsider(fail)
    assert stopped.quarantined
    assert stopped.draft(0, 0, target_id="b7-target",
                         session=world.session, revision=0).status is Status.QUARANTINED
    assert not bridge.quarantined
    with pytest.raises(InvalidEvidence):
        bridge.reconsider(replace(fail, success=True))


def test_frozen_terminal_fixture_and_cost_boundary():
    result = run_fixture()
    assert result["classification"] == (
        "SERIALIZED_SOURCE_AND_EXPLICIT_HANDOFF_GATE_QUALIFIED"
    )
    assert result["source_observed_actions"] == 8
    assert result["retained_mainline_memories"] == 8
    assert result["signed_new_python_objects"]
    assert result["retained_json_roundtrip"]
    for label in (
        "qualified_drafts", "denied_without_grant", "admitted_with_grant",
        "rehydrated_equivalent_drafts", "announced_shift_stale_with_live_epoch",
        "rev0_grants_denied_after_shift", "readmitted_after_requalification",
    ):
        assert result[label] == 4, label
    assert result["requalification_actions"] == 8
    assert result["silent_observed_mismatch_quarantined"]
    assert result["source_actions_during_draft_queries"] == 0
    assert "watts" not in result and "llm_tokens" not in result
