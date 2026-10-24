"""DEV-only S49 owner-local WAIT issuer fence, never World proof.

Only the existing owner may invoke this companion around its normal issuer.
It does not install an Executor, listener or timer, and requires the owner to
call before_issue *before* every Action issuance on that same code path.
Other issuers, Paper clock authenticity, full-tick activity and original-source
custody are outside this module. Never mint SourceBoundTick(WAIT).
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from relay_self.action_supervision import ActionSupervisor

SOURCE = "S49_P1_OWNER_WAIT_FENCE_DEV_V1"
MAX_ROWS = 12  # ARM + 8 OBSERVED ticks + SEAL; ABORT for failed windows
FIELDS = frozenset({
    "source", "ordinal", "kind", "session_id", "marker_id", "world",
    "world_tick", "source_ref", "action_id", "controls_clear_ref",
})


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 256


def _row(kind: str, session: str, marker: str, world: str,
         ordinal: int, tick: int | None, source_ref: str,
         action_id: str | None, clear_ref: str | None = None) -> dict:
    return {
        "source": SOURCE, "ordinal": ordinal, "kind": kind,
        "session_id": session, "marker_id": marker, "world": world,
        "world_tick": tick, "source_ref": source_ref,
        "action_id": action_id, "controls_clear_ref": clear_ref,
    }


class S49WaitFenceDev:
    """Owner-invoked synchronous admission fence; fail closed on any drift.

    This class must be held by S49's *existing* sole Action-issuer code path.
    It is not connected to original qualify() in this DEV phase. A caller
    falsely reporting an empty Supervisor or a Paper tick is NOT attestation.
    """

    def __init__(self, *, owner: object, supervisor: ActionSupervisor,
                 session_id: str, marker_id: str, world: str):
        if (owner is None or not isinstance(supervisor, ActionSupervisor)
                or any(not _identifier(x) for x in (session_id, marker_id, world))):
            raise BoundaryRejected("invalid owner-local WAIT fence identity")
        self._owner = owner
        self._supervisor = supervisor
        self._session = session_id
        self._marker = marker_id
        self._world = world
        self._phase = "NEW"
        self._rows: list[dict] = []
        self._previous_tick: int | None = None

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def original_rows(self) -> tuple[dict, ...]:
        return tuple(dict(row) for row in self._rows)

    def _check(self, owner: object) -> None:
        if owner is not self._owner:
            self._phase = "ABORTED"
            raise BoundaryRejected("unrecognized WAIT fence owner")
        if self._supervisor.open_actions:
            self._phase = "ABORTED"
            raise BoundaryRejected("open supervised Action during owner WAIT fence")

    def _record(self, kind: str, tick: int | None, ref: str,
                action: str | None, clear_ref: str | None = None) -> None:
        if not _identifier(ref):
            self._phase = "ABORTED"
            raise BoundaryRejected("missing original source reference")
        self._rows.append(_row(
            kind, self._session, self._marker, self._world,
            len(self._rows) + 1, tick, ref, action, clear_ref,
        ))

    def arm(self, owner: object, *, closed_action_id: str,
            terminal_outcome_ref: str, controls_clear_ref: str) -> None:
        self._check(owner)
        if (self._phase != "NEW" or not _identifier(closed_action_id)
                or not _identifier(controls_clear_ref)):
            self._phase = "ABORTED"
            raise BoundaryRejected("WAIT arm needs closed Action and clear readback")
        # These references alone never attest actual terminal or motor release.
        self._record("ARM", None, terminal_outcome_ref, closed_action_id,
                     controls_clear_ref)
        self._phase = "ARMED"

    def before_issue(self, owner: object, *, action_id: str,
                     attempted_source_ref: str) -> None:
        """Sole issuer must invoke BEFORE grant/physical command, not after."""
        self._check(owner)
        if not _identifier(action_id) or not _identifier(attempted_source_ref):
            self._phase = "ABORTED"
            raise BoundaryRejected("invalid attempted Action source")
        if self._phase in {"ARMED", "SAMPLING"}:
            # Invalidate, do not silently keep clean WAIT samples.
            self._phase = "ABORTED"
            self._record("BLOCKED_ISSUE", None, attempted_source_ref, action_id)
            raise BoundaryRejected("Action attempted inside owner WAIT fence")
        if self._phase != "SEALED":
            raise BoundaryRejected("WAIT fence not safely released")

    def observe_paper_tick(self, owner: object, *, world_tick: int,
                           source_ref: str) -> None:
        self._check(owner)
        if (self._phase not in {"ARMED", "SAMPLING"}
                or type(world_tick) is not int or world_tick < 1
                or len(self._rows) >= 9
                or (self._previous_tick is not None
                    and world_tick != self._previous_tick + 1)):
            self._phase = "ABORTED"
            raise BoundaryRejected("gapped, excessive or unordered WAIT tick")
        self._record("PAPER_SAMPLE", world_tick, source_ref, None)
        self._previous_tick = world_tick
        self._phase = "SAMPLING"

    def seal(self, owner: object, *, seal_source_ref: str) -> tuple[dict, ...]:
        self._check(owner)
        if self._phase != "SAMPLING" or len(self._rows) != 9:
            self._phase = "ABORTED"
            raise BoundaryRejected("incomplete WAIT fence cannot seal")
        self._record("SEAL", None, seal_source_ref, None)
        self._phase = "SEALED"
        return self.original_rows


def review_s49_owner_wait_fence(rows: Sequence[Mapping[str, object]], *,
                                session_id: str, marker_id: str, world: str,
                                first_world_tick: int, last_world_tick: int) -> dict:
    """Validate S49 owner-local emission shape, not provenance or World clock."""
    if (not isinstance(rows, (list, tuple)) or len(rows) != 10
            or any(not _identifier(x) for x in (session_id, marker_id, world))
            or type(first_world_tick) is not int or first_world_tick < 1
            or type(last_world_tick) is not int
            or last_world_tick != first_world_tick + 7):
        raise BoundaryRejected("missing/unbounded owner WAIT fence original")
    for i, row in enumerate(rows):
        kind = "ARM" if i == 0 else "SEAL" if i == 9 else "PAPER_SAMPLE"
        tick = first_world_tick + i - 1 if 1 <= i <= 8 else None
        if (not isinstance(row, Mapping) or set(row) != FIELDS
                or row.get("source") != SOURCE
                or type(row.get("ordinal")) is not int
                or row["ordinal"] != i + 1 or row.get("kind") != kind
                or row.get("session_id") != session_id
                or row.get("marker_id") != marker_id
                or row.get("world") != world
                or row.get("world_tick") != tick
                or not _identifier(row.get("source_ref"))
                or (not _identifier(row.get("action_id")) if i == 0
                    else row.get("action_id") is not None)
                or (not _identifier(row.get("controls_clear_ref")) if i == 0
                    else row.get("controls_clear_ref") is not None)):
            raise BoundaryRejected("unbound or forged owner WAIT fence row")
    return {
        "classification": "S49_OWNER_LOCAL_ISSUER_FENCE_DEV_ONLY",
        "owner_original_rows": len(rows),
        "session_id": session_id,
        "first_world_tick": first_world_tick,
        "last_world_tick": last_world_tick,
        "same_owner_local_action_window_screened": True,
        "original_source_authenticated_by_r": False,
        "global_issuer_absence": "NOT_ATTESTED",
        "paper_world_clock_bound_to_owner": "NOT_ATTESTED",
        "whole_tick_physical_inactivity": "NOT_ATTESTED",
        "wait_interval_ref": None,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "science_go": False,
    }
