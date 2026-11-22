"""Nonissuing cognitive restore reconciliation for P0-D typed owner cuts.

Two independent cognitive representations may survive a coarse checkpoint:
PersistentCognition v3 and the typed SelfOwnerCut pattern registry. Until the
owner-state schema adopts the same strict Preset codec, a mismatch MUST HOLD.
Never treat old physical WAL or L0 cursors as grants on a forked World.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from relay_self.cognitive_minimal_dev import PatternRegistry
from relay_self.persistent_cognition import (
    PersistentCognition,
    load_persistent_cognition,
)
from relay_self.preset_registry_checkpoint import (
    PresetCheckpointRefusal,
    decode_pattern_registry,
    encode_pattern_registry,
)


@dataclass(frozen=True, slots=True)
class InertRestoredSchema:
    self_id: str
    registry: PatternRegistry
    prior_registry_revision: int
    new_worldbody_observation_required: bool = True
    old_intent_or_skill_resume_authorized: bool = False
    native_action_issue_authorized: bool = False
    old_llm_output_current: bool = False
    old_target_current: bool = False


def reconcile_restored_self_schema(
    cognition: PersistentCognition,
    *,
    owner_cut_pattern_registry: object,
    expected_self_id: str,
) -> InertRestoredSchema:
    """Require exact matching owner-state cut before accepting a restored Registry.

    The owner_cut_pattern_registry is the *parsed* JSON registry field from a
    committed, hash-verified P0-D typed owner cut. Caller must check cohort
    generation/World/branch/roster, WAL and source ownership separately.
    """
    if (not isinstance(cognition, PersistentCognition)
            or cognition.identity.self_id != expected_self_id
            or cognition.pattern_registry is None):
        raise PresetCheckpointRefusal(
            "Self cognition missing matching v3 Schema registry"
        )
    parsed = decode_pattern_registry(
        owner_cut_pattern_registry, expected_self_id=expected_self_id,
    )
    retained = cognition.pattern_registry
    if encode_pattern_registry(
        retained, self_id=expected_self_id,
    ) != encode_pattern_registry(parsed, self_id=expected_self_id):
        raise PresetCheckpointRefusal(
            "Persistent cognition and typed owner cut disagree on Schema revision"
        )
    return InertRestoredSchema(
        expected_self_id, parsed, parsed.revision,
    )


def reconcile_restored_self_schema_file(
    cognition_path: Path,
    *,
    owner_cut_pattern_registry: object,
    expected_self_id: str,
) -> InertRestoredSchema:
    """Post-hash copy read only; never starts a Skill or grants Action issuance."""
    return reconcile_restored_self_schema(
        load_persistent_cognition(cognition_path),
        owner_cut_pattern_registry=owner_cut_pattern_registry,
        expected_self_id=expected_self_id,
    )
