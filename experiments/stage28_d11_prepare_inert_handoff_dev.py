"""D11: independently audited D9 source -> inert original D8 A/B fork.

This is a CPU-only, one-shot local DEV handoff. It NEVER launches Paper,
Node, a model, L2, or physical Actions. D10's separate-process audit is
verified again BEFORE any restored World/Self bytes can be written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from relay_self.exploration_d10_original_source_audit_dev import (
    audit_d10_original_d9_source,
)
from relay_self.exploration_d8_owned_source_dev import (
    D8OwnedSourcePins,
    inspect_d8_original_source,
    load_d8_pins,
)
from relay_self.stage28c1_inert_restore_dev import (
    inspect_stage28c_source,
    prepare_stage28c_inert_restore,
)


class D11HandoffHold(RuntimeError):
    """No qualified source/fork/pins: do not launch the restored World."""


def _digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise D11HandoffHold("independent evidence file absent or symlinked")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _outside(target: Path, root: Path) -> bool:
    target_abs, root_abs = target.absolute(), root.absolute()
    return target_abs != root_abs and root_abs not in target_abs.parents


def inspect_d11_source(
    evidence_dir: Path,
    generation: Path,
    *,
    manifest_sha256: str,
    manifest_files: int,
    world_id: str,
    source_branch: str,
    committed_sha256: str,
) -> tuple[object, str]:
    """Recompute D10 from sealed bytes, then compare its EXTERNAL audit."""
    evidence_dir, generation = Path(evidence_dir), Path(generation)
    if (
        evidence_dir.is_symlink() or generation.is_symlink()
        or not evidence_dir.is_dir()
        or generation.parent.name != "typed-world-self-generations"
        or generation.parent.parent.absolute() != evidence_dir.absolute()
        or _digest(evidence_dir / "SHA256SUMS") != manifest_sha256
        or type(manifest_files) is not int or not 1 <= manifest_files <= 100000
    ):
        raise D11HandoffHold("sealed original evidence path or pins invalid")
    source = inspect_stage28c_source(
        generation, expected_world_id=world_id,
        expected_source_branch_id=source_branch,
        expected_generation_id=generation.name,
    )
    if source.committed_sha256 != committed_sha256:
        raise D11HandoffHold("original COMMITTED digest disagrees")
    original = audit_d10_original_d9_source(
        evidence_dir, generation,
        expected_manifest_sha256=manifest_sha256,
        expected_files=manifest_files,
        expected_world_id=world_id,
        expected_source_branch_id=source_branch,
        expected_committed_sha256=committed_sha256,
    )
    audit_path = evidence_dir.parent / "d10-independent-audit.json"
    audit_sha256 = _digest(audit_path)
    try:
        outside_audit = json.loads(audit_path.read_bytes())
    except (OSError, UnicodeError, ValueError) as exc:
        raise D11HandoffHold("external independent D10 audit invalid") from exc
    if (
        outside_audit != json.loads(json.dumps(asdict(original)))
        or original.original_model_choice_id != "1"
        or original.independent_source_classification
        != "D10_ORIGINAL_BYTES_CORRELATED_DEV"
        or original.original_l2_replay_authorized
        or original.original_action_replay_authorized
        or original.original_real_world_execution_attested
    ):
        raise D11HandoffHold("independent D10 raw proof differs or L1 deferred")
    return original, audit_sha256


def prepare_d11_inert_handoff(
    evidence_dir: Path,
    generation: Path,
    restored: Path,
    pins_path: Path,
    *,
    manifest_sha256: str,
    manifest_files: int,
    world_id: str,
    source_branch: str,
    committed_sha256: str,
    restore_id: str,
) -> dict[str, object]:
    """Prepare exactly one inert fork and exclusive D8 8-field pins JSON."""
    evidence_dir, generation = Path(evidence_dir), Path(generation)
    restored, pins_path = Path(restored), Path(pins_path)
    if (
        not restore_id or type(restore_id) is not str
        or restored.exists() or restored.is_symlink()
        or pins_path.exists() or pins_path.is_symlink()
        or pins_path.parent.is_symlink() or not pins_path.parent.is_dir()
        or not _outside(restored, evidence_dir)
        or not _outside(pins_path, evidence_dir)
        or not _outside(pins_path, restored)
        or pins_path.absolute() == restored.absolute()
    ):
        raise D11HandoffHold("fresh inert fork and external pins paths required")

    _, independent_digest = inspect_d11_source(
        evidence_dir, generation,
        manifest_sha256=manifest_sha256, manifest_files=manifest_files,
        world_id=world_id, source_branch=source_branch,
        committed_sha256=committed_sha256,
    )
    fork = prepare_stage28c_inert_restore(
        generation, restored,
        expected_world_id=world_id,
        expected_source_branch_id=source_branch,
        expected_committed_sha256=committed_sha256,
        expected_generation_id=generation.name, restore_id=restore_id,
    )
    pins = D8OwnedSourcePins(
        generation_id=generation.name,
        world_id=world_id,
        source_branch_id=source_branch,
        fork_branch_id=fork.restored_branch_id,
        committed_sha256=committed_sha256,
        stage28b_evidence_sha256=manifest_sha256,
        stage28b_evidence_files=manifest_files,
        d10_source_audit_sha256=independent_digest,
    )
    # Do not publish ready-to-use pins until D8 independently validates the
    # NEW fork and the actual D10/B historical manifest. No L2 replay.
    candidate, _ = inspect_d8_original_source(
        generation, restored, evidence_dir, pins=pins,
    )
    if (
        candidate.owner_roster != ("A", "B")
        or candidate.real_world_attested
        or candidate.physical_action_issue_authorized
        or candidate.l2_dispatch_authorized
    ):
        raise D11HandoffHold("original D8 inert source gate rejected")
    serialized = (json.dumps(asdict(pins), sort_keys=True, indent=2) + "\n").encode()
    with pins_path.open("xb") as stream:
        os.chmod(pins_path, 0o600)
        stream.write(serialized)
        stream.flush()
        os.fsync(stream.fileno())
    if pins_path.read_bytes() != serialized or load_d8_pins(pins_path) != pins:
        raise D11HandoffHold("D8 pins disk readback differs; freeze as HOLD")
    return {
        "classification": "D11_INERT_HANDOFF_PREPARED_OFFLINE_DEV",
        "generation_id": pins.generation_id,
        "world_id": pins.world_id,
        "fork_branch_id": pins.fork_branch_id,
        "d10_independent_audit_sha256": independent_digest,
        "d8_source_pins_sha256": _digest(pins_path),
        "d8_source_pins_path": str(pins_path.absolute()),
        "restored": str(restored.absolute()),
        "real_world_execution_attested": False,
        "real_model_execution_attested": False,
        "old_l2_replay_authorized": False,
        "physical_action_issue_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--manifest-files", type=int, required=True)
    parser.add_argument("--world-id", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--committed-sha256", required=True)
    parser.add_argument("--restored", type=Path)
    parser.add_argument("--restore-id")
    parser.add_argument("--source-pins-json", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect-only", action="store_true")
    mode.add_argument("--prepare-once", action="store_true")
    args = parser.parse_args()
    options = dict(
        manifest_sha256=args.manifest_sha256,
        manifest_files=args.manifest_files,
        world_id=args.world_id,
        source_branch=args.source_branch,
        committed_sha256=args.committed_sha256,
    )
    try:
        if args.inspect_only:
            if any(v is not None for v in (
                args.restored, args.restore_id, args.source_pins_json,
            )):
                raise D11HandoffHold("inspect-only cannot declare outputs")
            _, audit_sha = inspect_d11_source(
                args.evidence_dir, args.generation, **options,
            )
            result = {
                "classification": "D11_PRE_FORK_SOURCE_BYTES_VERIFIED_DEV",
                "d10_independent_audit_sha256": audit_sha,
                "real_world_execution_attested": False,
                "physical_action_issue_authorized": False,
            }
        else:
            if any(v is None for v in (
                args.restored, args.restore_id, args.source_pins_json,
            )):
                raise D11HandoffHold("complete inert fork/pins args required")
            result = prepare_d11_inert_handoff(
                args.evidence_dir, args.generation, args.restored,
                args.source_pins_json, restore_id=args.restore_id, **options,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        print(f"D11_PRE_WORLD_HOLD={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
