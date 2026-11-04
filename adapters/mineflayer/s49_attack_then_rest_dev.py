"""Bug-0 original S49 one native ATTACK followed by REST intent (DEV).

This joins *two previously tested* S49 flows in one original session/owner:
one issuer-bound ATTACK and a subsequent non-Action REST observation.
It NEVER admits P1 fatigue recovery from position snapshots or from an
attack ACK, even when the Paper zombie Health difference is observed.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.s31a_real_server_ci import _command, _correlated_observe
from adapters.mineflayer.s49_attack_dev import run_s49_attack_dev
from adapters.mineflayer.s49_attack_server_health import TARGET_TAG
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from adapters.mineflayer.s49_rest_dev import inspect_rest_native_samples
from relay_self.action import ActionState


class S49AttackRestDevRejected(RuntimeError):
    """The original one-Action-to-REST sequence was not source-qualified."""


async def run_s49_attack_then_rest_dev(
    session: MineflayerProcessSession, server: object,
    owner: NormalSessionActionExecutor, report: dict[str, Any],
    *, health_log: Path,
) -> None:
    if (
        not isinstance(session, MineflayerProcessSession)
        or not isinstance(owner, NormalSessionActionExecutor)
        or session.started.session_id != owner.session_id
        or getattr(server, "stdin", None) is None
        or session.process_returncode is not None
        or not isinstance(health_log, Path)
        or owner._count != 0
        or owner._dispatched
        or owner.supervisor.open_actions
        or owner._post_move_settling_unqualified
        or owner.intent.current_intent is None
        or owner.intent.current_intent.intent_id != "escape-threat"
    ):
        raise S49AttackRestDevRejected("fresh original S49 ATTACK owner required")
    sid = owner.session_id
    report["stage"] = "BUG0_ATTACK_THEN_REST_ORIGINAL_S49"
    report["rest_intent_selected"] = False
    report["rest_action_issued"] = False
    report["p1_fatigue_recovery_attested"] = False
    report["p1_owner_integrated"] = False

    # Existing one-shot original S49 ATTACK, including separately bracketed
    # read-only Paper before/after Health. No second ATTACK on any failure.
    attack_receipt = await run_s49_attack_dev(
        session, server, owner, report, health_log=health_log,
    )
    if (
        attack_receipt.terminal.state is not ActionState.OUTCOME
        or owner._count != 1
        or len(owner._dispatched) != 1
        or owner.supervisor.open_actions
        or len(report.get("actual_native_actions", ())) != 1
        or report["actual_native_actions"][0].get("kind") != "ATTACK"
    ):
        raise S49AttackRestDevRejected("ATTACK did not close within original S49")
    report["attack_rest_link"] = {
        "action_id": attack_receipt.terminal.action_id,
        "attack_effect_seq": attack_receipt.effect.seq,
        "attack_after_probe_seq": attack_receipt.after_probe.seq,
        "action_terminal": attack_receipt.terminal.state.value,
        "fight_event_p1_attested": False,
        "p1_fight_tick_source": None,
    }
    # Independent operator staging: the original target is removed after
    # the one ATTACK terminal; not a new Self Action nor a defense claim.
    # Prefer removing ONLY the uniquely tagged staging target.
    command = f"kill @e[type=minecraft:zombie,tag={TARGET_TAG}]"
    _command(server, command)
    report.setdefault("operator_world_commands", []).append(command)
    await server.stdin.drain()
    await asyncio.sleep(2.0)

    first = await _correlated_observe(
        session, f"s49-attack-rest-{sid}-baseline",
    )
    policy = S49BasicPriorityL0(sid, max_decisions=12)
    choice = policy.decide(first, rest_requested=True)
    report["rest_choice"] = {
        "selected": choice.selected,
        "preferred": choice.preferred,
        "reason": choice.reason,
        "probe_seq": choice.probe_seq,
        "native_source_ref": first.provenance.reference,
        "action_issued": choice.action_issued,
        "permission_granted": choice.permission_granted,
    }
    if (
        choice.selected != "REST"
        or choice.preferred != "REST"
        or choice.action_issued or choice.permission_granted
        or first.seq <= attack_receipt.after_probe.seq
        or owner._count != 1 or owner.supervisor.open_actions
    ):
        raise S49AttackRestDevRejected(
            "post-ATTACK original native L0 REST intent not admitted"
        )
    report["rest_intent_selected"] = True
    report["stage"] = "BUG0_POST_ATTACK_REST_NATIVE_STATIONARY_SAMPLES"
    observations = [first]
    for index in range(8):
        await asyncio.sleep(0.4)
        observations.append(await _correlated_observe(
            session, f"s49-attack-rest-{sid}-{index:02d}",
        ))
    result = inspect_rest_native_samples(observations, session_id=sid)
    report["rest_observation"] = result
    report["attack_rest_link"]["rest_baseline_probe_seq"] = first.seq
    report["attack_rest_link"]["rest_last_probe_seq"] = observations[-1].seq
    if (
        owner._count != 1
        or len(owner._dispatched) != 1
        or owner.supervisor.open_actions
        or not result["native_stationary_sample_candidate"]
    ):
        raise S49AttackRestDevRejected(
            "post-ATTACK native REST observation changed original Action owner"
        )
    # The original P1 evaluator is a distinct unmerged owner. Source-less
    # simulated World ticks and ATTACK command ACK are NEVER fed to P1 as
    # authenticated physical WAIT/FIGHT frames.
    report["p1_scope"] = {
        "original_p1_owner": "research/p1-fatigue-body-20261016",
        "native_attack_command_attested": True,
        "paper_server_health_drop_observed": report.get(
            "attack_server_health_drop_observed", False,
        ),
        "physical_p1_fight_tick_attested": False,
        "physical_p1_wait_ticks_attested": 0,
        "p1_fatigue_before": None,
        "p1_fatigue_after": None,
        "p1_fatigue_recovery_attested": False,
        "p1_model_preview_allowed_offline_only": True,
        "m_basal_cost_waived": False,
        "source_independently_attested": False,
    }
    report["stage"] = "BUG0_ATTACK_THEN_REST_NATIVE_SAMPLES_CLOSED"
