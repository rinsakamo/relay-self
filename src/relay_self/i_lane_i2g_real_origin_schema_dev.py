"""I2g opt-in: initial *born original* A/B recorded empty Schema source.

No invented exploration Pattern, no L1/L2/Action. This is installed ONCE
before the first real Native JOIN. It is never a migration of historic
Stage28b, which legitimately had no recorded Schema or persistent Registry.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.innate_schema import SchemaSnapshot
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner


class I2gOriginSchemaHold(RuntimeError):
    """Original initial A/B cognition cannot become source of a new typed v3."""


@dataclass(frozen=True, slots=True)
class I2gInitialSourceReceipt:
    self_ids: tuple[str, str]
    original_registry_revisions: tuple[tuple[str, int], ...]
    initial_cognition_sha256: tuple[tuple[str, str], ...]
    schema_modes: tuple[tuple[str, str], ...]
    born_initial_only: bool = True
    learning_claimed: bool = False
    physical_action_authorized: bool = False


def register_i2g_born_original_empty_schemas(
    resident: ResidentCognitiveWorkOwner,
) -> I2gInitialSourceReceipt:
    """Check both original durable Regs before atomically registering both.

    Saving cognition, when required, is the responsibility of the original
    owner constructor BEFORE this call; this method never repairs files.
    """
    if not isinstance(resident, ResidentCognitiveWorkOwner):
        raise I2gOriginSchemaHold("original resident owner required")
    with resident.lock:
        try:
            if (tuple(sorted(resident.owners)) != ("A", "B")
                    or resident._present_schemas):
                raise I2gOriginSchemaHold("unique unregistered born A/B required")
            initial = initial_patterns()
            snapshots = []
            digests = []
            for sid in ("A", "B"):
                owner = resident.owners[sid]
                state = resident._state(sid)
                if (
                    owner.self_id != sid or owner.cohort is not resident
                    or state.mode != "OFFLINE" or state.epoch != 0
                    or owner.supervisor.open_actions or owner.intent.current_intent
                    or owner.pending_questions
                    or owner.skills or owner.peer_deliveries
                    or owner.retained.memories
                    or owner.pattern_registry != initial
                    or owner.retained.pattern_registry != initial
                    or owner.retained.exploration_continuity is not None
                    or load_persistent_cognition(owner.files.cognition_file)
                    != owner.retained
                ):
                    raise I2gOriginSchemaHold(
                        "born Self/innate registry must match first persisted source"
                    )
                digest = hashlib.sha256(
                    owner.files.cognition_file.read_bytes()
                ).hexdigest()
                digests.append((sid, digest))
                snapshots.append((sid, SchemaSnapshot(sid, initial.revision, ())))
            # Original resident has the ONLY Schema registration authority.
            # If the second fails no partial installed A activation may leak.
            try:
                for sid, snapshot in snapshots:
                    resident.register_present_schema(sid, snapshot)
            except (RuntimeError, ValueError):
                resident._present_schemas.clear()
                raise
            return I2gInitialSourceReceipt(
                ("A", "B"),
                tuple((sid, snap.revision) for sid, snap in snapshots),
                tuple(digests),
                tuple((sid, "NO_EXPLORATION_MODULE") for sid, _ in snapshots),
            )
        except I2gOriginSchemaHold:
            raise
        except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
            raise I2gOriginSchemaHold(
                "original born A/B initial Schema/Registry not durable"
            ) from exc
