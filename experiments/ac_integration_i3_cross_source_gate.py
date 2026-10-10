"""I3 evidence adjudication: independent green CIs never make a causal World join.

Evaluates the existing I2 S17/S10/S11/I1 source-owner contract on live
test-double Python objects. B11/B12 manifest metadata are isolated source
identifiers ONLY, not imported as evidence or silently merged into I2.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.ac_integration_i2_governed_projection import (
    I2Result,
    ProjectionGrant,
    evaluate_i2,
)
from relay_self.action_feedback import LearningFeedbackInterpretation
from relay_self.learning import LearningCommitResult

MANIFEST = Path(__file__).with_name("ac_integration_i3_manifest.json")
FROZEN_DIGEST = "e0e80424849aaeb4efd79299f958c123e63b5590edd44cee4f6b73b1b0a0215b"
FROZEN_I2 = "256b87faf33b0b44499b47981cf8d3a6c755253d"
FROZEN_B11 = "8dd1f0cc115285293736f5d36950469d3866a9db"
FROZEN_B12 = "33686285cd2ffe5865538fd11113c8736f6c36a4"


class I3Rejected(ValueError):
    """Reject a forged cross-World source or attempted authority promotion."""


@dataclass(frozen=True, slots=True)
class ExternalB11Scope:
    """Untrusted metadata pointer, NOT B11's actual object-identity witness."""

    session: str
    revision: int
    source_kind: str
    cue_kind: str
    actions: tuple[int, int]
    event_ids: tuple[str, ...]
    heldout_total: int
    habit_correct: int
    cheap_tags_correct: int
    grant_kind: str
    physical_origin_attested: bool = False
    production_s11_owner: bool = False


@dataclass(frozen=True, slots=True)
class I3Verdict:
    classification: str
    i2_source_session: str
    i2_source_request_id: str
    i2_cue_band: str
    i2_before_candidate: str
    i2_after_candidate: str
    i2_cheap_candidate: str
    b11_source_session: str
    b11_training_actions_reported: int
    b11_heldout_habit_reported: int
    b11_heldout_cheap_reported: int
    causal_join: bool = False
    shared_world_witnesses: bool = False
    shared_action_space: bool = False
    common_cue_semantics: bool = False
    production_habit_owner: bool = False
    native_source_attested: bool = False
    benefit_over_cheap_rule: bool = False
    joint_runtime_go: bool = False


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    item: dict[str, Any] = {}
    for key, value in pairs:
        if key in item:
            raise I3Rejected("duplicate manifest key")
        item[key] = value
    return item


def frozen_manifest() -> dict[str, Any]:
    try:
        raw = MANIFEST.read_text(encoding="utf-8")
        m = json.loads(raw, object_pairs_hook=_unique)
        packed = json.dumps(
            m, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (OSError, ValueError) as exc:
        raise I3Rejected("I3 manifest unavailable or invalid") from exc
    if hashlib.sha256(packed).hexdigest() != FROZEN_DIGEST:
        raise I3Rejected("prospectively frozen I3 manifest changed")
    return m


def b11_readonly_scope() -> ExternalB11Scope:
    """Only the frozen B11/B12 *claim* scope; no B11 source authentication."""
    m = frozen_manifest()
    return ExternalB11Scope(
        session=m["b11_source_session"],
        revision=m["b11_source_revision"],
        source_kind=m["b11_source_kind"],
        cue_kind=m["b11_cue"],
        actions=tuple(m["b11_actions"]),
        event_ids=tuple(f"b11-sim-world:event:{i}" for i in range(1, 9)),
        heldout_total=m["b11_heldout"],
        habit_correct=m["b11_habit_correct"],
        cheap_tags_correct=m["b11_cheap_tags_correct"],
        grant_kind=m["b12_authority"],
    )


def adjudicate_i3(
    i1_inputs: dict[str, Any],
    owner_commit: LearningCommitResult,
    feedback: LearningFeedbackInterpretation,
    test_grant: ProjectionGrant,
    b11: ExternalB11Scope,
    *,
    request: str = "offline",
) -> I3Verdict:
    """Evaluate exact I2 logic, then deny causal transfer across foreign source.

    B11's issuer-owned ledger is NOT present in this branch or this process.
    Even passing this gate cannot license a Habit write; actual B12/B11 CI is
    independent, and no cross-branch common-native-source grant exists.
    """
    m = frozen_manifest()
    if request != "offline":
        raise I3Rejected("production, physical, automatic L2 or Habit grant forbidden")
    if not isinstance(b11, ExternalB11Scope):
        raise I3Rejected("B11 scope must be explicitly distinguished")
    expected = b11_readonly_scope()
    if b11 != expected:
        raise I3Rejected("B11 source identity, witness inventory, or null comparator drift")
    # Reject carefully forged alternative types rather than accepting bool
    # as int or ad hoc source/physical attestation promises.
    for name in ("revision", "heldout_total", "habit_correct", "cheap_tags_correct"):
        if type(getattr(b11, name)) is not int:
            raise I3Rejected(f"B11 {name} has wrong type")
    if (
        type(b11.actions) is not tuple
        or len(b11.actions) != 2
        or any(type(x) is not int for x in b11.actions)
        or type(b11.event_ids) is not tuple
        or any(type(x) is not str for x in b11.event_ids)
        or type(b11.physical_origin_attested) is not bool
        or type(b11.production_s11_owner) is not bool
        or b11.physical_origin_attested
        or b11.production_s11_owner
    ):
        raise I3Rejected("B11 metadata is not physical or production authority")
    if (
        m["base_i2"] != FROZEN_I2
        or m["b11_head"] != FROZEN_B11
        or m["b12_head"] != FROZEN_B12
        or m["i2_ci"] != 38030431852
        or m["b11_ci"] != 38030146847
        or m["b12_ci"] != 38030776737
        or m["shared_world_witness_present"] is not False
        or m["production_s11_owner_present"] is not False
        or m["physical_origin_attested"] is not False
        or m["measured_cost_advantage"] is not False
        or m["production_go"] is not False
    ):
        raise I3Rejected("frozen cross-lane claim ceiling invalid")
    if not isinstance(i1_inputs, dict):
        raise I3Rejected("actual I2 source inputs required")
    receipt = i1_inputs.get("owner_receipt")
    if receipt is None or not hasattr(receipt, "source_receipt"):
        raise I3Rejected("typed I2 source observation absent")

    # Executes ACTUAL unchanged I2 evaluator, not a hand-written emulation.
    result: I2Result = evaluate_i2(
        i1_inputs, owner_commit, owner_commit, feedback, test_grant,
    )
    source = receipt.source_receipt.source
    cm = receipt.source_receipt.evidence.threat_clearance_cm
    if (
        source.session_id != m["i2_s29_session"]
        or receipt.request_id != m["i2_s29_request"]
        or feedback.action_id != m["i2_s17_action"]
        or source.session_id == b11.session
        or not result.cheap_matches_s11
        or not result.new_matches_s24
        or result.repertoire_production_committed
        or result.physical_source_attested
        or result.production_go
        or result.l2_actually_run
        or result.new_action_issued
        or result.action_authorized
    ):
        raise I3Rejected("I2 comparison is not source-qualified or attempted promotion")
    band = "near" if cm <= 100 else "far"
    if band not in ("near", "far"):
        raise I3Rejected("unknown frozen I2 cue")
    if (
        result.s11_old_candidate != "WAIT"
        or result.s11_new_candidate != ("MOVE_AWAY" if band == "near" else "WAIT")
        or result.cheap_retention_threshold != result.s11_new_candidate
    ):
        raise I3Rejected("I2 learned scalar versus cheap decision drift")

    return I3Verdict(
        classification="I3_CROSS_SOURCE_NONTRANSFER_AND_CHEAP_NULL_CI_PASS",
        i2_source_session=source.session_id,
        i2_source_request_id=receipt.request_id,
        i2_cue_band=band,
        i2_before_candidate=result.s11_old_candidate,
        i2_after_candidate=result.s11_new_candidate,
        i2_cheap_candidate=result.cheap_retention_threshold,
        b11_source_session=b11.session,
        b11_training_actions_reported=len(b11.event_ids),
        b11_heldout_habit_reported=b11.habit_correct,
        b11_heldout_cheap_reported=b11.cheap_tags_correct,
    )
