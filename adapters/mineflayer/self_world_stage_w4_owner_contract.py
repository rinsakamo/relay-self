"""W4-OWNER: offline-only admission contract for the ORIGINAL S49 reader.

This gate NEVER receives a Mineflayer session, process, server, stdin/out,
Action issuer, or S10 writer. It cannot install itself in an S49 live path.
Its owner token is an in-process test capability, NOT independently verified
S49 ownership or external authorization.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerOrientedSnapshot,
)
from adapters.mineflayer.self_world_stage_w4_logtap import W4CollectorMarker
from adapters.mineflayer.self_world_stage_w4_preflight import (
    W4PreworldBlocked,
    plan_native_nh1_placement,
    require_native_nh1_orientation,
)
from adapters.mineflayer.self_world_stage_w4_window import (
    W4PlacementCommands,
    build_w4_window_commands,
)


@dataclass(frozen=True, slots=True)
class W4OwnerReadback:
    schema: str
    session_id: str
    slot: int
    pre_source: str
    post_source: str
    marker_hash: str
    token: str
    placement_window: str = "UNATTESTED_PREWORLD_BLOCKED"
    owner_attested: bool = False
    trusted_world_tick: bool = False
    physical_run_permitted: bool = False
    s10_permission: bool = False


class W4OwnerHandoffGate:
    """Single ordered consumer of already-owned observations (DEV synthetic).

    Important: this is a *contract* a future original-owner implementation
    would need to meet, not evidence the original S49 runtime meets it.
    """

    def __init__(self, *, session_id: str, native_owner: object) -> None:
        if not session_id or type(native_owner) is not object:
            raise W4PreworldBlocked("session and distinct in-process owner required")
        self._session = session_id
        self._native_owner = native_owner
        self._phase = "IDLE"
        self._pre: MineflayerObservation | None = None
        self._commands: W4PlacementCommands | None = None
        self._marker: W4CollectorMarker | None = None
        self._active_token: str | None = None
        self._active_slot: int | None = None
        self._source_refs: set[str] = set()
        self._used_tokens: set[str] = set()
        self._last_seq = -1

    @property
    def phase(self) -> str:
        return self._phase

    def _deny(self, detail: str) -> None:
        self._phase = "BLOCKED"
        raise W4PreworldBlocked(detail)

    def _check_owner(self, owner: object) -> None:
        if owner is not self._native_owner:
            self._deny("foreign or missing original native-reader owner token")

    def before_world(
        self, observation: MineflayerObservation, *,
        owner: object, request_id: str, slot: int, token: str,
        origin: str,
    ) -> W4PlacementCommands:
        """Pre-world observation must be explicitly S49-owner-mediated.

        The existing post-entity reprobe callback cannot supply this before
        a zombie exists; labeling it PREWORLD is not a provenance upgrade.
        """
        self._check_owner(owner)
        if (
            self._phase != "IDLE"
            or origin != "s49_original_owner_pre_world"
            or type(observation) is not MineflayerObservation
            or observation.session_id != self._session
            or observation.seq <= self._last_seq
            or observation.provenance.reference in self._source_refs
            or type(slot) is not int or slot not in (1, 2)
        ):
            self._deny("not a fresh preworld original-owner reading")
        try:
            require_native_nh1_orientation(
                observation, expected_session=self._session,
                expected_request_id=request_id, before_seq=observation.seq + 1,
                minimum_seq=self._last_seq + 1,
                seen_source_refs=frozenset(self._source_refs),
            )
            placement = plan_native_nh1_placement(
                observation, expected_session=self._session,
                expected_request_id=request_id, before_seq=observation.seq + 1,
                slot=slot,
            )
            commands = build_w4_window_commands(
                placement, one_time_token=token,
                seen_tokens=frozenset(self._used_tokens),
            )
        except (W4PreworldBlocked, ValueError, TypeError) as exc:
            self._deny("invalid source-bound preworld placement")
            raise AssertionError("unreachable") from exc
        self._pre = observation
        self._commands = commands
        self._active_token = token
        self._active_slot = slot
        self._source_refs.add(observation.provenance.reference)
        self._phase = "AWAIT_MARKER"
        return commands

    def observe_existing_collector_marker(
        self, marker: W4CollectorMarker, *, owner: object,
    ) -> None:
        self._check_owner(owner)
        commands = self._commands
        if (
            self._phase != "AWAIT_MARKER"
            or type(marker) is not W4CollectorMarker
            or commands is None
            or marker.log_line.count(commands.confirmation_marker) != 1
            or not marker.log_line.endswith(commands.expected_log_suffix)
            or marker.start_byte < marker.cursor.start_byte
            or marker.end_byte <= marker.start_byte
            or not marker.producer_content_only
            or marker.external_source_qualified
            or marker.physical_run_permitted
        ):
            self._deny("existing collector content marker absent or inconsistent")
        self._marker = marker
        self._phase = "AWAIT_POST_PROBE"

    def after_world(
        self, observation: MineflayerObservation, *,
        owner: object, request_id: str,
    ) -> W4OwnerReadback:
        self._check_owner(owner)
        pre, commands, marker = self._pre, self._commands, self._marker
        if (
            self._phase != "AWAIT_POST_PROBE"
            or pre is None or commands is None or marker is None
            or type(observation) is not MineflayerObservation
            or observation.session_id != self._session
            or observation.kind != "probe"
            or observation.request_id != request_id
            or request_id == pre.request_id
            or observation.seq <= pre.seq
            or observation.provenance.reference in self._source_refs
            or not isinstance(observation.snapshot, MineflayerOrientedSnapshot)
        ):
            self._deny("native after-probe lacks exact sole-owner lineage")
        self._source_refs.add(observation.provenance.reference)
        self._last_seq = observation.seq
        self._used_tokens.add(self._active_token)
        self._phase = "IDLE"
        return W4OwnerReadback(
            schema="W4_OWNER_DEV_CONTENT_CONTRACT_V0",
            session_id=self._session,
            slot=self._active_slot,
            pre_source=pre.provenance.reference,
            post_source=observation.provenance.reference,
            marker_hash=marker.raw_line_sha256,
            token=self._active_token,
        )

    def abort(self, *, owner: object) -> None:
        self._check_owner(owner)
        self._phase = "BLOCKED"
