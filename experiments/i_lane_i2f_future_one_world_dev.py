"""I2f LOCAL one-shot original v3 A/B World -> real L2/L1 model raw capture.

Separate from the protected *historic* Stage28b run: requires explicit NEW
v3 source/Native history pins, actual exclusive llama PID/GGUF single slot,
fresh isolated Paper execution/evidence directories and opt-in grants. Only
the original bridge/Owner/lane can issue the TWO model requests; no physical
Action, no retry, and no automatic independent PASS promotion.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from experiments.i_lane_i2e_original_dual_model_raw_dev import (
    I2eOriginalDualModeRawProvider,
    run_i2e_original_dual_raw,
)
from experiments.p0d_real_paper_smoke_dev import _write_bytes_new
from experiments.p0d_real_two_native_smoke_dev import _verify_local_runtime
from experiments.stage24g_model_gate_dev import (
    Stage24gModelGateReceipt,
    verify_stage24g_model_gate,
)
from experiments.stage24g_pinned_assets_launch_dev import check_stage24g_pinned_assets
from experiments.stage28c2b_real_recovered_rejoin_dev import (
    inspect_real_recovered_sources,
    run_restored_a_b_real_observation,
)
from relay_self.i_lane_i1_native_preflight_dev import require_i1_native_preflight
from relay_self.i_lane_i2f_future_source_pins_dev import (
    I2fFutureSourcePins,
    read_i2f_future_source_pins,
)
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentLlamaInferenceLane,
)
from relay_self.stage28c2b_native_paper_body_link_dev import (
    link_recovered_a_b_native_paper_body,
)


class I2fOriginalWorldHold(RuntimeError):
    """Real model/native/Paper/source preflight not independently qualified."""


async def run_i2f_one_original_world(
    *, generation: Path, restored: Path, original_evidence: Path,
    pins: I2fFutureSourcePins,
    paper_jar: Path, plugin_jar: Path,
    execution_dir: Path, evidence_dir: Path,
    java: str, node: str, llama_endpoint: str, model_alias: str,
    gate: Stage24gModelGateReceipt,
    timeout_s: float = 180, presence_timeout_s: float = 12,
    model_wait_s: float = 60,
) -> Path:
    """Exactly one future v3 World run; model chooses, NOT runner flags."""
    if (
        not isinstance(pins, I2fFutureSourcePins)
        or not isinstance(gate, Stage24gModelGateReceipt)
        or gate.model_alias != model_alias
        or gate.llama_pid <= 1 or gate.slot_count != 1 or gate.slot_id != 0
        or type(model_wait_s) not in (int, float)
        or not 0 < model_wait_s <= 60
    ):
        raise I2fOriginalWorldHold("new v3 source and owned model slot required")

    async def on_reconnected(
        *, prepared, bridge, boot, world, links, paper, evidence, report,
    ) -> None:
        if (
            bridge.inference_lane is not None
            or not bridge.physical.observation_only
            or bridge.physical.active_action_ids
            or paper.owned_session_id != boot.paper_session_id
            or prepared.recovered.plan.source_world_id != pins.source_world_id
            or prepared.recovered.receipt.source_committed_sha256
            != pins.source_committed_sha256
            or set(bridge.owners) != {"A", "B"}
        ):
            raise I2fOriginalWorldHold("original verified A/B Body or new-source pin missing")
        _write_bytes_new(
            evidence / "i2f-model-preflight.json",
            (json.dumps(asdict(gate), sort_keys=True, indent=2) + "\n").encode(),
        )
        raw_dir = evidence / "i2f-original-dual-model"
        raw_dir.mkdir(mode=0o700)
        provider = I2eOriginalDualModeRawProvider(
            endpoint=llama_endpoint, model=model_alias,
            raw_dir=raw_dir, timeout=min(45.0, model_wait_s),
        )
        witness = LlamaCppSingleSlotWitness(
            provider=provider, backend_ref="i2f-pid-" + str(gate.llama_pid),
        )
        witness.require_idle()
        lane = ResidentLlamaInferenceLane(
            provider=provider, cognitive_work=bridge.cognitive_work,
            witness=witness,
        )
        bridge.attach_observation_only_bounded_l1(lane)
        try:
            # Read from the ORIGINAL A+B native subprocesses, not a new
            # model-facing observation client, then refresh the original
            # owned Paper/presence link. A stale link is HOLD.
            for sid in ("A", "B"):
                await bridge.refresh_i1_read_only_sense(sid, timeout_s=2.0)
            fresh_world, fresh_links = link_recovered_a_b_native_paper_body(
                bridge=bridge, paper=paper, boot=boot,
                forbidden_native_sessions=frozenset(
                    boot.historical_native_sessions
                ),
                i1_require_complete_paper_prefix=True,
            )
            if (
                fresh_world.paper_session_id != world.paper_session_id
                or {link.self_id for link in fresh_links} != {"A", "B"}
                or len(fresh_links) != len(links)
            ):
                raise I2fOriginalWorldHold("same original A/B Paper refresh not correlated")
            model_result = await run_i2e_original_dual_raw(
                bridge=bridge, boot=boot,
                world=fresh_world, links=fresh_links,
                self_id="A", lane=lane,
                provider=provider, timeout_s=model_wait_s,
            )
            report["i2f_dual_model_completed"] = True
            report["i2f_model_result"] = model_result["outcome"]["outcome"]
            report["i2f_model_report_sha256"] = hashlib.sha256(
                (raw_dir / "i2e-dual-model-report.json").read_bytes()
            ).hexdigest()
            if model_result["all_physical_actions"] != 0:
                raise I2fOriginalWorldHold("physical action forbidden")
        finally:
            report["real_gemma_post"] = provider.completed
            report["model_post_attempted"] = provider.attempted
            report["i2f_model_raw_sha256"] = {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(raw_dir.iterdir()) if p.is_file()
            }
        if provider.attempted != 2 or provider.completed != 2:
            raise I2fOriginalWorldHold("actual L2/L1 model entity bytes incomplete")
        report["stage28c2c_backend_terminal_idle"] = asdict(lane.require_world_idle())
        report["i2f_model_gate"] = asdict(gate)
        report["fresh_l1_run"] = True
        report["real_action_issued"] = 0

    return await run_restored_a_b_real_observation(
        generation=generation, restored=restored,
        stage28b_evidence=original_evidence,
        execution_dir=execution_dir, evidence_dir=evidence_dir,
        paper_jar=paper_jar, plugin_jar=plugin_jar,
        java=java, node=node,
        timeout_s=timeout_s,
        presence_timeout_s=presence_timeout_s,
        on_reconnected=on_reconnected,
        i1_original_cpu_sense=True,
        future_pins=pins,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--original-evidence", type=Path, required=True)
    parser.add_argument("--new-source-pins", type=Path, required=True)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--gguf-path", type=Path, required=True)
    parser.add_argument("--llama-pid", type=int, required=True)
    parser.add_argument("--model-alias", required=True)
    parser.add_argument("--llama-endpoint", required=True)
    parser.add_argument("--execution-dir", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--presence-timeout-s", type=float, default=12.0)
    parser.add_argument("--model-wait-s", type=float, default=60.0)
    parser.add_argument("--eula-accepted", action="store_true")
    parser.add_argument("--real-world-dev-grant", action="store_true")
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    try:
        if (args.inspect_only == args.execute_once
                or not args.eula_accepted
                or (args.inspect_only and (
                    args.real_world_dev_grant
                    or args.execution_dir is not None
                    or args.evidence_dir is not None
                ))
                or (args.execute_once and (
                    not args.real_world_dev_grant
                    or args.execution_dir is None
                    or args.evidence_dir is None
                ))):
            raise I2fOriginalWorldHold(
                "inspect-only or exactly one World DEV and explicit grants required"
            )
        pins = read_i2f_future_source_pins(args.new_source_pins)
        checked = check_stage24g_pinned_assets(
            paper_jar=args.paper_jar,
            plugin_jar=args.plugin_jar,
            scratch_parent=(
                args.execution_dir.parent
                if args.execution_dir else args.restored.parent
            ),
            accepted_eula=True,
        )
        _verify_local_runtime(args.java, args.node)
        require_i1_native_preflight(node=args.node)
        _, state = inspect_real_recovered_sources(
            args.generation, args.restored, args.original_evidence,
            future_pins=pins,
        )
        if state.plan.source_world_id != pins.source_world_id:
            raise I2fOriginalWorldHold("future original source changed")
        gate = verify_stage24g_model_gate(
            gguf_path=args.gguf_path, llama_pid=args.llama_pid,
            model_alias=args.model_alias,
            llama_endpoint=args.llama_endpoint,
            systemone_endpoint=args.llama_endpoint,
        )
        print("I2F_NEW_V3_AND_GPU_PRE_WORLD_PASS "
              "world_started=false model_post=false physical_actions=0", flush=True)
        if args.inspect_only:
            return 0
        result = asyncio.run(run_i2f_one_original_world(
            generation=args.generation, restored=args.restored,
            original_evidence=args.original_evidence, pins=pins,
            paper_jar=checked.paper_jar, plugin_jar=checked.plugin_jar,
            execution_dir=args.execution_dir, evidence_dir=args.evidence_dir,
            java=args.java, node=args.node,
            llama_endpoint=args.llama_endpoint, model_alias=args.model_alias,
            gate=gate, timeout_s=args.timeout_s,
            presence_timeout_s=args.presence_timeout_s,
            model_wait_s=args.model_wait_s,
        ))
        print("I2F_CAPTURED_INDEPENDENT_AUDIT_PENDING=" + str(result), flush=True)
        return 0
    except BaseException as exc:
        print(f"I2F_PRE_WORLD_OR_TRIAL_HOLD={type(exc).__name__}:{exc}",
              file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
