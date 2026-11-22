"""Stage28b opt-in: one pinned real Paper A/B retired typed World/Self cut.

No LLM, no operator MOVE, no 60s autosave/continued cognition claim. This
launcher deliberately reuses the attested Stage24g Paper + resident witness
binary rather than asking users for new, arbitrary SHA pins.
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
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    args = parser.parse_args()
    try:
        if args.execute_once and not args.real_world_dev_grant:
            raise ValueError("Stage28b real World DEV approval required")
        if args.inspect_only and args.real_world_dev_grant:
            raise ValueError("inspect-only must not receive World authorization")
        checked = check_stage24g_pinned_assets(
            paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
            scratch_parent=args.scratch_parent, accepted_eula=args.eula_accepted,
        )
        _verify_local_runtime(args.java, args.node)
        print(
            "STAGE28B_PINNED_READONLY_OK "
            f"paper_sha256={checked.paper_sha256} "
            f"plugin_sha256={checked.plugin_sha256} "
            "world_created=false model_post=false", flush=True,
        )
        if args.inspect_only:
            return 0
        result = asyncio.run(run_real_resident_presence(
            paper_jar=checked.paper_jar, paper_sha256=checked.paper_sha256,
            plugin_jar=checked.plugin_jar, plugin_sha256=checked.plugin_sha256,
            scratch_parent=checked.scratch_parent,
            accepted_eula=True, real_world_dev_grant=True,
            real_llm_grant=False, b_autonomous_l1_dev=False,
            b_selected_move_dev=False, world_only=False,
            typed_owner_cut_dev=True, java=args.java, node=args.node,
            timeout_s=args.timeout_s,
        ))
        print(f"STAGE28B_TYPED_OWNER_RESULT={result}", flush=True)
        return 0
    except Exception as exc:
        print(
            f"STAGE28B_HOLD={type(exc).__name__}:{exc}",
            file=sys.stderr, flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
