"""Opt-in real llama.cpp / Mineflayer one-turn DEV runner for #828 §27.

No hidden Minecraft server start, model discovery, retry, S49 replacement,
native Action grant or automatic learning promotion. Requires a separately
running authorized local Minecraft server and llama.cpp runtime.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import uuid
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
from experiments.cognitive_minimal_minecraft_dev import (
    execute_one_cognitive_world_turn,
    read_correlated_native_probe,
)
from experiments.controlled_minecraft_vertical import ControlledScenario
from experiments.cognitive_physical_eat_runner import issue_eat_from_selected_l1_dev
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import (
    MinimalCognitionError,
    initial_patterns,
    parse_l2_pattern_proposal,
    prepare_l2_pattern_request,
)
from relay_self.intent import IntentCommitment
from relay_self.relay_engine import RelayEngine


def _native_observation_record(observation: MineflayerObservation) -> dict[str, object]:
    """Complete *decoded* native facts with exact session/seq provenance.

    This is not the original adapter stdout JSON byte stream, nor an S49
    grant. Preserve all sensor fields, including unknown/null and coverage.
    """
    return {
        "evidence_format": "TYPED_DECODED_MINEFLAYER_OBSERVATION_V1",
        "native_source": observation.provenance.source,
        "native_source_ref": observation.provenance.reference,
        # Convert typed tuples to JSON arrays now, not only when the CLI
        # writes its file, so returned evidence and checkpoint compare exactly.
        "observation": json.loads(json.dumps(asdict(observation), allow_nan=False)),
    }


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
                   help="LEGACY UNFENCED DEV (not Physical ActionPort); default shadow")
    p.add_argument("--physical-eat-dev", action="store_true",
                   help="explicit single EAT parent Action via durable Physical ActionPort; "
                        "mutually exclusive with old physical issuer and shadow-only mode")
    p.add_argument("--physical-journal-path",
                   help="persistent, owned journal path; REQUIRED for physical EAT DEV")
    p.add_argument("--physical-create-journal", action="store_true",
                   help="explicitly create a NEW journal in an existing directory; "
                        "never reset an existing WAL")
    p.add_argument("--acknowledge-physical-dev-unverified-grants",
                   action="store_true",
                   help="DEV-only: caller-provided authority labels do not authenticate principal")
    p.add_argument("--physical-propose-authority",
                   help="explicit operator supplied PROPOSE authority label")
    p.add_argument("--physical-issue-authority",
                   help="explicit distinct operator supplied ISSUE authority label")
    p.add_argument("--s49-readonly-shadow", action="store_true",
                   help="two post-L1 native probes and S49-like Target precheck; "
                        "never issue an Action or grant S49 authority")
    p.add_argument("--pre-l1-native-probe", action="store_true",
                   help="with read-only shadow or EAT DEV: use fresh correlated "
                        "native probe (not spawn) as L1 starting observation")
    p.add_argument("--pre-l1-wait-s", type=float, default=0,
                   help="0..60 seconds after native spawn for controlled DEV "
                        "World setup before the pre-L1 probe; no effects issued")
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
    if args.s49_readonly_shadow and (args.execute_native or args.physical_eat_dev):
        raise MinimalCognitionError(
            "explicit S49 shadow-only mode cannot issue any physical Action"
        )
    if args.physical_eat_dev and args.execute_native:
        raise MinimalCognitionError(
            "two physical issuers cannot coexist: legacy unfenced vs durable EAT"
        )
    if args.pre_l1_native_probe and (
        not (args.s49_readonly_shadow or args.physical_eat_dev)
        or args.execute_native
    ):
        raise MinimalCognitionError(
            "pre-L1 native probe requires read-only shadow or durable EAT DEV"
        )
    if args.physical_eat_dev:
        if (
            not args.physical_journal_path
            or not args.acknowledge_physical_dev_unverified_grants
            or not args.physical_propose_authority
            or not args.physical_issue_authority
            or args.physical_propose_authority == args.physical_issue_authority
            or args.acknowledge_unfenced_dev
        ):
            raise MinimalCognitionError(
                "physical EAT DEV requires durable WAL, two distinct external "
                "authority labels and explicit unauthenticated-grants acknowledgement"
            )
    elif (
        args.physical_journal_path is not None
        or args.physical_create_journal
        or args.acknowledge_physical_dev_unverified_grants
        or args.physical_propose_authority is not None
        or args.physical_issue_authority is not None
    ):
        raise MinimalCognitionError(
            "physical EAT journal and authority options require --physical-eat-dev"
        )
    if (not math.isfinite(args.pre_l1_wait_s)
            or not 0 <= args.pre_l1_wait_s <= 60
            or (args.pre_l1_wait_s > 0 and not args.pre_l1_native_probe)):
        raise MinimalCognitionError(
            "pre-L1 World setup wait requires read-only probe and 0..60 seconds"
        )
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
    physical_journal: PhysicalActionJournal | None = None
    physical_eat = None
    first: MineflayerObservation | None = None
    spawn: MineflayerObservation | None = None
    pre_l1_probe_diagnostics: dict[str, object] | None = None
    owner = IntentCommitment()
    supervisor = ActionSupervisor()
    try:
        if args.physical_eat_dev:
            # A journal from a previous session is never silently reseeded.
            # Check STOP/UNKNOWN before World connect or GPU inference.
            physical_journal = (
                PhysicalActionJournal.create(
                    args.physical_journal_path, self_id=args.self_id,
                ) if args.physical_create_journal else
                PhysicalActionJournal.restore(
                    args.physical_journal_path, self_id=args.self_id,
                )
            )
            physical_journal.require_clear()
        session = await MineflayerProcessSession.launch(
            MineflayerLaunchConfig(
                host=args.mc_host, port=args.mc_port, username=args.mc_username,
                version=args.mc_version,
            ),
            node_executable=args.node, startup_timeout_s=args.startup_timeout_s,
        )
        spawn = await _initial_spawn(session, args.startup_timeout_s)
        first = spawn
        # Before any GPU inference, persist source-qualified initial native
        # facts. A handled failure includes this in final audit, while an
        # interrupted process can leave this checkpoint as partial evidence.
        _write_evidence(args.evidence_path, {
            "evidence_class": "DEV_INITIAL_NATIVE_CHECKPOINT",
            "stage": "INITIAL_NATIVE_OBSERVED_BEFORE_L1",
            "native_success_claim": False,
            "physical_action_issued": False,
            "original_s49_preissue_wal": "NOT_CONNECTED",
            "world_session": first.session_id,
            "initial_native_observation": _native_observation_record(first),
            "spawn_native_observation": _native_observation_record(spawn),
            "pre_l1_probe_requested": args.pre_l1_native_probe,
            "scenario_inputs": {
                "edible_item_names": list(scenario.edible_item_names),
                "hazard_entity_names": sorted(scenario.hazard_entity_names),
                "fight_max_distance": scenario.fight_max_distance,
                "food_threshold": scenario.food_threshold,
            },
        })
        if args.pre_l1_native_probe:
            # The isolated test World may be configured by its **server**
            # owner after the player spawns; never make World changes here.
            # The actual cognition input is a fresh correlated, post-setup
            # native fact, not the possibly early spawn inventory snapshot.
            if args.pre_l1_wait_s:
                await asyncio.sleep(args.pre_l1_wait_s)
            probe_id = f"cognitive-pre-l1-{uuid.uuid4().hex}"
            pre_l1_probe_diagnostics = {
                "request_id": probe_id,
                "stage": "PRE_L1_PROBE_REQUEST_PREPARED",
                "receive_limit": 4096,
            }
            _write_evidence(args.evidence_path, {
                "evidence_class": "DEV_INITIAL_NATIVE_CHECKPOINT",
                "stage": "PRE_L1_PROBE_REQUEST_PREPARED",
                "native_success_claim": False,
                "physical_action_issued": False,
                "world_session": spawn.session_id,
                "spawn_native_observation": _native_observation_record(spawn),
                "pre_l1_probe_diagnostics": pre_l1_probe_diagnostics,
                "original_s49_preissue_wal": "NOT_CONNECTED",
            })
            # The post-spawn 0..60s wait may queue many passive native move/
            # inventory events. Use an enlarged but strictly bounded budget
            # ONLY here. Post-L1 shadow still uses its strict 32-event budget.
            first = await read_correlated_native_probe(
                session, spawn, scenario,
                request_id=probe_id, max_messages=4096,
                diagnostics=pre_l1_probe_diagnostics,
            )
            _write_evidence(args.evidence_path, {
                "evidence_class": "DEV_INITIAL_NATIVE_CHECKPOINT",
                "stage": "PRE_L1_NATIVE_PROBE_OBSERVED_BEFORE_L1",
                "native_success_claim": False,
                "physical_action_issued": False,
                "original_s49_preissue_wal": "NOT_CONNECTED",
                "world_session": first.session_id,
                "spawn_native_observation": _native_observation_record(spawn),
                "initial_native_observation": _native_observation_record(first),
                "pre_l1_probe_requested": True,
                "pre_l1_probe_diagnostics": pre_l1_probe_diagnostics,
                "pre_l1_wait_s": args.pre_l1_wait_s,
                "scenario_inputs": {
                    "edible_item_names": list(scenario.edible_item_names),
                    "hazard_entity_names": sorted(scenario.hazard_entity_names),
                    "fight_max_distance": scenario.fight_max_distance,
                    "food_threshold": scenario.food_threshold,
                },
            })
        receipt = await execute_one_cognitive_world_turn(
            session, first, scenario,
            self_id=args.self_id, intent_id=args.intent_id,
            registry=initial_patterns(), relay_engine=engine, intent_owner=owner,
            supervisor=supervisor, grant_real_world=True,
            issue_native=args.execute_native,
            acknowledge_unfenced_dev=args.acknowledge_unfenced_dev,
            # Pre-issue two-probe evidence is read-only; the physical EAT
            # route is a separate, explicitly granted single ActionPort.
            s49_readonly_shadow=(args.s49_readonly_shadow or args.physical_eat_dev),
        )
        if (
            args.physical_eat_dev
            and receipt.status == "S49_SHADOW_READY"
            and receipt.selection.option is not None
            and receipt.selection.option.skill_id == "EAT"
        ):
            assert physical_journal is not None
            physical_eat = await issue_eat_from_selected_l1_dev(
                session, receipt,
                intent_owner=owner, supervisor=supervisor,
                journal=physical_journal, self_id=args.self_id,
                intent_id=args.intent_id,
                propose_authority_id=args.physical_propose_authority,
                issue_authority_id=args.physical_issue_authority,
                dev_physical_grant=True,
                acknowledge_unverified_principal=(
                    args.acknowledge_physical_dev_unverified_grants
                ),
            )
        supervised_actions = (
            supervisor.recorded_actions if args.physical_eat_dev
            else (() if receipt.run is None else receipt.run.actions)
        )
        issued_at = next(
            (event.at_ns for action in supervised_actions
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
            "existing_issuer": (
                "cognitive_physical_eat_runner.issue_eat_from_selected_l1_dev"
                if args.physical_eat_dev else
                "controlled_minecraft_vertical.execute_decision"
            ),
            "model_declared": args.model,
            "systemone_backend": bool(args.systemone_endpoint),
            "world_session": first.session_id,
            "initial_native_observation": _native_observation_record(first),
            "spawn_native_observation": _native_observation_record(spawn),
            "pre_l1_probe_requested": args.pre_l1_native_probe,
            "pre_l1_probe_diagnostics": pre_l1_probe_diagnostics,
            "pre_l1_wait_s": args.pre_l1_wait_s,
            "initial_schema_frame": asdict(receipt.initial_frame),
            "current_schema_frame": (
                None if receipt.current_frame is None
                else asdict(receipt.current_frame)
            ),
            "native_probe_trace": [
                _native_observation_record(obs) for obs in receipt.native_probe_trace
            ],
            "scenario_inputs": {
                "edible_item_names": list(scenario.edible_item_names),
                "hazard_entity_names": sorted(scenario.hazard_entity_names),
                "fight_max_distance": scenario.fight_max_distance,
                "food_threshold": scenario.food_threshold,
            },
            "status": (
                "NATIVE_EAT_OUTCOME_DEV_ONLY" if physical_eat is not None
                else receipt.status
            ),
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
            "correlated_probe_request_id": receipt.probe_request_id,
            "correlated_probe_seq": receipt.probe_sequence,
            "s49_readonly_handoff": (
                None if receipt.s49_readonly_handoff is None
                else asdict(receipt.s49_readonly_handoff)
            ),
            "s49_shadow_refusal": receipt.s49_shadow_refusal,
            "selected": (None if receipt.selection.option is None
                         else asdict(receipt.selection.option)),
            "selection_reason": receipt.selection.reason,
            "action_outcome_count": (
                1 if physical_eat is not None else receipt.actual_action_outcomes
            ),
            "native_eat_consequence_attested": (
                True if physical_eat is not None
                else receipt.native_eat_consequence_attested
            ),
            "physical_eat_dev_selected": args.physical_eat_dev,
            "physical_eat_parent_action_id": (
                None if physical_eat is None else physical_eat.action_id
            ),
            "physical_journal_path": args.physical_journal_path,
            "physical_journal_unresolved": (
                None if physical_journal is None else physical_journal.unresolved
            ),
            "physical_journal_records": (
                [] if physical_journal is None else physical_journal.records
            ),
            "native_actions": (
                [{"action_id": a.action_id, "state": a.state.value}
                 for a in supervised_actions]
            ),
            "native_effect_receipts": (
                ([
                    {"action_id": m.action_id, "result": m.result,
                     "effect": m.effect, "source_ref": m.provenance.reference}
                    for m in (physical_eat.action.equip, physical_eat.action.consume)
                ] if physical_eat is not None else
                [] if receipt.run is None else [
                    {"action_id": message.action_id, "result": message.result,
                     "effect": message.effect, "source_ref": message.provenance.reference}
                    for message in receipt.run.messages
                    if isinstance(message, MineflayerEffectResult)
                ])
            ),
            "skill_final_state": (
                "started" if physical_eat is not None else
                None if receipt.run is None else
                receipt.run.skill_execution.state.value
            ),
            "provider_prompt_tokens": receipt.l1_result.observed_prompt_tokens,
            "provider_completion_tokens": receipt.l1_result.observed_completion_tokens,
            "separate_prefill_decode_timing": "NOT_MEASURED",
            "gpu_preemption": "NOT_MEASURED",
            "self_grant_execute_native": args.execute_native,
            "physical_fence": (
                "PREISSUE_WAL_EAT_DEV" if physical_eat is not None else
                "WAL_READY_NO_ISSUE" if args.physical_eat_dev else
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
        history = supervisor.recorded_actions
        audit: dict[str, object] = {
            "evidence_class": "DEV_FAILED_NOT_QUALIFIED",
            "error": f"{type(exc).__name__}: {str(exc)[:500]}",
            "world_session": None if first is None else first.session_id,
            "initial_native_observation": (
                None if first is None else _native_observation_record(first)
            ),
            "spawn_native_observation": (
                None if spawn is None else _native_observation_record(spawn)
            ),
            "pre_l1_probe_requested": args.pre_l1_native_probe,
            "pre_l1_probe_diagnostics": pre_l1_probe_diagnostics,
            "physical_eat_dev_selected": args.physical_eat_dev,
            "physical_journal_path": args.physical_journal_path,
            "physical_journal_unresolved": (
                None if physical_journal is None else physical_journal.unresolved
            ),
            "physical_journal_records": (
                [] if physical_journal is None else physical_journal.records
            ),
            "current_intent_id": (
                None if owner.current_intent is None
                else owner.current_intent.intent_id
            ),
            "open_action_ids": [action.action_id for action in in_flight],
            "open_action_states": [action.state.value for action in in_flight],
            "recorded_actions": [
                {"action_id": action.action_id, "state": action.state.value}
                for action in history
            ],
            "action_consequence": (
                "UNKNOWN_POSSIBLY_ISSUED" if (
                    in_flight or (
                        physical_journal is not None and physical_journal.unresolved
                    )
                ) else "PRIOR_EFFECTS_REQUIRE_REVIEW" if history
                else "NO_SUPERVISED_ISSUE_RECORDED"
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
