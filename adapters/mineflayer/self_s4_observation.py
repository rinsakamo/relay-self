"""S4 read-only native observation audit for natural Self World sessions.

Measures only the *outer* S49 stream accepted by the bounded driver.
It does not observe protocol messages consumed by S49 probe/Action internals,
nor prove global absence of a target in the underlying Minecraft World.
"""
from __future__ import annotations

from collections import Counter

from adapters.mineflayer.python_protocol import MineflayerObservation


class ObservationAuditRejected(ValueError):
    """Unexpected or non-monotone native source; no inferred safe observation."""


class S4NativeObservationAudit:
    """Bounded, owner-local counters; no Action, model, or observation reads."""

    def __init__(self, session_id: str, *, max_frames: int) -> None:
        if (
            not isinstance(session_id, str) or not session_id
            or type(max_frames) is not int or not 1 <= max_frames <= 10000
        ):
            raise ObservationAuditRejected("explicit session and frame ceiling required")
        self.session_id = session_id
        self.max_frames = max_frames
        self.frames = 0
        self.first_seq: int | None = None
        self.last_seq: int | None = None
        self.kinds: Counter[str] = Counter()
        self.entity_frames = 0
        self.entity_frames_no_zombie = 0
        self.entity_frames_with_zombie = 0
        self.non_entity_frames_with_zombie = 0
        self.snapshots_with_zombie = 0
        self.snapshots_coverage_truncated = 0
        self.entity_snapshots_coverage_truncated = 0
        self.near_zombie_snapshots = 0
        self.multiple_zombie_snapshots = 0

    def observe(self, frame: MineflayerObservation) -> None:
        """Called synchronously after the driver receives an original native frame."""
        if (
            not isinstance(frame, MineflayerObservation)
            or frame.session_id != self.session_id
            or frame.provenance.source != "mineflayer"
            or frame.request_id is not None
            or (self.last_seq is not None and frame.seq <= self.last_seq)
            or self.frames >= self.max_frames
        ):
            raise ObservationAuditRejected("foreign/replayed/unbounded native frame")
        self.frames += 1
        if self.first_seq is None:
            self.first_seq = frame.seq
        self.last_seq = frame.seq
        self.kinds[frame.kind] += 1
        snapshot = frame.snapshot
        coverage = snapshot.nearby_entities_coverage
        if coverage.truncated:
            self.snapshots_coverage_truncated += 1
            if frame.kind == "entities":
                self.entity_snapshots_coverage_truncated += 1
        targets = tuple(e for e in snapshot.nearby_entities if e.name == "zombie")
        if targets:
            self.snapshots_with_zombie += 1
            if len(targets) > 1:
                self.multiple_zombie_snapshots += 1
            if any(0 < e.distance < 4 for e in targets):
                self.near_zombie_snapshots += 1
        if frame.kind == "entities":
            self.entity_frames += 1
            if targets:
                self.entity_frames_with_zombie += 1
            else:
                self.entity_frames_no_zombie += 1
        elif targets:
            self.non_entity_frames_with_zombie += 1

    def report(self, source: object, *, decisions: int) -> dict[str, object]:
        """Single end-of-session summary; describes observed scope, not World safety."""
        if type(decisions) is not int or decisions < 0:
            raise ObservationAuditRejected("invalid original L0 decision counter")
        source_counters = {}
        for key in (
            "ignored_non_target_entities",
            "ignored_duplicate_target_updates",
            "ignored_hurt_frames",
        ):
            value = getattr(source, key, 0)
            if type(value) is not int or value < 0:
                raise ObservationAuditRejected("unqualified source filter counter")
            source_counters[key] = value
        if decisions:
            verdict = "S49_DECISION_PATH_ENTERED"
        elif self.entity_frames_with_zombie:
            verdict = "ENTITY_TARGET_OUTER_SEEN_BUT_NO_DECISION"
        elif self.non_entity_frames_with_zombie:
            verdict = "ZOMBIE_ONLY_IN_NON_ENTITY_SNAPSHOTS"
        elif self.snapshots_coverage_truncated:
            verdict = "NO_TARGET_OBSERVED_WITH_TRUNCATED_REGISTRY"
        elif self.frames:
            verdict = "NO_ZOMBIE_IN_OUTER_OBSERVED_SNAPSHOTS"
        else:
            verdict = "NO_OUTER_NATIVE_OBSERVATIONS"
        return {
            "audit_schema": "SELF_S4_OUTER_NATIVE_AUDIT_V1",
            "classification": verdict,
            "accepted_outer_frames": self.frames,
            "first_outer_source_seq": self.first_seq,
            "last_outer_source_seq": self.last_seq,
            "outer_observation_kind_counts": dict(sorted(self.kinds.items())),
            "entity_frames": self.entity_frames,
            "entity_frames_no_zombie": self.entity_frames_no_zombie,
            "entity_frames_with_zombie": self.entity_frames_with_zombie,
            "non_entity_frames_with_zombie": self.non_entity_frames_with_zombie,
            "snapshots_with_zombie": self.snapshots_with_zombie,
            "snapshots_coverage_truncated": self.snapshots_coverage_truncated,
            "entity_snapshots_coverage_truncated": self.entity_snapshots_coverage_truncated,
            "near_zombie_snapshots": self.near_zombie_snapshots,
            "multiple_zombie_snapshots": self.multiple_zombie_snapshots,
            "native_source_filter_counters": source_counters,
            "s49_decisions": decisions,
            "underlying_world_absence_proven": False,
            "all_native_decoded_messages_observed": False,
            "inner_probe_action_frames_audited": False,
            "source_frames_archived_individually": False,
            "action_authority": False,
            "learning_updates": 0,
            "habit_grants": 0,
        }
