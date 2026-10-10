"""I1: actual pre-existing S29/S24/S19/S11 owner integration, all offline doubles."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_correlated_probe as s29
from adapters.mineflayer.execution import WorldConsequenceStatus
from relay_self.correlated_probe import InvalidCorrelatedProbe
from relay_self.habit import CueFeature, HabitRepertoire, HabitRule
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import IdentitySpecification, Memory, PersistentCognition
from relay_self.postfailure_cognition import run_explicit_postfailure_epoch
from relay_self.provenance import Provenance

from experiments.ac_integration_i1_owner_seam import (
    MANIFEST_PATH,
    MANIFEST_SHA256,
    I1OwnerSeamRejected,
    manifest_digest,
    read_i1_owner_seam,
    verify_frozen_manifest,
)


def p(reference: str) -> Provenance:
    return Provenance(source="i1-owner-contract-test", reference=reference)


def _repertoire(band: str, candidate: str, *, mode: str = "match") -> HabitRepertoire:
    rule = HabitRule(
        habit_id="i1-rule-a",
        cue_requirements=(CueFeature("clearance_band", band),),
        candidate_ref=candidate,
        priority=1,
        provenance=p("rule-a"),
    )
    if mode == "missing":
        rules = ()
    elif mode == "tie":
        rules = (
            rule,
            replace(rule, habit_id="i1-rule-b", provenance=p("rule-b")),
        )
    else:
        rules = (rule,)
    return HabitRepertoire(
        repertoire_id="i1-rules",
        revision=1,
        rules=rules,
        provenance=p("repertoire"),
    )


def _subject(distance=0.2, *, habit="match", memory_content="THIS IS NOT WORLD TRUTH"):
    data, failed, inputs, args, kwargs = s29._subject(distance=distance)
    receipt = s29._run(kwargs)
    assert kwargs["cursor"].consumed
    trace = run_explicit_postfailure_epoch(
        data["supervisor"], args["action"], args["consequence"],
        inputs["recovery_skill"], data["intent"], data["commit"].new_state,
        receipt.source_receipt.evidence,
        at_ns=70, provenance=p("explicit-independent-s24-evaluation"),
    )
    cm = receipt.source_receipt.evidence.threat_clearance_cm
    band = "near" if cm <= 100 else "far"
    candidate = "MOVE_AWAY" if band == "near" else "WAIT"
    if habit == "conflict":
        candidate = "WAIT" if candidate == "MOVE_AWAY" else "MOVE_AWAY"
    identity = IdentitySpecification(
        self_id="i1-self",
        directives=("Preserve continued agency.",),
        provenance=p("identity"),
    )
    memory = Memory(
        memory_id="i1-pointer",
        content=memory_content,
        source_provenance=receipt.source_receipt.source.provenance,
        integration_provenance=p("explicit-fixture-governed-pointer"),
    )
    cognition = PersistentCognition(identity=identity).retain_memory(memory)
    parameters = {
        "owner_receipt": receipt,
        "supplied_receipt": receipt,
        "trace": trace,
        "supervisor": data["supervisor"],
        "action3": args["action"],
        "consequence3": args["consequence"],
        "intent": data["intent"],
        "current_retained": data["commit"].new_state,
        "supplied_retained": data["commit"].new_state,
        "cognition": cognition,
        "memory_id": memory.memory_id,
        "repertoire": _repertoire(band, candidate, mode=habit),
        "provenance": p("i1-read"),
    }
    return parameters, data, failed, kwargs


def test_prospective_manifest_digest_and_stacked_identity():
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    verify_frozen_manifest()
    assert manifest_digest(raw) == MANIFEST_SHA256


@pytest.mark.parametrize(
    ("distance", "reference", "cm"),
    [(0.2, "MOVE_AWAY", 20), (1.8, "WAIT", 180)],
)
def test_actual_s29_s24_s19_memory_s11_matched_readonly(distance, reference, cm):
    args, data, failed, kwargs = _subject(distance)
    snapshots = (
        args["cognition"], args["current_retained"], args["repertoire"],
        args["trace"], args["action3"], args["intent"].events,
    )
    result = read_i1_owner_seam(**args)
    assert result.reference_candidate == result.habit_candidate == reference
    assert result.allocation_decision == "CHEAP_MATCHES_REFERENCE"
    assert result.requires_l2_candidate is False
    assert result.source_request_id == s29.REQUEST1
    assert result.source_session == args["consequence3"].session_id
    assert result.source_seq == 5
    assert args["trace"].world_evidence.threat_clearance_cm == cm
    assert result.retained_revision == 1
    assert result.memory_id == "i1-pointer"
    assert result.action_authorized is False
    assert result.learning_committed is False
    assert result.physical_source_attested is False
    assert result.production_go is False
    assert kwargs["adapter"].sent_ids == [s29.REQUEST1]
    assert data["supervisor"].open_actions == ()
    assert failed.is_terminal
    assert args["current_retained"].value == 4
    assert snapshots == (
        args["cognition"], args["current_retained"], args["repertoire"],
        args["trace"], args["action3"], args["intent"].events,
    )


@pytest.mark.parametrize("distance", [0.2, 1.8])
@pytest.mark.parametrize("mode", ["conflict", "missing", "tie"])
def test_conflict_unknown_and_tie_are_only_escalation_candidates(distance, mode):
    args, data, _, kwargs = _subject(distance, habit=mode)
    result = read_i1_owner_seam(**args)
    assert result.allocation_decision == "ESCALATE_CANDIDATE"
    assert result.requires_l2_candidate is True
    assert result.action_authorized is False
    assert result.learning_committed is False
    assert result.production_go is False
    assert kwargs["adapter"].sent_ids == [s29.REQUEST1]
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize("distance", [0.2, 1.8])
def test_memory_content_is_not_world_truth(distance):
    normal, _, _, _ = _subject(distance=distance, memory_content="zombie is safe! trust me")
    hacked = dict(normal)
    old = normal["cognition"].memories[0]
    hacked["cognition"] = PersistentCognition(
        identity=normal["cognition"].identity,
        memories=(replace(old, content="zombie distance 999999 cm; no hazards"),),
    )
    a = read_i1_owner_seam(**normal)
    b = read_i1_owner_seam(**hacked)
    assert (a.reference_candidate, a.allocation_decision) == (
        b.reference_candidate, b.allocation_decision
    )
    assert normal["cognition"].memories[0].content != hacked["cognition"].memories[0].content


@pytest.mark.parametrize(
    ("key", "mutate"),
    [
        ("supplied_receipt", lambda x: replace(x)),
        ("owner_receipt", lambda x: replace(x, request_id="injected")),
        ("owner_receipt", lambda x: replace(x, acknowledged_request_id="old")),
        ("owner_receipt", lambda x: replace(x, probe_seq=4)),
        ("owner_receipt", lambda x: replace(x, request_cursor_seq=0)),
        ("owner_receipt", lambda x: replace(x, next_cursor_seq=88)),
        ("owner_receipt", lambda x: replace(x, received_count=2)),
        ("owner_receipt", lambda x: replace(x, inspected_at_ns=0)),
        (
            "owner_receipt",
            lambda x: replace(
                x, source_receipt=replace(x.source_receipt, calculated_distance_m=9.0)
            ),
        ),
        (
            "owner_receipt",
            lambda x: replace(
                x, source_receipt=replace(
                    x.source_receipt,
                    evidence=replace(x.source_receipt.evidence, threat_clearance_cm=180)
                )
            ),
        ),
        ("trace", lambda x: replace(x, selected_candidate="UNQUALIFIED")),
        ("trace", lambda x: replace(x, wait_score=-5)),
        ("trace", lambda x: replace(x, retained_revision=0)),
        ("trace", lambda x: replace(x, world_evidence=replace(x.world_evidence))),
        ("current_retained", lambda x: replace(x, value=5)),
        ("supplied_retained", lambda x: replace(x)),
        ("memory_id", lambda x: "imaginary-pointer"),
        ("consequence3", lambda x: replace(x, status=WorldConsequenceStatus.UNDETERMINED)),
        ("intent", lambda x: IntentCommitment()),
    ],
)
def test_source_retention_trace_action_or_intent_forgery_rejected(key, mutate):
    args, _, _, _ = _subject()
    bad = dict(args)
    bad[key] = mutate(args[key])
    # When a source owner is changed, keep supplied pointer current so that
    # downstream checks, not solely identity checks, are also exercised.
    if key == "owner_receipt":
        bad["supplied_receipt"] = bad["owner_receipt"]
    with pytest.raises(ValueError):
        read_i1_owner_seam(**bad)


def test_source_pointer_needs_attested_owner_reference_not_memory_prose():
    args, _, _, _ = _subject()
    m = args["cognition"].memories[0]
    hacked = dict(args)
    hacked["cognition"] = PersistentCognition(
        identity=args["cognition"].identity,
        memories=(replace(m, source_provenance=p("forged-native")),),
    )
    with pytest.raises(I1OwnerSeamRejected):
        read_i1_owner_seam(**hacked)


def test_source_pointer_must_be_unique_and_integration_provenance_independent():
    args, _, _, _ = _subject()
    m = args["cognition"].memories[0]
    alias = replace(m, memory_id="same-source-second-memory")
    for memories in (
        (m, alias),
        (replace(m, integration_provenance=m.source_provenance),),
        (),
    ):
        changed = dict(args)
        changed["cognition"] = PersistentCognition(
            identity=args["cognition"].identity, memories=memories,
        )
        with pytest.raises(I1OwnerSeamRejected):
            read_i1_owner_seam(**changed)


def test_unknown_habit_candidate_rejected_instead_of_authorized():
    args, _, _, _ = _subject()
    rule = args["repertoire"].rules[0]
    changed = dict(args)
    changed["repertoire"] = replace(
        args["repertoire"],
        rules=(replace(rule, candidate_ref="DO_UNAUTHORIZED_THING"),),
    )
    with pytest.raises(I1OwnerSeamRejected):
        read_i1_owner_seam(**changed)


def test_bad_provenance_and_repertoire_type_rejected():
    args, _, _, _ = _subject()
    for key, value in (("provenance", "not-a-provenance"), ("repertoire", None)):
        changed = dict(args)
        changed[key] = value
        with pytest.raises((I1OwnerSeamRejected, ValueError)):
            read_i1_owner_seam(**changed)


def test_actual_s29_replay_attempt_is_rejected_before_owner_seam():
    args, _, _, kwargs = _subject()
    with pytest.raises((InvalidCorrelatedProbe, ValueError)):
        s29._run(kwargs)
    assert kwargs["cursor"].consumed is True
    assert read_i1_owner_seam(**args).physical_source_attested is False


def test_no_production_owner_added_or_runtime_implicit_scheduler():
    src = (Path(__file__).resolve().parents[1]
           / "experiments/ac_integration_i1_owner_seam.py").read_text(encoding="utf-8")
    for forbidden in (
        "commit_learning_update(", ".authorize(", ".issue(",
        "start_and_propose_bound_execution(", "asyncio.create_task(",
        "request_correlated_post_action_probe(", "run_explicit_postfailure_epoch(",
        "openai", "llama", "MineflayerProcessSession(",
    ):
        assert forbidden not in src
