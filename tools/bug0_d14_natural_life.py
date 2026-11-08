"""D14 R4: bounded original-S49 natural-world survival reactions.

This module never stages a zombie, alters Paper physics, or issues native
effects itself. Decisions are read-only; ATTACK and EAT use the *retained*
NormalSessionActionExecutor and its pre-ISSUE persistent nonmotion fence.
Movement/STOP/Intent rearm are not silently approximated by native commands.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Callable

from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalActionStage,
    NormalAttackingAuthorization,
    NormalEatingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from relay_self.action import ActionState
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence

R4_GRANT = "D14_R4_NATURAL_S49_ONEWORLD_ONLY"
MAX_DECISIONS = 64
MAX_ACTIONS = 32
READ_TIMEOUT_S = 7


class NaturalLifeRejected(RuntimeError):
    """Source, explicit DEV grant or original physical authority was absent."""


def admissible_natural_attack(previous: Any, current: Any) -> int | None:
    """Return one stable close native zombie, not a fabricated defense grant.

    This is a conservative *precheck*. S49's own admission is mandatory.
    """
    if (
        previous.session_id != current.session_id
        or previous.seq >= current.seq
        or previous.request_id == current.request_id
        or previous.snapshot.nearby_entities_coverage.truncated
        or current.snapshot.nearby_entities_coverage.truncated
        or len(previous.snapshot.nearby_entities) != 1
        or len(current.snapshot.nearby_entities) != 1
        or previous.snapshot.health <= 0 or current.snapshot.health <= 0
        or previous.snapshot.oxygen_level == 0
        or current.snapshot.oxygen_level == 0
        or previous.snapshot.nearby_entities_coverage.candidate_count != 1
        or current.snapshot.nearby_entities_coverage.candidate_count != 1
    ):
        return None
    a = previous.snapshot.nearby_entities[0]
    b = current.snapshot.nearby_entities[0]
    if (
        a.name != "zombie" or b.name != "zombie"
        or a.entity_id != b.entity_id
        or not 0.1 <= a.distance <= 2.8
        or not 0.1 <= b.distance <= 2.8
        or any(
            abs(getattr(a.position, k) - getattr(b.position, k)) > 0.25
            or abs(getattr(previous.snapshot.position, k)
                   - getattr(current.snapshot.position, k)) > 0.05
            for k in ("x", "y", "z")
        )
    ):
        return None
    return b.entity_id


class NaturalLifeLoop:
    """One World / session / Intent / original S49 issuer; fail closed.

    A run-wide operator opt-in permits bounded attempts, but each physical
    Action still needs a fresh scoped two-stage grant and original admission.
    This is DEV operator-scoped authority, NOT proven autonomous grant origin.
    """

    def __init__(self, session: Any, evidence_dir: Path, report: dict[str, Any]) -> None:
        if os.environ.get(R4_GRANT) != "1":
            raise NaturalLifeRejected("NO_ONEWORLD_R4_PHYSICAL_GRANT")
        sid = session.started.session_id
        self.session = session
        self.sid = sid
        self.report = report
        self.intent = IntentCommitment()
        self.intent.commit(
            f"d14-natural-survival-{sid}",
            objective="stay alive and respond to observed body and world changes",
            at_ns=1,
            provenance=Provenance("d14-r4-original-s49-owner", "natural-world-intent"),
        )
        self.owner = NormalSessionActionExecutor(
            sid, self.intent, max_sequential_attacks=MAX_ACTIONS,
        )
        self.policy = S49BasicPriorityL0(sid, max_decisions=MAX_DECISIONS)
        self.nonmotion = OriginalS49NonMotionFence.create(
            evidence_dir / "original_s49_nonmotion_fence.json",
            self_id="s49-original-self",
        )
        self.cycles = 0
        self.stopped = False
        self.report.update({
            "s49_physical_issuer": "ORIGINAL_NORMAL_SESSION_ACTION_EXECUTOR",
            "original_s49_session_id": sid,
            "original_s49_intent_id": self.intent.current_intent.intent_id,
            "life_decisions": [],
            "life_action_outcomes": [],
            "new_s49_actions": 0,
            "life_stop_reason": None,
            "nonmotion_fence_path": str(self.nonmotion.path),
            "move_admission": "NOT_CONNECTED_IN_R4",
            "stop_settling": "NOT_CONNECTED_IN_R4",
            "intent_rearm": "NOT_CONNECTED_IN_R4",
            "rest_mode": "PASSIVE_INTENT_ONLY",
            "c1_intent_experiences": 0,
            "learning_updates": 0,
            "model_posts": 0,
            "skill_installs": 0,
        })

    async def _read(self, suffix: str):
        return await asyncio.wait_for(
            _correlated_observe(self.session, f"d14-r4-{self.cycles:03d}-{suffix}"),
            timeout=READ_TIMEOUT_S,
        )

    def _grant(self, kind: str, current: Any, action_id: str,
               target: int | None = None, choice: Any = None):
        common = dict(
            intent_id=self.intent.current_intent.intent_id,
            session_id=self.sid, action_id=action_id,
            probe_seq=current.seq, probe_request_id=current.request_id,
            granted=True,
        )
        result = []
        for stage in (NormalActionStage.PROPOSE, NormalActionStage.ISSUE):
            key = stage.value.lower()
            metadata = dict(
                stage=stage,
                authority_id=f"d14-r4-{kind}-{key}-{self.cycles}",
                provenance=Provenance(
                    "d14-r4-explicit-operator-dev-scope",
                    f"{kind}:{key}:{self.cycles}:{current.seq}",
                ),
            )
            if kind == "ATTACK":
                result.append(NormalAttackingAuthorization(
                    **common, **metadata, target_entity_id=target,
                ))
            elif kind == "EAT":
                result.append(NormalEatingAuthorization(
                    **common, **metadata,
                    food_item=choice.item_name, food_slot=choice.item_slot,
                ))
            else:
                raise NaturalLifeRejected("UNSUPPORTED_ORIGINAL_ACTION")
        return tuple(result)

    async def step(self, save: Callable[..., None]) -> None:
        if self.stopped or self.cycles >= MAX_DECISIONS:
            return
        if (
            self.owner.supervisor.open_actions or self.nonmotion.unresolved
            or self.owner._count >= MAX_ACTIONS
        ):
            self.stopped = True
            self.report["life_stop_reason"] = "ORIGINAL_S49_BOUND_OR_UNRESOLVED"
            return
        if self.session.process_returncode is not None:
            self.stopped = True
            self.report["life_stop_reason"] = "NATIVE_PROCESS_ENDED"
            return
        self.cycles += 1
        try:
            previous = await self._read("pre")
            current = await self._read("fresh")
        except Exception as exc:
            # A dead Self may have disconnected before the Paper terminal is
            # ingested. Do not retry an Action or erase the original death.
            self.stopped = True
            self.report["life_stop_reason"] = (
                f"NATIVE_OBSERVATION_UNAVAILABLE:{type(exc).__name__}"
            )
            save("LIFE_READBACK_FAILED", "", native={
                "cycle": self.cycles, "error_type": type(exc).__name__,
            })
            return
        if (
            previous.session_id != self.sid or current.session_id != self.sid
            or current.seq <= previous.seq
            or current.seq <= self.owner._last_issued_probe_seq
        ):
            self.stopped = True
            self.report["life_stop_reason"] = "STALE_OR_OTHER_SESSION_NATIVE"
            return

        decision = self.policy.decide(
            current,
            rest_requested=(
                not current.snapshot.nearby_entities
                and current.snapshot.food > 14
            ),
        )
        event = {
            "cycle": self.cycles, "intent_id": self.intent.current_intent.intent_id,
            "session_id": self.sid,
            "previous_seq": previous.seq, "native_seq": current.seq,
            "native_request_id": current.request_id,
            "selected": decision.selected, "preferred": decision.preferred,
            "fallback": decision.fallback, "reason": decision.reason,
            "health": current.snapshot.health, "food": current.snapshot.food,
            "zombies": [
                {"id": ent.entity_id, "distance": ent.distance}
                for ent in current.snapshot.nearby_entities if ent.name == "zombie"
            ],
            "rotten_count": sum(
                item.count for item in current.snapshot.inventory
                if item.name == "rotten_flesh"
            ),
            "source": "NATIVE_BODY_WORLD_CURRENT_NOT_GLOBAL_TRUTH",
            "action_id": None, "terminal": None,
        }
        self.report["life_decisions"].append(event)
        save("LIFE_DECISION", "", native=event)

        kind = None
        target = None
        choice = None
        if (
            decision.selected == "DEFER"
            and decision.preferred == "MOVE_AWAY"
            and decision.fallback == "ATTACK"
        ):
            target = admissible_natural_attack(previous, current)
            if target is not None:
                kind = "ATTACK"
        elif decision.selected == "EAT":
            kind = "EAT"
            choice = self.policy.food._last_decision.choice

        if kind is None:
            return
        action_id = f"d14-r4-s49-{kind.lower()}-{self.cycles}-{self.sid}"
        grants = self._grant(kind, current, action_id, target=target, choice=choice)
        try:
            if kind == "ATTACK":
                self.owner.require_attack_authorizations(
                    previous, current, target, *grants,
                )
            else:
                self.owner.require_eating_authorizations(
                    choice, current, *grants, previous_probe=previous,
                )
        except NormalActionRejected as exc:
            event["admission"] = "DEFER_ORIGINAL_S49_REFUSED"
            event["admission_type"] = type(exc).__name__
            return

        event["admission"] = "ORIGINAL_S49_GRANTED"
        event["action_id"] = action_id
        # This executes only through the original S49 issuer. The typed
        # persistent PREPARE is fsynced before supervisor ISSUE and native IO.
        try:
            if kind == "ATTACK":
                receipt = await self.owner.execute_attack(
                    self.session, previous, current, target, *grants,
                    allow_target_disappearance=True,
                    physical_fence=self.nonmotion,
                )
            else:
                receipt = await self.owner.execute_eat(
                    self.session, choice, current, *grants,
                    previous_probe=previous, physical_fence=self.nonmotion,
                )
        finally:
            self.report["new_s49_actions"] = self.owner._count
        if receipt.terminal.state is not ActionState.OUTCOME:
            raise NaturalLifeRejected("ORIGINAL_S49_ACTION_NOT_S16_OUTCOME")
        if kind == "EAT":
            self.policy.acknowledge_verified_eat(receipt)
        outcome = {
            "action_id": action_id, "kind": kind,
            "terminal": receipt.terminal.state.value,
            "session_id": self.sid,
            "native_before_seq": previous.seq,
            "native_admitted_seq": current.seq,
            "original_fence_sha256": self.nonmotion.sha256,
            "interpretation": "S16_OUTCOME_NOT_WORLD_SUCCESS_PROOF",
        }
        event["terminal"] = outcome["terminal"]
        self.report["life_action_outcomes"].append(outcome)
        save("LIFE_ACTION", "", native=outcome)

    def final_audit_fields(self) -> None:
        self.report["new_s49_actions"] = self.owner._count
        self.report["original_s49_supervisor_open"] = len(self.owner.supervisor.open_actions)
        self.report["original_s49_fence_sha256"] = self.nonmotion.sha256
        self.report["original_s49_fence_unresolved"] = self.nonmotion.unresolved
        self.report["original_s49_fence_action_ids"] = [
            a["action_id"] for a in self.nonmotion.actions
        ]
        self.report["life_decision_count"] = len(self.report["life_decisions"])
        self.report["life_outcome_count"] = len(self.report["life_action_outcomes"])
