"""I1 DEV-only original Mineflayer dependency preflight, before Paper/World.

The original Node bridge refuses symlinked worktree dependencies and missing
owner-guard oxygen backports BEFORE producing adapter_started. The historical
Python runtime preflight checked file symlinks but not a symlinked node_modules
ancestor; this checker deliberately mirrors the actual Node inspection.
No install/patch/copy, GPU task, Paper boot, Mineflayer bot or physical action.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path


class I1NativePreflightHold(RuntimeError):
    """I1 cannot start any World without the exact original Native sources."""


@dataclass(frozen=True, slots=True)
class I1NativePreflightReceipt:
    mineflayer_version: str
    entities_sha256: str
    node_inspector_verified: bool = True
    native_module_import_verified: bool = True
    no_symlink_ancestors: bool = True
    world_started: bool = False
    node_module_warning_code: str | None = None
    node_module_stderr_sha256: str = ""
    node_module_stderr_raw: str = ""


_NODE_OK = re.compile(
    r"STAGE24D_MINEFLAYER_OWNER_PATCH_OK original=4\.39\.0 "
    r"source_sha256=([0-9a-f]{64})\n?\Z"
)


# Only the exact, observed Node 22.x two-line DEP0040 diagnostic is
# qualified. Never pass arbitrary stderr, --no-deprecation, NODE_NO_WARNINGS,
# alternate error output or any additional warning/stack trace.
_NODE_PUNYCODE_DEP0040 = re.compile(
    r"\(node:[1-9][0-9]{0,9}\) \[DEP0040\] DeprecationWarning: "
    r"The `punycode` module is deprecated\. Please use a userland alternative instead\.\r?\n"
    r"\(Use `node --trace-deprecation \.\.\.` to show where the warning was created\)\r?\n?\Z"
)


def qualify_i1_node_module_stderr(stderr: str) -> str | None:
    """Classify exact bounded runtime diagnostic; never silence stderr.

    Return one known warning code or None for a genuinely empty stderr.
    Unknown diagnostics, duplicates, trace stacks, spoofed banners and
    downstream import errors are HOLD with their original bytes visible.
    """
    if type(stderr) is not str:
        raise I1NativePreflightHold("original Node stderr unavailable or malformed")
    if stderr == "":
        return None
    raw = stderr.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) <= 512 and _NODE_PUNYCODE_DEP0040.fullmatch(stderr):
        return "DEP0040"
    raise I1NativePreflightHold(
        "unqualified original Node module stderr sha256=" + digest
        + " raw=" + repr(stderr[:1024])
    )


def require_i1_native_preflight(
    *, node: str, bridge_dir: Path | None = None,
) -> I1NativePreflightReceipt:
    """Read-only, fail-closed path, version, patch and exact Node-source check.

    Must be called BEFORE execution-copy creation and before Paper.start_owned.
    The bridge location is the actual repository module path, never NODE_PATH.
    A bridge_dir parameter is only for offline adversarial filesystem tests.
    """
    if type(node) is not str or not node.strip():
        raise I1NativePreflightHold("explicit original Node runtime required")
    root = (
        Path(__file__).resolve().parents[2] / "adapters" / "mineflayer"
        if bridge_dir is None else Path(bridge_dir)
    ).absolute()
    expected = (
        (root, True),
        (root / "node_modules", True),
        (root / "node_modules" / "mineflayer", True),
        (root / "node_modules" / "mineflayer" / "lib", True),
        (root / "node_modules" / "mineflayer" / "lib" / "plugins", True),
        (root / "oxygen_owner_patch.mjs", False),
        (root / "node_modules" / "mineflayer" / "package.json", False),
        (root / "node_modules" / "mineflayer" / "lib" / "plugins" / "entities.js", False),
    )
    for path, directory in expected:
        try:
            kind = path.lstat().st_mode
            if (
                stat.S_ISLNK(kind)
                or (not stat.S_ISDIR(kind) if directory else not stat.S_ISREG(kind))
                or path.resolve(strict=True) != path
            ):
                raise I1NativePreflightHold(
                    "worktree-local Mineflayer dependencies must not use symlinks: "
                    + str(path)
                )
        except OSError as exc:
            raise I1NativePreflightHold(
                "worktree-local Mineflayer dependency missing or inaccessible: "
                + str(path)
            ) from exc
    manifest = root / "node_modules" / "mineflayer" / "package.json"
    source = root / "node_modules" / "mineflayer" / "lib" / "plugins" / "entities.js"
    try:
        package = json.loads(manifest.read_bytes())
        if (type(package) is not dict
                or package.get("version") != "4.39.0"):
            raise I1NativePreflightHold(
                "only exact worktree-local Mineflayer 4.39.0 may start I1"
            )
        source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    except (OSError, UnicodeError, ValueError) as exc:
        raise I1NativePreflightHold(
            "original Mineflayer package or source is unreadable"
        ) from exc
    try:
        result = subprocess.run(
            [node, str(root / "oxygen_owner_patch.mjs"), "--inspect-only"],
            capture_output=True, text=True, timeout=10, check=False,
            cwd=root,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise I1NativePreflightHold(
            "Node source inspector could not complete before Paper boot"
        ) from exc
    match = _NODE_OK.fullmatch(result.stdout)
    if (result.returncode != 0 or match is None
            or match.group(1) != source_sha or result.stderr.strip()):
        raise I1NativePreflightHold(
            "original Node oxygen owner source inspector rejected dependencies "
            "or returned inconsistent source SHA256; no World permitted"
        )
    # Loading the actual module has no bot, socket or World side effect.
    # Unlike a version/file-only check, it detects incomplete npm-ci trees
    # whose transitive JS dependencies would crash the original Native startup
    # after Paper had already been launched. Reuse Node's own require path
    # resolution from the same original worktree as bridge.mjs.
    load_probe = (
        "const fs=require('node:fs');"
        "const path=require('node:path');"
        "const root=fs.realpathSync(path.join(process.cwd(),'node_modules','mineflayer'));"
        "const loaded=fs.realpathSync(require.resolve('mineflayer'));"
        "if(!loaded.startsWith(root+path.sep))"
        "throw new Error('Mineflayer module escaped original worktree');"
        "const mineflayer=require('mineflayer');"
        "if(typeof mineflayer.createBot!=='function')"
        "throw new Error('Mineflayer createBot unavailable');"
        "process.stdout.write('I1_NATIVE_MODULE_LOAD_OK\\n');"
    )
    try:
        loaded = subprocess.run(
            [node, "--eval", load_probe], capture_output=True,
            text=True, timeout=15, check=False, cwd=root,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise I1NativePreflightHold(
            "original Mineflayer module import preflight unavailable"
        ) from exc
    if (loaded.returncode != 0
            or loaded.stdout != "I1_NATIVE_MODULE_LOAD_OK\n"):
        raise I1NativePreflightHold(
            "original worktree-local Mineflayer module cannot load fully "
            "before Paper boot; returncode=" + str(loaded.returncode)
            + " stdout=" + repr(loaded.stdout[:1024])
            + " stderr=" + repr(loaded.stderr[:1024])
        )
    # A warning is not an import failure. Allow only the exact known Node
    # diagnostic, preserving its bytes and SHA in the original capture.
    warning = qualify_i1_node_module_stderr(loaded.stderr)
    return I1NativePreflightReceipt(
        "4.39.0", source_sha,
        node_module_warning_code=warning,
        node_module_stderr_sha256=hashlib.sha256(
            loaded.stderr.encode("utf-8")
        ).hexdigest(),
        node_module_stderr_raw=loaded.stderr,
    )
