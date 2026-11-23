"""R2-0: one pure compatibility contract for legacy Present vs Schema CURRENT.

This code owns **no state**. It cannot load a checkpoint, read a Native/Paper
source, register a Schema, select an Intent or issue a Physical/GPU action.
The original B Owner remains the sole mutation authority, R1 remains an
opt-in read-only consumer, and R2-1 product routing is explicitly out of scope.

Keeping the initial R1 comparison and cached freshness recheck on the same
predicate prevents independent drift between their refusal conditions.
"""
from __future__ import annotations

from relay_self.bd1b_owner_present_dev import BD1bOwnerPresent
from relay_self.r0_cognitive_context_dev import CurrentSchemaFrame


# Stable diagnostic codes already returned by the original R1 comparison.
# Do not turn an expected legacy OBSERVED SelfBody claim into Schema CURRENT.
R2_LEGACY_CURRENT_DIAGNOSTIC_CODES = (
    "LEGACY_SOURCE_DIFFERS_FROM_R1_CURRENT",
    "LEGACY_SCHEMA_DIFFERS_FROM_R1_CURRENT",
    "LEGACY_SELF_OR_WORLD_SCOPE_MISMATCH",
    "LEGACY_NATIVE_PAPER_REVISION_MISMATCH",
    "LEGACY_OWNER_EPOCH_MISMATCH",
    "LEGACY_REGISTRY_REVISION_MISMATCH",
    "LEGACY_SCHEMA_SIGNAL_MISMATCH",
    "LEGACY_NEED_REFERENCE_MISMATCH",
    "LEGACY_ATTENTION_REFERENCE_MISMATCH",
)


def legacy_current_mismatch_codes(
    legacy: BD1bOwnerPresent, current: CurrentSchemaFrame,
) -> tuple[str, ...]:
    """Compare exactly the nine existing R1 ownership/Present boundaries.

    Read-only pure projection: no lock acquisition, file access, Owner
    mutation, Memory store, schema registration, new source qualification or
    model/Physical authorization. The caller owns the original resident lock,
    original Source readback and epoch validity checks. A caller may use these
    codes only for diagnostics or to **reject** stale cached context.
    """
    if type(legacy) is not BD1bOwnerPresent or type(current) is not CurrentSchemaFrame:
        return ("LEGACY_OR_CURRENT_TYPE_INVALID",)

    differences: list[str] = []
    checks = (
        (legacy.source == current.source, R2_LEGACY_CURRENT_DIAGNOSTIC_CODES[0]),
        (legacy.schema == current.schema, R2_LEGACY_CURRENT_DIAGNOSTIC_CODES[1]),
        (legacy.present.three_self.scope == current.scope,
         R2_LEGACY_CURRENT_DIAGNOSTIC_CODES[2]),
        (legacy.present.three_self.source_revision_refs == current.source_revision_refs,
         R2_LEGACY_CURRENT_DIAGNOSTIC_CODES[3]),
        (legacy.present.frame_revision == current.owner_epoch,
         R2_LEGACY_CURRENT_DIAGNOSTIC_CODES[4]),
        (legacy.present.registry_revision == current.schema.revision,
         R2_LEGACY_CURRENT_DIAGNOSTIC_CODES[5]),
        (legacy.present.signals == current.signals,
         R2_LEGACY_CURRENT_DIAGNOSTIC_CODES[6]),
        (legacy.present.need_refs == current.need_refs,
         R2_LEGACY_CURRENT_DIAGNOSTIC_CODES[7]),
        (legacy.present.attention_refs == current.attention_refs,
         R2_LEGACY_CURRENT_DIAGNOSTIC_CODES[8]),
    )
    for agrees, code in checks:
        if not agrees:
            differences.append(code)
    return tuple(differences)
