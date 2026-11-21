"""Ephemeral original-owner Present; no admission or persistence authority."""
from dataclasses import dataclass

from relay_self.bd1b_owner_source_dev import BD1bOwnerSource, build_bd1b_owner_source
from relay_self.common_io import ScopeRef
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


def build_bd1b_owner_present(*, bridge, boot, world, links, self_id):
    """Revalidate the live source and project solely from current owner state."""
    if bridge.cognitive_work is None:
        raise BD1bPresentHold("original resident required")
    with bridge.cognitive_work.lock:
        source = build_bd1b_owner_source(
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
        three = project_three_self(retained=owner.retained, scope=scope,
                                   epoch_ref=epoch, source_revision_refs=refs,
                                   claims=(claim,))
        present = project_present_frame(
            three_self=three, snapshot=schema,
            current_registry_revision=owner.pattern_registry.revision,
            current_source_revision_refs=refs, frame_revision=source.resident_epoch,
        )
        # The existing bridge does not retain an attested, available action
        # catalogue. A PhysicalCapability value alone is only a reference and
        # cannot establish that an action is currently available.
        return BD1bOwnerPresent(source, schema, present,
                               "NO_VERIFIED_ACTION_CATALOG")
