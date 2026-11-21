"""Stage24b DEV: pinned asset check -> optional one-shot ORIGINAL real runner.

Avoid operator copy/paste of a 64-character plugin SHA. This *does not*
choose a Skill, issue an Action, launch a model, authenticate a GPU service,
or replace the guarded Paper runner. Read-only by default. No retries.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from experiments.p0d_real_paper_smoke_dev import (
    PAPER_1218_60_SHA256,
    file_sha256,
    prepare_assets,
)
from experiments.p0d_real_resident_presence_dev import run_real_resident_presence
from experiments.p0d_real_two_native_smoke_dev import _verify_local_runtime

# P0BRecorder actual jar, independently hashed in the archived pre-World
# Stage24b HOLD (PR #925 / Issue #911, HEAD c3b1347b). Narrow DEV pin only:
# if rebuilt, a new independently verified pin/review is required.
PINNED_STAGE24B_PLUGIN_SHA256 = (
    "cabf144a275c1582ecbbdcb6fb394b311f0705f5ca7d330bb80659437abe324e"
)


class Stage24bPinnedPreflightRefusal(RuntimeError):
    """No World or inference can begin with unqualified asset identities."""


@dataclass(frozen=True, slots=True)
class Stage24bPinnedAssetReceipt:
    paper_jar: Path
    plugin_jar: Path
    scratch_parent: Path
    paper_sha256: str
    plugin_sha256: str
    world_created: bool = False
    gpu_used: bool = False
    physical_action_issued: bool = False


def check_stage24b_pinned_assets(
    *, paper_jar: Path, plugin_jar: Path,
    scratch_parent: Path, accepted_eula: bool,
) -> Stage24bPinnedAssetReceipt:
    """Read-only check from jar BYTES; old pre-World HOLD remains immutable.

    Trust anchors are the previously attested known-good hashes, not
    caller-supplied command line digests. Existing prepare_assets independently
    rehashes and verifies jar structure and the non-symlink scratch parent.
    """
    if not accepted_eula:
        raise Stage24bPinnedPreflightRefusal("Minecraft EULA approval required")
    for name, path in (("paper", paper_jar), ("plugin", plugin_jar)):
        if (
            not isinstance(path, Path)
            or path.is_symlink()
            or not path.is_file()
            or path.suffix != ".jar"
        ):
            raise Stage24bPinnedPreflightRefusal(
                f"{name} must be a real owned source jar, not a symlink"
            )
    expected = (PAPER_1218_60_SHA256, PINNED_STAGE24B_PLUGIN_SHA256)
    if any(
        not re.fullmatch(r"[0-9a-f]{64}", digest) for digest in expected
    ):
        raise Stage24bPinnedPreflightRefusal("invalid pinned source hash")
    calculated = (file_sha256(paper_jar), file_sha256(plugin_jar))
    if calculated != expected:
        raise Stage24bPinnedPreflightRefusal(
            "source jar bytes do not match independently confirmed Stage24b pins"
        )
    # Same original Stage23/24 source-format checks; no World creation.
    paper, plugin, scratch = prepare_assets(
        paper_jar=paper_jar, paper_sha256=calculated[0],
        plugin_jar=plugin_jar, plugin_sha256=calculated[1],
        scratch_parent=scratch_parent, accepted_eula=True,
    )
    return Stage24bPinnedAssetReceipt(
        paper, plugin, scratch, calculated[0], calculated[1],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--scratch-parent", type=Path, required=True)
    parser.add_argument("--eula-accepted", action="store_true")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect-only", action="store_true")
    mode.add_argument("--execute-once", action="store_true")
    parser.add_argument("--real-world-dev-grant", action="store_true")
    parser.add_argument("--grant-real-llm", action="store_true")
    parser.add_argument("--llama-endpoint")
    parser.add_argument("--systemone-endpoint")
    parser.add_argument("--model")
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    args = parser.parse_args()
    try:
        # Fail BEFORE touching jars/World when execution permissions or model
        # identity are absent; inspect-only is always read-only.
        if args.execute_once and (
            not args.real_world_dev_grant or not args.grant_real_llm
            or not all(
                isinstance(x, str) and x.strip()
                for x in (
                    args.llama_endpoint, args.systemone_endpoint, args.model,
                )
            )
        ):
            raise Stage24bPinnedPreflightRefusal(
                "explicit real World/model grants and backend references required"
            )
        if args.inspect_only and (
            args.real_world_dev_grant or args.grant_real_llm
        ):
            raise Stage24bPinnedPreflightRefusal(
                "inspect-only must not be granted physical/model effects"
            )
        checked = check_stage24b_pinned_assets(
            paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
            scratch_parent=args.scratch_parent,
            accepted_eula=args.eula_accepted,
        )
        print(
            "STAGE24B_ASSET_CHECK_OK "
            f"paper_sha256={checked.paper_sha256} "
            f"plugin_sha256={checked.plugin_sha256} "
            "world_created=false gpu_used=false",
            flush=True,
        )
        # Reuse the ORIGINAL World runner's exact worktree-local runtime gate,
        # not external NODE_PATH resolution. This also runs in inspect-only
        # so the next real attempt cannot fail with the old missing lock
        # dependencies after an apparently successful preflight.
        _verify_local_runtime(args.java, args.node)
        print(
            "STAGE24B_RUNTIME_CHECK_OK "
            "java_major=21 node_major=22 "
            "mineflayer=4.39.0 origin=worktree-local-locked-install "
            "world_created=false gpu_used=false",
            flush=True,
        )
        if args.inspect_only:
            return 0
        # After the opt-in, the ORIGINAL real World runner checks every asset
        # again with exact source-byte hashes; only its own issuer may MOVE.
        result = asyncio.run(run_real_resident_presence(
            paper_jar=checked.paper_jar,
            paper_sha256=checked.paper_sha256,
            plugin_jar=checked.plugin_jar,
            plugin_sha256=checked.plugin_sha256,
            scratch_parent=checked.scratch_parent,
            accepted_eula=True,
            real_world_dev_grant=args.real_world_dev_grant,
            real_llm_grant=args.grant_real_llm,
            b_autonomous_l1_dev=True,
            b_selected_move_dev=False,
            b_pulse_seconds=0.35,
            world_only=True,
            java=args.java, node=args.node, timeout_s=args.timeout_s,
            llama_endpoint=args.llama_endpoint,
            systemone_endpoint=args.systemone_endpoint,
            model_name=args.model,
        ))
        print(f"STAGE24B_ONESHOT_REAL_RESULT={result}", flush=True)
        return 0
    except Exception as exc:
        print(
            f"STAGE24B_PINNED_HOLD={type(exc).__name__}:{exc}",
            file=sys.stderr,
            flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
