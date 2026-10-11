"""Self-owned, single-use llama.cpp backend wrapper for the existing real demo.

One explicit *operator* CLI owns only the llama-server subprocess it creates,
and then delegates the exact original S49 Minecraft experiment to self_demo.
Never treats process termination as backend STOP ACK, VRAM release, or proof of
model-generated gameplay. No general shell, arbitrary environment or port use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from adapters.mineflayer.self_demo import CONFIRM

REPORT_NAME = "owned_llama_receipt.json"
LOG_NAME = "owned_llama_server.log"


class OwnedModelRejected(ValueError):
    """A model process cannot be safely owned or source-qualified."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def _regular(path: Path, *, executable: bool = False) -> Path:
    if not isinstance(path, Path) or path.is_symlink():
        raise OwnedModelRejected("symlinks are not accepted as owned model artifacts")
    item = path.resolve(strict=True)
    mode = item.stat().st_mode
    if not stat.S_ISREG(mode) or (executable and not os.access(item, os.X_OK)):
        raise OwnedModelRejected("expected a regular local executable/file")
    return item


def _preflight_mineflayer_dependencies() -> dict[str, str]:
    """Verify actual bridge-context Node imports, BEFORE llama/GPU/Java launch.

    Node's package resolution follows module realpaths. Merely finding a
    mineflayer/package.json via a symlink does not qualify its transitive
    minecraft-protocol dependency. No bot or Minecraft connection is made.
    """
    folder = Path(__file__).resolve().parent
    bridge = folder / "bridge.mjs"
    modules = folder / "node_modules"
    if (not bridge.is_file() or bridge.is_symlink()
            or not modules.is_dir() or modules.is_symlink()):
        raise OwnedModelRejected(
            "actual worktree bridge and physical node_modules required; "
            "run npm ci --prefix adapters/mineflayer in this checkout"
        )
    # Execute actual module imports from this bridge's own URL and the
    # resolved Mineflayer package realpath; no shell or network operations.
    bridge_literal = json.dumps(str(bridge), ensure_ascii=True)
    probe = (
        "const {createRequire}=require('node:module');"
        f"const root=createRequire({bridge_literal});"
        "const mf=root('mineflayer');"
        "const pkg=root('mineflayer/package.json');"
        "if(pkg.version!=='4.39.0'||typeof mf.createBot!=='function')"
        "{process.exit(21)};"
        "const internal=createRequire(root.resolve('mineflayer'));"
        "const protocol=internal('minecraft-protocol');"
        "if(!protocol||typeof protocol!=='object'){process.exit(22)};"
        "process.stdout.write(JSON.stringify({"
        "mineflayer:pkg.version,"
        "mineflayer_entry:require('node:fs').realpathSync(root.resolve('mineflayer')),"
        "minecraft_protocol_entry:"
        "require('node:fs').realpathSync(internal.resolve('minecraft-protocol'))"
        "}));"
    )
    try:
        done = subprocess.run(
            ["node", "-e", probe], cwd=folder, check=False,
            capture_output=True, text=True, timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OwnedModelRejected(
            "Mineflayer bridge-relative module import preflight unavailable"
        ) from exc
    if done.returncode != 0 or len(done.stdout) > 4096:
        raise OwnedModelRejected(
            "Mineflayer/ minecraft-protocol import failed from actual "
            "bridge path; npm ci into this worktree, do not symlink node_modules"
        )
    try:
        value = json.loads(done.stdout)
        if (value["mineflayer"] != "4.39.0"
                or not Path(value["mineflayer_entry"]).is_file()
                or not Path(value["minecraft_protocol_entry"]).is_file()):
            raise ValueError("inconsistent resolved module paths")
    except (ValueError, KeyError, TypeError) as exc:
        raise OwnedModelRejected(
            "Mineflayer bridge-relative dependency evidence invalid"
        ) from exc
    return value


def _free_loopback(port: int) -> None:
    # A preflight, not a retained reservation: the process is checked as alive
    # after model/model-ID probing. Never connect to a pre-existing service.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise OwnedModelRejected("model port is already occupied") from exc


def _ready(port: int, alias: str) -> bool:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(
            f"http://127.0.0.1:{port}/health", timeout=.4,
        ) as response:
            if response.status != 200:
                return False
            if len(response.read(2049)) > 2048:
                return False
        with opener.open(
            f"http://127.0.0.1:{port}/v1/models", timeout=.4,
        ) as response:
            if response.status != 200:
                return False
            blob = response.read(8193)
            if len(blob) > 8192:
                return False
            models = json.loads(blob)
            if not isinstance(models, dict) or not isinstance(models.get("data"), list):
                return False
            return any(
                isinstance(model, dict) and model.get("id") == alias
                for model in models["data"]
            )
    except (OSError, ValueError, UnicodeError, urllib.error.URLError):
        return False


def _stop_only_owned(proc: subprocess.Popen, *, grace_s: float = 5.0) -> dict[str, object]:
    """Signal only freshly spawned process group. No killall/pkill/system services."""
    before = proc.poll()
    if before is not None:
        return {"child_exit": before, "sigterm_sent": False, "sigkill_sent": False}
    group = os.getpgid(proc.pid)
    if group != proc.pid:
        raise OwnedModelRejected("owned process-group identity no longer matches")
    os.killpg(group, signal.SIGTERM)
    try:
        proc.wait(timeout=grace_s)
        return {
            "child_exit": proc.returncode, "sigterm_sent": True,
            "sigkill_sent": False,
        }
    except subprocess.TimeoutExpired:
        # Only the same original process group. No surrounding processes.
        if proc.poll() is None and os.getpgid(proc.pid) == proc.pid:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=3)
        return {
            "child_exit": proc.returncode, "sigterm_sent": True,
            "sigkill_sent": True,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run original disposable Self demo with an exclusively owned llama.cpp server"
    )
    parser.add_argument("--run-disposable", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--llama-server", type=Path, required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--gguf-sha256", required=True)
    parser.add_argument("--model-alias", required=True)
    parser.add_argument("--model-port", type=int, required=True)
    parser.add_argument("--ctx-size", type=int, default=4352)
    parser.add_argument("--gpu-layers", type=int, default=0)
    parser.add_argument("--ready-timeout", type=float, default=90.0)
    parser.add_argument("--model-timeout", type=float, default=12.0)
    args = parser.parse_args(argv)

    # Strict preflight before any new process, logfile or model read.
    try:
        if not args.run_disposable or args.confirm != CONFIRM:
            raise OwnedModelRejected("explicit disposable-World consent required")
        if (args.output_dir.is_symlink() or not args.output_dir.is_dir()
                or any(args.output_dir.iterdir())):
            raise OwnedModelRejected("evidence folder must be new and empty")
        if (type(args.model_port) is not int or not 1024 <= args.model_port <= 65535
                or args.model_port == 25565):
            raise OwnedModelRejected("non-game localhost model port required")
        if (type(args.ctx_size) is not int or not 256 <= args.ctx_size <= 32768
                or type(args.gpu_layers) is not int or not 0 <= args.gpu_layers <= 99
                or not .1 <= args.model_timeout <= 120
                or not 1 <= args.ready_timeout <= 180):
            raise OwnedModelRejected("unbounded model resource configuration")
        if (not args.model_alias.isascii() or not args.model_alias
                or len(args.model_alias) > 80
                or not all(c.isalnum() or c in "_-." for c in args.model_alias)):
            raise OwnedModelRejected("invalid model alias")
        if (len(args.gguf_sha256) != 64
                or any(c not in "0123456789abcdef" for c in args.gguf_sha256)):
            raise OwnedModelRejected("explicit lowercase expected GGUF SHA256 required")
        if os.environ.get("NODE_OPTIONS"):
            raise OwnedModelRejected("NODE_OPTIONS shim is forbidden")
        if not __import__("shutil").which("java") or not __import__("shutil").which("node"):
            raise OwnedModelRejected("Java and Node missing")
        # Mandatory BEFORE expensive GGUF hash, model spawn and World startup.
        node_deps = _preflight_mineflayer_dependencies()
        binary = _regular(args.llama_server, executable=True)
        gguf = _regular(args.gguf)
        if gguf.suffix.lower() != ".gguf":
            raise OwnedModelRejected("local source must be an explicit GGUF")
        _free_loopback(args.model_port)
        model_digest = _sha256(gguf)
        if model_digest != args.gguf_sha256:
            raise OwnedModelRejected("GGUF content SHA256 does not match exact caller grant")
        binary_digest = _sha256(binary)
        # Recheck port after potential multi-GB SHA work.
        _free_loopback(args.model_port)
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({
            "status": "BLOCKED", "reason": type(exc).__name__,
            "model_process_launched": False, "minecraft_launched": False,
        }, sort_keys=True))
        return 2

    log = args.output_dir / LOG_NAME
    receipt = args.output_dir / REPORT_NAME
    state: dict[str, object] = {
        "schema": "SELF_OWNED_LLAMA_PROCESS_V1",
        "status": "UNKNOWN", "model_alias_claimed": args.model_alias,
        "model_port": args.model_port, "llama_server_sha256": binary_digest,
        "gguf_sha256_verified": model_digest,
        "gguf_filename": gguf.name,
        "ctx_size": args.ctx_size, "gpu_layers_requested": args.gpu_layers,
        "parallel_slots_requested": 1,
        "llm_generated_actions": 0, "learned_habits": 0,
        "stop_ack": False, "gpu_release_verified": False,
        "backend_model_identity_attested": False,
        "physical_minecraft_outcome_attested_by_wrapper": False,
        "node_bridge_dependency_preflight": node_deps,
        "model_process_launched": False, "minecraft_launch_attempted": False,
    }
    process: subprocess.Popen | None = None
    code = 1
    try:
        with log.open("x", encoding="utf-8") as stream:
            process = subprocess.Popen(
                [
                    str(binary), "--model", str(gguf), "--alias", args.model_alias,
                    "--host", "127.0.0.1", "--port", str(args.model_port),
                    "--parallel", "1", "--ctx-size", str(args.ctx_size),
                    "--n-gpu-layers", str(args.gpu_layers),
                ],
                stdin=subprocess.DEVNULL, stdout=stream,
                stderr=subprocess.STDOUT, close_fds=True,
                start_new_session=True,
                cwd=str(args.output_dir),
            )
            state["model_process_launched"] = True
            state["owned_pid"] = process.pid
            deadline = time.monotonic() + args.ready_timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    state["status"] = "MODEL_EARLY_EXIT"
                    break
                if _ready(args.model_port, args.model_alias) and process.poll() is None:
                    state["loopback_health_and_alias_checked"] = True
                    break
                time.sleep(.1)
            else:
                state["status"] = "MODEL_READINESS_TIMEOUT"
            if state.get("loopback_health_and_alias_checked"):
                state["minecraft_launch_attempted"] = True
                # Calls the EXISTING S49 product CLI in an owned child process.
                # No shell, replay, new Game Action authorizer or L2->Action route.
                env = dict(os.environ)
                env["PYTHONPATH"] = os.pathsep.join(
                    [str(Path(__file__).resolve().parents[2] / "src"),
                     str(Path(__file__).resolve().parents[2] / "tests"),
                     str(Path(__file__).resolve().parents[2])]
                )
                invoked = subprocess.run(
                    [
                        sys.executable, "-m", "adapters.mineflayer.self_demo",
                        "--run-disposable", "--confirm", CONFIRM,
                        "--output-dir", str(args.output_dir),
                        "--live-think", "--model-alias", args.model_alias,
                        "--model-port", str(args.model_port),
                        "--model-timeout", str(args.model_timeout),
                    ], check=False, env=env,
                )
                state["self_demo_exit"] = invoked.returncode
                code = 0 if invoked.returncode == 0 else 1
                state["status"] = (
                    "SELF_DEMO_RETURNED_SUCCESS_NOT_PHYSICAL_ATTESTATION"
                    if code == 0 else "SELF_DEMO_FAILED_OR_UNKNOWN"
                )
    except (OSError, RuntimeError, ValueError) as exc:
        state["status"] = "OWNED_MODEL_OR_DEMO_ERROR"
        state["error_type"] = type(exc).__name__
    finally:
        if process is not None:
            try:
                state.update(_stop_only_owned(process))
                state["owned_process_waited"] = True
            except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
                state["status"] = "OWNED_CLEANUP_UNCONFIRMED"
                state["cleanup_error"] = type(exc).__name__
                code = 1
        try:
            with receipt.open("x", encoding="utf-8") as stream:
                json.dump(state, stream, indent=2, sort_keys=True)
                stream.write("\n")
        except OSError:
            code = 1
        print(json.dumps({
            "status": state["status"], "model_process_launched": state["model_process_launched"],
            "minecraft_launch_attempted": state["minecraft_launch_attempted"],
            "owned_process_waited": state.get("owned_process_waited", False),
            "wrapper_exit": code,
        }, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
