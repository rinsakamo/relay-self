"""Read-only reuse of PINNED RSEE #588 World + external Node admission.

This is not a launcher, admission permission, a duplicate RSEE validator,
or a replacement for R/V independent source assessment. No Java/Node/LLM
processes, sockets, filesystem installation or World mutations occur here.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RSEE_HEAD = "34820f6bf391c77f325d7c29d3b779a33e3ca835"
# Git blob IDs verified on RSEE #588. Reuse ORIGINAL code from a pinned
# external checkout rather than copying a second World/Node validator into S.
SOURCE_BLOBS = {
    "experiments/__init__.py": "8218464f85b277ae732c70fe92eb3bfb57ce7aec",
    "experiments/standard_env/golden_admission.py": "d36c5c0f2c52848225e15cc9b827126517d91619",
    "experiments/standard_env/world_binding.py": "81b95e4588b40b5ce6ca4bddbad392f840cccee6",
    "experiments/standard_env/node_runtime.py": "76b20501c4b8d39baf1240a297b155905c8a197d",
    "adapters/mineflayer/bridge.mjs": "5f44a3a032a6b7da998f613f28681ae6fff61fac",
    "adapters/mineflayer/protocol.mjs": "db466eb4ce4b80f83e581f8e1f55b62cc8d31025",
    "adapters/mineflayer/bridge_hooks.mjs": "53e08e0434a0900fc81b036791a038caa196f27f",
    "adapters/mineflayer/package.json": "a09393edcd7aad83debad430820f828401c4173a",
    "adapters/mineflayer/package-lock.json": "8e4259d0d7523578e5f9262cf223a2af23c7758c",
}

B0_CONFIRM = "B0-RSEE-I-OWN-ONE-DISPOSABLE-WORLD"

# This subprocess imports RSEE owner code ONLY after exact-head/blob checking.
# -I prevents PYTHONPATH/site injection; -B prevents .pyc writes.
# It deliberately does not start a Minecraft/Node model or open sockets.
_RSEE_CHECK = """
import json
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from experiments.standard_env.golden_admission import verify_qualified_world
from experiments.standard_env.node_runtime import verify_node_runtime

root, jar, snapshot, manifest, initial, node = map(Path, sys.argv[1:7])
world = verify_qualified_world(jar, snapshot, manifest, initial)
npm = verify_node_runtime(node, root / "adapters/mineflayer")
print(json.dumps({
    "classification": "B0_RSEE_ORIGINAL_WORLD_AND_NODE_OFFLINE_READY",
    "jar_sha256": world.jar_sha256,
    "manifest_sha256": world.manifest_sha256,
    "initial_evidence_sha256": world.initial_evidence_sha256,
    "world_file_count": len(world.files),
    "node": npm,
    "physical_execution_authorized": False
}, sort_keys=True))
"""


class B0RSEERejected(ValueError):
    """Cannot bind exact pinned RSEE source, World or Node runtime."""


@dataclass(frozen=True, slots=True)
class B0RSEEInputs:
    checkout: Path
    jar: Path
    snapshot: Path
    manifest: Path
    initial_evidence: Path
    node_runtime_root: Path
    eula_accepted: bool = False


def _pinned_source(checkout: Path) -> None:
    if not checkout.is_absolute() or checkout.is_symlink() or not checkout.is_dir():
        raise B0RSEERejected("explicit real absolute RSEE checkout required")
    try:
        head = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=8,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise B0RSEERejected("cannot establish RSEE git HEAD") from exc
    if head.stdout.strip() != RSEE_HEAD:
        raise B0RSEERejected("RSEE checkout does not match pinned #588 HEAD")
    for relative, pinned in SOURCE_BLOBS.items():
        file = checkout / relative
        if (
            any(p.is_symlink() for p in (file, *file.parents) if p != Path("/"))
            or not file.is_file()
        ):
            raise B0RSEERejected("RSEE source file missing or symlinked")
        raw = file.read_bytes()
        if len(raw) > 1_000_000:
            raise B0RSEERejected("RSEE source size exceeded")
        blob = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw,
        ).hexdigest()
        if blob != pinned:
            raise B0RSEERejected("RSEE source code differs from exact pinned blob")
    # Namespace packages must not be overridden from unpinned RSEE source.
    if (checkout / "experiments/standard_env/__init__.py").exists():
        raise B0RSEERejected("unexpected RSEE package initializer")


def verify_b0_rsee(
    inputs: B0RSEEInputs, *, snapshot_copy: Path | None = None,
) -> dict:
    """Invoke the EXACT RSEE read-only checker once; fail closed on any error."""
    if not isinstance(inputs, B0RSEEInputs) or inputs.eula_accepted is not True:
        raise B0RSEERejected("RSEE inputs and separate EULA consent required")
    checkout = inputs.checkout
    _pinned_source(checkout)
    snapshot = snapshot_copy if snapshot_copy is not None else inputs.snapshot
    for path in (
        inputs.jar, snapshot, inputs.manifest,
        inputs.initial_evidence, inputs.node_runtime_root,
    ):
        if not isinstance(path, Path) or not path.is_absolute():
            raise B0RSEERejected("absolute RSEE artifact paths required")
    command = [
        sys.executable, "-I", "-B", "-c", _RSEE_CHECK,
        str(checkout), str(inputs.jar), str(snapshot),
        str(inputs.manifest), str(inputs.initial_evidence),
        str(inputs.node_runtime_root),
    ]
    try:
        child = subprocess.run(
            command, capture_output=True, check=False, timeout=70,
            text=True, encoding="utf-8",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise B0RSEERejected("RSEE read-only verifier failed") from exc
    if child.returncode != 0 or len(child.stdout) > 8192:
        raise B0RSEERejected("RSEE World/Node offline verification rejected")
    try:
        result = json.loads(child.stdout)
    except (ValueError, UnicodeError) as exc:
        raise B0RSEERejected("RSEE read-only reply not valid JSON") from exc
    if (
        not isinstance(result, dict)
        or result.get("classification")
        != "B0_RSEE_ORIGINAL_WORLD_AND_NODE_OFFLINE_READY"
        or result.get("physical_execution_authorized") is not False
        or result.get("world_file_count") != 26
        or result.get("jar_sha256")
        != "2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7"
        or result.get("manifest_sha256")
        != "5b1876db6a97fc8b9c4331938ca47727037c5626a241213d871b2073665996f8"
        or result.get("initial_evidence_sha256")
        != "7c974390d1879967ef5b5ce3b37d59a9628974c5f3e2a2dfefcf5e1e7701648b"
        or not isinstance(result.get("node"), dict)
        or result["node"].get("mineflayer_installed_version") != "4.39.0"
        or result["node"].get("node_runtime_root")
        != str(inputs.node_runtime_root)
    ):
        raise B0RSEERejected("RSEE identities/Node results are not qualified")
    _pinned_source(checkout)  # no silent source mutation during checking
    return result
