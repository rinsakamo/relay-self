"""Source-revalidated, ephemeral inquiry about bounded observation coverage."""
import hashlib
import json
from dataclasses import dataclass
from typing import ClassVar

from relay_self.bd1b_owner_present_dev import BD1bOwnerPresent
from relay_self.exploration_need_dev import ExplorationBasis
from relay_self.three_self_present import EpistemicStatus


class CoverageInquiryHold(ValueError):
    """The supplied readout is not the current original-owner projection."""


@dataclass(frozen=True, slots=True)
class CoverageInquiryProposal:
    """A read-only candidate; neither a QuestionRecord nor an adoption."""

    question_ref: str
    self_id: str
    world_id: str
    branch_id: str
    world_epoch: int
    resident_epoch: int
    need_signal_ref: str
    coverage_claim_ref: str
    source_revision_refs: tuple[str, ...]
    schema_id: str
    schema_module_version: int
    schema_revision: int
    kind: ClassVar[str] = "CURRENT_OBSERVATION_COVERAGE"
    meaning: ClassVar[str] = "What remains unknown within the limits of the current observation?"
    epistemic_status: ClassVar[EpistemicStatus] = EpistemicStatus.UNKNOWN


def build_coverage_inquiry(*, bridge, boot, world, links, self_id,
                           readout: BD1bOwnerPresent) -> CoverageInquiryProposal | None:
    """Compare to a freshly rebuilt Present while holding the original lock.

    Identical evidence yields the same ref; callers can deduplicate by ref without
    maintaining a mutable proposal store. A changed source yields a new ref.
    """
    if bridge.cognitive_work is None:
        raise CoverageInquiryHold("original resident required")
    return _build_inquiry(bridge=bridge, boot=boot, world=world, links=links,
                          self_id=self_id, readout=readout,
                          present_reader=bridge.cognitive_work.read_present_cpu)


def _build_inquiry(*, bridge, boot, world, links, self_id, readout, present_reader):
    if bridge.cognitive_work is None:
        raise CoverageInquiryHold("original resident required")
    with bridge.cognitive_work.lock:
        current = present_reader(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
        )
        if type(readout) is not BD1bOwnerPresent or readout != current:
            raise CoverageInquiryHold("stale, foreign or altered Present")
        need = current.exploration_need
        if need is None:
            return None
        refs = current.present.three_self.source_revision_refs
        claims = tuple(
            claim for claim in current.present.three_self.self_world.claims
            if len(need.basis) == 1 and claim.claim_key == need.basis[0].present_ref
        )
        if (current.present.signals != (need.signal,)
                or need.signal.signal_kind != "EXPLORATION_NEED"
                or need.signal.source_revision_refs != refs
                or len(need.basis) != 1
                or need.basis[0].kind is not ExplorationBasis.EXPERIENCE_GAP
                or need.basis[0].status is not EpistemicStatus.INFERRED
                or len(claims) != 1
                or claims[0].claim_key != need.basis[0].present_ref
                or claims[0].coverage_ref != claims[0].claim_key
                or claims[0].status is not EpistemicStatus.INFERRED
                or claims[0].source_revision_refs != refs):
            raise CoverageInquiryHold("Need and bounded coverage disagree")
        source = current.source
        parts = [self_id, source.world_id, source.branch_id, source.world_epoch,
                 source.resident_epoch, need.signal.envelope.event_id,
                 claims[0].claim_key, list(refs), need.signal.schema_id,
                 need.signal.module_version, current.schema.revision]
        digest = hashlib.sha256(json.dumps(parts, ensure_ascii=False,
                                           separators=(",", ":")).encode()).hexdigest()
        return CoverageInquiryProposal(
            "coverage-inquiry:v1:" + digest, self_id, source.world_id,
            source.branch_id, source.world_epoch, source.resident_epoch,
            need.signal.envelope.event_id, claims[0].claim_key, refs,
            need.signal.schema_id, need.signal.module_version, current.schema.revision,
        )
