"""D10 one-shot seal of a STOPPED original D9 World+Native+Gemma source.

Run after the original owned Paper/Native runner exits, never concurrently.
The SHA256SUMS produced here inventories *all* immutable files other than
the existing 3 nested World dimension SHA256SUMS verified by Stage28.
Only a separate subsequent process is allowed to claim the audit passed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28c1_inert_restore_dev import inspect_stage28c_source


class D10SealHold(RuntimeError):
    """No immutable source inventory; never continue to restored Paper."""


@dataclass(frozen=True, slots=True)
class D10SealedInventory:
    source_manifest_sha256: str
    source_manifest_files: int
    generation_id: str
    committed_sha256: str
    world_id: str
    source_branch_id: str
    evidence_root: str
    independently_audited: bool = False
    physical_action_issue_authorized: bool = False


_NESTED_WORLD_MANIFESTS = (
    "world/SHA256SUMS",
    "paper-dimensions/world_nether/SHA256SUMS",
    "paper-dimensions/world_the_end/SHA256SUMS",
)


def _digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise D10SealHold("original source is absent or symlinked")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def seal_d10_stopped_original(
    evidence_root: Path, generation: Path, *,
    expected_world_id: str,
    expected_source_branch_id: str,
) -> D10SealedInventory:
    root = Path(evidence_root)
    generation = Path(generation)
    manifest = root / "SHA256SUMS"
    if (
        root.is_symlink() or not root.is_dir() or manifest.exists()
        or manifest.is_symlink() or generation.is_symlink()
        or not generation.is_dir() or generation.parent.name
        != "typed-world-self-generations"
        or generation.parent.parent.resolve() != root.resolve()
    ):
        raise D10SealHold("new unsealed original source and typed cut required")
    source = inspect_stage28c_source(
        generation, expected_world_id=expected_world_id,
        expected_source_branch_id=expected_source_branch_id,
        expected_generation_id=generation.name,
    )
    if tuple(c.self_id for c in verify_typed_generation(generation)) != ("A", "B"):
        raise D10SealHold("typed original A/B source cannot be sealed")
    report_file = root / "resident-presence-result.json"
    if report_file.is_symlink():
        raise D10SealHold("source report symlinked")
    try:
        report = json.loads(report_file.read_bytes())
    except (OSError, ValueError) as exc:
        raise D10SealHold("terminal D9 report missing") from exc
    if (
        report.get("classification")
        != "REAL_D9_SOURCE_A_B_TYPED_CUT_CAPTURED_INDEPENDENT_AUDIT_PENDING"
        or report.get("cleanup_uncertain")
        or report.get("d9_actual_model_post_count") != 1
        or report.get("d9_previous_l2_model_post_count") != 0
        or report.get("real_b_physical_action") is not False
        or report.get("real_b_physical_wal_outcome") is not False
        or type(report.get("steps")) is not list
        or len(report["steps"]) != 1
        or report["steps"][0].get("typed_world_self_generation")
        != str(generation)
        or report.get("world_uuid") != source.world_id
        or not all(
            (root / path).is_file() and not (root / path).is_symlink()
            for path in (
                "D9-A-question-only.json",
                "D9-B-original-bounded-L1.json",
                "d9-pre-inference-paper-resident-owned.log",
                "stage24g-model-preworld.json",
                "stage24g-systemone-http/systemone-request-body.bin",
                "stage24g-systemone-http/systemone-response-body.bin",
                "stage24g-systemone-http/systemone-http-evidence.json",
                "D10-original-native-A0.jsonl",
                "D10-original-native-A1.jsonl",
                "D10-original-native-B0.jsonl",
            )
        )
    ):
        raise D10SealHold("D9 model/Paper/native original source incomplete")
    nested = {
        (generation.relative_to(root) / name).as_posix()
        for name in _NESTED_WORLD_MANIFESTS
    }
    observed: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise D10SealHold("foreign symlink inside original source")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            if name not in nested:
                if name == "SHA256SUMS" or not re.fullmatch(
                    r"[A-Za-z0-9_.\-/]+", name
                ):
                    raise D10SealHold("untracked or unsafe source path")
                observed[name] = _digest(path)
        elif not path.is_dir():
            raise D10SealHold("unsupported original evidence filesystem node")
    if not nested.issubset({
        path.relative_to(root).as_posix()
        for path in root.rglob("SHA256SUMS")
    }) or len(observed) > 100000:
        raise D10SealHold("three Paper dimension inventories missing")
    if "resident-presence-result.json" not in observed:
        raise D10SealHold("source report not included in frozen manifest")
    serialized = "".join(
        f"{digest}  {name}\n" for name, digest in sorted(observed.items())
    ).encode("utf-8")
    # No rename/overwrite: a seal may only be created once for this source.
    try:
        with manifest.open("xb") as output:
            os.chmod(manifest, 0o600)
            output.write(serialized)
            output.flush()
            os.fsync(output.fileno())
    except OSError as exc:
        raise D10SealHold("cannot exclusively seal original source") from exc
    if manifest.read_bytes() != serialized:
        raise D10SealHold("source manifest readback differs")
    return D10SealedInventory(
        _digest(manifest), len(observed), generation.name,
        source.committed_sha256, source.world_id, source.source_branch_id,
        str(root.absolute()),
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--generation", type=Path, required=True)
    p.add_argument("--world-id", required=True)
    p.add_argument("--source-branch", required=True)
    args = p.parse_args()
    try:
        result = seal_d10_stopped_original(
            args.evidence_dir, args.generation,
            expected_world_id=args.world_id,
            expected_source_branch_id=args.source_branch,
        )
    except (D10SealHold, OSError, ValueError, RuntimeError) as exc:
        print(f"D10_SEAL_HOLD={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2
    from dataclasses import asdict
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
