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

from adapters.mineflayer.attack_execution import AttackActionReceipt
from adapters.mineflayer.eat_execution import EatingActionReceipt
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalActionStage,
    NormalAttackingAuthorization,
    NormalEatingAuthorization,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from adapters.mineflayer.s49_basic_priority_l0 import S49BasicPriorityL0
from adapters.mineflayer.s49_reactive_defense import evaluate_native_damage_defense
from relay_self.action import ActionState
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d14_natural_motion import NaturalOriginalS49Motion

R4_GRANT = "D14_R4_NATURAL_S49_ONEWORLD_ONLY"
R6_GRANT = "D14_R6_NATURAL_MOTION_ONEWORLD_ONLY"
R9_COMBAT_GRANT = "D14_R9_COMBAT_FIRST_ONEWORLD_ONLY"
F1_DEFENSE_GRANT = "D14_F1_REACTIVE_DEFENSE_ONEWORLD_ONLY"
MAX_DECISIONS = 1024
R11_MAX_DECISIONS = 4096  # Read-only observation capacity; S49 Action budget unchanged.
R11_DAY_GRANT = "D14_R11_NATURAL_DAY_ONEWORLD_ONLY"
POLICY_EPOCH_DECISIONS = 64
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
        self.combat_first = os.environ.get(R9_COMBAT_GRANT) == "1"
        self.r11_day = os.environ.get(R11_DAY_GRANT) == "1"
        self.defense_f1 = os.environ.get(F1_DEFENSE_GRANT) == "1"
        self._defense_last_native = None
        self.decision_limit = R11_MAX_DECISIONS if self.r11_day else MAX_DECISIONS
        self._r11_last_rotten_inventory_count: int | None = None
        if self.combat_first and any(os.environ.get(key) != "1" for key in (
            "D14_R5_LOCAL_ONEWORLD_ONLY", R6_GRANT,
            "D14_R7_NATIVE_EVIDENCE_ONEWORLD_ONLY",
            "D7_PASSIVE_CONTROLS_WORLD_ONLY",
        )):
            raise NaturalLifeRejected("R9_COMBAT_REQUIRES_R5_R6_R7_S50_GRANTS")
        if self.r11_day and (
            not self.combat_first
            or os.environ.get("D14_R10_INITIAL_STONE_SWORD_ONEWORLD_ONLY") != "1"
        ):
            raise NaturalLifeRejected("R11_DAY_REQUIRES_R10_R9_NATIVE_OWNER")
        if self.defense_f1 and (
            not self.r11_day or not self.combat_first
            or os.environ.get("D14_R10_INITIAL_STONE_SWORD_ONEWORLD_ONLY") != "1"
        ):
            raise NaturalLifeRejected("F1_DEFENSE_REQUIRES_R11_R10_R9_OWNER_GRANTS")
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
            dev_reactive_defense_source=self.defense_f1,
        )
        self.policy = S49BasicPriorityL0(sid, max_decisions=POLICY_EPOCH_DECISIONS)
        self.nonmotion = OriginalS49NonMotionFence.create(
            evidence_dir / "original_s49_nonmotion_fence.json",
            self_id="s49-original-self",
        )
        # R4/R5 are unchanged without a SEPARATE R6 local-only grant.
        if os.environ.get(R6_GRANT) == "1":
            if os.environ.get("D14_R5_LOCAL_ONEWORLD_ONLY") != "1":
                raise NaturalLifeRejected("R6_MOTION_REQUIRES_EXPLICIT_LOCAL_R5_GRANT")
            self.motion = NaturalOriginalS49Motion(
                sid, self.intent, self.owner, evidence_dir,
            )
        else:
            self.motion = None
        self.cycles = 0
        self._last_policy_rotation_cycle = 0
        self.stopped = False
        self.report.update({
            "s49_physical_issuer": "ORIGINAL_NORMAL_SESSION_ACTION_EXECUTOR",
            "r9_combat_first_opt_in": self.combat_first,
            "f1_reactive_defense_opt_in": self.defense_f1,
            "f1_reactive_defense_actions": 0,
            "r11_natural_day_opt_in": self.r11_day,
            "r11_l0_decision_resource_limit": self.decision_limit,
            "r11_item_seek_action_authorized": False,
            "original_s49_session_id": sid,
            "original_s49_intent_id": self.intent.current_intent.intent_id,
            "life_decisions": [],
            "life_action_outcomes": [],
            "life_unresolved_actions": [],
            "life_policy_epochs": 1,
            "new_s49_actions": 0,
            "life_stop_reason": None,
            "nonmotion_fence_path": str(self.nonmotion.path),
            "move_admission": (
                "R6_ORIGINAL_S49_NATIVE_ENTITIES_S14_DURABLE_FENCE"
                if self.motion is not None else "NOT_CONNECTED_IN_R4"
            ),
            "stop_settling": (
                "R6_S15_CLEAR_ACK_ONLY_PHYSICAL_STOP_UNATTESTED"
                if self.motion is not None else "NOT_CONNECTED_IN_R4"
            ),
            "intent_rearm": "NOT_CONNECTED_IN_R4",
            "rest_mode": "PASSIVE_INTENT_ONLY",
            "c1_intent_experiences": 0,
            "learning_updates": 0,
            "model_posts": 0,
            "skill_installs": 0,
        })

    def capture_native_event(self, frame: Any) -> None:
        if self.motion is not None:
            self.motion.capture_event(frame)

    async def _read(self, suffix: str):
        return await asyncio.wait_for(
            _correlated_observe(
                self.session, f"d14-r4-{self.cycles:03d}-{suffix}",
                on_entity_event=(
                    self.capture_native_event if self.motion is not None else None
                ),
            ),
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

    def stop_due_to_native_loss(self, reason: str) -> None:
        """Fail closed for L0/Action, while Paper may finish autonomously."""
        if (
            self.owner.supervisor.open_actions or self.nonmotion.unresolved
            or (self.motion is not None and self.motion.fence.unresolved)
            or not isinstance(reason, str) or not reason
        ):
            raise NaturalLifeRejected("UNRESOLVED_ACTION_OR_BAD_NATIVE_LOSS")
        self.stopped = True
        self.report["life_stop_reason"] = reason

    def _rotate_native_cursor(self) -> None:
        """Rotate read-only bounded L0 policy, never S49 Action or Intent."""
        if (
            self.cycles > 0
            and self.cycles % POLICY_EPOCH_DECISIONS == 0
            and self._last_policy_rotation_cycle != self.cycles
        ):
            self._last_policy_rotation_cycle = self.cycles
            self.policy = S49BasicPriorityL0(
                self.sid, max_decisions=POLICY_EPOCH_DECISIONS,
            )
            self.report["life_policy_epochs"] += 1

    async def step(self, save: Callable[..., None]) -> None:
        if self.stopped:
            return
        if self.cycles >= self.decision_limit:
            self.stopped = True
            self.report["life_stop_reason"] = "L0_TOTAL_DECISION_RESOURCE_LIMIT"
            return
        if (
            self.owner.supervisor.open_actions or self.nonmotion.unresolved
            or (self.motion is not None and self.motion.fence.unresolved)
            or self.owner._count >= MAX_ACTIONS
        ):
            self.stopped = True
            self.report["life_stop_reason"] = "ORIGINAL_S49_BOUND_OR_UNRESOLVED"
            return
        if self.session.process_returncode is not None:
            self.stopped = True
            self.report["life_stop_reason"] = "NATIVE_PROCESS_ENDED"
            return
        self._rotate_native_cursor()
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

        # Maintain exactly one prior fresh native probe across cycles.
        # Never preserve a damage candidate beyond this single decision:
        # there is no replay or persistent new Action grant.
        reactive = None
        f1_reason = "F1_NOT_ENABLED"
        if self.defense_f1:
            sources = (previous, self._defense_last_native)
            refusals = []
            for witness in sources:
                candidate, reason = evaluate_native_damage_defense(
                    previous, current, witness,
                )
                if candidate is not None:
                    reactive, f1_reason = candidate, reason
                    break
                refusals.append(reason)
            if reactive is None:
                f1_reason = "/".join(refusals)
        self._defense_last_native = current

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
            "r10_native_stone_sword_inventory_slots": sorted(
                item.slot for item in current.snapshot.inventory
                if item.name == "stone_sword" and item.count == 1
            ),
            "source": "NATIVE_BODY_WORLD_CURRENT_NOT_GLOBAL_TRUTH",
            "action_id": None, "terminal": None,
        }
        if self.defense_f1:
            event["f1_source_candidate_reason"] = f1_reason
            event["f1_native_health_loss"] = (
                reactive.health_loss if reactive is not None else None
            )
            event["f1_native_witness_seq"] = (
                reactive.witness.seq if reactive is not None else None
            )
            event["f1_causal_zombie_damage_attested"] = False
        if self.r11_day:
            # Only native observations enter the Self-side readout. Paper
            # global loot source must NEVER be projected as a Self Goal or
            # used to mint a new S49 item-directed MOVE.
            nearby_untyped_items = [
                {"entity_id": ent.entity_id, "distance": ent.distance}
                for ent in current.snapshot.nearby_entities
                if ent.name in ("item", "dropped_item")
                or ent.entity_type == "item"
            ]
            event["r11_native_dropped_item_candidates"] = nearby_untyped_items
            event["r11_item_type_from_native"] = "UNKNOWN"
            event["r11_item_approach_authorization"] = "NOT_CONNECTED"
            current_rotten = event["rotten_count"]
            prior_rotten = self._r11_last_rotten_inventory_count
            event["r11_native_rotten_inventory_delta_since_last_decision"] = (
                current_rotten - prior_rotten if prior_rotten is not None else None
            )
            self._r11_last_rotten_inventory_count = current_rotten
        if self.r11_day and (
            previous.snapshot.oxygen_level is None
            or current.snapshot.oxygen_level is None
        ):
            # A raw Mineflayer oxygen=-1 is a *missing* breath reading,
            # not proof of oxygen=0 or full breathing. Keep live readback
            # and genuine World sampling, but do not mint S49 Action grants.
            event["r12_oxygen_observed"] = False
            event["r12_action_admission"] = (
                "DEFER_UNKNOWN_OXYGEN_NO_PHYSICAL_ISSUE"
            )
            self.report["life_decisions"].append(event)
            save("LIFE_DECISION", "", native=event)
            return
        self.report["life_decisions"].append(event)
        save("LIFE_DECISION", "", native=event)

        kind = None
        target = None
        choice = None
        reactive_source = None
        if (
            decision.selected == "DEFER"
            and decision.preferred == "MOVE_AWAY"
            and decision.fallback == "ATTACK"
        ):
            # R9 is a separate DEV opt-in. A stable, close, same-ID native
            # zombie is eligible for original S49 ATTACK BEFORE any MOVE;
            # otherwise the original R6 MOVE admission remains unchanged.
            # In particular, do not lift the original post-MOVE STOP fence.
            attack_target = admissible_natural_attack(previous, current)
            if (
                self.combat_first
                and attack_target is not None
                and not self.owner._post_move_settling_unqualified
            ):
                kind = "ATTACK"
                target = attack_target
                event["r9_priority"] = "ATTACK_BEFORE_MOVE_NATIVE_PAIR"
            elif (
                self.combat_first and self.defense_f1
                and reactive is not None
                and not self.owner._post_move_settling_unqualified
            ):
                kind = "ATTACK"
                target = reactive.target_entity_id
                reactive_source = reactive
                event["f1_admission"] = (
                    "REACTIVE_HEALTH_LOSS_NATIVE_PAIR_ORIGINAL_S49"
                )
                event["r9_priority"] = "F1_REACTIVE_ATTACK_BEFORE_MOVE"
            elif (
                self.combat_first
                and not self.owner._post_move_settling_unqualified
            ):
                # A zombie at 2.8–4m can approach naturally. Issuing MOVE
                # here would make the later close-range ATTACK ineligible
                # until independent Paper-effective STOP, which R9 cannot
                # prove. WAIT adds no issuer, native effect or fake clearance.
                event["r9_priority"] = "WAIT_FOR_NATIVE_ATTACK_ADMISSION"
            # Legacy R6 MOVE remains available with R9 disabled; it still
            # requires a real unsolicited entities frame and frozen S14.
            elif self.motion is not None:
                native_event = self.motion.current_candidate(current)
                if native_event is not None:
                    event["admission"] = "R6_ORIGINAL_S49_MOVE_SELECTED"
                    event["action_id"] = (
                        f"d14-r6-s49-move-{self.cycles}-{self.sid}"
                    )
                    self.motion.last_receipt_diagnostic = None
                    try:
                        outcome = await self.motion.issue_original_move(
                            self.session, native_event, current, cycle=self.cycles,
                        )
                    except BaseException as exc:
                        # Never recover, reissue or assert a terminal Outcome.
                        # Preserve the exact original supervisor state when one
                        # exists, plus the original partial S16 receipt.
                        try:
                            s49_state = self.owner.supervisor.get(
                                event["action_id"]
                            ).state.value
                        except (KeyError, ValueError):
                            s49_state = None
                        unresolved = {
                            "cycle": self.cycles,
                            "action_id": event["action_id"],
                            "session_id": self.sid,
                            "intent_id": self.intent.current_intent.intent_id,
                            "native_event_seq": native_event.seq,
                            "native_admitted_seq": current.seq,
                            "error_type": type(exc).__name__,
                            "error_detail": str(exc)[:512],
                            "original_s49_supervisor_state": s49_state,
                            "original_move_fence_unresolved": (
                                self.motion.fence.unresolved
                            ),
                            "original_move_fence_sha256": self.motion.fence.sha256,
                            "original_s16_receipt": (
                                self.motion.last_receipt_diagnostic
                            ),
                            "interpretation": (
                                "UNRESOLVED_NOT_DISPATCH_OR_STOP_PROOF"
                            ),
                        }
                        self.report["life_unresolved_actions"].append(unresolved)
                        save("LIFE_ACTION_UNRESOLVED", "", native=unresolved)
                        raise
                    finally:
                        self.report["new_s49_actions"] = self.owner._count
                    event["terminal"] = outcome["terminal"]
                    self.report["life_action_outcomes"].append(outcome)
                    save("LIFE_ACTION", "", native=outcome)
                    return
            if kind is None:
                target = attack_target
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
                if reactive_source is not None:
                    self.owner.require_attack_authorizations(
                        previous, current, target, *grants,
                        reactive_damage_source=reactive_source,
                    )
                else:
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
                    **({"reactive_damage_source": reactive_source}
                       if reactive_source is not None else {}),
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
        if kind == "ATTACK" and isinstance(receipt, AttackActionReceipt):
            # Native effect / event claims are NOT Paper health/death or
            # damage attribution. Preserve exactly what the S49 owner saw.
            outcome.update({
                "original_s49_native_attack_ack_seq": receipt.effect.seq,
                "original_s49_native_attack_ack_result": receipt.effect.result,
                "native_target_entity_id": receipt.target_entity_id,
                "native_target_hurt_event_seen": receipt.observed_target_hurt,
                "native_target_missing_after": receipt.target_missing_in_native_view,
                "damage_attested": False,
                "zombie_kill_attested": False,
            })
        elif kind == "EAT" and isinstance(receipt, EatingActionReceipt):
            # Verified S51 food+inventory deltas, not nutrition or C1 credit.
            outcome.update({
                "original_s51_food_before": receipt.outcome.food_before,
                "original_s51_food_after": receipt.outcome.food_after,
                "original_s51_consumed_item": receipt.outcome.consumed_item,
                "original_s51_inventory_before": receipt.outcome.count_before,
                "original_s51_inventory_after": receipt.outcome.count_after,
                "original_s51_after_probe_seq": receipt.outcome.after_probe_seq,
            })
        event["terminal"] = outcome["terminal"]
        if reactive_source is not None:
            outcome["f1_reactive_damage_source"] = (
                "NATIVE_HEALTH_DROP_NEAR_ZOMBIE_NOT_CAUSAL_PROOF"
            )
            outcome["f1_reactive_witness_seq"] = reactive_source.witness.seq
            outcome["f1_native_health_loss"] = reactive_source.health_loss
            self.report["f1_reactive_defense_actions"] += 1
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
        if self.motion is not None:
            self.report["original_s49_move_fence_sha256"] = self.motion.fence.sha256
            self.report["original_s49_move_fence_unresolved"] = (
                self.motion.fence.unresolved
            )
            self.report["original_s49_move_fence_action_ids"] = [
                a["action_id"] for a in self.motion.fence.actions
            ]
            self.report["r6_native_entities_event_count"] = (
                self.motion.seen_event_frames
            )
            self.report["original_s49_post_move_settling_unqualified"] = (
                self.owner._post_move_settling_unqualified
            )
        self.report["life_decision_count"] = len(self.report["life_decisions"])
        self.report["life_outcome_count"] = len(self.report["life_action_outcomes"])
