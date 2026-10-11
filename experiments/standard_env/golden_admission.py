"""RSEE Golden Run admission: EXACT qualified native World lineage.

This code verifies operator-held STOPPED World bytes only. It does not grant
a new Minecraft, LLM, GPU, S49 Action or scientific run authorization.
"""
from __future__ import annotations

from pathlib import Path

from experiments.standard_env.world_binding import (
    JAR_SHA256,
    WorldBinding,
    WorldBindingRejected,
    verify_world_binding,
)

# Exact bootstrap #583, independently read back on 2026-10-11.
# The approved *bootstrap* grant is exhausted and NOT a Golden Run grant.
QUALIFIED_BOOTSTRAP_HEAD = "ca4afee5c78102ed3f917ea6011b6bef124d98e3"
QUALIFIED_MANIFEST_SHA256 = (
    "5b1876db6a97fc8b9c4331938ca47727037c5626a241213d871b2073665996f8"
)
QUALIFIED_INITIAL_EVIDENCE_SHA256 = (
    "7c974390d1879967ef5b5ce3b37d59a9628974c5f3e2a2dfefcf5e1e7701648b"
)
QUALIFICATION = "WORLD_SNAPSHOT_QUALIFIED_STOPPED_BYTES_AND_NATIVE_STATE_ONLY"


def verify_qualified_world(
    jar: Path, snapshot: Path, manifest: Path, initial_evidence: Path,
) -> WorldBinding:
    """Bind to the specific independently audited snapshot, no substitutions.

    A self-consistent new manifest is NOT enough: all identity anchors must
    equal the read-back receipts for #583's *one* stopped initial World.
    """
    binding = verify_world_binding(
        jar, snapshot, manifest, initial_evidence,
        expected_jar_sha256=JAR_SHA256,
    )
    if (binding.jar_sha256 != JAR_SHA256
            or binding.manifest_sha256 != QUALIFIED_MANIFEST_SHA256
            or binding.initial_evidence_sha256 != QUALIFIED_INITIAL_EVIDENCE_SHA256):
        raise WorldBindingRejected("not the independently qualified #583 initial World")
    return binding
