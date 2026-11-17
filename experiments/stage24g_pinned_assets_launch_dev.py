"""Stage24g DEV: pinned asset check -> optional one-shot ORIGINAL real runner.

Avoid operator copy/paste of a 64-character plugin SHA. This *does not*
choose a Skill, issue an Action, launch a model, authenticate a GPU service,
or replace the guarded Paper runner. Read-only by default. No retries.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from experiments.p0d_real_paper_smoke_dev import (
    PAPER_1218_60_SHA256,
    file_sha256,
    prepare_assets,
)
from experiments.p0d_real_two_native_smoke_dev import _verify_local_runtime

# Built from Stage24g source with Java 21; archived and independently hashed
# in /home/rinsa/evidence/stage24g-witness-20261117/P0BRecorder.jar.
PINNED_STAGE24G_PLUGIN_SHA256 = (
    "0b20dd042231618fc301bbe26ee48c5808c09dafddc946c49f4393ca48386fb5"
)


class Stage24gPinnedPreflightRefusal(RuntimeError):
    """No World or inference can begin with unqualified asset identities."""


@dataclass(frozen=True, slots=True)
class Stage24gPinnedAssetReceipt:
    paper_jar: Path
    plugin_jar: Path
    scratch_parent: Path
    paper_sha256: str
    plugin_sha256: str
    world_created: bool = False
    gpu_used: bool = False
    physical_action_issued: bool = False


def check_stage24g_pinned_assets(
    *, paper_jar: Path, plugin_jar: Path,
    scratch_parent: Path, accepted_eula: bool,
) -> Stage24gPinnedAssetReceipt:
    """Read-only check from jar BYTES; old pre-World HOLD remains immutable.

    Trust anchors are the previously attested known-good hashes, not
    caller-supplied command line digests. Existing prepare_assets independently
    rehashes and verifies jar structure and the non-symlink scratch parent.
    """
    if not accepted_eula:
        raise Stage24gPinnedPreflightRefusal("Minecraft EULA approval required")
    for name, path in (("paper", paper_jar), ("plugin", plugin_jar)):
        if (
            not isinstance(path, Path)
            or path.is_symlink()
            or not path.is_file()
            or path.suffix != ".jar"
        ):
            raise Stage24gPinnedPreflightRefusal(
                f"{name} must be a real owned source jar, not a symlink"
            )
    expected = (PAPER_1218_60_SHA256, PINNED_STAGE24G_PLUGIN_SHA256)
    if any(
        not re.fullmatch(r"[0-9a-f]{64}", digest) for digest in expected
    ):
        raise Stage24gPinnedPreflightRefusal("invalid pinned source hash")
    calculated = (file_sha256(paper_jar), file_sha256(plugin_jar))
    if calculated != expected:
        raise Stage24gPinnedPreflightRefusal(
            "source jar bytes do not match independently confirmed Stage24g pins"
        )
    # Same original Stage23/24 source-format checks; no World creation.
    paper, plugin, scratch = prepare_assets(
        paper_jar=paper_jar, paper_sha256=calculated[0],
        plugin_jar=plugin_jar, plugin_sha256=calculated[1],
        scratch_parent=scratch_parent, accepted_eula=True,
    )
    return Stage24gPinnedAssetReceipt(
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
            raise Stage24gPinnedPreflightRefusal(
                "explicit real World/model grants and backend references required"
            )
        if args.inspect_only and (
            args.real_world_dev_grant or args.grant_real_llm
        ):
            raise Stage24gPinnedPreflightRefusal(
                "inspect-only must not be granted physical/model effects"
            )
        checked = check_stage24g_pinned_assets(
            paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
            scratch_parent=args.scratch_parent,
            accepted_eula=args.eula_accepted,
        )
        print(
            "STAGE24G_ASSET_CHECK_OK "
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
            "STAGE24G_RUNTIME_CHECK_OK "
            "java_major=21 node_major=22 "
            "mineflayer=4.39.0 origin=worktree-local-locked-install "
            "world_created=false gpu_used=false",
            flush=True,
        )
        if args.inspect_only:
            return 0
        raise Stage24gPinnedPreflightRefusal(
            "HOLD: independent GPU/model/WAL gate and HTTP capture are not yet implemented"
        )
    except Exception as exc:
        print(
            f"STAGE24G_PINNED_HOLD={type(exc).__name__}:{exc}",
            file=sys.stderr,
            flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
