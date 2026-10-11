"""RSEE Golden Run read-only host admission: no model, Minecraft, or sockets.

Checks the exact independently qualified #583 bytes and source-only host
requirements. A PASS never implies a new Golden Run permit or live proof.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

from experiments.standard_env.golden_admission import verify_qualified_world
from experiments.standard_env.preflight import PROFILE, REPO_ROOT, verify_local
from experiments.standard_env.world_binding import (
    JAR_SHA256,
    WorldBindingRejected,
)

LLAMA_SERVER_SHA256 = "ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536"
HEAD_RE = re.compile(r"[a-f0-9]{40}\Z")
PORTS = (1234, 25565)


class HostGateRejected(ValueError):
    """Read-only qualification failed; execution is never authorized."""


def _git_head(repo: Path) -> str:
    # Only local git read commands; never fetch, checkout, reset or modify.
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False, timeout=5,
    )
    if result.returncode != 0:
        raise HostGateRejected("worktree HEAD not available")
    return result.stdout.strip()


def _git_dirty(repo: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--"],
        capture_output=True, check=False, timeout=5,
    )
    if result.returncode not in (0, 1):
        raise HostGateRejected("worktree state not readable")
    return result.returncode != 0


def _port_listeners() -> set[int]:
    """Observe Linux TCP LISTEN entries without claiming exclusive control.

    No socket connection, bind, network request or other World/model I/O.
    """
    listeners: set[int] = set()
    examined = 0
    for name in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            raw = Path(name).read_text(encoding="ascii")
        except OSError as exc:
            raise HostGateRejected("Linux TCP listener state unavailable") from exc
        examined += 1
        for line in raw.splitlines()[1:]:
            fields = line.split()
            if len(fields) < 4:
                raise HostGateRejected("Linux TCP table malformed")
            # 0A is TCP_LISTEN; local_address contains IPv4 or IPv6 hex.
            if fields[3] == "0A":
                try:
                    listeners.add(int(fields[1].rsplit(":", 1)[1], 16))
                except (ValueError, IndexError) as exc:
                    raise HostGateRejected("Linux TCP listener parsing failed") from exc
    if examined != 2:
        raise HostGateRejected("both Linux TCP tables are required")
    return listeners


def _observed_native_initial(path: Path) -> dict[str, Any]:
    """Read exactly the #583 pinned sidecar; no inferred yaw or weather."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise HostGateRejected("native observation sidecar unavailable")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        start = record["initial_spawn"]
        probe = record["initial_probe"]
        state = record["native_stopped_state"]
        saved = state["stored_player"]
        saved_world = state["stored_world"]
        position = probe["snapshot"]["position"]
        p = [position[key] for key in ("x", "y", "z")]
        stored = saved["position"]
        if (
            record["schema"] != "RSEE_BOOTSTRAP_NATIVE_INITIAL_V1"
            or start["kind"] != "spawn"
            or probe["kind"] != "probe"
            or start["session_id"] != probe["session_id"]
            or type(start["seq"]) is not int or start["seq"] != 1
            or type(probe["seq"]) is not int or probe["seq"] != 2
            or probe["request_id"] != "rsee-bootstrap:initial:001"
            or p != [-6.5, -60.0, 10.5]
            or stored != p
            or probe["snapshot"]["health"] != 20
            or probe["snapshot"]["food"] != 20
            or saved["health"] != 20
            or saved["food"] != 20
            or saved["rotation_yaw_pitch"] != [0, 0]
            or probe["snapshot"]["inventory"] != []
            or saved["inventory"] != []
            or saved_world["day_time"] != 18000
            or saved_world["raining"] != 0
            or saved_world["thundering"] != 0
            or any(
                saved_world["full_gamerules"].get(key) != "false"
                for key in ("doMobSpawning", "doDaylightCycle", "doWeatherCycle")
            )
            or record["java_clean_exit_observed"] is not True
            or record["bridge_clean_exit_observed"] is not True
        ):
            raise HostGateRejected("qualified #583 native values have drifted")
    except (KeyError, TypeError, IndexError, ValueError, UnicodeError, OSError) as exc:
        raise HostGateRejected("native initial observation cannot be reinterpreted") from exc
    return {
        "native_observation_source": "PINNED_583_SIDECAR_NOT_NEW_LIVE_OBSERVATION",
        "session_id": probe["session_id"],
        "spawn_seq": start["seq"],
        "probe_seq": probe["seq"],
        "player_position": p,
        "stopped_yaw_pitch": saved["rotation_yaw_pitch"],
        "stopped_time": saved_world["day_time"],
        "native_complete_saved_state_checked": True,
    }


def _new_destination(path: Path) -> bool:
    if path.is_symlink() or path.exists():
        return False
    if path.parent.is_symlink() or not path.parent.is_dir():
        return False
    return stat.S_ISDIR(path.parent.lstat().st_mode)


def audit(
    *,
    expected_head: str,
    output_dir: Path,
    jar: Path,
    snapshot: Path,
    manifest: Path,
    initial_evidence: Path,
    gguf: Path,
    llama_server: Path,
    node_runtime_root: Path | None = None,
    repo: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Fail closed; no launch, output folder creation, or mutation of inputs."""
    if HEAD_RE.fullmatch(expected_head) is None:
        raise HostGateRejected("exact 40-digit git HEAD required")
    errors: list[str] = []
    head = _git_head(repo)
    if head != expected_head:
        errors.append("EXACT_WORKTREE_HEAD_MISMATCH")
    if _git_dirty(repo):
        errors.append("WORKTREE_TRACKED_DIFF_UNCOMMITTED")
    if not _new_destination(output_dir):
        errors.append("EVIDENCE_DESTINATION_NOT_FRESH")
    if os.environ.get("NODE_OPTIONS"):
        errors.append("NODE_OPTIONS_OVERRIDE_PRESENT")
    if node_runtime_root is None:
        errors.append("EXPLICIT_SHARED_NODE_RUNTIME_REQUIRED")

    preflight = verify_local(
        PROFILE,
        model=str(gguf),
        llama_server=str(llama_server),
        llama_sha256=LLAMA_SERVER_SHA256,
        minecraft_jar=str(jar),
        minecraft_sha256=JAR_SHA256,
        mineflayer_root=repo / "adapters" / "mineflayer",
        verify_product=True,
        node_runtime_root=node_runtime_root,
    )
    if preflight["classification"] != "RSEE_LOCAL_FILES_VERIFIED_NOT_PHYSICALLY_QUALIFIED":
        errors.append("HOST_ARTIFACT_OR_DEPENDENCY_MISMATCH")
    errors.extend(preflight["errors"])
    # Historical #580 messages claiming World is unbound are NOT used as
    # contemporary #584 Golden admission; the independently pinned snapshot is.
    if preflight.get("product_profile_audit", {}).get("gaps"):
        errors.append("PRODUCT_STATIC_PROFILE_GAPS")

    world_info: dict[str, Any] = {}
    try:
        binding = verify_qualified_world(jar, snapshot, manifest, initial_evidence)
        if len(binding.files) != 26:
            raise HostGateRejected("qualified World file count differs from audit")
        world_info = {
            "bootstrap_qualified_manifest": binding.manifest_sha256,
            "initial_native_sha256": binding.initial_evidence_sha256,
            "world_file_count": len(binding.files),
            **_observed_native_initial(initial_evidence),
        }
    except (WorldBindingRejected, HostGateRejected, OSError, TypeError) as exc:
        errors.append("EXACT_583_NATIVE_WORLD_IDENTITY_UNCONFIRMED")
        world_info["failure_type"] = type(exc).__name__
    ports = _port_listeners()
    busy = sorted(port for port in PORTS if port in ports)
    if busy:
        errors.append("EXPECTED_MODEL_OR_WORLD_PORT_HAS_LISTENER")

    return {
        "classification": (
            "RSEE_GOLDEN_HOST_OFFLINE_BLOCKED" if errors
            else "RSEE_GOLDEN_HOST_FILES_READY_NOT_AUTHORIZED"
        ),
        "errors": sorted(set(errors)),
        "expected_head": expected_head,
        "observed_head": head,
        "llama_server_sha256": LLAMA_SERVER_SHA256,
        "jar_sha256_expected": JAR_SHA256,
        "preflight_classification": preflight["classification"],
        "product_profile_classification": preflight.get("product_profile_audit", {}).get("classification"),
        "world": world_info,
        "port_listener_snapshot": {
            "ports": list(PORTS),
            "observed_listeners": busy,
            "exclusive_port_ownership_qualified": False,
        },
        "output_dir_absent": _new_destination(output_dir),
        "node_runtime_root": str(node_runtime_root) if node_runtime_root else None,
        "python_runtime_interpreter": preflight.get("python_interpreter"),
        "python_runtime_prefix": preflight.get("python_runtime_prefix"),
        "runtime_props_slots_qualified": False,
        "thinking_off_execution_qualified": False,
        "gpu_execution_qualified": False,
        "structured_generation_qualified": False,
        "physical_execution_authorized": False,
        "golden_run": "NOT_RUN",
        "llm_post": 0,
        "new_world_launch": 0,
        "side_effects": "NO_MODEL_MINECRAFT_OR_SOCKET_LAUNCH",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--new-output-dir", type=Path, required=True)
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--initial-evidence", type=Path, required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--llama-server", type=Path, required=True)
    parser.add_argument("--node-runtime-root", type=Path, required=True,
                        help="absolute physical external npm root with exact source manifests")
    args = parser.parse_args(argv)
    try:
        result = audit(
            expected_head=args.expected_head,
            output_dir=args.new_output_dir,
            jar=args.jar,
            snapshot=args.snapshot,
            manifest=args.manifest,
            initial_evidence=args.initial_evidence,
            gguf=args.gguf,
            llama_server=args.llama_server,
            node_runtime_root=args.node_runtime_root,
        )
    except (OSError, TypeError, ValueError, subprocess.SubprocessError) as exc:
        result = {
            "classification": "RSEE_GOLDEN_HOST_OFFLINE_BLOCKED",
            "errors": [type(exc).__name__],
            "physical_execution_authorized": False,
            "golden_run": "NOT_RUN",
            "llm_post": 0,
            "new_world_launch": 0,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["classification"] == "RSEE_GOLDEN_HOST_FILES_READY_NOT_AUTHORIZED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
