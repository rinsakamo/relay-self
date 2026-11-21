"""Explicit fresh-Self schema configuration; no cognition or action execution."""
from dataclasses import dataclass

from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.cognitive_minimal_dev import initial_patterns, initial_patterns_with_relative_move
from relay_self.innate_schema import SchemaActivation, SchemaMode, SchemaModuleSpec, SchemaSnapshot
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner


class SchemaBootstrapHold(RuntimeError):
    """Schema activation cannot be established from the saved Self."""


@dataclass(frozen=True, slots=True)
class SchemaBootstrapConfig:
    exploration_enabled: bool = False

    def __post_init__(self):
        if type(self.exploration_enabled) is not bool:
            raise ValueError("explicit boolean exploration configuration required")


def fresh_pattern_registry(config: SchemaBootstrapConfig):
    if not isinstance(config, SchemaBootstrapConfig):
        raise ValueError("explicit schema bootstrap configuration required")
    return initial_patterns_with_relative_move() if config.exploration_enabled else initial_patterns()


def create_fresh_owner(*, config: SchemaBootstrapConfig, retained, intent, native_session_id,
                       last_observed_tick, files, physical_supervisor):
    """Construct the original checkpoint owner with the explicitly selected registry."""
    owner = CheckpointedCognitiveOwner(
        retained=retained, intent=intent, pattern_registry=fresh_pattern_registry(config),
        native_session_id=native_session_id, last_observed_tick=last_observed_tick,
        files=files, physical_supervisor=physical_supervisor,
    )
    owner._fresh_schema_bootstrap_config = config
    return owner


def bootstrap_fresh_schemas(resident: ResidentCognitiveWorkOwner, config: SchemaBootstrapConfig):
    """Register separate snapshots before login, after original owners are created."""
    expected = fresh_pattern_registry(config)
    with resident.lock:
        # Check every Self before publishing any registration.
        for sid, owner in resident.owners.items():
            state = resident._state(sid)
            if (getattr(owner, "_fresh_schema_bootstrap_config", None) != config
                    or owner.fresh_native_observation_required
                    or owner.pattern_registry != expected or state.mode != "OFFLINE"
                    or state.epoch != 0 or sid in resident._present_schemas):
                raise SchemaBootstrapHold("fresh registry or registration state mismatch")
        for sid, owner in resident.owners.items():
            spec = SchemaModuleSpec(
                "exploratory", 1, frozenset({SchemaMode.FULL}),
                ("QUESTION_CANDIDATE", "EXPLORATION_NEED"), (),
                Provenance("innate-schema", "cognitive-v0.1-exploration-dev"),
            )
            snapshot = SchemaSnapshot(sid, owner.pattern_registry.revision, (
                SchemaActivation(spec, SchemaMode.FULL if config.exploration_enabled else SchemaMode.OFF),
            ))
            resident.register_present_schema(sid, snapshot)
        for owner in resident.owners.values():
            del owner._fresh_schema_bootstrap_config


def bootstrap_restored_schemas(resident: ResidentCognitiveWorkOwner, config: SchemaBootstrapConfig):
    """HOLD: current checkpoint formats contain no attested Schema activation."""
    if not isinstance(resident, ResidentCognitiveWorkOwner) or not isinstance(config, SchemaBootstrapConfig):
        raise ValueError("original resident and explicit schema configuration required")
    raise SchemaBootstrapHold("restored Schema activation is not recorded in checkpoint")
