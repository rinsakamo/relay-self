"""Stage28c2c: one isolated restored-original A/B real Paper + real Gemma L1.

CLI for LOCAL Codex, never GitHub CI real-World evidence. Explicitly
reuses the Stage28c2b source-pinned Paper/native owner runner with an opt-in
post-WorldBody callback. All physical issue paths remain observation-only.

The model provider writes the EXACT HTTP JSON entity-body bytes handed to
urllib and received from the server, not reconstructed requests or wire
headers. On any uncertain/timeout/foreign source: HOLD and NO retry.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path

from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderError,
    LlamaCppRelayProvider,
)
from experiments.p0d_real_paper_smoke_dev import _write_bytes_new, file_sha256
from experiments.p0d_real_two_native_smoke_dev import _verify_local_runtime
from experiments.stage24g_model_gate_dev import (
    Stage24gModelGateReceipt,
    verify_stage24g_model_gate,
)
from experiments.stage24g_pinned_assets_launch_dev import (
    check_stage24g_pinned_assets,
)
from experiments.stage28c2b_real_recovered_rejoin_dev import (
    inspect_real_recovered_sources,
    run_restored_a_b_real_observation,
)
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentLlamaInferenceLane,
)
from relay_self.stage28c2c_fresh_recovered_l1_dev import (
    prepare_fresh_original_l1_turn,
    run_one_fresh_original_bounded_choice,
)


class Stage28c2cRealL1Hold(RuntimeError):
    """Real original A/B L1 selection was not source-attested."""


class OriginalRawBoundedLlamaProvider(LlamaCppRelayProvider):
    """Exactly two raw-captured BOUNDED chat POSTs, no JEV/THINK fallback.

    The provider's original thread is owned by ResidentLlamaInferenceLane.
    A refused HTTP/response is still a partially attempted call and HOLD.
    """

    def __init__(
        self, *, endpoint: str, model: str, raw_dir: Path,
        timeout: float = 45,
    ) -> None:
        super().__init__(endpoint=endpoint, model=model, timeout=timeout)
        if (
            not isinstance(raw_dir, Path) or raw_dir.is_symlink()
            or not raw_dir.is_dir() or any(raw_dir.iterdir())
        ):
            raise Stage28c2cRealL1Hold("fresh empty owned raw Gemma directory required")
        self.raw_dir = raw_dir
        self.attempted = 0
        self.completed = 0
        self.source_receipts: list[dict] = []

    def _call(
        self, request_body: dict[str, object], *,
        endpoint: str | None = None,
    ) -> dict:
        if endpoint is not None or self.attempted >= 2:
            raise Stage28c2cRealL1Hold("JEV/THINK or repeated model POST forbidden")
        ordinal = self.attempted + 1
        raw_request = json.dumps(
            request_body, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        prefix = f"bounded-{ordinal}"
        _write_bytes_new(
            self.raw_dir / f"{prefix}-request-body.bin", raw_request,
        )
        self.attempted += 1
        req = urllib.request.Request(
            self.endpoint, data=raw_request,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        response_bytes: bytes | None = None
        status: int | None = None
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                status = response.status
                response_bytes = response.read(1024 * 1024 + 1)
        except urllib.error.HTTPError as exc:
            status = exc.code
            response_bytes = exc.read(1024 * 1024 + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # The remote backend may still be calculating. The GPU owner,
            # not a client timeout, must independently prove actual idle.
            raise LlamaCppProviderError(
                "real Gemma request may be in flight: " + type(exc).__name__
            ) from exc
        if (
            type(status) is not int or response_bytes is None
            or len(response_bytes) > 1024 * 1024
        ):
            raise Stage28c2cRealL1Hold("real model response bounded source missing")
        _write_bytes_new(
            self.raw_dir / f"{prefix}-response-body.bin", response_bytes,
        )
        receipt = {
            "schema": 1,
            "capture_type": "urllib_http_entity_bodies_not_wire_headers",
            "ordinal": ordinal,
            "http_status": status,
            "request_body_sha256": hashlib.sha256(raw_request).hexdigest(),
            "response_body_sha256": hashlib.sha256(response_bytes).hexdigest(),
            "request_body_bytes": len(raw_request),
            "response_body_bytes": len(response_bytes),
        }
        _write_bytes_new(
            self.raw_dir / f"{prefix}-http-evidence.json",
            (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode(),
        )
        if status != 200:
            raise LlamaCppProviderError("real Gemma HTTP status not 200")
        try:
            answer = json.loads(response_bytes)
        except (ValueError, UnicodeError) as exc:
            raise LlamaCppProviderError("real Gemma raw response invalid JSON") from exc
        if not isinstance(answer, dict):
            raise Stage28c2cRealL1Hold("real Gemma response must be object")
        self.completed += 1
        self.source_receipts.append(receipt)
        return answer


def inspect_real_l1_sources(
    *, generation: Path, restored: Path, stage28b_evidence: Path,
    paper_jar: Path, plugin_jar: Path,
    scratch_parent: Path, gguf: Path, llama_pid: int,
    model_alias: str, llama_endpoint: str,
    java: str, node: str,
) -> Stage24gModelGateReceipt:
    """Read-only original A/B, pinned jars and actual Gemma PID/GPU/slot."""
    _verify_local_runtime(java, node)
    inspect_real_recovered_sources(generation, restored, stage28b_evidence)
    check_stage24g_pinned_assets(
        paper_jar=paper_jar, plugin_jar=plugin_jar,
        scratch_parent=scratch_parent, accepted_eula=True,
    )
    # Pass SAME local endpoint for both arguments: preflight only inspects
    # the PID-owned socket/one idle slot; actual execution below is ordinary
    # strict structured-json BOUNDED (/v1/chat/completions), NOT Jev.
    return verify_stage24g_model_gate(
        gguf_path=gguf, llama_pid=llama_pid, model_alias=model_alias,
        llama_endpoint=llama_endpoint, systemone_endpoint=llama_endpoint,
    )


async def run_real_original_a_b_l1(
    *, generation: Path, restored: Path, stage28b_evidence: Path,
    paper_jar: Path, plugin_jar: Path,
    execution_dir: Path, evidence_dir: Path,
    java: str, node: str, llama_endpoint: str,
    model_alias: str, gate: Stage24gModelGateReceipt,
    timeout_s: float = 180, presence_timeout_s: float = 12,
    model_wait_s: float = 60,
) -> Path:
    """Exactly one newly isolated Paper trial; A/B each max ONE model POST."""
    if (
        not isinstance(gate, Stage24gModelGateReceipt)
        or gate.model_alias != model_alias or gate.llama_pid <= 1
        or gate.slot_count != 1 or gate.slot_id != 0
        or type(model_wait_s) not in (float, int)
        or not 0 < model_wait_s <= 75
    ):
        raise Stage28c2cRealL1Hold("source-pinned model and bounded wait required")

    async def on_reconnected(
        *, prepared, bridge, boot, world, links, paper, evidence, report,
    ) -> None:
        if (
            bridge.inference_lane is not None
            or not bridge.physical.observation_only
            or bridge.physical.active_action_ids
            or paper.owned_session_id != boot.paper_session_id
        ):
            raise Stage28c2cRealL1Hold("actual original Body requires no physical authority")
        _write_bytes_new(
            evidence / "stage28c2c-model-preflight.json",
            (json.dumps(asdict(gate), sort_keys=True, indent=2) + "\n").encode(),
        )
        raw_dir = evidence / "stage28c2c-llama-original"
        raw_dir.mkdir(mode=0o700)
        provider = OriginalRawBoundedLlamaProvider(
            endpoint=llama_endpoint, model=model_alias, raw_dir=raw_dir,
            timeout=min(45.0, model_wait_s),
        )
        witness = LlamaCppSingleSlotWitness(
            provider=provider, backend_ref=f"stage28c2c-pid-{gate.llama_pid}",
        )
        idle = witness.require_idle()
        # Stage28b original registry has no saved EXPLORE and no current
        # proven physical Preset. Thus NO injected Skill, Target or capability:
        # only the naturally generated ESCALATE_L2 / DEFER candidates.
        turns = {
            sid: prepare_fresh_original_l1_turn(
                plan=prepared.recovered.plan, bridge=bridge, boot=boot,
                world=world, links=links, idle=idle,
                self_id=sid, allowed_skills=frozenset(),
                preset_by_skill=(),
            )
            for sid in ("A", "B")
        }
        if any(
            [c.description for c in turns[sid].request.choices]
            != ["ESCALATE_L2", "DEFER"]
            for sid in ("A", "B")
        ):
            raise Stage28c2cRealL1Hold(
                "original checkpoint did not prove admissible physical Presets"
            )
        report["stage28c2c_original_turns"] = {
            sid: {
                "self_id": turn.self_id,
                "owner_scope": list(turn.owner_scope),
                "native_probe_ref": turn.native_probe_ref,
                "native_probe_seq": turn.native_probe_seq,
                "pattern_registry_revision": turn.pattern_registry_revision,
                "candidate_set_sha256": turn.candidate_set_sha256,
                "paper_session_id": turn.paper_session_id,
                "paper_boot_id": turn.paper_boot_id,
                "allowed_skills": [],
                "presets": [],
                "request": asdict(turn.request),
                "original_owner_adopted": True,
                "old_l1_result_reused": False,
                "physical_action_issue_authorized": False,
            }
            for sid, turn in turns.items()
        }
        lane = ResidentLlamaInferenceLane(
            provider=provider, cognitive_work=bridge.cognitive_work,
            witness=witness,
        )
        bridge.attach_observation_only_bounded_l1(lane)
        results = {}
        try:
            for sid in ("A", "B"):
                result = await run_one_fresh_original_bounded_choice(
                    bridge=bridge, boot=boot, turn=turns[sid],
                    lane=lane, timeout_s=model_wait_s,
                )
                if (
                    result.selection_status not in {"ESCALATE_L2", "DEFER"}
                    or result.choice_id not in {"1", "2"}
                    or result.selected_skill_id is not None
                    or result.selected_target_ref is not None
                    or result.action_issued or result.skill_started
                    or result.intent_committed or result.peer_sent
                    or result.old_l1_result_reused
                ):
                    raise Stage28c2cRealL1Hold(
                        "Gemma selected an unqualified original frozen option"
                    )
                results[sid] = asdict(result)
        finally:
            # Raw responses/partial files survive any failure; the enclosing
            # b runner will save HOLD and clean owned native/Paper only.
            report["real_gemma_post"] = provider.completed
            report["model_post_attempted"] = provider.attempted
            report["stage28c2c_model_raw_sha256"] = {
                path.name: file_sha256(path)
                for path in sorted(raw_dir.iterdir())
                if path.is_file()
            }
        if provider.attempted != 2 or provider.completed != 2:
            raise Stage28c2cRealL1Hold("both original A/B must have one real Gemma POST")
        # Existing bridge.logout will fence actual GPU work and verify
        # that both real provider futures are done and /slots is idle.
        report["stage28c2c_l1_results"] = results
        report["stage28c2c_model_gate"] = asdict(gate)
        report["stage28c2c_backend_terminal_idle"] = asdict(lane.require_world_idle())
        report["fresh_l1_run"] = True
        if not all(
            bridge.owners[sid].current_worldbody_observation
            is bridge.last_login_observations[sid]
            for sid in ("A", "B")
        ):
            raise Stage28c2cRealL1Hold("original A/B WorldBody changed after L1")
    return await run_restored_a_b_real_observation(
        generation=generation, restored=restored,
        stage28b_evidence=stage28b_evidence,
        execution_dir=execution_dir, evidence_dir=evidence_dir,
        paper_jar=paper_jar, plugin_jar=plugin_jar,
        java=java, node=node, timeout_s=timeout_s,
        presence_timeout_s=presence_timeout_s,
        on_reconnected=on_reconnected,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--stage28b-evidence", type=Path, required=True)
    parser.add_argument("--paper-jar", type=Path, required=True)
    parser.add_argument("--plugin-jar", type=Path, required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--llama-pid", type=int, required=True)
    parser.add_argument("--model-alias", required=True)
    parser.add_argument("--llama-endpoint", required=True)
    parser.add_argument("--execution-dir", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--java", default="java")
    parser.add_argument("--node", default="node")
    parser.add_argument("--eula-accepted", action="store_true")
    parser.add_argument("--real-world-dev-grant", action="store_true")
    parser.add_argument("--model-post-grant", action="store_true")
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--presence-timeout-s", type=float, default=12.0)
    parser.add_argument("--model-wait-s", type=float, default=60.0)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--inspect-only", action="store_true")
    modes.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    try:
        if not args.eula_accepted:
            raise Stage28c2cRealL1Hold("Minecraft EULA consent required")
        if args.inspect_only and (
            args.real_world_dev_grant or args.model_post_grant
            or args.execution_dir is not None or args.evidence_dir is not None
        ):
            raise Stage28c2cRealL1Hold("inspect must not create Paper or model POST")
        if args.execute_once and (
            not args.real_world_dev_grant or not args.model_post_grant
            or args.execution_dir is None or args.evidence_dir is None
        ):
            raise Stage28c2cRealL1Hold(
                "exactly one new isolated World and BOUNDED Gemma grant required"
            )
        scratch = (
            args.execution_dir.parent if args.execution_dir is not None
            else args.restored.parent
        )
        gate = inspect_real_l1_sources(
            generation=args.generation, restored=args.restored,
            stage28b_evidence=args.stage28b_evidence,
            paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
            scratch_parent=scratch, gguf=args.gguf, llama_pid=args.llama_pid,
            model_alias=args.model_alias, llama_endpoint=args.llama_endpoint,
            java=args.java, node=args.node,
        )
        print(
            "STAGE28C2C_SOURCE_MODEL_INSPECT_PASS "
            f"model_pid={gate.llama_pid} gpu={gate.gpu_name} "
            "slot_count=1 world_started=false model_post=false",
            flush=True,
        )
        if args.inspect_only:
            return 0
        result = asyncio.run(run_real_original_a_b_l1(
            generation=args.generation, restored=args.restored,
            stage28b_evidence=args.stage28b_evidence,
            paper_jar=args.paper_jar, plugin_jar=args.plugin_jar,
            execution_dir=args.execution_dir, evidence_dir=args.evidence_dir,
            java=args.java, node=args.node,
            llama_endpoint=args.llama_endpoint,
            model_alias=args.model_alias, gate=gate,
            timeout_s=args.timeout_s, presence_timeout_s=args.presence_timeout_s,
            model_wait_s=args.model_wait_s,
        ))
        print(f"STAGE28C2C_REAL_CAPTURED_UNAUDITED={result}", flush=True)
        return 0
    except BaseException as exc:
        print(
            f"STAGE28C2C_HOLD={type(exc).__name__}:{exc}",
            file=sys.stderr, flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
