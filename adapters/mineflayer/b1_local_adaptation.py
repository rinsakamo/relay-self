"""B1 DEV-only source-bound local MOVE observation and lateral candidate.

This is a bounded L1 *candidate*, not an S10 learning update or an S11 Habit.
Action authorization, actual movement and M0 safety remain with S50/S51.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict

from adapters.mineflayer.b0_ground_foraging import GroundTarget
from adapters.mineflayer.python_protocol import MineflayerObservation, MineflayerPosition
from adapters.mineflayer.seek_execution import SeekConsequence, SeekConsequenceKind
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.provenance import Provenance
from relay_self.seek_waypoint import SeekWaypoint


class B1LocalRejected(ValueError):
    """No fresh session-matched native blocked Action evidence."""


class B1LocalCandidate:
    """Single-session observational Memory with an explicitly cheap OFF comparator.

    ON reads one recorded native BLOCKED action and proposes -Z; OFF reacts to
    the same blocked Action with a fixed +Z turn and retains no Memory. This
    comparison does not establish a learning or behavioral advantage.
    """

    def __init__(self, session_id: str, *, retain: bool = True) -> None:
        if not isinstance(session_id, str) or not session_id:
            raise B1LocalRejected("nonempty native session required")
        if type(retain) is not bool:
            raise B1LocalRejected("explicit retention switch required")
        self.session_id = session_id
        self.retain = retain
        self.cognition = PersistentCognition(IdentitySpecification(
            self_id="b1-dev-" + session_id,
            directives=("only retain source-scoped blocked MOVE observations",),
            provenance=Provenance("b1-dev", session_id),
        ))
        self.blocked_count = 0
        self.reuse_count = 0
        self.alternative_outcomes = 0
        self.alternative_progressed = 0
        self._blocked_target: int | None = None
        self._blocked_seq = -1
        self._blocked_position: MineflayerPosition | None = None
        self._lateral: MineflayerPosition | None = None

    def record_blocked(
        self, before: MineflayerObservation, effect: SeekConsequence,
        after: MineflayerObservation, target: GroundTarget,
    ) -> None:
        if (
            self.blocked_count != 0
            or not isinstance(before, MineflayerObservation)
            or not isinstance(after, MineflayerObservation)
            or not isinstance(effect, SeekConsequence)
            or not isinstance(target, GroundTarget)
            or any(s != self.session_id for s in (
                before.session_id, effect.session_id, after.session_id,
                target.session_id,
            ))
            or before.kind != "probe" or after.kind != "probe"
            or not before.request_id or not after.request_id
            or before.provenance.source != "mineflayer"
            or after.provenance.source != "mineflayer"
            or before.seq != effect.before_seq
            or not before.seq < effect.after_seq < after.seq
            or effect.kind is not SeekConsequenceKind.BLOCKED
            or not math.isfinite(effect.progress_m)
            or effect.progress_m >= 0.05
            or effect.remaining_m <= 0.7
            or target.probe_seq >= after.seq
        ):
            raise B1LocalRejected("one fresh blocked native source/action required")
        self.blocked_count = 1
        self._blocked_target = target.entity_id
        self._blocked_seq = after.seq
        self._blocked_position = after.snapshot.position
        pos = after.snapshot.position
        self._lateral = MineflayerPosition(
            pos.x, pos.y, pos.z - 1.8 if self.retain else pos.z + 1.8,
        )
        if self.retain:
            observation = {
                "session_id": self.session_id,
                "target_entity_id": target.entity_id,
                "action_id": effect.action_id,
                "before_seq": before.seq,
                "effect_after_seq": effect.after_seq,
                "correlated_followup_seq": after.seq,
                "observed_position": asdict(pos),
                "effect_kind": effect.kind.value,
                "effect_progress_m": effect.progress_m,
                "lateral_candidate": asdict(self._lateral),
                "epistemic_ceiling": "BLOCKED_MOVE_NOT_GENERAL_GOAL_FAILURE",
            }
            memory = Memory(
                memory_id="b1-blocked-" + effect.action_id,
                content=json.dumps(observation, sort_keys=True),
                source_provenance=after.provenance,
                integration_provenance=Provenance("b1-dev-observation", effect.action_id),
            )
            self.cognition = self.cognition.retain_memory(memory)

    def next_waypoint(
        self, read: MineflayerObservation, target: GroundTarget,
    ) -> SeekWaypoint:
        if (
            not isinstance(read, MineflayerObservation)
            or not isinstance(target, GroundTarget)
            or read.session_id != self.session_id
            or target.session_id != self.session_id
            or read.kind != "probe" or not read.request_id
            or read.provenance.source != "mineflayer"
        ):
            raise B1LocalRejected("foreign or nonnative local candidate")
        if self._lateral is None:
            return target.waypoint()
        if (
            read.seq <= self._blocked_seq
            or target.entity_id != self._blocked_target
            or self._blocked_position is None
        ):
            raise B1LocalRejected("stale or foreign blocked source reuse")
        pos = read.snapshot.position
        if self.reuse_count == 0 and math.hypot(
            pos.x - self._blocked_position.x,
            pos.z - self._blocked_position.z,
        ) > 1.0:
            raise B1LocalRejected("changed local World context cannot reuse blocked memory")
        lateral = self._lateral
        if self.retain:
            # Decode the already-retained observation to make the next choice:
            # an in-memory flag or a preprogrammed preference alone is not reuse.
            if len(self.cognition.memories) != 1:
                raise B1LocalRejected("retention ON requires one native Memory")
            try:
                record = json.loads(self.cognition.memories[0].content)
                if (
                    record["session_id"] != self.session_id
                    or record["target_entity_id"] != target.entity_id
                    or record["correlated_followup_seq"] != self._blocked_seq
                    or record["effect_kind"] != "BLOCKED"
                ):
                    raise B1LocalRejected("retained blocked source identity changed")
                coords = record["lateral_candidate"]
                lateral = MineflayerPosition(coords["x"], coords["y"], coords["z"])
            except (KeyError, TypeError, ValueError) as exc:
                raise B1LocalRejected("retained observation not reusable") from exc
            if lateral != self._lateral:
                raise B1LocalRejected("retained candidate differs from source scope")
        if math.hypot(
            pos.x - lateral.x, pos.z - lateral.z,
        ) <= 0.65:
            self._lateral = None
            return target.waypoint()
        self.reuse_count += 1 if self.reuse_count == 0 else 0
        return SeekWaypoint(
            goal_id="b1-local-lateral",
            target=lateral,
            tolerance_m=0.65, max_step_m=1.0,
        )

    def record_alternative_outcome(self, effect: SeekConsequence) -> None:
        if (
            not isinstance(effect, SeekConsequence)
            or effect.session_id != self.session_id
            or self.reuse_count == 0
            or effect.kind not in (
                SeekConsequenceKind.BLOCKED,
                SeekConsequenceKind.PROGRESSED,
                SeekConsequenceKind.ARRIVED,
            )
        ):
            raise B1LocalRejected("native alternative effect required")
        self.alternative_outcomes += 1
        if effect.kind is not SeekConsequenceKind.BLOCKED:
            self.alternative_progressed += 1

    def evidence(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "retention_enabled": self.retain,
            "retained_observations": len(self.cognition.memories),
            "blocked_action_count": self.blocked_count,
            "reused_for_lateral_choice": self.reuse_count if self.retain else 0,
            "lateral_choice_count": self.reuse_count,
            "alternative_outcomes": self.alternative_outcomes,
            "alternative_progressed": self.alternative_progressed,
            "fixed_off_policy": "PLUS_Z_AFTER_BLOCKED",
            "retained_on_policy": "MINUS_Z_FROM_ONE_NATIVE_BLOCKED_ACTION",
            "learning_qualified": False,
            "habit_created": False,
            "science_success": False,
        }
