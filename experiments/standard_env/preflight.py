"""RSEE 1.0 offline-only local laboratory preflight.

This module NEVER launches an LLM, GPU process, Java server, Node bridge or World.
It does not grant execution permission or validate post-launch World/model identity.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PROFILE = Path(__file__).with_name("profile.v1.json")
REPO_ROOT = Path(__file__).resolve().parents[2]
SHA256 = re.compile(r"[a-f0-9]{64}\Z")


class PreflightError(ValueError):
    """A candidate laboratory profile or operator input is invalid."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _require(value: bool, message: str) -> None:
    if not value:
        raise PreflightError(message)


def read_profile(path: Path = PROFILE) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        profile = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError("invalid profile JSON") from exc
    _require(isinstance(profile, dict), "profile must be an object")
    _require(
        set(profile) == {
            "schema_version", "qualification", "host", "llm",
            "minecraft", "resource_key", "not_inferred"
        },
        "profile has missing or unknown root fields",
    )
    _require(type(profile["schema_version"]) is int and profile["schema_version"] == 1,
             "unsupported profile version")
    _require(profile["qualification"] == "CANDIDATE_NOT_PHYSICALLY_QUALIFIED",
             "profile cannot self-declare physical qualification")
    h, llm_config, m = profile["host"], profile["llm"], profile["minecraft"]
    _require(isinstance(h, dict) and isinstance(llm_config, dict) and isinstance(m, dict),
             "host/llm/minecraft must be objects")
    _require(
        h == {
            "platform": "linux-wsl2", "python": "3.12",
            "node_major": 22, "java_major": 21,
            "python_imports": ["pytest", "httpx"],
        },
        "unexpected host/runtime condition",
    )
    _require(
        set(llm_config) == {
            "engine", "model_family", "model_sha256", "host", "port",
            "context", "slots", "gpu_layers", "context_shift", "cache_prompt",
            "reasoning_effort", "structured_output"
        },
        "unexpected LLM profile fields",
    )
    _require(
        llm_config["engine"] == "llama.cpp"
        and llm_config["model_family"] == "Gemma-4-12B-it-Q4_K_M"
        and llm_config["model_sha256"]
        == "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
        and llm_config["host"] == "127.0.0.1"
        and type(llm_config["port"]) is int and llm_config["port"] == 1234
        and type(llm_config["context"]) is int and llm_config["context"] == 8192
        and type(llm_config["slots"]) is int and llm_config["slots"] == 1
        and type(llm_config["gpu_layers"]) is int and llm_config["gpu_layers"] == 999
        and llm_config["context_shift"] is False
        and llm_config["cache_prompt"] is False
        and llm_config["reasoning_effort"] == "none"
        and llm_config["structured_output"] == {"type": "json_schema", "strict": True},
        "unexpected LLM condition; change requires a separately versioned profile",
    )
    _require(
        m == {
            "mode": "disposable_only", "version": "1.21.8",
            "host": "127.0.0.1", "port": 25565,
            "mineflayer": "4.39.0", "initial_world": "UNBOUND_PER_RUN",
        },
        "unexpected Minecraft condition",
    )
    _require(profile["resource_key"] == "llama-cpp:local-gpu",
             "unexpected GPU resource key")
    _require(profile["not_inferred"] == [
        "llama_binary_sha256", "minecraft_server_jar_sha256",
        "world_seed_and_snapshot", "chat_template_and_tokenizer",
        "request_model_alias", "prompt_schema_and_sampling",
        "physical_execution_authorization",
    ], "unqualified physical fields must remain explicit")
    return profile, hashlib.sha256(raw).hexdigest()


def _sha_arg(value: str | None) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _version_output(executable: str, arg: str) -> str:
    if shutil.which(executable) is None:
        raise PreflightError(f"{executable} executable not found")
    try:
        completed = subprocess.run(
            [executable, arg], capture_output=True, text=True,
            timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError(f"{executable} version probe failed") from exc
    if completed.returncode != 0:
        raise PreflightError(f"{executable} version probe exited nonzero")
    return (completed.stdout + completed.stderr).strip()


def _check_tools(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    host = profile["host"]
    if platform.system() != "Linux":
        errors.append("Linux/WSL2 host required")
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12):
        errors.append("CPython 3.12 required")
    for module in host["python_imports"]:
        try:
            importlib.import_module(module)
        except Exception:
            errors.append(f"Python import failed: {module}")
    try:
        node = _version_output("node", "--version")
        match = re.match(r"v(\d+)\.", node)
        if not match or int(match.group(1)) < host["node_major"]:
            errors.append("Node >=22 required")
    except PreflightError as exc:
        errors.append(str(exc))
    try:
        java = _version_output("java", "-version")
        match = re.search(r'version "(\d+)', java)
        if not match or int(match.group(1)) != host["java_major"]:
            errors.append("Java 21 required")
    except PreflightError as exc:
        errors.append(str(exc))
    return errors


def _check_mineflayer(root: Path, expected_version: str) -> list[str]:
    errors: list[str] = []
    lock = root / "package-lock.json"
    installed = root / "node_modules" / "mineflayer" / "package.json"
    for path, label in ((lock, "lockfile"), (installed, "installed mineflayer")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            version = (
                obj["packages"][""]["dependencies"]["mineflayer"]
                if label == "lockfile"
                else obj["version"]
            )
            if version != expected_version:
                errors.append(f"{label} version differs from {expected_version}")
        except (OSError, ValueError, KeyError, TypeError):
            errors.append(f"{label} unavailable or invalid")
    return errors


def _check_file(path_text: str | None, expected: str | None, label: str,
                *, executable: bool = False) -> list[str]:
    if not path_text or not _sha_arg(expected):
        return [f"{label}: exact local path and expected SHA256 required"]
    path = Path(path_text).expanduser()
    if not path.is_file():
        return [f"{label}: regular local file not found"]
    if executable and not (path.stat().st_mode & 0o111):
        return [f"{label}: not executable"]
    try:
        actual = _sha256_file(path)
    except OSError:
        return [f"{label}: could not read file"]
    return [] if actual == expected else [f"{label}: SHA256 mismatch"]


def plan(profile_path: Path = PROFILE) -> dict[str, Any]:
    profile, digest = read_profile(profile_path)
    return {
        "classification": "RSEE_PLAN_ONLY",
        "profile_sha256": digest,
        "profile": profile,
        "not_verified": [
            "local dependencies", "llama-server and GGUF bytes",
            "Minecraft jar and initial World", "live model identity/slots",
            "GPU/VRAM and model/runtime behavior", "execution authorization",
        ],
        "side_effects": "NONE",
    }


def verify_local(
    profile_path: Path, *, model: str | None, llama_server: str | None,
    llama_sha256: str | None, minecraft_jar: str | None,
    minecraft_sha256: str | None, mineflayer_root: Path,
) -> dict[str, Any]:
    profile, digest = read_profile(profile_path)
    errors = _check_tools(profile)
    errors.extend(_check_mineflayer(mineflayer_root, profile["minecraft"]["mineflayer"]))
    errors.extend(_check_file(model, profile["llm"]["model_sha256"], "GGUF"))
    errors.extend(_check_file(llama_server, llama_sha256, "llama-server", executable=True))
    errors.extend(_check_file(minecraft_jar, minecraft_sha256, "Minecraft server jar"))
    return {
        "classification": (
            "RSEE_LOCAL_PREFLIGHT_BLOCKED"
            if errors else "RSEE_LOCAL_FILES_VERIFIED_NOT_PHYSICALLY_QUALIFIED"
        ),
        "profile_sha256": digest,
        "errors": errors,
        "physical_execution_authorized": False,
        "live_world_and_model_verified": False,
        "side_effects": "NO_LLM_OR_WORLD_LAUNCH",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=PROFILE)
    parser.add_argument("--verify-local", action="store_true",
                        help="Opt-in read-only tools/import/checksum verification; never launch")
    parser.add_argument("--model")
    parser.add_argument("--llama-server")
    parser.add_argument("--llama-sha256")
    parser.add_argument("--minecraft-jar")
    parser.add_argument("--minecraft-sha256")
    parser.add_argument("--mineflayer-root", type=Path,
                        default=REPO_ROOT / "adapters" / "mineflayer")
    args = parser.parse_args(argv)
    try:
        if args.verify_local:
            result = verify_local(
                args.profile, model=args.model, llama_server=args.llama_server,
                llama_sha256=args.llama_sha256, minecraft_jar=args.minecraft_jar,
                minecraft_sha256=args.minecraft_sha256,
                mineflayer_root=args.mineflayer_root,
            )
        else:
            if any((args.model, args.llama_server, args.llama_sha256,
                    args.minecraft_jar, args.minecraft_sha256)):
                raise PreflightError("artifact flags require --verify-local")
            result = plan(args.profile)
    except (PreflightError, OSError) as exc:
        result = {"classification": "RSEE_PROFILE_INVALID", "error": str(exc)}
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["classification"] in {
        "RSEE_PLAN_ONLY", "RSEE_LOCAL_FILES_VERIFIED_NOT_PHYSICALLY_QUALIFIED"
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
