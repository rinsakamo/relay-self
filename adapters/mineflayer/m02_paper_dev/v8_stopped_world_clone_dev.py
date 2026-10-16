"""S-owned V8 disposable stopped-Paper World generator + 5-arm byte clone DEV.

DEV_ONLY: one controlled Paper 1.21.8 startup/STOP for a fixed terrain seed,
then copy its *stopped* full World bytes to five independent paths. No
Mineflayer, Action, Energy or Food run. R independently checks all actual
stored files. These staged bytes are not a qualified V8 science environment.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import socket
from pathlib import Path
from typing import Any

ARMS = ("BASE_ON", "SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")
SEEDS = tuple(range(62101, 62109))
PAPER_JAR_SHA256 = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
DEV_CONFIRM = "V8-DEV-ISOLATED-PAPER-STOPPED-CLONES-ONLY"
MAX_FILES = 1024
MAX_BYTES = 512 * 1024 * 1024
CLASS = "S_V8_DEV_STOPPED_PAPER_FIVE_CLONES_NOT_QUALIFIED"


class CloneDevRejected(ValueError):
    """Unsafe input, aliased World, invalid evidence or forbidden mode."""


def need(ok: bool, why: str) -> None:
    if not ok:
        raise CloneDevRejected(why)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        while block := src.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def safe_root(p: Path) -> Path:
    need(isinstance(p, Path) and p.is_absolute() and p.is_dir()
         and not p.is_symlink() and not any(x.is_symlink() for x in p.parents),
         "nonabsolute, missing or symlinked World root")
    return p.resolve(strict=True)


def world_index(root: Path) -> list[dict[str, Any]]:
    """Independent S producer bytes, *not* a replacement for R audit."""
    root = safe_root(root)
    out = []
    total = 0
    for p in sorted(root.rglob("*")):
        need(not p.is_symlink() and (p.is_dir() or p.is_file()),
             "symlink or special file in stopped World")
        if p.is_dir():
            continue
        need(len(out) < MAX_FILES, "World file cardinality too large")
        size = p.stat().st_size
        need(0 <= size <= 64 * 1024 * 1024, "World entry too large")
        total += size
        need(total <= MAX_BYTES, "World tree too large")
        out.append({"relative_path": p.relative_to(root).as_posix(),
                    "size": size, "sha256": sha(p)})
    present = {v["relative_path"] for v in out}
    need("level.dat" in present
         and any(p.startswith("region/") and p.endswith(".mca") for p in present),
         "no real stopped World level.dat and generated terrain")
    return out


def clone_stopped_world(
    source: Path, output: Path, *, seed: int, confirm: str,
    producer_stop_attested: bool = False,
) -> dict[str, Any]:
    """Exclusive, bounded complete copies; no source writes or source re-use."""
    need(type(seed) is int and seed in SEEDS, "seed outside fixed V8 candidate roster")
    need(confirm == DEV_CONFIRM, "DEV-only clone confirmation missing")
    original = safe_root(source)
    need(output.is_absolute() and not output.exists()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "must use a new empty absolute output root")
    target = output.resolve(strict=False)
    need(target != original and target not in original.parents
         and original not in target.parents,
         "source/output root alias or nested World")
    expected = world_index(original)
    # Any changed path, missing file, unrelated World bytes fails immediately.
    output.mkdir(mode=0o700)
    try:
        for arm in ARMS:
            cloned = output / arm
            shutil.copytree(original, cloned, symlinks=False)
            need(world_index(cloned) == expected,
                 "one of five stopped World copies has different bytes: " + arm)
        need(world_index(original) == expected,
             "source World bytes changed while cloning")
        receipt = {
            "classification": CLASS,
            "mode": "DEV_ONLY", "seed": seed, "arms": list(ARMS),
            "source_world_root": str(original),
            "clone_root": str(output),
            "source_stopped_world_index": expected,
            "source_file_count": len(expected),
            "all_five_stopped_copies_byte_identical_to_source": True,
            "paper_producer_stop_attested": producer_stop_attested,
            "new_java_starts_during_clone_copy": 0,
            "native_agent_spawns": 0, "native_action_outcomes": 0,
            "food_resources_installed": False,
            "true_world_tick_and_pose_parity_attested": False,
            "R_independent_readback_passed": False,
            "engineering_qualification": False,
            "science_grant": None, "v8_science_trials_credited": 0,
            "science_go": False, "production_go": False,
        }
        (output / "source-clone-producer.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return receipt
    except BaseException:
        # It is only this brand-new S DEV-owned output directory; never
        # touch source or evidence outside this newly created root.
        shutil.rmtree(output)
        raise


def _server_properties(seed: int) -> bytes:
    need(type(seed) is int and seed in SEEDS, "unsupported fixed DEV seed")
    return (
        "server-ip=127.0.0.1\n"
        "server-port=25565\n"
        "online-mode=false\n"
        "enforce-secure-profile=false\n"
        "gamemode=survival\n"
        "force-gamemode=true\n"
        "difficulty=hard\n"
        "level-type=minecraft:normal\n"
        "level-name=world\n"
        f"level-seed={seed}\n"
        "max-players=1\n"
        "simulation-distance=4\n"
        "view-distance=4\n"
        "generate-structures=false\n"
        "spawn-monsters=false\n"
        "spawn-animals=false\n"
        "spawn-npcs=false\n"
        "enable-rcon=false\n"
        "white-list=false\n"
        "spawn-protection=0\n"
        "motd=RelaySelf V8 disposable stopped World clone DEV\n"
    ).encode("ascii")


async def bootstrap_dev(
    paper_jar: Path, output: Path, *, seed: int, confirm: str,
) -> dict[str, Any]:
    """One new Paper Java DEV startup; never a QUAL/SCIENCE attempt."""
    from adapters.mineflayer.s31a_real_server_ci import (
        _ready_server, _shutdown_server,
    )

    need(confirm == DEV_CONFIRM and type(seed) is int and seed in SEEDS,
         "V8 DEV bootstrap authorization scope absent")
    need(paper_jar.is_absolute() and paper_jar.is_file()
         and not paper_jar.is_symlink() and sha(paper_jar) == PAPER_JAR_SHA256,
         "unverified official Paper 1.21.8 binary")
    need(output.is_absolute() and not output.exists()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "V8 DEV bootstrap requires fresh isolated absolute root")
    need(not (paper_jar in output.parents or output in paper_jar.parents),
         "unacceptable source/output nesting")
    with socket.socket() as sock:
        need(sock.connect_ex(("127.0.0.1", 25565)) != 0,
             "real Minecraft loopback port already occupied")
    output.mkdir(mode=0o700)
    server_root = output / "isolated-server"
    server_root.mkdir()
    jar = server_root / "paper-1.21.8.jar"
    shutil.copyfile(paper_jar, jar)
    (server_root / "eula.txt").write_text("eula=true\n", encoding="ascii")
    props = _server_properties(seed)
    (server_root / "server.properties").write_bytes(props)
    server = collector = None
    started = False
    pid: int | None = None
    try:
        server, collector, _ = await _ready_server(
            server_root, jar, output / "original-paper-console.log")
        started = True
        pid = server.pid
    finally:
        await _shutdown_server(server, collector)
    need(started and server is not None and server.returncode == 0,
         "not one successfully stopped official Paper process")
    with socket.socket() as sock:
        need(sock.connect_ex(("127.0.0.1", 25565)) != 0,
             "DEV Paper listener not released")
    # Check genuine generated terrain exists after graceful stop and is
    # separate from the never-started five-world clone-copy stage.
    saved = server_root / "world"
    files = world_index(saved)
    cloned = clone_stopped_world(
        saved, output / "clones", seed=seed,
        confirm=confirm, producer_stop_attested=True,
    )
    result = {
        "classification": "S_V8_DEV_PAPER_GENERATED_STOPPED_CLONES_R_PENDING",
        "mode": "DEV_ONLY", "paper_jar_sha256": sha(jar),
        "server_properties_sha256": hashlib.sha256(props).hexdigest(),
        "seed_requested": seed,
        "java_process_count": 1, "java_pid": pid,
        "java_exit": server.returncode, "native_mineflayer_sessions": 0,
        "paper_stop_after_terrain_generation": True,
        "localhost_port_released": True,
        "generated_source_world_file_count": len(files),
        "stopped_clone_producer": cloned["classification"],
        "stopped_clone_sha256_equal": True,
        "r_independent_source_verification": False,
        "new_qualification_grants": 0, "science_trials": 0,
        "science_go": False, "production_go": False,
    }
    (output / "s-v8-dev-paper-receipt.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path)
    p.add_argument("--paper-jar", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--confirm", required=True)
    a = p.parse_args()
    try:
        need((a.source is None) != (a.paper_jar is None),
             "select exactly one stopped source or real DEV Paper bootstrap")
        if a.paper_jar is not None:
            result = asyncio.run(bootstrap_dev(
                a.paper_jar, a.output, seed=a.seed, confirm=a.confirm,
            ))
        else:
            result = clone_stopped_world(
                a.source, a.output, seed=a.seed, confirm=a.confirm,
            )
        code = 0
    except (CloneDevRejected, OSError, ValueError) as exc:
        result = {
            "classification": "S_V8_DEV_WORLD_CLONE_REFUSED_OR_FAILED",
            "reason": f"{type(exc).__name__}: {exc}",
            "science_trials": 0, "science_go": False,
            "production_go": False,
        }
        code = 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
