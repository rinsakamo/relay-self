"""Opt-in real llama.cpp / Mineflayer one-turn DEV runner for #828 §27.

No hidden Minecraft server start, model discovery, retry, S49 replacement,
native Action grant or automatic learning promotion. Requires a separately
running authorized local Minecraft server and llama.cpp runtime.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerObservation,
)
from experiments.cognitive_minimal_minecraft_dev import execute_one_cognitive_world_turn
from experiments.controlled_minecraft_vertical import ControlledScenario
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    initial_patterns,
    parse_l2_pattern_proposal,
    prepare_l2_pattern_request,
)
from relay_self.intent import IntentCommitment
from relay_self.relay_engine import RelayEngine


class CognitiveWorldRunError(RuntimeError):
    """Failed DEV run with preserved *uncertain*, not successful, native evidence."""

    def __init__(self, audit: dict[str, object]) -> None:
        self.audit = audit
        super().__init__(str(audit["error"]))


def _write_evidence(path: str | None, value: dict[str, object]) -> None:
    """Write a complete one-shot result, including failure, before reporting."""
    if path is None:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--grant-real-world", action="store_true")
    p.add_argument("--grant-real-llm", action="store_true")
    p.add_argument("--execute-native", action="store_true",
                   help="opt into main-branch EAT/FIGHT physical issuer; default shadow")
    p.add_argument("--acknowledge-unfenced-dev", action="store_true",
                   help="explicit DEV-only risk acceptance: original S49 #767 "
                        "durable PRE-ISSUE fence is not integrated")
    p.add_argument("--mc-host", default="127.0.0.1")
    p.add_argument("--mc-port", type=int, default=25565)
    p.add_argument("--mc-version", default="1.21.8")
    p.add_argument("--mc-username", default="RelaySelf")
    p.add_argument("--node", default="node")
    p.add_argument("--llama-endpoint", default="http://127.0.0.1:8080/v1/chat/completions")
    p.add_argument("--systemone-endpoint", help="explicit Jev-capable /v1/systemone endpoint")
    p.add_argument("--model", required=True)
    p.add_argument("--llama-timeout-s", type=float, default=30,
                   help="per-provider HTTP timeout, not a GPU preemption guarantee")
    p.add_argument("--evidence-path",
                   help="local JSON result including failure and outstanding Action IDs")
    p.add_argument("--self-id", default="relay-self-cognitive-dev")
    p.add_argument("--intent-id", default="intent-cognitive-dev-1")
    p.add_argument("--edible-item", action="append", default=[],
                   help="known edible inventory item name (repeat for multiple)")
    p.add_argument("--hazard-name", action="append", default=[],
                   help="name from native Mineflayer entity facts, e.g. zombie")
    p.add_argument("--fight-max-distance", type=float)
    p.add_argument("--hunger-threshold", type=float, default=10)
    p.add_argument("--startup-timeout-s", type=float, default=30)
    p.add_argument("--evidence-timeout-s", type=float, default=8)
    p.add_argument("--enable-l2-proposal", action="store_true",
                   help="one unaccepted SystemTwo JSON hypothesis if L1 escalates")
    return p


async def _initial_spawn(session: MineflayerProcessSession, timeout_s: float) -> MineflayerObservation:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise MinimalCognitionError("no source-qualified spawn observation")
        msg = await asyncio.wait_for(session.receive(), timeout=remaining)
        if isinstance(msg, MineflayerObservation):
            if msg.kind == "death":
                raise MinimalCognitionError("Self died before initial cognition")
            if msg.kind == "spawn":
                return msg
        if isinstance(msg, (MineflayerAdapterErrorMessage, MineflayerCommandError,
                            MineflayerConnectionEnd)):
            raise MinimalCognitionError(
                f"native session unavailable: {type(msg).__name__}"
            )


async def run(args: argparse.Namespace) -> dict[str, object]:
    if not args.grant_real_world or not args.grant_real_llm:
        raise MinimalCognitionError("both explicit real-world and real-LLM grants required")
    if args.execute_native and not args.acknowledge_unfenced_dev:
        raise MinimalCognitionError(
            "UNFENCED_DEV_ONLY: --execute-native requires "
            "--acknowledge-unfenced-dev; #767 S49 pre-ISSUE fence is absent"
        )
    if args.fight_max_distance is not None and args.fight_max_distance <= 0:
        raise MinimalCognitionError("invalid configured fight range")
    scenario = ControlledScenario(
        hazard_entity_names=frozenset(args.hazard_name),
        food_threshold=args.hunger_threshold,
        edible_item_names=tuple(args.edible_item),
        destinations=(),
        fight_max_distance=args.fight_max_distance,
        evidence_timeout_s=args.evidence_timeout_s,
        max_evidence_messages=32,
        cognition_think_allowed=False,
    )
    engine = RelayEngine(LlamaCppRelayProvider(
        endpoint=args.llama_endpoint, systemone_endpoint=args.systemone_endpoint,
        model=args.model, timeout=args.llama_timeout_s,
    ))
    session: MineflayerProcessSession | None = None
    first: MineflayerObservation | None = None
    owner = IntentCommitment()
    supervisor = ActionSupervisor()
    try:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(
                host=args.mc_host, port=args.mc_port, username=args.mc_username,
                version=args.mc_version,
            ),
            node_executable=args.node, startup_timeout_s=args.startup_timeout_s,
        )
        first = await _initial_spawn(session, args.startup_timeout_s)
        receipt = await execute_one_cognitive_world_turn(
            session, first, scenario,
            self_id=args.self_id, intent_id=args.intent_id,
            registry=initial_patterns(), relay_engine=engine, intent_owner=owner,
            supervisor=supervisor, grant_real_world=True,
            issue_native=args.execute_native,
            acknowledge_unfenced_dev=args.acknowledge_unfenced_dev,
        )
        issued_at = next(
            (event.at_ns for action in ([] if receipt.run is None else receipt.run.actions)
             for event in action.events if event.state.value == "issued"),
            None,
        )
        committed_at = (
            None if owner.current_intent is None
            else owner.current_intent.committed_at_ns
        )
        outcome = {
            "evidence_class": "REAL_LLM_AND_NATIVE_WORLD_DEV_ATTEMPT",
            "qualification": "NOT_CLAIMED",
            "original_s49_full_runtime": "NOT_CONNECTED",
            "existing_issuer": "controlled_minecraft_vertical.execute_decision",
            "model_declared": args.model,
            "systemone_backend": bool(args.systemone_endpoint),
            "world_session": first.session_id,
            "status": receipt.status,
            "l1_choice_id": receipt.l1_result.choice_id,
            "l1_latency_ns": receipt.l1_elapsed_ns,
            "intent_to_action_issued_ns": (
                None if issued_at is None or committed_at is None
                else issued_at - committed_at
            ),
            "schema_cpu_epoch_ns": receipt.initial_frame.elapsed_ns,
            "schema_pattern_checks": receipt.initial_frame.pattern_checks,
            "target_count": len(receipt.initial_frame.options),
            "probe_latency_ns": receipt.probe_elapsed_ns,
            "selected": (None if receipt.selection.option is None
                         else asdict(receipt.selection.option)),
            "selection_reason": receipt.selection.reason,
            "action_outcome_count": receipt.actual_action_outcomes,
            "native_actions": (
                [] if receipt.run is None else
                [{"action_id": a.action_id, "state": a.state.value}
                 for a in receipt.run.actions]
            ),
            "native_effect_receipts": (
                [] if receipt.run is None else [
                    {"action_id": message.action_id, "result": message.result,
                     "effect": message.effect, "source_ref": message.provenance.reference}
                    for message in receipt.run.messages
                    if isinstance(message, MineflayerEffectResult)
                ]
            ),
            "skill_final_state": (
                None if receipt.run is None else
                receipt.run.skill_execution.state.value
            ),
            "provider_prompt_tokens": receipt.l1_result.observed_prompt_tokens,
            "provider_completion_tokens": receipt.l1_result.observed_completion_tokens,
            "separate_prefill_decode_timing": "NOT_MEASURED",
            "gpu_preemption": "NOT_MEASURED",
            "self_grant_execute_native": args.execute_native,
            "physical_fence": (
                "UNFENCED_DEV_ONLY" if args.execute_native else "NOT_ISSUED"
            ),
            "original_s49_preissue_wal": "NOT_CONNECTED",
        }
        if args.enable_l2_proposal and receipt.status == "ESCALATE_L2":
            request = prepare_l2_pattern_request(receipt.initial_frame)
            try:
                expr = await asyncio.to_thread(engine.open, request)
                proposal = parse_l2_pattern_proposal(
                    expr.text, model_provenance=expr.provenance,
                )
                outcome["l2_pattern"] = {
                    "proposal": asdict(proposal),
                    "self_accepted": False,
                    "published": False,
                }
            except Exception as exc:
                outcome["l2_pattern"] = {
                    "proposal": None,
                    "rejected": f"{type(exc).__name__}: {str(exc)[:180]}",
                    "published": False,
                }
        return outcome
    except (Exception, asyncio.CancelledError, KeyboardInterrupt) as exc:
        # A command could already be *issued* but never acknowledged. A
        # failure must retain IDs and uncertainty; do not invent OUTCOMEs.
        in_flight = supervisor.open_actions
        audit: dict[str, object] = {
            "evidence_class": "DEV_FAILED_NOT_QUALIFIED",
            "error": f"{type(exc).__name__}: {str(exc)[:500]}",
            "world_session": None if first is None else first.session_id,
            "current_intent_id": (
                None if owner.current_intent is None
                else owner.current_intent.intent_id
            ),
            "open_action_ids": [action.action_id for action in in_flight],
            "open_action_states": [action.state.value for action in in_flight],
            "action_consequence": (
                "UNKNOWN_POSSIBLY_ISSUED" if in_flight
                else "NO_PENDING_ISSUED_ACTION_AT_FAILURE"
            ),
            "native_success_claim": False,
            "original_s49_preissue_wal": "NOT_CONNECTED",
        }
        raise CognitiveWorldRunError(audit) from exc
    finally:
        if session is not None:
            try:
                await session.shutdown(timeout_s=3)
            except Exception:
                try:
                    await session.terminate()
                except Exception:
                    # Do not mask a real issuance/observation failure with
                    # a secondary shutdown/cleanup exception.
                    pass


def main() -> int:
    args = parser().parse_args()
    try:
        result = asyncio.run(run(args))
    except Exception as exc:
        payload = (
            exc.audit if isinstance(exc, CognitiveWorldRunError)
            else {
                "evidence_class": "DEV_FAILED_NOT_QUALIFIED",
                "error": f"{type(exc).__name__}: {str(exc)[:500]}",
                "native_success_claim": False,
            }
        )
        _write_evidence(args.evidence_path, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    _write_evidence(args.evidence_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
