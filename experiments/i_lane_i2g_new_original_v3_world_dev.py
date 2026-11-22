"""I2g: one NEW original passive A/B real Paper→typed recorded-v3 source.

The historical Stage28b runner remains unchanged by default. This wrapper
sets a NEW opt-in born persistent PatternRegistry + recorded EMPTY Schema
before first native JOIN and captures three original Native stdin/stdout
sessions while leaving all Physical Actions and GPU model work unused.
A separate process MUST independently audit/seal before the I2f fork.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from experiments.p0d_real_resident_presence_dev import run_real_resident_presence
from experiments.p0d_real_two_native_smoke_dev import _verify_local_runtime
from experiments.stage24g_pinned_assets_launch_dev import (
    check_stage24g_pinned_assets,
)
from relay_self.i_lane_i1_native_preflight_dev import require_i1_native_preflight


class I2gRealOriginHold(RuntimeError):
    """Initial real A/B original Source must remain HOLD without full witnesses."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--scratch-parent", type=Path, required=True)
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--eula-accepted", action="store_true")
    parser.add_argument("--real-world-dev-grant", action="store_true")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect-only", action="store_true")
    mode.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    try:
        if (
            not args.eula_accepted
            or (args.inspect_only and args.real_world_dev_grant)
            or (args.execute_once and not args.real_world_dev_grant)
        ):
            raise I2gRealOriginHold(
                "explicit EULA and exactly one separate original World DEV grant required"
            )
        checked = check_stage24g_pinned_assets(
            paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
            scratch_parent=args.scratch_parent, accepted_eula=True,
        )
        _verify_local_runtime(args.java, args.node)
        preflight = require_i1_native_preflight(node=args.node)
        print(
            "I2G_ORIGINAL_BORN_V3_PRE_WORLD_PASS "
            f"paper_sha256={checked.paper_sha256} "
            f"plugin_sha256={checked.plugin_sha256} "
            f"mineflayer_version={preflight.mineflayer_version} "
            "world_started=false native_joined=false real_gemma_posts=0",
            flush=True,
        )
        if args.inspect_only:
            return 0
        result = asyncio.run(run_real_resident_presence(
            paper_jar=checked.paper_jar, paper_sha256=checked.paper_sha256,
            plugin_jar=checked.plugin_jar, plugin_sha256=checked.plugin_sha256,
            scratch_parent=checked.scratch_parent, accepted_eula=True,
            real_world_dev_grant=True, java=args.java, node=args.node,
            timeout_s=args.timeout_s, world_only=False,
            b_selected_move_dev=False, b_autonomous_l1_dev=False,
            real_llm_grant=False, typed_owner_cut_dev=True,
            i2g_original_v3_source=True,
        ))
        # That return means one bounded real source CAPTURE, not audit PASS.
        # The independent source verifier and seal are intentionally external.
        print(
            "I2G_REAL_ORIGINAL_V3_CAPTURED_INDEPENDENT_AUDIT_PENDING="
            + str(result), flush=True,
        )
        return 0
    except BaseException as exc:
        print(
            f"I2G_REAL_ORIGINAL_PRE_WORLD_OR_TRIAL_HOLD="
            f"{type(exc).__name__}:{exc}",
            file=sys.stderr, flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
