"""Explicit fresh-Self schema configuration; no cognition or action execution."""
from dataclasses import dataclass

from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
from relay_self.cognitive_minimal_dev import initial_patterns, initial_patterns_with_relative_move
from relay_self.exploration_schema_record_dev import require_recorded_schema
from relay_self.innate_schema import SchemaMode
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.self_owner_checkpoint_dev import SelfOwnerCut


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
            from relay_self.exploration_schema_record_dev import canonical_exploration_snapshot

            snapshot = canonical_exploration_snapshot(
                self_id=sid, registry=owner.pattern_registry,
                mode=SchemaMode.FULL if config.exploration_enabled else SchemaMode.OFF,
            )
            resident.register_present_schema(sid, snapshot)
        for owner in resident.owners.values():
            del owner._fresh_schema_bootstrap_config


def bootstrap_restored_schemas(
    resident: ResidentCognitiveWorkOwner,
    config: SchemaBootstrapConfig | None,
    *,
    source_cuts: tuple[SelfOwnerCut, ...] | None = None,
):
    """Replay ONLY same-generation original recorded activations before login.

    An optional caller config can RESTRICT the recorded state, never invent or
    turn on a module. Legacy source without a v3 activation stays HOLD.
    """
    if (not isinstance(resident, ResidentCognitiveWorkOwner)
            or (config is not None and not isinstance(config, SchemaBootstrapConfig))):
        raise ValueError("original resident and optional config required")
    with resident.lock:
        if (type(source_cuts) is not tuple or len(source_cuts) != len(resident.owners)
                or {cut.self_id for cut in source_cuts} != set(resident.owners)
                or any(type(cut) is not SelfOwnerCut or cut.schema_snapshot is None
                       for cut in source_cuts)):
            raise SchemaBootstrapHold("restored Schema activation is not recorded in checkpoint")
        # Full cohort preflight before installing either registration.
        for cut in source_cuts:
            owner = resident.owners[cut.self_id]
            state = resident._state(cut.self_id)
            if (state.mode != "OFFLINE" or state.epoch != 0
                    or cut.self_id in resident._present_schemas
                    or owner.pattern_registry != cut.pattern_registry
                    or owner.retained.pattern_registry != cut.pattern_registry):
                raise SchemaBootstrapHold("original offline schema source no longer matches")
            try:
                snapshot = require_recorded_schema(
                    cut.schema_snapshot, self_id=cut.self_id,
                    registry=owner.pattern_registry,
                )
            except ValueError as exc:
                raise SchemaBootstrapHold("restored Schema snapshot invalid") from exc
            enabled = snapshot.get("exploratory").mode is SchemaMode.FULL
            if config is not None and enabled != config.exploration_enabled:
                raise SchemaBootstrapHold("requested activation differs from recorded source")
        for cut in source_cuts:
            resident.register_present_schema(cut.self_id, cut.schema_snapshot)
