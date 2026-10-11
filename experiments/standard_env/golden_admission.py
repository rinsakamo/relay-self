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


def main(argv: list[str] | None = None) -> int:
    """Read-only qualified-World check; no model, port, JVM, Node or game."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Verify exact #583 stopped World identity; never launch a process"
    )
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--initial-evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        binding = verify_qualified_world(
            args.jar, args.snapshot, args.manifest, args.initial_evidence,
        )
    except (OSError, TypeError, WorldBindingRejected) as exc:
        print(json.dumps({
            "classification": "GOLDEN_WORLD_ADMISSION_BLOCKED",
            "reason": type(exc).__name__,
            "physical_execution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps({
        "classification": "GOLDEN_WORLD_BYTES_PINNED_OFFLINE",
        "qualified_bootstrap_head": QUALIFIED_BOOTSTRAP_HEAD,
        "qualified_scope": QUALIFICATION,
        "jar_sha256": binding.jar_sha256,
        "world_manifest_sha256": binding.manifest_sha256,
        "initial_native_sha256": binding.initial_evidence_sha256,
        "files": len(binding.files),
        "physical_execution_authorized": False,
        "llm_post": 0,
        "world_action": 0,
        "golden_run": "NOT_RUN",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
