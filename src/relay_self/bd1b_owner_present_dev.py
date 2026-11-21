"""Ephemeral original-owner Present; no admission or persistence authority."""
import hashlib
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerNearbyEntitiesCoverage
from relay_self.bd1b_owner_source_dev import BD1bOwnerSource, build_bd1b_owner_source
from relay_self.common_io import Clock, ClockStamp, CommonEnvelope, ScopeRef
from relay_self.exploration_need_dev import (
    ExplorationBasis,
    ExplorationEvidence,
    ExplorationNeed,
    propose_exploration_need,
)
from relay_self.innate_schema import SchemaSnapshot
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError
from relay_self.three_self_present import (
    EpistemicStatus,
    Lens,
    LensClaim,
    PresentFrame,
    project_present_frame,
    project_three_self,
)


class BD1bPresentHold(RuntimeError):
    """Owner schema registration is unavailable or stale."""


@dataclass(frozen=True, slots=True)
class BD1bOwnerPresent:
    source: BD1bOwnerSource
    schema: SchemaSnapshot
    present: PresentFrame
    no_candidate_reason: str
    exploration_need: ExplorationNeed | None = None
    no_need_reason: str | None = None


def build_bd1b_owner_present(*, bridge, boot, world, links, self_id):
    """Revalidate the live source and project solely from current owner state."""
    return _build_present(bridge=bridge, boot=boot, world=world, links=links,
                          self_id=self_id, source_reader=build_bd1b_owner_source)


def _build_present(*, bridge, boot, world, links, self_id, source_reader):
    if bridge.cognitive_work is None:
        raise BD1bPresentHold("original resident required")
    with bridge.cognitive_work.lock:
        source = source_reader(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
        )
        try:
            schema = bridge.cognitive_work.present_schema(self_id)
        except ResidentCognitiveWorkError as exc:
            raise BD1bPresentHold("current registered schema required") from exc
        owner = bridge.owners[self_id]
        probe = owner.current_worldbody_observation
        scope = ScopeRef(self_id, source.paper_session_id)
        refs = (
            f"native:{source.native_session_id}:{source.native_probe_ref}:{source.native_probe_seq}:{source.native_probe_source_ref}",
            f"paper:{source.paper_session_id}:{source.paper_boot_id}:{source.paper_log_sha256}:{source.paper_tick_source_ref}",
        )
        epoch = f"resident:{source.resident_epoch}:world:{source.world_epoch}"
        claim = LensClaim(scope, Lens.SELF_BODY, "native-worldbody",
                          EpistemicStatus.OBSERVED, (probe.provenance,), refs,
                          source.native_probe_ref)
        coverage = getattr(probe.snapshot, "nearby_entities_coverage", None)
        claims = [claim]
        coverage_key = None
        if type(coverage) is MineflayerNearbyEntitiesCoverage:
            # This describes the probe record, not the existence or absence of
            # anything beyond its bounded registry, distance and result limit.
            coverage_key = f"native-coverage:{source.native_session_id}:{source.native_probe_ref}:{source.native_probe_seq}"
            value = (f"scope:{coverage.source_scope}:max-distance:{coverage.max_distance}:"
                     f"max-entities:{coverage.max_entities}:candidates:{coverage.candidate_count}:"
                     f"truncated:{coverage.truncated}:world-knowledge-not-comprehensive")
            claims.append(LensClaim(scope, Lens.SELF_WORLD, coverage_key,
                                    EpistemicStatus.INFERRED, (probe.provenance,), refs,
                                    value, coverage_key))
        three = project_three_self(retained=owner.retained, scope=scope,
                                   epoch_ref=epoch, source_revision_refs=refs,
                                   claims=tuple(claims))
        present = project_present_frame(
            three_self=three, snapshot=schema,
            current_registry_revision=owner.pattern_registry.revision,
            current_source_revision_refs=refs, frame_revision=source.resident_epoch,
        )
        need = None
        if coverage_key is not None:
            event_hash = hashlib.sha256((self_id + epoch + "|".join(refs)).encode()).hexdigest()
            envelope = CommonEnvelope(
                event_id="exploration-need:" + event_hash, kind="COGNITIVE_SIGNAL",
                scope=scope, occurred_at=ClockStamp(Clock.WORLD_TICK, source.native_world_time_tick),
                provenance=probe.provenance, source_refs=(probe.provenance,),
            )
            need = propose_exploration_need(
                present=present, snapshot=schema, schema_id="exploratory",
                evidence=(ExplorationEvidence(ExplorationBasis.EXPERIENCE_GAP,
                                               coverage_key, EpistemicStatus.INFERRED),),
                other_needs=(), disposition=None, signal_envelope=envelope,
                current_registry_revision=owner.pattern_registry.revision,
                current_source_revision_refs=refs,
            )
            if need is not None:
                present = project_present_frame(
                    three_self=three, snapshot=schema,
                    current_registry_revision=owner.pattern_registry.revision,
                    current_source_revision_refs=refs, frame_revision=source.resident_epoch,
                    signals=(need.signal,),
                )
        # The existing bridge does not retain an attested, available action
        # catalogue. A PhysicalCapability value alone is only a reference and
        # cannot establish that an action is currently available.
        # Paper is external to the resident lock. Recheck its receipt and the
        # native/owner identity after projection before exposing the result.
        if (source_reader(bridge=bridge, boot=boot, world=world,
                                    links=links, self_id=self_id) != source
                or bridge.cognitive_work.present_schema(self_id) != schema
                or owner.current_worldbody_observation is not probe):
            raise BD1bPresentHold("source changed during projection")
        return BD1bOwnerPresent(source, schema, present,
                               "NO_VERIFIED_ACTION_CATALOG", need,
                               None if need else ("NO_COVERAGE_EVIDENCE" if coverage_key is None
                                                  else "NEED_SCHEMA_INELIGIBLE"))
