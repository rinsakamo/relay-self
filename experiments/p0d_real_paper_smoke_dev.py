"""#860 P0-D real-Paper single-World tick/save smoke (explicitly authorized DEV).

This script does NOT launch any Self, perform an automated 60s checkpoint,
restore any cognition, or replay actions. It owns a brand-new, disposable
Paper 1.21.8 world only and checks the exact Paper main-thread tick ACK
before two clean save/stop cycles. It NEVER attaches to existing servers.

No EULA acceptance is inferred: the operator must pass --eula-accepted.
The supplied Paper jar and plugin jar must match explicit SHA256 values.
On failure retain the entire scratch directory and report HOLD.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from relay_self.owned_paper_world_dev import OwnedPaperWorld
from relay_self.paper_tick_witness_dev import PaperMainThreadTickReader


class RealPaperSmokeRefusal(RuntimeError):
    """Do not promote a partial/unowned/uncertain Paper World observation."""


# Official PaperMC Fill v3 1.21.8 stable build 60, as published by PaperMC.
# Do not silently run another Minecraft version or an unreviewed server binary.
PAPER_1218_60_SHA256 = (
    "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as data:
        while chunk := data.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def prepare_assets(
    *, paper_jar: Path, paper_sha256: str, plugin_jar: Path,
    plugin_sha256: str, scratch_parent: Path, accepted_eula: bool,
) -> tuple[Path, Path, Path]:
    """Fail before modifying any filesystem if terms or provenance are absent."""
    if accepted_eula is not True:
        raise RealPaperSmokeRefusal(
            "operator must explicitly accept Minecraft EULA via --eula-accepted"
        )
    root = Path(scratch_parent)
    if root.is_symlink() or not root.is_dir():
        raise RealPaperSmokeRefusal("existing non-symlink scratch parent required")
    result = []
    for source, digest in ((paper_jar, paper_sha256), (plugin_jar, plugin_sha256)):
        source = Path(source)
        if (
            source.is_symlink() or not source.is_file() or source.suffix != ".jar"
            or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
            or file_sha256(source) != digest
        ):
            raise RealPaperSmokeRefusal("jar source, format or SHA256 mismatch")
        result.append(source.resolve(strict=True))
    with zipfile.ZipFile(result[1]) as plugin:
        if "plugin.yml" not in plugin.namelist():
            raise RealPaperSmokeRefusal("Paper plugin jar has no plugin.yml")
        manifest = plugin.read("plugin.yml")
        if b"name: P0BRecorder" not in manifest:
            raise RealPaperSmokeRefusal("wrong Paper observer plugin")
        if (
            "io/github/rinsakamo/p0b/TickWitness.class" not in plugin.namelist()
            or "io/github/rinsakamo/p0b/Recorder.class" not in plugin.namelist()
        ):
            raise RealPaperSmokeRefusal("Paper tick witness plugin not compiled")
    with zipfile.ZipFile(result[0]) as jar:
        if "META-INF/MANIFEST.MF" not in jar.namelist():
            raise RealPaperSmokeRefusal("Paper server jar lacks manifest")
    return result[0], result[1], root.resolve(strict=True)


def _write_bytes_new(path: Path, data: bytes) -> None:
    with path.open("xb") as target:
        target.write(data)
        target.flush()
        os.fsync(target.fileno())


def _wait_log(
    process: subprocess.Popen[bytes], log_file: Path,
    *, markers: tuple[bytes, ...], timeout_s: float,
) -> bytes:
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        log = log_file.read_bytes()
        if process.poll() is not None:
            raise RealPaperSmokeRefusal("owned bootstrap Paper process exited unexpectedly")
        if all(marker in log for marker in markers):
            return log
        time.sleep(0.1)
    raise RealPaperSmokeRefusal("real Paper bootstrap plugin/ready markers timed out")


def _bootstrap_paper(
    *, world_root: Path, launch: tuple[str, ...], timeout_s: float,
) -> Path:
    """Freshly create only this disposable world; don't attach to any PID."""
    log_path = world_root / "evidence" / "bootstrap.log"
    with log_path.open("xb") as log:
        process = subprocess.Popen(
            launch, cwd=world_root, stdin=subprocess.PIPE,
            stdout=log, stderr=subprocess.STDOUT, shell=False,
        )
    _write_bytes_new(
        world_root / "evidence" / "bootstrap.pid",
        (str(process.pid) + "\n").encode(),
    )
    try:
        _wait_log(
            process, log_path, timeout_s=timeout_s,
            markers=(b"Done (", b"P0D_TICK_READY boot="),
        )
        if process.stdin is None:
            raise RealPaperSmokeRefusal("owned Paper bootstrap console missing")
        offset = len(log_path.read_bytes())
        process.stdin.write(b"save-all flush\n")
        process.stdin.flush()
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            if process.poll() is not None:
                raise RealPaperSmokeRefusal("bootstrap exited before flush completion")
            if b"Saved the game" in log_path.read_bytes()[offset:]:
                break
            time.sleep(0.1)
        else:
            raise RealPaperSmokeRefusal("bootstrap flush completion unobserved; HOLD")
        process.stdin.write(b"stop\n")
        process.stdin.flush()
        status = process.wait(timeout=timeout_s)
        raw = log_path.read_bytes()
        if (
            status != 0 or b"Saved the game" not in raw[offset:]
            or b"Stopping server" not in raw
        ):
            raise RealPaperSmokeRefusal("bootstrap Paper did not save and exit cleanly")
        return log_path
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise RealPaperSmokeRefusal(
            "uncertain bootstrap Paper process; inspect exact PID and logs"
        ) from exc
    finally:
        if process.poll() is not None and process.stdin is not None:
            process.stdin.close()


def _world_uuid(world_dir: Path) -> str:
    uid = world_dir / "uid.dat"
    if uid.is_symlink() or not uid.is_file():
        raise RealPaperSmokeRefusal("Paper World UUID uid.dat missing")
    data = uid.read_bytes()
    if len(data) != 16:
        raise RealPaperSmokeRefusal("Paper uid.dat must contain exactly 16 UUID bytes")
    return str(uuid.UUID(bytes=data))


def _world_manifest(server_dir: Path) -> dict[str, str]:
    """Evidence after clean exit, covering the present overworld/dimensions."""
    hashes: dict[str, str] = {}
    for name in ("world", "world_nether", "world_the_end"):
        root = server_dir / name
        if not root.exists():
            continue
        if root.is_symlink() or not root.is_dir():
            raise RealPaperSmokeRefusal("world dimension path is not an owned directory")
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise RealPaperSmokeRefusal("symlink within World dimension not allowed")
            if path.is_file():
                hashes[str(path.relative_to(server_dir))] = file_sha256(path)
                if len(hashes) > 100000:
                    raise RealPaperSmokeRefusal("unexpectedly huge smoke World manifest")
    if "world/level.dat" not in hashes or "world/uid.dat" not in hashes:
        raise RealPaperSmokeRefusal("World level.dat / uid.dat missing from evidence")
    return hashes


def _free_local_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


def run_real_paper_smoke(
    *, paper_jar: Path, paper_sha256: str,
    plugin_jar: Path, plugin_sha256: str,
    scratch_parent: Path, accepted_eula: bool,
    java: str = "java", timeout_s: float = 120.0,
    heap_mb: int = 1536,
) -> Path:
    """Return the audit JSON only after two independent real-source tick cuts."""
    if (
        type(timeout_s) not in (float, int) or not 20 <= timeout_s <= 180
        or type(heap_mb) is not int or not 512 <= heap_mb <= 8192
        or type(java) is not str or not java.strip()
    ):
        raise RealPaperSmokeRefusal("bounded Java/heap/timeout settings required")
    paper, plugin, scratch = prepare_assets(
        paper_jar=paper_jar, paper_sha256=paper_sha256,
        plugin_jar=plugin_jar, plugin_sha256=plugin_sha256,
        scratch_parent=scratch_parent, accepted_eula=accepted_eula,
    )
    if paper_sha256 != PAPER_1218_60_SHA256:
        raise RealPaperSmokeRefusal(
            "only pinned official Paper 1.21.8 stable build 60 may be launched"
        )
    root = Path(tempfile.mkdtemp(prefix="p0d-real-paper-only-", dir=scratch))
    os.chmod(root, 0o700)
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700)
    plugins = root / "plugins"
    plugins.mkdir(mode=0o700)
    import shutil

    shutil.copyfile(paper, root / "paper.jar")
    shutil.copyfile(plugin, plugins / "P0BRecorder.jar")
    _write_bytes_new(root / "eula.txt", b"eula=true\n")
    properties = (
        "level-name=world\n"
        "server-ip=127.0.0.1\n"
        f"server-port={_free_local_port()}\n"
        "online-mode=true\n"
        "enable-rcon=false\n"
        "enable-query=false\n"
        "view-distance=2\n"
        "simulation-distance=2\n"
        "max-players=1\n"
        "max-world-size=5000\n"
        "spawn-protection=0\n"
        "generate-structures=false\n"
    )
    _write_bytes_new(root / "server.properties", properties.encode())
    launch = (
        java, "-Xms512M", f"-Xmx{heap_mb}M",
        "-jar", str(root / "paper.jar"), "--nogui",
    )
    report_path = evidence / "real-paper-smoke-result.json"
    audit: dict[str, object] = {
        "schema": 1, "qualification": "HOLD",
        "paper_jar_sha256": paper_sha256,
        "plugin_jar_sha256": plugin_sha256,
        "real_minecraft_self_sessions": 0,
        "real_autosave_60s": False,
        "multi_self_crash_recovery": False,
        "replay": False,
        "run_dir": str(root),
        "launch": launch,
        "steps": [],
    }
    owner: OwnedPaperWorld | None = None
    try:
        bootstrap_log = _bootstrap_paper(
            world_root=root, launch=launch, timeout_s=timeout_s,
        )
        world_dir = root / "world"
        world_id = _world_uuid(world_dir)
        audit["world_uuid"] = world_id
        audit["bootstrap_log_sha256"] = file_sha256(bootstrap_log)
        holder: dict[str, OwnedPaperWorld] = {}
        witness = PaperMainThreadTickReader(
            spool_dir=root / "plugins" / "P0BRecorder" / "p0d-ticks",
            expected_world_uuid=world_id,
            read_owned_log=lambda session: holder["owner"].read_owned_log(session),
            timeout_seconds=min(15.0, timeout_s / 3),
        )
        owner = OwnedPaperWorld(
            server_dir=root, world_dir=world_dir,
            evidence_dir=evidence, command=launch,
            world_id=world_id, branch_id="p0d-live-tick-only",
            tick_readback=witness, timeout_seconds=timeout_s,
        )
        holder["owner"] = owner
        for cycle in range(2):
            session = owner.start_owned()
            saved = owner.stop_and_save()
            if saved.old_server_session_id != session:
                raise RealPaperSmokeRefusal("Paper save session mismatch")
            if not saved.tick_source_ref.startswith("paper-main-thread:p0d:"):
                raise RealPaperSmokeRefusal("Paper main-thread source not bound")
            manifest = _world_manifest(root)
            if _world_uuid(world_dir) != world_id:
                raise RealPaperSmokeRefusal("World UUID changed after Paper restart")
            snapshot = evidence / f"cycle-{cycle + 1}-world"
            snapshot.mkdir()
            for dimension in ("world", "world_nether", "world_the_end"):
                if (root / dimension).is_dir():
                    shutil.copytree(root / dimension, snapshot / dimension)
            if _world_manifest(snapshot) != manifest:
                raise RealPaperSmokeRefusal("saved World snapshot readback mismatch")
            step = {
                "cycle": cycle,
                "server_session": session,
                "paper_tick": saved.logical_tick,
                "paper_tick_source_ref": saved.tick_source_ref,
                "paper_log_path": saved.stopped_server_ref,
                "process_exit_code": saved.process_exit_code,
                "world_files_sha256": manifest,
                "world_snapshot": str(snapshot),
            }
            audit["steps"].append(step)
        steps = audit["steps"]
        if (
            steps[0]["server_session"] == steps[1]["server_session"]
            or steps[0]["paper_tick_source_ref"] == steps[1]["paper_tick_source_ref"]
        ):
            raise RealPaperSmokeRefusal("second Paper boot/tick receipt was reused")
        audit["qualification"] = "REAL_PAPER_SINGLE_WORLD_TICK_SAVE_SMOKE_DEV"
    except BaseException as exc:
        audit["reason"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        _write_bytes_new(
            report_path, (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode(),
        )
        print(f"P0D_REAL_PAPER_AUDIT={report_path}", file=sys.stderr, flush=True)
        if owner is not None and owner.owned_session_id is not None:
            print(
                "P0D_HOLD: owned Paper may still be running; inspect process "
                "and evidence before manually stopping it.",
                file=sys.stderr, flush=True,
            )
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--plugin-sha256", required=True)
    parser.add_argument("--scratch-parent", type=Path, required=True)
    parser.add_argument(
        "--eula-accepted", action="store_true",
        help="explicit operator confirmation for this isolated Minecraft server",
    )
    parser.add_argument("--java", default="java")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--heap-mb", type=int, default=1536)
    args = parser.parse_args()
    try:
        audit = run_real_paper_smoke(
            paper_jar=args.paper_jar, paper_sha256=args.paper_sha256,
            plugin_jar=args.plugin_jar, plugin_sha256=args.plugin_sha256,
            scratch_parent=args.scratch_parent,
            accepted_eula=args.eula_accepted, java=args.java,
            timeout_s=args.timeout_s, heap_mb=args.heap_mb,
        )
    except (RealPaperSmokeRefusal, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"P0D_REAL_PAPER_HOLD: {exc}", file=sys.stderr)
        return 1
    print(audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
