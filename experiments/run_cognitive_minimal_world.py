"""Opt-in real llama.cpp / Mineflayer one-turn DEV runner for #828 §27.

No hidden Minecraft server start, model discovery, retry, S49 replacement,
native Action grant or automatic learning promotion. Requires a separately
running authorized local Minecraft server and llama.cpp runtime.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
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


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--grant-real-world", action="store_true")
    p.add_argument("--grant-real-llm", action="store_true")
    p.add_argument("--execute-native", action="store_true",
                   help="opt into original EAT/FIGHT physical issuer; default shadow")
    p.add_argument("--mc-host", default="127.0.0.1")
    p.add_argument("--mc-port", type=int, default=25565)
    p.add_argument("--mc-version", default="1.21.8")
    p.add_argument("--mc-username", default="RelaySelf")
    p.add_argument("--node", default="node")
    p.add_argument("--llama-endpoint", default="http://127.0.0.1:8080/v1/chat/completions")
    p.add_argument("--systemone-endpoint", help="explicit Jev-capable /v1/systemone endpoint")
    p.add_argument("--model", required=True)
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
        model=args.model,
    ))
    session: MineflayerProcessSession | None = None
    try:
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(
                host=args.mc_host, port=args.mc_port, username=args.mc_username,
                version=args.mc_version,
            ),
            node_executable=args.node, startup_timeout_s=args.startup_timeout_s,
        )
        first = await _initial_spawn(session, args.startup_timeout_s)
        owner = IntentCommitment()
        supervisor = ActionSupervisor()
        receipt = await execute_one_cognitive_world_turn(
            session, first, scenario,
            self_id=args.self_id, intent_id=args.intent_id,
            registry=initial_patterns(), relay_engine=engine, intent_owner=owner,
            supervisor=supervisor, grant_real_world=True,
            issue_native=args.execute_native,
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
            "skill_final_state": (
                None if receipt.run is None else
                receipt.run.skill_execution.state.value
            ),
            "provider_prompt_tokens": receipt.l1_result.observed_prompt_tokens,
            "provider_completion_tokens": receipt.l1_result.observed_completion_tokens,
            "self_grant_execute_native": args.execute_native,
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
    finally:
        if session is not None:
            try:
                await session.shutdown(timeout_s=3)
            except Exception:
                await session.terminate()


def main() -> int:
    args = parser().parse_args()
    try:
        result = asyncio.run(run(args))
    except Exception as exc:
        print(json.dumps({
            "evidence_class": "DEV_FAILED_NOT_QUALIFIED",
            "error": f"{type(exc).__name__}: {str(exc)[:500]}",
        }, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
