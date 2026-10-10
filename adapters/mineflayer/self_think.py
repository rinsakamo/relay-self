"""Optional source-grounded, read-only L2 commentary for the Self demo.

Uses the existing S60-A single-lease owner and S60-B1 loopback-only HTTP
transport after a COMPLETED real S49 report.  Never maps text to an Action,
Skill result, LearningFeedback or Habit. No backend launch/STOP ACK claim.
"""
from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Mapping
from typing import Any

from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
)
from relay_self.best_effort_displacement import BestEffortDisplacement
from relay_self.interruption_fence import CognitionContext
from relay_self.provenance import Provenance

MODEL_SOURCE = "SELF_DEMO_S60B1_L2_ADVISORY"
SOURCE_WORLD = "S49_REAL_MINEFLAYER_RECEIPT"


def native_advisory_prompt(rows: tuple[dict[str, object], ...]) -> tuple[str, str, int]:
    """Minimal genuine report projection, never a simulated goal certificate."""
    if not isinstance(rows, tuple) or len(rows) != 10:
        raise ValueError("three-epoch native report trace required")
    if rows[0].get("kind") != "start" or rows[-1].get("kind") != "summary":
        raise ValueError("completed native report required")
    sid = rows[0].get("session")
    if not isinstance(sid, str) or not sid or len(sid) > 128:
        raise ValueError("source session not bounded")
    expected = (
        "start", "native_observation", "decision", "native_observation",
        "decision", "native_action_outcome", "native_observation",
        "decision", "native_action_outcome", "summary",
    )
    if tuple(r.get("kind") for r in rows) != expected:
        raise ValueError("incomplete native sequence")
    if any(r.get("source_type") != SOURCE_WORLD for r in rows):
        raise ValueError("mixed synthetic and native sources")
    if (rows[-1].get("decisions") != 3
            or rows[-1].get("native_terminal_actions") != 2
            or rows[-1].get("real_model_calls") != 0
            or rows[-1].get("in_world_learning_updates") != 0):
        raise ValueError("unqualified source-native completion")
    observations = [r for r in rows if r["kind"] == "native_observation"]
    decisions = [r for r in rows if r["kind"] == "decision"]
    outcomes = [r for r in rows if r["kind"] == "native_action_outcome"]
    if [d.get("selected") for d in decisions] != ["WAIT", "MOVE_AWAY", "MOVE_AWAY"]:
        raise ValueError("foreign native L0 decisions")
    if (any(d.get("issued_native_action") is not (i > 0)
            for i, d in enumerate(decisions))
            or any(a.get("terminal") != "outcome"
                   or a.get("world_source_session") != sid
                   or a.get("goal_success_attested") is not False
                   or a.get("signed_negative_z") is not False
                   or a.get("retained_update") is not False
                   for a in outcomes)):
        raise ValueError("native outcome cannot become goal/learning evidence")
    seqs = [o.get("probe_seq") for o in observations]
    if (any(type(s) is not int or s < 0 for s in seqs)
            or seqs != sorted(set(seqs))
            or len(seqs) != 3):
        raise ValueError("stale or duplicated observation order")
    positions = []
    for idx, (obs, decision) in enumerate(zip(observations, decisions, strict=True)):
        target_distance = obs.get("target_distance_m")
        if (obs.get("epoch") != idx+1 or decision.get("epoch") != idx+1
                or type(target_distance) not in (float, int)
                or not math.isfinite(target_distance)
                or not 0 < target_distance < 100):
            raise ValueError("source geography invalid")
        positions.append((idx+1, round(target_distance, 2), decision["selected"]))
    movements = []
    for record in outcomes:
        value = record.get("movement_m")
        if (type(value) not in (int, float) or not math.isfinite(value)
                or not 0.05 <= value <= 16):
            raise ValueError("movement receipt invalid")
        movements.append(round(value, 3))
    # No attacker-controlled free-form text from untrusted entities in this
    # short prompt; values are scalar from the verified S49 record.
    sentence = (
        "Observations in one Minecraft S49 disposable test World:\n"
        + "\n".join(
            f"epoch {epoch}: zombie distance {distance} m; L0 selected {choice}"
            for epoch, distance, choice in positions
        )
        + f"\nTwo supervised movements were observed: {movements} m.\n"
        "No goal-success, learned Habit, signed error, or in-World learning "
        "was independently demonstrated. Describe what is observed and one "
        "uncertainty in at most two concise sentences. Do NOT provide game "
        "commands or interpret this as action authorization."
    )
    return sid, sentence, seqs[-1]


async def bounded_native_commentary(
    rows: tuple[dict[str, object], ...], *, model: str, port: int,
    timeout_s: float = 12.0, max_tokens: int = 96,
) -> dict[str, Any]:
    """At most ONE pre-existing localhost model HTTP attempt, no retries.

    Failure produces an unknown commentary, never modifies original World
    report/memory or releases a claimed GPU slot/backend lease. This call is
    sequential *after* the native S49 host has completed and shut down.
    """
    sid, prompt, seq = native_advisory_prompt(rows)
    if (type(timeout_s) not in (int, float) or not math.isfinite(timeout_s)
            or not 0.5 <= timeout_s <= 30):
        raise ValueError("explicit bounded model timeout required")
    config = LoopbackTransportConfig(
        model=model, port=port, slots=1, max_tokens=max_tokens,
        connect_s=min(3.0, timeout_s),
        read_s=timeout_s, whole_s=timeout_s,
    )
    context = CognitionContext(sid, seq, 1, 1)
    p = Provenance("self-demo-l2-local-admission", f"{sid}:{seq}")
    now = time.monotonic
    model_result: str | None = None
    status = "UNCONFIRMED"
    adapter = LoopbackDisplacementAdapter(
        config,
        lambda request: {
            "model": config.model,
            "messages": [
                {"role": "system", "content": (
                    "You are a read-only observer. Do not issue actions, "
                    "claim causality or invent goal success."
                )},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": config.max_tokens,
            "stream": False,
        },
    )
    owner = BestEffortDisplacement(
        context, p.source, adapter.start, adapter.cancel, now
    )
    adapter.bind(owner)
    events: list[str] = []
    try:
        request = owner.admit(
            context, "L2", priority=1,
            deadline=now()+timeout_s,
            wait_budget=timeout_s,
            provenance=p,
        )
        owner.submit(request)
        # The S60 owner, not this app, judges completion and stale contexts.
        # Do not await a task running beyond the declared wall budget.
        stop_at = now() + timeout_s
        while now() < stop_at:
            await asyncio.sleep(0.025)
            accepted = owner.tick()
            if accepted is not None:
                value = accepted.value
                if isinstance(value, str) and 0 < len(value) <= 8192:
                    model_result = value[:1500]
                    status = "ADVISORY_ONLY"
                break
            # Provider failure remains an unconfirmed lease, not reusable.
            if any(x.event == "PROVIDER_UNCONFIRMED" for x in owner.receipts):
                break
    finally:
        events = [r.event for r in owner.receipts]
        await adapter.aclose()
    return {
        "kind": "l2_commentary",
        "source_type": MODEL_SOURCE,
        "input_world_session": sid,
        "input_world_seq": seq,
        "level": "L2",
        "model_alias_claimed": config.model,
        "provider_identity_cryptographically_verified": False,
        "status": status,
        "text_untrusted_advisory": model_result,
        "used_as_action": False,
        "authorized_actions": 0,
        "learning_feedback_created": False,
        "habit_updated": False,
        "backend_stop_ack": False,
        "gpu_release_claimed": False,
        "transport_events": events,
    }
