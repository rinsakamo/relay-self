"""Product DEV-only read of *existing* S49 native probes into SelfBody/World.

No sender, L0/L1 selector, provider, S10 writer or World owner is reachable.
All data is a transient per-probe projection; this witness is NOT physical
source attestation or evidence of adaptive behavior.
"""
from __future__ import annotations

from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from relay_self.self_body import compose_self_body_view
from relay_self.self_world import compose_self_world_view

DEV_SELF_ID = "self-product-passive-native-observer"
MAX_PROBES = 3


class PassiveSelfViewsRejected(ValueError):
    """Foreign, stale, duplicate or non-native observer source."""


class PassiveSelfViews:
    """Single S49 session; one common source per transient Body/World epoch."""

    def __init__(self) -> None:
        self._session: str | None = None
        self._last_seq: int = -1
        self._seen_body: tuple[str, ...] = ()
        self._seen_world: tuple[str, ...] = ()
        self._rows: list[dict] = []
        self._errors: list[str] = []

    def observe(self, reading: MineflayerObservation) -> None:
        """Project already received probe, without requesting another one."""
        if not isinstance(reading, MineflayerObservation) or reading.kind != "probe":
            raise PassiveSelfViewsRejected("original S49 correlated probe required")
        if (
            type(reading.seq) is not int or reading.seq <= self._last_seq
            or not isinstance(reading.session_id, str) or not reading.session_id
            or reading.request_id is None
            or not reading.request_id.startswith(
                f"s49-actual:{reading.session_id}:event-"
            )
            or self._session not in (None, reading.session_id)
            or len(self._rows) >= MAX_PROBES
        ):
            raise PassiveSelfViewsRejected("foreign/replayed/excess native probe")
        present = project_mineflayer_present(reading)
        if (
            present.session_id != reading.session_id
            or present.seq != reading.seq
            or present.request_id != reading.request_id
            or present.provenance.reference != f"{reading.session_id}:{reading.seq}"
        ):
            raise PassiveSelfViewsRejected("noncorrelated native Present")
        epoch = f"native-probe-{reading.seq}"
        body = compose_self_body_view(
            self_id=DEV_SELF_ID, session_id=reading.session_id, epoch_id=epoch,
            observation=project_body_present(present),
            minimum_native_seq=self._last_seq + 1,
            seen_observation_refs=self._seen_body,
        )
        world = compose_self_world_view(
            self_id=DEV_SELF_ID, session_id=reading.session_id, epoch_id=epoch,
            observation=project_self_world_present(present, observer_id=DEV_SELF_ID),
            self_body=body,
            minimum_native_seq=self._last_seq + 1,
            seen_observation_refs=self._seen_world,
        )
        if (
            world.self_body is not body or world.observation is None
            or body.observation is None
            or world.observation.provenance != body.observation.source_provenance
            or world.observation.native_seq != body.observation.native_seq
            or world.observation.request_id != body.observation.request_id
        ):
            raise PassiveSelfViewsRejected("SelfBody/SelfWorld source did not join")
        self._rows.append({
            "kind": "passive_self_views",
            "classification": "DEV_ONLY_NOT_QUALIFIED",
            "self_id": DEV_SELF_ID,
            "session_id": reading.session_id,
            "native_seq": reading.seq,
            "request_id": reading.request_id,
            "body_source_ref": body.observation.source_ref,
            "world_source_ref": world.observation.source_ref,
            "body_world_exact_source_join": True,
            "health_observed": body.observed("health").value,
            "food_observed": body.observed("food").value,
            "observed_world_entities": len(world.observation.entities),
            "coverage_truncated": world.observation.coverage_truncated,
            "unobserved_world_absent": None,
            "world_safe": None,
            "action_authorized": False,
            "action_issued": False,
            "model_calls": 0,
            "s10_commits": 0,
            "memory_writes": 0,
        })
        self._session = reading.session_id
        self._last_seq = reading.seq
        self._seen_body = (*self._seen_body, body.observation.source_ref)
        self._seen_world = (*self._seen_world, world.observation.source_ref)

    def record_error(self, exc: Exception) -> None:
        """Retain observer failure without allowing it to control original L0."""
        self._errors.append(type(exc).__name__)

    def rows(self) -> tuple[dict, ...]:
        return tuple(dict(row) for row in self._rows)

    def summary(self) -> dict:
        return {
            "kind": "passive_self_views_summary",
            "classification": "DEV_ONLY_NOT_QUALIFIED",
            "session_id": self._session,
            "native_probes_joined": len(self._rows),
            "observer_errors": list(self._errors),
            "source_scope": "ORIGINAL_S49_PROBE_CALLBACK_NOT_INDEPENDENT_ATTESTATION",
            "action_issuer": "EXISTING_S49_ONLY",
            "extra_native_probes": 0,
            "model_calls": 0,
            "action_issued": False,
            "s10_commits": 0,
            "memory_writes": 0,
            "source_qualified": False,
            "science_qualified": False,
        }
