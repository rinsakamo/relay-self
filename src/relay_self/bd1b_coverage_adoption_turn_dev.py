"""CPU-only preparation of a source-bound coverage adoption choice.

A turn is not a decision, ticket, persistence authority, or post-inference proof.
The existing source verifier deliberately requires the GPU lane to be disconnected.
"""
from dataclasses import asdict, dataclass
from uuid import uuid4

from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    project_identity_context,
)
from relay_self.stage28c2c_fresh_recovered_l1_dev import _freeze_hash


class CoverageAdoptionTurnHold(RuntimeError):
    """The original source or frozen request is no longer current."""


CHOICES = (
    BoundedChoice("1", "ADOPT — adopt this inquiry as my own OPEN Question"),
    BoundedChoice("2", "HOLD — do not adopt now; leave it pending"),
    BoundedChoice("3", "DECLINE — do not adopt this inquiry"),
)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class CoverageAdoptionTurn:
    self_id: str
    owner: object
    intent_owner: object
    intent_events: tuple
    owner_scope: tuple[int, str, int]
    cohort_owners: tuple[object, object]
    cohort_scopes: tuple[tuple[int, str, int], tuple[int, str, int]]
    cohort_probes: tuple[object, object]
    continuity_revision: int
    inquiry: object
    source: object
    original_probe: object
    work_ref: str
    request: BoundedChoiceRequest
    candidate_set_sha256: str


def _snapshot(*, bridge, boot, world, links, self_id, request_id,
              present_reader=None, inquiry_reader=None):
    resident = bridge.cognitive_work
    if resident is None:
        raise CoverageAdoptionTurnHold("original resident required")
    present_reader = present_reader or resident.read_present_cpu
    inquiry_reader = inquiry_reader or resident.read_coverage_inquiry_cpu
    owner = resident.owners[self_id]
    owner._eligible()
    if bridge.owners.get(self_id) is not owner or owner.self_id != self_id:
        raise CoverageAdoptionTurnHold("original owner identity mismatch")
    events = owner.intent.events
    identity = owner.retained.identity
    present = present_reader(bridge=bridge, boot=boot, world=world,
                                        links=links, self_id=self_id)
    inquiry = inquiry_reader(bridge=bridge, boot=boot, world=world,
                                                  links=links, self_id=self_id)
    if inquiry is None:
        raise CoverageAdoptionTurnHold("current coverage inquiry required")
    # A second projection must agree with the inquiry's complete source and schema.
    if (inquiry.self_id != self_id or inquiry.source_revision_refs != present.present.three_self.source_revision_refs
            or inquiry.schema_revision != present.schema.revision
            or inquiry.world_id != present.source.world_id
            or inquiry.branch_id != present.source.branch_id
            or inquiry.world_epoch != present.source.world_epoch
            or inquiry.resident_epoch != present.source.resident_epoch):
        raise CoverageAdoptionTurnHold("inquiry source changed")
    scope = resident.current_scope(self_id)
    probe = owner.current_worldbody_observation
    continuity = owner.retained.exploration_continuity
    if continuity is not None and continuity.self_id != self_id:
        raise CoverageAdoptionTurnHold("foreign continuity")
    revision = 0 if continuity is None else continuity.revision
    intent = owner.intent.current_intent
    context = CognitionDatum.from_value(
        "current_coverage_inquiry", {
            **asdict(inquiry), "meaning": inquiry.meaning,
            "epistemic_status": inquiry.epistemic_status.value,
            "source": asdict(present.source),
        }, Provenance("coverage-inquiry", inquiry.question_ref),
    )
    request = BoundedChoiceRequest(
        request_id=request_id,
        instruction="Choose whether to adopt this current observation coverage inquiry as your own OPEN Question.",
        intent_id=None if intent is None else intent.intent_id,
        focus=inquiry.question_ref, choices=CHOICES, context=(context,),
        identity_context=project_identity_context(owner.retained.identity), think_allowed=False,
    )
    digest = _freeze_hash(self_id, scope, request, boot, probe,
                          owner.pattern_registry.revision, ())
    final_present = present_reader(
        bridge=bridge, boot=boot, world=world, links=links, self_id=self_id
    )
    if (final_present != present or inquiry_reader(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id
        ) != inquiry or owner.intent.events != events or owner.retained.identity != identity
            or resident.owners[self_id] is not owner
            or owner.current_worldbody_observation is not probe
            or resident.current_scope(self_id) != scope
            or (0 if owner.retained.exploration_continuity is None
                else owner.retained.exploration_continuity.revision) != revision):
        raise CoverageAdoptionTurnHold("owner or source changed during preparation")
    return owner, scope, revision, inquiry, present.source, probe, request, digest


def prepare_coverage_adoption_turn(*, bridge, boot, world, links, self_id):
    """Freeze a current inquiry under the original lock before GPU connection."""
    resident = bridge.cognitive_work
    if resident is None:
        raise CoverageAdoptionTurnHold("original resident required")
    with resident.lock:
        work_ref = "coverage-adoption-work-" + uuid4().hex
        request_id = "coverage-adoption-request-" + uuid4().hex
        owner, scope, rev, inquiry, source, probe, request, digest = _snapshot(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            request_id=request_id,
        )
        turn = CoverageAdoptionTurn(self_id, owner, owner.intent, owner.intent.events,
                                    scope, tuple(resident.owners[sid] for sid in ("A", "B")),
                                    tuple(resident.current_scope(sid) for sid in ("A", "B")),
                                    tuple(resident.owners[sid].current_worldbody_observation for sid in ("A", "B")),
                                    rev, inquiry, source, probe, work_ref,
                                    request, digest)
        resident._coverage_adoption_turns[work_ref] = turn
        return turn


def validate_coverage_adoption_turn_cpu(*, bridge, boot, world, links, turn):
    """Recheck a turn before GPU connection; never validate a model result."""
    if type(turn) is not CoverageAdoptionTurn or bridge.cognitive_work is None:
        raise CoverageAdoptionTurnHold("original turn required")
    with bridge.cognitive_work.lock:
        if bridge.cognitive_work._coverage_adoption_turns.get(turn.work_ref) is not turn:
            raise CoverageAdoptionTurnHold("unregistered prepared turn")
        owner, scope, rev, inquiry, source, probe, request, digest = _snapshot(
            bridge=bridge, boot=boot, world=world, links=links, self_id=turn.self_id,
            request_id=turn.request.request_id,
        )
        if (owner is not turn.owner or owner.intent is not turn.intent_owner
                or owner.intent.events != turn.intent_events or scope != turn.owner_scope
                or any(bridge.cognitive_work.owners[sid] is not turn.cohort_owners[i]
                       or bridge.cognitive_work.current_scope(sid) != turn.cohort_scopes[i]
                       or bridge.cognitive_work.owners[sid].current_worldbody_observation is not turn.cohort_probes[i]
                       for i, sid in enumerate(("A", "B")))
                or rev != turn.continuity_revision or inquiry != turn.inquiry
                or source != turn.source or probe is not turn.original_probe
                or request != turn.request or digest != turn.candidate_set_sha256
                or not turn.work_ref.startswith("coverage-adoption-work-")):
            raise CoverageAdoptionTurnHold("turn changed or stale")
