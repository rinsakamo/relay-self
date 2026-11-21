"""I Lane I2: source-bound B/E exploration -> Goal/Question -> bounded L1 handoff.

Uses ONLY the original B owner and the I1 source-qualified Native/Paper
readout. This does not submit a model request, adopt a Goal/Question/Intent,
persist cognition, authorize a Skill/Target or issue any physical Action.

An old restored Self with no saved exploration Pattern must remain without
an exploration Goal, even when its bounded native coverage is unknown.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, replace

from relay_self.cognitive_minimal_dev import Goal
from relay_self.i_lane_i1_cpu_schema_probe_dev import (
    I1CPUProbe,
    prepare_i1_cpu_schema_probe,
)
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionDatum,
    project_identity_context,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner


class I2OriginalGoalHold(RuntimeError):
    """Original source, candidate, or bounded L1 handoff not current."""


@dataclass(frozen=True, slots=True)
class I2OriginalGoalHandoff:
    """Ephemeral CPU-only proposal, not a model ticket or saved Goal."""

    self_id: str
    native_session_id: str
    native_seq: int
    native_request_id: str
    sense_revision: str
    paper_session_id: str
    paper_log_sha256: str
    resident_epoch: int
    registry_revision: int
    source_revision_refs: tuple[str, ...]
    need_signal_ref: str | None
    question_candidate_ref: str | None
    goal_candidates: tuple[Goal, ...]
    status: str
    bounded_request: BoundedChoiceRequest
    material_sha256: str
    model_invoked: bool = False
    question_adopted: bool = False
    goal_adopted: bool = False
    intent_committed: bool = False
    action_issue_authorized: bool = False


def _material(bridge, probe: I1CPUProbe, sid: str) -> dict:
    source = probe.original.present.source
    inquiry = probe.original.coverage_inquiry
    need = probe.original.present.exploration_need
    owner = bridge.owners[sid]
    sense = bridge.current_i1_correlated_sense(sid)
    if (sense is None or sense.observation.kind != "probe"
            or source.self_id != sid
            or probe.original.present.present.three_self.scope != sense.scope
            or probe.original.source_revision_refs[-1] != sense.source_revision_ref
            or probe.percept.sequence != sense.observation.seq
            or probe.percept.source != sense.provenance
            or source.native_session_id != sense.observation.session_id
            or source.native_probe_seq > sense.observation.seq
            or source.native_probe_ref != owner.current_worldbody_observation.request_id
            or source.paper_log_sha256 not in probe.original.source_revision_refs[1]
            or owner.pattern_registry.revision != probe.schema.registry_revision
            or probe.schema.options or probe.l1_proposal.frame != probe.schema
            or tuple((cid, choice.description) for cid, choice
                     in zip((cid for cid, _ in probe.l1_proposal.numbered),
                            probe.l1_proposal.request.choices, strict=True))
            != tuple((choice.choice_id, choice.description)
                     for choice in probe.l1_proposal.request.choices)
            or tuple(entry for _, entry in probe.l1_proposal.numbered)
            != ("ESCALATE_L2", "DEFER")
            or probe.l1_proposal.request.think_allowed
            or probe.model_invoked or probe.action_issue_authorized):
        raise I2OriginalGoalHold("original B/E/Native/Paper CPU source or L1 choices mismatch")
    goals = tuple(g for g in probe.schema.goals
                  if g.schema_id == "exploration" and g.goal_id == "EXPLORE_WORLD")
    if need is None:
        if inquiry is not None or goals or probe.percept.exploration_need:
            raise I2OriginalGoalHold("unqualified exploration cannot form a Goal or Question")
        need_ref = question_ref = None
    else:
        if (inquiry is None or len(goals) != 1 or not goals[0].unresolved
                or not probe.percept.exploration_need
                or need.signal.signal_kind != "EXPLORATION_NEED"
                or need.signal.source_revision_refs != probe.original.source_revision_refs
                or inquiry.self_id != sid
                or inquiry.need_signal_ref != need.signal.envelope.event_id
                or inquiry.source_revision_refs != probe.original.source_revision_refs
                or inquiry.world_epoch != source.world_epoch
                or inquiry.resident_epoch != source.resident_epoch):
            raise I2OriginalGoalHold("exploration Need, bounded Question and CPU Goal disagree")
        need_ref = need.signal.envelope.event_id
        question_ref = inquiry.question_ref
    return {
        "self_id": sid,
        "native_session_id": sense.observation.session_id,
        "native_seq": sense.observation.seq,
        "native_request_id": sense.observation.request_id,
        "native_provenance": sense.provenance.reference,
        "sense_revision": sense.source_revision_ref,
        "paper_session_id": source.paper_session_id,
        "paper_log_sha256": source.paper_log_sha256,
        "paper_tick_source_ref": source.paper_tick_source_ref,
        "world_id": source.world_id,
        "branch_id": source.branch_id,
        "world_epoch": source.world_epoch,
        "resident_epoch": source.resident_epoch,
        "registry_revision": owner.pattern_registry.revision,
        "source_revision_refs": probe.original.source_revision_refs,
        "need_signal_ref": need_ref,
        "question_candidate_ref": question_ref,
        "goal_candidates": tuple(
            (g.goal_id, g.schema_id, g.skill_id, g.skill_version,
             g.strength, g.unresolved)
            for g in goals
        ),
        "numbered": tuple((x.choice_id, x.description)
                          for x in probe.l1_proposal.request.choices),
        "original_intent_id": (
            owner.intent.current_intent.intent_id
            if owner.intent.current_intent is not None else None
        ),
        # The same active intent ID can change lifecycle (reconsideration,
        # release, etc.). Freeze the complete original event tuple so a
        # stale in-flight L1 never inherits a later Owner decision.
        "original_intent_events": tuple(
            (event.kind.value, event.intent_id, event.at_ns,
             event.objective, event.reason, event.provenance.reference)
            for event in owner.intent.events
        ),
    }


def _digest(material: dict) -> str:
    return hashlib.sha256(json.dumps(
        material, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode()).hexdigest()


def _prepare(*, bridge, boot, world, links, self_id: str,
             request_id: str,
             i2b_read_attached_lane: bool = False) -> I2OriginalGoalHandoff:
    resident = getattr(bridge, "cognitive_work", None)
    if (type(self_id) is not str or self_id not in ("A", "B")
            or not isinstance(resident, ResidentCognitiveWorkOwner)
            or type(request_id) is not str
            or re.fullmatch(
                r"i2-original-" + self_id + r"-[0-9a-f]{32}", request_id,
            ) is None):
        raise I2OriginalGoalHold("exact original A/B owner and I2 request required")
    with resident.lock:
        # The proven I1 source validator re-reads original B Present,
        # Question candidate, original E matched Native and owned Paper.
        probe = prepare_i1_cpu_schema_probe(
            bridge=bridge, boot=boot, world=world, links=links,
            self_id=self_id, i1_require_correlated_sense=True,
            i2b_read_attached_lane=i2b_read_attached_lane,
        )
        material = _material(bridge, probe, self_id)
        owner = bridge.owners[self_id]
        source_datum = CognitionDatum.from_value(
            "i2_original_exploration_source",
            material, probe.percept.source,
        )
        request = replace(
            probe.l1_proposal.request,
            request_id=request_id,
            context=(*probe.l1_proposal.request.context, source_datum),
            identity_context=project_identity_context(owner.retained.identity),
            think_allowed=False,
        )
        if (len(request.choices) != 2
                or tuple(x.description for x in request.choices)
                != ("ESCALATE_L2", "DEFER")):
            raise I2OriginalGoalHold("I2 no accepted executable Skill/Target option")
        # Recheck original source after creating the bounded request.
        second = prepare_i1_cpu_schema_probe(
            bridge=bridge, boot=boot, world=world, links=links,
            self_id=self_id, i1_require_correlated_sense=True,
            i2b_read_attached_lane=i2b_read_attached_lane,
        )
        if _material(bridge, second, self_id) != material:
            raise I2OriginalGoalHold("original B/E source changed during I2 preparation")
        goals = tuple(g for g in probe.schema.goals
                      if g.schema_id == "exploration" and g.goal_id == "EXPLORE_WORLD")
        return I2OriginalGoalHandoff(
            self_id=self_id,
            native_session_id=material["native_session_id"],
            native_seq=material["native_seq"],
            native_request_id=material["native_request_id"],
            sense_revision=material["sense_revision"],
            paper_session_id=material["paper_session_id"],
            paper_log_sha256=material["paper_log_sha256"],
            resident_epoch=material["resident_epoch"],
            registry_revision=material["registry_revision"],
            source_revision_refs=material["source_revision_refs"],
            need_signal_ref=material["need_signal_ref"],
            question_candidate_ref=material["question_candidate_ref"],
            goal_candidates=goals,
            status=("EXPLORATION_GOAL_UNRESOLVED_TARGET" if goals
                    else "NO_QUALIFIED_EXPLORATION_GOAL"),
            bounded_request=request,
            material_sha256=_digest(material),
        )


def prepare_i2_original_goal_handoff(*, bridge, boot, world, links, self_id: str,
                                     i2b_read_attached_lane: bool = False
                                     ) -> I2OriginalGoalHandoff:
    """Freeze current original qualified Need/Question/Goal for future L1."""
    return _prepare(
        bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
        request_id="i2-original-" + self_id + "-" + uuid.uuid4().hex,
        i2b_read_attached_lane=i2b_read_attached_lane,
    )


def verify_i2_original_goal_handoff(*, bridge, boot, world, links,
                                    handoff: I2OriginalGoalHandoff,
                                    i2b_read_attached_lane: bool = False) -> None:
    """Revalidate sources and exact frozen request; never submit a model."""
    if type(handoff) is not I2OriginalGoalHandoff:
        raise I2OriginalGoalHold("original typed I2 handoff required")
    try:
        fresh = _prepare(
            bridge=bridge, boot=boot, world=world, links=links,
            self_id=handoff.self_id,
            request_id=handoff.bounded_request.request_id,
            i2b_read_attached_lane=i2b_read_attached_lane,
        )
    except (RuntimeError, ValueError, KeyError, AttributeError) as exc:
        raise I2OriginalGoalHold("I2 original source changed since freeze") from exc
    if fresh != handoff:
        raise I2OriginalGoalHold("I2 frozen owner/Source/Goal/L1 request mismatch")
