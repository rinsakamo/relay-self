"""Read-only RSEE/profile compatibility audit of the frozen Self product owner.

This audit reads Python source and CLI controls only. It NEVER launches a
provider, Minecraft, Node, Java, HTTP, or World and never grants a live run.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from experiments.standard_env.preflight import PROFILE, PreflightError, read_profile

ROOT = Path(__file__).resolve().parents[2]
OWNER = ROOT / "adapters" / "mineflayer" / "self_owned_llama.py"
L2 = ROOT / "adapters" / "mineflayer" / "self_live_think.py"


def _source(path: Path) -> ast.AST:
    # Exact local worktree only. Source inspection is NOT an execution proof.
    if not path.is_file() or path.is_symlink():
        raise PreflightError("product source unavailable or symlinked")
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise PreflightError("product source is not readable Python") from exc


def _model_request_keys(tree: ast.AST) -> set[str]:
    found: list[set[str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        names = {
            k.value for k in node.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)
        }
        if {"model", "messages", "stream", "max_tokens"}.issubset(names):
            found.append(names)
    if len(found) != 1:
        raise PreflightError("cannot identify one canonical live L2 payload constructor")
    return found[0]


def _launch_flags(tree: ast.AST) -> set[str]:
    launches = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == "Popen" and node.args
                and isinstance(node.args[0], ast.List)):
            flags = {
                item.value for item in node.args[0].elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
            launches.append(flags)
    if len(launches) != 1 or "--host" not in launches[0]:
        raise PreflightError("cannot identify one canonical owned llama launch")
    return launches[0]


def audit_product(
    *,
    profile_path: Path = PROFILE,
    owner: Path = OWNER,
    l2: Path = L2,
    ctx: int | None = None,
    gpu_layers: int | None = None,
    model_port: int | None = None,
    gguf_sha256: str | None = None,
) -> dict[str, Any]:
    profile, digest = read_profile(profile_path)
    request_keys = _model_request_keys(_source(l2))
    flags = _launch_flags(_source(owner))
    llm = profile["llm"]
    gaps: list[str] = []

    if "reasoning_effort" not in request_keys:
        gaps.append("L2_REQUEST_REASONING_OFF_NOT_EXPLICIT")
    if "cache_prompt" not in request_keys:
        gaps.append("L2_REQUEST_CACHE_DISABLED_NOT_EXPLICIT")
    # L2 here is read-only free-text commentary; JSON schema is only mandatory
    # for structured-decision workloads, never inferred to be enabled here.
    if "--no-context-shift" not in flags:
        gaps.append("OWNED_LLAMA_CONTEXT_SHIFT_NOT_DISABLED")
    if ctx is not None and ctx != llm["context"]:
        gaps.append("CONTEXT_DIFFERS_FROM_STANDARD")
    if gpu_layers is not None and gpu_layers != llm["gpu_layers"]:
        gaps.append("GPU_OFFLOAD_DIFFERS_FROM_STANDARD")
    if model_port is not None and model_port != llm["port"]:
        gaps.append("LOOPBACK_PORT_DIFFERS_FROM_STANDARD")
    if gguf_sha256 is not None and gguf_sha256 != llm["model_sha256"]:
        gaps.append("GGUF_IDENTITY_DIFFERS_FROM_STANDARD")
    # Product wrapper also caps --gpu-layers at 99; this is an explicit
    # version-scoped fact, checked against AST rather than assumed from text.
    caps_99 = any(
        isinstance(node, ast.Compare)
        and any(isinstance(comp, ast.Constant) and comp.value == 99
                for comp in node.comparators)
        and isinstance(node.left, ast.Constant) and node.left.value == 0
        for node in ast.walk(_source(owner))
    )
    # The exact product AST uses "0 <= args.gpu_layers <= 99", so the value
    # 99 appears in the Compare comparators, with a first comparator on arg.
    if caps_99 and llm["gpu_layers"] > 99:
        gaps.append("OWNED_LLAMA_GPU_LAYER_CAP_BELOW_STANDARD")

    return {
        "classification": (
            "RSEE_PRODUCT_STATIC_GAPS" if gaps
            else "RSEE_PRODUCT_STATIC_COMPATIBLE_NOT_PHYSICALLY_QUALIFIED"
        ),
        "profile_sha256": digest,
        "profile_qualification": profile["qualification"],
        "gaps": gaps,
        "observed_l2_wire_fields": sorted(request_keys),
        "observed_launcher_flags": sorted(flags),
        "runtime_observation": False,
        "physical_execution_authorized": False,
        "science_calls": 0,
        "world_actions": 0,
    }


def print_audit(**options: Any) -> int:
    try:
        result = audit_product(**options)
    except (PreflightError, OSError, ValueError) as exc:
        result = {
            "classification": "RSEE_PRODUCT_AUDIT_INVALID",
            "reason": type(exc).__name__,
            "physical_execution_authorized": False,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["classification"] == (
        "RSEE_PRODUCT_STATIC_COMPATIBLE_NOT_PHYSICALLY_QUALIFIED"
    ) else 2
